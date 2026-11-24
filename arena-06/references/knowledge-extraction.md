# 知识点提取、归一化与去重（Knowledge Extraction）

把重要概念、变量、方法、结论拆成**可检索条目**，避免重复或矛盾。每条保留正式 `source_anchor`；success 下每条都必须有真实有效锚点。

## 条目类型

| type | 含义 |
|---|---|
| `concept` | 概念/术语 |
| `variable` | 变量/参数/符号 |
| `method` | 方法/算法/流程 |
| `result` | 结果/数值结论 |
| `metric` | 评价指标 |
| `limitation` | 局限/边界 |

## 条目字段

```json
{"id": "kp-001", "type": "concept", "label": "TEF", "value": "热强化因子 = (Nu/Nu0)/(f/f0)^(1/3)",
 "source_anchor": "§2 ¶1", "status": "ok"}
```

## 归一化

1. 缩写与全称统一（`SGD` ↔ `stochastic gradient descent` 归为一条，首现展开）。
2. 同义表述统一（`efficiency` 与 `performance` 若指同一量，归为一条并注明）。
3. 术语与我的术语表（若有）一致。

## 去重与冲突

1. 同一知识点只建一条，不因出现位置不同而重复。
2. 原文表述矛盾 → 保留**两处原文**并标 `status=conflict`，`value` 写两处原文，`note` 说明冲突位置；**不擅自取舍**。
3. 无法确定是否同一概念 → 分两条并在 `uncertainties` 提示"可能重复，待人工合并"。

## 可检索性

- `label` 用规范化术语；`value` 用一句话可比较的表述。
- 支持按 `type`、`label` 检索；跨论文比较时对齐 `label` 与 `metric`。

## 样例（示意）

```json
[
  {"id":"kp-001","type":"variable","label":"TEF","value":"热强化因子","source_anchor":"§2 ¶1","status":"ok"},
  {"id":"kp-002","type":"result","label":"最优 TEF","value":"1.42 @ Re=1e4","source_anchor":"§4 Table 2","status":"ok"},
  {"id":"kp-003","type":"limitation","label":"适用范围","value":"仅湍流、Re=1e4","source_anchor":"§5 ¶2","status":"ok"}
]
```
