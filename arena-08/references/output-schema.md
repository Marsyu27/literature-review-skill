# refined / result.json 字段与守恒契约（Output Schema）

## 契约优先级

`/input/case.json/output_contract` > 本文件默认字段。合同字段不得改名、省略或改变类型；本文件补足几何与审计字段。机械产物为 `layout.refined.json`，语义产物为 `final-result.json`，二者使用同一 source lineage。

## 顶层结构（核心字段）

```json
{
  "case_id": "<语义结果回填；机械 blocks/refined 可无>",
  "status": "success | partial | unable | in_progress",
  "status_reason": "<partial/unable 必填>",
  "pages": 2,
  "mode": "layout | text-only",
  "columns": "single | double | mixed",
  "column_boundary": 300.0,
  "page_layouts": [
    {"page": 1, "columns": "double", "column_boundary": 300.0,
     "n_cols": 2, "order": "left-to-right", "width": 600, "height": 800}
  ],
  "page_zones": [
    {"zone_id": "p1-z03", "page": 1, "kind": "body_columns",
     "bbox": [60, 170, 560, 218], "source_block_ids": ["b4", "b9"],
     "source_unit_ids": ["p1-z03-u01", "p1-z03-u02"], "order": 2}
  ],
  "reading_units": [
    {"unit_id": "p1-z03-u01", "page": 1, "zone_id": "p1-z03",
     "source_block_ids": ["b4"], "source_unit_ids": ["p1-z03-u01"],
     "text": "由 source_parts 按序生成", "text_sha256": "<unit.text SHA-256>",
     "bbox": [60, 170, 275, 218],
     "source_parts": [
       {"source_block_id": "b4", "source_unit_id": "p1-z03-u01",
        "part_index": 0, "part_count": 1, "text": "原始整块文字",
        "hash": "<part.text SHA-256>", "bbox": [60, 170, 275, 218]}
     ]}
  ],
  "blocks": [],
  "tables": [], "formulas": [], "figures": [],
  "uncertainties": [], "gaps": [], "unmapped_block_ids": [],
  "conservation_report": {"source_block_count": 23, "result_block_count": 23,
                          "source_normalized_text_sha256": "<SHA>",
                          "result_normalized_text_sha256": "<相同 SHA>"},
  "tool_commands": []
}
```

### page_zones

- `zone_id/page/kind/bbox/source_block_ids/source_unit_ids/order` 必填。kind 常见为 `preamble/abstract/body_columns/body_single/full_width/full_width_float/header/footer`。
- `source_block_ids` 的阅读顺序必须与最终 blocks 在该 zone 的 order 一致；每块只出现在一个 zone。zone.bbox 是成员块 bbox 的并集。
- header/footer 不丢失也不混入正文，分别成 zone 且可回链 reading units。

### blocks

每个原块保留 parse 的 `id/page/kind/column/text/bbox/source_lines`，重排只改变 `order`，并增加：

```json
{
  "id": "b4", "kind": "body | header | footer | table_candidate",
  "type": "<可选语义类型>", "page": 1, "column": 0,
  "bbox": [60, 170, 275, 218], "text": "文字逐字保留",
  "source_lines": [{"text": "原始行", "bbox": [60, 170, 275, 182]}],
  "order": 4, "zone_id": "p1-z03", "source_unit_ids": ["p1-z03-u01"]
}
```

原始 id/text/kind/page/column/source_lines 不得变；普通语义类型、confidence 等可附加。当前 refine 一个原块只有一个完整 part，不 secretly split。表格 `tables[].block_id` 指向 blocks 正文；原 rows/cells/page 不变，cells bbox 与该原块几何可解释。新 HTML/Markdown 不覆盖原证据。

### reading_units 与 source_parts

- unit 必须含 `unit_id/page/zone_id/source_block_ids/source_unit_ids/text/bbox/source_parts`；`source_unit_ids` 当前恰为 `[unit_id]`，每个 part.source_unit_id 也等于所属 unit_id。
- `unit.source_block_ids` 与 parts 的 block IDs 顺序完全相同；一个源块在当前实现恰好映射一次。unit.bbox 为 parts bbox 并集，unit.text 是 parts.text 以换行连接的结果。允许的正则空白归一不许可删字、换词、改数学符号。
- validator 核 part.hash、unit.text_sha256（若给）、unit 文本摘要、全 source_parts union、单位上下文及全局顺序。沿用旧 source_parts 而修改 unit.text、交换不同上下文 parts、少一条 part 都失败。
- 公式原块独立 unit，不能把不同原公式的 original/LaTeX 拼成一个新公式。

