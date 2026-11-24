#!/usr/bin/env python3
"""文献翻译交付的结构、源文区间和 work/final 一致性门禁（纯标准库）。

用法：
  python3 scripts/validate_translation_delivery.py \
    --case case.json --source-text source-snapshot.txt --result result.json \
    [--work-segments segments.json] --report delivery-report.json

最小契约：result.segments 每项含 id/source/target/source_start/source_end。
source_start/source_end 是所保存 UTF-8 源文快照的 Python 字符下标（不是字节
下标），且 snapshot[source_start:source_end] 必须与 source 完全相同。所有段落按
区间递增、不得重叠，target 去首尾空白后不得为空。

success 必须从 0 到 len(snapshot) 连续全覆盖；partial/unable 必须给出非空
status_reason，并用 uncovered_ranges 精确声明全部未覆盖区间。区间对象的规范
形式为 {"source_start": 0, "source_end": 10}；为便于读取旧工作文件，也接受
[start, end] 二元数组，报告统一输出对象形式。

output_contract 的每个声明字段都必须存在。字符串类型名、{"type": ...} 描述
以及非 null 示例值可推断 JSON 基本类型；无法推断时写 warning，不伪造类型通过。
success 有任何未解决 warning 也失败，partial/unable 可以带 warning 通过结构门禁，
但必须由交付方把相应核验缺口列入 status_reason/uncertainties。

退出码：所有硬检查通过且无 success warning 为 0；任何错误为 1。
"""
import argparse
import json
import os
import sys

SEGMENT_FIELDS = ("id", "source", "target", "source_start", "source_end")
COMPARE_FIELDS = SEGMENT_FIELDS
DEFAULT_OPTIONAL_TYPES = {
    "source_lang": {"string"},
    "target_lang": {"string"},
    "terminology": {"array"},
    "uncertainties": {"array"},
    "tool_commands": {"array"},
}
_TYPE_ALIASES = {
    "string": "string", "str": "string", "text": "string",
    "array": "array", "list": "array",
    "object": "object", "dict": "object", "map": "object",
    "boolean": "boolean", "bool": "boolean",
    "integer": "integer", "int": "integer",
    "number": "number", "float": "number", "double": "number",
    "null": "null", "none": "null",
}


def add_issue(bucket, issue_type, message, **extra):
    item = {"type": issue_type, "message": message}
    item.update(extra)
    bucket.append(item)


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def json_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def matches_type(value, expected):
    actual = json_type(value)
    if actual in expected:
        return True
    return actual == "integer" and "number" in expected


def infer_types(spec):
    """返回可推断的 JSON 类型集合；无法可靠推断时返回 None。"""
    if isinstance(spec, str):
        name = spec.strip().lower()
        # "string" 等是类型声明；其他字符串（如 "zh"）作为示例值，也足以推断 string。
        return {_TYPE_ALIASES.get(name, "string")}
    if spec is None:
        return None
    if isinstance(spec, (bool, int, float)):
        return {json_type(spec)}
    if isinstance(spec, list):
        names = [_TYPE_ALIASES.get(x.strip().lower()) for x in spec
                 if isinstance(x, str)]
        if spec and len(names) == len(spec) and all(names):
            return set(names)
        return {"array"}
    if isinstance(spec, dict):
        if "type" in spec:
            declared = spec["type"]
            if isinstance(declared, str):
                name = _TYPE_ALIASES.get(declared.strip().lower())
                return {name} if name else None
            if isinstance(declared, list):
                names = [_TYPE_ALIASES.get(x.strip().lower()) for x in declared
                         if isinstance(x, str)]
                if declared and len(names) == len(declared) and all(names):
                    return set(names)
            return None
        for key in ("example", "default", "value"):
            if key in spec:
                return infer_types(spec[key])
        if "properties" in spec:
            return {"object"}
        descriptor_keys = {"description", "required", "title", "$schema"}
        if descriptor_keys.intersection(spec):
            return None
        return {"object"}
    return None


def contract_declarations(contract, errors, label="case.output_contract"):
    """归一化为 [{field, spec}]；对象映射和 name/field 对象数组均可读。"""
    declarations = []
    if isinstance(contract, dict):
        for field, spec in contract.items():
            declarations.append({"field": field, "spec": spec})
    elif isinstance(contract, list):
        for index, item in enumerate(contract):
            if isinstance(item, str) and item:
                declarations.append({"field": item, "spec": None})
            elif isinstance(item, dict) and isinstance(item.get("name", item.get("field")), str):
                field = item.get("name", item.get("field"))
                declarations.append({"field": field, "spec": item})
            else:
                add_issue(errors, "invalid_contract_declaration",
                          f"{label}[{index}] 必须是字段名或含 name/field 的对象")
    else:
        add_issue(errors, "invalid_output_contract",
                  f"{label} 必须是字段声明对象或数组")
    return declarations


