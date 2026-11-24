---
name: nanopublication-extraction
description: >-
  Use when the task is to turn scientific-paper claims into nanopublications —
  decompose paragraphs into atomic, independently-verifiable assertions
  (subject-predicate-object), bind each assertion to its minimal sufficient
  evidence snippet and exact source location, record full provenance metadata
  (paper, authors, year, version, identifiers), and export machine-readable
  JSON-LD/RDF. Produces per-assertion nanopublications, not one blob per
  paragraph. Do NOT use for translation, polishing, summarization, or Q&A —
  split and anchor claims faithfully, do not rephrase or infer beyond the text.
---

# Nanopublication 抽取（Nanopublication Extraction）

目标：把论文结论拆成**一条条可独立判断真假的断言**，每条绑定**最小充分证据 + 原文位置 + 来源元数据**，并导出**可机器读取**的结构。四个纪律：**拆得细、对得上、追得回、读得懂**。

## 何时使用 / 何时不用

**使用**：把论文段落拆成 Nanopublication（断言 + 证据 + 来源），导出 JSON-LD/RDF。

**不用**：翻译、润色、整段摘要、内容问答。本 Skill 只做忠实拆解与对齐，不推断原文没有的断言、不合并/改写结论。

## 强制流程（按顺序执行）

### 第 0 步：读输入，定输出契约
1. 读 `/input/case.json`：取 `case_id`、`output_contract` 字段、论文材料路径、任务范围。
2. 读 `/input/task.md`：确认范围（整篇 / 指定段落 / 指定章节）。
3. 记录 `case_id`。`result.json` 必须含 `case_id` 与全部 output_contract 字段。

### 第 1 步：断言拆解（拆得细）
对每个目标段落，按 references/assertion-decomposition.md 拆成**原子断言**：
- 每条 = 单一 `subject – predicate – object`，可独立判断真假。
- 复合句按**并列/因果/让步/条件**拆开，每条保留各自的**条件与限定范围**（如"在 X 条件下""n=3""p<0.05"）。
- 拒绝把整段塞进一个"断言"字段。

### 第 2 步：证据绑定（对得上）
每条断言绑定**最小充分证据**（见 references/evidence-binding.md）：
- `evidence_text`：真正支撑该断言的**最小原文片段**（不是整段复制）。
- `evidence_location`：原文位置（`page` + `§章节` + `¶段落` + `Fig./Table/Eq.`）。
- 区分**直接证据**与**间接推论**：断言由原文直接陈述 → `direct`；需要推断 → `indirect` 并标注推断依据。

### 第 3 步：来源元数据（追得回）
记录完整溯源链（见 references/provenance-metadata.md）：
- 论文、作者、年份、版本、DOI/标识符、数据来源。
- 断言 → 证据 → 论文 → 作者 → 年份 → 版本 的链路完整，他人能据此回到原文。

### 第 4 步：关系类型受控词表（读得懂 + 对得上）
谓词（predicate）从 references/relation-vocabulary.md 的**受控词表**取值，不自由发挥；主体/客体方向必须准确（谁作用于谁）。

### 第 5 步：质量检查（拆得细 + 对得上）
按 references/quality-check.md 逐条检查：断言过宽、证据不足、关系类型错误、主体混淆、来源缺失、限定词丢失。每条给出**可复现的判定依据**。检查不通过 → 回第 1 步或标 `uncertain`。

### 第 6 步：结构化导出（读得懂）
写 `/app/output/result.json`（见 references/output-schema.md），并导出 JSON-LD（含 `assertion` / `provenance` / `pubinfo` 三部分），字段与序列化形态符合约定，下游程序可直接解析。

## 异常与边界

| 情况 | 处置 |
|---|---|
| 扫描件无文本层 | 先 OCR；仍不可靠则标 `uncertain`，不臆造断言 |
| 断言找不到支撑证据 | 标 `status=unverified`，写"证据缺失"，不硬绑 |
| 断言与证据冲突 | 保留两处原文并标 `conflict`，不擅自取舍 |
| 主体/关系方向不明 | 标 `uncertain`，不猜测方向 |
| 限定词/条件被省略 | 断言必须保留限定词，缺失则 `uncertain` |

## 复用与维护

- 字段定义、受控词表、抽取规则、证据定位方法可被他人复用。
- 每次运行保留 `case_id` 与工具命令，便于复现与审计。
- 本 Skill 只做忠实拆解对齐，不评价研究结论。

详见随附资源：
- `references/assertion-decomposition.md` —— 断言拆解规则（并列/因果/让步/条件）
- `references/relation-vocabulary.md` —— 关系类型受控词表
- `references/evidence-binding.md` —— 证据绑定（最小充分 + 直接/间接）
- `references/provenance-metadata.md` —— 来源元数据与溯源链
- `references/quality-check.md` —— 质量检查清单
- `references/output-schema.md` —— result.json / JSON-LD 字段契约
- `examples/nanopub-examples.md` —— 标注为示例的断言样例（非正式案例）
