# 知识图谱示例（标注为示例，非正式案例）

> 以下均为**示意**，用于说明实体识别、对齐、关系抽取、来源绑定、查询与增量的格式，不冒充正式评测案例结果。文中 `source_id`、`paragraph_id`（如 `primary`、`pri-p-0007`）均为**自造示意 ID**，实际运行须取自输入 corpus manifest 与组织方 JATS 段落 ID。

## 示例 1：实体识别（抽得准）

```json
{"entity_id":"E1","type":"method","label":"Model M","aliases":["M","the proposed model"],"first_mention":"pri-p-0007","attribution":"self","source_id":"primary"}
{"entity_id":"E2","type":"metric","label":"accuracy","aliases":["ACC"],"first_mention":"pri-p-0030","attribution":"self","source_id":"primary"}
{"entity_id":"E3","type":"method","label":"baseline B","aliases":["B"],"first_mention":"pri-p-0030","attribution":"reported","source_id":"primary"}
```

> 基线 B 若为他人方法，`attribution=reported`，不并入作者结论。

## 示例 2：实体对齐（对得齐）

```json
{"entity_id":"E1","label":"stochastic gradient descent","aliases":["SGD","随机梯度下降"],"source_id":"primary","merge_basis":"pri-p-0003 首现展开，全篇同指","homonym":false}
{"entity_id":"E9","label":"Model A","aliases":["A"],"source_id":"secondary","homonym":false,"status":"uncertain","note":"与另一论文的 Model A 仅确认同名，实例关系待确认"}
```

## 示例 3：关系抽取 + 来源（连得对 + 回得去）

```json
{"edge_id":"R1","source":"E1","predicate":"outperforms","target":"E3","condition":"on dataset D, p<0.05",
 "evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031","quote":"Model M achieves 0.81 vs 0.79","strength":"strong","note":"human-readable：§5 Table 2"}]}
```

> 原文若只说"比较"未说更优，用 `compares` 而非 `outperforms`。

## 示例 4：查询（查得到）

```json
{"query":"哪些方法在数据集 D 上优于基线？",
 "result_subgraph":[{"source":"E1","predicate":"outperforms","target":"E3"}],
 "evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031","quote":"Model M achieves 0.81 vs 0.79","strength":"strong"}],
 "uncertain_relations":["E1 vs E4 是否可比较，原文未明说"]}
```

## 示例 5：增量更新与跨篇对齐（不错误合并）

paper2（`secondary`）的 Model M 建为**独立实体 E7**，与 paper1（`primary`）的 E1 各自挂自己 `source_id` 的证据：

```json
{"action":"add","entity_id":"E7","type":"method","label":"Model M","aliases":["M"],"source_id":"secondary",
 "evidence":{"source_id":"secondary","paragraph_id":"sec-p-0012","quote":"We introduce Model M","strength":"strong"}}
{"edge_id":"R12","source":"E7","predicate":"same_concept","target":"E1",
 "condition":"同名概念，未证实同一物理实例",
 "evidence":[
   {"source_id":"primary","paragraph_id":"pri-p-0007","quote":"We call our method Model M","strength":"strong"},
   {"source_id":"secondary","paragraph_id":"sec-p-0012","quote":"We introduce Model M","strength":"strong"}
 ]}
{"action":"conflict","edge1":"R1 (A 优于 B)","edge2":"R9 (B 优于 A)","note":"primary vs secondary 条件不同，保留两条边并标 conflict"}
```

> **为何不合并**：现有双侧引文只分别证明两篇都出现"Model M"，没有同一样品编号、同一模型 checkpoint 或同一数据集版本证据，`merge_basis` 不足以合并；故建 `same_concept` 边并注明“同名概念，未证实同一物理实例”，而非把 E7 并入 E1。这里既没有证实同一实例，也没有证明它们必然不同或“无共同 checkpoint”。
