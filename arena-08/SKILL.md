---
name: pdf-document-parsing
description: >-
  Use when the task is to parse a scientific PDF into structured, reusable
  content — extract text, restore multi-column reading order, rebuild tables,
  recognize section hierarchy, preserve formulas and special characters, and OCR
  scanned pages. Produces a structured result (JSON + Markdown) where every block
  is mapped back to its source page and region, and optionally organizes the
  parsed content into editable academic slides (PPTX) with speaker notes and a
  rendered PDF/PNG preview. Do NOT use for summarizing, translating, or answering
  content questions — parse structure and evidence, do not interpret the science.
---

# 科研 PDF 文档解析（Scientific PDF Parsing）

目标：把科研 PDF **完整、按序、可复核**地解析成结构化结果。纪律：**提得全、排得对、拆得清、核得回**。执行链固定为 `parse_pdf → refine_layout → refined reading_units/blocks 上的语义工作 → validate_layout`。图表与公式按结构元素识别，不解释其科学含义。

## 何时使用 / 不用

**使用**：PDF → 结构化文本/表格/公式/章节，带页级证据；或把解析结果组织为可编辑幻灯片。

**不用**：文献翻译、摘要写作、内容问答、知识图谱构建。不评价、不总结、不推断科学结论。

## 强制流程（按顺序执行；允许明确 partial）

### 第 0 步：读输入，确定输出契约

1. 读 `/input/case.json`：`case_id`、`output_contract`、PDF 路径与任务；读 `/input/task.md`。
2. 先记字段清单；最终结果原样回填 `case_id` 和 output_contract 的每个字段。
3. 先落输出骨架和状态；加密 PDF 报 `unable`，不破解。

### 第 1 步：原始机械解析（parse_pdf，仅初排）

1. 探测 `command -v pdftotext`，运行：
   ```bash
   python3 scripts/parse_pdf.py --pdf <PDF> --out /app/work/blocks.json
   ```
2. 退出 0：得到真实词坐标、逐页 `page_layouts`、原始 `blocks/tables/headers_footers`。每个块的 `source_lines=[{text,bbox}]` 是后续唯一几何底稿；`id/text/kind` 是原记录，表格 `rows/cells` 不得在本流程中失真。
3. parse 的现有初排仍可能是整左栏→整右栏，**不得把这一步宣称为已正确 zone 重排**，也不得让 LLM 在此手改几何。
4. 退出 2：进入 text-only；bbox 为 null、order 按文本流并写 uncertainties。text-only 无真实几何，不运行 refine。无文字层转第 7 步 OCR，失败则明确 `image_only`。

### 第 2 步：纵向 zone 机械细化与文字核对（refine_layout）

```bash
python3 scripts/refine_layout.py \
  --input /app/work/blocks.json \
  --out /app/work/layout.refined.json \
  --report /app/work/conservation.json
```

1. 每页依据 `page_layouts.column_boundary` 和 source_lines 真实 bbox 划分 `preamble/abstract/body_columns/full_width_float/...` 纵向 zones；在各 body zone 内分别左栏 y→右栏 y，跨 zone 按 y。**禁止整页一次左右分栏或同 y 左右正文混读。**
2. 首页标题、作者、摘要处理到第一次稳定双栏正文；通栏 table/figure 先找几何证据，caption 可上可下。caption/table 样式只能辅助，证据不足保留 ordinary columns 并记录 warnings。
3. 输出的 `page_zones`、`reading_units`、更新后的 `blocks` 和 `conservation_report` 全部保留。所有 body/header/footer 原 ID 必须出现且只出现一次；unit.text 由其 source_parts 顺序生成。
4. 逐页核 source/report 的 block 数、字符/词数、normalized SHA、missing/duplicate/unmapped；**后续一切语义工作只使用 refined 的 reading_units/blocks，不回到旧整页栏序。**

### 第 3 步：语义标注与顺序使用（不再机械改序）

1. LLM 只在 refined `reading_units/blocks` 上标注标题层级、摘要、正文、图注、参考文献和表格语义；**不手算 bbox，不重写 source_parts 来迎合文本。**
2. 几何 algorithm 的证据见 references/layout-reading-order.md。语义不确定写 `uncertainties`，不得用猜的顺序覆盖机械证据；确需人工改动也仍须通过最终 validator。
3. 跨页续接不得重复原块或句子；原块文字保留，必要时用语义关联字段表达，而不是悄悄删并文本。

### 第 4 步：结构识别

- 识别章节层级、题注、公式编号和参考文献，保留原编号。
- title/abstract/caption/formula 若最终作为已解析字段输出，建立 `document_evidence` 到精炼后的原 block/unit；不能只给无来源的新字符串。

### 第 5 步：表格解析

