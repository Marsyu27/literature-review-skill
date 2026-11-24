#!/usr/bin/env python3
"""PDF 版面机械解析（scripts/parse_pdf.py）

用 pdftotext -bbox-layout 拿真实逐词坐标，机械完成栏判定、阅读顺序、
页眉页脚剔除与表格候选检出，产出 blocks.json 作为 LLM 语义标注的底稿。
LLM 不再手算 bbox XML。

流程：
  1. 无 pdftotext → 退出码 2，输出 {"error":"pdftotext unavailable","mode":"text-only"}；
  2. pdftotext -bbox-layout 解析 XHTML，抽取逐词 xMin/yMin/xMax/yMax/text；
  3. 分栏：正文区（剔除页面上下各 8%）按词 xMin 直方图判双峰，并要求词覆盖
     直方图存在真实栏间谷底（连续空带）→ 双栏，取谷底中心为分界；
     阅读顺序 = 先左栏自上而下再右栏；单栏直接自上而下；
  4. 页眉页脚：规范化文本行在 ≥50%（至少 2 页）页面顶部/底部（各 8% 带）重复出现，
     且该文本不同时出现在正文区 → 标 header/footer 并从正文流剔除；
  5. 组块：先按栏分词，词成行（yMin 容差），行成块（垂直间距阈值或行首 x 跳变），
     每块给 id/page/column/order/bbox/text/kind（body/header/footer/table_candidate）；
  6. 表格候选：块内 ≥2 行共享 ≥3 个对齐 x 起始列（每列覆盖 ≥60% 行）且对齐列
     覆盖 ≥50% 词 → table_candidate，附 rows（TSV）与单元格 bbox。

输出 blocks.json：
  {"pages", "mode":"layout", "columns", "column_boundary",
   "blocks": [...], "headers_footers": [...], "tables": [...]}

用法：python3 scripts/parse_pdf.py --pdf paper.pdf --out blocks.json
退出码：0 成功；2 pdftotext 缺失或执行失败（输出 text-only 降级 JSON）。
Python 仅用标准库；外部依赖仅 poppler-utils 的 pdftotext。
"""
import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

BAND = 0.08            # 页面上下各 8% 为页眉/页脚候选带
LINE_Y_TOL = 3.0       # 词成行的 yMin 容差（pt）
BIN_W = 4.0            # xMin 直方图 bin 宽（pt）
PEAK_MASK = 30.0       # 主峰两侧屏蔽宽度（pt），用于找第二峰
GUTTER_MIN = 8.0       # 栏间谷底最小宽度（pt）
CELL_X_TOL = 6.0       # 表格对齐列的 x 聚类容差（pt）
BLOCK_X_SHIFT = 20.0   # 行首 x 跳变超过此值即开新块（pt）


def localname(tag):
    return tag.rsplit("}", 1)[-1]


def extract_pages(xhtml_path):
    """解析 bbox-layout XHTML → [{width,height,words:[{t,x0,y0,x1,y1}]}]。"""
    tree = ET.parse(xhtml_path)
    pages = []
    for el in tree.iter():
        if localname(el.tag) != "page":
            continue
        page = {
            "width": float(el.get("width", "0")),
            "height": float(el.get("height", "0")),
            "words": [],
        }
        for w in el.iter():
            if localname(w.tag) != "word":
                continue
            text = (w.text or "").strip()
            if not text:
                continue
            page["words"].append({
                "t": text,
                "x0": float(w.get("xMin")), "y0": float(w.get("yMin")),
                "x1": float(w.get("xMax")), "y1": float(w.get("yMax")),
            })
        pages.append(page)
    return pages


def words_to_lines(words):
    """词按 yMin 容差聚成行，行内按 x0 排序。"""
    lines = []
    for w in sorted(words, key=lambda w: (w["y0"], w["x0"])):
        for ln in lines:
            if abs(w["y0"] - ln["y0"]) <= LINE_Y_TOL:
                ln["words"].append(w)
                ln["y0"] = min(ln["y0"], w["y0"])
                ln["y1"] = max(ln["y1"], w["y1"])
                break
        else:
            lines.append({"y0": w["y0"], "y1": w["y1"], "words": [w]})
    for ln in lines:
        ln["words"].sort(key=lambda w: w["x0"])
        ln["x0"] = ln["words"][0]["x0"]
        ln["x1"] = max(w["x1"] for w in ln["words"])
        ln["text"] = " ".join(w["t"] for w in ln["words"])
    return sorted(lines, key=lambda ln: (ln["y0"], ln["x0"]))


