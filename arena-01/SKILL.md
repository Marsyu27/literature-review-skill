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

### 第 2 步：固化源文快照与长文分段（段落全）
1. 先确定规范化原文并**原样保存**为 `/app/work/source-snapshot.txt`，此后分段、机检与复核都使用同一快照，不得一边翻译一边改源文。快照中的换行和段间分隔符也占用字符区间。
2. 按**语义边界**切分：章节 → 段落 → 句子。保留原编号（章节号、段号、句号）。每项记录唯一 `id` / `source` / `source_start` / `source_end`；下标是 Python 字符下标（不是 UTF-8 字节数），且必须满足 `snapshot[source_start:source_end] == source`。可把段尾换行并入前一段，以便区间连续。
3. 跨页、跨栏、跨章节的段落：按语义接续，不重复、不遗漏、不错位。区间必须递增且不重叠；ID 不得重复。
4. 页眉页脚、脚注、边注：单独翻译并标记，不混入正文。
5. `success` 的区间必须从 0 到 `len(snapshot)` 连续全覆盖；尚未翻译的区间不能用空 target 占位，应改判 `partial` 并在 `uncovered_ranges` 逐项声明。

### 第 3 步：逐段翻译 + 双语对照（段落全 + 可核验）
对每段输出结构化对照（不要只给译文），并同步写入工作版 `segments.json`：
- `id`（唯一段号）、`source`（原文段落，含段号）
- `target`（非空译文；译不出时写非空的 unable 说明标记，不留空）
- `source_start` / `source_end`（对应已保存快照的半开字符区间）
- `basis`（译法依据，尤其术语与关键句）

**逐句**翻译，不是逐段意译重写。句子边界保留。

### 第 4 步：关系守恒检查（关系准）
对每一句，用 references/hedge-strength.md 的强度分级检查，并核对：
- **指代**：this/these/it/该/其 等指代对象是否与原文一致。
- **否定与限定**：否定范围、only if/unless/under X、量词 some/most/all 保持原意。
- **因果 vs 让步**：because/causes（因果）与 although/despite（让步）不得互换。
- **数字与单位**：数值、单位、显著性（p<0.05）、置信区间**一字不改**。
- **公式与编号**：`$...$`、`$$...$$`、`\(...\)`、`\[...\]` 公式内容仅可规范化空白，`ln`→`lg`、上下标或运算符改变都不合格；`Fig. 2` 可译为 `图2`，`Eq. (3)` 可译为 `公式(3)`，但图表/公式引用类型与编号必须不变（`Fig. 2`→`Table 2`、`图2`→`表2`均失败）。
- **文献引用**：`[12]`/`(Smith, 2020)` 指向不变。

### 第 5 步：译文与交付核验（可核验，机械检查先行）
先把第 1 步术语表落盘为 `terminology.json`、第 3 步工作分段落盘为 `segments.json`，并按 references/output-schema.md 写出候选 `/app/output/result.json`。三个核验脚本均使用同一份源文快照与工作分段：

1. `python3 scripts/check_terminology.py --terms terminology.json --segments segments.json --report work/terminology-report.json`
   —— 机械检查术语**回填**（source 命中 `term` 或任一 alias 而 target 缺 locked 译名 → error）、旧译**漂移**（warning）、**frozen** 逐字约束；同一表面形式的多条目必须各有 `context`，每段只能命中一个语境候选，否则明确配置 error，有 error 退出码 1。
2. `python3 scripts/check_conservation.py --segments segments.json --report work/conservation-report.json`
   —— 逐段核对数字、文献引用、带单位量、四种定界形式的公式多重集合及图表/公式引用的**类型+编号**。公式只规范化空白；英文与中文标签可互译，不要求英文标签原样保留。**missing 或 added 任一非空都退出码 1**，added 不是备注。公式、图表/公式编号和文献引用会先掩码再抽数字，避免重复计数。
