---
name: scientific-literature-translation
description: >-
  Use when the task is to translate a scientific paper or excerpt (English↔Chinese)
  with verifiable fidelity — produce paragraph-level bilingual alignment, a frozen
  terminology table that is actually enforced across title/abstract/body/figure
  captions/conclusions, and a per-paragraph source pointer plus an explicit
  "untranslatable/uncertain" list. Do NOT use for polishing, summarizing, or
  answering content questions — translate faithfully, do not paraphrase the science.
---

# 科研文献翻译（Scientific Literature Translation）

目标：把科研论文**忠实、可复核**地翻译成另一种语言。四个纪律：**术语稳、段落全、关系准、可核验**——术语全篇统一且真正执行、段落不漏不重不错位、指代/否定/限定/数字/公式/引用与原文一致、每段译文能指回原文并标注译不准之处。

## 何时使用 / 何时不用

**使用**：整篇论文或指定章节/摘要/图注的翻译；需要双语对照与术语表。

**不用**：学术润色（那是润色 Skill）、摘要写作、内容问答、从零生成。若输入是"翻译+润色"混合任务，先翻译进入本流程，再在修改记录里区分两类操作。

## 强制流程（按顺序执行）

### 第 0 步：读输入，定输出契约
1. 读 `/input/case.json`：取 `case_id`、`output_contract` 字段清单、待翻译材料路径、目标语言。
2. 读 `/input/task.md`：确认翻译范围（全文 / 指定章节 / 摘要 / 图注 / 表格）。
3. 记录：`case_id`、源语言→目标语言、翻译范围。`result.json` 必须含 `case_id` 与 output_contract 全部字段。

### 第 1 步：术语抽取与冻结（术语稳）
1. 通读原文，抽取并登记：领域术语、缩写与全称、专有名词、度量单位写法。
2. 每个术语给出**唯一译名**，写进术语表（见 references/terminology-lock.md 与 terminology.schema.json）。同一概念多种原文表达合并为一行：`term` 写 canonical form，其他表面形式写 `aliases[]`，不得用 `performance / efficiency` 式拼接字符串。不同语义的同名形式分条，并为每条配置可区分的 `context` 正则列表。
3. 术语表是**冻结**的：后续标题、摘要、正文、图注、结论中，同一术语必须用同一译名；发现漂移即回改。
4. 原文术语本就混用时，以**多数派**为准，在术语表标注"已按多数统一，原文另有 X"，并把冲突点放进 `uncertainties`。

### 第 2 步：长文分段（段落全）
1. 按**语义边界**切分：章节 → 段落 → 句子。保留原编号（章节号、段号、句号）。
2. 跨页、跨栏、跨章节的段落：按语义接续，不重复、不遗漏、不错位。
3. 页眉页脚、脚注、边注：单独翻译并标记，不混入正文。
4. 每段分配唯一 `段落号`（如 `§2 ¶3`），译文与原文一一对应。

### 第 3 步：逐段翻译 + 双语对照（段落全 + 可核验）
对每段输出结构化对照（不要只给译文）：
- `source`（原文段落，含段号）
- `target`（译文）
- `basis`（译法依据，尤其术语与关键句）

**逐句**翻译，不是逐段意译重写。句子边界保留。

### 第 4 步：关系守恒检查（关系准）
对每一句，用 references/hedge-strength.md 的强度分级检查，并核对：
- **指代**：this/these/it/该/其 等指代对象是否与原文一致。
- **否定与限定**：否定范围、only if/unless/under X、量词 some/most/all 保持原意。
- **因果 vs 让步**：because/causes（因果）与 although/despite（让步）不得互换。
- **数字与单位**：数值、单位、显著性（p<0.05）、置信区间**一字不改**。
- **公式与编号**：公式原样保留，`(3)`/`Eq.(2)` 编号对应不变。
- **文献引用**：`[12]`/`(Smith, 2020)` 指向不变。

