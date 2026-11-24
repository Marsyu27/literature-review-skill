#!/usr/bin/env python3
"""可运行的 layout 细化 quickstart；只使用标准库与真实 CLI。

    # 合成真实 bbox 几何（每次使用临时目录，不写提交目录）
    python3 src/layout_quickstart.py

    # 加载自己的 parse_pdf JSON / JSON 几何 fixture
    python3 src/layout_quickstart.py --input /path/blocks.json --workdir /tmp/layout-demo

输出 refined/validation 路径及校验状态。几何 fixture 必须含 source_lines；此
示例不声称已理解数学语义或科学内容。src/reproduce.py 也复用这里的合成几何。
"""
import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def make_block(bid, page, column, kind, lines, order=None, block_type=None):
    source_lines = [{"text": text, "bbox": list(box)} for text, box in lines]
    bbox = [min(x["bbox"][0] for x in source_lines), min(x["bbox"][1] for x in source_lines),
            max(x["bbox"][2] for x in source_lines), max(x["bbox"][3] for x in source_lines)]
    block = {"id": bid, "page": page, "column": column, "order": order,
             "bbox": bbox, "text": "\n".join(x["text"] for x in source_lines),
             "kind": kind, "source_lines": source_lines}
    if block_type:
        block["type"] = block_type
    return block


def build_synthetic_source():
    """两页真实数值几何：首页 title/abstract、两种 caption 位置、figure、公式。"""
    blocks = [
        make_block("h1", 1, None, "header", [("Journal 7", [230, 20, 370, 32])]),
        # 初排故意是整左栏→整右栏，且居中的 title 被错标到右栏。
        make_block("left-intro", 1, 0, "body", [
            ("Left body one starts before every right body line.", [60, 170, 275, 182]),
            ("Left body two keeps its own vertical flow.", [60, 186, 275, 198]),
            ("Left body three has no same-y interleaving.", [60, 202, 275, 214])], 0),
        make_block("table-above-left", 1, 0, "table_candidate", [
            ("A 1.0", [60, 270, 270, 282]), ("B 2.0", [60, 286, 270, 298])], 2),
        make_block("left-middle", 1, 0, "body", [
            ("Left after the first wide table.", [60, 340, 275, 352]),
            ("The second left line remains before right text.", [60, 356, 275, 368])], 3),
        make_block("table-below-left", 1, 0, "table_candidate", [
            ("C 3.0", [60, 410, 270, 422]), ("D 4.0", [60, 426, 270, 438])], 4),
        make_block("formula-middle", 1, 0, "body", [
            ("E = mc² + αβ = 3.14", [70, 610, 270, 626])], 5, "formula"),
        make_block("footer-1", 1, None, "footer", [("Page 1", [280, 770, 320, 782])]),
        make_block("abstract", 1, 0, "body", [
            ("Abstract", [60, 110, 125, 122]),
            ("We retain α = β + 3.14 and every original symbol.", [60, 130, 540, 142])], 1),
        make_block("title", 1, 1, "body", [
            ("A Centered Study of α Transport", [150, 60, 450, 78])], 6),
        make_block("authors", 1, 1, "body", [
            ("A. Author · B. Author", [190, 88, 410, 100])], 7),
        make_block("right-intro", 1, 1, "body", [
            ("Right body one must follow the left column.", [330, 170, 560, 182]),
            ("Right body two must not merge with left rows.", [330, 186, 560, 198]),
            ("Right body three closes this body zone.", [330, 202, 560, 214])], 8),
        make_block("table-above-caption", 1, 1, "body", [
            ("Table 1: Caption above a split wide table α", [130, 250, 285, 262])], 9),
        make_block("table-above-right", 1, 1, "table_candidate", [
            ("α 10", [330, 270, 540, 282]), ("β 20", [330, 286, 540, 298])], 10),
        make_block("right-middle", 1, 1, "body", [
            ("Right after the first wide table.", [330, 340, 560, 352]),
            ("The second right line has symbol γ.", [330, 356, 560, 368])], 11),
        make_block("table-below-right", 1, 1, "table_candidate", [
            ("γ 30", [330, 410, 540, 422]), ("δ 40", [330, 426, 540, 438])], 12),
        make_block("table-below-caption", 1, 1, "body", [
            ("Table 2: Caption below the wide table β", [160, 450, 460, 462])], 13),
        make_block("figure-panel", 1, 1, "body", [
            ("[Figure panel spanning both columns: α β]", [60, 520, 540, 532])], 14),
        make_block("figure-caption", 1, 1, "body", [
            ("Figure 1: Float preserves α and 0.5 units.", [120, 542, 500, 554])], 15),
        make_block("right-formula-row", 1, 1, "body", [
            ("Right body beside the display formula δ = 4.2.", [330, 610, 560, 626])], 16),
        make_block("h2", 2, None, "header", [("Journal 7", [230, 20, 370, 32])]),
        make_block("page2-left", 2, 0, "body", [
            ("Second page left line one.", [60, 70, 275, 82]),
            ("Second page left line two.", [60, 86, 275, 98]),
            ("Second page left line three ε.", [60, 102, 275, 114])], 0),
        make_block("page2-right", 2, 1, "body", [
            ("Second page right line one.", [330, 70, 560, 82]),
            ("Second page right line two.", [330, 86, 560, 98]),
            ("Second page right line three ζ.", [330, 102, 560, 114])], 1),
        make_block("footer-2", 2, None, "footer", [("Page 2", [280, 770, 320, 782])]),
    ]
    tables = []
    for stem, left_rows, right_rows in (
        ("table-above", [["A", "1.0"], ["B", "2.0"]], [["α", "10"], ["β", "20"]]),
        ("table-below", [["C", "3.0"], ["D", "4.0"]], [["γ", "30"], ["δ", "40"]]),
    ):
        for side, rows in (("left", left_rows), ("right", right_rows)):
            block = next(b for b in blocks if b["id"] == stem + "-" + side)
            tables.append({"block_id": block["id"], "page": 1,
                           "rows": ["\t".join(row) for row in rows],
                           "cells": [[[line["bbox"] for line in block["source_lines"][i:i+1]][0]] for i, _ in enumerate(rows)]})
    return {
        "pages": 2, "mode": "layout", "columns": "double", "column_boundary": 300.0,
        "page_layouts": [
            {"page": 1, "columns": "double", "column_boundary": 300.0, "n_cols": 2,
             "order": "left-to-right", "width": 600, "height": 800},
            {"page": 2, "columns": "double", "column_boundary": 300.0, "n_cols": 2,
             "order": "left-to-right", "width": 600, "height": 800},
        ],
        "blocks": blocks, "headers_footers": [
            {"kind": "header", "text": "Journal 7", "pages": [1, 2]}],
        "tables": tables,
        "formulas": [{"id": "(1)", "page": 1, "block_id": "formula-middle",
                      "original": "E = mc² + αβ = 3.14"}],
    }


