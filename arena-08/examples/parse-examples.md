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
