#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nanopublication 结果质检脚本（纯标准库）。

用法：
    # JSON-LD 导出前的记录质检（不要求已有 JSON-LD）
    python scripts/validate_nanopub.py --records-only /app/output/result.json

    # 导出后的最终严格质检（至少一个完整 JSON-LD 文档）
    python scripts/validate_nanopub.py /app/output/result.json [extra.jsonld ...]

校验项：
  1. 每条 assertion 的 predicate 在受控词表内（核心 14 + 扩展 8，见
     references/relation-vocabulary.md；本脚本内置同一清单）；
  2. 每条 nanopublication 记录含 assertion / evidence / provenance 三个字段；
     evidence 为空时，仅 status=unverified 的记录可作为 warning 放行；
  3. 最终严格质检要求至少一个 JSON-LD 文档，并逐文档检查 @context、
     assertion/evidence/provenance/pubinfo 四类 named graph，以及
     urn:nanopub:<case_id>:<n> 形态的顶层 @id。JSON-LD 来源为 result.json 的
     "jsonld" 字段、"jsonld_files" 字段所列文件和命令行追加文件。

退出码：全部通过为 0；任一校验失败为非 0，并把错误清单打印到 stderr。
"""

import argparse
import json
import os
import re
import sys

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
REQUIRED_GRAPHS = ("assertion", "evidence", "provenance", "pubinfo")
NANOPUB_URN_RE = re.compile(r"^urn:nanopub:[^:\s]+:[1-9]\d*$")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
    nps = result.get("nanopublications")
    if not isinstance(nps, list) or not nps:
        errors.append("result.json 缺少非空的 nanopublications 数组")
        return
    for i, rec in enumerate(nps, 1):
        rid = rec.get("id", f"#{i}") if isinstance(rec, dict) else f"#{i}"
        if not isinstance(rec, dict):
            errors.append(f"{rid}: 记录不是对象")
            continue
        for key in ("assertion", "evidence", "provenance"):
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
    """收集 JSON-LD 文档：命令行文件 + result.json 内嵌/引用。"""
    docs = []
    for path in extra_files:
        try:
            docs.append((path, load_json(path)))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"JSON-LD 文件 {path} 无法解析: {exc}")
    embedded = result.get("jsonld") or result.get("json_ld")
    if isinstance(embedded, str):
        try:
            docs.append(("result.json#jsonld", json.loads(embedded)))
        except json.JSONDecodeError as exc:
            errors.append(f"result.json 内嵌 jsonld 字符串无法解析: {exc}")
    elif isinstance(embedded, (dict, list)):
        docs.append(("result.json#jsonld", embedded))
    refs = result.get("jsonld_files") or []
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
    """把 np:assertion、...#assertion 等表示归一为 named graph 键名。"""
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
    """兼容契约示例的 @graph 列表及等价的 @graph 对象/直接四键表示。"""
    declared = set()
    graph_ids = {}

    for key in doc:
        graph_name = local_name(key)
        if graph_name in REQUIRED_GRAPHS:
            declared.add(graph_name)

    graph_container = doc.get("@graph")
    graph_items = graph_container if isinstance(graph_container, list) else [graph_container]
    if isinstance(graph_container, dict) and "@id" not in graph_container:
        # 支持 {"@graph": {"assertion": {...}, ...}} 的按键分组形式。
        graph_items = []
        for key, value in graph_container.items():
            graph_name = local_name(key)
            if graph_name in REQUIRED_GRAPHS:
                declared.add(graph_name)
                if isinstance(value, dict) and isinstance(value.get("@id"), str):
                    graph_ids[graph_name] = value["@id"]

    for item in graph_items:
        if not isinstance(item, dict):
            continue
        for key in item:
            graph_name = local_name(key)
            if graph_name in REQUIRED_GRAPHS:
                declared.add(graph_name)
        graph_name = local_name(item.get("@id"))
        if graph_name in REQUIRED_GRAPHS:
            declared.add(graph_name)
            graph_ids[graph_name] = item["@id"]

    missing = [key for key in REQUIRED_GRAPHS if key not in declared]
    if missing:
        errors.append(
            f"JSON-LD 输出 {name} 缺少 named graph: {', '.join(missing)}"
            "（要求 assertion/evidence/provenance/pubinfo 四键）"
        )

    doc_id = doc.get("@id")
    if not isinstance(doc_id, str) or not NANOPUB_URN_RE.fullmatch(doc_id):
        errors.append(
            f"JSON-LD 输出 {name} 的顶层 @id 不符合 urn:nanopub:<case_id>:<n>；"
            f"实际为 {doc_id!r}"
        )
        return
    for graph_name, graph_id in graph_ids.items():
        expected = f"{doc_id}#{graph_name}"
        if graph_id != expected:
            errors.append(
                f"JSON-LD 输出 {name} 的 {graph_name} graph @id 应为 {expected!r}，"
                f"实际为 {graph_id!r}"
            )


def check_jsonld(result, result_dir, extra_files, errors):
    docs = collect_jsonld_docs(result, result_dir, extra_files, errors)
    items = []
    for name, doc in docs:
        if isinstance(doc, list):
            items.extend((name, d) for d in doc)
        else:
            items.append((name, doc))
    if not items:
        errors.append(
            "最终严格质检未找到任何 JSON-LD 文档；不得跳过 @context/named graph 校验"
        )
        return
    for name, doc in items:
        if not isinstance(doc, dict):
            errors.append(f"JSON-LD 输出 {name} 的每个文档都必须是对象")
            continue
        if "@context" not in doc:
            errors.append(f"JSON-LD 输出 {name} 缺少 @context")
        check_named_graphs(name, doc, errors)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Nanopublication 记录与 JSON-LD 严格质检")
    parser.add_argument(
        "--records-only", action="store_true",
        help="仅做 JSON-LD 导出前的记录质检，不检查 JSON-LD",
    )
    parser.add_argument("result", help="result.json 路径")
    parser.add_argument("extra_jsonld", nargs="*", help="追加的 JSON-LD 文件")
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
        print("记录质检通过：谓词全部在受控词表内；assertion/evidence/provenance 齐全；evidence 已按 status 校验。尚未执行 JSON-LD 最终严格质检。")
    else:
        print("最终严格质检通过：谓词全部在受控词表内；assertion/evidence/provenance 齐全；evidence 已按 status 校验；JSON-LD @context、四类 named graph 与 URN @id 形态校验完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
