---
name: literature-knowledge-graph
description: >-
  Use when the task is to build a knowledge graph from scientific papers —
  extract entities that actually appear in the text (researcher, material,
  method, task, metric, conclusion), align aliases/abbreviations without false
  merges, extract only evidence-backed relations with direction and conditions,
  bind every node and edge to source evidence with strength, support graph
  queries with result subgraphs, and export a readable graph file. Produces
  nodes + edges + provenance, not a free-form summary. Do NOT use for
  translation, polishing, or Q&A — capture the paper's actual objects and
  relations, do not infer entities by common sense or merge by guess.
---

# 文献知识图谱构建（Literature Knowledge Graph）

目标：从论文抽取**真实出现的实体与关系**，对齐别名、绑定证据、支持查询、可增量更新，导出可读图谱。四个纪律：**抽得准、连得对、对得齐、查得到、回得去**。

## 何时使用 / 何时不用

**使用**：从一篇或多篇论文构建实体-关系图谱（节点 + 边 + 来源证据），支持查询与导出。

**不用**：翻译、润色、摘要、问答、Nanopublication（那是另一 Skill）。本 Skill 只抽取论文里真实出现的对象与关系，不凭常识补实体、不凭猜测合并或连边。

## 强制流程（按顺序执行）

### 第 0 步：读输入，定输出契约
1. 读 `/input/case.json`：取 `case_id`、`output_contract` 字段、论文材料路径、任务范围。
2. 读 `/input/task.md`：确认范围（单篇 / 多篇、指定主题）。
3. 记录 `case_id`。`result.json` 必须含 `case_id` 与全部 output_contract 字段。

### 第 1 步：实体识别（抽得准）
按 references/entity-recognition.md 抽取实体，类型限：`researcher`、`material`、`method`、`task`、`metric`、`conclusion`。
- 实体必须是**论文里真实出现**的对象，保留原文表述与位置。
- 区分**作者自述**与**他人转述/综述引用**：后者标 `attribution=reported`，不作为作者结论。
- 不凭常识补全概念（原文没写"量子计算"，就不建该节点）。

### 第 2 步：实体对齐（对得齐）
按 references/entity-alignment.md 处理别名/缩写/大小写/全称简称/同名冲突：
- 同一对象的不同写法合并为一个节点，记录合并依据。
- 同名不同对象（同名冲突）**不错误合并**，分节点并标 `homonym`。
- 产出 `entity_id`（稳定编号）+ `aliases`（别名列表）。

### 第 3 步：关系抽取（连得对）
按 references/relation-extraction.md 抽取关系，谓词用受控词表：`uses`、`compares`、`outperforms`、`supports`、`contradicts` 等。
- 只建立**有证据支持**的关系；方向与适用条件与原文一致。
- 区分直接证据 vs 共现/转述/推测：后者标 `evidence=weak` 或不建边。
- 因果 vs 相关、优于 vs 比较 不得混用。

### 第 4 步：来源绑定（回得去）
按 references/source-binding.md，为每个节点、每条边绑定：
- `evidence_text`（原文片段）+ `evidence_location`（论文标识 + 章节/图表位置）。
- `evidence_strength`（strong/medium/weak）。

### 第 5 步：图谱查询与导出（查得到）
按 references/graph-query.md：
- 提供**至少 3 个真实查询**，每个给出结果子图 + 支撑证据 + 无法确定的关系。
- 导出可读图谱文件（JSON，含 nodes/edges/provenance）。

### 第 6 步：增量更新（多篇场景）
按 references/graph-query.md 的增量更新约定：新论文加入时保留既有 `entity_id`/节点，说明新增、合并、冲突关系处置方式。

## 异常与边界

| 情况 | 处置 |
|---|---|
| 扫描件无文本层 | OCR；不可靠则标 `uncertain`，不臆造实体/关系 |
| 关系无证据 | 不建边，或标 `evidence=weak` 并说明 |
| 实体同名冲突 | 分节点 + 标 `homonym`，不错误合并 |
| 别名无法确定是否同一实体 | 分节点 + `uncertain`，提示待人工合并 |
| 关系方向/条件不明 | 标 `uncertain`，不猜测 |

## 复用与维护

- 实体类型、关系词表、对齐规则、证据强度、图谱 schema 均可复用。
- `entity_id` 稳定，支持跨论文增量更新。
- 本 Skill 只做忠实抽取，不评价研究结论。

详见随附资源：
- `references/entity-recognition.md` —— 实体识别与自述/转述区分
- `references/entity-alignment.md` —— 别名归一与同名冲突
- `references/relation-extraction.md` —— 关系抽取与受控词表
- `references/source-binding.md` —— 来源绑定与证据强度
- `references/graph-query.md` —— 图谱查询与增量更新
- `references/output-schema.md` —— result.json / 图谱导出契约
- `examples/kg-examples.md` —— 标注为示例的图谱片段（非正式案例）