def check_expected_geometry(refined):
    """只核阅读几何和字符守恒，不断言任何科学语义。"""
    blocks = {b["id"]: b for b in refined["blocks"]}
    assert blocks["title"]["order"] < blocks["left-intro"]["order"]
    assert blocks["abstract"]["order"] < blocks["left-intro"]["order"]
    assert blocks["abstract"]["zone_id"] != blocks["left-intro"]["zone_id"]
    for stem, caption, before in (
        ("table-above", "table-above-caption", True),
        ("table-below", "table-below-caption", False),
    ):
        left, right = blocks[stem + "-left"], blocks[stem + "-right"]
        assert left["zone_id"] == right["zone_id"] == blocks[caption]["zone_id"]
        orders = [left["order"], right["order"], blocks[caption]["order"]]
        assert abs(left["order"] - right["order"]) <= 2
        assert (blocks[caption]["order"] == min(orders)) if before else (blocks[caption]["order"] == max(orders))
        zone = next(z for z in refined["page_zones"] if z["zone_id"] == left["zone_id"])
        assert zone["kind"] == "full_width_float"
    assert blocks["figure-panel"]["zone_id"] == blocks["figure-caption"]["zone_id"]
    assert blocks["formula-middle"]["text"] == "E = mc² + αβ = 3.14"
    formula_unit = next(u for u in refined["reading_units"] if "formula-middle" in u["source_block_ids"])
    assert formula_unit["source_block_ids"] == ["formula-middle"], "不同原始公式不得拼成一个新公式单元"
    # 每个 body_columns zone 都必须完整走完左栏，再走右栏；不能同 y 双线穿插。
    for zone in refined["page_zones"]:
        if zone["kind"] != "body_columns":
            continue
        sides = []
        for bid in zone["source_block_ids"]:
            line = blocks[bid]["source_lines"][0]
            x0, _, x1, _ = line["bbox"]
            sides.append(0 if (x0 + x1) / 2 < 300 else 1)
        assert sides == sorted(sides), (zone["zone_id"], sides)


def run_chain(source_path, workdir):
    os.makedirs(workdir, exist_ok=True)
    refined_path = os.path.join(workdir, "layout.refined.json")
    conservation_path = os.path.join(workdir, "conservation.json")
    validation_path = os.path.join(workdir, "validation.json")
    commands = [
        [sys.executable, os.path.join(ROOT, "scripts", "refine_layout.py"),
         "--input", source_path, "--out", refined_path, "--report", conservation_path],
        [sys.executable, os.path.join(ROOT, "scripts", "validate_layout.py"),
         "--source", source_path, "--result", refined_path, "--report", validation_path],
    ]
    for command in commands:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError("CLI failed (%d): %s\n%s\n%s" %
                               (proc.returncode, " ".join(command), proc.stdout, proc.stderr))
    with open(refined_path, encoding="utf-8") as fh:
        refined = json.load(fh)
    with open(validation_path, encoding="utf-8") as fh:
        validation = json.load(fh)
    return refined_path, validation_path, refined, validation


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="blocks.json 或等价 JSON 几何 fixture")
    parser.add_argument("--workdir", help="输出目录；缺省为自动清理的临时目录")
    args = parser.parse_args(argv)
    if args.workdir:
        os.makedirs(args.workdir, exist_ok=True)
        context = None
        workdir = args.workdir
    else:
        context = tempfile.TemporaryDirectory(prefix="layout-quickstart-")
        workdir = context.name
    try:
        source_path = args.input
        if not source_path:
            source_path = os.path.join(workdir, "synthetic-blocks.json")
            with open(source_path, "w", encoding="utf-8") as fh:
                json.dump(build_synthetic_source(), fh, ensure_ascii=False, indent=2)
        refined_path, validation_path, refined, validation = run_chain(source_path, workdir)
        if not args.input:
            check_expected_geometry(refined)
        print(json.dumps({"refined": refined_path, "validation": validation_path,
                          "validation_status": validation["validation_status"],
                          "blocks": len(refined["blocks"]), "zones": len(refined["page_zones"]),
                          "reading_units": len(refined["reading_units"])}, ensure_ascii=False, indent=2))
        return 0
    finally:
        if context is not None:
            context.cleanup()


if __name__ == "__main__":
    sys.exit(main())
