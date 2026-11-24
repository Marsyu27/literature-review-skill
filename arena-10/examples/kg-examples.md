# 知识图谱示例（标注为示例，非正式案例）

> 以下是一个两篇论文的同步示意，用同一组节点和边说清实体、关系、来源及真实工具输出，不冒充正式评测结果。`primary`/`secondary`、paragraph ID、引文均为自造示例；实际运行必须取自输入 manifest 与两篇组织方 JATS。所有查询均可由 `scripts/kg_tool.py` 重算。

## 1. 两个独立来源与节点（抽得准）

```json
{"source_id":"primary","jats_file":"primary-material.json"}
{"source_id":"secondary","jats_file":"secondary-material.json"}
```

```json
{"entity_id":"E1","type":"method","label":"Model M","aliases":["M"],"source_id":"primary","first_mention":"pri-p-0007","attribution":"self","homonym":false,"evidence":{"source_id":"primary","paragraph_id":"pri-p-0007","quote":"We call our method Model M","strength":"strong"}}
{"entity_id":"E2","type":"metric","label":"accuracy","aliases":["ACC"],"source_id":"primary","first_mention":"pri-p-0030","attribution":"self","homonym":false,"evidence":{"source_id":"primary","paragraph_id":"pri-p-0030","quote":"accuracy","strength":"strong"}}
{"entity_id":"E3","type":"method","label":"baseline B","aliases":["B"],"source_id":"primary","first_mention":"pri-p-0030","attribution":"reported","homonym":false,"evidence":{"source_id":"primary","paragraph_id":"pri-p-0030","quote":"baseline B","strength":"strong"}}
{"entity_id":"E7","type":"method","label":"Model M","aliases":["M"],"source_id":"secondary","first_mention":"sec-p-0012","attribution":"self","homonym":true,"status":"uncertain","evidence":{"source_id":"secondary","paragraph_id":"sec-p-0012","quote":"We introduce Model M","strength":"strong"}}
{"entity_id":"E8","type":"method","label":"stochastic gradient descent","aliases":["SGD"],"source_id":"secondary","first_mention":"sec-p-0013","attribution":"self","homonym":false,"merge_basis":"sec-p-0013 展开 SGD 全称","evidence":{"source_id":"secondary","paragraph_id":"sec-p-0013","quote":"SGD (stochastic gradient descent)","strength":"strong"}}
{"entity_id":"E9","type":"conclusion","label":"Conclusion C","aliases":[],"source_id":"secondary","first_mention":"sec-p-0014","attribution":"self","homonym":false,"evidence":{"source_id":"secondary","paragraph_id":"sec-p-0014","quote":"Conclusion C","strength":"strong"}}
```

E1 与 E7 跨篇同名但实例身份未定，故分节点；E7 的 `homonym:true` 与 `status:uncertain` 保留边界。E8 的 SGD/全称是**篇内**别名归一，不能据此外推跨篇实例合并。基线 B 若为他人方法，`attribution=reported`，不并入作者结论。

## 2. 主图边：关系抽取 + 来源（连得对、回得去）

```json
{"edge_id":"R1","source":"E1","predicate":"outperforms","target":"E3","condition":"on dataset D, p<0.05","evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031","quote":"Model M: 0.81 vs 0.79","strength":"strong"}]}
{"edge_id":"R12","source":"E7","predicate":"same_concept","target":"E1","condition":"同名概念，未证实同一物理实例","evidence":[{"source_id":"primary","paragraph_id":"pri-p-0007","quote":"We call our method Model M","strength":"strong"},{"source_id":"secondary","paragraph_id":"sec-p-0012","quote":"We introduce Model M","strength":"strong"}]}
{"edge_id":"R13","source":"E7","predicate":"uses","target":"E8","condition":"secondary training procedure","evidence":[{"source_id":"secondary","paragraph_id":"sec-p-0013","quote":"Model M uses SGD","strength":"strong"}]}
{"edge_id":"R14","source":"E8","predicate":"supports","target":"E9","condition":"secondary ablation","evidence":[{"source_id":"secondary","paragraph_id":"sec-p-0014","quote":"SGD ablation supports C","strength":"strong"}]}
```

