#!/usr/bin/env python3
"""用原始 line bbox 做纵向 zone 细化，不改变任何源块文字。

用法：
    python scripts/refine_layout.py --input blocks.json \
        --out layout.refined.json --report conservation.json

输入必须来自当前 parse_pdf.py（每个块含 source_lines），或提供等价的真实
JSON 几何。这里不做翻译、公式 LaTeX 生成或科学语义判断。双栏正文的顺序是在
**每一个纵向 body zone 内**左栏 y→右栏 y，而不是整页一次分左右栏。

保守边界：
* 只有真实 line 跨过栏界，或左右 table_candidate 至少两行同 y 对齐，才作
  为通栏 seeds；Table/Figure 字样只帮助扩展邻近表格行，不能凭空创建通栏。
* 同 y、跨栏、扩展间隙等阈值均由本页 source_lines 的中位线高/正常行距导出。
* 证据不足时保留 ordinary body_columns，并写 uncertainties/warnings。
* 一个原 block 只进入一个 zone、一个 reading_unit part；不在本步骤拆字或改字。
"""
import argparse
import copy
import hashlib
import json
import os
import re
import statistics
import sys

CAPTION_RE = re.compile(r"^\s*(table|tab\.|figure|fig\.|表|图)\s*[\dIVXivx一二三四五六七八九十]*\s*[:：.]?", re.I)
ABSTRACT_RE = re.compile(r"^\s*(?:abstract|summary|摘要)(?:\s|[:：.\-—]|$)", re.I)


class LayoutError(ValueError):
    pass


