#!/usr/bin/env python3
"""Skill 轻量自检：真实 CLI + 临时目录，不写 results/manifest/PPTX 到提交树。

    python3 src/reproduce.py

覆盖 frontmatter/资源、OCR TSV（不调用 tesseract）、build_slides 临时 PPTX、
合成真实 layout 几何的 refine/validate 正反例，以及 blocks_files。若系统已有
pdftotext，还运行一个不下载字体/不联网的最小 PDF smoke test；否则明确跳过。
"""
import copy
import csv
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import layout_quickstart  # noqa: E402

REQUIRED = [
    "README.md", "SKILL.md",
    "references/layout-reading-order.md", "references/table-structure.md",
    "references/formula-preservation.md", "references/ocr-fallback.md",
    "references/output-schema.md", "scripts/parse_pdf.py",
    "scripts/refine_layout.py", "scripts/validate_layout.py",
    "scripts/parse_ocr_tsv.py", "scripts/build_slides.py",
    "src/layout_quickstart.py", "examples/parse-examples.md",
]


def command(args, timeout=120):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=ROOT)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def write_json(path, value):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2)


def check_frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    require(text.startswith("---"), "SKILL.md 缺少 YAML frontmatter")
    first_end = text.find("\n---", 3)
    require(first_end >= 0, "SKILL.md frontmatter 未闭合")
    fm = text[3:first_end]
    require("name:" in fm and "description:" in fm, "frontmatter 缺 name/description")


