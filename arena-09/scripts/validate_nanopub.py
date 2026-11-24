#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nanopublication records-only 与 record↔JSON-LD 严格等性质检。

用法：
    python scripts/validate_nanopub.py --records-only /app/output/result.json
    python scripts/export_nanopub.py /app/output/result.json \
        --out-dir /app/output/nanopubs --update-result
    python scripts/validate_nanopub.py /app/output/result.json [extra.jsonld ...]

最终质检将每一个实际文档与 export_nanopub.build_document(result, rec) 的
canonical 构造结果做 JSON 树严格全等比较。对象键顺序不影响等价；数组顺序、
字段缺多、值变化均影响等价。实际文档必须采用 canonical 四 graph 列表外壳，
不接受其他 JSON-LD 同义外壳。内嵌 jsonld/json_ld、jsonld_files 和 CLI 附件
都是独立来源，合并计数，不能用附件替代或绕过记录映射。
"""

import argparse
import json
import os
import sys

from export_nanopub import (
    CONTEXT,
    GRAPH_NAMES,
    NANOPUB_URN_RE,
    CanonicalizationError,
    build_document,
    load_json,
)

# 与 references/relation-vocabulary.md 一致的完整受控词表：
# 核心 14 项（is_a / instance_of 视为同组两项）+ 扩展 8 项。
CORE_PREDICATES = {
    "causes", "increases", "decreases",
    "is_associated_with", "correlates_with",
    "improves", "reduces",
    "consists_of",
    "is_a", "instance_of",
    "has_property", "measured_as",
    "located_in", "binds_to", "expressed_in",
}
EXTENDED_PREDICATES = {
    "extracted_from", "holds_under", "proposes", "conflicts_with",
    "applies_to", "defined_as", "supported_by", "uncertain_because",
}
ALLOWED_PREDICATES = CORE_PREDICATES | EXTENDED_PREDICATES
REQUIRED_GRAPHS = GRAPH_NAMES


def normalize_predicate(pred):
    """去掉 np: 等命名空间前缀后比对。"""
    if not isinstance(pred, str):
        return ""
    return pred.rsplit(":", 1)[-1].strip()


def evidence_is_empty(evidence):
    if evidence is None:
        return True
    if isinstance(evidence, dict):
        text = evidence.get("evidence_text") or evidence.get("np:evidence_text")
        return not (isinstance(text, str) and text.strip())
    if isinstance(evidence, str):
        return not evidence.strip()
    return False


def check_predicates_and_fields(result, errors, warnings):
    """保留原有词表/字段/空证据检查，并增加稳定的一一对应主键。"""
    nps = result.get("nanopublications")
    if not isinstance(nps, list) or not nps:
        errors.append("result.json 缺少非空的 nanopublications 数组")
        return
    seen_ids = {}
    for i, rec in enumerate(nps, 1):
        rid = rec.get("id", f"#{i}") if isinstance(rec, dict) else f"#{i}"
        if not isinstance(rec, dict):
            errors.append(f"{rid}: 记录不是对象")
            continue
        expected_id = f"np-{i:03d}"
        if isinstance(rid, str) and rid in seen_ids:
            errors.append(
                f"{rid}: record.id 重复（第 {seen_ids[rid]} 条与第 {i} 条）"
            )
        if not isinstance(rid, str):
            errors.append(f"第 {i} 条 record.id 必须是 np-001 形式的字符串，实际为 {rid!r}")
        elif rid not in seen_ids:
            seen_ids[rid] = i
        if rid != expected_id:
            errors.append(
                f"第 {i} 条 record.id 应为 {expected_id!r}（从 np-001 连续编号），实际为 {rid!r}"
            )
        for key in ("assertion", "evidence", "provenance", "status", "basis"):
            if key not in rec:
                errors.append(f"{rid}: 缺少字段 {key}")
        assertion = rec.get("assertion")
        if not isinstance(assertion, dict):
            errors.append(f"{rid}: assertion 必须是含 subject/predicate/object 的对象")
        else:
            pred = normalize_predicate(
                assertion.get("predicate") or assertion.get("np:predicate")
            )
            if pred not in ALLOWED_PREDICATES:
                errors.append(
                    f"{rid}: predicate '{assertion.get('predicate')}' 不在受控词表内"
                )
        if "provenance" in rec and not isinstance(rec.get("provenance"), dict):
            errors.append(f"{rid}: provenance 必须是对象")
        if "evidence" in rec and rec.get("evidence") is not None and not isinstance(
            rec.get("evidence"), (dict, str)
        ):
            errors.append(f"{rid}: evidence 必须是对象、字符串或 null")
        if "evidence" in rec and evidence_is_empty(rec.get("evidence")):
            if rec.get("status") == "unverified":
                warnings.append(
                    f"{rid}: status=unverified，允许 evidence 为空；"
                    "该断言尚未得到原文证据验证，须在 basis/uncertainties 说明缺口"
                )
            else:
                errors.append(
                    f"{rid}: evidence 为空；仅明确 status=unverified 的记录可带空证据"
                )


def collect_jsonld_docs(result, result_dir, extra_files, errors):
    """合并所有来源；不把一个来源当作另一个来源的替代。"""
    docs = []
    for path in extra_files:
        try:
            docs.append((path, load_json(path)))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"JSON-LD 文件 {path} 无法解析: {exc}")
    for field in ("jsonld", "json_ld"):
        if field not in result or result[field] is None:
            continue
        embedded = result[field]
        source = f"result.json#{field}"
        if isinstance(embedded, str):
            try:
                docs.append((source, json.loads(embedded)))
            except json.JSONDecodeError as exc:
                errors.append(f"{source} 内嵌字符串无法解析: {exc}")
        elif isinstance(embedded, (dict, list)):
            docs.append((source, embedded))
        else:
            errors.append(f"{source} 必须是 JSON-LD 对象、数组或 JSON 字符串")
    refs = result.get("jsonld_files", [])
    if not isinstance(refs, list):
        errors.append("result.json 的 jsonld_files 必须是文件路径数组")
        refs = []
    for rel in refs:
        if not isinstance(rel, str) or not rel.strip():
            errors.append("jsonld_files 含有空路径或非字符串路径")
            continue
        path = rel if os.path.isabs(rel) else os.path.join(result_dir, rel)
        try:
            docs.append((path, load_json(path)))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"JSON-LD 文件 {path} 无法解析: {exc}")
    return docs


def local_name(value):
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if "#" in value:
        value = value.rsplit("#", 1)[-1]
    elif ":" in value:
        value = value.rsplit(":", 1)[-1]
    else:
        value = value.rsplit("/", 1)[-1]
    return value.strip().lower()


def check_named_graphs(name, doc, errors):
    """最终格式只接受 canonical @graph 四对象列表及规范 URN 后缀。"""
    doc_id = doc.get("@id")
    if not isinstance(doc_id, str) or not NANOPUB_URN_RE.fullmatch(doc_id):
        errors.append(
            f"JSON-LD 输出 {name} 的顶层 @id 不符合 urn:nanopub:<case_id>:<n>；"
            f"实际为 {doc_id!r}"
        )
    graph = doc.get("@graph")
    if not isinstance(graph, list):
        errors.append(f"JSON-LD 输出 {name} 的 @graph 必须是 canonical 四对象列表")
        return
    if len(graph) != len(REQUIRED_GRAPHS):
        errors.append(
            f"JSON-LD 输出 {name} 的 @graph 必须恰含四项，实际为 {len(graph)} 项"
        )
    for index, graph_name in enumerate(REQUIRED_GRAPHS):
        if index >= len(graph):
            continue
        item = graph[index]
        if not isinstance(item, dict):
            errors.append(f"JSON-LD 输出 {name} 的第 {index + 1} 个 graph 不是对象")
            continue
        graph_id = item.get("@id")
        if local_name(graph_id) != graph_name:
            errors.append(
                f"JSON-LD 输出 {name} 的第 {index + 1} 个 graph 应为 {graph_name}，"
                f"实际 @id 为 {graph_id!r}"
            )
        if isinstance(doc_id, str):
            expected = f"{doc_id}#{graph_name}"
            if graph_id != expected:
                errors.append(
                    f"JSON-LD 输出 {name} 的 {graph_name} graph @id 应为 {expected!r}，"
                    f"实际为 {graph_id!r}"
                )


def canonical_differences(actual, expected, path="$", limit=12):
    """给出机器可读 JSON 树差异；对象键序不当作差异，数组顺序当作差异。"""
    differences = []

    def visit(left, right, location):
        if len(differences) >= limit:
            return
        if type(left) is not type(right):
            differences.append(f"{location}: 类型/值不同，实际 {left!r}，期望 {right!r}")
            return
        if isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                if key not in left:
                    differences.append(f"{location}.{key}: 缺失，期望 {right[key]!r}")
                elif key not in right:
                    differences.append(f"{location}.{key}: 多余，实际 {left[key]!r}")
                else:
                    visit(left[key], right[key], f"{location}.{key}")
        elif isinstance(right, list):
            if len(left) != len(right):
                differences.append(
                    f"{location}: 数组长度不同，实际 {len(left)}，期望 {len(right)}"
                )
            for index, (left_item, right_item) in enumerate(zip(left, right)):
                visit(left_item, right_item, f"{location}[{index}]")
        elif left != right:
            differences.append(f"{location}: 实际 {left!r}，期望 {right!r}")

    visit(actual, expected, path)
    return differences


def check_jsonld(result, result_dir, extra_files, errors):
    docs = collect_jsonld_docs(result, result_dir, extra_files, errors)
    items = []
    for name, doc in docs:
        if isinstance(doc, list):
            items.extend((name, d) for d in doc)
        else:
            items.append((name, doc))

    records = result.get("nanopublications")
    record_count = len(records) if isinstance(records, list) else 0
    if not items:
        errors.append(
            "最终严格质检未找到任何 JSON-LD 文档；不得跳过 @context/named graph 校验"
        )
        return
    if len(items) != record_count:
        errors.append(
            f"JSON-LD 文档数必须等于 record 数：实际 {len(items)}，期望 {record_count}"
        )

    occurrences = {}
    for name, doc in items:
        if not isinstance(doc, dict):
            errors.append(f"JSON-LD 输出 {name} 的每个文档都必须是对象")
            continue
        if doc.get("@context") != CONTEXT:
            errors.append(f"JSON-LD 输出 {name} 的 @context 与 canonical 定义不完全相等")
        check_named_graphs(name, doc, errors)
        doc_id = doc.get("@id")
        if isinstance(doc_id, str):
            occurrences.setdefault(doc_id, []).append(name)

    for urn, sources in occurrences.items():
        if len(sources) > 1:
            errors.append(f"JSON-LD URN 重复: {urn!r} 出现于 {sources}")

    expected_urns = set()
    for rec in records if isinstance(records, list) else []:
        if not isinstance(rec, dict):
            continue
        rid = rec.get("id", "<unknown>")
        try:
            expected = build_document(result, rec)
        except CanonicalizationError as exc:
            errors.append(f"{rid}: 无法构造 canonical JSON-LD: {exc}")
            continue
        urn = expected["@id"]
        expected_urns.add(urn)
        if urn not in occurrences:
            errors.append(f"{rid}: 缺失一一对应的 JSON-LD 文档 {urn!r}")
            continue
        name = occurrences[urn][0]
        index = next(
            (i for i, (_, doc) in enumerate(items)
             if isinstance(doc, dict) and doc.get("@id") == urn),
            None,
        )
        actual = items[index][1]
        if actual != expected:
            differences = canonical_differences(actual, expected)
            errors.append(
                f"{rid}: record↔JSON-LD 非 canonical 全等（{name}）："
                + "；".join(differences)
            )

    for urn, sources in occurrences.items():
        if urn not in expected_urns:
            errors.append(f"JSON-LD 含无对应 record 的额外 URN {urn!r}（来源 {sources}）")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Nanopublication 记录与 JSON-LD 严格等性质检")
    parser.add_argument(
        "--records-only", action="store_true",
        help="仅做 JSON-LD 导出前的记录质检，不检查也绝不声称已检查 JSON-LD",
    )
    parser.add_argument("result", help="result.json 路径")
    parser.add_argument("extra_jsonld", nargs="*", help="追加的 JSON-LD 文件（同样合并计数）")
    args = parser.parse_args(argv)

    errors = []
    warnings = []
    try:
        result = load_json(args.result)
    except Exception as exc:  # noqa: BLE001
        print(f"错误: 无法读取 {args.result}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(result, dict):
        print(f"错误: {args.result} 顶层不是 JSON 对象", file=sys.stderr)
        return 2

    check_predicates_and_fields(result, errors, warnings)
    if not args.records_only:
        check_jsonld(
            result, os.path.dirname(os.path.abspath(args.result)),
            args.extra_jsonld, errors,
        )

    for warning in warnings:
        print(f"警告: {warning}", file=sys.stderr)
    if errors:
        print("质检未通过，错误清单：", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    if args.records_only:
        print(
            "records-only 记录质检通过：谓词、字段、连续 id 与 evidence 状态规则已检查；"
            "尚未执行 JSON-LD 导出或最终等价质检，不代表 Final 通过。"
        )
    else:
        print(
            "最终严格等价质检通过：record 与 canonical JSON-LD 数量、URN、SPO/condition、"
            "evidence、status/basis、provenance、pubinfo 逐项全等；@context 与四 graph 合规。"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
