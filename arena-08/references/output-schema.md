# result.json 完整字段与页级证据映射契约（Output Schema）

## 契约优先级

1. **`/input/case.json` 的 `output_contract` 字段 > 本文件定义的 Skill 默认字段**。
2. `output_contract` 声明的每个字段**缺失必补**（字段名与类型原样回填，不得改名或省略）。
3. 命名或类型与本文件默认字段冲突时，**以 `output_contract` 为准**，本文件字段仅作默认补充。

## 长文档 blocks 分块落盘

- `blocks` 超过约 500 块或单次写盘过大时，按页序分块落盘为 `/app/output/blocks-part-1.json` … `blocks-part-N.json`，每文件形如 `{"part": 1, "of": N, "blocks": [...]}`。
- 分块边界**按页切分，不跨页**；每块仍保留 `id/page/column/order/bbox/text/kind` 全字段。
- 此时 result.json 的 `blocks` 字段替换为 `blocks_files`（分块文件路径清单）+ 少量抽样块；`scripts/parse_pdf.py` 的原始输出 `blocks.json` 完整保留在工作目录作为审计底稿。

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

  "mode": "layout | text-only",

  "blocks": [
    {
      "id": "b3",
      "kind": "body | header | footer | table_candidate",
      "type": "heading | paragraph | table | formula | figure_caption | footnote | marginalia",
      "page": 1,
      "column": 0,
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
| `mode` | 是 | `layout`（parse_pdf.py 版面模式，有真实坐标）或 `text-only`（pdftotext 缺失的降级：bbox 一律 null、order 按文本流） |
| `document` | 是 | 整篇结构：标题、作者、摘要、章节树、参考文献 |
| `blocks` | 是 | 全量结构单元流，含 `page`/`bbox`/`order`/`confidence` —— 这是"核得回"的载体。`kind` 由 parse_pdf.py 机械产出（body/header/footer/table_candidate），`type` 由 LLM 在 blocks.json 上语义标注补充 |
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
