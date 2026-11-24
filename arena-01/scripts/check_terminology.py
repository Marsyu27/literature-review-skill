#!/usr/bin/env python3
"""术语表强制约束与全篇回填核验（scripts/check_terminology.py）

输入：
  --terms     terminology.json：[{"term","aliases"[],"locked","context"[],
                                  "alternates"[],"frozen"}]
              term       原文术语 canonical form（大小写不敏感匹配）
              aliases    同概念的其他原文表面形式；任一形式出现都触发 locked
              locked     唯一锁定译名（target 中必须出现）
              context    可选正则字符串或正则列表；至少一个正则匹配 source 才锁定
              alternates 旧译/别译清单（target 中出现即判漂移）
              frozen     true 时 locked 必须逐字（区分大小写）出现
  --segments  segments.json：[{"id","source","target"}]
  --report    报告输出路径（缺省打印到 stdout）

同一表面形式被多条术语登记时，每条都必须配置 context；每个 source 段落中
同一表面形式只能命中一个语境候选，否则报告明确配置错误，不会同时要求两个译名。
旧式简单 {"term","locked","alternates","frozen"} 记录完全兼容，aliases/context 可省。

输出：JSON 报告 {"errors":[],"warnings":[],"checked_terms":N,"checked_segments":M}
退出码：有 error（含配置错误）→ 1；否则 0。仅依赖 Python 标准库。
"""
import argparse
import json
import re
import sys


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _ascii_bounded(term):
    """术语首尾均为 ASCII 字母数字时启用词边界，避免 TEF 命中 TEF-1X 之类。"""
    return bool(term) and term[0].isascii() and term[0].isalnum() \
        and term[-1].isascii() and term[-1].isalnum()


def contains(text, needle, ignore_case=False):
    """needle 是否出现于 text；ASCII 术语加词边界，中文等直接子串匹配。"""
    if not needle or not text:
        return False
    flags = re.IGNORECASE if ignore_case else 0
    pat = re.escape(needle)
    if _ascii_bounded(needle):
        pat = r"(?<![A-Za-z0-9])" + pat + r"(?![A-Za-z0-9])"
    return re.search(pat, text, flags) is not None


def _surface_key(surface):
    return surface.strip().casefold()


def _context_list(entry):
    context = entry.get("context")
    if context is None or context == "":
        return []
    if isinstance(context, str):
        return [context]
    if isinstance(context, list) and all(isinstance(x, str) and x for x in context):
        return context
    return None


def _configuration(terms):
    """校验新结构，建立 surface -> entry indices；错误用报告表达而非异常崩溃。"""
    errors = []
    surfaces = {}
    contexts = {}
    invalid_entries = set()
    invalid_surfaces = set()

    if not isinstance(terms, list):
        return [{
            "type": "configuration_error",
            "message": "terminology.json 顶层必须是术语对象数组",
        }], surfaces, contexts, invalid_entries, invalid_surfaces

    for idx, entry in enumerate(terms):
        if not isinstance(entry, dict):
            errors.append({
                "type": "configuration_error", "entry_index": idx,
                "message": f"术语条目[{idx}] 必须是对象",
            })
            invalid_entries.add(idx)
            continue
        term = entry.get("term", "")
        locked = entry.get("locked", "")
        if not isinstance(term, str) or not term.strip() \
                or not isinstance(locked, str) or not locked:
            errors.append({
                "type": "configuration_error", "entry_index": idx,
                "message": f"术语条目[{idx}] 必须含非空字符串 term 与 locked",
            })
            invalid_entries.add(idx)
            continue
        aliases = entry.get("aliases", []) or []
        if not isinstance(aliases, list) or not all(isinstance(x, str) for x in aliases):
            errors.append({
                "type": "configuration_error", "entry_index": idx, "term": term,
                "message": f"术语 '{term}' 的 aliases 必须是字符串数组",
            })
            invalid_entries.add(idx)
            continue
        patterns = _context_list(entry)
        if patterns is None:
            errors.append({
                "type": "configuration_error", "entry_index": idx, "term": term,
                "message": f"术语 '{term}' 的 context 必须是正则字符串或非空正则字符串数组",
            })
            invalid_entries.add(idx)
            continue
        compiled = []
        for pattern in patterns:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as exc:
                errors.append({
                    "type": "configuration_error", "entry_index": idx, "term": term,
                    "context": pattern,
                    "message": f"术语 '{term}' 的 context 正则无效: {exc}",
                })
                invalid_entries.add(idx)
        contexts[idx] = compiled
        for surface in [term] + aliases:
            surface = surface.strip()
            if surface:
                surfaces.setdefault(_surface_key(surface), {})[idx] = surface

    # 同名多义没有语境是配置错误；这些 surface 不再执行相互冲突的双锁定。
    for key, owners in surfaces.items():
        if len(owners) <= 1:
            continue
        no_context = [idx for idx in owners if not contexts.get(idx)]
        if no_context:
            invalid_surfaces.add(key)
            sample = next(iter(owners.values()))
            errors.append({
                "type": "configuration_error", "surface": sample,
                "entry_indices": sorted(owners),
                "message": (
                    f"表面形式 '{sample}' 对应多条术语条目，但其中存在无 context 的条目； "
                    "多义条目必须分别配置可区分语境的 context 正则列表"
                ),
            })
    return errors, surfaces, contexts, invalid_entries, invalid_surfaces


