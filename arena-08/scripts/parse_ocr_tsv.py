#!/usr/bin/env python3
"""把 Tesseract TSV 转成带 bbox/confidence 的词级、行级 JSON。

用法：
    tesseract page.png out tsv   # 需要时另加 -l eng / -l chi_sim+eng
    python3 scripts/parse_ocr_tsv.py --tsv out.tsv --out out.json

仅使用标准库。confidence 保留 Tesseract 的 0--100 标度，未知值为 null；
行 confidence 是行内已知词 confidence 按词框面积加权的均值，不补造置信度。
"""
import argparse
import csv
import json
import sys


def _int(row, key):
    return int(row[key])


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence(value):
    confidence = _number(value)
    if confidence is None or not 0.0 <= confidence <= 100.0:
        return None
    return confidence


def parse_tsv(path):
    """读取 TSV；过滤空词，按页/块/段/行聚合行文本、bbox 和置信度。"""
    words = []
    lines = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        required = {"level", "page_num", "block_num", "par_num", "line_num",
                    "word_num", "left", "top", "width", "height", "conf", "text"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("invalid Tesseract TSV header")
        for row in reader:
            text = (row.get("text") or "").strip()
            if not text or row.get("level") != "5":
                continue
            left, top = _int(row, "left"), _int(row, "top")
            width, height = _int(row, "width"), _int(row, "height")
            if width < 0 or height < 0:
                raise ValueError("negative word bbox size")
            confidence = _confidence(row.get("conf"))
            identity = tuple(_int(row, key) for key in
                             ("page_num", "block_num", "par_num", "line_num"))
            word = {
                "page": identity[0],
                "block": identity[1],
                "paragraph": identity[2],
                "line": identity[3],
                "word": _int(row, "word_num"),
                "text": text,
                "bbox": [left, top, left + width, top + height],
                "confidence": confidence,
            }
            words.append(word)
            rec = lines.setdefault(identity, [])
            rec.append(word)

    line_out = []
    for identity, line_words in lines.items():
        line_words.sort(key=lambda w: (w["word"], w["bbox"][0]))
        weighted = [
            (w["confidence"], max(1, w["bbox"][2] - w["bbox"][0])
             * max(1, w["bbox"][3] - w["bbox"][1]))
            for w in line_words if w["confidence"] is not None
        ]
        confidence = (sum(c * area for c, area in weighted) / sum(area for _, area in weighted)
                      if weighted else None)
        line_out.append({
            "page": identity[0], "block": identity[1],
            "paragraph": identity[2], "line": identity[3],
            "text": " ".join(w["text"] for w in line_words),
            "bbox": [min(w["bbox"][0] for w in line_words),
                     min(w["bbox"][1] for w in line_words),
                     max(w["bbox"][2] for w in line_words),
                     max(w["bbox"][3] for w in line_words)],
            "confidence": round(confidence, 3) if confidence is not None else None,
        })
    return {
        "mode": "ocr-tsv",
        "confidence_scale": "tesseract-0-100",
        "words": words,
        "lines": line_out,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tsv", required=True, help="Tesseract 生成的 TSV 文件")
    parser.add_argument("--out", help="JSON 输出路径；缺省写 stdout")
    args = parser.parse_args()
    try:
        result = parse_tsv(args.tsv)
    except (OSError, ValueError, KeyError) as exc:
        print(f"parse_ocr_tsv: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
