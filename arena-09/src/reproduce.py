#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skill 真实 CLI 正反回归（纯标准库，所有测试输出均在 tempfile 中）。

运行: python3 src/reproduce.py
成功退出码 0；资源缺失、frontmatter 错误或任一正反例不符合预期退出码 1。
不向提交目录写 results、run.log、__pycache__ 或测试 JSON-LD。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTER = os.path.join(ROOT, "scripts", "export_nanopub.py")
VALIDATOR = os.path.join(ROOT, "scripts", "validate_nanopub.py")

REQUIRED = [
    "SKILL.md",
    "references/assertion-decomposition.md",
    "references/relation-vocabulary.md",
    "references/evidence-binding.md",
    "references/provenance-metadata.md",
    "references/quality-check.md",
    "references/output-schema.md",
    "examples/nanopub-examples.md",
    "scripts/export_nanopub.py",
    "scripts/validate_nanopub.py",
    "src/reproduce.py",
]


class RegressionFailure(AssertionError):
    pass


def require(condition, message):
    if not condition:
        raise RegressionFailure(message)


def check_frontmatter(path):
    with open(path, encoding="utf-8") as handle:
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
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def run_cli(arguments, cwd):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable] + arguments,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def expect_success(process, label):
    require(
        process.returncode == 0,
        f"{label} 应通过，实际退出码 {process.returncode}\n"
        f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}",
    )


def expect_rejection(process, label):
    require(
        process.returncode == 1,
        f"{label} 应以退出码 1 拒绝，实际退出码 {process.returncode}\n"
        f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}",
    )


def graph(doc, name):
    return next(item for item in doc["@graph"] if item["@id"].endswith("#" + name))


def export_and_validate(case_dir, label):
    result_path = os.path.join(case_dir, "result.json")
    out_dir = os.path.join(case_dir, "nanopubs")
    exported = run_cli(
        [EXPORTER, result_path, "--out-dir", out_dir, "--update-result"], case_dir
    )
    expect_success(exported, label + " / export")
    validated = run_cli([VALIDATOR, result_path], case_dir)
    expect_success(validated, label + " / validate")
    return exported, validated


def base_result():
    provenance = {
        "assertion": "np-001",
        "evidence": "page=2 §3 ¶2",
        "paper": "A Demonstration Study",
        "author": "A. Author",
        "year": "2025",
        "version": "arXiv v2",
        "data_source": "supplement S1",
        "extractionMethod": "此自由文本必须被规范模板覆盖",
        "wasDerivedFrom": "urn:stale:value",
    }
    first = {
        "id": "np-001",
        "assertion": {
            "subject": "Treatment A",
            "predicate": "reduces",
            "object": "tumor size",
            "condition": "by 30%, p<0.05, in mice",
        },
        "evidence": {
            "evidence_text": "Treatment A reduced tumor size by 30% (p<0.05) in mice",
            "evidence_location": "page=2 §3 ¶2",
            "evidence_type": "direct",
        },
        "provenance": provenance,
        "status": "ok",
        "basis": "原文直接给出方向、数值和限定条件。",
    }
    second = {
        "id": "np-002",
        "assertion": {
            "subject": "Treatment A",
            "predicate": "improves",
            "object": "survival",
            "condition": "",
        },
        "evidence": {
            "evidence_text": "Treatment A improved survival in mice",
            "evidence_location": "page=2 §3 ¶2",
            "evidence_type": "direct",
        },
        "provenance": dict(provenance, assertion="np-002"),
        "status": "ok",
        "basis": "原文直接陈述生存期改善。",
    }
    return {
        "case_id": "regression-case",
        "status": "success",
        "status_reason": "",
        "pubinfo": {
            "paper_title": "A Demonstration Study",
            "authors": ["A. Author", "B. Author"],
            "year": "2025",
            "version": "arXiv v2",
            "identifier": "arXiv:2501.00000",
            "license": "CC-BY-4.0",
        },
        "nanopublications": [first, second],
        "uncertainties": [],
        "tool_commands": [],
        "sentinel": "update-result 不得删除此字段",
        "jsonld": {"stale": True},
        "json_ld": {"also_stale": True},
    }


def copy_case(base_dir, root, name):
    target = os.path.join(root, name)
    shutil.copytree(base_dir, target)
    return target


def modify_doc(case_dir, record_id, mutate):
    refs = read_json(os.path.join(case_dir, "result.json"))["jsonld_files"]
    relative = next(path for path in refs if path.endswith(record_id + ".jsonld"))
    path = os.path.join(case_dir, relative)
    doc = read_json(path)
    mutate(doc)
    write_json(path, doc)


def validate_case(case_dir):
    return run_cli([VALIDATOR, os.path.join(case_dir, "result.json")], case_dir)