### 第 5 步：译文核验（可核验，机械检查先行）
先把第 1 步术语表落盘为 `terminology.json`、第 3 步双语段落落盘为 `segments.json`（机读格式见 references/terminology-lock.md 与 references/output-schema.md），然后**先跑两个核验脚本**，再人工回核脚本覆盖不了的项：

1. `python3 scripts/check_terminology.py --terms terminology.json --segments segments.json --report work/terminology-report.json`
   —— 机械检查术语**回填**（source 命中 `term` 或任一 alias 而 target 缺 locked 译名 → error）、旧译**漂移**（warning）、**frozen** 逐字约束；同一表面形式的多条目必须各有 `context`，每段只能命中一个语境候选，否则明确配置 error，有 error 退出码 1。
2. `python3 scripts/check_conservation.py --segments segments.json --report work/conservation-report.json`
   —— 逐段核对数字（含正负号、Unicode −、小数/百分数/千分位、`10^-3` 指数与 `1e-3` 科学计数）、引用标记（`[n]` 与 `(Author, year)`）、带单位量（如 `300 K`、`2.5 m/s`）是否守恒；**missing 或 added 任一非空都退出码 1**，added 不是备注。

**两个脚本全绿（退出码均为 0）才允许交付；红则修复译文后重跑，直到全绿；确属原文残缺的残余缺口如实写入 `uncertainties` 并说明脚本报告路径。**

脚本覆盖不了的项仍需人工逐段回核（读译文，对照原文）：
1. 否定/限定/因果是否未变（references/hedge-strength.md）；
2. 指代对象是否一致；
3. 是否漏译、多译、错位。
生成**需人工确认清单**（译不准、歧义、术语冲突、原文残缺），写入 `uncertainties`。

### 第 6 步：产出结果
按 references/output-schema.md 写 `/app/output/result.json`，并输出双语对照文档（Markdown：段号 + 原文 + 译文 + 依据）与术语表。

## 检查点与降级

1. 第 0 步读完输入即写 `/app/output/result.json` 骨架（`case_id` + output_contract 字段占位 + `status:"in_progress"`），任何时刻中断都有可交付物。
2. 按章节分块增量更新：每译完一章即回写 result.json 与 segments.json，不等到全文译完。
3. 预算过半按 **译文主体 → 术语表 → 守恒核验 → uncertainties** 降级：先保译文主体完整，再保术语表，核验缺口如实写进 `uncertainties`。
4. 每次降级在 `status_reason` 写明降了哪一级、缺口在哪一章。

## 异常与边界

| 情况 | 处置 |
|---|---|
| 原文残缺/模糊/扫描不清 | 标注 `unable/uncertain`，不猜译 |
| 术语有歧义（一词多义） | 按上下文取义，术语表注明，`uncertainties` 提示 |
| 公式为图片 | 保留渲染图，标注不确定，不臆造符号 |
| 图表题注含特殊符号 | 保留符号，仅译叙述文字 |
| 目标语言术语无标准译名 | 给出音译/意译并标注"暂定译名" |

## 复用与维护

- 术语表每次运行落盘为可读文本，供后续论文复用。
- references/hedge-strength.md 是"关系准"的唯一判定依据。
- 本 Skill 只做忠实翻译，不做研究结论判断；遇到"这句是否科学正确"交给用户。

详见随附资源：
- `scripts/check_terminology.py` —— 术语回填/漂移/frozen 机械核验（纯标准库）
- `scripts/check_conservation.py` —— 数字/引用/带单位量守恒逐段核验（纯标准库）
- `references/terminology-lock.md` —— 术语表抽取、锁定与冲突处理
- `references/hedge-strength.md` —— 限定词/程度词强度分级与守恒（关系准核心）
- `references/bilingual-alignment.md` —— 段落级双语对照与段号约定
- `references/translation-verification.md` —— 译文核验清单（数字/单位/公式/引用/否定）
- `references/output-schema.md` —— result.json 字段契约
- `examples/translation-examples.md` —— 标注为示例的对照（非正式案例）
