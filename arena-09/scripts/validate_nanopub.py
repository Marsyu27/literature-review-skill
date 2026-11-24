#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nanopublication 结果质检脚本（纯标准库）。

用法：
    python scripts/validate_nanopub.py /app/output/result.json [extra.jsonld ...]

校验项：
  1. 每条 assertion 的 predicate 在受控词表内（核心 14 + 扩展 8，见
     references/relation-vocabulary.md；本脚本内置同一清单）；
  2. 每条 nanopublication 记录含 assertion / evidence / provenance 三个字段，
     且 evidence 非空（evidence_text 或等效内容不为空）；
  3. JSON-LD 输出含 @context（JSON-LD 来源：result.json 的 "jsonld" 字段、
     "jsonld_files" 字段所列文件，以及命令行追加的 JSON-LD 文件）。

退出码：全部通过为 0；任一校验失败为非 0，并把错误清单打印到 stderr。
"""

import json
import os
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


def check_predicates_and_fields(result, errors):
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
        if isinstance(assertion, dict):
            pred = normalize_predicate(
                assertion.get("predicate") or assertion.get("np:predicate")
            )
            if pred not in ALLOWED_PREDICATES:
                errors.append(
                    f"{rid}: predicate '{assertion.get('predicate')}' 不在受控词表内"
                )
        if "evidence" in rec and evidence_is_empty(rec.get("evidence")):
            errors.append(f"{rid}: evidence 为空（evidence_text 缺失或空白）")


def collect_jsonld_docs(result, result_dir, extra_files, errors):
    """收集 JSON-LD 文档：命令行文件 + result.json 内嵌/引用。"""
    docs = []
    for path in extra_files:
        try:
            docs.append((path, load_json(path)))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"JSON-LD 文件 {path} 无法解析: {exc}")
    if isinstance(result, dict):
        embedded = result.get("jsonld") or result.get("json_ld")
        if isinstance(embedded, str):
            try:
                docs.append(("result.json#jsonld", json.loads(embedded)))
            except json.JSONDecodeError as exc:
                errors.append(f"result.json 内嵌 jsonld 字符串无法解析: {exc}")
        elif isinstance(embedded, (dict, list)):
            docs.append(("result.json#jsonld", embedded))
        for rel in result.get("jsonld_files") or []:
            path = rel if os.path.isabs(rel) else os.path.join(result_dir, rel)
            try:
                docs.append((path, load_json(path)))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"JSON-LD 文件 {path} 无法解析: {exc}")
    return docs


def check_context(result, result_dir, extra_files, errors):
    docs = collect_jsonld_docs(result, result_dir, extra_files, errors)
    if not docs:
        print("警告: 未找到 JSON-LD 导出（无 jsonld 字段/文件），跳过 @context 校验",
              file=sys.stderr)
        return
    items = []
    for name, doc in docs:
        if isinstance(doc, list):
            items.extend((name, d) for d in doc)
        else:
            items.append((name, doc))
    for name, doc in items:
        if not isinstance(doc, dict) or "@context" not in doc:
            errors.append(f"JSON-LD 输出 {name} 缺少 @context")


def main(argv):
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    result_path = argv[1]
    extra_files = argv[2:]
    errors = []
    try:
        result = load_json(result_path)
    except Exception as exc:  # noqa: BLE001
        print(f"错误: 无法读取 {result_path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(result, dict):
        print(f"错误: {result_path} 顶层不是 JSON 对象", file=sys.stderr)
        return 2

    check_predicates_and_fields(result, errors)
    check_context(result, os.path.dirname(os.path.abspath(result_path)),
                  extra_files, errors)

    if errors:
        print("质检未通过，错误清单：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("质检通过：谓词全部在受控词表内；assertion/evidence/provenance 齐全且 evidence 非空；JSON-LD @context 校验完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
