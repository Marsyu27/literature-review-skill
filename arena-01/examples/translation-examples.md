# 翻译示例（标注为示例，非正式案例）

> 以下均为**示意**，用于说明输出格式与守恒原则，不冒充正式评测案例结果。

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

## 示例 5：公式与编号保留

- 原文：`Substituting into Eq. (3) yields F = −k_B T ln Z.`
- 译文：`代入式 (3) 得 F = −k_B T ln Z。`
- 依据：公式原样保留；`Eq. (3)` → 式 (3)；负号 `−`、下标 `_B` 不失真。

## 示例 6：带符号数字与指数字符守恒

- 原文：`The values were -0.5, 10^-3, and 1e-3.`
- 译文：`这些值为 -0.5、10^-3 和 1e-3。`（exit 0）
- 把 `10^-3` 译成 `10^3`、删掉 `-0.5` 的负号，或额外译入 `20%`，均会产生 missing/added 并非零退出；`added` 不是备注。
