#!/usr/bin/env python3
"""译文守恒核验（scripts/check_conservation.py）

机械执行"关系准"中的可抽取部分：逐段对 source/target 做守恒抽取比对，
替代"全靠模型自查"。

抽取三类条目并逐段比对（多重集合，计数敏感）：
  1. 数字 number    —— 含正负号（含 Unicode −）、小数、百分数、千分位、
                      指数 `10^-3`/`10^3` 与科学计数 `1e-3`；
  2. 引用 citation  —— `[12]`、`[1-3]` 与 `(Author, year)`（含 et al./and/&）两种形态；
  3. 带单位量 quantity —— 数字+单位 token（m/s、kg、K、mol、mol/L、µm、°C、ppm 等）。

引用标记会先掩码再抽数字，避免把 [12] 的 12、(Smith, 2020) 的 2020 重复计为数字。

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


def _norm_space(s):
    return re.sub(r"\s+", " ", s).strip()


def _norm_num(s):
    """保留符号/指数，只统一等价书写中的千分位、Unicode 负号与指数花括号。"""
    return re.sub(r"\^\{([+\-]?\d+)\}", r"^\1", s.replace(",", "").replace("−", "-"))


def extract(text):
    """对一段文本抽取三类守恒条目，返回 {kind: Counter}。"""
    text = text or ""
    citations = Counter()
    masked = text
    for rx in (BRACKET_CITE_RE, AUTHOR_YEAR_RE):
        def _sub(m, _c=citations):
            _c[_norm_space(m.group(0))] += 1
            return " " * len(m.group(0))
        masked = rx.sub(_sub, masked)

    numbers = Counter(_norm_num(m.group(0)) for m in NUM_RE.finditer(masked))
    quantities = Counter(
        _norm_num(m.group("num")) + " " + m.group("unit")
        for m in QTY_RE.finditer(masked)
    )
    return {"number": numbers, "citation": citations, "quantity": quantities}


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
    ap = argparse.ArgumentParser(description="译文守恒核验（数字/引用/带单位量）")
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
        for kind in ("number", "citation", "quantity"):
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
