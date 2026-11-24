#!/usr/bin/env python3
"""validate_anchors.py — 校验锚点真实性、quote 与必填覆盖（纯标准库）。

规则：
  1. 递归收集 result.json 中所有带 `source_anchor`/`anchor` 字段的条目，锚点
     形态须为 `§x` 或 `§x ¶y`（可附带 Table/Fig 等补充定位）。
  2. 每个 §x 必须存在于 anchor_index.json 的 sections；若带 ¶y，该段落必须存在。
  3. 非空 quote 必须是被引范围原文的子串；大小写不敏感、空白归一。
  4. success/partial 下双向对照索引与 result.sections 的完整 §ID：success 不得
     缺节、多节或使用 uncertain 占位；partial 的每个未完成索引章节都必须有
     {id, status=uncertain, reason} 占位，不能静默漏节。正常 section 的
     source_anchor 必须包含自己的 §ID，preamble 不例外。
  5. success 下，所有非空 paper_card 字段必须由顶层 paper_card_anchors 覆盖，
     每个 section 和 knowledge_point 都必须有 source_anchor。
  6. partial 下仅明确 status=uncertain 的条目可缺锚点（warning），但至少要有
     一个核心内容真实有效的锚点，且 status_reason/uncertainties 必须交代缺口。
     仅有空内容的 unable 可不产生锚点，但必须写 status_reason。
  7. checked=0 的空锚点全集不得通过（上述 unable 例外除外）。

paper_card_anchors 项形如 {"field":"findings", "source_anchor":"§2 ¶1",
"quote":"可选原文"}；partial 的缺锚点占位可写 {"field":"limitations",
"status":"uncertain", "reason":"原文定位待确认"}。

用法：
  python3 scripts/validate_anchors.py --result result.json \
      --index anchor_index.json --report anchor_report.json
"""
import argparse
import json
import re
import sys