def optional_case_declarations(case, errors):
    """可选扩展声明 never overrides output_contract；只核 result 中实际出现的字段。"""
    declarations = []
    for key in ("optional_fields", "optional_output_fields"):
        if key in case:
            declarations.extend(contract_declarations(case[key], errors, "case." + key))
    return declarations


def check_field_declarations(result, declarations, required, errors, warnings,
                             contract_checks, skip_fields=frozenset()):
    for declaration in declarations:
        field = declaration["field"]
        if not field or field in skip_fields:
            continue
        present = field in result
        if required and not present:
            add_issue(errors, "missing_contract_field",
                      f"result 缺少声明字段 '{field}'", field=field)
            contract_checks.append({"field": field, "status": "error",
                                    "reason": "missing"})
            continue
        if not present:
            continue
        expected = infer_types(declaration["spec"])
        if expected is None:
            message = (f"字段 '{field}' 的声明无法推断基本类型；已核存在性，"
                       "类型必须人工核验，不能记为机检通过")
            add_issue(warnings, "unknown_contract_type", message, field=field)
            contract_checks.append({"field": field, "status": "warning",
                                    "reason": "unknown_type"})
            continue
        value = result[field]
        if not matches_type(value, expected):
            add_issue(errors, "contract_type_mismatch",
                      f"字段 '{field}' 应为 {sorted(expected)}，实际为 {json_type(value)}",
                      field=field, expected=sorted(expected), actual=json_type(value))
            contract_checks.append({"field": field, "status": "error",
                                    "expected": sorted(expected), "actual": json_type(value)})
        else:
            contract_checks.append({"field": field, "status": "ok",
                                    "expected": sorted(expected), "actual": json_type(value)})


def validate_segments(segments, source, label, errors):
    """核最小分段结构；返回所有区间本身合法的分段，供覆盖计算使用。"""
    valid = []
    if not isinstance(segments, list):
        add_issue(errors, "invalid_segments", f"{label} 必须是数组")
        return valid
    seen_ids = set()
    previous = None
    for index, segment in enumerate(segments):
        location = f"{label}[{index}]"
        if not isinstance(segment, dict):
            add_issue(errors, "invalid_segment", f"{location} 必须是对象", segment_index=index)
            continue
        for field in SEGMENT_FIELDS:
            if field not in segment:
                add_issue(errors, "missing_segment_field", f"{location} 缺少 '{field}'",
                          segment_index=index, field=field)
        seg_id = segment.get("id")
        if not isinstance(seg_id, str) or not seg_id.strip():
            add_issue(errors, "invalid_segment_id", f"{location}.id 必须是非空字符串",
                      segment_index=index)
        elif seg_id in seen_ids:
            add_issue(errors, "duplicate_segment_id", f"段 ID 重复：'{seg_id}'",
                      segment_index=index, segment_id=seg_id)
        else:
            seen_ids.add(seg_id)
        src = segment.get("source")
        if not isinstance(src, str):
            add_issue(errors, "invalid_segment_source", f"{location}.source 必须是字符串",
                      segment_index=index)
        target = segment.get("target")
        if not isinstance(target, str) or not target.strip():
            add_issue(errors, "empty_target", f"{location}.target 必须是非空字符串",
                      segment_index=index)
        start, end = segment.get("source_start"), segment.get("source_end")
        span_valid = True
        if not is_int(start) or not is_int(end):
            add_issue(errors, "invalid_span_type",
                      f"{location}.source_start/source_end 必须是整数（不能是布尔值）",
                      segment_index=index)
            span_valid = False
        elif not (0 <= start < end <= len(source)):
            add_issue(errors, "invalid_span",
                      f"{location} 区间 [{start}, {end}) 不满足 0 <= start < end <= {len(source)}",
                      segment_index=index, source_start=start, source_end=end)
            span_valid = False
        if span_valid:
            if isinstance(src, str) and source[start:end] != src:
                add_issue(errors, "source_snapshot_mismatch",
                          f"{location}.source 与快照 [{start}, {end}) 的逐字切片不一致",
                          segment_index=index, segment_id=seg_id)
            if previous is not None:
                prev_index, prev_start, prev_end = previous
                if start < prev_end:
                    add_issue(errors, "overlapping_spans",
                              f"{location} 区间 [{start}, {end}) 与 {label}[{prev_index}] "
                              f"区间 [{prev_start}, {prev_end}) 重叠或未递增",
                              segment_index=index, previous_segment_index=prev_index)
                elif start < prev_start:
                    add_issue(errors, "non_increasing_spans",
                              f"{location} 区间未按 source_start 递增", segment_index=index)
            previous = (index, start, end)
            valid.append({"index": index, "source_start": start, "source_end": end})
        for optional, kind in (("basis", "string"), ("status", "string")):
            if optional in segment and json_type(segment[optional]) != kind:
                add_issue(errors, "invalid_segment_optional_type",
                          f"{location}.{optional} 若提供则必须是{kind}", segment_index=index)
    return valid


