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

目标：把一份科研 PDF **完整、按序、可复核**地解析成结构化结果。四个纪律：**提得全、排得对、拆得清、核得回**——不丢行、不串栏、层级与表格结构还原、每个结果都能指回原文页码与区块。图表与公式在本 Skill 中**按结构元素识别，不解释其科学含义**。

## 何时使用 / 何时不用

**使用**：解析 PDF → 结构化文本/表格/公式/章节，带页级证据映射；或把解析结果组织成可编辑幻灯片。

**不用**：文献翻译、摘要写作、内容问答、知识图谱构建（那是其他 Skill 的职责）。本 Skill 不评价、不总结、不推断科学结论。

## 强制流程（按顺序执行；每步先记状态，允许部分完成）

### 第 0 步：读取输入，确定输出契约
1. 读 `/input/case.json`：取 `case_id`、`output_contract` 字段清单、PDF 文件路径、任务说明。
2. 读 `/input/task.md`：确认本次案例的具体要求（解析整篇 / 指定章节 / 表格 / 公式等）。
3. **先记录**：`case_id`、PDF 路径、output_contract 要求的字段名。后续 `result.json` 必须包含这些字段 + `case_id`，不得遗漏、不得改名。

### 第 1 步：机械解析（真实坐标与初排阅读顺序）
1. 先探测：`command -v pdftotext`。
2. 跑 `python3 scripts/parse_pdf.py --pdf <PDF> --out /app/work/blocks.json`：
   - 退出码 0 → `blocks.json` 已含逐词真实坐标、单/双栏判定（词 xMin 直方图双峰+栏间谷底）、初排阅读顺序（左栏→右栏）、页眉页脚剔除（≥50% 页重复行）、表格候选（`kind=table_candidate`，附 TSV 行与单元格 bbox）。**后续一切结构工作以它为底稿。**
   - 退出码 2 → pdftotext 缺失或执行失败，进入 **text-only 降级**：仅用可行手段提取纯文本，坐标字段一律 `null`，`order` 按文本流，result 标注 `mode:"text-only"` 并把降级写入 `uncertainties`。
3. 体检结论（页数、加密、有无文字层）记录进 `tool_commands`；加密 PDF 报 `status=unable`，不尝试破解；无文字层 → 走第 7 步 OCR，`tesseract` 缺失则该页标 `image_only`。

### 第 2 步：文字提取核对（提得全）
- 以 `blocks.json` 的块文本为准**逐页**核对：不丢行、不丢段——分页是"核得回"的前提，不要整篇一股脑 dump。
- 页眉页脚已被脚本剔除并存入 `headers_footers`，**不要混回正文**；脚注、边注单独标记（`type=footnote/marginalia`）。
- text-only 降级模式下无坐标可核对，须把"无版面信息"写进 `uncertainties`。

### 第 3 步：语义标注与顺序修正（排得对）
1. **LLM 只在 `blocks.json` 上工作**：对每个 block 做语义标注/修正（标题层级、摘要/正文/图注/参考文献类别、跨栏块归属、表格语义），**不再手算 bbox XML**。
2. 栏判定与阅读顺序以脚本输出为初排；仅在有明确证据（如跨栏标题被误切）时修正 `order`/`column`，并把修正依据写入 `uncertainties`。
3. 跨页续接：段落被截断到下一页时按语义接续，不得重复、不得错位。
4. 判定规则细则见 references/layout-reading-order.md；不确定的拼接在 `uncertainties` 里如实标注，**不靠猜**。

### 第 4 步：结构识别（拆得清）
- 识别标题层级（1/2/3 级）、摘要、正文段落、图表题注、公式编号、参考文献列表。
- 章节编号（如 `2.3`、`III.A`）保留原样，建立层级。
- 参考文献：逐条切分（按编号或首行缩进），保留原始编号。

### 第 5 步：表格解析（拆得清）
- 以 `blocks.json` 中 `kind=table_candidate` 的块为**底稿**（已附 TSV 行与单元格 bbox），再结合题注 `Table ...` 定位确认；脚本漏检的表格按 references/table-structure.md 人工定位。
- 重建行列与单元格归属；跨行跨列、合并单元格、多层表头、跨页续表都要还原。
- 输出 **Markdown 或 HTML**（合并单元格用 HTML `rowspan/colspan` 表达最准确），并附题注与页码。
- 规则见 references/table-structure.md。表格若为图片，标注为图片表格并走 OCR 或标注 `uncertainty`。

### 第 6 步：公式与特殊字符（拆得清）
- 数学公式、上下标、希腊字母、特殊符号：提取时**保留原样**，不"转写"成近似字符。
- 有 LaTeX 可读形式时附 `latex` 字段，但**始终保留 `original` 原文对照**；无法判定时标注 `uncertainty`，不要猜。
- 规则见 references/formula-preservation.md。

