# 强制审计（第二遍）

草稿完成后、交付之前执行。审计的对象是**已写出的草稿与 result.json**，不是计划。三项审计逐项留痕，结果写入 `result.json.audit`；发现的问题修复后复检，修复不了的在 `uncertainty.undetermined` 声明。预算紧张时压缩草稿篇幅也要完成审计——未审计的草稿不得交付。

## 1. 引用支持度审计（citation audit）

逐条取出草稿中的论断 Cn 与其引用的证据行摘录，重读并判断：**这段摘录是否支撑这句话？**

- 支撑 → `ok`。
- 部分支撑（摘录只覆盖论断的一部分）→ 收窄论断至摘录实际支持的范围，`revised`。
- 摘录方向对但强度不足（单篇/局限被写成定论）→ 降级措辞，`downgraded`。
- 摘录与论断无关 → 删除论断或换用真正支撑的证据行，`dropped`；换证据行后复检。

记录：`{checked, supported, fixed, dropped}` 计数 + 每条 `{claim_id, verdict, reason}`。`dropped` 必须写明原因，这是质量改进的证据而非失败。

## 2. 覆盖率交叉检查（coverage check）

三个方向全部核对：

- **文献 → 论断**：每篇 `included` 文献至少被一条论断引用。未被引用的纳入文献：若与研究问题相关则补写论断并配证据行；若实无用武之地，在 `issues` 说明保留原因（如仅用于背景）。
- **主题 → 证据**：每个主题至少一条证据行；空主题删除或合并。
- **证据 → 论断**：每条证据行至少被一条论断使用；孤儿证据行说明是提取冗余还是漏写论断，冗余的保留在证据表但注明。

记录：`{included_sources_cited, themes_with_evidence, evidence_rows_used}` 计数 + `issues` 数组。

## 3. 强度措辞一致性（wording audit）

在 `review.md` 全文中检索强措辞词表：表明、证实、证明、确立、一致、显著、首次、最优。逐处核对其论断的 `strength`：

- 措辞与层级一致 → 通过。
- 越级（如 `suggestive` 用了"证实"）→ 改回该层级允许措辞，`corrected` 计数加一。

反向也查：`contested`/`not_reported` 的论断不得出现肯定性结论措辞。

记录：`{strong_wording_checked, corrected}` 计数 + 每条 `{claim_id, before, after}`。

## 审计与修订记录

三项审计完成后，在 `change_record` 追加一条 `{version, changed: "audit", reason: "<三项审计结果摘要>"}`。审计发现的每一处实质性修改都要能在 `change_record` 或 `audit.items` 中找到对应记录。