## blocks_files 与内嵌 layout

- 长文档可按页写入 `blocks-part-N.json`，每项形如 `{"part":1,"of":N,"blocks":[...]}`；根结果使用 `blocks_files:[相对或绝对路径]`。
- 相对路径以声明它的 source/result JSON 所在目录解析。source 侧和 result 侧均可使用；validator 会收集 inline + 所有 files，不按列表长度猜完整。
- 必须保证源 ID 在最终展开后**恰好一次**。不要同时把同一批块作为“抽样” inline 又在 files 中提供，否则属于重复 ID；最稳妥是 files 模式下 `blocks:[]`。
- final-result 可把 page_zones/reading_units 放在 `layout`、`refined_layout` 或 `layout_refined` 对象中。若根与内嵌同时有 blocks，两者 ID 覆盖、text 和 zone_id 必须一致，不能悄悄分叉或漏块。
- 表格 cell、formula、header/footer 同样在守恒范围内；只比较正文字数或 ID 数量不构成通过。

## title / abstract / caption / formula 证据

`document_evidence` 可选；但 `status=success` 且声称相应字段已解析时强制。格式：

```json
{
  "document_evidence": {
    "title": {"block_ids": ["b1"], "source_unit_ids": ["p1-z02-u01"],
              "text": "与所回链原块规范化文本相同"},
    "abstract": {"block_ids": ["b3"], "text": "Abstract ..."},
    "captions": [{"id": "Table 1", "block_id": "b20", "text": "Table 1: ..."}],
    "formulas": [{"id": "(1)", "block_id": "b30", "original": "E = mc² + αβ"}]
  }
}
```

- title/abstract 的目标字符串及 evidence.text 必须等于所回链原块的规范化连接文本；所声明 source_unit IDs 必须真包含对应 part。
- caption 原文必须存在于回链块；有 id 时还要匹配结果 table/figure，不能借其它 figure 的同样式块。
- formula.original 必须存在于回链块；latex 可另给但不替代 original。result formula/table 的 block_id 本身也必须存在。
- success 中每个非空 document.title/abstract、每个已解析 caption/formula 都需映射。缺一项或指错原块均为 error，不能仅补页码。

## 状态、gaps 与 validator 的退出码

```bash
python scripts/validate_layout.py --source blocks.json \
  --result layout.refined.json --report validation.json
# 或 --result final-result.json
```

- `success`：完整覆盖且无 gaps/unmapped；成功声明的语义字段都有 evidence。validation report `success=true` 只表示该守恒契约通过。
- `partial`：必须 status_reason 和明确 uncertainties/gaps。一般 OCR 缺口可只给 gap；如果 reading_units 未映射某源块，则该 ID 必须同时精确出现在根 `unmapped_block_ids` 与某 `gaps[].block_id`（或 `block_ids`）。zone/final blocks 中的原块本身仍不得丢。
- partial 若满足上述披露，validator 可退出 0，但报告为 `validation_status=partial`、`success=false`、`warnings` 非空。少报一个 unmapped ID 就退出 1。
- `unable` / 无真实 bbox 不得宣称几何 success。text-only 不运行 refine。

始终硬失败（退出 1）：源块从最终 blocks 丢失/复制、text 非空白变化、page/kind/column/source_lines 被改、未知 ID、unit.text 与 parts 不符、part 缺字段/hash/bbox 错、part union 未披露缺失或重复、zone page/order/bbox 上下文错位、原 table rows/cells/page 改变或 table/formula 回链不存在、success evidence 缺失/指错。

## conservation_report / validation report

两阶段报告都纳入 source/result block 数、reading unit/zone 数、字符数、规范化文本 SHA、missing/duplicate/unmapped 与 warnings。独立 validator 额外写：

- `source_word_count/result_word_count`；
- 按源 ID 序列计算的 `source_normalized_text_sha256/result_normalized_text_sha256`（阅读重排不应改变它们）；
- `reading_units_normalized_text_sha256` 与 `source_parts_normalized_text_sha256`；
- `exact_text_changed_block_ids`、errors/warnings、`validation_status/exit_code`。

只让 ID 数量相等不够；源文字删除、旧 parts + 新 unit.text、parts 部分缺失、context 对调、错误 document_evidence 都必须失败。通过也不表示数学语义或科学内容已读懂。

## 诚实原则

数字、单位、引用、公式原文逐字保留；没有把把握就标 uncertainty/gap。每条结构化结果可回到 page/bbox/block/unit/part。可由 `src/layout_quickstart.py --input blocks.json` 在临时或指定工作目录验证同一 CLI 链。
