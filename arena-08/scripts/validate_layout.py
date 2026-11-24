#!/usr/bin/env python3
"""从磁盘独立核查 source → refined/final-result 的块与 reading_unit 守恒。

用法：
    python scripts/validate_layout.py --source blocks.json \
        --result layout.refined.json --report report.json

退出 0 表示所声明的 complete/partial 状态通过检查；partial 会在报告中写
success=false 与 warnings。退出 1 表示守恒/回链失败。它不是语义正确性证明。

支持根级或 layout/refined_layout 内嵌的 page_zones/reading_units，以及相对
JSON 所在目录解析的 blocks_files。当前 refine 的 source_parts 是完整原块，因此
每个源块必须恰好出现一次；禁止用旧 parts 配合被篡改的 unit.text。
"""
import argparse
import copy
import hashlib
import json
import math
import os
import re
import sys


def norm(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def sha(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def collect_blocks(payload, base_dir, errors, label):
    inline = payload.get("blocks", [])
    if not isinstance(inline, list):
        errors.append("%s.blocks 必须是数组" % label)
        inline = []
    blocks = copy.deepcopy(inline)
    files = payload.get("blocks_files", [])
    if not isinstance(files, list):
        errors.append("%s.blocks_files 必须是路径数组" % label)
        files = []
    for item in files:
        if not isinstance(item, str) or not item:
            errors.append("%s.blocks_files 含无效路径" % label)
            continue
        path = item if os.path.isabs(item) else os.path.join(base_dir, item)
        try:
            part = load_json(path)
        except (OSError, ValueError) as exc:
            errors.append("无法读取 %s blocks_files %s: %s" % (label, item, exc))
            continue
        chunk = part if isinstance(part, list) else part.get("blocks")
        if not isinstance(chunk, list):
            errors.append("%s blocks_files %s 缺少数组 blocks" % (label, item))
            continue
        blocks.extend(copy.deepcopy(chunk))
    return blocks


def boxes_equal(a, b):
    try:
        return len(a) == len(b) == 4 and all(math.isclose(float(x), float(y), abs_tol=1e-6) for x, y in zip(a, b))
    except (TypeError, ValueError):
        return False


def union(boxes):
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def canonical_digest(blocks):
    canonical = [{"id": b.get("id"), "page": b.get("page"), "kind": b.get("kind"),
                  "text": norm(b.get("text", ""))} for b in blocks]
    return sha(json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def select_geometry(result, base_dir, errors):
    geometry = result
    if not isinstance(result.get("reading_units"), list) or not isinstance(result.get("page_zones"), list):
        for key in ("layout", "refined_layout", "layout_refined"):
            candidate = result.get(key)
            if isinstance(candidate, dict) and isinstance(candidate.get("reading_units"), list):
                geometry = candidate
                break
    blocks_container = result if ("blocks" in result or "blocks_files" in result) else geometry
    blocks = collect_blocks(blocks_container, base_dir, errors, "result")
    # 如果根与内嵌 layout 都带 blocks，二者不可暗中分叉。
    if geometry is not result and ("blocks" in geometry or "blocks_files" in geometry) and blocks_container is result:
        embedded = collect_blocks(geometry, base_dir, errors, "result.layout")
        root_map = {b.get("id"): b for b in blocks}
        embedded_map = {b.get("id"): b for b in embedded}
        if set(root_map) != set(embedded_map):
            errors.append("根 blocks 与内嵌 layout.blocks 的 ID 覆盖不一致")
        else:
            for bid, b in embedded_map.items():
                other = root_map[bid]
                if norm(b.get("text", "")) != norm(other.get("text", "")) or b.get("zone_id") != other.get("zone_id"):
                    errors.append("根/内嵌 block %s 的文本或 zone 不一致" % bid)
    return geometry, blocks


def disclosed_ids(document):
    ids = set(document.get("unmapped_block_ids", []) or [])
    gaps = document.get("gaps", []) or []
    gap_ids = set()
    for gap in gaps:
        if isinstance(gap, dict):
            if isinstance(gap.get("block_id"), str):
                gap_ids.add(gap["block_id"])
            for key in ("block_ids", "unmapped_block_ids"):
                if isinstance(gap.get(key), list):
                    gap_ids.update(x for x in gap[key] if isinstance(x, str))
    return ids, gap_ids


def check_document_evidence(result, final_by_id, part_owner, errors):
    evidence = result.get("document_evidence")
    document = result.get("document", {}) or {}
    status = result.get("status")
    if status == "success":
        if norm(document.get("title", "")) and not (isinstance(evidence, dict) and evidence.get("title")):
            errors.append("success 已给出 document.title，但 document_evidence.title 缺失")
        if norm(document.get("abstract", "")) and not (isinstance(evidence, dict) and evidence.get("abstract")):
            errors.append("success 已给出 document.abstract，但 document_evidence.abstract 缺失")
        captions = [x for key in ("tables", "figures") for x in result.get(key, []) or []
                    if norm(x.get("caption", ""))]
        formulas = [x for x in result.get("formulas", []) or [] if norm(x.get("original", "") or x.get("latex", ""))]
        if captions and not (isinstance(evidence, dict) and evidence.get("captions")):
            errors.append("success 已解析 caption，但 document_evidence.captions 缺失")
        if formulas and not (isinstance(evidence, dict) and evidence.get("formulas")):
            errors.append("success 已解析 formula，但 document_evidence.formulas 缺失")
    if evidence is None:
        return
    if not isinstance(evidence, dict):
        errors.append("document_evidence 必须是对象")
        return
    for key in ("title", "abstract"):
        if key in evidence and not isinstance(evidence[key], dict):
            errors.append("document_evidence.%s 必须是含 block_ids 的对象" % key)
    for key in ("captions", "formulas"):
        if key in evidence and not isinstance(evidence[key], (list, dict)):
            errors.append("document_evidence.%s 必须是证据记录数组" % key)

    def records_for(key):
        value = evidence.get(key, [])
        return [value] if isinstance(value, dict) else value if isinstance(value, list) else []

    def linked(record):
        if not isinstance(record, dict):
            errors.append("document_evidence 记录必须是对象")
            return []
        ids = record.get("block_ids")
        if ids is None and record.get("block_id") is not None:
            ids = [record["block_id"]]
        if not isinstance(ids, list) or not ids:
            errors.append("document_evidence 记录缺少 block_id/block_ids")
            return []
        valid = []
        for bid in ids:
            if bid not in final_by_id:
                errors.append("document_evidence 回链未知 block %s" % bid)
            elif bid not in part_owner:
                errors.append("document_evidence block %s 没有 reading_unit source_part" % bid)
            else:
                valid.append(bid)
        unit_ids = record.get("source_unit_ids")
        if unit_ids is None and record.get("source_unit_id") is not None:
            unit_ids = [record["source_unit_id"]]
        if unit_ids is not None:
            for bid in valid:
                if part_owner[bid] not in unit_ids:
                    errors.append("document_evidence block %s 与声明 source_unit_id 不匹配" % bid)
        return valid

    if status == "success":
        caption_evidence = records_for("captions")
        for key in ("tables", "figures"):
            for entry in result.get(key, []) or []:
                if not norm(entry.get("caption", "")):
                    continue
                found = any(isinstance(rec, dict) and
                            ((entry.get("id") is not None and rec.get("id") == entry.get("id")) or
                             (entry.get("block_id") and rec.get("block_id") == entry.get("block_id")))
                            for rec in caption_evidence)
                if not found:
                    errors.append("success caption %s 缺 document_evidence 映射" % entry.get("id", entry.get("block_id")))
        formula_evidence = records_for("formulas")
        for entry in result.get("formulas", []) or []:
            if not norm(entry.get("original", "") or entry.get("latex", "")):
                continue
            found = any(isinstance(rec, dict) and
                        ((entry.get("id") is not None and rec.get("id") == entry.get("id")) or
                         (entry.get("block_id") and rec.get("block_id") == entry.get("block_id")))
                        for rec in formula_evidence)
            if not found:
                errors.append("success formula %s 缺 document_evidence 映射" % entry.get("id", entry.get("block_id")))

    for key in ("title", "abstract"):
        for record in records_for(key):
            ids = linked(record)
            joined = norm("\n".join(final_by_id[bid].get("text", "") for bid in ids))
            claimed = record.get("text", document.get(key)) if isinstance(record, dict) else None
            if claimed is not None and norm(claimed) != joined:
                errors.append("document_evidence.%s 文本与回链块不一致" % key)
            target = norm(document.get(key, ""))
            if target and target != joined:
                errors.append("document.%s 与 document_evidence 回链块不一致" % key)

    caption_targets = [entry for key in ("tables", "figures") for entry in result.get(key, []) or []
                       if isinstance(entry, dict) and norm(entry.get("caption", ""))]
    for record in records_for("captions"):
        ids = linked(record)
        joined = norm("\n".join(final_by_id[bid].get("text", "") for bid in ids))
        claimed = record.get("text", record.get("caption")) if isinstance(record, dict) else None
        if claimed is not None and norm(claimed) not in joined:
            errors.append("caption evidence 文本不在回链原块中")
        if isinstance(record, dict) and record.get("id") is not None:
            matches = [entry for entry in caption_targets if entry.get("id") == record.get("id")]
            if not matches:
                errors.append("caption evidence id %s 没有对应 table/figure" % record.get("id"))
            elif any(norm(entry.get("caption")) not in joined for entry in matches):
                errors.append("caption evidence id %s 回链到错误原块" % record.get("id"))

    formula_targets = [entry for entry in result.get("formulas", []) or [] if isinstance(entry, dict)]
    for record in records_for("formulas"):
        ids = linked(record)
        joined = norm("\n".join(final_by_id[bid].get("text", "") for bid in ids))
        claimed = record.get("original", record.get("text")) if isinstance(record, dict) else None
        if claimed is not None and norm(claimed) not in joined:
            errors.append("formula evidence original 不在回链原块中")
        if isinstance(record, dict) and record.get("id") is not None:
            matches = [entry for entry in formula_targets if entry.get("id") == record.get("id")]
            if not matches:
                errors.append("formula evidence id %s 没有对应 formula" % record.get("id"))
            else:
                for entry in matches:
                    original = norm(entry.get("original", ""))
                    if original and original not in joined:
                        errors.append("formula evidence id %s 回链到错误原块" % record.get("id"))


def validate(source, source_blocks, result, result_blocks, result_base):
    errors, warnings = [], []
    geometry, result_blocks = select_geometry(result, result_base, errors) if result_blocks is None else (result, result_blocks)
    status = result.get("status")
    if status == "partial" and not norm(result.get("status_reason", "")):
        errors.append("status=partial 必须填写 status_reason")
    if status not in (None, "success", "partial", "unable", "in_progress"):
        errors.append("未知 status: %s" % status)

    source_ids = [b.get("id") for b in source_blocks]
    result_ids = [b.get("id") for b in result_blocks]
    source_by_id = {b.get("id"): b for b in source_blocks}
    final_by_id = {b.get("id"): b for b in result_blocks}
    for label, ids in (("source", source_ids), ("result", result_ids)):
        duplicates = sorted({str(x) for x in ids if ids.count(x) > 1})
        invalid = [x for x in ids if not isinstance(x, str) or not x]
        if duplicates:
            errors.append("%s block ID 重复: %s" % (label, duplicates))
        if invalid:
            errors.append("%s 含空/非字符串 block ID" % label)
    missing = sorted(set(source_by_id) - set(final_by_id))
    extra = sorted(set(final_by_id) - set(source_by_id))
    if missing:
        errors.append("最终 blocks 丢失源块: %s" % missing)
    if extra:
        errors.append("最终 blocks 增加未知块: %s" % extra)

    exact_text_changes, whitespace_changes = [], []
    for bid in sorted(set(source_by_id) & set(final_by_id)):
        src, dst = source_by_id[bid], final_by_id[bid]
        if src.get("text", "") != dst.get("text", ""):
            exact_text_changes.append(bid)
            if norm(src.get("text", "")) != norm(dst.get("text", "")):
                errors.append("block %s 文本内容/空白以外发生变化" % bid)
            else:
                whitespace_changes.append(bid)
        for field in ("page", "kind", "column"):
            if src.get(field) != dst.get(field):
                errors.append("block %s 原字段 %s 被改变" % (bid, field))
        if "source_lines" in src:
            if "source_lines" not in dst:
                errors.append("block %s 丢失 source_lines" % bid)
            elif dst["source_lines"] != src["source_lines"]:
                errors.append("block %s source_lines 被改变" % bid)
        if dst.get("zone_id") is None:
            errors.append("block %s 缺 zone_id" % bid)
        if not isinstance(dst.get("order"), int):
            errors.append("block %s 缺整数 order" % bid)
    if whitespace_changes:
        warnings.append("仅空白格式变化的 blocks: %s" % whitespace_changes)
    order_pairs = [(b.get("page"), b.get("order")) for b in result_blocks if isinstance(b.get("order"), int)]
    if len(order_pairs) != len(set(order_pairs)):
        errors.append("同页 block order 不唯一")

    # 原 table entry 必须回指仍存在的正文块；rows/cells/page 不得静默变形。
    result_tables = result.get("tables", geometry.get("tables", [])) or []
    table_by_block = {}
    for table in result_tables:
        if not isinstance(table, dict):
            errors.append("table entry 必须是对象")
            continue
        bid = table.get("block_id")
        if bid:
            if bid not in final_by_id:
                errors.append("table entry 回链未知 block %s" % bid)
            if bid in table_by_block:
                errors.append("多个 table entry 复用 block_id %s" % bid)
            table_by_block[bid] = table
    for table in source.get("tables", []) or []:
        bid = table.get("block_id")
        if bid and bid not in final_by_id:
            errors.append("原 table block %s 在最终 blocks 不存在" % bid)
        if bid:
            dst = table_by_block.get(bid)
            if dst is None:
                errors.append("原 table entry %s 在结果缺失" % bid)
                continue
            for key in ("rows", "cells", "page"):
                if key in table and table.get(key) != dst.get(key):
                    errors.append("table %s 的原字段 %s 被改变" % (bid, key))
            if "bbox" in table and not boxes_equal(table["bbox"], final_by_id.get(bid, {}).get("bbox")):
                errors.append("table %s bbox 与原块不一致" % bid)
    for group_name in ("tables", "formulas"):
        for entry in source.get(group_name, []) or []:
            bid = entry.get("block_id") or entry.get("source_block_id")
            if bid and bid not in final_by_id:
                errors.append("原 %s 对应 block %s 不存在" % (group_name, bid))
    for formula in result.get("formulas", geometry.get("formulas", [])) or []:
        bid = formula.get("block_id") or formula.get("source_block_id")
        if bid and bid not in final_by_id:
            errors.append("formula 回链未知 block %s" % bid)

    # reading_units / source_parts：unit text 必须由当次 parts 重建，且上下文一致。
    units = geometry.get("reading_units")
    if not isinstance(units, list):
        errors.append("结果缺少数组 reading_units")
        units = []
    zones = geometry.get("page_zones")
    if not isinstance(zones, list):
        errors.append("结果缺少数组 page_zones")
        zones = []
    unit_by_id, part_owner, part_record = {}, {}, {}
    sequence = []
    for unit in units:
        if not isinstance(unit, dict):
            errors.append("reading_unit 必须是对象")
            continue
        uid = unit.get("unit_id")
        if not isinstance(uid, str) or not uid:
            errors.append("reading_unit 缺 unit_id")
            continue
        if uid in unit_by_id:
            errors.append("reading_unit ID 重复: %s" % uid)
        unit_by_id[uid] = unit
        if unit.get("source_unit_ids") != [uid]:
            errors.append("unit %s source_unit_ids 必须恰好指向自身" % uid)
        parts = unit.get("source_parts")
        if not isinstance(parts, list):
            errors.append("unit %s 缺 source_parts" % uid)
            parts = []
        ids_from_unit = unit.get("source_block_ids")
        ids_from_parts = [p.get("source_block_id") for p in parts if isinstance(p, dict)]
        if ids_from_unit != ids_from_parts:
            errors.append("unit %s source_block_ids 与 source_parts 顺序/覆盖不一致" % uid)
        rebuilt = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict))
        if norm(unit.get("text", "")) != norm(rebuilt):
            errors.append("unit %s text 无法由 source_parts 有序重建" % uid)
        if unit.get("text_sha256") is not None and unit.get("text_sha256") != sha(unit.get("text", "")):
            errors.append("unit %s text_sha256 不匹配" % uid)
        pages, zone_ids = set(), set()
        for part in parts:
            if not isinstance(part, dict):
                errors.append("unit %s 含非对象 source_part" % uid)
                continue
            bid = part.get("source_block_id")
            for field in ("source_block_id", "source_unit_id", "text", "hash", "bbox"):
                if field not in part:
                    errors.append("unit %s source_part 缺字段 %s" % (uid, field))
            if bid in part_owner:
                errors.append("源块 %s 在 source_parts 出现多次" % bid)
            part_owner[bid] = uid
            part_record[bid] = part
            sequence.append(bid)
            if part.get("source_unit_id") != uid:
                errors.append("part %s source_unit_id 与所属 unit 不一致" % bid)
            text = part.get("text", "")
            if part.get("hash") != sha(text):
                errors.append("part %s hash 不匹配其 text" % bid)
            src = source_by_id.get(bid)
            dst = final_by_id.get(bid)
            if src is None or dst is None:
                errors.append("part 回链未知 block %s" % bid)
                continue
            if norm(text) != norm(src.get("text", "")):
                errors.append("part %s 不是原 block 的完整守恒文本" % bid)
            if not boxes_equal(part.get("bbox"), src.get("bbox")):
                errors.append("part %s bbox 与原 block 不一致" % bid)
            pages.add(dst.get("page")); zone_ids.add(dst.get("zone_id"))
            if unit.get("zone_id") != dst.get("zone_id"):
                errors.append("unit %s zone context 与 block %s 不一致" % (uid, bid))
        if len(pages) > 1 or unit.get("page") not in pages and pages:
            errors.append("unit %s page context 与 parts 不一致" % uid)
        expected_box = union([p["bbox"] for p in parts if isinstance(p, dict) and isinstance(p.get("bbox"), list)])
        if expected_box is not None and not boxes_equal(unit.get("bbox"), expected_box):
            errors.append("unit %s bbox 不是 source_parts bbox 的并集" % uid)
        if len(zone_ids) > 1:
            errors.append("unit %s 混入多个 zone 的 blocks" % uid)

    unmapped = sorted(set(source_by_id) - set(part_owner))
    unmapped_list, gap_ids = disclosed_ids(result)
    if unmapped:
        if status != "partial":
            errors.append("reading_units 未映射源块: %s" % unmapped)
        elif set(unmapped) != unmapped_list or not set(unmapped).issubset(gap_ids):
            errors.append("partial 的未映射块必须同时精确列入 unmapped_block_ids 与 gaps.block_id(s): %s" % unmapped)
        else:
            warnings.append("partial 明示未映射 blocks: %s" % unmapped)
    if unmapped_list - set(unmapped):
        errors.append("unmapped_block_ids 声明了实际仍被映射/未知的块: %s" % sorted(unmapped_list - set(unmapped)))
    if status == "success" and (result.get("gaps") or result.get("unmapped_block_ids")):
        errors.append("success 不得带 gaps/unmapped_block_ids")

    zone_by_id = {}
    zone_orders = []
    for zone in zones:
        zid = zone.get("zone_id")
        if not isinstance(zone.get("order"), int):
            errors.append("zone %s 缺整数 order" % zid)
        else:
            zone_orders.append((zone.get("page"), zone.get("order")))
        if not isinstance(zid, str) or not zid:
            errors.append("page_zone 缺 zone_id")
            continue
        if zid in zone_by_id:
            errors.append("page_zone ID 重复: %s" % zid)
        zone_by_id[zid] = zone
        bids = zone.get("source_block_ids")
        if not isinstance(bids, list):
            errors.append("zone %s 缺 source_block_ids" % zid)
            continue
        assigned = [b["id"] for b in sorted(result_blocks, key=lambda b: b.get("order", 0))
                    if b.get("zone_id") == zid]
        if bids != assigned:
            errors.append("zone %s source_block_ids 与最终 blocks 的 zone/order 不一致" % zid)
        for bid in bids:
            b = final_by_id.get(bid)
            if b is None or b.get("page") != zone.get("page"):
                errors.append("zone %s 的 block/page 回链错误: %s" % (zid, bid))
        if zone.get("source_unit_ids") != [u.get("unit_id") for u in units if u.get("zone_id") == zid]:
            errors.append("zone %s source_unit_ids 与 reading_units 覆盖/顺序不一致" % zid)
        expected_box = union([final_by_id[bid]["bbox"] for bid in bids if bid in final_by_id and isinstance(final_by_id[bid].get("bbox"), list)])
        if expected_box is not None and not boxes_equal(zone.get("bbox"), expected_box):
            errors.append("zone %s bbox 不是成员 block bbox 的并集" % zid)
    if len(zone_orders) != len(set(zone_orders)):
        errors.append("同页 page_zone order 不唯一")
    for b in result_blocks:
        if b.get("zone_id") not in zone_by_id:
            errors.append("block %s 指向未知 zone" % b.get("id"))
    expected_sequence = [b["id"] for b in sorted(result_blocks, key=lambda b: (b.get("page"), b.get("order", 0)))
                         if b["id"] in part_owner]
    if sequence != expected_sequence:
        errors.append("reading_units 的全局顺序与最终 blocks page/order 不一致（可能 context 换位）")

    check_document_evidence(result, final_by_id, part_owner, errors)
    source_chars = sum(len(b.get("text", "")) for b in source_blocks)
    result_chars = sum(len(b.get("text", "")) for b in result_blocks)
    final_in_source_order = [final_by_id[bid] for bid in source_ids if bid in final_by_id]
    unit_text_digest = sha(json.dumps([{"unit_id": u.get("unit_id"), "text": norm(u.get("text", ""))}
                                      for u in units if isinstance(u, dict)], ensure_ascii=False, separators=(",", ":")))
    part_text_digest = canonical_digest([{"id": bid, "page": source_by_id.get(bid, {}).get("page"),
                                          "kind": source_by_id.get(bid, {}).get("kind"),
                                          "text": part_record[bid].get("text", "")}
                                         for bid in source_ids if bid in part_record])
    report = {
        "success": not errors and status != "partial",
        "validation_status": "invalid" if errors else "partial" if status == "partial" else "valid",
        "exit_code": 1 if errors else 0,
        "errors": errors, "warnings": warnings,
        "source_block_count": len(source_blocks), "result_block_count": len(result_blocks),
        "reading_unit_count": len(units), "zone_count": len(zones),
        "source_character_count": source_chars, "result_character_count": result_chars,
        "source_word_count": sum(len(re.findall(r"\S+", b.get("text", ""))) for b in source_blocks),
        "result_word_count": sum(len(re.findall(r"\S+", b.get("text", ""))) for b in result_blocks),
        "source_normalized_text_sha256": canonical_digest(source_blocks),
        "result_normalized_text_sha256": canonical_digest(final_in_source_order),
        "reading_units_normalized_text_sha256": unit_text_digest,
        "source_parts_normalized_text_sha256": part_text_digest,
        "exact_text_changed_block_ids": exact_text_changes,
        "missing_block_ids": missing, "extra_block_ids": extra,
        "unmapped_block_ids": unmapped, "duplicate_block_ids": sorted({i for i in result_ids if result_ids.count(i) > 1}),
    }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    errors = []
    try:
        source = load_json(args.source)
        source_blocks = collect_blocks(source, os.path.dirname(os.path.abspath(args.source)), errors, "source")
        result = load_json(args.result)
        report = validate(source, source_blocks, result, None, os.path.dirname(os.path.abspath(args.result)))
        report["errors"] = errors + report["errors"]
        report["success"] = not report["errors"] and result.get("status") != "partial"
        report["validation_status"] = "invalid" if report["errors"] else "partial" if result.get("status") == "partial" else "valid"
        report["exit_code"] = 1 if report["errors"] else 0
        report["source_path"] = os.path.abspath(args.source)
        report["result_path"] = os.path.abspath(args.result)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        report = {"success": False, "validation_status": "invalid", "exit_code": 1,
                  "errors": ["读取/校验失败: %s" % exc], "warnings": []}
    parent = os.path.dirname(os.path.abspath(args.report))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("validate_layout: %s errors=%d warnings=%d" %
          (report["validation_status"], len(report["errors"]), len(report["warnings"])))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