- 以 refined blocks 中 `kind=table_candidate` 和原 `tables[].block_id` 为底稿，保留原 rows/cells/bbox；table entry 对应 block 必须仍存在。
- 跨栏左右 piece 应位于同一 full-width zone；caption 在上/下按机械 order 使用。语义重建的 HTML/Markdown 写新字段，不覆盖原单元格证据。
- 合并单元格、多层表头、跨页续表按 references/table-structure.md；图片表格走 OCR 或标 uncertainty。

### 第 6 步：公式与特殊字符

- 原公式、上下标、希腊字母、数字、负号逐字保留；LaTeX 另存 `latex`，`original` 永远对照，无法判定不猜。
- 不将不同原公式的原文/LaTeX 拼成一个新公式；公式 reading unit/part 必须可回链。见 references/formula-preservation.md。

### 第 7 步：扫描版 OCR 兜底

- 先实际探测 `tesseract`。运行 `tesseract <page>.png <out> tsv`（按实际语言加 `-l`），再：
  ```bash
  python3 scripts/parse_ocr_tsv.py --tsv <out>.tsv --out <out>.json
  ```
- 词/行 confidence 保留 Tesseract 0–100，行值按 bbox 面积加权；未知为 null。禁止给普通文本伪造区域置信度。
- OCR 失败的页/块明确 gaps/uncertainties；缺失不是 success。

### 第 8 步：页级证据映射

每个结构化单元记录 `page/bbox/confidence/source`；额外保留 refined `zone_id/source_unit_ids/source_parts`。title/abstract/caption/formula 回链规则见 references/output-schema.md。所有机械映射来自工具，LLM 不计算 fake bbox。

### 第 9 步：组织输出与可选幻灯片

- 主产物为结构化 JSON + Markdown/HTML 全文稿，携带 refined zones/units/conservation report；长文档按 output-schema 分块，不能用抽样 blocks 或 blocks_files 漏掉原块。
- 可选 `scripts/build_slides.py` 生成可编辑学术 PPTX。PPT 不替代结构化 JSON。实际探测 soffice/libreoffice，不可用时诚实跳过预览。

### 第 10 步：产出 final-result.json

包含 case_id、`status+status_reason`、output_contract 全字段、document/blocks/tables/formulas/figures、page_zones/reading_units/conservation_report、证据映射、uncertainties 和必要 gaps。

`partial` 必须填 status_reason。未映射 reading-unit 原块要同时精确列入 `unmapped_block_ids` 与 `gaps[].block_id(s)`；最终 blocks 本身仍不得丢源块。`success` 不得带未披露 gaps，且所有声称已解析的 title/abstract/caption/formula 均需 document_evidence。

### 第 11 步：独立守恒校验（必须）

```bash
python3 scripts/validate_layout.py \
  --source /app/work/blocks.json \
  --result /app/work/final-result.json \
  --report /app/work/validation.json
```

- 退出 1 不得交付 success；修复或明确 unable/partial。退出 0 的 partial 报告中仍是 `success=false`。
- 核 source coverage、ID 唯一、text/SHA/字数、part union、unit.text、bbox/zone、blocks_files/embedding、table/formula 回链与 document_evidence。
- validator 通过证明声明的守恒契约成立，不证明数学语义/科学内容已读懂。

## 可用工具（先探测）

| 工具 | 用途 | 缺失时 |
|---|---|---|
| `pdftotext` | parse_pdf 的真实 bbox 输入 | text-only；不能伪造几何 |
| `refine_layout.py` / `validate_layout.py` | zone 细化 / 磁盘独立核守恒 | 随 Skill 提供，纯标准库 |
| `tesseract` | 扫描件 OCR TSV | 标 image_only/partial，不猜 |
| `soffice` / `libreoffice` | 可选 PPTX PDF 预览 | 跳过并注明 |

实际命令写 `tool_commands`，禁止编造工具结果。

## 检查点与降级

1. parse 后立即保留 blocks.json；refine 后立即保留 refined 与 conservation.json。
2. 长文档分块按页，不跨页；每批语义结果增量保留原 ID 与 evidence。
3. 预算不足按正文 blocks→章节→表格→公式/图注→可选预览降级。任何 partial 都写页码/ID 缺口，最后仍跑 validator。
4. 多栏或 float 无可靠 full-width 证据时保守留在 ordinary columns 并写 warnings；不能为了整齐丢字或创建原文不存在的句子/公式。

## 复用与维护

新样本必须回写几何边界和自检；自检 `python3 src/reproduce.py` 只在临时目录生成文件。随附资源：
- `scripts/parse_pdf.py` —— 原块、source_lines 与初排
- `scripts/refine_layout.py` —— 纵向 full-width/body zones 与 reading_units
- `scripts/validate_layout.py` —— 独立守恒 validator
- `scripts/parse_ocr_tsv.py` / `scripts/build_slides.py` —— OCR / 可选幻灯片
- `references/layout-reading-order.md`、`references/output-schema.md` —— 几何与 schema 契约
- `src/layout_quickstart.py`、`examples/parse-examples.md` —— 可加载 JSON 几何的示例（不含科学理解声明）
