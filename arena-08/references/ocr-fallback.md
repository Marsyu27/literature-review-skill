# 扫描版 PDF 的 OCR 流程（OCR Fallback）

## 触发条件

- `pdftotext` 提取结果为空白或几乎无文本 → 无文字层，判定为扫描版。
- 或文字层存在但错字密度高（抽样对比渲染图）→ 混合型，对低质量页走 OCR。

## 流程

1. **渲染**：`pdftoppm -png -r 300` 逐页渲染为图像。
2. **预处理**（用 scientific-python，如 Pillow/OpenCV 可用则用）：
   - 灰度化、二值化（Otsu）、去噪、去倾斜（deskew）。
   - 低分辨率页放大到 ≥300 DPI 等效。
3. **OCR**：`tesseract <page>.png out -l eng`（或含中文 `-l chi_sim+eng`，按文档语言）。
4. **后处理校验**：
   - 常见 OCR 错字对照（`rn`↔`m`、`1`↔`l`、`0`↔`O`、`α`↔`a`）。
   - 数字/单位/公式区域重点复核，必要时放大重 OCR。
5. **置信度**：OCR 结果附置信度；低置信度区域在输出中标注。

## 边界

- 图片型公式、图片型表格：OCR 后仍需人工核对，标注 `uncertainty`。
- OCR 无法识别的页 → `status=partial`，该页标注"无法解析"，不编造内容。
- 语言混杂（中英混排）：用多语言模型，并在 `uncertainties` 说明。
