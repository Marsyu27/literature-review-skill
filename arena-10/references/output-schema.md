# result.json / 图谱导出契约（Output Schema）

## 硬性要求

1. `case_id` 原样回填；`status` + `status_reason` 必填。
2. **output_contract**：`/input/case.json` 里 `output_contract` 声明的每个字段都要出现，字段名与类型一致。
3. 顶层 `sources` 数组登记每篇论文；主图可机器读取：`nodes` + `edges` + `provenance`。每条边的 `evidence` **一律为非空数组**，包含 `{source_id, paragraph_id, quote, strength}` 四元组（`note` 可选）；节点 `evidence` 沿用单个四元组对象。
4. 每条 `queries[]` 必须有机器可执行的 `query_spec`。自然语言 `query` 仅供人读展示，不参与执行。`result_subgraph`、`evidence`、`execution` 必须由 `scripts/kg_tool.py query` 从主图重算，禁止模型或人工另写。
5. 查询子图每一项精确为 `{edge_id, source, predicate, target}`，只能投影已登记的主图边；不得加入仅存在于查询答案中的边。查询证据从命中边的 `evidence` 按稳定顺序继承、逐项精确去重，不允许增写、改写或补引文。
6. 节点/边 ID 非空且唯一，边端点必须存在，证据 `source_id` 必须在 `sources` 登记。源节点与目标节点属于不同论文 `source_id` 时，该边必须有双方来源的四元组证据；这同样适用于 `same_concept` 与其他合规跨篇关系。查询记录中显式引用的每个 `edge_id` 必须在主图存在。

## 字段定义

```json
{
  "case_id": "<回填>",
  "status": "in_progress | success | partial | unable",
  "status_reason": "<unable/partial 时必填；查询不足时写明真实数量和原因>",
  "sources": [
    {"source_id":"primary","jats_file":"primary-material.json","doi":"10.xxxx/aaaa","title":"…","authors":["…"]},
    {"source_id":"secondary","jats_file":"secondary-material.json","doi":"10.yyyy/bbbb","title":"…","authors":["…"]}
  ],
  "nodes": [
    {"entity_id":"E1","type":"method|material|task|metric|researcher|conclusion","label":"…","aliases":["…"],"source_id":"primary","first_mention":"pri-p-0007","attribution":"self|reported","homonym":false,"evidence":{"source_id":"primary","paragraph_id":"pri-p-0007","quote":"…","strength":"strong","note":"可选备注"}}
  ],
  "edges": [
    {"edge_id":"R1","source":"E1","target":"E3","predicate":"uses|compares|outperforms|supports|contradicts|same_concept|…","condition":"…","evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031","quote":"…","strength":"strong"}]}
  ],
  "queries": [
    {
      "query":"哪些方法优于基线？",
      "query_spec":{"op":"filter_edges","predicate":"outperforms","source_id":"primary","label_contains":"baseline"},
      "result_subgraph":[{"edge_id":"R1","source":"E1","predicate":"outperforms","target":"E3"}],
      "evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031","quote":"…","strength":"strong"}],
      "execution":{"operation":"filter_edges","matched_edge_ids":["R1"],"result_count":1},
      "uncertain_relations":["…"]
    }
  ],
  "provenance": [],
  "uncertainties": ["需要人工确认的清单"],
  "tool_commands": ["实际执行的 query/validate 命令"]
}
```

`query_spec` 的完整 DSL 与 path 额外输出见 `references/graph-query.md`。

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` / `status` / `status_reason` | 是 | 运行状态三件套 |
| `sources[]` | 是 | 论文级来源清单；`source_id` 取自 corpus manifest。`doi`/`title`/`authors` 只能来自输入 manifest 与对应 JATS，禁止从首篇推断第二篇 |
| `nodes[]` | 是 | 实体，含 `entity_id`/`type`/`label`/`aliases`/`attribution`/`homonym`/单对象 `evidence`；`first_mention` 用 paragraph_id |
| `edges[]` | 是 | 主图关系，含唯一 `edge_id`、存在的 `source`/`target`、`predicate`、`condition` 与数组 `evidence`；跨篇边必须有双侧证据 |
| `queries[].query` | 是 | 人读问题，仅展示；改它不会改变执行语义 |
| `queries[].query_spec` | 是 | 唯一执行逻辑：`filter_edges` / `neighbors` / `path`；规格错误、缺规格或悬空 edge_id 均失败 |
| `queries[].result_subgraph` | 工具写 | 主图边投影，稳定按 `edge_id` 排序；真实空结果为 `[]` |
| `queries[].evidence` | 工具写 | 命中主图边的证据继承结果，稳定精确去重；空结果为 `[]` |
| `queries[].execution` | 工具写 | `operation`、`matched_edge_ids`、`result_count`；path 另有排序后的 `paths` |
| `queries[].uncertain_relations` | 可选 | Agent 对语义不确定性的判断；工具不证明其语义，也不据此补边 |
| `uncertainties` | 是 | 无法判断/需人工确认项 |
| `tool_commands` | 推荐 | 实际命令，用于复现 |

`matched_edge_ids` 与 `result_subgraph` 顺序一致且按 `edge_id` 排序；`result_count` 是命中边数，不是 path 数。空路径或过滤无命中不会伪造“兜底”边。

## 执行与验证

```bash
python3 scripts/kg_tool.py query --graph /app/output/result.json --out /app/output/executed.json
python3 scripts/kg_tool.py validate --graph /app/output/executed.json --report /app/output/report.json
# 或原子覆盖原文件：
python3 scripts/kg_tool.py query --graph /app/output/result.json --update
python3 scripts/kg_tool.py validate --graph /app/output/result.json --report /app/output/report.json
```

`validate` 独立重算每条规格并精确比较子图、继承证据及整个 `execution`。图结构错误、缺规格、计算结果不符、状态数量约束不符均退出 1；通过退出 0。具体 DSL 和失败语义见 graph-query.md。

## 状态与降级

- `success`：至少 3 条 `query_spec` 均真实执行且 validate 通过，主图节点/边可复核；少于 3 条直接失败。
- `partial`：可少于 3 条，但只交付真实执行的查询；`status_reason` 必须写明真实数量（Arabic 数字，供机器核查）和未完成原因。例如“真实执行 2 条查询；第 3 条因材料解析失败未完成”。
- `unable`：无法处理（材料缺失/加密/无文本层），写明原因，不编造。

## 诚实原则

实体只取论文真实出现的对象；关系只有证据才连边；别名合并记录依据、同名冲突不错误合并；跨篇同名词条默认拆分，合并须有双侧 paragraph_id 证据；`same_concept` 必须有双侧四元组 quote，条件统一为“同名概念，未证实同一物理实例”，不得由单侧引文推断“无共同 checkpoint”；数值/单位/限定词逐字保留。工具验证图与查询的一致性，不替代 Agent 对原文语义、证据强度和 `uncertain_relations` 的判断。
