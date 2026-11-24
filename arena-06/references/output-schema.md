# result.json 字段契约（Output Schema）

## 硬性要求

1. `case_id` 原样回填；`status` + `status_reason` 必填。
2. **output_contract**：`/input/case.json` 里 `output_contract` 声明的每个字段都要出现，字段名与类型一致。
3. 每条笔记/字段/知识点可回链原文（锚点），未报告与不确定项如实标注。

## 契约优先级

- **第一优先：`output_contract` 声明的字段**。`case.json` 的 `output_contract` 里声明的每个字段必须原样出现（字段名、类型一致），这是平台打分的硬约束，不可缺省、不可改名。
- **第二优先：本文件定义的默认字段**（`paper_card`/`sections`/`knowledge_points`/`uncertainties` 等）。output_contract 未覆盖时按默认字段补齐；与 output_contract 冲突时以 output_contract 为准。
- output_contract 为空或未声明时，默认字段全量输出。

## 字段定义

```json
{
  "case_id": "<回填>",
  "status": "success | partial | unable",
  "status_reason": "<unable/partial 时必填>",
  "paper_card": {"title":"…","research_question":"…","data":"…","methods":"…","findings":"…","limitations":"…","conclusion":"…"},
  "sections": [
    {"id":"§1","title":"Introduction","purpose":"…","method":"…","results":"…","transition":"…"}
  ],
  "knowledge_points": [
    {"id":"kp-001","type":"concept|variable|method|result|metric|limitation","label":"…","value":"…","source_anchor":"§2 ¶1","status":"ok|uncertain|conflict"}
  ],
  "uncertainties": ["需要人工确认的清单"],
  "tool_commands": ["实际执行的命令，用于复现与审计"]
}
```

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` / `status` / `status_reason` | 是 | 运行状态三件套 |
| `paper_card` | 是 | 统一字段卡片（研究问题/数据/方法/发现/局限/结论）——"留得住" |
| `sections` | 是 | 按原文章节对齐的总结——"对得上" |
| `knowledge_points` | 是 | 可检索知识点，归一化去重，含锚点——"用得上" |
| 各字段/条目的 `source_anchor` | 是 | 锚点回链——"找得回"；必须取自 `build_anchor_index.py` 索引，交付前经 `validate_anchors.py` 核验 |
| `uncertainties` | 是 | 无法判断/需人工确认项；无则空数组 |
| `tool_commands` | 推荐 | 实际命令，用于复现 |

## 状态与降级

- `success`：所有 output_contract 字段有值，各字段/条目可复核。
- `partial`：部分完成（如个别章节残缺、知识点有冲突），`uncertainties` 说明缺口。
- `unable`：无法处理（材料缺失/加密/无法读取），写明原因，不编造。

## 诚实原则

数值、单位、限定词逐字保留；原文未报告 → `not_reported`；原文自相矛盾 → `conflict` 保留两处原文；译不出/读不出就标不确定，不补造。