# 形如 "§2"、"§2 ¶1"、"§3 Table 1; §5 Table 3" 的锚点，逐个 § 段校验并配对紧随的 ¶
ANCHOR_RE = re.compile(r"§\s*(\d+)(?:\s*¶\s*(\d+))?")
ANCHOR_KEYS = ("source_anchor", "anchor")
SKIP_KEYS = ANCHOR_KEYS + ("quote",)
CORE_PREFIXES = ("$.paper_card_anchors", "$.sections", "$.knowledge_points")


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def is_nonempty(value):
    """null、空白字符串、空数组/对象为空；0 与 false 仍是有内容的字段值。"""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def collect_entries(obj, path="$"):
    """递归收集所有带非空锚点字段的条目 -> [(path, anchor, quote)]。"""
    entries = []
    if isinstance(obj, dict):
        anchor = None
        for k in ANCHOR_KEYS:
            if isinstance(obj.get(k), str) and obj[k].strip():
                anchor = obj[k]
                break
        if anchor is not None:
            quote = obj.get("quote")
            entries.append((path, anchor, quote if isinstance(quote, str) else None))
        for k, v in obj.items():
            if k in SKIP_KEYS:
                continue
            entries.extend(collect_entries(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            entries.extend(collect_entries(v, f"{path}[{i}]"))
    return entries


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def error(errors, path, reason, anchor=None):
    item = {"path": path, "reason": reason}
    if anchor is not None:
        item["anchor"] = anchor
    errors.append(item)


def check_required_coverage(result, errors, warnings):
    """检查 paper_card/sections/knowledge_points 的正式锚点字段覆盖。"""
    status = result.get("status")
    partial = status == "partial"

    def missing_anchor(path, obj, description):
        uncertain = isinstance(obj, dict) and obj.get("status") == "uncertain"
        if partial and uncertain:
            warnings.append({
                "path": path,
                "reason": f"partial 中 {description} 明确为 status=uncertain，暂缺锚点；"
                          "缺口必须已在 status_reason/uncertainties 交代",
            })
        else:
            reason = f"{description} 缺少非空 source_anchor"
            if uncertain and not partial:
                reason += "；只有 partial 下的 status=uncertain 条目才可缺锚点"
            error(errors, path, reason)

    card = result.get("paper_card")
    descriptors = result.get("paper_card_anchors")
    if not isinstance(card, dict):
        error(errors, "$.paper_card", "paper_card 必须是对象")
        card = {}
    if not isinstance(descriptors, list):
        error(errors, "$.paper_card_anchors", "paper_card_anchors 必须是数组（无锚点时为空数组）")
        descriptors = []

    by_field = {}
    for i, descriptor in enumerate(descriptors):
        path = f"$.paper_card_anchors[{i}]"
        if not isinstance(descriptor, dict):
            error(errors, path, "paper_card_anchors 项必须是对象")
            continue
        field = descriptor.get("field")
        if not isinstance(field, str) or not field.strip():
            error(errors, path, "paper_card_anchors 项缺少非空 field")
            continue
        by_field.setdefault(field, []).append((path, descriptor))
        if not (isinstance(descriptor.get("source_anchor"), str)
                and descriptor["source_anchor"].strip()):
            missing_anchor(path, descriptor, f"paper_card 字段 {field!r} 的锚点项")

    for field, value in card.items():
        if not is_nonempty(value):
            continue
        field_descriptors = by_field.get(field, [])
        has_formal_anchor = any(
            isinstance(descriptor.get("source_anchor"), str)
            and descriptor["source_anchor"].strip()
            for _, descriptor in field_descriptors
        )
        if not has_formal_anchor and not any(
            partial and descriptor.get("status") == "uncertain"
            for _, descriptor in field_descriptors
        ):
            error(
                errors, f"$.paper_card.{field}",
                f"非空 paper_card 字段 {field!r} 未在 paper_card_anchors 中覆盖",
            )

    sections = result.get("sections")
    if not isinstance(sections, list):
        error(errors, "$.sections", "sections 必须是数组")
        sections = []
    for i, section in enumerate(sections):
        path = f"$.sections[{i}]"
        if not isinstance(section, dict):
            error(errors, path, "section 必须是对象")
            continue
        if not (isinstance(section.get("source_anchor"), str)
                and section["source_anchor"].strip()):
            missing_anchor(path, section, f"section {section.get('id', i)!r}")

    knowledge_points = result.get("knowledge_points")
    if not isinstance(knowledge_points, list):
        error(errors, "$.knowledge_points", "knowledge_points 必须是数组")
        knowledge_points = []
    for i, point in enumerate(knowledge_points):
        path = f"$.knowledge_points[{i}]"
        if not isinstance(point, dict):
            error(errors, path, "knowledge_point 必须是对象")
            continue
        if not (isinstance(point.get("source_anchor"), str)
                and point["source_anchor"].strip()):
            missing_anchor(path, point, f"knowledge_point {point.get('id', i)!r}")

    if status == "partial":
        if not (isinstance(result.get("status_reason"), str)
                and result["status_reason"].strip()):
            error(errors, "$.status_reason", "partial 必须用 status_reason 交代范围、缺口及原因")
        if not is_nonempty(result.get("uncertainties")):
            error(errors, "$.uncertainties", "partial 必须用非空 uncertainties 交代未决项/缺锚点")


def check_section_alignment(result, index_sections, errors, warnings):
    """双向核对完整章节集，返回报告中使用的四个 ID 列表。"""
    status = result.get("status")
    enforce_complete_set = status in ("success", "partial")
    result_sections = result.get("sections")
    if not isinstance(result_sections, list):
        result_sections = []

    result_ids = []
    seen = set()
    for i, section in enumerate(result_sections):
        path = f"$.sections[{i}]"
        if not isinstance(section, dict):
            continue  # 类型错误已由 check_required_coverage 报告
        sid = section.get("id")
        if not isinstance(sid, str) or not sid.strip():
            error(errors, path, "section 缺少非空字符串 id（须为索引中的 §n）")
            continue
        sid = sid.strip()
        result_ids.append(sid)
        if sid in seen:
            error(errors, path, f"section id {sid!r} 重复；每个索引章节只能对应一个结果项")
        else:
            seen.add(sid)
        if sid not in index_sections:
            error(errors, path, f"额外章节 {sid} 不存在于索引的完整 §ID 集合")

        uncertain = section.get("status") == "uncertain"
        has_anchor = (
            isinstance(section.get("source_anchor"), str)
            and section["source_anchor"].strip()
        )
        if uncertain:
            reason = section.get("reason")
            if status == "success":
                error(errors, path, f"success 不接受索引章节 {sid} 的 uncertain 占位")
            if status == "partial":
                if not (isinstance(reason, str) and reason.strip()):
                    error(errors, path, f"partial 的章节占位 {sid} 必须含非空 reason")
                if has_anchor:
                    warnings.append({
                        "path": path,
                        "reason": f"partial 中索引章节 {sid} 明确为 status=uncertain；请人工复核占位原因",
                    })
        else:
            own_anchor = False
            if has_anchor:
                own_anchor = any(
                    f"§{match.group(1)}" == sid
                    for match in ANCHOR_RE.finditer(section["source_anchor"])
                )
            if not own_anchor:
                error(
                    errors, path,
                    f"正常 section {sid} 的 source_anchor 必须包含自己的 §ID {sid}",
                    section.get("source_anchor") if has_anchor else None,
                )

    missing = [sid for sid in index_sections if sid not in seen]
    if enforce_complete_set:
        for sid in missing:
            requirement = (
                "success 必须覆盖索引中的每个章节（preamble 也按普通 § 处理）"
                if status == "success"
                else "partial 不得静默漏节；必须保留 {id, status:'uncertain', reason:'...'} 占位"
            )
            error(errors, "$.sections", f"缺少索引章节 {sid}；{requirement}")

    extras = []
    for sid in result_ids:
        if sid not in index_sections and sid not in extras:
            extras.append(sid)
    return {
        "index_sections": list(index_sections),
        "result_sections": result_ids,
        "missing_sections": missing,
        "extra_sections": extras,
    }


def main():
    ap = argparse.ArgumentParser(description="校验 result.json 锚点、quote 与必填覆盖")
    ap.add_argument("--result", required=True, help="result.json 路径")
    ap.add_argument("--index", required=True, help="build_anchor_index.py 生成的 anchor_index.json")
    ap.add_argument("--report", required=True, help="输出校验报告 JSON 路径")
    args = ap.parse_args()

    try:
        result = load_json(args.result)
        index = load_json(args.index)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[validate_anchors] 无法读取输入: {e}", file=sys.stderr)
        return 2
    if not isinstance(result, dict) or not isinstance(index, dict):
        print("[validate_anchors] result 与 index 顶层都必须是 JSON 对象", file=sys.stderr)
        return 2

    sections = {
        s["id"]: s for s in index.get("sections", [])
        if isinstance(s, dict) and isinstance(s.get("id"), str)
    }
    errors = []
    warnings = []
    checked = 0
    valid_checked = 0
    valid_core_checked = 0

    check_required_coverage(result, errors, warnings)
    section_alignment = check_section_alignment(result, sections, errors, warnings)

    for path, anchor, quote in collect_entries(result):
        checked += 1
        matches = list(ANCHOR_RE.finditer(anchor))
        if not matches:
            error(errors, path, "锚点不含可解析的 § 章节 ID（形态须为 §x 或 §x ¶y）", anchor)
            continue
        target_texts = []
        anchor_ok = True
        for m in matches:
            sec_id = f"§{m.group(1)}"
            sec = sections.get(sec_id)
            if sec is None:
                error(errors, path, f"章节 {sec_id} 不存在于索引", anchor)
                anchor_ok = False
                continue
            paragraphs = sec.get("paragraphs", [])
            if m.group(2):
                par_id = f"¶{m.group(2)}"
                par = next(
                    (p for p in paragraphs if isinstance(p, dict) and p.get("id") == par_id),
                    None,
                )
                if par is None:
                    error(errors, path,
                          f"段落 {sec_id} {par_id} 不存在于索引（该节共 {len(paragraphs)} 段）",
                          anchor)
                    anchor_ok = False
                    continue
                target_texts.append(par.get("text", ""))
            else:
                target_texts.extend(
                    p.get("text", "") for p in paragraphs if isinstance(p, dict)
                )
        if anchor_ok and quote and quote.strip():
            if norm(quote) not in norm("\n".join(target_texts)):
                error(errors, path, f"quote 不是被引范围原文的子串: {quote[:60]!r}", anchor)
                anchor_ok = False
        if anchor_ok:
            valid_checked += 1
            if path.startswith(CORE_PREFIXES):
                valid_core_checked += 1

    card = result.get("paper_card") if isinstance(result.get("paper_card"), dict) else {}
    has_content = (
        any(is_nonempty(value) for value in card.values())
        or bool(result.get("sections"))
        or bool(result.get("knowledge_points"))
        or bool(result.get("paper_card_anchors"))
    )
    unable_without_content = result.get("status") == "unable" and not has_content
    if checked == 0 and not unable_without_content:
        error(errors, "$", "checked=0：没有任何锚点，空锚点全集不得通过")
    if result.get("status") == "partial" and valid_core_checked == 0:
        error(
            errors, "$",
            "partial 至少要有 paper_card/section/knowledge_point 的一个真实有效锚点；"
            "不能全部以 uncertain 缺锚点",
        )
    if unable_without_content:
        if not (isinstance(result.get("status_reason"), str)
                and result["status_reason"].strip()):
            error(errors, "$.status_reason", "unable 无内容例外仍必须用 status_reason 说明无法处理原因")
        warnings.append({"path": "$", "reason": "unable 且无内容，允许 checked=0"})

    report = {
        "result": args.result,
        "index": args.index,
        "checked": checked,
        "valid_checked": valid_checked,
        "valid_core_checked": valid_core_checked,
        **section_alignment,
        "ok": not errors,
        "warnings": warnings,
        "errors": errors,
    }
    try:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as e:
        print(f"[validate_anchors] 无法写入报告: {e}", file=sys.stderr)
        return 2

    for warning in warnings:
        print(f"  WARNING {warning['path']}: {warning['reason']}")
    if errors:
        print(
            f"[validate_anchors] 校验失败：检查 {checked} 条锚点"
            f"（有效 {valid_checked} 条），共 {len(errors)} 条错误"
        )
        for e in errors:
            anchor_text = f" anchor={e['anchor']!r}" if "anchor" in e else ""
            print(f"  ERROR {e['path']}{anchor_text}: {e['reason']}")
        print(f"[validate_anchors] 报告已写入 {args.report}")
        return 1
    print(
        f"[validate_anchors] 全部通过：{checked} 条锚点均存在于索引，quote 核对一致，"
        "paper_card/sections/knowledge_points 必填覆盖完整"
        + ("；unable 无内容例外" if unable_without_content else "")
    )
    print(f"[validate_anchors] 报告已写入 {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
