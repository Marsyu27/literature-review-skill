# result.json 完整字段与页级证据映射契约（Output Schema）

## 硬性要求

1. `case_id` 原样回填，`status` + `status_reason` 必填。
2. **output_contract**：`/input/case.json` 里 `output_contract` 声明的每个字段都必须出现在 result.json，字段名与类型一致，不得遗漏或改名。
3. 结构化解析结果与证据映射：正文每个单元、每张表格、每个公式、每个图注都能指回页码/区块。

## 字段定义

```json
{
  "case_id": "<回填>",
  "status": "success | partial | unable",
  "status_reason": "<unable/partial 时必填；success 可写空字符串>",

  "document": {
    "title": "…",
    "authors": "…",
    "affiliations": "…",
    "abstract": "…",
    "sections": [
      {"level": 1, "number": "1", "title": "Introduction", "page": 1, "blocks": ["b3","b4"]}
    ],
    "references": [
      {"id": "[1]", "text": "…", "page": 12}
    ]
  },

  "blocks": [
    {
      "id": "b3",
      "type": "heading | paragraph | table | formula | figure_caption | footnote | header | footer | marginalia",
      "page": 1,
      "bbox": [x0, y0, x1, y1],
      "text": "…",
      "order": 3,
      "confidence": 1.0,
      "source": "page=1, left column"
    }
  ],

  "tables": [
    {"id": "Table 1", "page": 4, "caption": "…", "html": "<table>…</table>", "note": "跨页续表，起始页 4"}
  ],

  "formulas": [
    {"id": "(3)", "page": 5, "original": "…", "latex": "$…$", "confidence": 0.9}
  ],

  "figures": [
    {"id": "Fig. 2", "page": 6, "caption": "…", "bbox": [x0,y0,x1,y1]}
  ],

  "headers_footers": [
    {"type": "header", "text": "Journal Name", "pages": [1,2,3]}
  ],

  "uncertainties": [
    "页 4 表格为图片，OCR 低置信度",
    "页 7 公式 (8) 上下标无法确定"
  ],

  "tool_commands": [
    "pdftotext -layout paper.pdf out.txt",
    "pdftoppm -png -r 150 paper.pdf page"
  ]
}
```

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` / `status` / `status_reason` | 是 | 运行状态三件套 |
| `document` | 是 | 整篇结构：标题、作者、摘要、章节树、参考文献 |
| `blocks` | 是 | 全量结构单元流，含 `page`/`bbox`/`order`/`confidence` —— 这是"核得回"的载体 |
| `tables` / `formulas` / `figures` | 按需 | 从 blocks 中抽取的结构化子集 |
| `headers_footers` | 是 | 页眉页脚/水印，单独存放不混入正文 |
| `uncertainties` | 是 | 无法判断/需人工确认项；无则空数组 |
| `tool_commands` | 推荐 | 实际执行的工具命令，用于复现与审计 |
| output_contract 字段 | 是 | 按 case.json 原样回填 |

## 状态与降级

- `success`：所有 output_contract 字段有值，关键结构可复核。
- `partial`：部分完成（如扫描页 OCR 失败、个别公式无法还原），`uncertainties` 必须说明缺口。
- `unable`：无法解析（加密、文件损坏、无可用工具），写明原因，不编造结果。

## 诚实原则

- 数字、单位、公式、引用编号**逐字保留**；读不出就标不确定，不补造。
- 每条结果都说明"从哪来"（page/bbox/tool），第三方可复核。
