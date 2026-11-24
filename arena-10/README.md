# literature-knowledge-graph · 文献知识图谱构建 Skill

围绕真实论文开发的可被 Agent 调用的 Skill。核心纪律：**抽得准、连得对、对得齐、查得到、回得去**。查询不是自然语言模拟：每条 `query_spec` 都由同一个标准库工具在主图上执行，子图和证据不可手写。

## 用途

- 从一篇或多篇论文抽取真实实体与关系，对齐别名、绑定证据、导出 nodes + edges + provenance。
- 用稳定小 DSL 执行 `filter_edges`、`neighbors`、有向最短 `path`，支持真实空结果。
- 校验图一致性、跨篇双侧证据、查询派生字段和成功/部分完成状态；不引入图数据库。

## 文件结构

```
SKILL.md                            # 主 Skill（第 0–7 步强制流程）
scripts/kg_tool.py                  # query / validate，纯 Python 标准库
references/entity-recognition.md    # 实体识别与自述/转述区分
references/entity-alignment.md      # 别名归一与同名冲突
references/relation-extraction.md   # 关系抽取与受控词表
references/source-binding.md        # 来源绑定与证据强度
references/graph-query.md           # 完整 DSL、CLI 与增量更新
references/output-schema.md         # result.json / 图谱导出契约
examples/kg-examples.md             # 两篇 JATS 的同步可执行示例
src/reproduce.py                    # tempfile CLI 正反回归，无提交残留
```

## 调用方式

Agent 按 SKILL.md 执行：读输入与 output_contract → 登记 manifest/两篇 JATS 来源 → 实体识别与对齐 → 关系抽取与来源绑定 → **先完成主图 nodes/edges，再运行 query，最后 validate**。自然语言 `query` 只作展示；禁止模型手写查询子图、查询证据或 `execution`。

在 Skill 根目录运行：

```bash
python3 scripts/kg_tool.py query --graph /app/output/result.json --update
python3 scripts/kg_tool.py validate --graph /app/output/result.json --report /app/output/report.json
```

也可保留原文件：`query --graph result.json --out executed.json`。`--update` 使用同目录临时文件和 `os.replace` 原子覆盖。成功退出 0；图、规格或结果校验失败退出 1；参数语法错误退出 2。

最小 DSL：

```json
{"op":"filter_edges","predicate":"outperforms","source_id":"primary","label_contains":"baseline"}
{"op":"neighbors","entity_id":"E7","direction":"out","predicate":"uses"}
{"op":"path","start":"E7","end":"E3","max_depth":2}
```

工具覆盖写入每条查询的 `result_subgraph`、`evidence`、`execution.matched_edge_ids` 与 `result_count`。子图每项只有 `edge_id/source/predicate/target`；证据按命中主图边继承并稳定去重。详细语义见 `references/graph-query.md`。

## 输出契约

最终结果写 `/app/output/result.json`，必含：`case_id`、`status`、`status_reason`、全部 output_contract 动态字段、`sources[]`、`nodes[]`、`edges[]`、`queries[]`、`uncertainties`。每条查询必须有 `query_spec`。节点 evidence 为单个四元组对象，边与查询 evidence 为数组，跨篇边必须有双方原文证据。

`success` 至少 3 条真实执行并校验通过的查询；`partial` 可少于 3 条，但 `status_reason` 要如实写出实际数量和未完成原因。空查询结果可以成功，不能为凑数伪造边。

## 依赖与自检

Python 3，**无强制第三方包**；`kg_tool.py` 仅用标准库，抽取仍由加载 Skill 的 LLM 依规则执行。

```bash
python3 src/reproduce.py
```

自检通过真实子进程调用 CLI：两个来源、7 条边、filter/neighbors/path/empty 四查询；核对输出确为主图子集，并覆盖原子更新、最短路径稳定排序及要求的全部正反用例。所有测试文件位于临时目录，退出时自动清理。

## 最小调用示例（示意，非正式案例）

输入 `/input/case.json`：

```json
{
  "case_id":"demo",
  "output_contract":{"format":"json"},
  "corpus_manifest":"/input/corpus-manifest.json",
  "materials":[
    "/input/primary-material.json",
    "/input/secondary-material.json"
  ]
}
```

`corpus-manifest.json` 分别声明 primary/secondary 的 DOI、作者、来源哈希与许可证；`primary-material.json` 和 `secondary-material.json` 是两篇独立论文的 JATS 正文，各自 paragraph ID 用作锚点。`material.json` 若提供仅作正文索引，不能把同一论文的不同格式冒充两个来源。读取这两篇正文与 manifest 建主图后，为至少三个问题写规格，再执行上述 query/validate 命令。完整节点、边及与边真实对应的执行输出见 `examples/kg-examples.md`，字段契约见 `references/output-schema.md`。

## 异常处理与限制

- 无文本层 → OCR，不可靠则 uncertain；关系无证据 → 不建边或标 weak；同名冲突 → 分节点 + homonym；增量冲突 → 保留两条边 + conflict。
- `uncertain_relations` 可保留 Agent 判断，但工具不证明其语义；工具也不做 JATS 全文 quote 对齐，只校验 JSON 图结构、来源登记和确定性查询结果。
- 本 Skill 不凭常识补实体、不凭猜测合并或连边；查询不可达/零命中时返回空子图、空证据与空 matched IDs。
