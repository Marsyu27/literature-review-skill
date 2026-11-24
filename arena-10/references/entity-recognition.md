# 实体识别（Entity Recognition）

抽取论文里**真实出现**的科研对象，不凭常识补全。

## 实体类型（受控）

| 类型 | 含义 | 示例 |
|---|---|---|
| `researcher` | 研究者/作者/机构 | 某作者、某团队 |
| `material` | 材料/数据/数据集/化合物 | 数据集 D、蛋白质 P |
| `method` | 方法/模型/算法/流程 | 模型 M、算法 A |
| `task` | 任务/问题 | 分类、翻译、预测 |
| `metric` | 评价指标 | 准确率、F1、TEF |
| `conclusion` | 结论/发现 | "A 优于 B" |

## 规则

1. **真实出现**：实体在原文中被提及，保留原文表述与位置；原文没有的概念不建节点。
2. **自述 vs 转述**：
   - 作者自述（本文的方法/结果）→ `attribution=self`。
   - 引用他人（"Smith 等人提出 X""综述转述"）→ `attribution=reported`。
   - 转述实体不并入作者结论，可作为独立节点但标来源。
3. **保留原文位置**：每个实体记 `source_id`（manifest 论文标识）与 `first_mention`（组织方 JATS `paragraph_id`）及原文写法。
4. 指标等数值 → 实体为指标，数值作为属性/边，不把数值当实体。

## 样例（示意）

```json
{"entity_id":"E1","type":"method","label":"Model M","aliases":["M","the proposed model"],"source_id":"primary","first_mention":"pri-p-0007","attribution":"self"}
{"entity_id":"E2","type":"metric","label":"accuracy","aliases":["ACC"],"source_id":"primary","first_mention":"pri-p-0030","attribution":"self"}
```
