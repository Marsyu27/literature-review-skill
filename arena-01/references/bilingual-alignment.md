# 段落级双语对照与段号约定（Bilingual Alignment）

## 目标

每段译文都能**指回原文**，段号一一对应，支持定位回看、逐段修改、引用核对。

## 段号约定

- 章节号保留原文编号（如 `2.3`、`III.A`）。
- 段落号用 `§<章节> ¶<段落序号>`，如 `§2 ¶3` 表示第 2 章第 3 段。
- 句号用 `sent.<序号>`，如 `§2 ¶3 sent.4`。

## 对照格式（每段必须同时给原文与译文）

```markdown
## §2 ¶3
- **原文**：We measured the transition temperature at 4.2 K under a field of 0.5 T.
- **译文**：我们在 0.5 T 的磁场下测得转变温度为 4.2 K。
- **依据**：4.2 K、0.5 T 逐字保留；transition temperature → 转变温度（术语表）。
```

## 跨页 / 跨栏 / 跨章节处理

- 段落被截断到下一页/栏 → 接续为一段，段号不变，`basis` 标注"跨页接续：页 X→X+1"。
- 页眉页脚/脚注/边注 → 单独翻译并标 `type=header/footer/footnote`，不混入正文。
- 跨栏大标题/图表 → 单独标记，不归入某一栏。

## 不重复、不遗漏、不错位

- 每段原文只译一次；译文段数必须与原文段数一致。
- 若某段"译不出"（残缺/模糊），保留原段落号并标 `unable/uncertain`，不跳过、不编造。

## 结果输出

对照结果写入 result.json 的 `segments` 数组，每项含 `id`（段号）、`source`、`target`、`basis`、`status`（ok/uncertain/unable）。
