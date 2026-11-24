# 论文卡片字段字典（Paper Card Fields）

统一字段让同一领域的多篇论文可**并排比较**。每个非空字段值必须通过顶层 `paper_card_anchors` 回链原文（见 source-anchoring.md），每项为 `{field,source_anchor,quote?}`，不要把锚点写进字段字符串。

## 必填字段

| 字段 | 含义 | 说明 |
|---|---|---|
| `title` | 标题 | 原样 |
| `authors` | 作者 | 原样 |
| `research_question` | 研究问题/目标 | 论文要回答什么 |
| `data` | 数据与材料 | 数据集、样本量、来源、采集条件 |
| `methods` | 方法条件 | 模型、参数、实验条件、关键假设 |
| `findings` | 主要发现 | 含关键数值、显著性 |
| `limitations` | 局限 | 作者自述 + 客观可见边界 |
| `conclusion` | 结论 | 论文最终主张（保留限定强度） |

## 可选字段

| 字段 | 含义 |
|---|---|
| `contribution` | 贡献/创新点 |
| `baseline` | 对比基线 |
| `metrics` | 评价指标 |
| `key_conditions` | 让结论成立的前提条件 |
| `open_questions` | 未解决问题 |

## 规则

1. **留得住**：前提条件（如"仅在 X 条件下""n=3""体外实验"）必须随结论一起记录，不得省略。
2. **数值保留**：关键数值、单位、显著性、置信区间逐字保留。
3. **限定强度**：结论的限定词（可能/表明/证明）保留原强度，不加强不削弱。
4. **字段缺失**：原文未报告 → 字段标 `not_reported`，不编造。

## 样例（示意，非正式案例）

```json
{
  "paper_card": {
    "title": "A Demonstration Study",
    "research_question": "某方法是否在 X 条件下优于基线",
    "data": "数据集 D，n=1000，来源 …",
    "methods": "模型 M，超参 …，假设 …",
    "findings": "准确率 0.81 vs 基线 0.79（p<0.05）",
    "limitations": "仅在 X 条件下验证；样本来自单一中心",
    "conclusion": "该方法在 X 条件下显著优于基线"
  },
  "paper_card_anchors": [
    {"field":"title","source_anchor":"§1 ¶1"},
    {"field":"research_question","source_anchor":"§1 ¶2"},
    {"field":"data","source_anchor":"§3 ¶1"},
    {"field":"methods","source_anchor":"§3 ¶2"},
    {"field":"findings","source_anchor":"§4 ¶1"},
    {"field":"limitations","source_anchor":"§5 ¶1"},
    {"field":"conclusion","source_anchor":"§6 ¶1"}
  ]
}
```
