#!/usr/bin/env python3
"""build_anchor_index.py — 为论文文本/Markdown 生成稳定锚点索引（纯标准库）。

按标题行切分章节并赋稳定 ID（§1..§n），章节内按空行切段落赋 ¶1..¶m。
标题行识别规则（按优先级）：
  1. Markdown 标题：`#` ~ `######` 开头；
  2. 编号标题：`数字+.` 或 `数字+)` 开头（如 `1. Introduction`、`2.3 Methods`）；
  3. 全大写小节名：整行字母均为大写（如 `INTRODUCTION`、`RELATED WORK`）。
首个标题之前的前置内容（题名/作者/摘要等）归入首个章节之前的 "(preamble)" 节。

输出 anchor_index.json：
  {"source": <输入路径>,
   "sections": [{"id": "§1", "title": "...", "start_line": N,
                 "paragraphs": [{"id": "¶1", "preview": "<前40字>", "line": N,
                                 "text": "<段落原文，供 validate_anchors.py 核对 quote>"}]}]}

用法：
  python3 scripts/build_anchor_index.py --input paper.md --out anchor_index.json
"""
import argparse
import json
import re
import sys

MD_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
NUM_HEADING = re.compile(r"^(\d+(?:\.\d+)*)[.)]\s+(\S.*)$")
# 编号标题的标题部分应以字母/中日韩字符开头，且不像整句（避免误伤 "2023. We ..." 类正文）
NUM_HEADING_TITLE = re.compile(r"^[A-Za-z一-鿿]")
SENTENCE_END = tuple(".。!！?？;；")


def heading_title(line):
    """若该行是标题行，返回标题文本；否则返回 None。"""
    s = line.strip()
    if not s:
        return None
    m = MD_HEADING.match(s)
    if m:
        return m.group(1).strip()
    m = NUM_HEADING.match(s)
    if m and len(s) <= 120:
        rest = m.group(2).strip()
        if NUM_HEADING_TITLE.match(rest) and not rest.endswith(SENTENCE_END):
            return s
    letters = [c for c in s if c.isalpha()]
    if 2 <= len(letters) and len(s) <= 80 and all(c.isupper() for c in letters):
        return s
    return None


def split_paragraphs(body_lines):
    """body_lines: (lineno, text) 列表；按空行切段落。lineno 为 1-based 行号。"""
    paras = []
    buf = []
    start = None
    for lineno, text in body_lines:
        if text.strip():
            if start is None:
                start = lineno
            buf.append(text.strip())
        else:
            if buf:
                paras.append((start, " ".join(buf)))
                buf, start = [], None
    if buf:
        paras.append((start, " ".join(buf)))
    out = []
    for i, (line, text) in enumerate(paras, 1):
        preview = re.sub(r"\s+", " ", text)[:40]
        out.append({"id": f"¶{i}", "preview": preview, "line": line, "text": text})
    return out


def build_index(text):
    lines = text.splitlines()
    sections = []
    cur_title = None
    cur_start = None
    body = []

    def flush():
        nonlocal cur_title, cur_start, body
        if cur_title is None and not any(t.strip() for _, t in body):
            body = []
            return
        sid = f"§{len(sections) + 1}"
        sections.append({
            "id": sid,
            "title": cur_title if cur_title is not None else "(preamble)",
            "start_line": cur_start if cur_start is not None else (body[0][0] if body else 1),
            "paragraphs": split_paragraphs(body),
        })
        cur_title, cur_start, body = None, None, []

    for i, line in enumerate(lines, 1):
        title = heading_title(line)
        if title is not None:
            flush()
            cur_title, cur_start = title, i
        else:
            body.append((i, line))
    flush()
    return {"source": None, "sections": sections}


def main():
    ap = argparse.ArgumentParser(description="生成论文锚点索引 anchor_index.json")
    ap.add_argument("--input", required=True, help="论文文本/Markdown 文件路径")
    ap.add_argument("--out", required=True, help="输出 anchor_index.json 路径")
    args = ap.parse_args()
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"[build_anchor_index] 无法读取输入: {e}", file=sys.stderr)
        return 2
    index = build_index(text)
    index["source"] = args.input
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write("\n")
    nsec = len(index["sections"])
    npar = sum(len(s["paragraphs"]) for s in index["sections"])
    print(f"[build_anchor_index] {args.input} -> {args.out}: {nsec} 节, {npar} 段")
    for s in index["sections"]:
        print(f"  {s['id']} {s['title']!r} (start_line={s['start_line']}, {len(s['paragraphs'])} 段)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
