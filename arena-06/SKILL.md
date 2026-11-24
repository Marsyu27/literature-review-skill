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

### 第 1 步：结构识别 + 生成锚点索引（对得上）
1. **先跑 `scripts/build_anchor_index.py` 生成锚点索引**：
   `python3 scripts/build_anchor_index.py --input <论文文本/md> --out anchor_index.json`。
   索引按标题行切分章节并赋稳定 ID（`§1..§n`），章节内按空行切段落赋 `¶1..¶m`；
   后续所有锚点**必须取自该索引中的 ID**，不允许自编号。
2. 识别论文自身结构：标题、作者、摘要、章节（编号与标题）、图表、公式、参考文献。
3. **骨架跟着原文走**，不套用通用摘要模板。若原文章节编号为 `2.3`、`III.A`，笔记保留原编号与层级（索引的 `§n` 是定位 ID，与原编号并列记录，不互相替代）。
4. 识别"论证顺序"：每个章节的目的（做什么）与方法（怎么做）→ 结果 → 结论，并保留章节间承接关系。
5. 页眉页脚、脚注单独标记，不混入正文。

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
- 锚点 = 第 1 步索引中的稳定 ID：`§x` 或 `§x ¶y`；可附带 `Fig./Table/Eq. 编号` 作补充定位。
- **只允许使用索引里存在的 §/¶ ID**；`page=N` 仅在输入材料自带真实页码时附加。
- 锚点必须指向**真正对应的位置**，不是笼统的"见正文"；带 `quote` 的条目，quote 必须逐字摘自被引段落。
- 无法确定位置 → 标 `uncertain`，不伪造锚点。

### 第 6 步：输出 result.json
写 `/app/output/result.json`（见 references/output-schema.md），含：
- `case_id`、`status`、`status_reason`
- output_contract 全部字段
- `paper_card`、`sections`（章节总结）、`knowledge_points`（知识点）、`uncertainties`

同时输出 Markdown 笔记（可读、可检索、可比较）。

### 第 7 步：交付前核验（必须全绿）
写盘前必须运行锚点校验，全部通过才可交付：
```
python3 scripts/validate_anchors.py --result /app/output/result.json \
    --index anchor_index.json --report /app/output/anchor_report.json
```
- 退出码 0：锚点全部存在于索引、quote 与原文一致，可交付。
- 退出码 1：按报告逐条修正（换用索引中真实存在的 ID、订正 quote），或把对应条目标 `uncertain` 后重跑；**未通过核验的锚点不得留在交付物中**。

## 检查点与降级

- 检查点 1（第 1 步后）：`anchor_index.json` 已生成且章节数与原文观感一致；为 0 节 → 输入无标题结构，改用"全文一节"降级并说明。
- 检查点 2（第 5 步后）：每条 `source_anchor` 都能人工在索引中查到；查不到 → 立即换 ID 或标 `uncertain`。
- 检查点 3（第 7 步）：`validate_anchors.py` 退出码 0；非 0 → 回到第 5 步修正，不得带病交付。
- 降级：索引生成失败（输入为空/无法读取）→ `status=unable` 并写明原因；个别段落无法定位 → 条目级 `uncertain`，整体可 `partial`。
- 预算不足时优先保证：锚点索引 + 核验通过 > 知识点数量。

## 异常与边界

| 情况 | 处置 |
|---|---|
| 扫描件/乱码/双栏错序 | 自包含规则：无版面信息时一律按输入文本顺序组织章节与段落；疑似错序或不可判读的块标 `uncertain` 并在 `uncertainties` 说明原因，不臆测重排 |
| 图表/公式缺失或为图片 | 保留编号与位置，标"内容不可读"，不臆造 |
| 原文自相矛盾 | 保留两处原文并标 `conflict`，不擅自取舍 |
| 前提条件缺失 | 在 `limitations`/`uncertainties` 注明"原文未报告" |
| 超长论文 | 分章节处理，每节独立输出，最终合并 |

## 复用与维护

- 字段字典、锚点格式、知识点条目模板均可被他人复用于新论文。
- 每次运行保留 `case_id` 与工具命令，便于复现与审计。
- 本 Skill 只做忠实抽取整理，不评价研究质量。

详见随附资源：
- `scripts/build_anchor_index.py` —— 生成 §/¶ 稳定锚点索引（纯标准库）
- `scripts/validate_anchors.py` —— 交付前锚点/quote 核验（纯标准库，非全绿退出码 1）
- `references/paper-card-fields.md` —— 论文卡片字段字典
- `references/section-alignment.md` —— 章节对齐与承接关系规则
- `references/knowledge-extraction.md` —— 知识点提取、归一化与去重
- `references/source-anchoring.md` —— 锚点格式与可核验性
- `references/output-schema.md` —— result.json 字段契约
- `examples/summary-examples.md` —— 标注为示例的笔记（非正式案例）
