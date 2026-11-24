# 段落级双语对照与段号约定（Bilingual Alignment）

## 目标

每段译文都能**指回原文**，段号一一对应，支持定位回看、逐段修改、引用核对。

## 段号约定

- 章节号保留原文编号（如 `2.3`、`III.A`）。
- 段落号用 `§<章节> ¶<段落序号>`，如 `§2 ¶3` 表示第 2 章第 3 段。
- 句号用 `sent.<序号>`，如 `§2 ¶3 sent.4`。

## 对照格式（每段必须同时给原文、译文与快照区间）

先保存唯一、后续不再修改的规范化源文快照。`source_start/source_end` 是快照的 Python Unicode 字符半开区间（不是字节数），且 `source == snapshot[source_start:source_end]`。以下单段快照恰为 71 个字符：

```markdown
## §2 ¶3 · 快照 [0,71)
- **原文**：We measured the transition temperature at 4.2 K under a field of 0.5 T.
- **译文**：我们在 0.5 T 的磁场下测得转变温度为 4.2 K。
- **区间**：source_start=0，source_end=71。
- **依据**：4.2 K、0.5 T 逐字保留；transition temperature → 转变温度（术语表）。
```

## 跨页 / 跨栏 / 跨章节处理

- 段落被截断到下一页/栏 → 接续为一段，段号不变，`basis` 标注"跨页接续：页 X→X+1"。
- 页眉页脚/脚注/边注 → 单独翻译并标 `type=header/footer/footnote`，不混入正文。
- 跨栏大标题/图表 → 单独标记，不归入某一栏。

## 不重复、不遗漏、不错位

- 每段原文只译一次，ID 唯一，区间按原文递增且不重叠；success 的区间必须从 0 到快照末尾连续全覆盖。
- 段间换行也占快照字符位置，可并入前一段，避免无意的覆盖空洞。
- 若某段“译不出”（残缺/模糊），保留原段落号并标 `unable/uncertain`，target 写非空的 unable 原因标记并降级，不跳过、不编造。
- partial 可以只含已完成且 target 非空的段，但必须用非空 `status_reason` 与精确 `uncovered_ranges` 声明全部缺口，不能静默少段。

## 结果输出

对照结果写入 result.json 的 `segments` 数组，每项至少含 `id`、`source`、`target`、`source_start`、`source_end`，默认另含 `basis`、`status`（ok/uncertain/unable）。顶层 `uncovered_ranges` 在 partial/unable 时必填；交付前用 `scripts/validate_translation_delivery.py` 核 source 快照切片、ID、区间、覆盖和 work/final 五项（id/source/target/source_start/source_end）一致性。