### 第 7 步：扫描版 OCR（提得全的兜底）
- 无文字层或文字层质量差：用 `tesseract` 识别；`tesseract` 缺失 → 该页标 `image_only` 并写入 `uncertainties`，不猜内容。
- 预处理（放大/二值化去噪）只用环境中**实际存在**的工具（先 `command -v` 探测）；OCR 后做**后处理校验**（常见错字对照）。
- 低置信度区域明确标注。流程见 references/ocr-fallback.md。

### 第 8 步：页级证据映射（核得回）
每个结构化单元（段落、标题、表格、公式、图注）记录：
- `page`（页码，从 1 起）
- `bbox`（区块坐标，若有）
- `confidence`（文字层 1.0；OCR 按置信度）
- `source`（如 `page=3, top-left column`）

这是本 Skill 的硬性要求：**关键结论可复核，读不出/不确定的地方如实标注**。

### 第 9 步：组织输出（结构化 + 可选幻灯片）
1. **主产物**：结构化 JSON（第 10 步的 result.json）+ 一份 Markdown/HTML 全文解析稿。
2. **可选产物**：把解析结果组织成**可编辑学术 PPTX**——每个结构单元（标题页/章节/表格/公式/图注/参考文献）对应一张幻灯片，备注里写入**页级证据映射**（页码+区块）与**讲稿要点**；再用 `soffice --headless --convert-to pdf`（如可用）生成 PDF/PNG 预览，**soffice 缺失则跳过预览并在 result 注明**。
   - 生成脚本：`scripts/build_slides.py`（自包含，见其头部用法说明）。
   - 说明：PPT 是"结构化结果的可编辑组织形态"，**不是替代**结构化 JSON/Markdown；评分以解析质量为重。

### 第 10 步：产出 result.json
严格写 `/app/output/result.json`，包含：
- `case_id`（原样回填）
- `status`（success / partial / unable）+ `status_reason`
- **output_contract 要求的全部字段**（回填，不遗漏、不改名）
- 结构化解析结果（blocks/tables/formulas/figures/sections）
- 证据映射与 `uncertainties`

完整字段定义见 references/output-schema.md。

## 可用工具（三档诚实声明；先 `command -v` 探测，不假设）

| 工具 | 档位 | 缺失时的处置 |
|---|---|---|
| `pdftotext`（poppler-utils） | **版面模式必需**（scripts/parse_pdf.py 的唯一外部依赖） | 降级 text-only：坐标字段 `null`、`order` 按文本流、result 标注 `mode:"text-only"` |
| `tesseract` | 可选（扫描件 OCR） | 扫描页标 `image_only`，写入 `uncertainties`，不猜内容 |
| `soffice`（LibreOffice） | 可选（PPTX 渲染 PDF/PNG 预览） | 跳过预览，result 注明"预览缺失：soffice 不可用" |

实际执行的命令写进 `tool_commands`；禁止编造工具输出，禁止声称工具具备其没有的能力。

## 检查点与降级

1. 第 0 步读完输入即写 `/app/output/result.json` 骨架（`case_id` + output_contract 占位 + `status:"in_progress"`）。
2. 第 1 步 parse_pdf.py 一跑完立即落盘 `blocks.json`；长文档按 references/output-schema.md 分块写 `blocks-part-N.json`，每批语义标注完成后增量回写。
3. 预算过半按 **正文 blocks（含页码）→ 章节结构 → 表格 → 公式/图注 → 预览** 降级；预览最先用时可弃。
4. 每次降级在 `status_reason` 写明降级级别与缺口页码；`status=partial` 也必须落盘。

## 异常与边界处理

| 情况 | 处置 |
|---|---|
| 加密 PDF / 无法打开 | `status=unable`，写明原因 |
| 无文字层且 OCR 失败 | 标注该页无法解析，不猜内容 |
| 多栏顺序不确定 | 给出最可能顺序，并在 `uncertainties` 说明判定依据 |
| 表格为图片 | 标注 `type=image_table`，OCR 或标 `uncertainty` |
| 公式无法还原 | 保留原文截图/近似，标注不确定，不臆造 |
| 页眉页脚/广告水印 | 标记并排除，不混入正文 |

## 复用与维护

- 解析脚本、规则表、示例均可被他人用于新的学科文献。
- 新增版式样本时，把判定规则回写进对应 references 文件。
- 每次运行输出保留 `case_id` 与工具命令记录，便于复现与审计。

详见随附资源：
- `scripts/parse_pdf.py` —— 版面机械解析：真实坐标、栏判定、阅读顺序、页眉页脚剔除、表格候选（标准库 + pdftotext）
- `references/layout-reading-order.md` —— 多栏阅读顺序与页眉页脚判定
- `references/table-structure.md` —— 表格结构重建规则
- `references/formula-preservation.md` —— 公式/特殊字符保真
- `references/ocr-fallback.md` —— 扫描版 PDF 的 OCR 流程
- `references/output-schema.md` —— result.json 完整字段与页级证据映射契约
- `scripts/build_slides.py` —— 可编辑 PPTX 生成与渲染预览（自包含）
- `examples/parse-examples.md` —— 标注为示例的解析样例（非正式案例）