def norm_key(text):
    """页眉页脚规范化：小写、数字→#、压缩空白。"""
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", text.lower())).strip()


def detect_columns(body_words, page_width):
    """词 xMin 直方图双峰 + 词覆盖谷底 → ("double", boundary) / ("single", None)。"""
    if not body_words:
        return "single", None
    lo = min(w["x0"] for w in body_words)
    hi = max(w["x1"] for w in body_words)
    if hi - lo < 0.3 * page_width:
        return "single", None
    # 1) 词覆盖直方图找最宽连续空带（栏间谷底）
    obw = 2.0
    nb = int((hi - lo) / obw) + 1
    occ = [0] * nb
    for w in body_words:
        a = max(0, int((w["x0"] - lo) / obw))
        b = min(nb - 1, int((w["x1"] - lo) / obw))
        for i in range(a, b + 1):
            occ[i] += 1
    best_start, best_len, cur_start, cur_len = 0, 0, 0, 0
    for i in range(nb):
        if occ[i] == 0:
            if cur_len == 0:
                cur_start = i
            cur_len += 1
            if cur_len > best_len:
                best_start, best_len = cur_start, cur_len
        else:
            cur_len = 0
    gutter_w = best_len * obw
    boundary = lo + (best_start + best_len / 2) * obw
    left = [w for w in body_words if (w["x0"] + w["x1"]) / 2 < boundary]
    frac = len(left) / len(body_words)
    gutter_ok = (gutter_w >= GUTTER_MIN
                 and 0.1 <= frac <= 0.9
                 and boundary - lo >= 0.15 * page_width
                 and hi - boundary >= 0.15 * page_width)
    # 2) 词 xMin 直方图判双峰
    xs = [w["x0"] for w in body_words]
    x0, x1 = min(xs), max(xs)
    nbins = int((x1 - x0) / BIN_W) + 1
    hist = [0] * nbins
    for x in xs:
        hist[int((x - x0) / BIN_W)] += 1
    p1 = max(range(nbins), key=lambda i: hist[i])
    c1 = x0 + (p1 + 0.5) * BIN_W
    p2, second = None, 0
    for i in range(nbins):
        ci = x0 + (i + 0.5) * BIN_W
        if abs(ci - c1) > PEAK_MASK and hist[i] > second:
            p2, second = i, hist[i]
    bimodal = (p2 is not None
               and hist[p2] >= 0.2 * hist[p1]
               and abs(x0 + (p2 + 0.5) * BIN_W - c1) >= 0.15 * page_width)
    if gutter_ok and bimodal:
        return "double", boundary
    return "single", None


