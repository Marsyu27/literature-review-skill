# pdf-document-parsing · 文献文档解析 Skill

围绕真实科研 PDF 解析任务开发的 Skill。核心纪律：**提得全、排得对、拆得清、核得回**。流程先做机械几何，再让语义工作只消费可审计的 refined reading units，最后独立核守恒。

## 用途与边界

- 把科研 PDF 解析为结构化结果（正文、章节、表格、公式、图表位置），每个单元可指回原文页码与区块。
- 支持逐页多栏、页中通栏浮动体的纵向 zone 阅读顺序、复杂表格重建、章节层级、公式/特殊字符保真、扫描版 OCR。
- 可选把解析结果组织成可编辑学术 PPTX。
- **只做结构与证据解析**；不评价、不总结、不推断科学结论。Examples 和自检中的几何通过，不表示工具理解了数学语义或科学内容。

## 文件结构

```
SKILL.md                              # 主 Skill（保留 YAML frontmatter）
scripts/parse_pdf.py                  # pdftotext 真实词坐标 → 原块 + source_lines（初排）
scripts/refine_layout.py              # source_lines → 纵向 page_zones / reading_units（纯标准库）
scripts/validate_layout.py            # 独立从磁盘核 blocks/parts/zones/tables/evidence（纯标准库）
scripts/parse_ocr_tsv.py              # Tesseract TSV → 词/行 text、bbox、confidence（纯标准库）
scripts/build_slides.py               # 可编辑 PPTX 生成 + 可选渲染预览
src/layout_quickstart.py              # 可加载 JSON 几何 fixture 的真实 CLI quickstart
references/layout-reading-order.md    # zone 算法、保守几何边界与降级说明
references/output-schema.md           # refined/final-result schema 与守恒契约
references/table-structure.md         # 表格结构重建规则
references/formula-preservation.md    # 公式/特殊字符保真
references/ocr-fallback.md            # 扫描版 PDF 的 OCR 流程
examples/parse-examples.md            # 示意样例与 quickstart（非科学语义判断）
src/reproduce.py                      # 全部轻自检，产物只在临时目录
```

## 完整运行链（quickstart）

```bash
# 1) 原始块：保留真实 line/text/bbox；parse 自身不声称已做好 zone 重排
python3 scripts/parse_pdf.py --pdf paper.pdf --out work/blocks.json

# 2) 机械细化：逐页、逐垂直 zone 排左右栏，重建可靠通栏浮动体
python3 scripts/refine_layout.py \
  --input work/blocks.json \
  --out work/layout.refined.json \
  --report work/conservation.json

# 3) 语义步骤只读取 layout.refined.json 的 reading_units/blocks。
#    保存 title/abstract/caption/formula 的原始块回链，不重排/重写 source_parts。
#    此处可在 work/final-result.json 加入 document/type/table/formula 等结果。

# 4) 最终独立校验；也可直接把 layout.refined.json 作为 --result
python3 scripts/validate_layout.py \
  --source work/blocks.json \
  --result work/final-result.json \
  --report work/validation.json
```

`validate_layout.py` 退出码：0 = 所声明状态通过，1 = 守恒/回链失败。`status=partial` 只有在 `gaps` 与 `unmapped_block_ids` 明示缺口时才可对未映射 reading units 返回 0；报告仍为 `success=false`、`validation_status=partial`。源块从最终 `blocks` 丢失、块文本被删/改、重复 ID、part 与 unit 文本不一致、zone 错位、table/formula 回链失效，均返回 1。

已有 JSON 几何 fixture 可直接运行：

```bash
python3 src/layout_quickstart.py --input work/blocks.json --workdir /tmp/layout-demo
# 不带 --input 时创建合成两页几何，默认临时目录并在退出时清理
python3 src/layout_quickstart.py
python3 src/reproduce.py
```

## 细化原则（不让 LLM 手算 bbox）

- `parse_pdf.py` 每个块现在附 `source_lines=[{text,bbox}]`。原 `id/text/kind/page/column`、表格 `rows/cells` 均保留，CLI 与既有 OCR/PPT 工具路径不变。
- `refine_layout.py` 只在 page_layouts 的**该页栏界**和 source_lines 真实几何上工作。首页标题/作者/摘要处理到第一次稳定双栏正文；其它垂直区间分别先左栏 y、再右栏 y。跨 zone 按 y，不把同 y 左右正文混为双线。
- 通栏 seed 必须来自跨栏 line 或左右表格候选的同 y 重建证据；`Table/Figure` 字样只作辅助扩展。上置/下置 caption 都可与相邻 table-cell lines 合并。证据不足仍留在 `body_columns`，并在 `uncertainties`/report warnings 说明。
- `reading_units[].source_parts` 是原块的完整片段，带 `source_block_id/source_unit_id/text/hash/bbox`；`unit.text` 由 parts 顺序拼接。公式块独立成 unit，不把不同原公式的原文/LaTeX 拼成一个新公式。
- 几何阈值按本页中位线高和正常行距缩放，详见 `references/layout-reading-order.md`。没有真实坐标时不能伪造 zone。

## blocks、embedding 与 blocks_files 守恒

最终 blocks 必须对源 `body/header/footer/table_candidate` 等每个 ID 恰好一次，保留原文字和 kind/page/column；重排只改 `order` 并增加 `zone_id`。`tables[].block_id` 和公式证据必须能找到原块。

`validate_layout.py` 支持根级 `blocks`、`blocks_files`（相对 result/source JSON 的目录解析），以及 `layout`/`refined_layout` 内嵌 reading units。根 blocks 与内嵌 blocks 同时存在时不得覆盖不同文本/zone；分块文件不可只给抽样而静默漏块。行数不是充分条件：还核文本规范化 SHA、字数、part union、unit 摘要、zone 顺序、bbox 和原 table cells。

## 依赖（三档诚实声明）

- **Python 无新第三方依赖**：`parse_pdf.py`、`refine_layout.py`、`validate_layout.py`、`parse_ocr_tsv.py` 均只用标准库；`build_slides.py` 的 python-pptx 仍为可选增强，未安装时用 OOXML fallback。
- **poppler-utils（pdftotext）**：版面模式必需；缺失时 parse_pdf 退出码 2，降级 text-only。text-only 不得运行几何 refine。
- **tesseract**（可选）：扫描件 OCR，保留真实置信度；缺失就标 `image_only`，不得伪造。
- **soffice/libreoffice**（可选）：PPTX 预览；缺失或系统调用失败时明确跳过。

## 输出契约

`/app/output/result.json` 必含 case 要求的字段、结构化结果、页级证据、`uncertainties`、`gaps`（若有）及 refined `page_zones/reading_units/conservation_report`。`success` 若声称已解析 title/abstract/caption/formula，必须同时提供可核的 `document_evidence`。完整字段和 partial 规则见 `references/output-schema.md`。
