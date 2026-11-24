#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 result.json 的 records 机械导出 canonical JSON-LD（纯标准库）。

用法：
    python scripts/export_nanopub.py /app/output/result.json \
        --out-dir /app/output/nanopubs --update-result

JSON-LD 的唯一内容来源是 result.json。build_document() 同时供导出器和最终
质检器使用，避免两套映射漂移。导出不删除 out-dir 中的其他文件。
"""

import argparse
import copy
import json
import os
import re
import sys

CONTEXT = {
    "schema": "https://schema.org/",
    "np": "https://example.org/nanopub-skill/ns#",
    "assertion": "np:assertion",
    "evidence": "np:evidence",
    "provenance": "np:provenance",
    "pubinfo": "np:pubinfo",
}
GRAPH_NAMES = ("assertion", "evidence", "provenance", "pubinfo")
RECORD_ID_RE = re.compile(r"^np-(\d{3}|[1-9]\d{3,})$")
NANOPUB_URN_RE = re.compile(r"^urn:nanopub:[^:\s]+:[1-9]\d*$")
PROVENANCE_KEYS = ("assertion", "evidence", "paper", "author", "year", "version")


class CanonicalizationError(ValueError):
    """输入记录无法按契约机械导出。"""


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def record_number(record_id):
    """返回 np-NNN 的十进制序号；拒绝前导零、np-000 等替代外壳。"""
    if not isinstance(record_id, str):
        raise CanonicalizationError(f"record.id 必须是 np-001 形式的字符串，实际为 {record_id!r}")
    match = RECORD_ID_RE.fullmatch(record_id)
    if not match or int(match.group(1)) < 1:
        raise CanonicalizationError(f"record.id 必须形如 np-001 且序号从 1 开始，实际为 {record_id!r}")
    return int(match.group(1))


def nanopub_urn(result, rec):
    case_id = result.get("case_id")
    number = record_number(rec.get("id"))
    urn = f"urn:nanopub:{case_id}:{number}"
    if not isinstance(case_id, str) or not NANOPUB_URN_RE.fullmatch(urn):
        raise CanonicalizationError(
            "case_id 必须是非空字符串，且不能包含冒号或空白；"
            f"无法由 {case_id!r} 构造合规 URN"
        )
    return urn


def build_document(result, rec):
    """由一条 record 构造唯一 canonical 文档，不读取任何既有 JSON-LD。

    canonical 外壳固定为 @context、顶层 @id、按 GRAPH_NAMES 排列的四项
    @graph 列表。未提供的 pubinfo 标准字段使用空值；license 仅在输入含该
    字段时输出。空 condition 省略，evidence 三键始终保留。
    """
    if not isinstance(result, dict) or not isinstance(rec, dict):
        raise CanonicalizationError("result 与每条 record 都必须是 JSON 对象")
    for key in ("status", "basis"):
        if key not in rec:
            raise CanonicalizationError(f"{rec.get('id', '<unknown>')}: 缺少字段 {key}")
    assertion = rec.get("assertion")
    if not isinstance(assertion, dict):
        raise CanonicalizationError(f"{rec.get('id', '<unknown>')}: assertion 必须是对象")
    evidence = rec.get("evidence")
    if evidence is None:
        evidence = {}
    if not isinstance(evidence, dict):
        raise CanonicalizationError(f"{rec.get('id', '<unknown>')}: evidence 必须是对象或 null")
    provenance = rec.get("provenance")
    if not isinstance(provenance, dict):
        raise CanonicalizationError(f"{rec.get('id', '<unknown>')}: provenance 必须是对象")
    pubinfo = result.get("pubinfo", {})
    if pubinfo is None:
        pubinfo = {}
    if not isinstance(pubinfo, dict):
        raise CanonicalizationError("result.pubinfo 必须是对象或 null")

    urn = nanopub_urn(result, rec)
    predicate = assertion.get("predicate", assertion.get("np:predicate", ""))
    if isinstance(predicate, str) and not predicate.startswith("np:"):
        predicate = "np:" + predicate

    assertion_graph = {
        "@id": urn + "#assertion",
        "@type": "np:Assertion",
        "np:subject": assertion.get("subject", assertion.get("np:subject", "")),
        "np:predicate": predicate,
        "np:object": assertion.get("object", assertion.get("np:object", "")),
        "np:status": rec.get("status", ""),
        "np:basis": rec.get("basis", ""),
    }
    condition = assertion.get("condition", assertion.get("np:condition"))
    if condition is not None and condition != "":
        assertion_graph["np:condition"] = condition

    evidence_graph = {
        "@id": urn + "#evidence",
        "@type": "np:Evidence",
        "np:evidence_text": evidence.get("evidence_text", evidence.get("np:evidence_text", "")),
        "np:evidence_location": evidence.get(
            "evidence_location", evidence.get("np:evidence_location", "")
        ),
        "np:evidence_type": evidence.get("evidence_type", evidence.get("np:evidence_type", "")),
    }

    provenance_graph = {
        "@id": urn + "#provenance",
        "@type": "np:Provenance",
    }
    normalized_provenance = {}
    for key, value in provenance.items():
        if not isinstance(key, str) or not key or key.startswith("@"):
            raise CanonicalizationError(f"{rec.get('id')}: provenance 含非法字段名 {key!r}")
        local = key[3:] if key.startswith("np:") else key
        if local in normalized_provenance:
            raise CanonicalizationError(f"{rec.get('id')}: provenance 字段 {local!r} 重复定义")
        normalized_provenance[local] = value
    for key in PROVENANCE_KEYS:
        if key in normalized_provenance:
            provenance_graph["np:" + key] = normalized_provenance[key]
    for key in sorted(normalized_provenance):
        if key not in PROVENANCE_KEYS and key not in {"wasDerivedFrom", "extractionMethod"}:
            provenance_graph["np:" + key] = normalized_provenance[key]
    provenance_graph["np:wasDerivedFrom"] = urn + "#evidence"
    paper_title = pubinfo.get("paper_title", "")
    provenance_graph["np:extractionMethod"] = (
        f"由 nanopublication-extraction Skill 从论文 {paper_title} 抽取"
    )

    pubinfo_graph = {
        "@id": urn + "#pubinfo",
        "@type": "schema:ScholarlyArticle",
        "schema:name": paper_title,
        "schema:author": pubinfo.get("authors", []),
        "schema:datePublished": pubinfo.get("year", ""),
        "schema:version": pubinfo.get("version", ""),
        "schema:identifier": pubinfo.get("identifier", ""),
    }
    if "license" in pubinfo:
        pubinfo_graph["schema:license"] = pubinfo["license"]

    return {
        "@context": copy.deepcopy(CONTEXT),
        "@id": urn,
        "@graph": [assertion_graph, evidence_graph, provenance_graph, pubinfo_graph],
    }


def build_documents(result):
    """验证 id 唯一、连续后，按 record 顺序构造完整文档集。"""
    records = result.get("nanopublications") if isinstance(result, dict) else None
    if not isinstance(records, list) or not records:
        raise CanonicalizationError("result.nanopublications 必须是非空数组")
    documents = []
    seen = set()
    for index, rec in enumerate(records, 1):
        if not isinstance(rec, dict):
            raise CanonicalizationError(f"第 {index} 条 record 不是对象")
        record_id = rec.get("id")
        expected_id = f"np-{index:03d}"
        if isinstance(record_id, str) and record_id in seen:
            raise CanonicalizationError(f"record.id 重复: {record_id!r}")
        if record_id != expected_id:
            raise CanonicalizationError(
                f"record.id 必须唯一且从 np-001 连续编号：第 {index} 条应为 "
                f"{expected_id!r}，实际为 {record_id!r}"
            )
        seen.add(record_id)
        documents.append(build_document(result, rec))
    return documents


def _json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def export_result(result_path, out_dir, update_result=False):
    """导出稳定文件，返回 (documents, manifest)；失败时不改写 result。"""
    result_path = os.path.abspath(result_path)
    out_dir = os.path.abspath(out_dir)
    result = load_json(result_path)
    if not isinstance(result, dict):
        raise CanonicalizationError("result.json 顶层必须是对象")
    documents = build_documents(result)
    records = result["nanopublications"]

    os.makedirs(out_dir, exist_ok=True)
    output_paths = []
    for rec, document in zip(records, documents):
        path = os.path.join(out_dir, rec["id"] + ".jsonld")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_json_text(document))
        output_paths.append(path)

    manifest = [
        os.path.relpath(path, os.path.dirname(result_path)).replace(os.sep, "/")
        for path in output_paths
    ]
    if update_result:
        # 只改 JSON-LD 来源字段；留出目录中的其他文件及其他 result 字段不动。
        result.pop("jsonld", None)
        result.pop("json_ld", None)
        result["jsonld_files"] = manifest
        with open(result_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_json_text(result))
    return documents, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="从 records 机械导出 canonical JSON-LD")
    parser.add_argument("result", help="result.json 路径")
    parser.add_argument("--out-dir", required=True, help="每 record 一个 np-NNN.jsonld 的输出目录")
    parser.add_argument(
        "--update-result", action="store_true",
        help="仅更新 result.json 的 jsonld_files，并移除内嵌 jsonld/json_ld 陈旧字段",
    )
    args = parser.parse_args(argv)
    try:
        documents, manifest = export_result(args.result, args.out_dir, args.update_result)
    except (CanonicalizationError, OSError, json.JSONDecodeError) as exc:
        print(f"导出失败: {exc}", file=sys.stderr)
        return 1
    print(f"已机械导出 {len(documents)} 个 canonical JSON-LD 文档：")
    for path in manifest:
        print(f"  {path}")
    if args.update_result:
        print("已更新 jsonld_files，并清除内嵌 jsonld/json_ld 字段。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
