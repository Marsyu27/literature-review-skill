# 来源绑定与证据强度（Source Binding）

每个节点、每条边都能**回得去**原文。

## 必填锚点字段（四元组）

| 字段 | 含义 |
|---|---|
| `source_id` | 论文标识，取自输入 corpus manifest 的论文标识（如 `primary` / `secondary`），**禁止自编** |
| `paragraph_id` | 组织方 JATS 段落 ID（不是 PDF 页码，也不是自建 `§/¶`） |
| `quote` | ≤30 字原文短引，逐字摘自该段落 |
| `strength` | strong / medium / weak |

可选 `note`：human-readable 备注（如旧式 `§3 ¶2, Table 2` 的人工可读位置说明），仅作备注，不作锚点依据。

## 证据强度

| 强度 | 判定 |
|---|---|
| `strong` | 原文直接陈述 |
| `medium` | 由原文推断（组合多处、逻辑推导，`basis` 写明步骤） |
| `weak` | 转述、综述、共现、推测 |

## 规则

1. `source_id` + `paragraph_id` 指向**真正对应**的论文与 JATS 段落，不写笼统的"见正文"；`quote` 必须逐字出自该段落。
2. **边的 `evidence` 一律为数组**，即使只有一个锚点也写成 `[{...}]`；节点沿用单个四元组对象，查询 `evidence` 为数组。证据跨段落/跨篇 → 在数组中列出所有锚点（每条各自带 `source_id` + `paragraph_id`）；跨篇边必须同时有 primary 与 secondary 的双侧证据，单侧引文不能闭合跨篇关系。查询证据只能由 `scripts/kg_tool.py query` 从命中主图边继承、稳定去重，Agent 不得为查询另写或改引文；validate 会独立重算并拒绝不一致内容。
3. 无法确定位置 → 标 `uncertain`，不伪造 paragraph_id。
4. 转述/综述证据 → 标 `weak` 并注明"非作者结论"。
5. 根 DOI/title/authors 属首篇，不得套到第二篇；每篇的元数据只取自 manifest 与其自身 JATS。
6. `same_concept` 的双侧引文只分别支持“各篇出现该名称”；`condition` 固定写“同名概念，未证实同一物理实例”。除非原文另有两侧实例证据，不得写成“非同一实例”“无共同 checkpoint”或“两篇独立训练”。

## 样例（示意 ID）

```json
{"edge_id":"R1","evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031",
 "quote":"Model M achieves 0.81 accuracy","strength":"strong",
 "note":"human-readable：§5 Table 2"}]}
```