3. `python3 scripts/validate_translation_delivery.py --case /input/case.json --source-text work/source-snapshot.txt --result /app/output/result.json --work-segments segments.json --report work/delivery-report.json`
   —— 核 case_id、output_contract 字段存在性及可推断基本类型、段 ID、非空 target、快照逐字切片、递增不重叠区间、覆盖状态、partial/unable 的 `status_reason` 与精确 `uncovered_ranges`，并逐字段防止工作 `segments.json` 与最终 `result.segments` 漂移。未提供 `--work-segments` 时仅省略漂移比对，不省略其余检查。无法推断的契约类型记 warning；success 带 warning 不能通过，partial/unable 必须把对应人工核验缺口列出。

**交付门禁按状态区分，不能拿“全绿”掩盖降级，也不能拿 partial 逃避检查：**
- `success`：区间从 0 到快照末尾连续全覆盖（`uncovered_ranges` 为 `[]` 或省略），三个脚本均退出 0，术语 drift warning 与契约类型 warning 均已解决，且下述语义人工回核完成；这才叫“所有检查全绿”。
- `partial`：仍须跑结构/覆盖门禁；所有已交付段必须 ID 唯一、target 非空、区间合法递增不重叠、source 与快照一致，若有工作分段则 work/final 一致。`status_reason` 必须非空，`uncovered_ranges` 必须精确列出所有未译区间。术语/守恒报告存在 error、未运行 `--work-segments`、未做语义人工回核或契约类型只能人工判断时，均须把范围与报告路径列入 `status_reason` / `uncertainties`；delivery 脚本退出 0 只代表结构与覆盖声明通过，**不代表语义或全部机检通过**。
- `unable`：同样保留合法结构、精确未覆盖区间和非空原因，不编造已完成状态。

三个脚本覆盖不了的项仍需人工逐段回核（读译文，对照原文）：
1. 否定/限定/因果是否未变（references/hedge-strength.md）；
2. 指代对象是否一致；
3. 是否漏译、多译、错位。
生成**需人工确认清单**（译不准、歧义、术语冲突、原文残缺、未执行的语义核验），写入 `uncertainties`。success 修复后重跑至全绿；partial 如实交付缺口，不得静默省略核验。

### 第 6 步：产出结果
交付通过上述状态门禁的 `/app/output/result.json`，并输出双语对照文档（Markdown：段号 + 快照区间 + 原文 + 译文 + 依据）与术语表；`tool_commands` 记录实际执行的三条命令和报告路径。

## 检查点与降级

1. 第 0 步读完输入即写 `/app/output/result.json` 工作骨架（`case_id` + output_contract 字段占位 + `status:"in_progress"`）。中断准备交付时必须改为诚实的 `partial/unable`，删除空 target 占位段，并补齐 `uncovered_ranges` 与原因；工作骨架本身不冒充通过最终门禁的结果。
2. 按章节分块增量更新：每译完一章即回写 result.json 与 segments.json，不等到全文译完；两者始终使用同一快照及相同 ID/source/target/区间。
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
- `scripts/check_conservation.py` —— 数字/文献引用/带单位量/公式/图表公式引用守恒逐段核验（纯标准库）
- `scripts/validate_translation_delivery.py` —— 快照切片、ID/区间/覆盖、output_contract 与 work/final 交付门禁（纯标准库）
- `references/result.schema.json` —— result.json 静态 JSON Schema（动态区间与覆盖仍由上述脚本核验）
- `references/terminology-lock.md` —— 术语表抽取、锁定与冲突处理
- `references/hedge-strength.md` —— 限定词/程度词强度分级与守恒（关系准核心）
- `references/bilingual-alignment.md` —— 段落级双语对照与段号约定
- `references/translation-verification.md` —— 译文核验清单（数字/单位/公式/引用/否定）
- `references/output-schema.md` —— result.json 字段契约
- `examples/translation-examples.md` —— 标注为示例的对照（非正式案例）
