# 结构化笔记示例（标注为示例，非正式案例）

> 以下均为**示意**，用于说明输出格式与对齐/锚点原则，不冒充正式评测案例结果。所有锚点都使用正式字段，不嵌在正文字符串值中。

## 示例 1：章节对齐（对得上）

```json
{"id":"§2","title":"Methods","purpose":"描述模型与训练流程","method":"数据集 D、超参 …","results":"—","transition":"承接 §1 的问题定义，为 §3 实验提供方法","source_anchor":"§2","status":"ok"}
```

## 示例 2：论文卡片 + 顶层配套锚点（留得住 + 找得回）

```json
{
  "paper_card": {
    "research_question": "方法 M 是否在 X 条件下优于基线 B",
    "data": "数据集 D，n=1000",
    "findings": "准确率 0.81 vs 0.79，p<0.05",
    "limitations": "仅在 X 条件下验证；单一中心样本"
  },
  "paper_card_anchors": [
    {"field":"research_question","source_anchor":"§1 ¶2"},
    {"field":"data","source_anchor":"§3 ¶1"},
    {"field":"findings","source_anchor":"§4 Table 2","quote":"Accuracy reaches 0.81 versus 0.79 baseline (p<0.05)"},
    {"field":"limitations","source_anchor":"§5 ¶2"}
  ]
}
```

## 示例 3：知识点去重与归一化（用得上）

- 原文三处分别写 `SGD`、`stochastic gradient descent`、`随机梯度下降` → 归并为一条：
  `{"id":"kp-001","type":"method","label":"SGD","value":"随机梯度下降","source_anchor":"§2 ¶1; §3 ¶2; §4 ¶1","status":"ok"}`

## 示例 4：原文矛盾，不擅自取舍

- 原文 §3 报 `TEF=1.42`，§5 报 `TEF=1.38`（不同工况）。
  `{"id":"kp-002","type":"result","label":"最优 TEF","value":"1.42（工况A）；1.38（工况B）","source_anchor":"§3 Table 1; §5 Table 3","status":"conflict","note":"两处工况不同，非笔误，需人工确认"}`

## 示例 5：未报告如实标注

- 原文未给样本量时，`paper_card.data` 写 `"数据集 D（样本量 not_reported）"`，配套锚点写 `{"field":"data","source_anchor":"§3 ¶1"}`，并把未报告项写入 `uncertainties`。
- 若 partial 中连位置也无法确认，可写 `{"field":"data","status":"uncertain","reason":"原文定位待确认"}`，但必须有其他真实有效锚点，并在 `status_reason`/`uncertainties` 交代；success 不允许这样缺锚点。
