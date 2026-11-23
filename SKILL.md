---
name: literature-review
description: "围绕固定研究问题组织文献证据并生成可核验综述：先写纳排标准再筛选，提取跨文献比较矩阵，从数据归纳主题，建立论断-证据双向回链，按证据强度分层措辞生成综述草稿，并以强制第二遍审计（引用支持度+覆盖率+措辞一致性）保证每条实质论断可指回具体文献的具体位置。适用于文献综述、系统筛选、趋势分析、选题评估与深度研究任务。"
---

# 文献综述生成（证据可回链版）

综述不是把摘要连起来。在一批真实文献上依次完成：**先写纳排标准 → 筛选并留证 → 提取比较矩阵 → 从数据归纳主题 → 证据表回链 → 分层措辞写草稿 → 强制审计后交付**。产出的每一条实质论断都必须能回答：它由哪篇文献的哪个位置支撑、证据强度是什么、与相反结论是什么关系。

本 Skill 与通用流程的两个硬性区别：

1. **两遍架构**：第一遍生成（步骤 P1–P5），第二遍审计（P6）。审计不是自查感想，而是逐条重读"论断 ↔ 证据摘录"并修复，审计结果写入 `result.json.audit`。未审计的草稿不得交付。
2. **双向回链**：论断有编号（C1、C2…），证据行有编号（E1、E2…），综述正文句末标注 `(E3; E7)`，文末附论断↔证据对照表；核验者从任何一句都能跳到证据行，再跳到原文位置。

## 一、运行契约与预算管理

运行时按实际路径定位文件，先读内容再判断，不以文件名或标签推断输入：

- 评测环境：原始输入通常为 `/input/case.json` 与 `/input/task.md`；文献与工具由 `environment/resources.yaml` 或 `case.json` 声明；PDF 只给原文、无预解析答案层，须自行解析（文本层用 pdf-text-tool 提取、扫描版用 ocr-tool、图表必要时用 pdf-render-tool 渲染查看）。可用工具以 `resources.yaml` 实际声明为准。
- 工作目录 `/app/work`；最终结果放 `/app/output`，其中 `result.json` 必须含 `case_id`（原样保留）并覆盖输入 `output_contract` 声明的全部字段；另交付 `review.md`（综述正文）与 `evidence_matrix.md`（筛选记录+比较矩阵+证据表）。
- 交互环境：输入路径不明时询问用户，不凭空假设。

**预算检查点（约 64 次模型请求、900 秒）**：读完输入立即写 `result.json` 骨架（`case_id` + `status: "in_progress"` + 各字段空数组）到 `/app/output/result.json`，之后每完成一步就地更新。预算消耗过半时停止扩张性工作，按"筛选记录 → 证据行 → 综合结论 → 主题 → 草稿正文 → 审计"的优先级收尾；来不及完成的部分标 `status: "partial"` 并写入 `uncertainty.undetermined`。任何情况下不得让 `result.json` 缺失或停留在骨架状态。

## 二、固定工作流

### P1 读输入与定位文献

读 `case.json`、`task.md`、`resources.yaml`，提取：研究问题、检索/筛选约束、文献清单、`output_contract`。列出全部文献及可获得性（全文/仅摘要/缺失）。**读完立刻写 `result.json` 骨架。**

### P2 写纳排标准（先于任何筛选）

把研究问题转成明确的纳入/排除标准，每条写明理由；处理重复、低相关、仅摘要三类情形的规则先行约定。标准写好后不随筛选结果临时改动，确需改动记入 `change_record`。细则见 [references/screening.md](references/screening.md)。

### P3 筛选并留记录

逐条执行纳排：先用题录/摘要判断，**只有纳入的文献才读全文**。每条留 `{id, status, reason, evidence_location}`，同时累计 PRISMA 式计数 `screening_flow`（识别、去重、筛掉及理由分类、纳入）。记录模板见 [templates/screening-log.md](templates/screening-log.md)。

### P4 提取比较矩阵与证据行

对纳入文献：**先填跨文献比较矩阵**（统一字段：研究设计、对象/样本、方法、指标、主要结果、结论、局限），**再抽证据行**（一条证据行只承载一个论断，带逐字短摘录与位置）。语料 ≤30 篇时纳入文献全部读全文，不允许"只看摘要"充数。比较矩阵模板见 [templates/comparison-matrix.md](templates/comparison-matrix.md)，证据规则见 [references/evidence-extraction.md](references/evidence-extraction.md)。

### P5 归纳主题、识别冲突与空白

从比较矩阵的方法、对象、结论分歧中**自下而上**归纳主题，不从"背景-方法-挑战-展望"套模板；维护主题台账（每篇文献归入何主题、不归属的说明原因）。结论相反或方法互斥的文献并列呈现；空白落到具体证据缺口。见 [references/topic-induction.md](references/topic-induction.md)。

### P6 写综述草稿

