# result.json / 图谱导出契约（Output Schema）

## 硬性要求

1. `case_id` 原样回填；`status` + `status_reason` 必填。
2. **output_contract**：`/input/case.json` 里 `output_contract` 声明的每个字段都要出现，字段名与类型一致。
3. 顶层 `sources` 数组登记每篇论文；图谱可机器读取：`nodes` + `edges` + `provenance`。每条边的 `evidence` **一律为数组**，包含一个或多个 `{source_id, paragraph_id, quote, strength}` 四元组；跨篇边必须有双侧来源的四元组。节点 `evidence` 可保留单个四元组对象；查询 `evidence` 保持数组。

## 字段定义

```json
{
  "case_id": "<回填>",
  "status": "in_progress | success | partial | unable",
  "status_reason": "<unable/partial 时必填>",
  "sources": [
    {"source_id":"primary","jats_file":"primary-material.json","doi":"10.xxxx/aaaa","title":"…","authors":["…"]},
    {"source_id":"secondary","jats_file":"secondary-material.json","doi":"10.yyyy/bbbb","title":"…","authors":["…"]}
  ],
  "nodes": [
    {"entity_id":"E1","type":"method|material|task|metric|researcher|conclusion","label":"…","aliases":["…"],"first_mention":"pri-p-0007","attribution":"self|reported","homonym":false,"evidence":{"source_id":"primary","paragraph_id":"pri-p-0007","quote":"…","strength":"strong","note":"可选 human-readable 备注"}}
  ],
  "edges": [
    {"edge_id":"R1","source":"E1","target":"E3","predicate":"uses|compares|outperforms|supports|contradicts|same_concept|…","condition":"…","evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031","quote":"…","strength":"strong"}]}
  ],
  "queries": [
    {"query":"…","result_subgraph":[{"source":"E1","predicate":"…","target":"E3"}],"evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031","quote":"…","strength":"strong"}],"uncertain_relations":["…"]}
  ],
  "provenance": [],
  "uncertainties": ["需要人工确认的清单"],
  "tool_commands": ["实际执行的命令，用于复现与审计"]
}
```

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` / `status` / `status_reason` | 是 | 运行状态三件套 |
| `sources[]` | 是 | 论文级来源清单：`source_id` 取自 corpus manifest 的论文标识；`doi`/`title`/`authors` **只能来自输入 manifest 与对应 JATS**，禁止从首篇推断第二篇 |
| `nodes[]` | 是 | 实体，含 `entity_id`/`type`/`label`/`aliases`/`attribution`/`homonym`/`evidence`；`first_mention` 用 paragraph_id |
| `edges[]` | 是 | 关系，含 `source`/`target`/`predicate`/`condition`/`evidence`；跨篇 `same_concept` 必须同时包含 primary/secondary 双侧证据 |
| `evidence` | 是 | 四元组为 `{source_id, paragraph_id, quote(≤30字), strength}`，`note` 可选；**edges 与 queries 的 evidence 均为数组**，nodes 可为单个四元组对象 |
| `queries[]` | 是 | ≥3 个真实查询 + 结果子图 + 证据 + 不确定关系 |
| `uncertainties` | 是 | 无法判断/需人工确认项 |
| `tool_commands` | 推荐 | 实际命令，用于复现 |

## 状态与降级

- `success`：所有 output_contract 字段有值，节点/边可复核。
- `partial`：部分完成（个别实体对齐待定、关系证据不足）。
- `unable`：无法处理（材料缺失/加密/无文本层），写明原因，不编造。

## 诚实原则

实体只取论文真实出现的对象；关系只有证据才连边；别名合并记录依据、同名冲突不错误合并；跨篇同名词条默认拆分，合并须有双侧 paragraph_id 证据；`same_concept` 必须有双侧四元组 quote，条件统一为“同名概念，未证实同一物理实例”，不得由单侧引文推断“无共同 checkpoint”；数值/单位/限定词逐字保留；不确定就标 `uncertain`，不补造。
