#!/usr/bin/env python3
"""build_anchor_index.py — 为论文文本/Markdown/PDF 生成稳定锚点索引。

按标题行切分章节并赋稳定 ID（§1..§n），章节内按空行切段落赋 ¶1..¶m。
标题行识别规则（按优先级）：
  1. Markdown 标题：`#` ~ `######` 开头；
  2. 编号标题：阿拉伯数字、罗马数字或字母编号（如 `1. Introduction`、
     `III.A Methods`、`IV. Experimental Results`、`A. Methods`）；
  3. 全大写小节名：整行字母均为大写（如 `INTRODUCTION`、`RELATED WORK`）；
  4. 保守识别短的无编号 Title Case 标题（如 `Introduction`、`Methods`）：
     行长/词数受限、无句末标点且后续有正文；采纳后仍写 warning 供复核。
首个标题之前的前置内容（题名/作者/摘要等）归入首个章节之前的 "(preamble)" 节。
疑似标题但未采纳的候选及需人工复核的启发式切分写入顶层 `warnings`，不隐藏不确定性。

输出 anchor_index.json：
  {"source": <输入路径>,
   "sections": [{"id": "§1", "title": "...", "start_line": N,
                 "paragraphs": [{"id": "¶1", "preview": "<前40字>", "line": N,
                                 "text": "<段落原文，供 validate_anchors.py 核对 quote>"}]}],
   "warnings": [{"line": N, "text": "...", "type": "...", "reason": "..."}]}

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
ROMAN_OR_LETTER_HEADING = re.compile(
    r"^((?:[IVXLCDM]+\.[A-Z]\.?)|(?:[IVXLCDM]+[.)])|(?:[A-Z][.)]))\s+(\S.*)$"
)
# 编号标题的标题部分应以字母/中日韩字符开头，且不像整句（避免误伤 "2023. We ..." 类正文）
NUM_HEADING_TITLE = re.compile(r"^[A-Za-z一-鿿]")
SENTENCE_END = tuple(".。!！?？;；")
TITLE_CASE_STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "of",
    "on", "or", "the", "to", "via", "vs", "with",
}
# 仅以常见论文结构词收尾，降低把论文题名或普通 Title Case 正文切成新节的概率。
TITLE_CASE_TERMINALS = {
    "abstract", "acknowledgement", "acknowledgements", "acknowledgment",
    "acknowledgments", "analysis", "appendices", "appendix", "approach",
    "background", "conclusion", "conclusions", "data", "dataset", "datasets",
    "design", "discussion", "evaluation", "experiment", "experiments", "findings",
    "implementation", "introduction", "limitation", "limitations", "materials",
    "method", "methodology", "methods", "model", "models", "references",
    "results", "setup", "study", "summary", "work",
}


def _numbered_title(s):
    """返回已校验的编号标题；不逐项产生 warning。"""
    match = NUM_HEADING.match(s) or ROMAN_OR_LETTER_HEADING.match(s)
    if not match or len(s) > 120:
        return None
    rest = match.group(2).strip()
    if NUM_HEADING_TITLE.match(rest) and not rest.endswith(SENTENCE_END):
        return s
    return None


def _looks_title_case(s):
    """短、纯文字、各主要单词首字母大写；句中常见小连接词可小写。"""
    if not (2 <= len(s) <= 60) or s.endswith(SENTENCE_END):
        return False
    if not re.fullmatch(r"[A-Za-z][A-Za-z\s'’&/-]*", s):
        return False
    words = re.findall(r"[A-Za-z]+", s)
    if not (1 <= len(words) <= 8) or words[-1].lower() not in TITLE_CASE_TERMINALS:
        return False
    for i, word in enumerate(words):
        if i and word.lower() in TITLE_CASE_STOPWORDS and word.islower():
            continue
        if not word[0].isupper():
            return False
    return True


def _has_following_body(following_lines):
    """仅看下一个非空行；若它仍像标题，则不为当前候选强行切节。"""
    for future in following_lines:
        candidate = future.strip()
        if not candidate:
            continue
        if MD_HEADING.match(candidate) or _numbered_title(candidate) or _looks_title_case(candidate):
            return False
        letters = [c for c in candidate if c.isalpha()]
        if 2 <= len(letters) and len(candidate) <= 80 and all(c.isupper() for c in letters):
            return False
        return any(c.isalpha() for c in candidate)
    return False


def classify_heading(line, following_lines=()):
    """返回 (标题或 None, warnings)；无编号启发式的采纳与拒绝均留痕。"""
    s = line.strip()
    if not s:
        return None, []
    match = MD_HEADING.match(s)
    if match:
        return match.group(1).strip(), []

    numbered_match = NUM_HEADING.match(s) or ROMAN_OR_LETTER_HEADING.match(s)
    if numbered_match:
        title = _numbered_title(s)
        if title is not None:
            return title, []
        rest = numbered_match.group(2).strip()
        if len(s) > 120:
            reason = "疑似编号标题，但行超过 120 字，为避免切开长正文未采纳"
        elif not NUM_HEADING_TITLE.match(rest):
            reason = "疑似编号标题，但编号后不是字母/中日韩字符开头的标题，未采纳"
        else:
            reason = "疑似编号标题，但标题部分有句末标点，按正文保留"
        return None, [{
            "line": None, "text": s, "type": "heading_rejected", "reason": reason,
        }]

    letters = [c for c in s if c.isalpha()]
    if 2 <= len(letters) and len(s) <= 80 and all(c.isupper() for c in letters):
        return s, []

    if _looks_title_case(s):
        if _has_following_body(following_lines):
            return s, [{
                "line": None,
                "text": s,
                "type": "heading_review",
                "reason": "无编号短 Title Case 行按保守规则识别为标题；请人工复核切分",
            }]
        return None, [{
            "line": None,
            "text": s,
            "type": "heading_rejected",
            "reason": "疑似无编号 Title Case 标题，但后续没有可确认正文，未切分",
        }]
    return None, []


def heading_title(line, following_lines=()):
    """兼容原调用：只返回标题文本；build_index 会另存完整 warning。"""
    title, _ = classify_heading(line, following_lines)
    return title


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
    warnings = []
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
        title, heading_warnings = classify_heading(line, lines[i:])
        if title is not None:
            flush()
            cur_title, cur_start = title, i
        else:
            body.append((i, line))
        for warning in heading_warnings:
            warning["line"] = i
            warnings.append(warning)
    flush()
    return {"source": None, "sections": sections, "warnings": warnings}


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
    print(
        f"[build_anchor_index] {args.input} -> {args.out}: {nsec} 节, {npar} 段；"
        f"来源={source_kind}；warnings={len(index['warnings'])}"
    )
    for s in index["sections"]:
        print(f"  {s['id']} {s['title']!r} (start_line={s['start_line']}, {len(s['paragraphs'])} 段)")
    for warning in index["warnings"]:
        print(f"  WARNING line={warning['line']}: {warning['reason']}：{warning['text']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
