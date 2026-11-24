#!/usr/bin/env python3
"""build_anchor_index.py — 为论文文本/Markdown/PDF 生成稳定锚点索引。

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
  python3 scripts/build_anchor_index.py --input /input/paper.pdf --out anchor_index.json

PDF 输入通过可选系统依赖 `pdftotext -layout` 转为文本；普通文本/Markdown
仍直接按 UTF-8 读取，不依赖外部命令。pdftotext 不可用或转换失败时清晰报错并非零退出。
"""
import argparse
import json
import re
import shutil
import subprocess
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


def decode_output(data):
    """解码子进程文本；不把二进制 PDF 或编解码异常抛给调用方。"""
    return data.decode("utf-8", errors="replace")


def read_pdf_with_pdftotext(path):
    executable = shutil.which("pdftotext")
    if executable is None:
        print(
            "[build_anchor_index] 检测到 PDF，但系统未安装或找不到 pdftotext。"
            "请安装 Poppler（提供 pdftotext），或先用 `pdftotext -layout paper.pdf paper.txt` "
            "转换后以文本/Markdown 作为 --input。",
            file=sys.stderr,
        )
        return None, 2
    try:
        proc = subprocess.run(
            [executable, "-layout", path, "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        print(
            f"[build_anchor_index] 无法执行 pdftotext: {exc}。"
            "请改为先手动转换 PDF，再输入文本/Markdown。",
            file=sys.stderr,
        )
        return None, 2
    if proc.returncode != 0:
        detail = decode_output(proc.stderr).strip()
        print(
            f"[build_anchor_index] pdftotext -layout 转换失败（退出码 {proc.returncode}）"
            f"：{detail or '未提供错误详情'}。请修复 PDF，或手动转换后输入文本/Markdown。",
            file=sys.stderr,
        )
        return None, 2
    return decode_output(proc.stdout), 0


def main():
    ap = argparse.ArgumentParser(description="生成论文锚点索引 anchor_index.json")
    ap.add_argument("--input", required=True, help="论文文本/Markdown/PDF 文件路径")
    ap.add_argument("--out", required=True, help="输出 anchor_index.json 路径")
    args = ap.parse_args()

    is_pdf = args.input.lower().endswith(".pdf")
    if is_pdf:
        text, code = read_pdf_with_pdftotext(args.input)
        if code:
            return code
    else:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"[build_anchor_index] 无法读取输入: {e}", file=sys.stderr)
            return 2
        except UnicodeError as e:
            print(
                f"[build_anchor_index] 文本不是有效 UTF-8，无法读取: {e}。"
                "请转为 UTF-8 文本；PDF 请使用 .pdf 后缀。",
                file=sys.stderr,
            )
            return 2
    index = build_index(text)
    index["source"] = args.input
    try:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as e:
        print(f"[build_anchor_index] 无法写入输出: {e}", file=sys.stderr)
        return 2
    nsec = len(index["sections"])
    npar = sum(len(s["paragraphs"]) for s in index["sections"])
    source_kind = "PDF（pdftotext -layout）" if is_pdf else "文本/Markdown"
    print(f"[build_anchor_index] {args.input} -> {args.out}: {nsec} 节, {npar} 段；来源={source_kind}")
    for s in index["sections"]:
        print(f"  {s['id']} {s['title']!r} (start_line={s['start_line']}, {len(s['paragraphs'])} 段)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
