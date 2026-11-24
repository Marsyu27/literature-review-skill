# 实体对齐（Entity Alignment）

处理别名、缩写、大小写、全称简称与**同名冲突**，既不重复建节点，也不错误合并。

## 归一规则

1. 缩写与全称统一（`SGD` ↔ `stochastic gradient descent` 归为一个 `entity_id`，`aliases` 列全）。
2. 大小写、连字符、单复数差异统一（`State-of-the-art` → `state-of-the-art`）。
3. 同一对象的多种写法 → 合并为一个节点，记录合并依据 `merge_basis`。

## 同名冲突（homonym）

- 同名不同对象（如两个"Model A"来自不同论文）→ **分节点**，标 `homonym=true`，`note` 说明区别。
- 无法确定是否同一对象 → 分节点 + `status=uncertain`，写入 `uncertainties` 待人工合并。

## 合并依据

每次合并记录 `merge_basis`：如"原文 §1 首次定义 `SGD (stochastic gradient descent)`，后续 §2–§5 均指同一对象"。

## 样例（示意）

```json
{"entity_id":"E1","label":"stochastic gradient descent","aliases":["SGD","随机梯度下降"],"merge_basis":"§1 首现展开，全篇同指","homonym":false}
{"entity_id":"E9","label":"Model A","aliases":["A"],"homonym":true,"note":"与另一论文的 Model A 同名不同物，来自不同文献"}
```
