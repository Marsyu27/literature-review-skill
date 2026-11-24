# literature-summary-structured-notes · 文献总结与结构化笔记 Skill

围绕真实论文整理开发的可被 Agent 调用的 Skill。核心纪律：**对得上、留得住、找得回、用得上**。

## 用途

- 把论文做成与章节对齐的结构化笔记、统一字段论文卡片、去重知识点清单，每条带锚点回链。
- 输出可检索、可比较、可继续加工，能被下一次阅读或写作直接使用。

## 文件结构

```
SKILL.md                               # 主 Skill（入口，六步流程）
references/paper-card-fields.md        # 论文卡片字段字典
references/section-alignment.md        # 章节对齐与承接关系
references/knowledge-extraction.md     # 知识点提取、归一化与去重
references/source-anchoring.md         # 锚点格式与可核验性
references/output-schema.md            # result.json 契约
examples/summary-examples.md           # 标注为示例的笔记
src/reproduce.py                       # 自检入口
```

## 调用方式

加载 Skill 后，Agent 按 SKILL.md 六步流程：读输入→结构识别→论文卡片→章节总结→知识点提取→锚点回链→输出 result.json。

## 输出契约

`/app/output/result.json` 必含：`case_id`、`status`、`status_reason`、output_contract 字段、`paper_card`、`sections`、`knowledge_points`（含 `source_anchor`）、`uncertainties`。

## 依赖

无强制第三方包；笔记整理由加载 Skill 的 LLM 执行，`references/` 提供规则。

## 异常处理与限制

- 扫描件/双栏错序 → 修正阅读顺序，不可靠则标 uncertain；图表/公式缺失 → 保留编号，标内容不可读；原文矛盾 → 保留两处原文，标 conflict；前提缺失 → not_reported。
- 本 Skill 只做忠实抽取整理，不评价研究质量、不推断原文没有的内容。

## 最小调用示例（示意，非正式案例）

输入 `/input/case.json`：`{"case_id":"demo","output_contract":{"lang":"zh"},"pdf":"/input/paper.pdf"}`

输出结构见 `references/output-schema.md` 与 `examples/summary-examples.md`。
