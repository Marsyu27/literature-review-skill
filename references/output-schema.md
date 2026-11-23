# result.json 输出字段定义

`result.json` 是机器可读的最终结果。若输入提供显式 `output_contract`（或等价字段 `result_schema`/`output_fields`），**以输入的契约为准**，本文件为默认结构；输入契约要求的字段一个不能少，本文件定义的字段作为补充一并给出。

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `case_id` | string | 是 | 输入中的案例标识，**原样保留**，不改写不拼接 |
| `status` | enum | 是 | `success`（完整可用）/ `partial`（有结果但有限制）/ `failed`（未产出可用结果）；进行中骨架用 `in_progress` |
| `research_product` | object | 是 | 研究产物：综述/筛选/趋势/选题评估结果 |
| `evidence_matrix` | object | 是 | 证据矩阵：筛选流、筛选记录、比较矩阵、证据行 |
| `audit` | object | 是 | 第二遍审计结果（见下） |
| `uncertainty` | object | 是 | 冲突、偏倚、空白与无法确定项 |
| `sources` | array | 是 | 文献来源与可获得性 |
| `change_record` | array | 是 | 修订记录 |

## research_product

- `research_question`：string，从输入转述的研究问题（可检验、范围明确）。
- `type`：`review` / `screening` / `trend` / `topic_evaluation`。
- `themes`：数组，每条 `{id, name, subthemes, supported_by, boundary}`。`name` 须反映文献实际聚类（如"化学还原法合成路线"），不写"研究现状"这类空名；`supported_by` 是文献 id 列表；`boundary` 写明哪些内容属于/不属于该主题。
- `sections`：数组，每条 `{id, heading, paragraphs}`；`paragraphs` 每条 `{claim_id, claim, strength, evidence_ids}`。
- `conclusions`：数组，每条 `{claim_id, statement, strength, evidence_ids, scope_note}`，`scope_note` 写明结论适用范围（人群/条件/方法）。
- `claim_id` 为 C1、C2…，在 `sections` 与 `conclusions` 中**全局唯一**；结论不复用正文论断的编号，而是自成论断并引用相同证据行。

## evidence_matrix

- `screening_flow`：object，PRISMA 式计数 `{identified, duplicates_removed, screened, excluded_irrelevant, excluded_other, abstract_only, included}`。计数必须与 `screening_records` 实际条数一致（校验脚本会核）。
- `screening_records`：数组，每条 `{id, status, reason, evidence_location}`。`status` 取 `included` / `excluded_duplicate` / `excluded_irrelevant` / `excluded_other` / `abstract_only`；`evidence_location` 写明判断依据来自标题/摘要/全文哪一节。
- `comparison_matrix`：数组，每篇纳入文献一条 `{source_id, design, population, method, metrics, main_results, conclusions, limitations}`，字段值填原文内容或「未报告」。
- `evidence_rows`：数组，每条 `{id, source_id, excerpt, location, claim, strength, note}`。`id` 为 E1、E2… 全文唯一；`excerpt` 为逐字短摘录；`location` 为页码/段落/图表；`strength` 取四级强度。

## audit（第二遍审计结果，必填）

- `citation_audit`：`{checked, supported, fixed, dropped}` 计数 + `items` 数组，每条 `{claim_id, verdict(ok|revised|downgraded|dropped), reason}`。
- `coverage_check`：`{included_sources_cited, themes_with_evidence, evidence_rows_used}` 计数 + `issues` 数组（未达标项及处置）。
- `wording_audit`：`{strong_wording_checked, corrected}` 计数 + `items` 数组。

## uncertainty

- `conflicts`：每条 `{id, between, point, possible_reason}`。
- `biases`：每条 `{type, description, impact}`，`type` 如检索偏倚、出版偏倚、单一数据源、样本偏倚。
- `gaps`：每条 `{id, gap, evidence_basis}`，`gap` 是具体证据缺口。
- `undetermined`：每条 `{item, reason, impact}`。

## sources

数组，每条 `{id, authors, year, title, venue_or_doi, full_text_available}`。只有材料里真实存在的元数据才写；缺失字段标「未知」，不补造。

## change_record

数组，每条 `{version, changed, reason}`。

## 状态判定参考

- `success`：纳排标准先写并执行、证据表与双向回链完整、主题从文献归纳、冲突与空白明确、三项审计完成且问题已处置，可据此复现筛选并逐条核对引用。
- `partial`：存在缺口（缺全文、元数据不全、部分论断无证据行、审计未全部通过），已在 `uncertainty` 标明。
- `failed`：无法读取输入、文献不可用、检索为空且无产出、或输入与任务不匹配。