def mark_headers_footers(n_pages, band_lines_per_page, body_keys):
    """重复出现于 ≥50%（≥2 页）同侧带内、且不在正文区出现的行 → header/footer。"""
    found = {"header": {}, "footer": {}}
    if n_pages < 2:
        return found
    need = max(2, (n_pages + 1) // 2)
    hits = {"header": {}, "footer": {}}
    for pi, entries in enumerate(band_lines_per_page):
        for kind, ln in entries:
            key = norm_key(ln["text"])
            if not key or key in body_keys:
                continue
            rec = hits[kind].setdefault(key, {"text": ln["text"], "pages": set()})
            rec["pages"].add(pi + 1)
    for kind in ("header", "footer"):
        for key, rec in hits[kind].items():
            if len(rec["pages"]) >= need:
                found[kind][key] = {"text": rec["text"], "pages": sorted(rec["pages"])}
    return found


def lines_to_blocks(lines, med_h):
    """行成块：垂直间距超阈值或行首 x 跳变超阈值即开新块。"""
    blocks = []
    for ln in lines:
        if blocks:
            prev = blocks[-1]
            gap = ln["y0"] - prev["y1"]
            shift = abs(ln["x0"] - prev["lines"][-1]["x0"])
            if gap <= 1.1 * med_h and shift <= BLOCK_X_SHIFT:
                prev["lines"].append(ln)
                prev["x0"] = min(prev["x0"], ln["x0"]); prev["x1"] = max(prev["x1"], ln["x1"])
                prev["y0"] = min(prev["y0"], ln["y0"]); prev["y1"] = max(prev["y1"], ln["y1"])
                continue
        blocks.append({
            "x0": ln["x0"], "y0": ln["y0"], "x1": ln["x1"], "y1": ln["y1"],
            "lines": [ln],
        })
    return blocks


def detect_table(block):
    """块内 ≥2 行共享 ≥3 个对齐 x 起始列（每列覆盖 ≥60% 行）且对齐列覆盖 ≥50% 词
    → 表格候选，返回 {"rows":[TSV], "cells"} 或 None。"""
    lines = block["lines"]
    n = len(lines)
    if n < 2:
        return None
    # 正文段落判别：行均词数高且词间距小 → 两端对齐正文，不是表格
    wpl = sorted(len(ln["words"]) for ln in lines)
    med_words = wpl[n // 2] if n % 2 else (wpl[n // 2 - 1] + wpl[n // 2]) / 2
    gaps = [b["x0"] - a["x1"] for ln in lines for a, b in zip(ln["words"], ln["words"][1:])]
    med_gap = statistics.median(gaps) if gaps else 0.0
    if med_words >= 8 and med_gap < 10.0:
        return None
    xs = sorted(w["x0"] for ln in lines for w in ln["words"])
    clusters = []  # [center, count]
    for x in xs:
        if clusters and x - clusters[-1][0] <= CELL_X_TOL:
            clusters[-1][1] += 1
            m = clusters[-1][1]
            clusters[-1][0] += (x - clusters[-1][0]) / m
        else:
            clusters.append([x, 1])
    need_rows = max(2, -(-6 * n // 10))  # ≥60% 行，向上取整
    aligned = []
    for center, _ in clusters:
        rows = {li for li, ln in enumerate(lines)
                for w in ln["words"] if abs(w["x0"] - center) <= CELL_X_TOL}
        if len(rows) >= need_rows:
            aligned.append(center)
    if len(aligned) < 3:
        return None
    total_words = sum(len(ln["words"]) for ln in lines)
    covered_words = sum(1 for ln in lines for w in ln["words"]
                        if any(abs(w["x0"] - c) <= CELL_X_TOL for c in aligned))
    if total_words == 0 or covered_words / total_words < 0.5:
        return None
    rows, cells = [], []
    for ln in lines:
        row_cells, row_boxes = [], []
        for center in aligned:
            ws = [w for w in ln["words"] if abs(w["x0"] - center) <= CELL_X_TOL]
            row_cells.append(" ".join(w["t"] for w in ws))
            row_boxes.append([
                round(min(w["x0"] for w in ws), 1), round(min(w["y0"] for w in ws), 1),
                round(max(w["x1"] for w in ws), 1), round(max(w["y1"] for w in ws), 1),
            ] if ws else None)
        covered = {id(w) for w in ln["words"]
                   if any(abs(w["x0"] - c) <= CELL_X_TOL for c in aligned)}
        rest = [w for w in ln["words"] if id(w) not in covered]
        if rest:
            row_cells.append(" ".join(w["t"] for w in rest))
            row_boxes.append([
                round(min(w["x0"] for w in rest), 1), round(min(w["y0"] for w in rest), 1),
                round(max(w["x1"] for w in rest), 1), round(max(w["y1"] for w in rest), 1),
            ])
        rows.append("\t".join(row_cells))
        cells.append(row_boxes)
    return {"rows": rows, "cells": cells}


def emit_text_only(out_path, error):
    payload = {"error": error, "mode": "text-only"}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        print(text)
    print(f"parse_pdf: {error}（降级 mode=text-only）", file=sys.stderr)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description="PDF 版面机械解析（pdftotext -bbox-layout → blocks.json）")
    ap.add_argument("--pdf", required=True, help="输入 PDF 路径")
    ap.add_argument("--out", default=None, help="blocks.json 输出路径（缺省 stdout）")
    args = ap.parse_args()

    if shutil.which("pdftotext") is None:
        emit_text_only(args.out, "pdftotext unavailable")

    with tempfile.TemporaryDirectory() as tmp:
        xhtml = os.path.join(tmp, "out.xhtml")
        proc = subprocess.run(
            ["pdftotext", "-bbox-layout", args.pdf, xhtml],
            capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(xhtml):
            emit_text_only(args.out,
                           "pdftotext failed: " + (proc.stderr or "").strip()[:200])
        try:
            pages = extract_pages(xhtml)
        except ET.ParseError as exc:
            emit_text_only(args.out, f"bbox XHTML parse failed: {exc}")

    n_pages = len(pages)
    page_w = max((p["width"] for p in pages), default=0) or 1

    # 正文区（剔除上下各 8%）词集合 → 栏判定
    body_words_all = []
    for p in pages:
        for w in p["words"]:
            yc = (w["y0"] + w["y1"]) / 2
            if BAND * p["height"] <= yc <= (1 - BAND) * p["height"]:
                body_words_all.append(w)
    columns, boundary = detect_columns(body_words_all, page_w)

    def col_of(x):
        if columns == "single" or boundary is None:
            return 0
        return 0 if x < boundary else 1

    # 逐页：带内行（页宽）与正文词（分栏）分别成行
    band_lines_per_page = []   # [(kind, line)] 供页眉页脚判定
    page_col_lines = []        # [{0:[...], 1:[...], "hf":[(kind,line)], "med_h":h}]
    for p in pages:
        band_words, col_words = [], {0: [], 1: []}
        for w in p["words"]:
            yc = (w["y0"] + w["y1"]) / 2
            if yc < BAND * p["height"] or yc > (1 - BAND) * p["height"]:
                band_words.append(w)
            else:
                col_words[col_of(w["x0"])].append(w)
        band_entries = []
        for ln in words_to_lines(band_words):
            yc = (ln["y0"] + ln["y1"]) / 2
            kind = "header" if yc < BAND * p["height"] else "footer"
            band_entries.append((kind, ln))
        band_lines_per_page.append(band_entries)
        heights = [ln["y1"] - ln["y0"]
                   for c in (0, 1) for ln in words_to_lines(col_words[c])]
        page_col_lines.append({
            "cols": {c: words_to_lines(col_words[c]) for c in (0, 1)},
            "band": band_entries,
            "med_h": statistics.median(heights) if heights else 10.0,
        })

    # 正文区规范化行集合（页眉页脚判定的排除项：正文里出现的文本不是页眉页脚）
    body_keys = set()
    for rec in page_col_lines:
        for c in (0, 1):
            for ln in rec["cols"][c]:
                body_keys.add(norm_key(ln["text"]))
    hf = mark_headers_footers(n_pages, band_lines_per_page, body_keys)
    hf_keys = {k: set(v.keys()) for k, v in hf.items()}

    blocks_out, tables_out = [], []
    order = 0
    for pi, rec in enumerate(page_col_lines):
        med_h = rec["med_h"]
        page_blocks = []  # (sort_col, y0, kind, block)
        # 带内行：命中重复判定 → header/footer 块；否则归并入正文行流
        spill = {0: [], 1: []}
        for kind, ln in rec["band"]:
            key = norm_key(ln["text"])
            if key in hf_keys.get(kind, set()):
                page_blocks.append((-1, ln["y0"], kind, {
                    "x0": ln["x0"], "y0": ln["y0"], "x1": ln["x1"], "y1": ln["y1"],
                    "lines": [ln],
                }))
            else:
                spill[col_of(ln["x0"])].append(ln)
        n_cols = 2 if columns == "double" else 1
        for c in range(n_cols):
            lines = sorted(rec["cols"][c] + spill[c],
                           key=lambda ln: (ln["y0"], ln["x0"]))
            for blk in lines_to_blocks(lines, med_h):
                page_blocks.append((c, blk["y0"], "body", blk))
        page_blocks.sort(key=lambda t: (t[0], t[1]))
        for c, _, kind, blk in page_blocks:
            table = detect_table(blk) if kind == "body" else None
            if table:
                kind = "table_candidate"
            bid = f"b{len(blocks_out) + 1}"
            entry = {
                "id": bid,
                "page": pi + 1,
                "column": None if kind in ("header", "footer") else c,
                "order": None if kind in ("header", "footer") else order,
                "bbox": [round(blk["x0"], 1), round(blk["y0"], 1),
                         round(blk["x1"], 1), round(blk["y1"], 1)],
                "text": "\n".join(ln["text"] for ln in blk["lines"]),
                "kind": kind,
            }
            if kind not in ("header", "footer"):
                order += 1
            blocks_out.append(entry)
            if table:
                tables_out.append({"block_id": bid, "page": pi + 1,
                                   "rows": table["rows"], "cells": table["cells"]})

    hf_out = [
        {"kind": kind, "text": rec["text"], "pages": rec["pages"]}
        for kind in ("header", "footer") for rec in hf[kind].values()
    ]
    result = {
        "pages": n_pages,
        "mode": "layout",
        "columns": columns,
        "column_boundary": round(boundary, 1) if boundary else None,
        "blocks": blocks_out,
        "headers_footers": hf_out,
        "tables": tables_out,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"blocks.json 已写入 {args.out}：pages={n_pages} columns={columns} "
              f"blocks={len(blocks_out)} tables={len(tables_out)} "
              f"headers_footers={len(hf_out)}")
    else:
        print(text)
    sys.exit(0)


if __name__ == "__main__":
    main()