def check(terms, segments):
    errors, warnings = [], []
    config_errors, surfaces, contexts, invalid_entries, invalid_surfaces = _configuration(terms)
    errors.extend(config_errors)

    for seg in segments:
        seg_id = seg.get("id", "?")
        source = seg.get("source", "") or ""
        target = seg.get("target", "") or ""
        selected = {}  # entry index -> 触发该条锁定的原文表面形式集合

        for key, owners in surfaces.items():
            if key in invalid_surfaces:
                continue
            present = {idx: surface for idx, surface in owners.items()
                       if contains(source, surface, ignore_case=True)}
            if not present:
                continue
            candidates = {
                idx: surface for idx, surface in present.items()
                if idx not in invalid_entries
                and (not contexts.get(idx)
                     or any(pattern.search(source) for pattern in contexts[idx]))
            }
            if len(candidates) > 1:
                sample = next(iter(present.values()))
                errors.append({
                    "segment_id": seg_id, "surface": sample,
                    "entry_indices": sorted(candidates),
                    "type": "ambiguous_context",
                    "message": (
                        f"{seg_id}: 表面形式 '{sample}' 同时命中多个语境候选 "
                        f"{sorted(candidates)}；同一表面形式只能有一个候选可执行锁定"
                    ),
                })
                continue
            for idx, surface in candidates.items():
                selected.setdefault(idx, set()).add(surface)

        for idx, matched_surfaces in sorted(selected.items()):
            entry = terms[idx]
            term = entry["term"]
            locked = entry["locked"]
            forms = "/".join(sorted(matched_surfaces, key=str.casefold))
            # (a)/(c) 回填与 frozen 逐字：同一条目有任一表面形式即执行一次。
            if entry.get("frozen"):
                if not contains(target, locked, ignore_case=False):
                    errors.append({
                        "segment_id": seg_id, "term": term, "matched": sorted(matched_surfaces),
                        "locked": locked, "type": "frozen_violation",
                        "message": f"{seg_id}: 原文含术语形式 '{forms}'，冻结译名 '{locked}' 未逐字出现于译文",
                    })
            else:
                if not contains(target, locked, ignore_case=True):
                    errors.append({
                        "segment_id": seg_id, "term": term, "matched": sorted(matched_surfaces),
                        "locked": locked, "type": "missing_backfill",
                        "message": f"{seg_id}: 原文含术语形式 '{forms}'，译文未回填锁定译名 '{locked}'",
                    })
            # (b) 漂移：旧译/别译出现即 warning（与 locked 相同者除外）。
            for alt in entry.get("alternates", []) or []:
                if not alt or alt == locked:
                    continue
                if contains(target, alt, ignore_case=True):
                    warnings.append({
                        "segment_id": seg_id, "term": term, "alternate": alt,
                        "type": "drift",
                        "message": f"{seg_id}: 译文出现术语 '{term}' 的旧译/别译 '{alt}'，应统一为 '{locked}'",
                    })
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description="术语表强制约束与全篇回填核验")
    ap.add_argument("--terms", required=True, help="terminology.json 路径")
    ap.add_argument("--segments", required=True, help="segments.json 路径")
    ap.add_argument("--report", default=None, help="报告输出路径（缺省 stdout）")
    args = ap.parse_args()

    terms = load_json(args.terms)
    segments = load_json(args.segments)
    errors, warnings = check(terms, segments)
    report = {
        "errors": errors,
        "warnings": warnings,
        "checked_terms": len(terms) if isinstance(terms, list) else 0,
        "checked_segments": len(segments),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"报告已写入 {args.report}：errors={len(errors)} warnings={len(warnings)}")
    else:
        print(text)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
