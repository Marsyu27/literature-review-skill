# literature-summary-structured-notes · 文献总结与结构化笔记 Skill

围绕真实论文整理开发的可被 Agent 调用的 Skill。核心纪律：**对得上、留得住、找得回、用得上**。

## 用途

- 把论文做成与章节对齐的结构化笔记、统一字段论文卡片、去重知识点清单，每条带锚点回链。
- 输出可检索、可比较、可继续加工，能被下一次阅读或写作直接使用。

## 文件结构

```
SKILL.md                               # 主 Skill（入口，七步流程）
scripts/build_anchor_index.py          # 文本/Markdown/PDF 生成 §/¶ 稳定锚点索引
scripts/validate_anchors.py            # 交付前锚点/quote/必填覆盖核验（纯标准库）
references/paper-card-fields.md        # 论文卡片字段字典
references/section-alignment.md        # 章节对齐与承接关系
references/knowledge-extraction.md     # 知识点提取、归一化与去重
references/source-anchoring.md         # 锚点格式与可核验性
references/output-schema.md            # result.json 契约
examples/summary-examples.md           # 标注为示例的笔记
src/reproduce.py                       # 自检入口
```

## 调用方式

加载 Skill 后，Agent 按 SKILL.md 七步流程：读输入并**立即写 result.json 骨架**→结构识别并跑 `build_anchor_index.py` 生成锚点索引→论文卡片→章节总结→知识点提取→正式锚点字段回链（只能取自索引 ID）→逐阶段就地更新 result.json→跑 `validate_anchors.py` 全绿后交付。success 下所有非空 paper_card 字段、每个 section、每个 knowledge_point 都必须覆盖；零锚点不能通过。

## 输出契约

`/app/output/result.json` 必含：`case_id`、`status`、`status_reason`、output_contract 字段、`paper_card`、顶层 `paper_card_anchors`（每项 `{field,source_anchor,quote?}`）、`sections`（每项含 `source_anchor`）、`knowledge_points`（含 `source_anchor`）、`uncertainties`。锚点不得只嵌在字符串值里。partial 仅 uncertain 条目可缺锚点并 warning，但至少一个核心有效锚点，且 `status_reason`/`uncertainties` 必须交代。

## 依赖

无强制第三方 Python 包；笔记整理由加载 Skill 的 LLM 执行，`references/` 提供规则。普通 UTF-8 文本/Markdown 建索引只用标准库。**PDF 需要可选系统依赖 Poppler 的 `pdftotext`**，脚本固定调用 `pdftotext -layout <input.pdf> -`：

```bash
python3 scripts/build_anchor_index.py --input /input/paper.pdf --out anchor_index.json
```

找不到工具或转换失败会打印清晰错误并非零退出，不会把 PDF 二进制解码异常原样抛出。可安装 Poppler，或先手动运行 `pdftotext -layout /input/paper.pdf /tmp/paper.txt` 后把文本作为 `--input`；失败时必须把 result.json 标为 unable/partial 并说明，不能声称索引已生成。

## 异常处理与限制

- 扫描件/双栏错序 → 无版面信息时按输入文本顺序组织，疑似错序/不可判读块标 uncertain 并说明；图表/公式缺失 → 保留编号，标内容不可读；原文矛盾 → 保留两处原文，标 conflict；前提缺失 → not_reported。
- 本 Skill 只做忠实抽取整理，不评价研究质量、不推断原文没有的内容。

## 最小调用示例（示意，非正式案例）

输入 `/input/case.json`：`{"case_id":"demo","output_contract":{"lang":"zh"},"pdf":"/input/paper.pdf"}`

输出结构见 `references/output-schema.md` 与 `examples/summary-examples.md`。

## 交付前质检

```bash
python3 scripts/validate_anchors.py --result /app/output/result.json \
  --index anchor_index.json --report /app/output/anchor_report.json
```

除原有 §/¶ 存在性与 quote 严格核对外，还检查必填覆盖与空锚点全集；报告含 `checked`、`valid_checked`、`warnings`、`errors`。