在证据表之上写草稿：每节先结论句（强度取支撑证据的最低级）再列证据；一段一个论点；句末引用 `(作者, 年份)` + 证据行号 `(E3)`；文末附论断↔证据对照表与参考文献（只列实际引用者）。强度措辞对照见 [references/synthesis.md](references/synthesis.md)，草稿模板见 [templates/review-draft.md](templates/review-draft.md)。

### P7 强制审计（第二遍，不可跳过）

草稿完成后执行三项审计，逐条留下结果，发现问题**修复后复检**，修复不了的在 `uncertainty` 声明：

1. **引用支持度审计**：逐条重读"论断 ↔ 所引证据行摘录"，判断摘录是否真的支撑该论断；不支撑的论断删除、改写或降级，记录处置。
2. **覆盖率交叉检查**：每篇纳入文献至少被一条论断引用；每个主题至少一条证据行；每条证据行至少被一条论断使用。列出未达标项并修复或说明。
3. **强度措辞一致性**：全文检索"表明/证实/证明/一致"等强措辞，核对其论断强度是否确为 `proven`；把越级措辞改回对应层级。

审计规则与记录格式见 [references/audit.md](references/audit.md) 与 [templates/audit-report.md](templates/audit-report.md)。

### P8 写输出与校验

写 `review.md`、`evidence_matrix.md`、`result.json`，运行 `python3 scripts/validate_result.py result.json` 做结构与交叉引用校验，修到无 error 后交付。输出字段定义见 [references/output-schema.md](references/output-schema.md)。

## 三、硬规则（违反即返工）

- **纳排标准先于筛选写明**并一致执行；筛选记录可复现（他人按同一标准重跑得到相同集合）。
- **证据强度只取四级**：`proven`（多篇一致且设计匹配）/ `suggestive`（单篇或局限，初步表明）/ `contested`（结论相反）/ `not_reported`（未报告）。措辞必须与层级一致，禁止把 `suggestive` 写成"证实"。
- **三层区分**：材料事实（原文直接给出）、合理推断（多条证据推出，显式标注推断链）、无法确定（证据不足，不写结论）。
- **冲突并列呈现**：写清谁 vs 谁、分歧点、可能原因；不抹成单线叙事。
- **空白具体化**：写"在 X 人群/条件下无直接证据""现有研究未比较 A 与 B"，不写"尚需进一步研究"式套话。
- **诚实**：缺全文写缺全文，元数据不全写不全，检索为空写为空；不编造文献、引文、页码或数据；只用材料中真实存在的元数据与摘录。
- **二手引用**标为二手并指向原始出处，或降级为 `suggestive`/`not_reported`。

## 四、异常处理

| 情形 | 处置 |
|---|---|
| 缺全文 | 标 `abstract_only`，只用于背景/趋势，不支撑需全文细节的论断 |
| 元数据不全 | 缺失字段标「未知」，不补造 DOI/标题/年份 |
| 文献重复 | 保留主记录，其余标 `excluded_duplicate` 并注明重复来源 |
| 结论冲突 | 双方并列，记入 `uncertainty.conflicts` |
| 超出上下文 | 分批处理，优先保证纳入文献的提取完整 |
| 检索/筛选为空 | 如实写为空及原因，不强行纳入，不编造 |
| 工具失败（PDF 解析/OCR） | 换备用工具重试一次，仍失败则标 `failed` 于该文献并说明影响 |

## 五、交付前自查

1. 纳排标准先于筛选写明并被一致执行？`screening_flow` 计数与记录数一致？
2. 每条实质论断都有证据行，且审计确认摘录真正支撑？
3. 主题从比较矩阵里长出来而非套模板？有无重叠、遗漏（主题台账）？
4. 强度措辞全部与层级一致？冲突并列？空白具体？
5. 材料事实/合理推断/无法确定三层分开？
6. `result.json` 含 `case_id` 与全部 `output_contract` 字段、`status` 如实、`sources`/`change_record` 完整？
7. `scripts/validate_result.py` 通过（0 error）？

按需加载的参考文件：

- 运行环境与工具细节：[references/runtime-and-tools.md](references/runtime-and-tools.md)
- 输出字段定义：[references/output-schema.md](references/output-schema.md)
- 筛选与纳排：[references/screening.md](references/screening.md)
- 证据提取与强度：[references/evidence-extraction.md](references/evidence-extraction.md)
- 主题归纳：[references/topic-induction.md](references/topic-induction.md)
- 草稿与引用：[references/synthesis.md](references/synthesis.md)
- 审计规程：[references/audit.md](references/audit.md)
- 模板：[templates/screening-log.md](templates/screening-log.md)、[templates/comparison-matrix.md](templates/comparison-matrix.md)、[templates/evidence-table.md](templates/evidence-table.md)、[templates/review-draft.md](templates/review-draft.md)、[templates/audit-report.md](templates/audit-report.md)
- 最小示例（标注为示例，非正式案例结果）：[examples/minimal-example.md](examples/minimal-example.md)
