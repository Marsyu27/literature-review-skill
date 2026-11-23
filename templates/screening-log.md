# 筛选记录模板

## 纳排标准（先于筛选写明）

| # | 标准 | 类型 | 理由 |
|---|---|---|---|
| 1 | … | 纳入 | … |
| 2 | … | 排除 | … |
| 3 | … | 仅摘要标记 | … |

## 筛选流计数（PRISMA 式）

| 阶段 | 数量 |
|---|---|
| identified 识别总数 | n |
| duplicates_removed 去重移除 | n |
| screened 进入筛选 | n |
| excluded_irrelevant 低相关排除 | n |
| excluded_other 其他排除 | n |
| abstract_only 仅摘要 | n |
| included 纳入 | n |

恒等式：identified = duplicates_removed + screened；screened = excluded_irrelevant + excluded_other + abstract_only + included。

## 逐条记录

| 文献 id | 状态 | 理由 | 依据位置（标题/摘要/全文章节） |
|---|---|---|---|
| S1 | included | 满足标准 1 | 摘要；全文 Sec.2 |
| S2 | excluded_irrelevant | 不满足标准 1：未报告 X 与 Y 的关系 | 摘要 |
| S3 | excluded_duplicate | 与 S1 为同一工作的预印本 | 标题/作者 |
| S4 | abstract_only | 无法获取全文 | 题录 |
