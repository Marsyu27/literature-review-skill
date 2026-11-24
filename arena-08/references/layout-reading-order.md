# 纵向 zone 与多栏阅读顺序（Layout & Reading Order）

## 两层机械流程

1. `scripts/parse_pdf.py` 用真实 `pdftotext -bbox-layout` 词框做逐页栏判定和**原始初排**。保留现有逐页 xMin 双峰+真实栏间空带、页眉页脚判定与表格候选；每个块附 `source_lines=[{text,bbox}]`。`id/text/kind/page/column` 是守恒记录，原表格 rows/cells 不改。此层的整左栏→整右栏不保证通栏标题/浮动体顺序。
2. `scripts/refine_layout.py` 只消费原 JSON/source_lines，按页建立纵向 `page_zones` 和可审计 `reading_units`，重排 order。它不靠 translated text、语义标签或 LLM 手算 bbox。
3. `scripts/validate_layout.py` 再从磁盘核源与结果。zone 几何通过不是数学/科学语义理解证明。

## 栏界与几何参数

- 每页只使用本页 `page_layouts.column_boundary`；单栏不猜栏界，缺失双页配置报错。
- 对应该页 source_lines 计算：中位线高 `H`；优先同一原块内相邻正行距中位数 `P`（缺失时 `1.4H`，并至少为 H）。
- 同 y 行容差 `max(0.20P, 0.25H)`；跨栏水平容差 `0.75H`；连续 cross-line 合并间隙 `1.25P`；caption 向表格扩展最大间隙 `2.0P`。因此都随正常纵距/线高（也是词框纵尺寸）缩放，不假定某个 PDF 的固定像素。
- “真实跨栏”是 line bbox 同时越过 `boundary±0.75H`。source_lines 缺失、line 与 block 文本不守恒或 bbox 无效时停止，不从字符串臆造坐标。

## 页首 preamble / abstract

只在第 1 页找“第一次稳定双栏正文”：普通 body（非 table/caption/abstract/formula 样式）左右两侧有同 y 行，且下一对同 y 行在不超过 `2.5P` 的正常节奏内出现。其 y 为稳定 onset。

- onset 前非表格、非题注块不论原 column 是 0/1，均作前置 zone；因此居中的短标题即使被初排错分到右栏，也不会被整页 split 留到右栏正文之后。
- 若前置块有 Abstract/Summary/摘要标识，之前为 `preamble`，标识起至 onset 为 `abstract`；否则只输出保守 `preamble`。标识不负责几何扩展。
- 一个源块跨 onset 时不拆字，整块保守留前置 zone 并 warning。找不到重复的 stable rows 时不强行把整页声明成通栏，保留普通栏流并 warning。

## 页中/页下 full-width floats

可靠 seed 只有两类：

1. source line 自身真实越过栏界；caption 跨栏、figure panel 跨栏或其他跨栏 line 都走此几何证据。
2. 左右 `table_candidate`/原 tables block 的两侧行至少两行同 y 对齐，才重建为 split-wide-table 证据。**仅普通正文左右同 y 不算通栏**，否则会把双栏正文拼成双线。

合并与扩展：

- 交集/同源块 seeds 合并；邻近连续真实 cross lines 在 `1.25P` 内合并。
- caption 在表格上方或下方均可：caption/table seed 在 `2P` 内向邻近 table-cell/table_candidate 块扩展。两侧 split L/R piece 进入同一 `full_width_float` zone，按 y、x 排块，caption 自然位于 cells 前或后。
- 可向表格 cells 扩展，不向相邻普通正文扩展。样式词 `Table/Figure/Fig./表/图` 只辅助扩展：单栏里仅有 caption 字样、只有单侧候选、普通表格候选无双侧证据时都保持 `body_columns` 并写 warnings。
- 无 caption 的可靠跨栏 line 可标 `full_width`，不伪称 figure/table。多个独立 floats 间隙大于合并边界时不强行归并。

## zone 内阅读顺序

- `preamble/abstract/full_width/full_width_float/body_single/header/footer`：按 y，再 x，再以源索引稳定排序。
- `body_columns`：先按真实 line bbox 为每块归侧；**该 zone 完整左栏 y 流后，才进入完整右栏 y 流**。下一个纵向 zone 再重新执行同样规则。
- 跨 zones 按 bbox y。页眉页脚各自成 zone，保留在 blocks/reading_units 而不混入正文流。
- 不拆原块文字：每个 block 只属一个 zone、一个完整 source_part。块跨边界时选择保守归属并披露，而不是改 text 让几何“好看”。

## reading_units 与来源片段

每个 preamble/abstract/float/header/footer zone 可形成一个有序 unit；body_columns 中每栏流分别形成 units。若同栏相邻多个非公式块合并，unit.text 由这些 parts 以换行连接。公式块始终独立，避免将不同原公式的原文/LaTeX 拼成一个新公式。

每个 part 至少含：

```json
{"source_block_id":"b7", "source_unit_id":"p1-z04-u01",
 "part_index":0, "part_count":1, "text":"原始整块文字",
 "hash":"<text 的 UTF-8 SHA-256>", "bbox":[0,0,0,0]}
```

`unit.text` 必须由当次 parts 有序重建；validator 同时核 part hash、原块文本/bbox、unit/page/zone/source_block_ids 和全局 order。只改 unit.text 而沿用旧 references/source_parts 会失败。

## 降级和禁止事项

- 模糊通栏、栏界缺证据、OCR 未读出均只对可核几何处理，并列 uncertainties/gaps。
- 禁止丢弃 header/footer 证据，禁止把同 y 左右正文拼成一行，禁止美化/改写数字、希腊字母、公式或表格 cells。
- 跨页段落可在语义层关联，但不得复制/删除源块。最终始终运行 validate_layout.py。
