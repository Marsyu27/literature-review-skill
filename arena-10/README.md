# literature-knowledge-graph · 文献知识图谱构建 Skill

围绕真实论文开发的可被 Agent 调用的 Skill。核心纪律：**抽得准、连得对、对得齐、查得到、回得去**。

## 用途

- 从论文抽取真实实体与关系，对齐别名、绑定证据、支持查询、可增量更新，导出可读图谱。
- 输出 nodes + edges + provenance，下游程序可直接解析。

## 文件结构

```
SKILL.md                            # 主 Skill（入口，六步流程）
references/entity-recognition.md    # 实体识别与自述/转述区分
references/entity-alignment.md      # 别名归一与同名冲突
references/relation-extraction.md   # 关系抽取与受控词表
references/source-binding.md        # 来源绑定与证据强度
references/graph-query.md           # 图谱查询与增量更新
references/output-schema.md         # result.json / 图谱导出契约
examples/kg-examples.md             # 标注为示例的图谱片段
src/reproduce.py                    # 自检入口
```

## 调用方式

加载 Skill 后，Agent 按 SKILL.md 六步流程：读输入→实体识别→实体对齐→关系抽取→来源绑定→查询与导出（+增量更新）。

## 输出契约

结果明确写 `/app/output/result.json`，必含：`case_id`、`status`、`status_reason`、全部 output_contract 动态字段、`sources[]`、`nodes[]`、`edges[]`、`queries[]`（≥3）、`uncertainties`。节点 evidence 可为单个四元组对象；边与查询 evidence 均为数组，跨篇 same_concept 必须有双侧原文证据。

## 依赖

无强制第三方包；抽取由加载 Skill 的 LLM 执行，`references/` 提供规则与受控词表。

## 异常处理与限制

- 无文本层 → OCR，不可靠则 uncertain；关系无证据 → 不建边或标 weak；同名冲突 → 分节点 + homonym；别名待定 → uncertain；增量冲突 → 保留两条边 + conflict。
- 本 Skill 只做忠实抽取，不凭常识补实体、不凭猜测合并或连边。

## 最小调用示例（示意，非正式案例）

输入 `/input/case.json`：`{"case_id":"demo","output_contract":{"format":"json"},"pdf":"/input/paper.pdf"}`

输出结构见 `references/output-schema.md` 与 `examples/kg-examples.md`。
