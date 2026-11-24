#!/usr/bin/env python3
"""术语表强制约束与全篇回填核验（scripts/check_terminology.py）

机械执行"术语稳"：术语表不是写在提示里的建议，而是逐段强制核验的约束。

输入：
  --terms     terminology.json：[{"term","locked","alternates"[],"frozen"}]
              term      原文术语（大小写不敏感匹配）
              locked    唯一锁定译名（target 中必须出现）
              alternates 旧译/别译清单（target 中出现即判漂移）
              frozen    true 时 locked 必须逐字（区分大小写）出现
  --segments  segments.json：[{"id","source","target"}]
  --report    报告输出路径（缺省打印到 stdout）

检查：
  (a) 回填：source 含某 term 时，target 必须含其 locked 译名 → 否则 error；
  (b) 漂移：target 出现 alternates 中任何旧译/别译 → warning；
  (c) frozen=true 的术语：target 必须逐字出现 locked → 否则 error。

输出：JSON 报告 {"errors":[],"warnings":[],"checked_terms":N,"checked_segments":M}
退出码：有 error → 1；否则 0。仅依赖 Python 标准库。
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


def check(terms, segments):
    errors, warnings = [], []
    for seg in segments:
        seg_id = seg.get("id", "?")
        source = seg.get("source", "") or ""
        target = seg.get("target", "") or ""
        for entry in terms:
            term = entry.get("term", "")
            locked = entry.get("locked", "")
            if not term or not locked:
                continue
            if not contains(source, term, ignore_case=True):
                continue  # 该段不含此术语，不约束
            # (a)/(c) 回填与 frozen 逐字
            if entry.get("frozen"):
                if not contains(target, locked, ignore_case=False):
                    errors.append({
                        "segment_id": seg_id, "term": term, "locked": locked,
                        "type": "frozen_violation",
                        "message": f"{seg_id}: 冻结术语 '{term}' 的锁定译名 '{locked}' 未逐字出现于译文",
                    })
            else:
                if not contains(target, locked, ignore_case=True):
                    errors.append({
                        "segment_id": seg_id, "term": term, "locked": locked,
                        "type": "missing_backfill",
                        "message": f"{seg_id}: 原文含术语 '{term}'，译文未回填锁定译名 '{locked}'",
                    })
            # (b) 漂移：旧译/别译出现即 warning（与 locked 相同者除外）
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
        "checked_terms": len(terms),
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
