# result.json 字段契约（Output Schema）

## 硬性要求

1. `case_id` 原样回填；`status` + `status_reason` 必填。
2. **output_contract**：`/input/case.json` 里 `output_contract` 声明的每个字段都要出现，字段名与类型一致。
3. 每个非空 paper_card 字段、每个正常 section、每个正常 knowledge_point 都必须用正式字段回链原文，未报告与不确定项如实标注；不得只把锚点嵌在字符串值中。
4. `sections` 必须对照索引完整 §ID 集合：success 不漏、不多、不用 `uncertain` 占位；partial 的每个未完成索引章节保留 `{"id":"§n","status":"uncertain","reason":"..."}`。preamble 不例外，正常 section 的 `source_anchor` 必须含自己的 §ID。

## 契约优先级

- **第一优先：`output_contract` 声明的字段**。`case.json` 的 `output_contract` 里声明的每个字段必须原样出现（字段名、类型一致），这是平台打分的硬约束，不可缺省、不可改名。
- **第二优先：本文件定义的默认字段**（`paper_card`/`paper_card_anchors`/`sections`/`knowledge_points`/`uncertainties` 等）。output_contract 未覆盖时按默认字段补齐；与 output_contract 冲突时以 output_contract 为准。
- output_contract 为空或未声明时，默认字段全量输出。

## 字段定义

```json
{
  "case_id": "<回填>",
  "status": "success | partial | unable",
  "status_reason": "<unable/partial 时必填>",
  "paper_card": {"title":"…","research_question":"…","data":"…","methods":"…","findings":"…","limitations":"…","conclusion":"…"},
  "paper_card_anchors": [
    {"field":"title","source_anchor":"§1 ¶1","quote":"可选：被引范围逐字原文"},
    {"field":"findings","source_anchor":"§4 ¶1","quote":"可选：被引范围逐字原文"}
  ],
  "sections": [
    {"id":"§1","title":"(preamble)","purpose":"…","method":"…","results":"…","transition":"…","source_anchor":"§1","status":"ok"},
    {"id":"§2","title":"Introduction","purpose":"…","method":"…","results":"…","transition":"…","source_anchor":"§2","status":"ok"},
    {"id":"§3","status":"uncertain","reason":"仅 partial：未形成独立论点，待据原文复核；source_anchor 可省略"}
  ],
  "knowledge_points": [
    {"id":"kp-001","type":"concept|variable|method|result|metric|limitation","label":"…","value":"…","source_anchor":"§2 ¶1","status":"ok|uncertain|conflict"}
  ],
  "uncertainties": ["需要人工确认的清单"],
  "tool_commands": ["实际执行的命令，用于复现与审计"]
}
```

`paper_card_anchors` 是顶层配套数组，`field` 必须写 `paper_card` 中的字段名；同一字段有多处证据时可写多项。`quote` 可省略，非空时必须逐字摘自 source_anchor 指向的范围。

`anchor_index.json` 除 `sections` 外含顶层 `warnings`：编号标题形态包括阿拉伯、罗马嵌套（如 `III.A`）、罗马与字母编号；短的常见无编号 Title Case 结构标题只在长度、标点与后续正文约束满足时采纳。`heading_review` 表示启发式采纳需复核，`heading_rejected` 表示疑似标题未采纳；不得把这些 warning 当作已确认无误。

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` / `status` / `status_reason` | 是 | 运行状态三件套 |
| `paper_card` | 是 | 统一字段卡片（研究问题/数据/方法/发现/局限/结论）——"留得住" |
| `paper_card_anchors` | 是 | 每个非空 paper_card 字段至少一项；`field/source_anchor` 正式分离，`quote` 可选 |
| `sections` | 是 | 按索引完整 §ID 集逐项对齐（含 preamble）；正常项含指向自身的 `source_anchor`，partial 不确定项含逐节 `reason` 占位——"对得上" |
| `knowledge_points` | 是 | 可检索知识点，归一化去重；每项含 `source_anchor`——"用得上" |
| `uncertainties` | 是 | 无法判断/需人工确认项；success 无则空数组，partial 必须非空并交代缺口 |
| `tool_commands` | 推荐 | 实际命令，用于复现 |

所有锚点必须取自 `build_anchor_index.py` 生成的索引，交付前由 `validate_anchors.py` 同时核验 §/¶ 存在性、quote、上述覆盖及章节双向全集。报告的 `index_sections`、`result_sections`、`missing_sections`、`extra_sections` 给出四个 ID 列表。success 下 `checked=0`、任一必填条目不覆盖、章节缺失/额外或使用占位均失败。

## 状态与降级

- `success`：所有 output_contract 字段有值；索引每个 §ID 都恰有一个正常完成的结果章节，无索引外 ID；所有非空 paper_card 字段、每个正常 section、每个正常 knowledge_point 都有真实有效锚点，section 锚点含自身 ID。`uncertain` 不能作为 success 缺锚点或章节占位的豁免理由。
- `partial`：部分完成。只有明确 `status=uncertain` 的条目可缺锚点，脚本保留 warning；`paper_card_anchors` 的缺锚点占位可写 `{"field":"limitations","status":"uncertain","reason":"定位待确认"}`。每个未正常完成的索引章节必须写 `{"id":"§n","status":"uncertain","reason":"..."}`，可无 `source_anchor`，不能直接从数组删除；索引外章节仍失败。整体至少须有一个来自 paper_card/section/knowledge_point 的真实有效锚点，且 `status_reason` 与非空 `uncertainties` 必须说明覆盖范围、缺口与原因。
- `unable`：无法处理（材料缺失/加密/无法读取），写明原因，不编造；确实无内容时允许零锚点。

## 检查点骨架

第 0 步读完输入立即创建 `/app/output/result.json`，第 1 步先确认其存在，之后每阶段就地更新。初始骨架：

```json
{"case_id":"<回填>","status":"in_progress","status_reason":"正在读取论文并生成锚点索引","paper_card":{},"paper_card_anchors":[],"sections":[],"knowledge_points":[],"uncertainties":[]}
```

还必须将 output_contract 声明的每个其他字段以符合其类型的空占位加入骨架，不能等最终交付才创建文件。

## 诚实原则

数值、单位、限定词逐字保留；原文未报告 → `not_reported`；原文自相矛盾 → `conflict` 保留两处原文；译不出/读不出就标不确定，不补造。不得为通过章节全集覆盖编造空泛摘要；无法提炼时只可依据原文标“未形成独立论点”，并使用 section `uncertain` + 整体 `partial` 如实降级。任何降级都不能用脚本 warning 掩盖最终缺失的正式锚点、逐节占位或索引。
