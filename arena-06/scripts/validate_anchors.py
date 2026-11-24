#!/usr/bin/env python3
"""validate_anchors.py — 校验 result.json 的锚点是否真实存在于锚点索引（纯标准库）。

规则：
  1. 递归收集 result.json 中所有带 `source_anchor`/`anchor` 字段的条目（笔记、
     论文字段、知识点等），锚点形态须为 `§x` 或 `§x ¶y`（可附带 Table/Fig 等补充
     定位，但 § 章节 ID 必须存在且可解析）。
  2. 每个 §x 必须存在于 anchor_index.json 的 sections；若带 ¶y，该段落必须存在
     于对应章节内。
  3. 若条目带 `quote` 字段（非空），quote 必须是被引段落原文的子串；锚点只到
     章节时，对该章节全部段落拼接文本核对。比较大小写不敏感、空白归一。
  4. 未解析/不存在的锚点、不匹配的 quote 逐条报错；有任何 error 时退出码 1。

用法：
  python3 scripts/validate_anchors.py --result result.json \
      --index anchor_index.json --report anchor_report.json
"""
import argparse
import json
import re
import sys

# 形如 "§2"、"§2 ¶1"、"§3 Table 1; §5 Table 3" 的锚点，逐个 § 段校验并配对紧随的 ¶
ANCHOR_RE = re.compile(r"§\s*(\d+)(?:\s*¶\s*(\d+))?")
ANCHOR_KEYS = ("source_anchor", "anchor")
SKIP_KEYS = ANCHOR_KEYS + ("quote",)


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def collect_entries(obj, path="$"):
    """递归收集所有带锚点字段的条目 -> [(path, anchor, quote)]。"""
    entries = []
    if isinstance(obj, dict):
        anchor = None
        for k in ANCHOR_KEYS:
            if isinstance(obj.get(k), str) and obj[k].strip():
                anchor = obj[k]
                break
        if anchor is not None:
            quote = obj.get("quote")
            entries.append((path, anchor, quote if isinstance(quote, str) else None))
        for k, v in obj.items():
            if k in SKIP_KEYS:
                continue
            entries.extend(collect_entries(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            entries.extend(collect_entries(v, f"{path}[{i}]"))
    return entries


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="校验 result.json 锚点与 anchor_index.json 的一致性")
    ap.add_argument("--result", required=True, help="result.json 路径")
    ap.add_argument("--index", required=True, help="build_anchor_index.py 生成的 anchor_index.json")
    ap.add_argument("--report", required=True, help="输出校验报告 JSON 路径")
    args = ap.parse_args()

    try:
        result = load_json(args.result)
        index = load_json(args.index)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[validate_anchors] 无法读取输入: {e}", file=sys.stderr)
        return 2

    sections = {s["id"]: s for s in index.get("sections", [])}
    errors = []
    checked = 0

    for path, anchor, quote in collect_entries(result):
        checked += 1
        matches = list(ANCHOR_RE.finditer(anchor))
        if not matches:
            errors.append({"path": path, "anchor": anchor,
                           "reason": "锚点不含可解析的 § 章节 ID（形态须为 §x 或 §x ¶y）"})
            continue
        target_texts = []
        anchor_ok = True
        for m in matches:
            sec_id = f"§{m.group(1)}"
            sec = sections.get(sec_id)
            if sec is None:
                errors.append({"path": path, "anchor": anchor,
                               "reason": f"章节 {sec_id} 不存在于索引"})
                anchor_ok = False
                continue
            if m.group(2):
                par_id = f"¶{m.group(2)}"
                par = next((p for p in sec["paragraphs"] if p["id"] == par_id), None)
                if par is None:
                    errors.append({"path": path, "anchor": anchor,
                                   "reason": f"段落 {sec_id} {par_id} 不存在于索引"
                                             f"（该节共 {len(sec['paragraphs'])} 段）"})
                    anchor_ok = False
                    continue
                target_texts.append(par.get("text", ""))
            else:
                target_texts.extend(p.get("text", "") for p in sec["paragraphs"])
        if anchor_ok and quote and quote.strip():
            if norm(quote) not in norm("\n".join(target_texts)):
                errors.append({"path": path, "anchor": anchor,
                               "reason": f"quote 不是被引范围原文的子串: {quote[:60]!r}"})

    report = {
        "result": args.result,
        "index": args.index,
        "checked": checked,
        "ok": not errors,
        "errors": errors,
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if errors:
        print(f"[validate_anchors] 校验失败：{checked} 条锚点中 {len(errors)} 条错误")
        for e in errors:
            print(f"  ERROR {e['path']} anchor={e['anchor']!r}: {e['reason']}")
        print(f"[validate_anchors] 报告已写入 {args.report}")
        return 1
    print(f"[validate_anchors] 全部通过：{checked} 条锚点均存在于索引，quote 核对一致")
    print(f"[validate_anchors] 报告已写入 {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
