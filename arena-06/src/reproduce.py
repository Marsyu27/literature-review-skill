#!/usr/bin/env python3
"""Skill 自检：资源盘点 + 实际“索引→校验”正反回归（纯标准库）。

运行: python3 src/reproduce.py
所有论文、索引、结果、报告和 manifest 均写入 tempfile 临时目录，退出时清理，
不在提交目录创建 results/、测试 JSON 或 __pycache__。
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "scripts" / "build_anchor_index.py"
VALIDATE = ROOT / "scripts" / "validate_anchors.py"
REQUIRED = [
    "SKILL.md",
    "README.md",
    "scripts/build_anchor_index.py",
    "scripts/validate_anchors.py",
    "src/reproduce.py",
    "references/paper-card-fields.md",
    "references/section-alignment.md",
    "references/knowledge-extraction.md",
    "references/source-anchoring.md",
    "references/output-schema.md",
    "examples/summary-examples.md",
]

PAPER = """Anchored Paper
Alex Author

This preamble states the scope of the synthetic paper.

1. Introduction
We study whether the anchored method improves the measured outcome.

2. Methods
The method uses a controlled comparison and records every condition.

III.A Experimental Setup
We evaluate the method on the synthetic dataset under a fixed budget.

IV. Experimental Results
Accuracy reaches 0.81 versus 0.79 baseline (p<0.05).
IV. Experimental Results details details details details details details details details details details details details details details details details details

A. Robustness
The robustness check retains the same conditions and reports the limitation.

