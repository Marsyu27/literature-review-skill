# pdf-document-parsing · 文献文档解析 Skill

围绕真实科研 PDF 解析任务开发的、可被 Agent 调用的 Skill。核心纪律：**提得全、排得对、拆得清、核得回**。

## 用途

- 把科研 PDF 解析为结构化结果（正文、章节、表格、公式、图表位置），**每个单元可指回原文页码与区块**。
- 支持多栏阅读顺序恢复、复杂表格重建、章节层级识别、公式/特殊字符保真、扫描版 OCR。
- 可选把解析结果组织成**可编辑学术 PPTX**（备注含页级证据映射与讲稿要点），并渲染 PDF/PNG 预览。

## 文件结构

```
SKILL.md                              # 主 Skill（入口，YAML frontmatter + 十步流程）
references/layout-reading-order.md    # 多栏阅读顺序与页眉页脚判定
references/table-structure.md         # 表格结构重建规则
references/formula-preservation.md    # 公式/特殊字符保真
references/ocr-fallback.md            # 扫描版 PDF 的 OCR 流程
references/output-schema.md           # result.json 契约与页级证据映射
scripts/build_slides.py               # 可编辑 PPTX 生成 + 渲染预览（自包含）
examples/parse-examples.md            # 标注为示例的解析样例
src/reproduce.py                      # 自检入口（校验+自测，非评测用例）
```

## 调用方式

加载 Skill 后，Agent 按 SKILL.md 的十步流程执行：

1. 读 `/input/case.json`（取 `case_id`、`output_contract` 字段、PDF 路径）与 `/input/task.md`。
2. 判 PDF 类型（文字层 / 扫描版）。
3. 提取文字 → 版面分析（多栏顺序）→ 结构识别 → 表格/公式 → 页级证据映射 → 输出 result.json（+ 可选 PPTX）。

## 输出契约

`/app/output/result.json` 必含：`case_id`、`status`、`status_reason`、output_contract 要求的全部字段、结构化解析结果、页级证据映射、`uncertainties`。详见 `references/output-schema.md`。

## 依赖

- 首选工具：`pdftotext`（pdf-text-tool）、`pdftoppm`（pdf-render-tool）、`tesseract`（ocr-tool）、`python3`（scientific-python）、`soffice`（office-renderer）。
- `scripts/build_slides.py` 优先用 `python-pptx`；未安装时自动回退到仅标准库的最小 OOXML 生成器，无需额外依赖。
- `requirements.txt` 为空：核心解析依赖环境预装工具，脚本无强制第三方包。

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
