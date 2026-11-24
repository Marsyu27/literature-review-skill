# 扫描版 PDF 的 OCR 流程（OCR Fallback）

## 触发条件

- `pdftotext` 提取结果为空白或几乎无文本 → 无文字层，判定为扫描版。
- 或文字层存在但错字密度高（抽样对比渲染图）→ 混合型，对低质量页走 OCR。

## 流程

1. **渲染**：`pdftoppm -png -r 300` 逐页渲染为图像（poppler-utils；与 parse_pdf.py 同源）。
2. **预处理**（只用环境中实际存在的工具，先 `command -v` 探测；都没有则跳过预处理直接 OCR）：
   - 灰度化、二值化（Otsu）、去噪、去倾斜（deskew）。
   - 低分辨率页放大到 ≥300 DPI 等效。
3. **OCR（TSV 必需）**：`tesseract <page>.png <out> tsv`。需要指定语言时在命令中加 `-l eng` 或 `-l chi_sim+eng`。随后运行：
   ```bash
   python3 scripts/parse_ocr_tsv.py --tsv <out>.tsv --out <out>.json
   ```
   解析器仅用标准库，过滤空文本，输出 `mode/confidence_scale/words/lines`。每个词与行都有 `text/bbox/confidence`，bbox 为像素坐标 `[x0,y0,x1,y1]`。confidence 保留 Tesseract 的 **0–100** 标度，非法或未知的 `-1` 转为 `null`；行 confidence 是已知词 confidence 按词框面积加权的均值，没有可用词置信度时为 `null`。
4. **后处理校验**：
   - 常见 OCR 错字对照（`rn`↔`m`、`1`↔`l`、`0`↔`O`、`α`↔`a`）。
   - 数字/单位/公式区域重点复核，必要时放大重 OCR。
5. **置信度与诚实性**：低置信度区域在输出中标注。普通 `tesseract ... <out>` 文本结果不含区域 confidence，不得为它伪造词/行 bbox 或置信度，也不得手写、猜测或把其他评分冒充 Tesseract confidence。后处理若改文本，不得相应“提升”仪器测得的 confidence。

## 边界

- 图片型公式、图片型表格：OCR 后仍需人工核对，标注 `uncertainty`。
- OCR 无法识别的页 → `status=partial`，该页标注"无法解析"，不编造内容。
- 语言混杂（中英混排）：用多语言模型，并在 `uncertainties` 说明。
