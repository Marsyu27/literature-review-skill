# 翻译示例（标注为示例，非正式案例）

> 以下均为**示意**，用于说明输出格式与守恒原则，不冒充正式评测案例结果。

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
