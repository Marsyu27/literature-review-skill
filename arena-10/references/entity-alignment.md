# 实体对齐（Entity Alignment）

处理别名、缩写、大小写、全称简称与**同名冲突**，既不重复建节点，也不错误合并。

## 归一规则（仅限篇内）

1. 缩写与全称统一（`SGD` ↔ `stochastic gradient descent` 归为一个 `entity_id`，`aliases` 列全）。
2. 大小写、连字符、单复数差异统一（`State-of-the-art` → `state-of-the-art`）。
3. 同一对象的多种写法 → 合并为一个节点，记录合并依据 `merge_basis`。

## 跨篇合并硬规则

- 缩写/大小写/连字符归一**仅限篇内**，不外推到另一篇。
- **跨篇同名词条默认拆分**为不同节点，各自挂各自 `source_id` 的证据。
- **跨篇合并且仅当同一物理实例**：两篇明确指向同一样品编号 / 同一模型 checkpoint / 同一数据集版本。
- 合并时 `merge_basis` 必须写明**双方 paragraph_id 双侧证据**；只有概念同名而无双侧实例证据 → 不合并，建 `same_concept` 边并注明"概念同名，非同一实例"。
- 相同通用方法/材料术语不代表两篇使用了相同物理样品、模型实例、数据集或实验条件。

## 同名冲突（homonym）

- 同名不同对象（如两个"Model A"来自不同论文）→ **分节点**，标 `homonym=true`，`note` 说明区别。
- 无法确定是否同一对象 → 分节点 + `status=uncertain`，写入 `uncertainties` 待人工合并。

## 合并依据

每次合并记录 `merge_basis`：篇内如"原文 pri-p-0003 首次定义 `SGD (stochastic gradient descent)`，后续段落均指同一对象"；跨篇须含双方 paragraph_id。

## 样例（示意 ID）

```json
{"entity_id":"E1","label":"stochastic gradient descent","aliases":["SGD","随机梯度下降"],"source_id":"primary","merge_basis":"pri-p-0003 首现展开，全篇同指","homonym":false}
{"entity_id":"E9","label":"Model A","aliases":["A"],"source_id":"secondary","homonym":true,"note":"与 primary 的 Model A 同名不同物，来自不同文献"}
```
