#!/usr/bin/env python3
"""译文守恒核验（scripts/check_conservation.py）

机械执行"关系准"中的可抽取部分：逐段对 source/target 做守恒抽取比对，
替代"全靠模型自查"。

抽取五类条目并逐段比对（多重集合，计数敏感）：
  1. 数字 number      —— 含正负号（含 Unicode −）、小数、百分数、千分位、
                        指数 `10^-3`/`10^3` 与科学计数 `1e-3`；
  2. 引用 citation    —— `[12]`、`[1-3]` 与 `(Author, year)`（含 et al./and/&）；
  3. 带单位量 quantity —— 数字+单位 token（m/s、kg、K、mol、mol/L、µm、°C、ppm 等）；
  4. 公式 formula     —— `$...$`、`$$...$$`、`\\(...\\)`、`\\[...\\]` 的内容，
                        仅规范化空白后逐字比较多重集合；
  5. 图表/公式引用 reference —— `Fig/Figure/图`、`Table/表`、`Eq/Equation/公式/式`
                        映射到同一类型，编号保持；语言标签可以翻译，类型不能改变。

公式会先掩码，再抽图表/公式引用；这两种新条目及文献引用也都会在抽数字和
带单位量前掩码，避免编号、上下标或引用年份被重复计数。

报告每条目：source 有而 target 缺失 → missing；target 新增（source 无）→ added；
均按段 id 定位。

用法：
  python3 scripts/check_conservation.py --segments segments.json [--report out.json]
退出码：missing 或 added 任一非空 → 1；否则 0。仅依赖 Python 标准库。
"""
import argparse
import json
import re
import sys
from collections import Counter

# 单位白名单（长的在前，保证 m/s、mol/L 先于 m、mol 匹配）
UNITS = [
    "mol/L", "mmol/L", "km/h", "m/s", "m/s²", "µmol", "mmol", "mol",
    "kPa", "MPa", "GPa", "Pa", "kJ", "kW", "kHz", "MHz", "GHz", "Hz",
    "µm", "um", "nm", "mm", "cm", "km", "mg", "kg", "mL", "µL", "min",
    "eV", "ppm", "ppb", "bar", "atm", "°C", "°F",
    "W", "J", "V", "A", "K", "L", "g", "h", "s", "m", "T", "N",
]
_UNIT_ALT = "|".join(re.escape(u) for u in sorted(UNITS, key=len, reverse=True))

_SIGN = r"[+\-−]?"
_DECIMAL = r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)"
_EXPONENT = r"(?:[eE][+\-−]?\d+|\^(?:\{[+\-−]?\d+\}|[+\-−]?\d+))?"
NUM_RE = re.compile(r"(?<![A-Za-z0-9_.])" + _SIGN + _DECIMAL + _EXPONENT + r"%?(?![A-Za-z0-9_])")
QTY_RE = re.compile(
    r"(?<![A-Za-z0-9_.])(?P<num>" + _SIGN + _DECIMAL + _EXPONENT + r")"
    r"\s?(?P<unit>" + _UNIT_ALT + r")(?![A-Za-z0-9µμ/])"
)
BRACKET_CITE_RE = re.compile(r"\[\d+(?:\s*[–—,\-]\s*\d+)*\]")
AUTHOR_YEAR_RE = re.compile(
    r"\([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’.\-]+"
    r"(?:(?:,| and | & | 与 )\s*[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’.\-]+)*"
    r"(?:\s+et\s+al\.?)?,\s*\d{4}[a-z]?\)"
)
# $$...$$ 必须排在 $...$ 前；具名组便于只取公式内容，不把定界符当公式字符。
FORMULA_RE = re.compile(
    r"\$\$(?P<double>.+?)\$\$"
    r"|\$(?P<single>[^$]+)\$"
    r"|\\\((?P<paren>.+?)\\\)"
    r"|\\\[(?P<bracket>.+?)\\\]",
    re.DOTALL,
)
REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?P<label>Fig(?:ure)?\.?|Table|Eq(?:uation)?\.?|公式|图|表|式)"
    r"\s*[\(（]?\s*(?P<number>\d+)\s*[\)）]?(?!\d)",
    re.IGNORECASE,
)
_REFERENCE_TYPES = {
    "fig": "figure", "figure": "figure", "图": "figure",
    "table": "table", "表": "table",
    "eq": "equation", "equation": "equation", "公式": "equation", "式": "equation",
}


