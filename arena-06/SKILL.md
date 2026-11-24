---
name: literature-summary-structured-notes
description: >-
  Use when the task is to turn a scientific paper into structured, reusable
  notes — section-aligned summaries, a unified paper card (research question,
  data, methods, findings, limitations), deduplicated knowledge points, and
  per-item source anchors back to page/paragraph/figure/table. Produces a
  retrievable JSON/Markdown notebook, not a single compressed abstract. Do NOT
  use for translation, polishing, or content Q&A — capture the paper's own
  structure and evidence, do not interpret or embellish.
---

# 文献总结与结构化笔记（Literature Summary & Structured Notes）

目标：把一篇论文整理成**与原文结构对齐、字段齐备、可回链、可复用**的笔记。四个纪律：**对得上、留得住、找得回、用得上**——骨架跟着论文自身章节走、关键要素与前提条件都记下、每条笔记能指回原文、笔记可检索可比较可继续加工。

## 何时使用 / 何时不用

**使用**：把论文做成结构化笔记/论文卡片/章节摘要/知识点清单，带来源锚点。

**不用**：文献翻译、学术润色、内容问答、从零生成综述结论。本 Skill 只忠实抽取与整理，不评价、不推断、不补充原文没有的内容。

## 强制流程（按顺序执行）

### 第 0 步：读输入，定输出契约
1. 读 `/input/case.json`：取 `case_id`、`output_contract` 字段、论文材料路径、任务范围。
2. 读 `/input/task.md`：确认本次要求（整篇笔记 / 论文卡片 / 章节摘要 / 知识点 / 指定章节）。
3. 记录 `case_id` 与 output_contract 字段。`result.json` 必须含 `case_id` 与全部 output_contract 字段。

### 第 1 步：结构识别（对得上）
1. 识别论文自身结构：标题、作者、摘要、章节（编号与标题）、图表、公式、参考文献。
2. **骨架跟着原文走**，不套用通用摘要模板。若原文章节编号为 `2.3`、`III.A`，笔记保留原编号与层级。
3. 识别"论证顺序"：每个章节的目的（做什么）与方法（怎么做）→ 结果 → 结论，并保留章节间承接关系。
4. 页眉页脚、脚注单独标记，不混入正文。

### 第 2 步：论文卡片（留得住）
按统一字段登记（见 references/paper-card-fields.md），至少覆盖：
- 研究问题 / 目标
- 数据与材料（数据集、样本量、来源）
- 方法条件（模型、参数、实验条件、假设）
- 主要发现（含关键数值）
- 局限（作者自述 + 客观可见的边界）
- 结论

每个字段的值都要能指回原文（见第 5 步锚点）。**结论成立的前提条件必须记下**，不省略限定词。

### 第 3 步：章节总结（对得上 + 留得住）
逐章节提炼，不是通篇压缩：
- 每节输出：`目的`、`方法/论证`、`结果/要点`、`承接（与前后节关系）`。
- 保留章节间逻辑链（如"第 2 节提出 X，第 3 节用 Y 验证"）。
- 关键数值、公式编号、图表引用保留。

### 第 4 步：知识点提取（用得上）
1. 抽取可检索条目：概念、变量、方法、结论、公式、数据集、评价指标。
2. **归一化**：术语/缩写/同义表述统一（如 `SGD` ↔ `stochastic gradient descent` 归为一条）。
3. **去重**：同一知识点不重复建条目；发现原文表述矛盾 → 标 `conflict` 并回链两处原文，不擅自取舍。
4. 每条知识点附：`id`、`label`、`value`、`source_anchor`、`type`（concept/variable/method/result/metric/limitation）。

### 第 5 步：锚点回链（找得回）
每条笔记、每个字段、每个知识点都要**锚点**（见 references/source-anchoring.md）：
- 格式：`page=N` + `§章节` + `¶段落` + `Fig./Table/Eq. 编号`（按可用粒度）。
- 锚点必须指向**真正对应的位置**，不是笼统的"见正文"。
- 无法确定位置 → 标 `uncertain`，不伪造锚点。

### 第 6 步：输出 result.json
写 `/app/output/result.json`（见 references/output-schema.md），含：
- `case_id`、`status`、`status_reason`
- output_contract 全部字段
- `paper_card`、`sections`（章节总结）、`knowledge_points`（知识点）、`uncertainties`

同时输出 Markdown 笔记（可读、可检索、可比较）。

## 异常与边界

| 情况 | 处置 |
|---|---|
| 扫描件/乱码/双栏错序 | 先按解析 Skill 的思路修正阅读顺序；仍不可靠则标 `uncertain` |
| 图表/公式缺失或为图片 | 保留编号与位置，标"内容不可读"，不臆造 |
| 原文自相矛盾 | 保留两处原文并标 `conflict`，不擅自取舍 |
| 前提条件缺失 | 在 `limitations`/`uncertainties` 注明"原文未报告" |
| 超长论文 | 分章节处理，每节独立输出，最终合并 |

## 复用与维护

- 字段字典、锚点格式、知识点条目模板均可被他人复用于新论文。
- 每次运行保留 `case_id` 与工具命令，便于复现与审计。
- 本 Skill 只做忠实抽取整理，不评价研究质量。

详见随附资源：
- `references/paper-card-fields.md` —— 论文卡片字段字典
- `references/section-alignment.md` —— 章节对齐与承接关系规则
- `references/knowledge-extraction.md` —— 知识点提取、归一化与去重
- `references/source-anchoring.md` —— 锚点格式与可核验性
- `references/output-schema.md` —— result.json 字段契约
- `examples/summary-examples.md` —— 标注为示例的笔记（非正式案例）