def run_regressions(root):
    base_dir = os.path.join(root, "valid")
    os.makedirs(base_dir)
    result_path = os.path.join(base_dir, "result.json")
    write_json(result_path, base_result())

    records_only = run_cli([VALIDATOR, "--records-only", result_path], base_dir)
    expect_success(records_only, "两条完整 record / records-only")
    require(
        "尚未执行 JSON-LD" in records_only.stdout and "不代表 Final" in records_only.stdout,
        "records-only 不得声称 Final 或 JSON-LD 已通过",
    )
    export_and_validate(base_dir, "两条完整 record")
    updated = read_json(result_path)
    require("jsonld" not in updated and "json_ld" not in updated, "陈旧内嵌字段未清除")
    require(updated["sentinel"] == "update-result 不得删除此字段", "update-result 删除了其他字段")
    require(
        updated["jsonld_files"] == ["nanopubs/np-001.jsonld", "nanopubs/np-002.jsonld"],
        "jsonld_files 不是本次规范清单",
    )
    first_doc = read_json(os.path.join(base_dir, updated["jsonld_files"][0]))
    require(len(first_doc["@graph"]) == 4, "canonical @graph 不是四项")
    require(
        graph(first_doc, "provenance")["np:wasDerivedFrom"]
        == "urn:nanopub:regression-case:1#evidence",
        "wasDerivedFrom 未由规范 URN 派生",
    )
    require(
        graph(first_doc, "provenance")["np:data_source"] == "supplement S1",
        "额外 provenance 字段未保留",
    )
    require("np:condition" not in graph(read_json(os.path.join(base_dir, updated["jsonld_files"][1])), "assertion"), "空 condition 未省略")

    tracked = [result_path] + [os.path.join(base_dir, path) for path in updated["jsonld_files"]]
    unrelated = os.path.join(base_dir, "nanopubs", "keep-unrelated.txt")
    with open(unrelated, "w", encoding="utf-8") as handle:
        handle.write("exporter 不得删除此文件\n")
    before = [hashlib.sha256(open(path, "rb").read()).hexdigest() for path in tracked]
    export_and_validate(base_dir, "稳定重跑")
    after = [hashlib.sha256(open(path, "rb").read()).hexdigest() for path in tracked]
    require(before == after, "重复 export --update-result 的文件内容不稳定")
    require(os.path.isfile(unrelated), "export --update-result 删除了其他文件")

    # (场景名, 是否先删除被改文档, 文档修改函数)；record 篡改另测。
    scenarios = [
        ("predicate 变化", "np-001", lambda doc: graph(doc, "assertion").__setitem__("np:predicate", "np:causes")),
        ("object 变化", "np-001", lambda doc: graph(doc, "assertion").__setitem__("np:object", "other outcome")),
        ("condition 变化", "np-001", lambda doc: graph(doc, "assertion").__setitem__("np:condition", "unbounded")),
        ("evidence 内容变化", "np-001", lambda doc: graph(doc, "evidence").__setitem__("np:evidence_text", "fabricated")),
        ("provenance 变化", "np-001", lambda doc: graph(doc, "provenance").__setitem__("np:paper", "Other Paper")),
        ("pubinfo 变化", "np-001", lambda doc: graph(doc, "pubinfo").__setitem__("schema:name", "Other Paper")),
    ]
    negative_count = 0
    for label, record_id, mutate in scenarios:
        case_dir = copy_case(base_dir, root, "bad-" + record_id + "-" + str(negative_count))
        modify_doc(case_dir, record_id, mutate)
        expect_rejection(validate_case(case_dir), label)
        negative_count += 1

    case_dir = copy_case(base_dir, root, "missing-document")
    refs = read_json(os.path.join(case_dir, "result.json"))["jsonld_files"]
    os.remove(os.path.join(case_dir, refs[-1]))
    expect_rejection(validate_case(case_dir), "少一文档")
    negative_count += 1

    case_dir = copy_case(base_dir, root, "extra-document")
    result_file = os.path.join(case_dir, "result.json")
    result = read_json(result_file)
    source = os.path.join(case_dir, result["jsonld_files"][-1])
    extra = os.path.join(case_dir, "nanopubs", "np-003.jsonld")
    shutil.copyfile(source, extra)
    with_extra = run_cli(
        [VALIDATOR, result_file, extra], case_dir
    )
    expect_rejection(with_extra, "多一 CLI extra 文档及重复附件来源")
    negative_count += 1

    case_dir = copy_case(base_dir, root, "embedded-duplicate")
    result_file = os.path.join(case_dir, "result.json")
    result = read_json(result_file)
    result["jsonld"] = read_json(os.path.join(case_dir, result["jsonld_files"][0]))
    write_json(result_file, result)
    expect_rejection(validate_case(case_dir), "内嵌 JSON-LD 重复来源")
    negative_count += 1

    case_dir = copy_case(base_dir, root, "duplicate-urn")
    def duplicate_urn(doc):
        doc["@id"] = "urn:nanopub:regression-case:1"
        for item in doc["@graph"]:
            item["@id"] = item["@id"].replace(":2#", ":1#")
    modify_doc(case_dir, "np-002", duplicate_urn)
    expect_rejection(validate_case(case_dir), "重复 URN")
    negative_count += 1

    case_dir = copy_case(base_dir, root, "wrong-urn-sequence")
    def wrong_sequence(doc):
        doc["@id"] = "urn:nanopub:regression-case:3"
        for item in doc["@graph"]:
            item["@id"] = item["@id"].replace(":2#", ":3#")
    modify_doc(case_dir, "np-002", wrong_sequence)
    expect_rejection(validate_case(case_dir), "错误 URN 序号")
    negative_count += 1

    case_dir = copy_case(base_dir, root, "alternate-shell")
    def alternate_shell(doc):
        doc["@graph"] = {item["@id"].rsplit("#", 1)[-1]: item for item in doc["@graph"]}
    modify_doc(case_dir, "np-001", alternate_shell)
    expect_rejection(validate_case(case_dir), "非 canonical graph 外壳")
    negative_count += 1

    for label, bad_id in (("record id 重复", "np-001"), ("record id 不连续", "np-003")):
        case_dir = copy_case(base_dir, root, "bad-record-" + bad_id)
        result_file = os.path.join(case_dir, "result.json")
        result = read_json(result_file)
        result["nanopublications"][1]["id"] = bad_id
        write_json(result_file, result)
        expect_rejection(validate_case(case_dir), label)
        out_dir = os.path.join(case_dir, "rejected-export")
        exported = run_cli(
            [EXPORTER, result_file, "--out-dir", out_dir, "--update-result"], case_dir
        )
        expect_rejection(exported, label + " / export")
        require(not os.path.exists(out_dir), label + ": 失败前不应创建导出目录")
        negative_count += 1

    unverified_dir = os.path.join(root, "valid-unverified")
    os.makedirs(unverified_dir)
    unverified = base_result()
    unverified.pop("jsonld")
    unverified.pop("json_ld")
    unverified["status"] = "partial"
    unverified["status_reason"] = "第二条证据缺失"
    unverified["nanopublications"][1]["status"] = "unverified"
    unverified["nanopublications"][1]["basis"] = "证据缺失，尚不能验证。"
    unverified["nanopublications"][1]["evidence"] = None
    unverified["uncertainties"] = ["np-002 证据缺失"]
    unverified_path = os.path.join(unverified_dir, "result.json")
    write_json(unverified_path, unverified)
    records_only = run_cli([VALIDATOR, "--records-only", unverified_path], unverified_dir)
    expect_success(records_only, "合法 unverified 空证据 / records-only")
    require("警告" in records_only.stderr, "unverified 空证据没有 warning")
    _, final = export_and_validate(unverified_dir, "合法 unverified 空证据")
    require("警告" in final.stderr, "最终质检没有保留 unverified warning")
    unverified_doc = read_json(
        os.path.join(unverified_dir, "nanopubs", "np-002.jsonld")
    )
    evidence_graph = graph(unverified_doc, "evidence")
    require(
        all(key in evidence_graph for key in ("np:evidence_text", "np:evidence_location", "np:evidence_type"))
        and all(evidence_graph[key] == "" for key in ("np:evidence_text", "np:evidence_location", "np:evidence_type")),
        "unverified 空证据未保留 canonical 三键结构",
    )
    return negative_count


