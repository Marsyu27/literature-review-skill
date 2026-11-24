# 解析示例（标注为示例，非正式案例）

> 以下均为**示意**，用于说明输出结构与页级证据映射，不冒充正式评测案例结果。

## 示例 1：正文段落 + 页级证据映射

```json
{
  "id": "b7",
  "type": "paragraph",
  "page": 3,
  "bbox": [72, 210, 260, 320],
  "text": "We measured the transition temperature at 4.2 K under a magnetic field of 0.5 T.",
  "order": 7,
  "confidence": 1.0,
  "source": "page=3, left column, 2nd paragraph"
}
```

说明：数字 `4.2 K`、`0.5 T` 逐字保留；`source` 指明可复核位置。

## 示例 2：多栏阅读顺序

原文双栏：左栏段落 A（页 2）→ 右栏段落 B（页 2）→ 跨栏标题 C（页 2 顶部）。

正确 `order`：C（跨栏，排最前）→ A → B。若错误地把 A、B 拼成一句，则"排得对"失分。

## 示例 3：合并单元格表格（HTML）

```html
<table>
  <tr><th rowspan="2">Method</th><th colspan="2">Accuracy</th></tr>
  <tr><th>Train</th><th>Test</th></tr>
  <tr><td>Baseline</td><td>0.81</td><td>0.79</td></tr>
</table>
```

附：`id="Table 2"`、`page=5`、`caption="Classification accuracy"`。

## 示例 4：公式保真

```json
{
  "id": "(3)",
  "page": 6,
  "original": "F = −k_B T ln Z",
  "latex": "$F = -k_B T \\ln Z$",
  "confidence": 0.95,
  "note": "下标 B、对数 ln 已核对渲染图"
}
```

说明：负号保持 `−`，下标 `_B` 不写成平 `B`。

## 示例 5：不确定项如实标注

```json
{
  "uncertainties": [
    "页 8 图 3 为扫描图，OCR 未能可靠识别坐标轴刻度",
    "页 5 公式 (2) 的求积上限可能是 ∞ 或 n，无法从文字层确定"
  ]
}
```

说明：无法判断的写进 `uncertainties`，**不猜**。

## 示例 6：source_lines 与纵向 zone（机械几何）

```json
{
  "id": "b17",
  "kind": "body",
  "page": 1,
  "column": 1,
  "text": "A Centered Study of α Transport",
  "bbox": [150, 60, 450, 78],
  "source_lines": [{"text": "A Centered Study of α Transport", "bbox": [150, 60, 450, 78]}],
  "zone_id": "p1-z02",
  "order": 1
}
```

虽然旧 parse 把该标题错分到 `column:1`，refine 使用 line 跨栏几何和首个稳定双栏正文 onset，将它放进 `preamble`，不是放到右栏正文之后。column 原值保留用于审计。

```json
{
  "zone_id": "p1-z05", "kind": "full_width_float",
  "source_block_ids": ["caption-above", "table-left", "table-right"],
  "source_unit_ids": ["p1-z05-u01"]
}
```

上例 caption 在上；caption 在下时 `source_block_ids` 为 table pieces 后接 caption。左右 piece 合并的充分几何证据是双侧 table candidates 的同 y 重建行或真实跨栏 line，**不是仅因出现“Table”字样**。普通双栏 body 仍在每个 body zone 内走完左栏再走右栏。

## 示例 7：完整运行链 / 可加载 JSON 几何 fixture

```bash
python3 scripts/parse_pdf.py --pdf paper.pdf --out work/blocks.json
python3 scripts/refine_layout.py --input work/blocks.json \
  --out work/layout.refined.json --report work/conservation.json
# 语义工作只读 refined reading_units/blocks，并加 document_evidence
python3 scripts/validate_layout.py --source work/blocks.json \
  --result work/final-result.json --report work/validation.json

# 无 PDF 时，可用已有 JSON geometry / parse 底稿复现
python3 src/layout_quickstart.py --input work/blocks.json --workdir /tmp/layout-demo
# 不带 input 会生成两页合成真实 bbox 几何；默认退出后清理
python3 src/layout_quickstart.py
python3 src/reproduce.py
```

合成自检覆盖居中/错分栏标题、abstract、caption 上/下的宽表、figure float、含 `mc²/αβ/3.14` 的独立公式、第二页普通双栏，以及丢块、复制、改 unit.text、缺 part、错 evidence 等 validator 反例。临时 PPTX 与 OCR TSV self-test 不依赖真 tesseract，所有产物只在临时目录。

**这些示例只验证可核几何、顺序和文字守恒；不声称 LaTeX 推断正确、数学语义已理解或科学内容已读懂。**
