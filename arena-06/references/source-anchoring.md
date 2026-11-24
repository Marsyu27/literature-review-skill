# 锚点格式与可核验性（Source Anchoring）

每条正常笔记、每个非空 paper_card 字段、每个正常 section、每个正常知识点都要能**指回原文**；partial 的不确定条目按显式占位降级。锚点不是模型自编号，而是由脚本生成、脚本核验的稳定 ID。正式字段为：顶层 `paper_card_anchors[]`（`field/source_anchor/quote?`）、`sections[].source_anchor`、`knowledge_points[].source_anchor`；不得只在字符串值末尾附 `（§x ¶y）`。

## 锚点定义

- 锚点 = **锚点索引中的稳定 ID**，由 `scripts/build_anchor_index.py` 对输入论文文本生成：
  - `§x`：章节 ID（`§1..§n`，按标题行切分：Markdown `#` 系列、阿拉伯编号、`III.A Methods` / `IV. Experimental Results` / `A. Methods` 等罗马或字母编号、全大写小节名，以及满足长度/标点/后续正文约束的常见无编号 Title Case 结构标题）；
  - `¶y`：章节内段落 ID（`¶1..¶m`，按空行切分）。
- 引用形态：`§x`（到章节）或 `§x ¶y`（到段落）；可附带 `Fig. 2` / `Table 1` / `Eq. (3)` 编号作补充定位。
- `page=N` **仅在输入材料自带真实页码时**附加（如原文分页的纯文本、带页码标记的抽取结果）；输入无真实页码时不得编造页码。
- 组合示例：`§2 ¶3`、`§4 Table 2`、`§1`。

## 规则

1. **只允许使用索引中存在的 §/¶ ID**；索引由输入文本确定性生成，同一输入同一索引，第三方可重跑复现。
2. 锚点必须指向**真正对应**的位置，不是笼统的"见正文/见原文"。
3. 条目带 `quote` 字段时，quote 必须逐字摘自被引段落（核验时大小写不敏感、空白归一）。
4. result.sections 与索引完整 §ID 集必须双向对齐，preamble 也是普通 §。success 不漏节、不多节、不用 `uncertain` 占位；每个正常 section 的 `source_anchor` 必须包含自己的 §ID。partial 的每个未完成索引章节保留 `{"id":"§n","status":"uncertain","reason":"..."}`，可缺锚点但不可静默删节。
5. success 不允许任何其他必填覆盖缺失。partial 仅明确 `status=uncertain` 的条目可缺锚点并 warning；paper_card 的缺锚点占位写 `{"field":"data","status":"uncertain","reason":"定位待确认"}`，且整体至少一个核心有效锚点，`status_reason` 与非空 `uncertainties` 必须说明缺口。不得伪造锚点，也不得为覆盖编造空泛摘要；无法提炼时只据原文标“未形成独立论点”并降为 partial。
6. 索引顶层 `warnings` 记录启发式标题采纳（`heading_review`）与疑似标题未采纳（`heading_rejected`）；先人工复核切分再生成/信任锚点，不能把 warning 隐藏为确定结构。
7. 图表/公式为图片且内容不可读 → 保留编号，标"内容不可读"。

## 核验（交付前必须全绿）

```
python3 scripts/validate_anchors.py --result result.json \
    --index anchor_index.json --report anchor_report.json
```

- 每条带 `source_anchor`/`anchor` 的条目逐一核对：§/¶ 必须存在于索引；quote 必须是被引范围原文的子串。
- 还检查所有非空 paper_card 字段在 `paper_card_anchors` 中的覆盖、每个正常 section/knowledge_point 的 `source_anchor` 以及 section 自身 §ID；对 success/partial 双向核对章节全集。报告含 `index_sections` / `result_sections` / `missing_sections` / `extra_sections`，并列出不确定占位 warning；`checked=0` 不得通过（unable 无内容例外）。
- 退出码 0 才可交付；退出码 1 时按报告补锚点、修正 ID/quote，或仅在 partial 下对明确无法定位条目标 `uncertain` 后重跑。
- 第三方复核方式：用同一输入重跑 `build_anchor_index.py` 得同一索引，再按锚点 ID 定位原文段落核对笔记内容。

## 样例（示意）

```json
{
  "paper_card": {"findings":"准确率 0.81 vs 0.79 (p<0.05)"},
  "paper_card_anchors": [
    {"field":"findings","source_anchor":"§4 ¶1","quote":"Accuracy reaches 0.81 versus 0.79 baseline (p<0.05)"}
  ]
}
```