Conclusion
The findings support the stated conclusion only under the reported conditions.
"""


def check_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False, "缺少 YAML frontmatter"
    end = text.find("\n---", 3)
    if end < 0:
        return False, "frontmatter 未闭合"
    frontmatter = text[3:end]
    complete = "name:" in frontmatter and "description:" in frontmatter
    return complete, "name/description 齐全" if complete else "缺 name 或 description"


def run_command(command, env):
    return subprocess.run(
        [str(part) for part in command],
        cwd=str(ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def section_id(index, title):
    return next(section["id"] for section in index["sections"] if section["title"] == title)


def make_success_result(index):
    preamble = index["sections"][0]
    introduction = section_id(index, "1. Introduction")
    results = section_id(index, "IV. Experimental Results")
    return {
        "case_id": "synthetic-anchor-regression",
        "status": "success",
        "status_reason": "合成论文的所有索引章节均已完成",
        "paper_card": {
            "title": "Anchored Paper",
            "findings": "Accuracy reaches 0.81 versus 0.79 baseline (p<0.05)",
        },
        "paper_card_anchors": [
            {
                "field": "title",
                "source_anchor": f"{preamble['id']} ¶1",
                "quote": "Anchored Paper",
            },
            {
                "field": "findings",
                "source_anchor": f"{results} ¶1",
                "quote": "Accuracy reaches 0.81 versus 0.79 baseline (p<0.05)",
            },
        ],
        "sections": [
            {
                "id": section["id"],
                "title": section["title"],
                "purpose": "依据该节原文记录其内容",
                "method": "不添加原文之外的信息",
                "results": "见该节原文",
                "transition": "按合成论文顺序承接",
                "source_anchor": section["id"],
                "status": "ok",
            }
            for section in index["sections"]
        ],
        "knowledge_points": [
            {
                "id": "kp-001",
                "type": "method",
                "label": "Anchored method",
                "value": "A controlled comparison under recorded conditions",
                "source_anchor": f"{introduction} ¶1",
                "status": "ok",
            }
        ],
        "uncertainties": [],
    }


def main():
    log = ["Skill 自检开始（所有产物仅使用 tempfile）"]
    failures = []
    records = []
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        log.append(f"缺失文件: {missing}")
        print("\n".join(log))
        return 1
    log.append(f"文件盘点: {len(REQUIRED)} 个必需文件全部存在（含功能脚本与 schema）")
    frontmatter_ok, message = check_frontmatter(ROOT / "SKILL.md")
    log.append(f"SKILL.md frontmatter 校验: {message}")
    if not frontmatter_ok:
        print("\n".join(log))
        return 1

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="literature-skill-regression-") as temp_dir:
        temp = Path(temp_dir)
        paper_path = temp / "synthetic-paper.txt"
        index_path = temp / "anchor_index.json"
        paper_path.write_text(PAPER, encoding="utf-8")
        built = run_command([sys.executable, BUILD, "--input", paper_path, "--out", index_path], env)
        records.append({"case": "build_anchor_index", "expected": 0, "exit": built.returncode})
        log.append(f"[build_anchor_index] exit={built.returncode} expected=0")
        if built.returncode != 0:
            failures.append("build_anchor_index")
            log.extend([built.stdout.strip(), built.stderr.strip(), "无法继续回归"])
            print("\n".join(part for part in log if part))
            return 1
        index = json.loads(index_path.read_text(encoding="utf-8"))
        titles = [section["title"] for section in index["sections"]]
        expected_titles = [
            "(preamble)",
            "1. Introduction",
            "2. Methods",
            "III.A Experimental Setup",
            "IV. Experimental Results",
            "A. Robustness",
            "Conclusion",
        ]
        heading_ok = (
            titles == expected_titles
            and isinstance(index.get("warnings"), list)
            and any(w.get("type") == "heading_review" for w in index["warnings"])
            and any(w.get("type") == "heading_rejected" for w in index["warnings"])
        )
        records.append({"case": "heading_forms_and_warnings", "expected": 0, "exit": 0 if heading_ok else 1})
        log.append(f"[heading_forms_and_warnings] exit={0 if heading_ok else 1} expected=0 titles={titles}")
        if not heading_ok:
            failures.append("heading_forms_and_warnings")

        baseline = make_success_result(index)

        def validate_case(name, result, expected, predicate=None):
            result_path = temp / f"{name}.result.json"
            report_path = temp / f"{name}.report.json"
            result_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            proc = run_command([
                sys.executable,
                VALIDATE,
                "--result", result_path,
                "--index", index_path,
                "--report", report_path,
            ], env)
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
            required_report_fields = {
                "index_sections", "result_sections", "missing_sections", "extra_sections",
            }
            valid = proc.returncode == expected and required_report_fields <= set(report)
            if predicate is not None:
                valid = valid and predicate(report)
            records.append({"case": name, "expected": expected, "exit": proc.returncode})
            log.append(
                f"[{name}] exit={proc.returncode} expected={expected} "
                f"report_fields={'ok' if required_report_fields <= set(report) else 'missing'}"
            )
            if not valid:
                failures.append(name)
                log.append(f"  stdout={proc.stdout.strip()}")
                log.append(f"  stderr={proc.stderr.strip()}")

        validate_case(
            "success_full_coverage",
            baseline,
            0,
            lambda report: report["ok"] and not report["missing_sections"] and not report["extra_sections"],
        )

        missing_section = copy.deepcopy(baseline)
        del missing_section["sections"][1]
        validate_case(
            "error_missing_section",
            missing_section,
            1,
            lambda report: bool(report["missing_sections"]),
        )

        forged_paragraph = copy.deepcopy(baseline)
        forged_paragraph["sections"][0]["source_anchor"] = "§1 ¶999"
        validate_case("error_forged_paragraph_id", forged_paragraph, 1)

        changed_quote = copy.deepcopy(baseline)
        changed_quote["paper_card_anchors"][1]["quote"] = "Accuracy reaches 0.99 versus baseline"
        validate_case("error_changed_quote", changed_quote, 1)

        missing_card_anchor = copy.deepcopy(baseline)
        missing_card_anchor["paper_card_anchors"] = [
            item for item in missing_card_anchor["paper_card_anchors"] if item["field"] != "findings"
        ]
        validate_case("error_missing_paper_card_anchor", missing_card_anchor, 1)

        partial = copy.deepcopy(baseline)
        partial["status"] = "partial"
        partial["status_reason"] = "两个章节无法形成独立摘要，以逐节占位保留完整索引覆盖"
        partial["uncertainties"] = ["§2 与 §3 的摘要需人工复核；其余章节和卡片锚点有效"]
        for position in (1, 2):
            sid = partial["sections"][position]["id"]
            partial["sections"][position] = {
                "id": sid,
                "status": "uncertain",
                "reason": "该节未形成独立论点，待依据原文人工复核",
            }
        validate_case(
            "partial_section_placeholders",
            partial,
            0,
            lambda report: report["ok"] and len(report["warnings"]) >= 2 and not report["missing_sections"],
        )

        partial_missing = copy.deepcopy(partial)
        del partial_missing["sections"][1]
        validate_case(
            "error_partial_silent_missing_section",
            partial_missing,
            1,
            lambda report: bool(report["missing_sections"]),
        )

        success_placeholder = copy.deepcopy(baseline)
        success_placeholder["sections"][1] = {
            "id": success_placeholder["sections"][1]["id"],
            "status": "uncertain",
            "reason": "success 中不允许用占位替代完成",
        }
        validate_case("error_success_section_placeholder", success_placeholder, 1)

        extra_section = copy.deepcopy(baseline)
        extra_section["sections"].append({"id": "§999", "source_anchor": "§999", "status": "ok"})
        validate_case(
            "error_extra_section",
            extra_section,
            1,
            lambda report: report["extra_sections"] == ["§999"],
        )

        wrong_own_anchor = copy.deepcopy(baseline)
        wrong_own_anchor["sections"][1]["source_anchor"] = baseline["sections"][0]["id"]
        validate_case("error_section_wrong_own_anchor", wrong_own_anchor, 1)

        manifest = {
            "skill": "literature-summary-structured-notes",
            "challenge_id": "product-arena-06-6d8cf72b",
            "files": REQUIRED,
            "regressions": records,
        }
        (temp / "skill_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    log.append("临时目录已清理；未在提交目录写入测试产物")
    total = len(records)
    passed = sum(record["exit"] == record["expected"] for record in records)
    log.append(f"回归汇总: {passed}/{total} 个退出码符合预期；失败项={failures}")
    print("\n".join(log))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
