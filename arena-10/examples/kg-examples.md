# 知识图谱示例（标注为示例，非正式案例）

> 以下均为**示意**，用于说明实体识别、对齐、关系抽取、来源绑定、查询与增量的格式，不冒充正式评测案例结果。

## 示例 1：实体识别（抽得准）

```json
{"entity_id":"E1","type":"method","label":"Model M","aliases":["M","the proposed model"],"first_mention":"§2 ¶1","attribution":"self"}
{"entity_id":"E2","type":"metric","label":"accuracy","aliases":["ACC"],"first_mention":"§5 ¶1","attribution":"self"}
{"entity_id":"E3","type":"method","label":"baseline B","aliases":["B"],"first_mention":"§5 ¶1","attribution":"reported"}
```

> 基线 B 若为他人方法，`attribution=reported`，不并入作者结论。

## 示例 2：实体对齐（对得齐）

```json
{"entity_id":"E1","label":"stochastic gradient descent","aliases":["SGD","随机梯度下降"],"merge_basis":"§1 首现展开，全篇同指","homonym":false}
{"entity_id":"E9","label":"Model A","aliases":["A"],"homonym":true,"note":"与另一论文的 Model A 同名不同物"}
```

## 示例 3：关系抽取 + 来源（连得对 + 回得去）

```json
{"edge_id":"R1","source":"E1","predicate":"outperforms","target":"E3","condition":"on dataset D, p<0.05",
 "evidence":{"evidence_text":"Model M achieves 0.81 vs baseline 0.79 (p<0.05)","evidence_location":"paper=Demo, §5 Table 2","evidence_strength":"strong"}}
```

> 原文若只说"比较"未说更优，用 `compares` 而非 `outperforms`。

## 示例 4：查询（查得到）

```json
{"query":"哪些方法在数据集 D 上优于基线？",
 "result_subgraph":[{"source":"E1","predicate":"outperforms","target":"E3"}],
 "evidence":["paper=Demo, §5 Table 2"],
 "uncertain_relations":["E1 vs E4 是否可比较，原文未明说"]}
```

## 示例 5：增量更新

```json
{"action":"merge","new_entity":"Model M (paper2)","merged_into":"E1","merge_basis":"paper2 §1 与 paper1 §2 为同一模型"}
{"action":"conflict","edge1":"R1 (A 优于 B)","edge2":"R9 (B 优于 A)","note":"paper1 vs paper3 条件不同，保留两条边并标 conflict"}
```
