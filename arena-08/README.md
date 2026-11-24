# pdf-document-parsing · 文献文档解析 Skill

围绕真实科研 PDF 解析任务开发的、可被 Agent 调用的 Skill。核心纪律：**提得全、排得对、拆得清、核得回**。

## 用途

- 把科研 PDF 解析为结构化结果（正文、章节、表格、公式、图表位置），**每个单元可指回原文页码与区块**。
- 支持多栏阅读顺序恢复、复杂表格重建、章节层级识别、公式/特殊字符保真、扫描版 OCR。
- 可选把解析结果组织成**可编辑学术 PPTX**（备注含页级证据映射与讲稿要点），并渲染 PDF/PNG 预览。

## 文件结构

```
SKILL.md                              # 主 Skill（入口，YAML frontmatter + 十步流程）
scripts/parse_pdf.py                  # 真实坐标/逐页栏判定/阅读顺序/页眉页脚/表格候选（标准库+pdftotext）
scripts/parse_ocr_tsv.py              # Tesseract TSV → 词/行 text、bbox、confidence（纯标准库）
scripts/build_slides.py               # 可编辑 PPTX 生成 + 渲染预览（自包含）
references/layout-reading-order.md    # 多栏阅读顺序与页眉页脚判定（LLM 语义修正依据）
references/table-structure.md         # 表格结构重建规则
references/formula-preservation.md    # 公式/特殊字符保真
references/ocr-fallback.md            # 扫描版 PDF 的 OCR 流程
references/output-schema.md           # result.json 契约（含契约优先级与 blocks 分块落盘）
examples/parse-examples.md            # 标注为示例的解析样例
src/reproduce.py                      # 自检入口（校验+自测，非评测用例）
```

## 调用方式

加载 Skill 后，Agent 按 SKILL.md 的十步流程执行：

1. 读 `/input/case.json`（取 `case_id`、`output_contract` 字段、PDF 路径）与 `/input/task.md`。
2. **机械解析先行**：`python3 scripts/parse_pdf.py --pdf <PDF> --out work/blocks.json`，拿到真实坐标、`page_layouts` 逐页单/双栏与栏界（混合文档顶层 `columns:"mixed"`）、逐页初排阅读顺序、页眉页脚剔除与表格候选；未识别的页眉页脚带内词会重新分列、重新成行。退出码 2 → text-only 降级（坐标 null、order 按文本流、result 标 `mode`）。
3. OCR 使用 `tesseract <page>.png <out> tsv`（如需语言模型，在命令中加 `-l <lang>`），再以 `python3 scripts/parse_ocr_tsv.py --tsv <out>.tsv --out <out>.json` 获得词/行 text、bbox、confidence。普通文本输出不得伪造区域置信度。
4. LLM 只在 blocks.json 上做语义标注/修正（标题层级、表格语义）→ 结构识别 → 公式 → 页级证据映射 → 输出 result.json（+ 可选 PPTX）。

## 输出契约

`/app/output/result.json` 必含：`case_id`、`status`、`status_reason`、output_contract 要求的全部字段、结构化解析结果、页级证据映射、`uncertainties`。详见 `references/output-schema.md`。

## 依赖（三档诚实声明）

- **Python 无第三方依赖**：`scripts/parse_pdf.py` 与 `scripts/parse_ocr_tsv.py` 仅用标准库；`scripts/build_slides.py` 优先用 `python-pptx`（可选），未安装时自动回退到仅标准库的最小 OOXML 生成器。
- **poppler-utils（pdftotext）**：版面模式必需；缺失时 parse_pdf.py 退出码 2，降级 text-only（坐标 null、order 按文本流、result 标 `mode:"text-only"`）。
- **tesseract**（可选）：以 TSV 配置执行扫描件 OCR，保留真实词/行区域置信度；缺失时扫描页标 `image_only`，不得伪造 confidence。
- **soffice 或 libreoffice**（可选）：PPTX 渲染 PDF 预览；脚本统一调用实际探测路径，缺失或系统调用失败时跳过预览并在 result 注明。`--render` 生成 PPTX 同名 PDF；`--render-pdf <out.pdf>` 将转换结果移到确切指定路径。

## 异常处理与限制

- 加密 PDF → `status=unable`；扫描页 OCR 失败 → 标注不确定，不编造。
- 多栏顺序/公式上下标不确定 → 取最可能结果并在 `uncertainties` 说明判定依据。
- 本 Skill 只做结构解析，不评价、不总结、不推断科学结论。

## 最小调用示例（示意，非正式案例）

输入 `/input/case.json`：
```json
{"case_id": "demo", "output_contract": {"summary": "解析全文", "format": "json"},
 "pdf": "/input/paper.pdf"}
```

输出 `/app/output/result.json` 结构见 `references/output-schema.md` 与 `examples/parse-examples.md`。
