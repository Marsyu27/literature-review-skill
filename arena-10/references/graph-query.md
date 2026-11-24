# 图谱查询与增量更新（Graph Query & Incremental Update）

图谱要能**回答真实查询**，并能在新论文加入时**保留既有节点与编号**。

## 图谱查询（至少 3 个真实查询）

每个查询记录：
- `query`：自然语言问题。
- `result_subgraph`：命中的节点与边。
- `evidence`：支撑证据与位置。
- `uncertain_relations`：无法确定的关系（标出，不硬答）。

## 查询示例模板（示意）

1. "方法 M 用到了哪些数据集？" → `(M, uses, D)` 子图 + 证据。
2. "哪些方法在数据集 D 上优于基线？" → `(X, outperforms, baseline)` 子图 + 证据。
3. "结论 C 由哪些结果支持？" → `(result, supports, C)` 子图 + 证据。

## 增量更新

1. 新论文加入 → 保留既有 `entity_id` 与 `edge_id`，新节点从新编号开始。
2. 新增：新实体/新关系 → 直接追加。
3. 合并：新论文中的实体与既有实体对齐（别名规则）→ 合并到原 `entity_id`，记录 `merge_basis`。
4. 冲突：新论文与既有关系矛盾（如 A 优于 B vs B 优于 A）→ 保留两条边 + 标 `conflict` + 注明论文与条件，不擅自删改。

## 导出

- 导出可读图谱文件：JSON（`nodes` + `edges` + `provenance`），字段见 output-schema.md。
- 每条边/节点带来源与证据强度，支持复核。

## 样例（示意）

```json
{"query":"哪些方法在数据集 D 上优于基线？",
 "result_subgraph":[{"source":"E1","predicate":"outperforms","target":"E3"}],
 "evidence":[{"source_id":"primary","paragraph_id":"pri-p-0031","quote":"Model M achieves 0.81 vs 0.79","strength":"strong"}],
 "uncertain_relations":["E1 vs E4 是否可比较，原文未明说"]}
```

> evidence 一律用 `{source_id, paragraph_id, quote, strength}` 四元组（示意 ID 见 kg-examples.md 文件头）。
