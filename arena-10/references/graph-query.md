# 图谱查询与增量更新（Graph Query & Incremental Update）

主图 `nodes`/`edges` 完成后，先给每条查询写 `query_spec`，再运行 `scripts/kg_tool.py`。自然语言 `query` 只是展示文本，不是查询语言，也不会被工具解析。禁止手写 `result_subgraph`、`evidence` 或 `execution`。

## 稳定小 DSL

每条 `queries[]` 的 `query_spec` 是对象，`op` 为下列三种之一。未知字段、错误类型、引用不存在的节点或 `edge_id` 均报错，不静默猜义。

### 1. `filter_edges`：显式过滤主图边

```json
{"op":"filter_edges","predicate":"outperforms","source_id":"primary","label_contains":"baseline"}
```

- 所有字段均可选；给定的条件取 AND，无条件的规格选择全部主图边。
- `predicate`：精确匹配边谓词。
- `source_id`：边的任一证据四元组具有该论文来源即匹配；双侧边可被其任一来源命中。
- `label_contains`：对边的**源节点或目标节点** `label` 做子串匹配；使用 Unicode `casefold()` 归一大小写，不做实体模糊合并。
- `edge_id`：可选精确边 ID 过滤；必须在主图存在。

示例等价于人读问题“primary 中哪些方法优于名称含 baseline 的对象？”。

### 2. `neighbors`：查一个实体的关联边

```json
{"op":"neighbors","entity_id":"E7","direction":"out","predicate":"uses","source_id":"secondary"}
```

- `entity_id` 与 `seed` 二选一且恰好一个，值必须是主图已有实体 ID。
- `direction`：`out`（出边）、`in`（入边）、`any`（任一端）；省略时默认 `any`。
- `predicate`、`source_id` 为可选约束，语义同 `filter_edges`；返回的是命中关联边，不是单独生成的节点列表。

### 3. `path`：确定性有向最短路径

```json
{"op":"path","start":"E7","end":"E3","max_depth":2}
```

- `start`/`end` 是主图实体 ID；只沿 `source → target` 方向遍历。
- `max_depth` 必填，整数 1–3，上限不可超过 3。
- 遍历简单路径，取全部最短路径；同长路径按“边 ID 序列、节点 ID 序列”稳定排序。
- `execution.paths` 逐项为 `{"node_ids":[...],"edge_ids":[...]}`；`result_subgraph` 是所有最短路径边的并集，按 `edge_id` 稳定去重排序。若只需要一条路径，取 `paths[0]`，但仍保留其余同长路径供审计。
- 不可达返回真实空子图和 `paths:[]`；`start == end` 是零边路径，`paths:[{"node_ids":[start],"edge_ids":[]}]`，命中边数为 0。

## 工具生成的查询记录

```json
{
  "query":"E7 经哪些边到达 E3？",
  "query_spec":{"op":"path","start":"E7","end":"E3","max_depth":2},
  "result_subgraph":[
    {"edge_id":"R1","source":"E1","predicate":"outperforms","target":"E3"},
    {"edge_id":"R12","source":"E7","predicate":"same_concept","target":"E1"}
  ],
  "evidence":["<由 R12、R1 的主图 evidence 自动继承并稳定去重>"],
  "execution":{
    "operation":"path",
    "matched_edge_ids":["R1","R12"],
    "result_count":2,
    "paths":[{"node_ids":["E7","E1","E3"],"edge_ids":["R12","R1"]}]
  },
  "uncertain_relations":["E7 与 E1 是否同一物理实例未确定"]
}
```

实际 JSON 的 `evidence` 只能是继承得到的四元组对象数组，上面字符串仅说明生成规则，不能照抄为真实证据。`result_subgraph` 按 `edge_id` 排序，因此路径遍历顺序只由 `execution.paths` 表达。`uncertain_relations` 由 Agent 保留，工具不证明其语义。

## CLI 与原子更新

在 Skill 根目录执行：

```bash
# 写到新文件，不改输入：
python3 scripts/kg_tool.py query --graph result.json --out executed.json

# 或原子覆盖原文件（同目录临时文件 + os.replace）：
python3 scripts/kg_tool.py query --graph result.json --update

# 独立重算并精确核对全部派生字段：
python3 scripts/kg_tool.py validate --graph executed.json --report report.json
```

省略 `--out` 且不用 `--update` 时默认写 `executed.json`；`--out` 与 `--update` 互斥。成功返回 0；输入/图/规格/校验错误返回 1；CLI 参数解析错误由 argparse 返回 2。

`query` 覆盖每条查询的：
- `result_subgraph`：仅 `{edge_id, source, predicate, target}`，全部来自主图；
- `evidence`：按排序后的命中边及边内证据顺序继承，按完整证据对象精确稳定去重；
- `execution`：`operation`、稳定排序的 `matched_edge_ids`、命中边数 `result_count`，path 另含 `paths`。

`validate` 先做图一致性检查，再独立重算并精确比较 `result_subgraph`、`evidence` 与整个 `execution`，报告写入 `report.json`，`valid:false` 时退出 1。改变自然语言 `query` 不影响执行语义，不被视为图内容篡改；改变 `query_spec` 后必须用 `query` 重新生成派生字段，不能手工同步。

## 图与状态校验

- `sources` 非空且 `source_id` 非空唯一；证据来源必须已登记。
- node/edge ID 非空唯一，边端点存在；节点 evidence 为单对象，边 evidence 为非空数组，四元组字段为非空字符串。
- 节点 `source_id` 可由节点字段或单对象 evidence 判定；两端属于不同论文时，边 evidence 必须同时含双方来源，`same_concept` 不例外。
- 查询记录内显式引用的每个 `edge_id`（包括过滤规格、子图和 execution）必须存在于主图。
- `success` 至少 3 条真实可执行查询；`partial` 可少于 3 条，但 `status_reason` 须含真实数量的 Arabic 数字及未完成原因。
- 工具不扩展为 JATS 全文解析，不验证 quote 是否真的是原文逐字短引；这仍是 Agent 的来源绑定责任。

## 增量更新

1. 新论文加入 → 保留既有 `entity_id` 与 `edge_id`，新节点/边使用新编号。
2. 新增：新实体/新关系 → 追加主图并绑定证据。
3. 合并：新论文实体与既有实体对齐 → 按 entity-alignment.md 合并，记录 `merge_basis`，不错误合并通用术语。
4. 冲突：保留条件不同的两条边并标 `conflict`，不擅自删改。
5. 主图变化后，重新执行 `query --update` 和 `validate`；不得沿用上批查询的旧子图或证据。

## 导出

导出 JSON 含 `nodes` + `edges` + `provenance`；完整字段见 output-schema.md。完整可执行示例见 `examples/kg-examples.md`，其中查询输出与示例边同步。