def check_ocr(workdir):
    # 真实 TSV 字段，无 tesseract 依赖；空词被过滤，行置信度按面积加权。
    fields = ["level", "page_num", "block_num", "par_num", "line_num", "word_num",
              "left", "top", "width", "height", "conf", "text"]
    rows = [
        ["5", 1, 1, 1, 1, 1, 0, 0, 10, 10, 90, "Alpha"],
        ["5", 1, 1, 1, 1, 2, 10, 0, 10, 10, 50, "beta"],
        ["5", 1, 1, 1, 1, 3, 20, 0, 10, 10, 90, "   "],
        ["5", 1, 1, 1, 2, 1, 0, 20, 10, 10, -1, "unknown"],
    ]
    tsv = os.path.join(workdir, "ocr.tsv")
    with open(tsv, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(fields)
        writer.writerows(rows)
    out = os.path.join(workdir, "ocr.json")
    proc = command([sys.executable, "scripts/parse_ocr_tsv.py", "--tsv", tsv, "--out", out])
    require(proc.returncode == 0, proc.stdout + proc.stderr)
    data = json.load(open(out, encoding="utf-8"))
    require(len(data["words"]) == 3 and len(data["lines"]) == 2, "OCR 空词过滤错误")
    require(data["lines"][0]["text"] == "Alpha beta", "OCR 行文本错误")
    require(math.isclose(data["lines"][0]["confidence"], 70.0), "OCR 面积加权置信度错误")
    require(data["lines"][1]["confidence"] is None, "未知 OCR confidence 必须为 null")


def check_slides(workdir):
    sample = {
        "document": {"title": "Skill Self-Test Paper", "authors": "Self-test",
                     "abstract": "Temporary editable PPTX self-test.",
                     "sections": [{"number": "1", "title": "Introduction", "page": 1, "summary": "Scope."}],
                     "references": [{"id": "[1]", "text": "Placeholder.", "page": 2}]},
        "tables": [{"id": "Table 1", "page": 1, "caption": "Self-test",
                    "html": "<table><tr><td>1</td><td>2</td></tr></table>"}],
        "formulas": [{"id": "(1)", "page": 1, "latex": "$E=mc^2$"}],
        "figures": [{"id": "Fig. 1", "page": 1, "caption": "Self-test"}],
    }
    source = os.path.join(workdir, "slides-input.json")
    pptx = os.path.join(workdir, "temporary-self-test.pptx")
    write_json(source, sample)
    proc = command([sys.executable, "scripts/build_slides.py", source, pptx])
    require(proc.returncode == 0 and os.path.getsize(pptx) > 100, proc.stdout + proc.stderr)
    with open(pptx, "rb") as fh:
        require(fh.read(2) == b"PK", "PPTX 不是 OOXML ZIP")


def minimal_pdf(path):
    """写单页 ASCII PDF；Helvetica 是 PDF base-14 引用，不加载/下载系统字体。"""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length 63 >>\nstream\nBT /F1 10 Tf 72 720 Td (Fixture alpha 3.14 and beta.) Tj ET\nendstream",
    ]
    # Length 按实际 stream 字节重写，避免手工数字成为隐性假设。
    stream = b"BT /F1 10 Tf 72 720 Td (Fixture alpha 3.14 and beta.) Tj ET\n"
    objects[4] = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream)
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(("%d 0 obj\n" % i).encode("ascii"))
        data.extend(obj + b"\nendobj\n")
    xref = len(data)
    data.extend(("xref\n0 %d\n" % (len(objects) + 1)).encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(("%010d 00000 n \n" % offset).encode("ascii"))
    data.extend(("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" %
                 (len(objects) + 1, xref)).encode("ascii"))
    with open(path, "wb") as fh:
        fh.write(data)


def check_real_pdftotext(workdir):
    if shutil.which("pdftotext") is None:
        return "skipped (pdftotext unavailable)"
    pdf = os.path.join(workdir, "minimal.pdf")
    out = os.path.join(workdir, "real-pdftotext-blocks.json")
    minimal_pdf(pdf)
    proc = command([sys.executable, "scripts/parse_pdf.py", "--pdf", pdf, "--out", out])
    require(proc.returncode == 0, proc.stdout + proc.stderr)
    data = json.load(open(out, encoding="utf-8"))
    require(data["mode"] == "layout" and data["blocks"], "真实 pdftotext fixture 无 blocks")
    for block in data["blocks"]:
        require(block.get("source_lines"), "parse_pdf 未附加 source_lines")
        joined = "\n".join(line["text"] for line in block["source_lines"])
        require(joined == block["text"], "source_lines/block.text 不一致")
    require("3.14" in " ".join(b["text"] for b in data["blocks"]), "真实 fixture 数字丢失")
    return "ok"


def validate_case(source, candidate, workdir, name, expected):
    candidate_path = os.path.join(workdir, name + ".json")
    report_path = os.path.join(workdir, name + ".report.json")
    write_json(candidate_path, candidate)
    proc = command([sys.executable, "scripts/validate_layout.py", "--source", source,
                    "--result", candidate_path, "--report", report_path])
    require(proc.returncode == expected,
            "%s: expected rc=%d got %d\n%s%s" % (name, expected, proc.returncode, proc.stdout, proc.stderr))
    with open(report_path, encoding="utf-8") as fh:
        report = json.load(fh)
    if expected:
        require(report["errors"] and report["success"] is False, name + " 未报告明确错误")
    return report


def check_layout(workdir):
    source = os.path.join(workdir, "synthetic-blocks.json")
    write_json(source, layout_quickstart.build_synthetic_source())
    _, _, refined, validation = layout_quickstart.run_chain(source, workdir)
    require(validation["success"] is True and validation["validation_status"] == "valid", "baseline validator 非 success")
    layout_quickstart.check_expected_geometry(refined)
    require(validation["source_normalized_text_sha256"] == validation["result_normalized_text_sha256"], "normalized hash 不守恒")
    require(validation["source_word_count"] == validation["result_word_count"], "字数不守恒")
    require(validation["source_character_count"] == validation["result_character_count"], "字符数不守恒")

    semantic_success = copy.deepcopy(refined)
    semantic_success.update({"status": "success", "status_reason": "",
        "document": {"title": "A Centered Study of α Transport",
                     "abstract": "Abstract We retain α = β + 3.14 and every original symbol."},
        "document_evidence": {
            "title": {"block_ids": ["title"], "text": "A Centered Study of α Transport"},
            "abstract": {"block_ids": ["abstract"],
                         "text": "Abstract We retain α = β + 3.14 and every original symbol."},
            "formulas": [{"id": "(1)", "block_id": "formula-middle",
                          "original": "E = mc² + αβ = 3.14"}]}})
    validate_case(source, semantic_success, workdir, "semantic-evidence-complete", 0)

    # partial 明示 OCR 缺口 + 一个 reading-unit 未映射 footer：rc0，但绝不报 success。
    partial = copy.deepcopy(refined)
    uid = next(b["source_unit_ids"][0] for b in partial["blocks"] if b["id"] == "footer-1")
    partial["reading_units"] = [u for u in partial["reading_units"] if u["unit_id"] != uid]
    for zone in partial["page_zones"]:
        zone["source_unit_ids"] = [x for x in zone["source_unit_ids"] if x != uid]
    partial.update({"status": "partial", "status_reason": "OCR unavailable; footer disclosed unmapped",
                    "uncertainties": ["OCR unavailable for scanned insert"],
                    "unmapped_block_ids": ["footer-1"],
                    "gaps": [{"block_id": "footer-1", "reason": "OCR unavailable; explicitly unmapped"}]})
    report = validate_case(source, partial, workdir, "partial-disclosed", 0)
    require(report["validation_status"] == "partial" and report["success"] is False and report["warnings"], "partial 不得静默 success")

    # 每个反例都从完整 refined 复制，确保 validator 不是仅比较 ID 数量。
    mutations = []

    lost = copy.deepcopy(refined)
    lost["blocks"] = [b for b in lost["blocks"] if b["id"] != "left-intro"]
    mutations.append(("lost-block", lost))

    duplicate = copy.deepcopy(refined)
    duplicate["blocks"].append(copy.deepcopy(duplicate["blocks"][0]))
    mutations.append(("duplicate-block", duplicate))

    deleted_text = copy.deepcopy(refined)
    next(b for b in deleted_text["blocks"] if b["id"] == "left-intro")["text"] = ""
    mutations.append(("deleted-block-text", deleted_text))

    changed_unit = copy.deepcopy(refined)
    next(u for u in changed_unit["reading_units"] if "authors" in u["source_block_ids"])["text"] += "\nFABRICATED"
    mutations.append(("unit-text-differs-from-parts", changed_unit))

    missing_part = copy.deepcopy(refined)
    unit = next(u for u in missing_part["reading_units"] if "authors" in u["source_block_ids"])
    unit["source_parts"] = [p for p in unit["source_parts"] if p["source_block_id"] != "authors"]
    mutations.append(("missing-source-part", missing_part))

    wrong_context = copy.deepcopy(refined)
    first, second = wrong_context["reading_units"][1:3]
    first["source_parts"], second["source_parts"] = second["source_parts"], first["source_parts"]
    mutations.append(("swapped-unit-context", wrong_context))

    wrong_evidence = copy.deepcopy(refined)
    wrong_evidence["document_evidence"] = {"title": {
        "block_ids": ["left-intro"], "text": "A Centered Study of α Transport"}}
    mutations.append(("wrong-document-evidence", wrong_evidence))

    changed_cells = copy.deepcopy(refined)
    changed_cells["tables"][0]["cells"][0][0][0] += 99
    mutations.append(("changed-table-cell-bbox", changed_cells))

    for name, candidate in mutations:
        validate_case(source, candidate, workdir, name, 1)

    # blocks_files 按页拆分：完整 coverage 必须成功；不是只看 inline 抽样。
    split = copy.deepcopy(refined)
    split["blocks"] = []
    split["blocks_files"] = ["final-part-1.json", "final-part-2.json"]
    for page in (1, 2):
        write_json(os.path.join(workdir, "final-part-%d.json" % page),
                   {"part": page, "of": 2,
                    "blocks": [b for b in refined["blocks"] if b["page"] == page]})
    split_report = validate_case(source, split, workdir, "blocks-files-complete", 0)
    require(split_report["result_block_count"] == len(refined["blocks"]), "blocks_files 漏计")

    # source 侧也支持 blocks_files。
    split_source = copy.deepcopy(refined)
    original_source = layout_quickstart.build_synthetic_source()
    split_source["blocks"] = []
    split_source["blocks_files"] = ["source-part-1.json", "source-part-2.json"]
    for page in (1, 2):
        write_json(os.path.join(workdir, "source-part-%d.json" % page),
                   {"part": page, "of": 2,
                    "blocks": [b for b in original_source["blocks"] if b["page"] == page]})
    source_parts_path = os.path.join(workdir, "source-with-parts.json")
    write_json(source_parts_path, split_source)
    report_path = os.path.join(workdir, "source-parts-validation.json")
    proc = command([sys.executable, "scripts/validate_layout.py", "--source", source_parts_path,
                    "--result", os.path.join(workdir, "layout.refined.json"), "--report", report_path])
    require(proc.returncode == 0, proc.stdout + proc.stderr)

    # 单侧 caption + 每侧仅一行 cells 不构成可靠宽表证据：保留 ordinary columns 并披露。
    uncertain = layout_quickstart.build_synthetic_source()
    for bid in ("table-above-left", "table-above-right"):
        block = next(b for b in uncertain["blocks"] if b["id"] == bid)
        block["source_lines"] = block["source_lines"][:1]
        block["text"] = block["source_lines"][0]["text"]
        block["bbox"] = copy.deepcopy(block["source_lines"][0]["bbox"])
        table = next(t for t in uncertain["tables"] if t["block_id"] == bid)
        table["rows"] = table["rows"][:1]
        table["cells"] = table["cells"][:1]
    uncertain_dir = os.path.join(workdir, "uncertain")
    os.makedirs(uncertain_dir)
    uncertain_source = os.path.join(uncertain_dir, "blocks.json")
    write_json(uncertain_source, uncertain)
    _, _, uncertain_refined, _ = layout_quickstart.run_chain(uncertain_source, uncertain_dir)
    left = next(b for b in uncertain_refined["blocks"] if b["id"] == "table-above-left")
    left_zone = next(z for z in uncertain_refined["page_zones"] if z["zone_id"] == left["zone_id"])
    require(left_zone["kind"] == "body_columns", "不足证据不应猜成 full_width_float")
    require(any("表格候选" in warning for warning in uncertain_refined["conservation_report"]["warnings"]),
            "ordinary-column fallback 必须有 warning")
    return {"blocks": len(refined["blocks"]), "zones": len(refined["page_zones"]),
            "units": len(refined["reading_units"]), "negative_cases": len(mutations),
            "conservative_uncertain_case": "ok"}


def main():
    missing = [p for p in REQUIRED if not os.path.isfile(os.path.join(ROOT, p))]
    require(not missing, "缺失文件: %s" % missing)
    check_frontmatter(os.path.join(ROOT, "SKILL.md"))
    with tempfile.TemporaryDirectory(prefix="pdf-skill-reproduce-") as workdir:
        check_ocr(workdir)
        check_slides(workdir)
        layout_summary = check_layout(workdir)
        pdf_status = check_real_pdftotext(workdir)
    require(not os.path.exists(os.path.join(ROOT, "results")), "自检不得创建提交树 results/")
    require(not os.path.exists(os.path.join(ROOT, "execution")), "自检不得创建提交树 execution/")
    print("Skill 自检通过")
    print("frontmatter/resources: ok (%d required files)" % len(REQUIRED))
    print("OCR TSV weighted confidence: ok (no tesseract invocation)")
    print("build_slides: ok (temporary PPTX only)")
    print("layout refine/validate: %s" % json.dumps(layout_summary, ensure_ascii=False))
    print("real pdftotext source_lines fixture: " + pdf_status)
    print("临时目录已清理；未生成 results/manifest/PPTX 到提交目录")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("自检失败: %s" % exc, file=sys.stderr)
        sys.exit(1)
