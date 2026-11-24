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
3. 记录 `case_id`。最终结果必须写 `/app/output/result.json`，含 `case_id` 与全部 output_contract 字段。
4. **立即写开工骨架**：先枚举 output_contract，将全部动态字段按声明类型以空字符串、空数组、空对象或 `null` 占位，不得只保留固定字段。默认结构为 `case_id`、`status:"in_progress"`、`status_reason:"处理中"`、`sources:[]`、`nodes:[]`、`edges:[]`、`queries:[]`、`uncertainties:[]`、`tool_commands:[]`、`provenance:[]`；动态字段与默认字段同名时以 output_contract 类型为准。开工即写入 `/app/output/result.json`。

### 第 1 步：读 corpus manifest 与两篇 JATS，登记来源
1. 读 `corpus-manifest.json`：为每篇论文登记独立 `source_id`（取自 manifest 的论文标识）、`jats_file`、`doi`、`title`、`authors`，写入输出顶层 `sources`。
2. 元数据**只取自 manifest 与对应 JATS**；根的 DOI/title/authors 属首篇，**不得套到第二篇**。
3. 按 source **分别抽取**：每篇独立扫描，节点/边锚点一律用该篇 `source_id` + 组织方 JATS `paragraph_id`（非 PDF 页码、非自建 §/¶）。
4. **禁止跨篇合并实体**，除非两篇明确指向同一物理实例（同一样品编号 / 同一模型 checkpoint）；合并须 `merge_basis` 写明双方 paragraph_id 双侧证据。

### 第 2 步：实体识别（抽得准）
按 references/entity-recognition.md 抽取实体，类型限：`researcher`、`material`、`method`、`task`、`metric`、`conclusion`。
- 实体必须是**论文里真实出现**的对象，保留原文表述与位置。
- 区分**作者自述**与**他人转述/综述引用**：后者标 `attribution=reported`，不作为作者结论。
- 不凭常识补全概念（原文没写"量子计算"，就不建该节点）。

### 第 3 步：实体对齐（对得齐）
按 references/entity-alignment.md 处理别名/缩写/大小写/全称简称/同名冲突：
- 同一对象的不同写法合并为一个节点，记录合并依据。
- 同名不同对象（同名冲突）**不错误合并**，分节点并标 `homonym`。
- 产出 `entity_id`（稳定编号）+ `aliases`（别名列表）。

### 第 4 步：关系抽取（连得对）
按 references/relation-extraction.md 抽取关系，谓词用受控词表：`uses`、`compares`、`outperforms`、`supports`、`contradicts` 等。
- 只建立**有证据支持**的关系；方向与适用条件与原文一致。
- 区分直接证据 vs 共现/转述/推测：后者标 `strength=weak` 或不建边。
- 因果 vs 相关、优于 vs 比较 不得混用。

### 第 5 步：来源绑定（回得去）
按 references/source-binding.md，为每个节点、每条边绑定四元组锚点：
- `source_id`（manifest 论文标识）+ `paragraph_id`（组织方 JATS 段落 ID）+ `quote`（≤30 字原文短引）+ `strength`（strong/medium/weak）。
- **边的 `evidence` 统一为非空数组**，可含一个或多个四元组；节点的 `evidence` 沿用单个对象；查询的 `evidence` 由工具继承为数组，禁止手写。
- 跨篇边必须有双侧证据：`same_concept` 同时列 primary 与 secondary 的四元组 quote，`condition` 写“同名概念，未证实同一物理实例”。不能由单侧引文推断“无共同 checkpoint”或两篇独立训练。
- 旧式 `§x ¶y` 仅作可选 human-readable `note`，不作锚点依据。

