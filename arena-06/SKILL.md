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
4. **读完输入立即在 `/app/output/result.json` 写检查点骨架**，不得等最终总结时才首次写盘。骨架含 `case_id`、`status="in_progress"`、`status_reason`、output_contract 全部字段的空占位（保持声明类型），以及默认字段 `paper_card={}`、`sections=[]`、`knowledge_points=[]`、`paper_card_anchors=[]`、`uncertainties=[]`：
```json
{"case_id":"<回填>","status":"in_progress","status_reason":"正在读取论文并生成锚点索引","paper_card":{},"paper_card_anchors":[],"sections":[],"knowledge_points":[],"uncertainties":[]}
```
随后在骨架中加入 output_contract 声明的其他空字段；之后每个阶段都**就地更新同一文件**。

### 第 1 步：结构识别 + 生成锚点索引（对得上）
1. **先跑 `scripts/build_anchor_index.py` 生成锚点索引**：
   `python3 scripts/build_anchor_index.py --input <论文文本/md> --out anchor_index.json`；
   PDF 使用同一最小调用链：`python3 scripts/build_anchor_index.py --input /input/paper.pdf --out anchor_index.json`，脚本调用可选系统依赖 `pdftotext -layout`。若工具缺失或转换失败会清晰非零退出；此时按错误提示安装 Poppler，或手动转换后再输入文本，不得假装索引已生成。
   索引按标题行切分章节并赋稳定 ID（`§1..§n`），章节内按空行切段落赋 `¶1..¶m`；
   后续所有锚点**必须取自该索引中的 ID**，不允许自编号。进入本步时先确认第 0 步骨架已存在，生成索引后立即就地更新 `status_reason`/进度；失败则把骨架更新为 `unable` 并写明原因。
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

每个非空字段的值都要能指回原文（见第 5 步锚点）。锚点放在顶层配套数组 `paper_card_anchors`，每项为 `{"field":"<paper_card 字段名>","source_anchor":"§x ¶y","quote":"可选逐字原文"}`，不塞进字段字符串。**结论成立的前提条件必须记下**，不省略限定词。

### 第 3 步：章节总结（对得上 + 留得住）
逐章节提炼，不是通篇压缩：
- 每节输出：`目的`、`方法/论证`、`结果/要点`、`承接（与前后节关系）`，并新增正式字段 `source_anchor`。
- 保留章节间逻辑链（如"第 2 节提出 X，第 3 节用 Y 验证"）。
- 关键数值、公式编号、图表引用保留。

### 第 4 步：知识点提取（用得上）
1. 抽取可检索条目：概念、变量、方法、结论、公式、数据集、评价指标。
2. **归一化**：术语/缩写/同义表述统一（如 `SGD` ↔ `stochastic gradient descent` 归为一条）。
3. **去重**：同一知识点不重复建条目；发现原文表述矛盾 → 标 `conflict` 并回链两处原文，不擅自取舍。
4. 每条知识点附：`id`、`label`、`value`、`source_anchor`、`type`（concept/variable/method/result/metric/limitation）。

### 第 5 步：锚点回链（找得回）
每条笔记、每个非空 paper_card 字段、每个 section、每个知识点都要**锚点**（见 references/source-anchoring.md）。paper_card 使用 `paper_card_anchors`，sections/knowledge_points 使用各自 `source_anchor`：
- 锚点 = 第 1 步索引中的稳定 ID：`§x` 或 `§x ¶y`；可附带 `Fig./Table/Eq. 编号` 作补充定位。
- **只允许使用索引里存在的 §/¶ ID**；`page=N` 仅在输入材料自带真实页码时附加。
- 锚点必须指向**真正对应的位置**，不是笼统的"见正文"；带 `quote` 的条目，quote 必须逐字摘自被引段落。
- success 下不得缺锚点；partial 下仅明确 `status=uncertain` 的条目可暂缺锚点并保留 warning，同时必须在 `status_reason` 与非空 `uncertainties` 交代缺口，且核心内容至少有一个真实有效锚点。无法确定位置 → 标 `uncertain`，不伪造锚点。

### 第 6 步：输出 result.json
写 `/app/output/result.json`（见 references/output-schema.md），含：
- `case_id`、`status`、`status_reason`
- output_contract 全部字段
- `paper_card`、顶层 `paper_card_anchors`、`sections`（每项含 `source_anchor`）、`knowledge_points`（每项含 `source_anchor`）、`uncertainties`

同时输出 Markdown 笔记（可读、可检索、可比较）。

### 第 7 步：交付前核验（必须全绿）
交付前必须运行最终锚点校验，全部通过才可交付：
```
python3 scripts/validate_anchors.py --result /app/output/result.json \
    --index anchor_index.json --report /app/output/anchor_report.json
```
- 退出码 0：锚点全部存在于索引、quote 与原文一致，且 success 的非空 paper_card 字段、每个 section、每个 knowledge_point 均有正式锚点；`checked=0` 不能通过（unable 无内容例外）。
- partial 可有 uncertain 缺锚点 warning，但至少一个核心锚点真实有效，并检查 `status_reason`/`uncertainties` 已交代；warning 不等于可省略这些说明。
- 退出码 1：按报告逐条修正（补正式锚点、换用索引中真实存在的 ID、订正 quote），或仅在 partial 下把对应条目标 `uncertain` 后重跑；**未通过核验的锚点不得留在交付物中**。

## 检查点与降级

- 检查点 0/1：第 0 步读完输入即写上述 `/app/output/result.json` 骨架；第 1 步开始先确认骨架存在，之后每阶段就地更新，绝不等到最终交付才创建文件。
- 检查点 1（第 1 步后）：`anchor_index.json` 已生成且章节数与原文观感一致；为 0 节 → 输入无标题结构，改用"全文一节"降级并说明，同时更新 result.json。
- 检查点 2（第 5 步后）：每条正式 `source_anchor` 都能人工在索引中查到，paper_card 的非空字段均在 `paper_card_anchors` 覆盖；查不到/漏覆盖 → 立即补锚点或换 ID，仅在 partial 下可标 `uncertain`。
- 检查点 3（第 7 步）：`validate_anchors.py` 退出码 0 且 checked>0（unable 无内容例外）；非 0 → 回到第 5 步修正，不得带病交付。
- 降级：索引生成失败（输入为空/无法读取、PDF 无 pdftotext 或转换失败）→ 在既有骨架上标 `status=unable` 并写明原因；个别段落无法定位 → partial 下条目级 `uncertain`，同时填写 `status_reason`/`uncertainties`。
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
- `scripts/build_anchor_index.py` —— 文本/Markdown/PDF 生成 §/¶ 稳定锚点索引（PDF 需可选系统工具 pdftotext）
- `scripts/validate_anchors.py` —— 交付前锚点/quote/必填覆盖核验（纯标准库，非全绿退出码 1）
- `references/paper-card-fields.md` —— 论文卡片字段字典
- `references/section-alignment.md` —— 章节对齐与承接关系规则
- `references/knowledge-extraction.md` —— 知识点提取、归一化与去重
- `references/source-anchoring.md` —— 锚点格式与可核验性
- `references/output-schema.md` —— result.json 字段契约
- `examples/summary-examples.md` —— 标注为示例的笔记（非正式案例）
