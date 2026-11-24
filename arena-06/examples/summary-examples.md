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

## 示例 6：完整章节覆盖与 partial 逐节占位

假设索引全集是 `§1=(preamble)`、`§2=Introduction`、`§3=III.A Methods`、`§4=Results`，result.sections 必须恰含这四个 ID；正常项的锚点必须含自身 ID：

```json
{
  "status": "partial",
  "status_reason": "§3 未形成独立论点，保留占位；其余章节已完成",
  "sections": [
    {"id":"§1","title":"(preamble)","results":"记录题名、作者与摘要原文要点","source_anchor":"§1","status":"ok"},
    {"id":"§2","title":"Introduction","results":"记录研究问题","source_anchor":"§2","status":"ok"},
    {"id":"§3","status":"uncertain","reason":"依据原文暂标未形成独立论点，待人工复核"},
    {"id":"§4","title":"Results","results":"记录结果与限定条件","source_anchor":"§4","status":"ok"}
  ],
  "uncertainties": ["§3 未形成独立论点，未编造摘要"]
}
```

删去 §3 或额外添加 §999 均失败；把 §3 的占位放进 success 也失败。不得为了通过覆盖检查给占位补写空泛的目的、方法、结果或承接。

## 示例 7：标题识别 warning 不等于确定结构

索引可识别 `III.A Methods`、`IV. Experimental Results`、`A. Methods`，并对短且后续有正文的常见无编号 Title Case 结构标题作保守识别。索引顶层 warnings 示例：

```json
{"line":18,"text":"Methods","type":"heading_review","reason":"无编号短 Title Case 行按保守规则识别为标题；请人工复核切分"}
```

`heading_rejected` 表示疑似标题未采纳，`heading_review` 表示启发式切分仍需复核；生成结果前应回看原文，而不是隐藏 warning。