R12 两端分属 secondary/primary，故必须同时有两篇四元组证据；单侧引文不能通过工具校验。原文若只说“比较”而未说更优，应使用 `compares` 而非 `outperforms`。

## 3. 查询规格与工具计算结果（查得到）

以下四条对应上面的主图边。实际工作流只手写 `query`、`query_spec` 和可选 `uncertain_relations`，其余三组字段由 `kg_tool.py query` 覆盖生成。

### 3.1 filter_edges：名称含 Alpha 的 uses 边（此处真实空结果）

```json
{"query":"哪些名称含 Alpha 的实体存在 uses 边？","query_spec":{"op":"filter_edges","predicate":"uses","label_contains":"alpha"},"result_subgraph":[],"evidence":[],"execution":{"operation":"filter_edges","matched_edge_ids":[],"result_count":0},"uncertain_relations":[]}
```

空数组是真实执行结果，不补兜底边。若用 `label_contains:"model m"`，Unicode 大小写归一后会命中 R13。

### 3.2 filter_edges：primary 中的 outperforms 边

```json
{"query":"primary 中哪些方法优于 baseline？","query_spec":{"op":"filter_edges","predicate":"outperforms","source_id":"primary","label_contains":"BASELINE"},"result_subgraph":[{"edge_id":"R1","source":"E1","predicate":"outperforms","target":"E3"}],"evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031","quote":"Model M: 0.81 vs 0.79","strength":"strong"}],"execution":{"operation":"filter_edges","matched_edge_ids":["R1"],"result_count":1},"uncertain_relations":[]}
```

### 3.3 neighbors：E7 的 uses 出边

```json
{"query":"secondary 的 Model M 使用了什么？","query_spec":{"op":"neighbors","seed":"E7","direction":"out","predicate":"uses","source_id":"secondary"},"result_subgraph":[{"edge_id":"R13","source":"E7","predicate":"uses","target":"E8"}],"evidence":[{"source_id":"secondary","paragraph_id":"sec-p-0013","quote":"Model M uses SGD","strength":"strong"}],"execution":{"operation":"neighbors","matched_edge_ids":["R13"],"result_count":1},"uncertain_relations":[]}
```

### 3.4 path：E7 到 E3 的有向最短路径

```json
{"query":"secondary 的 Model M 经哪些边连接 primary 的 baseline B？","query_spec":{"op":"path","start":"E7","end":"E3","max_depth":2},"result_subgraph":[{"edge_id":"R1","source":"E1","predicate":"outperforms","target":"E3"},{"edge_id":"R12","source":"E7","predicate":"same_concept","target":"E1"}],"evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031","quote":"Model M: 0.81 vs 0.79","strength":"strong"},{"source_id":"primary","paragraph_id":"pri-p-0007","quote":"We call our method Model M","strength":"strong"},{"source_id":"secondary","paragraph_id":"sec-p-0012","quote":"We introduce Model M","strength":"strong"}],"execution":{"operation":"path","matched_edge_ids":["R1","R12"],"result_count":2,"paths":[{"node_ids":["E7","E1","E3"],"edge_ids":["R12","R1"]}]},"uncertain_relations":["E7 与 E1 是否同一物理实例未确定；same_concept 不是实例合并"]}
```

## 4. 增量更新与跨篇对齐（不错误合并）

新增 third 论文时保留 E1/E3/E7 和 R1/R12/R13/R14 的编号，新对象从新编号开始；条件冲突的比较边保留双方及 `conflict` 标记。R12 的双侧引文只分别证明两篇都出现“Model M”，没有同一样品编号、模型 checkpoint 或数据集版本证据，因此不能合并 E7/E1，同样也不能反向证明“无共同 checkpoint”。

完成任何主图增量后，在 Skill 根目录重新运行：

```bash
python3 scripts/kg_tool.py query --graph result.json --update
python3 scripts/kg_tool.py validate --graph result.json --report report.json
```

禁止沿用手工维护的旧查询子图或证据；它们只能由新主图重新计算。
