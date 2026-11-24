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
2. 每个术语给出**唯一译名**，写进术语表（见 references/terminology-lock.md）。同一概念多种原文表达（同义/缩写/全称）合并为一行。
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

### 第 5 步：译文核验（可核验）
逐段回核（读译文，对照原文）：
1. 术语是否与第 1 步术语表一致；
2. 数字/单位/公式/引用是否逐字保留；
3. 否定/限定/因果是否未变；
4. 是否漏译、多译、错位。
生成**需人工确认清单**（译不准、歧义、术语冲突、原文残缺），写入 `uncertainties`。

### 第 6 步：产出结果
按 references/output-schema.md 写 `/app/output/result.json`，并输出双语对照文档（Markdown：段号 + 原文 + 译文 + 依据）与术语表。

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
- `references/terminology-lock.md` —— 术语表抽取、锁定与冲突处理
- `references/hedge-strength.md` —— 限定词/程度词强度分级与守恒（关系准核心）
- `references/bilingual-alignment.md` —— 段落级双语对照与段号约定
- `references/translation-verification.md` —— 译文核验清单（数字/单位/公式/引用/否定）
- `references/output-schema.md` —— result.json 字段契约
- `examples/translation-examples.md` —— 标注为示例的对照（非正式案例）