### 第 6 步：主图 → 真实查询 → 校验 → 导出（查得到）
严格按 **主图 nodes/edges 完成 → kg_tool.py query 计算 → kg_tool.py validate 验证** 的顺序，按 references/graph-query.md 使用稳定 DSL：
1. 提供至少 3 个真实查询。每条只由 Agent 写人读 `query`、机器可执行 `query_spec`（`filter_edges`/`neighbors`/`path`）及可选 `uncertain_relations`；自然语言 query 仅展示，不是执行逻辑。
2. **禁止手写或修补查询的 `result_subgraph`、`evidence`、`execution`**。在 Skill 根目录执行：
   ```bash
   python3 scripts/kg_tool.py query --graph /app/output/result.json --update
   ```
   也可 `--out /app/output/executed.json` 保留原文件。`--update` 原子覆盖；工具只投影主图边，按命中边继承证据并稳定去重，支持真实空结果。
3. 随后必须独立验证：
   ```bash
   python3 scripts/kg_tool.py validate --graph /app/output/result.json --report /app/output/report.json
   ```
   退出 0 才可交付；退出 1 时修正主图或 query_spec 后回到本步开头，绝不手改查询子图、继承证据、matched_edge_ids 或 report。success 少于 3 条会失败；partial 可少于 3 条，但 status_reason 必须含真实数量及未完成原因。
4. 导出可读 JSON（nodes/edges/provenance）及最终 result.json。主图增量更新后必须重新 query + validate，不得复用旧派生结果。工具不证明 `uncertain_relations` 的语义，也不替代原文证据审读。

### 第 7 步：增量更新（多篇场景）
按 references/graph-query.md 的增量更新约定：新论文加入时保留既有 `entity_id`/节点，说明新增、合并、冲突关系处置方式。

## 异常与边界

| 情况 | 处置 |
|---|---|
| 扫描件无文本层 | OCR；不可靠则标 `uncertain`，不臆造实体/关系 |
| 关系无证据 | 不建边，或标 `strength=weak` 并说明 |
| 实体同名冲突 | 分节点 + 标 `homonym`，不错误合并 |
| 别名无法确定是否同一实体 | 分节点 + `uncertain`，提示待人工合并 |
| 关系方向/条件不明 | 标 `uncertain`，不猜测 |
| 跨篇同名实体 | 默认拆分；合并须同一物理实例 + 双侧 paragraph_id 证据 |

## 检查点与降级

- **骨架先落盘**：按第 0 步写 `/app/output/result.json`（`case_id`/`status=in_progress`/`status_reason`、全部动态 output_contract 字段空占位及 sources/nodes/edges/queries/uncertainties 等默认结构），随时可交。
- **分源增量**：每处理完一篇论文立即增量写入该篇 sources/nodes/edges，再进下一篇；先保存 query_spec 草案和 uncertainties，主图可用后再由工具计算派生字段。
- **预算过半未完成** → 按 `sources → nodes → edges → query_spec → query → validate` 降级：先保 sources 完整，其次节点，再次边。
- success 查询最少 3 个；不足时将状态诚实设为 `partial`，只保留工具真实执行过的查询，并在 status_reason 写明实际数量及未完成原因。
- `partial` 时写明已完成范围与缺口，不补造；即使只有真实空结果也不能伪造非空主图或证据。

## 复用与维护

- 实体类型、关系词表、对齐规则、证据强度、图谱 schema 均可复用。
- `entity_id` 稳定，支持跨论文增量更新。
- 本 Skill 只做忠实抽取，不评价研究结论。

详见随附资源：
- `references/entity-recognition.md` —— 实体识别与自述/转述区分
- `references/entity-alignment.md` —— 别名归一与同名冲突
- `references/relation-extraction.md` —— 关系抽取与受控词表
- `references/source-binding.md` —— 来源绑定与证据强度
- `references/graph-query.md` —— filter_edges/neighbors/path DSL、CLI、校验与增量更新
- `references/output-schema.md` —— result.json / 图谱导出契约
- `scripts/kg_tool.py` —— 纯标准库查询执行与主图/派生结果验证
- `examples/kg-examples.md` —— 两篇论文、主图边与工具输出同步的示例（非正式案例）
- `src/reproduce.py` —— tempfile 真实 CLI 正反回归
