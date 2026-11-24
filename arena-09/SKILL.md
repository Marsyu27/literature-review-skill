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

### 第 5 步：导出前记录质检（拆得细 + 对得上）
按 references/quality-check.md 逐条检查：断言过宽、证据不足、关系类型错误、主体混淆、来源缺失、限定词丢失。每条给出**可复现的判定依据**。检查不通过 → 回第 1 步或标 `uncertain`。JSON-LD 导出前运行：
```
python scripts/validate_nanopub.py --records-only /app/output/result.json
```
此步只机检谓词词表、record 必填字段、唯一连续 id 与 evidence 状态规则，**不导出 JSON-LD，不代表 JSON-LD 或 Final 已通过**。`status=unverified` 的空 evidence 会留下可解释 warning，其他状态的空 evidence 是 error。

### 第 6 步：records-only 已通过 → 机械导出 → 最终等价质检（读得懂）
确认第 5 步 records-only 已通过后，**只运行 exporter，从 `/app/output/result.json` 的 `nanopublications` 与 `pubinfo` 机械生成 JSON-LD；模型不得独立另写、补写或同步第二份 JSON-LD/pubinfo**（完整 canonical 映射见 references/output-schema.md）：
```
python scripts/export_nanopub.py /app/output/result.json --out-dir /app/output/nanopubs --update-result
python scripts/validate_nanopub.py /app/output/result.json [extra.jsonld ...]
```
每条 record 的 id 必须唯一、连续且为 `np-NNN`，生成同名文件及 `urn:nanopub:<case_id>:<n>`；`@context` 固定，`@graph` 恰为 assertion/evidence/provenance/pubinfo 四对象列表。`--update-result` 仅更新 `jsonld_files` 并清除内嵌 `jsonld` / `json_ld` 陈旧字段，不删其他文件。partial/unverified 也按真实 records 导出，空证据仍保留 evidence graph 三键。

最终 validator 复用 exporter 的 `build_document` 做 canonical JSON 树严格全等比较：文档数必须等于 record 数，URN 一一对应，SPO/condition、evidence、status/basis、provenance 链接与字段、pubinfo 全部逐项相符；对象键顺序无关，数组顺序和任何字段/值缺多或改变都会导致失败。内嵌字段、`jsonld_files` 和 CLI 附件合并计数，额外来源不能绕过数量或内容映射。缺文档、多文档、重复 URN、非 canonical 外壳或任何内容不一致均为 error，修正 records 后重新机械导出并复检才可交付。

## 检查点与降级

- 第 0 步读完输入即把 `result.json` 骨架（`case_id` + `status: "in_progress"` + output_contract 全部字段的空值）写入 `/app/output/result.json`，之后每阶段就地更新。
- 断言逐批**增量落盘**：每完成一批（如一个章节/段落组）即把该批 nanopublications 追加写入结果或增量文件（如 `/app/output/nanopubs-part-N.json`），最终合并。
- 预算（请求数/时间）过半仍未完成时按顺序降级：**证据绑定 → 断言 → provenance → JSON-LD**，靠后项可放弃。
- 未完成部分标 `status: "partial"`，在 `status_reason` 写明已覆盖的段落范围、中断位置和全部缺口，不伪造已完成。partial 若已有输出，仍须满足已声明字段的输出契约并运行最终严格质检；缺少 JSON-LD 就是最终 error，不能用导出前记录质检的 warning 或跳过说明掩盖。确实无法导出时不得声称 JSON-LD 已完成，须在 `status_reason`/`uncertainties` 明列该缺口。

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
- `scripts/export_nanopub.py` —— records 与 result.pubinfo → canonical JSON-LD 的唯一机械导出器
- `scripts/validate_nanopub.py` —— records-only 与最终严格等性质检（词表/字段/@context/四 graph/URN/完整内容映射）
- `src/reproduce.py` —— 真实 CLI 正反回归；仅在 tempfile 写测试产物
- `examples/nanopub-examples.md` —— 标注为示例的断言样例（非正式案例）
