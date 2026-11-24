# 翻译示例（标注为示例，非正式案例）

> 以下均为**示意**，用于说明输出格式与守恒原则，不冒充正式评测案例结果。示例 0–6 的行内原译文只是单项规则片段，不是可省略区间字段的完整 result；完整可交付结构见示例 7–8 与 references/output-schema.md。

## 示例 0：同义表面形式与多义语境（terminology.json）

```json
[
  {"term": "performance", "aliases": ["efficiency"], "locked": "效率", "alternates": ["效能"]},
  {"term": "bank", "locked": "银行", "context": ["\\b(?:account|finance|deposit)s?\\b"]},
  {"term": "bank", "locked": "河岸", "context": ["\\b(?:river|stream)s?\\b"]}
]
```

- `Our performance improved.` → `我们的效率提高了。`
- `The efficiency improved.` → `效率提高了。`（alias 同样受检）
- `The bank holds the account.` → `银行持有该账户。`
- `The bank borders the river.` → `河岸与河流相接。`

两个 `bank` 条目不能省略 `context`；同一表面形式若在一段中命中多个语境候选，检查器报配置错误而非同时要求两个译名。

## 示例 1：术语锁定 + 数字逐字保留

- 原文：`The thermal enhancement factor (TEF) reached 1.42 at Re = 1e4.`
- 译文：`热强化因子（TEF）在 Re = 1e4 时达到 1.42。`
- 依据：TEF → 热强化因子（术语表，全篇统一）；1.42、1e4 逐字保留。
- 段号：§2 ¶3 · status=ok

## 示例 2：限定强度守恒（不升级）

- 原文：`The data may indicate a trend toward improvement.`
- 译文：`数据可能提示存在改善趋势。`
- 依据：`may` 为等级 2，译作"可能"；`indicate` 不升级为"表明/证明"。
- status=ok

## 示例 3：因果 vs 相关不互换

- 原文：`The treatment was associated with a lower relapse rate.`
- 错误译文：`该治疗降低了复发率。`（把"相关"译成了"因果"）
- 正确译文：`该治疗与较低的复发率相关。`
- 依据：`associated with` 是相关（等级 3），不得译为"降低"（因果）。

## 示例 4：译不准如实标注

- 原文：`The coherence length ξ was extracted from the fit.`
- 译文：`相干长度 ξ 由拟合提取。`
- status=uncertain
- 依据：`coherence length` 在本学科常见译名"相干长度"，但本文上下文中该量可能指另一长度尺度，需人工确认（已入 uncertainties）。

## 示例 5：公式与图表/公式引用类型、编号守恒

- 原文：`Substituting into Eq. (3) yields $F = −k_B T \ln Z$; see Fig. 2.`
- 译文：`代入公式(3)得 $F = −k_B T \ln Z$；见图2。`（exit 0）
- 依据：公式内容除规范化空白外逐字保留；`Eq./Equation` 与 `公式/式` 同映射为 equation，`Fig/Figure` 与 `图` 同映射为 figure，语言标签可翻译；负号 `−`、命令 `\ln`、下标 `_B` 不失真。
- `\ln`→`\lg`、`x_i`→`x^i`、`Fig. 2`→`Table 2` 或 `图2`→`表2` 均产生 missing/added 并退出 1。支持 `$...$`、`$$...$$`、`\(...\)`、`\[...\]`；公式中的数字和引用编号先掩码，不重复计数。

## 示例 6：带符号数字与指数字符守恒

- 原文：`The values were -0.5, 10^-3, and 1e-3.`
- 译文：`这些值为 -0.5、10^-3 和 1e-3。`（exit 0）
- 把 `10^-3` 译成 `10^3`、删掉 `-0.5` 的负号，或额外译入 `20%`，均会产生 missing/added 并非零退出；`added` 不是备注。

## 示例 7：快照字符区间 + success 全覆盖

`case.json`：`{"case_id":"demo","output_contract":{}}`。规范化源文快照精确为以下 12 个字符（第一行末尾换行也计入区间）：

```text
Alpha.
Beta.
```

第一段 `Alpha.\n` 是 `[0,7)`，第二段 `Beta.` 是 `[7,12)`。下面是完整 success 结构，而不是省略了必填字段的译文片段：

```json
{
  "case_id": "demo",
  "status": "success",
  "status_reason": "",
  "source_lang": "en",
  "target_lang": "zh",
  "terminology": [],
  "segments": [
    {
      "id": "§1 ¶1",
      "source": "Alpha.\n",
      "target": "阿尔法。",
      "source_start": 0,
      "source_end": 7,
      "basis": "源文快照 [0,7) 逐字切片；段尾换行并入本段",
      "status": "ok"
    },
    {
      "id": "§2 ¶1",
      "source": "Beta.",
      "target": "贝塔。",
      "source_start": 7,
      "source_end": 12,
      "basis": "源文快照 [7,12) 逐字切片",
      "status": "ok"
    }
  ],
  "uncovered_ranges": [],
  "uncertainties": [],
  "tool_commands": [
    "python3 scripts/check_terminology.py --terms terminology.json --segments segments.json --report work/terminology-report.json",
    "python3 scripts/check_conservation.py --segments segments.json --report work/conservation-report.json",
    "python3 scripts/validate_translation_delivery.py --case case.json --source-text work/source-snapshot.txt --result result.json --work-segments segments.json --report work/delivery-report.json"
  ]
}
```

`success` 必须连续覆盖 `[0,12)`，且术语/守恒/交付脚本和语义人工回核都完成；工作 `segments.json` 若随 `--work-segments` 送检，其五项 `id/source/target/source_start/source_end` 必须与终稿逐项相同。

## 示例 8：partial 精确声明未覆盖区间，不静默漏段

沿用示例 7 的 `case.json` 与快照，若只翻译 `Alpha.\n`，完整 partial 结果如下（不能用空 target 占第二段）：

```json
{
  "case_id": "demo",
  "status": "partial",
  "status_reason": "Beta. 尚未翻译；语义人工回核未完成。",
  "source_lang": "en",
  "target_lang": "zh",
  "terminology": [],
  "segments": [
    {
      "id": "§1 ¶1",
      "source": "Alpha.\n",
      "target": "阿尔法。",
      "source_start": 0,
      "source_end": 7,
      "basis": "源文快照 [0,7) 逐字切片",
      "status": "ok"
    }
  ],
  "uncovered_ranges": [{"source_start": 7, "source_end": 12}],
  "uncertainties": ["§2 ¶1 Beta. 未翻译", "未做语义人工对照回核"],
  "tool_commands": [
    "python3 scripts/check_terminology.py --terms terminology.json --segments segments.json --report work/terminology-report.json",
    "python3 scripts/check_conservation.py --segments segments.json --report work/conservation-report.json",
    "python3 scripts/validate_translation_delivery.py --case case.json --source-text work/source-snapshot.txt --result result.json --work-segments segments.json --report work/delivery-report.json"
  ]
}
```

上述结构检查退出 0 只表示 partial 的结构与覆盖声明合格，未完成的守恒/语义核验仍必须列在 `uncertainties`，不得宣称全绿；`uncovered_ranges` 写成 `[]` 会失败。
