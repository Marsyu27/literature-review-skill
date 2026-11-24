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

### 第 1 步：PDF 体检（判型）
用命令行工具检查，不要凭文件名猜：
- 是否有**文字层**：`pdftotext`（或环境中的 pdf-text-tool）对第 1 页能否提取出非空文本。能 → 文字版；不能 → 扫描版（走第 6 步 OCR）。
- 页数、页面尺寸、是否加密（加密时报告 `status=unable`，不要尝试破解）。
- 抽样检查是否**多栏**（见 references/layout-reading-order.md）。

### 第 2 步：文字提取（提得全）
- 有文字层：`pdftotext -layout`（保行结构）为主；必要时用 `pdftotext -bbox-layout` 获取坐标。
- 逐页提取，**不要整篇一股脑 dump**——分页是"核得回"的前提。
- 页眉页脚、脚注、边注：先单独识别并标记（`type=header/footer/footnote/marginalia`），**不要混进正文**。

### 第 3 步：版面分析与阅读顺序（排得对）
1. 用渲染工具（`pdftoppm` 或 pdf-render-tool）把页面渲染成 PNG，供视觉判定栏数、栏边界、跨栏标题。
2. 双栏/多栏：先判栏边界（x 坐标），**逐栏**从上到下提取，再按"左栏→右栏→跨栏续接"合并。跨栏的大标题/图表不归入某一栏。
3. 跨页续接：段落被截断到下一页时，按语义接续，不得重复、不得错位。
4. 判读顺序判定规则见 references/layout-reading-order.md；不确定的拼接在 `uncertainties` 里如实标注，**不靠猜**。

### 第 4 步：结构识别（拆得清）
- 识别标题层级（1/2/3 级）、摘要、正文段落、图表题注、公式编号、参考文献列表。
- 章节编号（如 `2.3`、`III.A`）保留原样，建立层级。
- 参考文献：逐条切分（按编号或首行缩进），保留原始编号。

### 第 5 步：表格解析（拆得清）
- 定位表格区域（框线、题注 `Table ...`）。
- 重建行列与单元格归属；跨行跨列、合并单元格、多层表头、跨页续表都要还原。
- 输出 **Markdown 或 HTML**（合并单元格用 HTML `rowspan/colspan` 表达最准确），并附题注与页码。
- 规则见 references/table-structure.md。表格若为图片，标注为图片表格并走 OCR 或标注 `uncertainty`。

### 第 6 步：公式与特殊字符（拆得清）
- 数学公式、上下标、希腊字母、特殊符号：提取时**保留原样**，不"转写"成近似字符。
- 有 LaTeX 可读形式时附 `latex` 字段，但**始终保留 `original` 原文对照**；无法判定时标注 `uncertainty`，不要猜。
- 规则见 references/formula-preservation.md。

### 第 7 步：扫描版 OCR（提得全的兜底）
- 无文字层或文字层质量差：用 OCR 工具（`tesseract` 或 ocr-tool）识别。
- 预处理：放大/二值化去噪（可用 scientific-python），再 OCR；OCR 后做**后处理校验**（常见错字对照）。
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
2. **可选产物**：把解析结果组织成**可编辑学术 PPTX**——每个结构单元（标题页/章节/表格/公式/图注/参考文献）对应一张幻灯片，备注里写入**页级证据映射**（页码+区块）与**讲稿要点**；再用渲染工具（office-renderer / `soffice --headless --convert-to pdf`）生成 PDF/PNG 预览。
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

## 可用工具（按环境实际探测，不假设）

| 用途 | 首选命令 | 环境工具名 |
|---|---|---|
| 文字提取 | `pdftotext -layout` | pdf-text-tool |
| 页面渲染 | `pdftoppm -png -r 150` | pdf-render-tool |
| OCR | `tesseract <img> out` | ocr-tool |
| 后处理/结构化 | `python3`（numpy/pandas/scipy） | scientific-python |
| PPT/Office 渲染 | `soffice --headless --convert-to pdf` | office-renderer |
| 字体检查 | `fc-list` | font-discovery |

**使用前先 `command -v <cmd>` 探测**；命令不存在则改用环境提供的对应工具，并把实际使用的命令写进运行状态。禁止编造工具输出。

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
- `references/layout-reading-order.md` —— 多栏阅读顺序与页眉页脚判定
- `references/table-structure.md` —— 表格结构重建规则
- `references/formula-preservation.md` —— 公式/特殊字符保真
- `references/ocr-fallback.md` —— 扫描版 PDF 的 OCR 流程
- `references/output-schema.md` —— result.json 完整字段与页级证据映射契约
- `scripts/build_slides.py` —— 可编辑 PPTX 生成与渲染预览（自包含）
- `examples/parse-examples.md` —— 标注为示例的解析样例（非正式案例）