def main():
    log = ["Skill CLI 正反回归开始"]
    missing = [path for path in REQUIRED if not os.path.isfile(os.path.join(ROOT, path))]
    if missing:
        print(f"缺失文件: {missing}", file=sys.stderr)
        return 1
    log.append(f"文件盘点: {len(REQUIRED)} 个必需文件全部存在")
    ok, message = check_frontmatter(os.path.join(ROOT, "SKILL.md"))
    require_frontmatter = ok
    if not require_frontmatter:
        print(f"SKILL.md frontmatter 校验失败: {message}", file=sys.stderr)
        return 1
    log.append(f"SKILL.md frontmatter 校验: {message}")
    try:
        with tempfile.TemporaryDirectory(prefix="nanopub-cli-regression-") as temp_dir:
            negative_count = run_regressions(temp_dir)
    except (RegressionFailure, OSError, ValueError) as exc:
        print("\n".join(log), file=sys.stderr)
        print(f"回归失败: {exc}", file=sys.stderr)
        return 1
    log.append("正向通过: 两条完整 record、稳定重跑、合法 unverified 空证据（含 warning）")
    log.append(f"反向通过: {negative_count} 组指定篡改均由真实 CLI 以退出码 1 拒绝")
    log.append("records-only 输出明确不代表 Final；临时目录已清理，未写提交测试产物")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
