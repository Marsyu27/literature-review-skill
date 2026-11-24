#!/usr/bin/env python3
"""Real CLI positive/negative regressions for scripts/kg_tool.py.

Everything is created in tempfile.TemporaryDirectory; no result or cache files
are committed or left in the submission.  Run: python3 src/reproduce.py
"""

import copy
import json
import os
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "scripts", "kg_tool.py")
REQUIRED = [
    "SKILL.md",
    "README.md",
    "references/entity-recognition.md",
    "references/entity-alignment.md",
    "references/relation-extraction.md",
    "references/source-binding.md",
    "references/graph-query.md",
    "references/output-schema.md",
    "examples/kg-examples.md",
    "scripts/kg_tool.py",
    "src/reproduce.py",
]


def check_frontmatter(path):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    if not text.startswith("---"):
        return False, "缺少 YAML frontmatter"
    end = text.find("\n---", 3)
    if end < 0:
        return False, "frontmatter 未闭合"
    frontmatter = text[3:end]
    ok = "name:" in frontmatter and "description:" in frontmatter
    return ok, "name/description 齐全" if ok else "缺 name 或 description"


def write_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def cli(arguments, expected_code):
    completed = subprocess.run(
        [sys.executable, TOOL] + arguments,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != expected_code:
        raise AssertionError(
            "CLI %s returned %d, expected %d\nstdout=%s\nstderr=%s"
            % (arguments, completed.returncode, expected_code, completed.stdout, completed.stderr)
        )
    return completed


def evidence(source_id, paragraph_id, quote):
    return {
        "source_id": source_id,
        "paragraph_id": paragraph_id,
        "quote": quote,
        "strength": "strong",
    }


def node(entity_id, label, source_id, paragraph_id):
    return {
        "entity_id": entity_id,
        "type": "method",
        "label": label,
        "aliases": [],
        "source_id": source_id,
        "evidence": evidence(source_id, paragraph_id, label),
    }


def edge(edge_id, source, target, predicate, evidence_items):
    return {
        "edge_id": edge_id,
        "source": source,
        "target": target,
        "predicate": predicate,
        "condition": "regression fixture",
        "evidence": evidence_items,
    }


def fixture():
    primary = "primary"
    secondary = "secondary"
    return {
        "case_id": "cli-regression",
        "status": "success",
        "status_reason": "四条查询均由工具真实执行",
        "sources": [
            {"source_id": primary, "jats_file": "primary-material.json"},
            {"source_id": secondary, "jats_file": "secondary-material.json"},
        ],
        "nodes": [
            node("N1", "Alpha Model", primary, "pri-p-001"),
            node("N2", "Dataset D", primary, "pri-p-002"),
            node("N3", "Result R", primary, "pri-p-003"),
            node("N4", "Alpha Model", secondary, "sec-p-001"),
            node("N5", "Baseline B", secondary, "sec-p-002"),
            node("N6", "Conclusion C", secondary, "sec-p-003"),
            node("N7", "Shared Concept", primary, "pri-p-004"),
        ],
        "edges": [
            edge("R1", "N1", "N2", "uses", [evidence(primary, "pri-p-002", "Alpha uses D")]),
            edge("R2", "N1", "N3", "supports", [evidence(primary, "pri-p-003", "Alpha supports R")]),
            edge("R3", "N4", "N1", "same_concept", [
                evidence(primary, "pri-p-001", "Alpha Model"),
                evidence(secondary, "sec-p-001", "Alpha Model"),
            ]),
            edge("R4", "N4", "N5", "outperforms", [evidence(secondary, "sec-p-002", "Alpha exceeds B")]),
            edge("R5", "N5", "N6", "supports", [evidence(secondary, "sec-p-003", "B supports C")]),
            edge("R7", "N4", "N7", "same_concept", [
                evidence(primary, "pri-p-004", "Shared Concept"),
                evidence(secondary, "sec-p-001", "Shared Concept"),
            ]),
            edge("R8", "N7", "N3", "supports", [evidence(primary, "pri-p-004", "Concept supports R")]),
        ],
        "queries": [
            {
                "query": "哪些主图边使用 Alpha Model？",
                "query_spec": {"op": "filter_edges", "predicate": "uses", "label_contains": "alpha model"},
                "uncertain_relations": [],
            },
            {
                "query": "Alpha Model 的 supports 出边是什么？",
                "query_spec": {"op": "neighbors", "entity_id": "N1", "direction": "out", "predicate": "supports"},
                "uncertain_relations": [],
            },
            {
                "query": "secondary Alpha Model 到 Result R 的最短路径是什么？",
                "query_spec": {"op": "path", "start": "N4", "end": "N3", "max_depth": 2},
                "uncertain_relations": [],
            },
            {
                "query": "不存在的标签有边吗？",
                "query_spec": {"op": "filter_edges", "label_contains": "definitely absent"},
                "uncertain_relations": [],
            },
        ],
        "provenance": [],
        "uncertainties": [],
        "tool_commands": [],
    }


def assert_main_graph_subset(executed, original):
    main_edges = {item["edge_id"]: item for item in original["edges"]}
    for query in executed["queries"]:
        ids = query["execution"]["matched_edge_ids"]
        assert ids == sorted(set(ids)), "matched_edge_ids must be stably sorted and unique"
        assert query["execution"]["result_count"] == len(ids)
        assert [item["edge_id"] for item in query["result_subgraph"]] == ids
        projected = []
        inherited = []
        for edge_id in ids:
            main = main_edges[edge_id]
            projected.append({
                "edge_id": edge_id,
                "source": main["source"],
                "predicate": main["predicate"],
                "target": main["target"],
            })
            for item in main["evidence"]:
                fingerprint = json.dumps(item, ensure_ascii=False, sort_keys=True)
                if fingerprint not in {json.dumps(old, ensure_ascii=False, sort_keys=True) for old in inherited}:
                    inherited.append(item)
        assert query["result_subgraph"] == projected, "query output is not an exact main-edge projection"
        assert query["evidence"] == inherited, "query evidence is not the complete stable-deduplicated main-edge inheritance"
    assert executed["queries"][3]["result_subgraph"] == []
    assert executed["queries"][3]["evidence"] == []
    assert executed["queries"][3]["execution"]["matched_edge_ids"] == []
    path_execution = executed["queries"][2]["execution"]
    assert path_execution["matched_edge_ids"] == ["R2", "R3", "R7", "R8"]
    assert path_execution["paths"] == [
        {"node_ids": ["N4", "N1", "N3"], "edge_ids": ["R3", "R2"]},
        {"node_ids": ["N4", "N7", "N3"], "edge_ids": ["R7", "R8"]},
    ], "equal-length paths are not deterministically sorted"


def expect_validation_failure(work, name, graph):
    graph_path = os.path.join(work, name + ".json")
    report_path = os.path.join(work, name + "-report.json")
    write_json(graph_path, graph)
    cli(["validate", "--graph", graph_path, "--report", report_path], 1)
    report = read_json(report_path)
    assert report["valid"] is False and report["errors"], name + " did not produce failure details"


def main():
    missing = [path for path in REQUIRED if not os.path.isfile(os.path.join(ROOT, path))]
    if missing:
        print("缺失文件: %s" % missing)
        return 1
    ok, message = check_frontmatter(os.path.join(ROOT, "SKILL.md"))
    if not ok:
        print("SKILL.md frontmatter 校验失败: %s" % message)
        return 1

    log = ["Skill CLI 正反回归开始", "文件盘点与 frontmatter: PASS"]
    with tempfile.TemporaryDirectory(prefix="kg-tool-regression-") as work:
        original = fixture()
        source_path = os.path.join(work, "source.json")
        executed_path = os.path.join(work, "executed.json")
        report_path = os.path.join(work, "report.json")
        write_json(source_path, original)

        cli(["query", "--graph", source_path, "--out", executed_path], 0)
        cli(["validate", "--graph", executed_path, "--report", report_path], 0)
        executed = read_json(executed_path)
        assert read_json(report_path)["valid"] is True
        assert_main_graph_subset(executed, original)
        log.append("query --out + validate: PASS (exit 0/0；7边、2来源、4查询；空结果与双最短路径为主图子集)")

        update_path = os.path.join(work, "update.json")
        write_json(update_path, original)
        cli(["query", "--graph", update_path, "--update"], 0)
        assert read_json(update_path) == executed, "--update did not produce deterministic identical JSON"
        update_report = os.path.join(work, "update-report.json")
        cli(["validate", "--graph", update_path, "--report", update_report], 0)
        log.append("query --update 原子更新 + validate: PASS (exit 0/0)")

        tampered = copy.deepcopy(executed)
        tampered["queries"][0]["result_subgraph"][0]["target"] = "NOT-A-MAIN-ENDPOINT"
        expect_validation_failure(work, "tampered-subgraph", tampered)
        log.append("篡改查询子图: PASS rejected (exit 1)")

        tampered = copy.deepcopy(executed)
        tampered["queries"][0]["evidence"][0]["quote"] = "FORGED-NON-MAIN-EVIDENCE"
        expect_validation_failure(work, "tampered-evidence", tampered)
        log.append("篡改继承 evidence: PASS rejected (exit 1)")

        tampered = copy.deepcopy(executed)
        tampered["queries"][0]["execution"]["matched_edge_ids"] = []
        expect_validation_failure(work, "tampered-matches", tampered)
        log.append("篡改 matched_edge_ids: PASS rejected (exit 1)")

        tampered = copy.deepcopy(executed)
        tampered["queries"][0]["query_spec"]["predicate"] = "outperforms"
        expect_validation_failure(work, "tampered-spec", tampered)
        log.append("篡改 query_spec: PASS rejected (exit 1)")

        tampered = copy.deepcopy(executed)
        del tampered["queries"][0]["query_spec"]
        expect_validation_failure(work, "missing-spec", tampered)
        log.append("缺 query_spec: PASS rejected (exit 1)")

        invalid = copy.deepcopy(executed)
        invalid["queries"][0]["query_spec"]["edge_id"] = "NOT-IN-MAIN-GRAPH"
        expect_validation_failure(work, "unknown-query-edge-id", invalid)
        log.append("查询引用非主图 edge_id: PASS rejected (exit 1)")

        invalid = copy.deepcopy(executed)
        invalid["nodes"].append(copy.deepcopy(invalid["nodes"][0]))
        expect_validation_failure(work, "duplicate-id", invalid)
        log.append("重复 node ID: PASS rejected (exit 1)")

        invalid = copy.deepcopy(executed)
        invalid["edges"].append(copy.deepcopy(invalid["edges"][0]))
        expect_validation_failure(work, "duplicate-edge-id", invalid)
        log.append("重复 edge ID: PASS rejected (exit 1)")

        invalid = copy.deepcopy(executed)
        invalid["edges"][0]["target"] = "DANGLING"
        expect_validation_failure(work, "dangling-endpoint", invalid)
        log.append("悬空边端点: PASS rejected (exit 1)")

        invalid = copy.deepcopy(executed)
        invalid["edges"][0]["evidence"] = evidence("primary", "pri-p-002", "not an array")
        expect_validation_failure(work, "edge-evidence-not-array", invalid)
        log.append("边 evidence 非数组: PASS rejected (exit 1)")

        invalid = copy.deepcopy(executed)
        invalid["edges"][0]["evidence"] = [evidence("UNREGISTERED", "pri-p-002", "unknown source")]
        expect_validation_failure(work, "unregistered-source", invalid)
        log.append("证据来源未登记: PASS rejected (exit 1)")

        invalid = copy.deepcopy(executed)
        invalid["edges"][2]["evidence"] = [evidence("secondary", "sec-p-001", "one side only")]
        expect_validation_failure(work, "one-sided-cross-paper", invalid)
        log.append("跨篇单侧证据: PASS rejected (exit 1)")

        partial = copy.deepcopy(executed)
        partial["queries"] = partial["queries"][:2]
        partial["status"] = "partial"
        partial["status_reason"] = "真实执行 2 条查询；其余 2 条因测试预算耗尽尚未完成。"
        partial_path = os.path.join(work, "partial.json")
        partial_report = os.path.join(work, "partial-report.json")
        write_json(partial_path, partial)
        cli(["query", "--graph", partial_path, "--update"], 0)
        cli(["validate", "--graph", partial_path, "--report", partial_report], 0)
        log.append("partial 真实 2 条且说明缺口: PASS accepted (query/validate exit 0/0)")

        dishonest_success = copy.deepcopy(partial)
        dishonest_success["status"] = "success"
        dishonest_success["status_reason"] = "声称完成"
        expect_validation_failure(work, "short-success", dishonest_success)
        log.append("success 少于 3 条: PASS rejected (exit 1)")

    log.append("全部回归通过；临时文件已自动清理，无提交残留。")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("SELFTEST FAILURE: %s" % exc, file=sys.stderr)
        sys.exit(1)