def uncovered_from_valid(valid, source_length):
    ranges = []
    cursor = 0
    # 排序只用于报告真实集合；原数组的顺序/重叠问题已由 validate_segments 报错。
    for item in sorted(valid, key=lambda x: (x["source_start"], x["source_end"])):
        start, end = item["source_start"], item["source_end"]
        if end <= cursor:
            continue
        if start > cursor:
            ranges.append({"source_start": cursor, "source_end": start})
        cursor = max(cursor, end)
    if cursor < source_length:
        ranges.append({"source_start": cursor, "source_end": source_length})
    return ranges


def covered_ranges(valid):
    merged = []
    for item in sorted(valid, key=lambda x: (x["source_start"], x["source_end"])):
        start, end = item["source_start"], item["source_end"]
        if merged and start <= merged[-1]["source_end"]:
            merged[-1]["source_end"] = max(end, merged[-1]["source_end"])
        else:
            merged.append({"source_start": start, "source_end": end})
    return merged


def read_uncovered(value, source_length, errors):
    if not isinstance(value, list):
        add_issue(errors, "invalid_uncovered_ranges", "uncovered_ranges 必须是区间数组")
        return None
    canonical = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            start, end = item.get("source_start"), item.get("source_end")
        elif isinstance(item, list) and len(item) == 2:
            start, end = item
        else:
            add_issue(errors, "invalid_uncovered_range",
                      f"uncovered_ranges[{index}] 必须是区间对象或 [start, end]")
            continue
        if not is_int(start) or not is_int(end) or not (0 <= start < end <= source_length):
            add_issue(errors, "invalid_uncovered_range",
                      f"uncovered_ranges[{index}] 不是合法非空字符区间")
            continue
        canonical.append({"source_start": start, "source_end": end})
    return canonical


