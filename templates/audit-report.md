# 审计记录模板

三项审计逐条留痕，汇总写入 `result.json.audit`。

## 1. 引用支持度审计

| claim_id | 引用证据行 | 判定 | 处置 | 理由 |
|---|---|---|---|---|
| C1 | E3, E7 | ok | — | 摘录覆盖论断全部要素 |
| C2 | E9 | downgraded | "证实"→"初步表明" | 单篇小样本 |
| C3 | E12 | dropped | 删除论断 | 摘录与论断无关 |

计数：checked = __，supported = __，fixed = __，dropped = __

## 2. 覆盖率交叉检查

| 检查项 | 结果 | 未达标项与处置 |
|---|---|---|
| 纳入文献均被引用 | __ / __ | S6 未被引用 → 补写论断 C9 (E15) |
| 主题均有证据 | __ / __ | 主题"X"无证据行 → 并入主题"Y" |
| 证据行均被使用 | __ / __ | E11 孤儿 → 注明提取冗余 |

计数：included_sources_cited = __/__，themes_with_evidence = __/__，evidence_rows_used = __/__

## 3. 强度措辞一致性

| claim_id | 原文措辞 | 改后措辞 | 原因 |
|---|---|---|---|
| C5 | 证实 | 初步表明 | strength=suggestive |

计数：strong_wording_checked = __，corrected = __

## 复检

- [ ] 修订后的论断已重新通过引用支持度审计
- [ ] 覆盖率问题全部处置或在 uncertainty 声明
- [ ] `change_record` 已追加审计摘要
