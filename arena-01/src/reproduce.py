#!/usr/bin/env python3
"""Skill 自检与真实脚本行为回归（src/reproduce.py，文献翻译）。

运行：python3 src/reproduce.py
所有 case/source/result/report/manifest 均写入 tempfile 临时目录并自动清理；
不在提交目录写测试产物，结束后清理提交目录内 __pycache__。仅依赖标准库。
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED = [
    "SKILL.md",
    "scripts/check_terminology.py",
    "scripts/check_conservation.py",
    "scripts/validate_translation_delivery.py",
    "references/terminology-lock.md",
    "references/terminology.schema.json",
    "references/result.schema.json",
    "references/hedge-strength.md",
    "references/bilingual-alignment.md",
    "references/translation-verification.md",
    "references/output-schema.md",
    "examples/translation-examples.md",
]


def check_frontmatter(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    if not text.startswith("---"):
        return False, "缺少 YAML frontmatter"
    end = text.find("\n---", 3)
    if end < 0:
        return False, "frontmatter 未闭合"
    fm = text[3:end]
    ok = ("name:" in fm) and ("description:" in fm)
    return ok, ("name/description 齐全" if ok else "缺 name 或 description")


def write_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def run_regressions(workdir):
    """通过 CLI subprocess 验证实际退出码，而非复制脚本内部逻辑。"""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    records = []
    failures = []

    def invoke(name, expected, arguments):
        command = [sys.executable] + [os.path.join(ROOT, p) for p in arguments[:1]] + arguments[1:]
        completed = subprocess.run(
            command, cwd=ROOT, env=env, text=True, capture_output=True, check=False
        )
        record = {"name": name, "expected_exit": expected,
                  "actual_exit": completed.returncode, "ok": completed.returncode == expected}
        records.append(record)
        if completed.returncode != expected:
            failures.append(record)
            print(f"FAIL {name}: expected={expected} actual={completed.returncode}")
            if completed.stdout:
                print(completed.stdout)
            if completed.stderr:
                print(completed.stderr)
        return completed

    case_path = os.path.join(workdir, "case.json")
    source_path = os.path.join(workdir, "source-snapshot.txt")
    result_path = os.path.join(workdir, "result.json")
    terms_path = os.path.join(workdir, "terminology.json")
    segments_path = os.path.join(workdir, "segments.json")

    s0 = ("The efficiency improved by 20% at 300 K; see Fig. 2, "
          "$y = \\ln x_i$, and \\(z_0\\).\n")
    t0 = "在 300 K 下，效率提高了 20%；见图2、$y = \\ln x_i$ 和 \\(z_0\\)。"
    s1 = "Equation (3) gives $$E = mc^2$$ and \\[a^2+b^2=c^2\\]."
    t1 = "公式(3)给出 $$E = mc^2$$ 和 \\[a^2+b^2=c^2\\]。"
    snapshot = s0 + s1
    segments = [
        {"id": "§1 ¶1", "source": s0, "target": t0,
         "source_start": 0, "source_end": len(s0),
         "basis": "术语、数字、公式、图表引用已核对", "status": "ok"},
        {"id": "§2 ¶1", "source": s1, "target": t1,
         "source_start": len(s0), "source_end": len(snapshot),
         "basis": "公式与公式编号已核对", "status": "ok"},
    ]
    case = {
        "case_id": "demo",
        "output_contract": {
            "answer": "string",
            "lang": "zh",
            "evidence": {"type": "array"},
            "metadata": {"type": "object"},
        },
    }
    result = {
        "case_id": "demo",
        "status": "success",
        "status_reason": "",
        "source_lang": "en",
        "target_lang": "zh",
        "answer": "完整译文见 segments。",
        "lang": "zh",
        "evidence": ["§1 ¶1", "§2 ¶1"],
        "metadata": {},
        "terminology": [
            {"term": "performance", "aliases": ["efficiency"], "locked": "效率",
             "alternates": ["效能"]}
        ],
        "segments": segments,
        "uncovered_ranges": [],
        "uncertainties": [],
        "tool_commands": [],
    }
    with open(source_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(snapshot)
    write_json(case_path, case)
    write_json(result_path, result)
    write_json(terms_path, result["terminology"])
    write_json(segments_path, segments)

    terminology = ["scripts/check_terminology.py", "--terms", terms_path,
                   "--segments", segments_path]
    conservation = ["scripts/check_conservation.py", "--segments", segments_path]
    invoke("good_terminology", 0, terminology + ["--report", os.path.join(workdir, "term-good.json")])
    invoke("good_en_zh_conservation", 0,
           conservation + ["--report", os.path.join(workdir, "cons-good.json")])

    delivery = ["scripts/validate_translation_delivery.py", "--case", case_path,
                "--source-text", source_path, "--result", result_path]
    invoke("good_full_delivery", 0, delivery + ["--work-segments", segments_path,
           "--report", os.path.join(workdir, "delivery-good.json")])

    # success 缺一段必须失败；完全相同的内容改判 partial 并精确声明缺口可通过。
    missing = copy.deepcopy(result)
    missing["segments"] = missing["segments"][:1]
    del missing["uncovered_ranges"]
    missing_path = os.path.join(workdir, "result-missing.json")
    write_json(missing_path, missing)
    invoke("success_missing_segment_fails", 1,
           ["scripts/validate_translation_delivery.py", "--case", case_path,
            "--source-text", source_path, "--result", missing_path,
            "--report", os.path.join(workdir, "delivery-missing.json")])

    partial = copy.deepcopy(missing)
    partial["status"] = "partial"
    partial["status_reason"] = "§2 未完成；语义人工回核尚未执行。"
    partial["uncovered_ranges"] = [{"source_start": len(s0), "source_end": len(snapshot)}]
    partial["uncertainties"] = ["§2 未翻译", "未做语义人工对照回核"]
    partial_path = os.path.join(workdir, "result-partial.json")
    write_json(partial_path, partial)
    invoke("partial_exact_uncovered_passes", 0,
           ["scripts/validate_translation_delivery.py", "--case", case_path,
            "--source-text", source_path, "--result", partial_path,
            "--report", os.path.join(workdir, "delivery-partial.json")])

    lying_partial = copy.deepcopy(partial)
    lying_partial["uncovered_ranges"] = []
    lying_path = os.path.join(workdir, "result-partial-lie.json")
    write_json(lying_path, lying_partial)
    invoke("partial_hidden_gap_fails", 1,
           ["scripts/validate_translation_delivery.py", "--case", case_path,
            "--source-text", source_path, "--result", lying_path,
            "--report", os.path.join(workdir, "delivery-partial-lie.json")])

    duplicate = copy.deepcopy(result)
    duplicate["segments"][1]["id"] = duplicate["segments"][0]["id"]
    duplicate_path = os.path.join(workdir, "result-duplicate.json")
    write_json(duplicate_path, duplicate)
    invoke("duplicate_id_fails", 1,
           ["scripts/validate_translation_delivery.py", "--case", case_path,
            "--source-text", source_path, "--result", duplicate_path,
            "--report", os.path.join(workdir, "delivery-duplicate.json")])

    drifted_work = copy.deepcopy(segments)
    drifted_work[1]["target"] = "公式(3)给出不同终稿。 $$E = mc^2$$ \\[a^2+b^2=c^2\\]"
    drift_path = os.path.join(workdir, "segments-drift.json")
    write_json(drift_path, drifted_work)
    invoke("work_final_drift_fails", 1, delivery + ["--work-segments", drift_path,
           "--report", os.path.join(workdir, "delivery-drift.json")])

    def conservation_mutation(name, mutate, report_name):
        changed = copy.deepcopy(segments)
        mutate(changed)
        path = os.path.join(workdir, "segments-" + report_name + ".json")
        write_json(path, changed)
        invoke(name, 1, ["scripts/check_conservation.py", "--segments", path,
                         "--report", os.path.join(workdir, "cons-" + report_name + ".json")])

    conservation_mutation(
        "formula_ln_to_lg_fails",
        lambda value: value[0].__setitem__("target", value[0]["target"].replace("\\ln", "\\lg")),
        "ln-lg",
    )
    conservation_mutation(
        "formula_subscript_change_fails",
        lambda value: value[0].__setitem__("target", value[0]["target"].replace("x_i", "x_j")),
        "subscript",
    )
    conservation_mutation(
        "figure_to_table_fails",
        lambda value: value[0].__setitem__("target", value[0]["target"].replace("图2", "表2")),
        "figure-table",
    )
    conservation_mutation(
        "added_twenty_percent_fails",
        lambda value: value[1].__setitem__("target", value[1]["target"] + "另增20%。"),
        "added-20",
    )
    return records, failures


def cleanup_pycache():
    for directory, dirnames, filenames in os.walk(ROOT, topdown=False):
        for dirname in dirnames:
            if dirname == "__pycache__":
                shutil.rmtree(os.path.join(directory, dirname))


def main():
    log = ["Skill 自检与真实行为回归开始"]
    missing = [p for p in REQUIRED if not os.path.exists(os.path.join(ROOT, p))]
    if missing:
        log.append(f"缺失文件: {missing}")
        print("\n".join(log))
        sys.exit(1)
    log.append(f"文件盘点: {len(REQUIRED)} 个必需文件全部存在")

    ok, msg = check_frontmatter(os.path.join(ROOT, "SKILL.md"))
    log.append(f"SKILL.md frontmatter 校验: {msg}")
    if not ok:
        print("\n".join(log))
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="translation-skill-") as workdir:
        records, failures = run_regressions(workdir)
        for record in records:
            log.append(f"{record['name']}: exit={record['actual_exit']} "
                       f"(expected={record['expected_exit']})")
        manifest = {
            "skill": "scientific-literature-translation",
            "challenge_id": "product-arena-01-5a9928c1",
            "files": REQUIRED,
            "regressions": records,
            "artifacts": "temporary_directory_only",
        }
        manifest_path = os.path.join(workdir, "skill_manifest.json")
        write_json(manifest_path, manifest)
        log.append("manifest 与全部测试报告仅写入临时目录，已自动清理")
    cleanup_pycache()
    log.append(f"行为回归: {len(records) - len(failures)}/{len(records)} 符合预期退出码")
    print("\n".join(log))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