def compare_work_final(work, final, errors):
    if not isinstance(work, list) or not isinstance(final, list):
        return
    if len(work) != len(final):
        add_issue(errors, "work_final_count_mismatch",
                  f"work/final 段数漂移：work={len(work)} final={len(final)}")
    for index, (work_segment, final_segment) in enumerate(zip(work, final)):
        if not isinstance(work_segment, dict) or not isinstance(final_segment, dict):
            continue
        for field in COMPARE_FIELDS:
            if field not in work_segment or field not in final_segment:
                continue
            if work_segment[field] != final_segment[field]:
                add_issue(errors, "work_final_mismatch",
                          f"第 {index} 项字段 '{field}' 在 work/final 间漂移",
                          segment_index=index, field=field,
                          work=work_segment[field], final=final_segment[field])


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def run(args):
    errors, warnings, contract_checks = [], [], []
    case = result = None
    source = ""
    work = None
    try:
        case = load_json(args.case)
        if not isinstance(case, dict):
            raise ValueError("case.json 顶层必须是对象")
        result = load_json(args.result)
        if not isinstance(result, dict):
            raise ValueError("result.json 顶层必须是对象")
        # newline="" 禁止通用换行转换，确保保存快照与下标严格对应。
        with open(args.source_text, encoding="utf-8", newline="") as handle:
            source = handle.read()
        if args.work_segments:
            work = load_json(args.work_segments)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        add_issue(errors, "input_error", f"输入读取或解析失败：{exc}")

    final_segments = []
    final_valid = []
    if not errors:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            add_issue(errors, "invalid_case_id", "case.case_id 必须是非空字符串")
        if result.get("case_id") != case_id:
            add_issue(errors, "case_id_mismatch", "result.case_id 必须与 case.case_id 原样一致",
                      expected=case_id, actual=result.get("case_id"))
        if not isinstance(result.get("case_id"), str) or not result.get("case_id", "").strip():
            add_issue(errors, "invalid_result_case_id", "result.case_id 必须是非空字符串")

        status = result.get("status")
        if status not in ("success", "partial", "unable"):
            add_issue(errors, "invalid_status", "result.status 必须是 success/partial/unable")
        reason = result.get("status_reason")
        if not isinstance(reason, str):
            add_issue(errors, "invalid_status_reason", "result.status_reason 必须是字符串")
        elif status in ("partial", "unable") and not reason.strip():
            add_issue(errors, "missing_status_reason", f"{status} 必须给出非空 status_reason")

        if "output_contract" not in case:
            add_issue(errors, "missing_output_contract", "case.json 缺少 output_contract")
            declarations = []
        else:
            declarations = contract_declarations(case["output_contract"], errors)
        declared_names = {item["field"] for item in declarations}
        check_field_declarations(result, declarations, True, errors, warnings, contract_checks)

        # output_contract 同名异型时优先；可选扩展和 Skill 默认字段只作补充。
        extras = optional_case_declarations(case, errors)
        check_field_declarations(result, extras, False, errors, warnings, contract_checks,
                                 skip_fields=declared_names)
        extra_names = {item["field"] for item in extras}
        for field, expected in DEFAULT_OPTIONAL_TYPES.items():
            if field in declared_names or field in extra_names or field not in result:
                continue
            value = result[field]
            if not matches_type(value, expected):
                add_issue(errors, "default_field_type_mismatch",
                          f"可选默认字段 '{field}' 若提供则必须是 {sorted(expected)}",
                          field=field, actual=json_type(value))
            contract_checks.append({"field": field, "status": "ok" if matches_type(value, expected)
                                    else "error", "source": "skill_default"})

        segments_value = result.get("segments")
        final_valid = validate_segments(segments_value, source, "result.segments", errors)
        if isinstance(segments_value, list):
            final_segments = segments_value
        uncovered = uncovered_from_valid(final_valid, len(source))
        if status == "success":
            if uncovered:
                add_issue(errors, "incomplete_success_coverage",
                          "success 必须从 0 到 len(source) 连续全覆盖",
                          uncovered_ranges=uncovered)
            if "uncovered_ranges" in result:
                declared = read_uncovered(result["uncovered_ranges"], len(source), errors)
                if declared is not None and declared != uncovered:
                    add_issue(errors, "uncovered_ranges_mismatch",
                              "success 的 uncovered_ranges 若提供则必须精确等于计算值（通常为空）",
                              expected=uncovered, actual=declared)
        elif status in ("partial", "unable"):
            if "uncovered_ranges" not in result:
                add_issue(errors, "missing_uncovered_ranges",
                          f"{status} 必须显式提供 uncovered_ranges，不能静默漏段")
            else:
                declared = read_uncovered(result["uncovered_ranges"], len(source), errors)
                if declared is not None and declared != uncovered:
                    add_issue(errors, "uncovered_ranges_mismatch",
                              "声明的 uncovered_ranges 必须按递增顺序精确等于全部未覆盖区间",
                              expected=uncovered, actual=declared)

        if args.work_segments:
            validate_segments(work, source, "work_segments", errors)
            compare_work_final(work, final_segments, errors)

        if status == "success" and warnings:
            add_issue(errors, "success_has_unresolved_warnings",
                      "success 要求所有机检全绿；存在类型无法推断等 warning，"
                      "应改为 partial 并声明人工核验缺口，或补全声明后重跑")

    report = {
        "ok": not errors,
        "case_id": case.get("case_id") if isinstance(case, dict) else None,
        "status": result.get("status") if isinstance(result, dict) else None,
        "source_length": len(source),
        "checked_segments": len(final_segments),
        "checked_work_segments": len(work) if isinstance(work, list) else 0,
        "covered_ranges": covered_ranges(final_valid),
        "uncovered_ranges": uncovered_from_valid(final_valid, len(source)),
        "contract_checks": contract_checks,
        "errors": errors,
        "warnings": warnings,
        "scope": "结构/快照/区间/output_contract/work-final；不替代术语、守恒或语义人工核验",
    }
    if args.report:
        parent = os.path.dirname(os.path.abspath(args.report))
        os.makedirs(parent, exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(f"报告已写入 {args.report}：errors={len(errors)} warnings={len(warnings)}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description="翻译交付结构、区间、契约与 work/final 漂移核验")
    parser.add_argument("--case", required=True, help="case.json")
    parser.add_argument("--source-text", required=True, help="保存后不再改动的规范化源文快照.txt")
    parser.add_argument("--result", required=True, help="最终 result.json")
    parser.add_argument("--work-segments", default=None, help="可选：送术语/守恒机检的 segments.json")
    parser.add_argument("--report", required=True, help="核验报告 JSON 路径")
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