def _norm_space(s):
    return re.sub(r"\s+", " ", s).strip()


def _norm_num(s):
    """保留符号/指数，只统一等价书写中的千分位、Unicode 负号与指数花括号。"""
    return re.sub(r"\^\{([+\-]?\d+)\}", r"^\1", s.replace(",", "").replace("−", "-"))


def _mask_matches(text, rx, on_match):
    """记录匹配并用等长空白掩码，供后续抽取器使用。"""
    def replace(match):
        on_match(match)
        return " " * len(match.group(0))
    return rx.sub(replace, text)


def extract(text):
    """对一段文本抽取五类守恒条目，返回 {kind: Counter}。"""
    text = text or ""

    formulas = Counter()
    def keep_formula(match):
        body = next(match.group(name) for name in ("double", "single", "paren", "bracket")
                    if match.group(name) is not None)
        # 只折叠空白；不改大小写、命令名、运算符或上下标。
        formulas[_norm_space(body)] += 1
    masked = _mask_matches(text, FORMULA_RE, keep_formula)

    references = Counter()
    def keep_reference(match):
        label = match.group("label").rstrip(".").casefold()
        kind = _REFERENCE_TYPES[label]
        references[kind + ":" + match.group("number")] += 1
    masked = _mask_matches(masked, REFERENCE_RE, keep_reference)

    citations = Counter()
    for rx in (BRACKET_CITE_RE, AUTHOR_YEAR_RE):
        masked = _mask_matches(
            masked, rx, lambda match: citations.update({_norm_space(match.group(0)): 1})
        )

    numbers = Counter(_norm_num(m.group(0)) for m in NUM_RE.finditer(masked))
    quantities = Counter(
        _norm_num(m.group("num")) + " " + m.group("unit")
        for m in QTY_RE.finditer(masked)
    )
    return {
        "number": numbers,
        "citation": citations,
        "quantity": quantities,
        "formula": formulas,
        "reference": references,
    }


def diff(seg_id, kind, src_counter, tgt_counter, missing, added):
    for item, n in sorted(src_counter.items()):
        have = tgt_counter.get(item, 0)
        if have < n:
            missing.append({
                "segment_id": seg_id, "kind": kind, "item": item,
                "expected": n, "found": have,
                "message": f"{seg_id}: {kind} '{item}' 原文出现 {n} 次，译文仅 {have} 次",
            })
    for item, n in sorted(tgt_counter.items()):
        have = src_counter.get(item, 0)
        if have < n:
            added.append({
                "segment_id": seg_id, "kind": kind, "item": item,
                "expected": have, "found": n,
                "message": f"{seg_id}: {kind} '{item}' 为译文新增（原文 {have} 次，译文 {n} 次）",
            })


def main():
    ap = argparse.ArgumentParser(description="译文守恒核验（数字/引用/带单位量/公式/图表公式引用）")
    ap.add_argument("--segments", required=True, help="segments.json 路径")
    ap.add_argument("--report", default=None, help="报告输出路径（缺省 stdout）")
    args = ap.parse_args()

    with open(args.segments, encoding="utf-8") as fh:
        segments = json.load(fh)

    missing, added = [], []
    for seg in segments:
        seg_id = seg.get("id", "?")
        src = extract(seg.get("source", ""))
        tgt = extract(seg.get("target", ""))
        for kind in ("number", "citation", "quantity", "formula", "reference"):
            diff(seg_id, kind, src[kind], tgt[kind], missing, added)

    report = {
        "checked_segments": len(segments),
        "ok": not missing and not added,
        "missing": missing,
        "added": added,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"报告已写入 {args.report}：missing={len(missing)} added={len(added)}")
    else:
        print(text)
    sys.exit(1 if missing or added else 0)


if __name__ == "__main__":
    main()
