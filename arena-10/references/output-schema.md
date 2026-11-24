# result.json / 图谱导出契约（Output Schema）

## 硬性要求

1. `case_id` 原样回填；`status` + `status_reason` 必填。
2. **output_contract**：`/input/case.json` 里 `output_contract` 声明的每个字段都要出现，字段名与类型一致。
3. 图谱可机器读取：`nodes` + `edges` + `provenance`，每个节点/边带来源与证据强度。

## 字段定义

```json
{
  "case_id": "<回填>",
  "status": "success | partial | unable",
  "status_reason": "<unable/partial 时必填>",
  "nodes": [
    {"entity_id":"E1","type":"method|material|task|metric|researcher|conclusion","label":"…","aliases":["…"],"first_mention":"§2 ¶1","attribution":"self|reported","homonym":false,"evidence":{"evidence_text":"…","evidence_location":"paper=…, §2 ¶1","evidence_strength":"strong"}}
  ],
  "edges": [
    {"edge_id":"R1","source":"E1","target":"E3","predicate":"uses|compares|outperforms|supports|contradicts|…","condition":"…","evidence":{"evidence_text":"…","evidence_location":"…","evidence_strength":"strong"}}
  ],
  "queries": [
    {"query":"…","result_subgraph":[{"source":"E1","predicate":"…","target":"E3"}],"evidence":["…"],"uncertain_relations":["…"]}
  ],
  "uncertainties": ["需要人工确认的清单"],
  "tool_commands": ["实际执行的命令，用于复现与审计"]
}
```

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` / `status` / `status_reason` | 是 | 运行状态三件套 |
| `nodes[]` | 是 | 实体，含 `entity_id`/`type`/`label`/`aliases`/`attribution`/`homonym`/`evidence` |
| `edges[]` | 是 | 关系，含 `source`/`target`/`predicate`/`condition`/`evidence` |
| `queries[]` | 是 | ≥3 个真实查询 + 结果子图 + 证据 + 不确定关系 |
| `uncertainties` | 是 | 无法判断/需人工确认项 |
| `tool_commands` | 推荐 | 实际命令，用于复现 |

## 状态与降级

- `success`：所有 output_contract 字段有值，节点/边可复核。
- `partial`：部分完成（个别实体对齐待定、关系证据不足）。
- `unable`：无法处理（材料缺失/加密/无文本层），写明原因，不编造。

## 诚实原则

实体只取论文真实出现的对象；关系只有证据才连边；别名合并记录依据、同名冲突不错误合并；数值/单位/限定词逐字保留；不确定就标 `uncertain`，不补造。