def norm(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def sha(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def bbox_union(boxes):
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def valid_bbox(box):
    try:
        vals = [float(v) for v in box]
    except (TypeError, ValueError):
        return False
    return len(vals) == 4 and vals[0] <= vals[2] and vals[1] <= vals[3]


def collect_blocks(payload, base_dir):
    """读取 inline blocks 或 blocks_files；拒绝静默漏块/重复 ID。"""
    blocks = [copy.deepcopy(b) for b in payload.get("blocks", [])]
    for rel in payload.get("blocks_files", []):
        path = rel if os.path.isabs(rel) else os.path.join(base_dir, rel)
        with open(path, encoding="utf-8") as fh:
            part = json.load(fh)
        if isinstance(part, list):
            chunk = part
        else:
            chunk = part.get("blocks")
        if not isinstance(chunk, list):
            raise LayoutError("blocks_files 项缺少数组 blocks: %s" % rel)
        blocks.extend(copy.deepcopy(chunk))
    return blocks


def load_source(path):
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    if payload.get("mode") == "text-only":
        raise LayoutError("text-only 没有真实 bbox，不能运行 zone 细化")
    blocks = collect_blocks(payload, os.path.dirname(os.path.abspath(path)))
    if not isinstance(blocks, list):
        raise LayoutError("输入 blocks 必须是数组")
    if not blocks:
        raise LayoutError("没有可追溯源 blocks；空文字层应按 OCR/partial 处理")
    ids = [b.get("id") for b in blocks]
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids):
        raise LayoutError("源 block ID 必须非空且唯一")
    for b in blocks:
        lines = b.get("source_lines")
        if not isinstance(lines, list) or not lines:
            raise LayoutError("block %s 缺少 source_lines；请先用当前 parse_pdf.py" % b["id"])
        if not valid_bbox(b.get("bbox")):
            raise LayoutError("block %s bbox 无效" % b["id"])
        for line in lines:
            if not isinstance(line.get("text"), str) or not valid_bbox(line.get("bbox")):
                raise LayoutError("block %s 含无效 source_lines text/bbox" % b["id"])
        if norm("\n".join(l["text"] for l in lines)) != norm(b.get("text", "")):
            raise LayoutError("block %s 的 text 与 source_lines 不守恒" % b["id"])
    return payload, blocks


def metrics(records):
    heights = [r["line"]["bbox"][3] - r["line"]["bbox"][1] for r in records]
    med_h = statistics.median(heights) if heights else 1.0
    med_h = max(med_h, 0.1)
    pitches = []
    by_block = {}
    for rec in records:
        by_block.setdefault(rec["block_id"], []).append(rec["line"])
    for group in by_block.values():
        group.sort(key=lambda l: (l["bbox"][1], l["bbox"][0]))
        for a, b in zip(group, group[1:]):
            d = b["bbox"][1] - a["bbox"][1]
            if 0.2 * med_h <= d <= 3.5 * med_h:
                pitches.append(d)
    pitch = statistics.median(pitches) if pitches else 1.4 * med_h
    pitch = max(pitch, med_h)
    return {
        "line_h": med_h,
        "pitch": pitch,
        "same_y": max(0.2 * pitch, 0.25 * med_h),
        "x_tol": 0.75 * med_h,
        "merge_gap": 1.25 * pitch,
        "float_expand": 2.0 * pitch,
    }


def line_side(line, boundary):
    if boundary is None:
        return 0
    box = line["bbox"]
    return 0 if (box[0] + box[2]) / 2 < boundary else 1


def crosses(line, boundary, x_tol):
    if boundary is None:
        return False
    box = line["bbox"]
    return box[0] < boundary - x_tol and box[2] > boundary + x_tol


def block_interval(block):
    box = block["bbox"]
    return box[1], box[3]


def stable_body_onset(records, boundary, m):
    """找第一对及其后续重复同 y 双栏正文行；标题/摘要/表格候选不作 rows。"""
    if boundary is None:
        return None
    sides = {0: [], 1: []}
    for rec in records:
        block = rec["block"]
        if block.get("kind") != "body" or block.get("is_table"):
            continue
        if block.get("type") in ("title", "abstract", "figure_caption", "formula"):
            continue
        line = rec["line"]
        text = line.get("text", "")
        if CAPTION_RE.match(text) or ABSTRACT_RE.match(text) or crosses(line, boundary, m["x_tol"]):
            continue
        sides[line_side(line, boundary)].append(rec)
    for side in sides.values():
        side.sort(key=lambda r: (r["line"]["bbox"][1], r["line"]["bbox"][0]))
    pairs = []
    used_right = set()
    for left in sides[0]:
        candidates = [r for r in sides[1] if id(r) not in used_right and
                      abs(r["line"]["bbox"][1] - left["line"]["bbox"][1]) <= m["same_y"]]
        if not candidates:
            continue
        right = min(candidates, key=lambda r: abs(r["line"]["bbox"][1] - left["line"]["bbox"][1]))
        used_right.add(id(right))
        pairs.append((left, right))
    pairs.sort(key=lambda p: min(p[0]["line"]["bbox"][1], p[1]["line"]["bbox"][1]))
    for i in range(len(pairs) - 1):
        a, b = pairs[i], pairs[i + 1]
        ay = min(x["line"]["bbox"][1] for x in a)
        by = min(x["line"]["bbox"][1] for x in b)
        if 0 < by - ay <= 2.5 * m["pitch"]:
            return ay
    return None


def make_records(blocks):
    records = []
    for index, block in enumerate(blocks):
        if block.get("kind") in ("header", "footer"):
            continue
        for line_index, line in enumerate(block["source_lines"]):
            records.append({"block": block, "block_id": block["id"], "block_index": index,
                            "line_index": line_index, "line": line})
    return records


def pair_table_seeds(records, boundary, m):
    """左右表格候选同 y ≥2 行才给跨栏几何证据，返回 seeds 与已配对块。"""
    by_block = {}
    for rec in records:
        if rec["block"].get("is_table") and not crosses(rec["line"], boundary, m["x_tol"]):
            by_block.setdefault(rec["block_id"], []).append(rec)
    left = {bid: rs for bid, rs in by_block.items()
            if any(line_side(r["line"], boundary) == 0 for r in rs)}
    right = {bid: rs for bid, rs in by_block.items()
             if any(line_side(r["line"], boundary) == 1 for r in rs)}
    seeds, paired_blocks, paired_rows = [], set(), 0
    for lbid, lrs in left.items():
        for rbid, rrs in right.items():
            if lbid == rbid:
                continue
            matches = 0
            ys = []
            for lr in lrs:
                if line_side(lr["line"], boundary) != 0:
                    continue
                candidates = [rr for rr in rrs if line_side(rr["line"], boundary) == 1 and
                              abs(rr["line"]["bbox"][1] - lr["line"]["bbox"][1]) <= m["same_y"]]
                if candidates:
                    matches += 1
                    rr = min(candidates, key=lambda r: abs(r["line"]["bbox"][1] - lr["line"]["bbox"][1]))
                    ys.extend([lr["line"]["bbox"][1], rr["line"]["bbox"][1]])
            if matches >= 2:
                blocks = [lrs[0]["block"], rrs[0]["block"]]
                y0 = min(block_interval(b)[0] for b in blocks)
                y1 = max(block_interval(b)[1] for b in blocks)
                seeds.append({"y0": y0, "y1": y1, "ids": {lbid, rbid},
                              "caption": any(CAPTION_RE.match(l["text"]) for b in blocks for l in b["source_lines"]),
                              "table": True, "cross": False})
                paired_blocks.update((lbid, rbid))
                paired_rows += matches
    return seeds, paired_blocks, paired_rows


def float_seeds(records, excluded, boundary, m):
    """生成可靠跨栏 seeds，并将 caption 与邻近表格 piece 合并。"""
    active = [r for r in records if r["block_id"] not in excluded]
    seeds, paired_blocks, paired_rows = pair_table_seeds(active, boundary, m)
    cross_ids = set()
    for rec in active:
        line = rec["line"]
        if not crosses(line, boundary, m["x_tol"]):
            continue
        cross_ids.add(rec["block_id"])
        seeds.append({"y0": line["bbox"][1], "y1": line["bbox"][3],
                      "ids": {rec["block_id"]}, "caption": bool(CAPTION_RE.match(line["text"])),
                      "table": bool(rec["block"].get("is_table")), "cross": True})

    def gap(a, b):
        return max(a["y0"], b["y0"]) - min(a["y1"], b["y1"])

    # 同一源块/相交区间必须合并；连续真实 cross lines 也可属于同一浮动体。
    changed = True
    while changed:
        changed = False
        for i in range(len(seeds)):
            if changed:
                break
            for j in range(i + 1, len(seeds)):
                a, b = seeds[i], seeds[j]
                g = gap(a, b)
                if (a["ids"] & b["ids"] or g <= m["merge_gap"] or
                    (g <= m["float_expand"] and (a["caption"] or b["caption"]) and
                     (a["table"] or b["table"]))):
                    a["y0"] = min(a["y0"], b["y0"]); a["y1"] = max(a["y1"], b["y1"])
                    a["ids"].update(b["ids"])
                    a["caption"] = a["caption"] or b["caption"]
                    a["table"] = a["table"] or b["table"]
                    a["cross"] = a["cross"] or b["cross"]
                    seeds.pop(j)
                    changed = True
                    break

    # caption 可在上或下：只向邻近 table-cell/table_candidate 块扩展，不向普通正文扩展。
    table_blocks = {r["block_id"]: r["block"] for r in active if r["block"].get("is_table")}
    changed = True
    while changed:
        changed = False
        for seed in seeds:
            if not (seed["caption"] or seed["table"]):
                continue
            for bid, block in table_blocks.items():
                if bid in seed["ids"]:
                    continue
                y0, y1 = block_interval(block)
                g = max(seed["y0"], y0) - min(seed["y1"], y1)
                if g <= m["float_expand"]:
                    seed["ids"].add(bid)
                    seed["y0"] = min(seed["y0"], y0); seed["y1"] = max(seed["y1"], y1)
                    seed["table"] = True
                    changed = True

    # 双侧重建已证明是宽表时，邻近、单栏中的短 caption 也可附着；
    # caption 样式只是在已有可靠 table 几何上辅助，不会单独产生 float。
    caption_blocks = {r["block_id"]: r["block"] for r in active
                      if any(CAPTION_RE.match(line["text"]) for line in r["block"]["source_lines"])}
    for seed in seeds:
        if not seed["table"]:
            continue
        for bid, block in caption_blocks.items():
            if bid in seed["ids"]:
                continue
            y0, y1 = block_interval(block)
            g = max(seed["y0"], y0) - min(seed["y1"], y1)
            if g <= m["float_expand"]:
                seed["ids"].add(bid)
                seed["y0"] = min(seed["y0"], y0); seed["y1"] = max(seed["y1"], y1)
                seed["caption"] = True
    return seeds, cross_ids, paired_blocks, paired_rows


def make_seed(kind, ids, blocks_by_id, **flags):
    boxes = [blocks_by_id[bid]["bbox"] for bid in ids]
    box = bbox_union(boxes)
    seed = {"kind": kind, "ids": set(ids), "y0": box[1], "y1": box[3]}
    seed.update(flags)
    return seed


def process_page(page, blocks, layout, source_table_ids):
    boundary = layout.get("column_boundary")
    if layout.get("n_cols", 1) != 2:
        boundary = None
    by_id = {b["id"]: b for b in blocks}
    original_index = {b["id"]: i for i, b in enumerate(blocks)}
    for b in blocks:
        b["is_table"] = b.get("kind") == "table_candidate" or b["id"] in source_table_ids
    records = make_records(blocks)
    m = metrics(records)
    warnings = []
    special = []
    excluded = set()

    # 只有首页用“稳定双栏正文”识别前置标题/摘要；其它页顶部可能是普通续段。
    onset = stable_body_onset(records, boundary, m) if page == 1 else None
    if onset is not None:
        pre = []
        for b in blocks:
            if b.get("kind") in ("header", "footer"):
                continue
            y0, y1 = block_interval(b)
            has_caption = any(CAPTION_RE.match(l["text"]) for l in b["source_lines"])
            if y0 < onset and not b.get("is_table") and not has_caption:
                pre.append(b)
                excluded.add(b["id"])
                if y1 > onset + m["same_y"]:
                    warnings.append("页 1 block %s 横跨首个稳定正文行，整块保守留在 header/abstract zone" % b["id"])
        pre.sort(key=lambda b: (b["bbox"][1], b["bbox"][0], original_index[b["id"]]))
        marker = None
        for i, b in enumerate(pre):
            if any(ABSTRACT_RE.match(l["text"]) for l in b["source_lines"]):
                marker = i
                break
        if marker is not None:
            if marker:
                special.append(make_seed("preamble", [b["id"] for b in pre[:marker]], by_id))
            special.append(make_seed("abstract", [b["id"] for b in pre[marker:]], by_id))
        elif pre:
            special.append(make_seed("preamble", [b["id"] for b in pre], by_id))
    elif page == 1 and boundary is not None:
        warnings.append("页 1 未找到重复同 y 的稳定双栏正文；不强行声明页首为通栏 preamble")

    floats, cross_ids, paired_blocks, paired_rows = float_seeds(records, excluded, boundary, m)
    for seed in floats:
        seed["kind"] = "full_width_float" if seed["caption"] or seed["table"] else "full_width"
        special.append(seed)
        excluded.update(seed["ids"])

    # 单侧 table/caption 字样不能替代 full-width 证据。
    for b in blocks:
        if b["id"] in excluded or b.get("kind") in ("header", "footer"):
            continue
        if b.get("is_table") and boundary is not None and b["id"] not in paired_blocks:
            warnings.append("页 %d block %s 是表格候选，但缺可靠跨栏/双侧重建行，保留 ordinary-column-zone" % (page, b["id"]))
        elif any(CAPTION_RE.match(l["text"]) for l in b["source_lines"]) and boundary is not None:
            warnings.append("页 %d block %s 仅 caption 样式不足以判通栏，保留 ordinary-column-zone" % (page, b["id"]))

    for kind in ("header", "footer"):
        ids = [b["id"] for b in blocks if b.get("kind") == kind]
        if ids:
            special.append(make_seed(kind, ids, by_id))
            excluded.update(ids)

    special.sort(key=lambda z: (z["y0"], z["y1"], z["kind"]))
    groups = []
    body_left = [b for b in blocks if b["id"] not in excluded]

    def add_body(members):
        if not members:
            return
        kind = "body_columns" if boundary is not None else "body_single"
        groups.append(make_seed(kind, [b["id"] for b in members], by_id))

    for seed in special:
        before = []
        remain = []
        for b in body_left:
            box = b["bbox"]
            center = (box[1] + box[3]) / 2
            (before if center < seed["y0"] else remain).append(b)
        add_body(before)
        groups.append(seed)
        body_left = remain
    add_body(body_left)
    groups.sort(key=lambda z: (z["y0"], z["y1"], 0 if z["kind"].startswith("body") else 1))

    zones, streams_by_zone = [], {}
    for zi, group in enumerate(groups, 1):
        zone_id = "p%d-z%02d" % (page, zi)
        members = [by_id[bid] for bid in group["ids"]]
        kind = group["kind"]
        if kind == "body_columns":
            side_lists = {0: [], 1: []}
            for b in members:
                votes = {0: 0.0, 1: 0.0}
                for line in b["source_lines"]:
                    side = line_side(line, boundary)
                    votes[side] += max(0.0, line["bbox"][2] - line["bbox"][0])
                side = 0 if votes[0] >= votes[1] else 1
                side_lists[side].append(b)
            streams = []
            for side in (0, 1):
                ordered = sorted(side_lists[side], key=lambda b: (b["bbox"][1], b["bbox"][0], original_index[b["id"]]))
                if ordered:
                    streams.append(ordered)
            ordered_blocks = [b for stream in streams for b in stream]
        else:
            ordered_blocks = sorted(members, key=lambda b: (b["bbox"][1], b["bbox"][0], original_index[b["id"]]))
            streams = [ordered_blocks] if ordered_blocks else []
        zones.append({"zone_id": zone_id, "page": page, "kind": kind,
                      "bbox": bbox_union([b["bbox"] for b in ordered_blocks]),
                      "source_block_ids": [b["id"] for b in ordered_blocks],
                      "source_unit_ids": [], "order": zi - 1})
        streams_by_zone[zone_id] = streams
    diagnostics = dict(m)
    diagnostics.update({"stable_body_onset": onset, "paired_table_rows": paired_rows,
                        "cross_line_blocks": sorted(cross_ids)})
    return zones, streams_by_zone, warnings, diagnostics


def is_formula_block(block, formula_ids):
    return (block["id"] in formula_ids or block.get("kind") == "formula" or
            block.get("type") in ("formula", "display_formula"))


def build_units(zones, streams_by_zone, blocks_by_id, formula_ids):
    units = []
    block_zone = {}
    block_unit = {}
    for zone in zones:
        for stream_index, stream in enumerate(streams_by_zone[zone["zone_id"]], 1):
            chunk = []

            def emit(part_blocks):
                if not part_blocks:
                    return
                unit_id = "%s-u%02d" % (zone["zone_id"], len(zone["source_unit_ids"]) + 1)
                parts = []
                for b in part_blocks:
                    block_zone[b["id"]] = zone["zone_id"]
                    block_unit[b["id"]] = unit_id
                    parts.append({"source_block_id": b["id"], "source_unit_id": unit_id,
                                  "part_index": 0, "part_count": 1,
                                  "text": b["text"], "hash": sha(b["text"]),
                                  "bbox": copy.deepcopy(b["bbox"])})
                text = "\n".join(p["text"] for p in parts)
                unit = {"unit_id": unit_id, "page": zone["page"], "zone_id": zone["zone_id"],
                        "source_block_ids": [b["id"] for b in part_blocks],
                        "source_unit_ids": [unit_id], "source_parts": parts,
                        "text": text, "text_sha256": sha(text),
                        "bbox": bbox_union([b["bbox"] for b in part_blocks])}
                units.append(unit)
                zone["source_unit_ids"].append(unit_id)

            for b in stream:
                if is_formula_block(b, formula_ids):
                    emit(chunk)
                    chunk = []
                    emit([b])
                else:
                    chunk.append(b)
            emit(chunk)
    return units, block_zone, block_unit


def canonical_digest(blocks):
    canonical = [{"id": b["id"], "page": b.get("page"), "kind": b.get("kind"),
                  "text": norm(b.get("text", ""))} for b in blocks]
    return sha(json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def refine(payload, source_blocks):
    source_blocks = copy.deepcopy(source_blocks)
    result = {k: copy.deepcopy(v) for k, v in payload.items() if k not in ("blocks", "blocks_files", "page_zones", "reading_units", "conservation_report")}
    final_blocks = copy.deepcopy(source_blocks)
    by_id = {b["id"]: b for b in final_blocks}
    layouts = {int(p["page"]): p for p in payload.get("page_layouts", []) if "page" in p}
    pages = sorted({b.get("page") for b in final_blocks})
    source_table_ids = {t.get("block_id") for t in payload.get("tables", []) if t.get("block_id")}
    formula_ids = {f.get("block_id") or f.get("source_block_id") for f in payload.get("formulas", [])}
    formula_ids.discard(None)
    all_zones, all_streams, warnings, page_diagnostics = [], {}, [], {}
    for page in pages:
        page_blocks = [b for b in final_blocks if b.get("page") == page]
        layout = layouts.get(page)
        if layout is None:
            # 只有完全旧式单栏输入可兼容；部分页配置缺失/混合版式不得猜成单栏。
            if payload.get("page_layouts") or payload.get("n_cols") == 2 or payload.get("columns") in ("double", "mixed"):
                raise LayoutError("页 %s 缺 page_layouts/column_boundary" % page)
            layout = {"page": page, "n_cols": 1, "column_boundary": None}
        if layout.get("n_cols") == 2 and layout.get("column_boundary") is None:
            raise LayoutError("页 %s 声明双栏但 column_boundary 为 null" % page)
        zones, streams, page_warnings, diagnostics = process_page(page, page_blocks, layout, source_table_ids)
        # process_page 可能处理了多个 zone，重新编号须在页内保持连续（其自身已完成）。
        all_zones.extend(zones)
        all_streams.update(streams)
        warnings.extend(page_warnings)
        page_diagnostics[str(page)] = diagnostics

    units, block_zone, block_unit = build_units(all_zones, all_streams, by_id, formula_ids)
    order_by_id = {}
    global_order = 0
    for zone in all_zones:
        for bid in zone["source_block_ids"]:
            order_by_id[bid] = global_order
            global_order += 1
    for b in final_blocks:
        b["order"] = order_by_id[b["id"]]
        b["zone_id"] = block_zone[b["id"]]
        b["source_unit_ids"] = [block_unit[b["id"]]]
        b.pop("is_table", None)

    source_ids = [b["id"] for b in source_blocks]
    final_ids = [b["id"] for b in final_blocks]
    exact_text = all(next(f for f in final_blocks if f["id"] == b["id"]).get("text") == b.get("text")
                     for b in source_blocks)
    part_ids = [p["source_block_id"] for u in units for p in u["source_parts"]]
    parts_exact = (len(part_ids) == len(set(part_ids)) and set(part_ids) == set(source_ids)
                   and all(p["text"] == source_blocks[source_ids.index(p["source_block_id"])]["text"]
                           and p["hash"] == sha(p["text"])
                           for u in units for p in u["source_parts"]))
    units_rebuild = all(u["text"] == "\n".join(p["text"] for p in u["source_parts"]) for u in units)
    report = {
        "ok": (len(source_ids) == len(final_ids) == len(set(final_ids)) and set(source_ids) == set(final_ids)
               and exact_text and parts_exact and units_rebuild),
        "status": "complete" if not warnings else "complete_with_warnings",
        "source_block_count": len(source_ids), "result_block_count": len(final_ids),
        "reading_unit_count": len(units), "zone_count": len(all_zones),
        "source_character_count": sum(len(b.get("text", "")) for b in source_blocks),
        "result_character_count": sum(len(b.get("text", "")) for b in final_blocks),
        "source_normalized_text_sha256": canonical_digest(source_blocks),
        "result_normalized_text_sha256": canonical_digest(sorted(final_blocks, key=lambda b: source_ids.index(b["id"]))),
        "missing_block_ids": sorted(set(source_ids) - set(final_ids)),
        "duplicate_block_ids": sorted({i for i in final_ids if final_ids.count(i) > 1}),
        "unmapped_block_ids": [], "gaps": [], "warnings": warnings,
        "geometry_diagnostics": page_diagnostics,
        "checks": {"source_line_texts_preserved": exact_text, "original_tables_copied": result.get("tables", []) == payload.get("tables", []),
                   "whole_block_source_parts": parts_exact, "unit_text_rebuilt_from_parts": units_rebuild,
                   "semantic_success_claimed": False},
    }
    result.update({"blocks": final_blocks, "page_zones": all_zones, "reading_units": units,
                   "conservation_report": report, "unmapped_block_ids": [], "gaps": [],
                   "uncertainties": list(dict.fromkeys(list(payload.get("uncertainties", [])) + warnings))})
    return result, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="parse_pdf.py 的 blocks.json")
    parser.add_argument("--out", required=True, help="layout.refined.json")
    parser.add_argument("--report", required=True, help="conservation.json")
    args = parser.parse_args(argv)
    try:
        payload, blocks = load_source(args.input)
        refined, report = refine(payload, blocks)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("refine_layout: %s" % exc, file=sys.stderr)
        return 2
    for path, data in ((args.out, refined), (args.report, report)):
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    print("refine_layout: blocks=%d zones=%d units=%d warnings=%d" %
          (len(refined["blocks"]), len(refined["page_zones"]), len(refined["reading_units"]), len(report["warnings"])))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
