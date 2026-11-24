#!/usr/bin/env python3
"""Skill 自检入口（src/reproduce.py）

本脚本不参与评测案例运行，仅用于：
1. 校验 SKILL.md 的 YAML frontmatter（name/description 存在且非空）；
2. 盘点 Skill 全部资源文件；
3. 用示例输入自检 scripts/build_slides.py，产出可编辑 PPTX；
4. 把上述结果写入 execution/results/skill_manifest.json 与 stdout（即 run.log）。

运行: python3 src/reproduce.py
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED = [
    "SKILL.md",
    "references/layout-reading-order.md",
    "references/table-structure.md",
    "references/formula-preservation.md",
    "references/ocr-fallback.md",
    "references/output-schema.md",
    "scripts/parse_pdf.py",
    "scripts/parse_ocr_tsv.py",
    "scripts/build_slides.py",
    "examples/parse-examples.md",
]


def check_frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if not text.startswith("---"):
        return False, "SKILL.md 缺少 YAML frontmatter"
    end = text.find("\n---", 3)
    if end < 0:
        return False, "SKILL.md frontmatter 未闭合"
    fm = text[3:end]
    ok = ("name:" in fm) and ("description:" in fm)
    return ok, ("name/description 齐全" if ok else "frontmatter 缺少 name 或 description")


def main():
    log = []
    log.append("Skill 自检开始")

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

    # 自检 build_slides.py
    sample = {
        "document": {
            "title": "Skill Self-Test Paper",
            "authors": "Self-test",
            "abstract": "Verifies build_slides produces an editable PPTX.",
            "sections": [{"number": "1", "title": "Introduction", "page": 1, "summary": "Scope."}],
            "references": [{"id": "[1]", "text": "Placeholder.", "page": 2}],
        },
        "tables": [{"id": "Table 1", "page": 1, "caption": "Self-test", "html": "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"}],
        "formulas": [{"id": "(1)", "page": 1, "latex": "$E=mc^2$"}],
        "figures": [{"id": "Fig. 1", "page": 1, "caption": "Self-test"}],
    }
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    sample_path = os.path.join(ROOT, "results", "self_test_input.json")
    with open(sample_path, "w", encoding="utf-8") as fh:
        json.dump(sample, fh, ensure_ascii=False, indent=2)

    pptx_out = os.path.join(ROOT, "results", "self_test_slides.pptx")
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "build_slides.py"), sample_path, pptx_out],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        log.append(f"build_slides.py 自检失败: {r.stderr[:400]}")
        print("\n".join(log))
        sys.exit(1)
    log.append("build_slides.py 自检通过，已生成可编辑 PPTX: " + pptx_out)
    if r.stdout.strip():
        log.append("build_slides 输出: " + r.stdout.strip().splitlines()[-1])

    manifest = {
        "skill": "pdf-document-parsing",
        "challenge_id": "product-arena-08-3027d350",
        "files": REQUIRED,
        "self_test": {
            "input": "results/self_test_input.json",
            "output_pptx": "results/self_test_slides.pptx",
            "status": "ok",
        },
        "notes": "Skill 以 SKILL.md 为入口，references/ 为规则，scripts/build_slides.py 为可选可编辑 PPTX 生成器。",
    }
    manifest_path = os.path.join(ROOT, "results", "skill_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    log.append("已写入 results/skill_manifest.json")

    print("\n".join(log))


if __name__ == "__main__":
    main()
