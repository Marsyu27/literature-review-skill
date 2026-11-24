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

加载 Skill 后，Agent 按 SKILL.md 七步流程：读输入并**立即写 result.json 骨架**→结构识别并跑 `build_anchor_index.py` 生成锚点索引→论文卡片→章节总结→知识点提取→正式锚点字段回链（只能取自索引 ID）→逐阶段就地更新 result.json→跑 `validate_anchors.py` 全绿后交付。result.sections 与索引完整 §ID 集双向对齐，preamble 也计入；success 不漏、不多、不用占位，正常 section 锚点含自身 ID，所有非空 paper_card 字段与正常 knowledge_point 均覆盖；零锚点不能通过。partial 的每个未完成索引章节必须保留 `uncertain + reason` 占位，不能静默删除。

## 输出契约

`/app/output/result.json` 必含：`case_id`、`status`、`status_reason`、output_contract 字段、`paper_card`、顶层 `paper_card_anchors`（每项 `{field,source_anchor,quote?}`）、`sections`、`knowledge_points`、`uncertainties`。正常 section/knowledge_point 含有效 `source_anchor`，锚点不得只嵌在字符串值里。partial 仅 uncertain 条目可缺锚点并 warning，但至少一个核心有效锚点，且 `status_reason`/`uncertainties` 必须交代；section 占位为 `{"id":"§n","status":"uncertain","reason":"..."}`。不得为全集覆盖编造空泛摘要，无法提炼时只可据原文标“未形成独立论点”并降为 partial。

## 标题识别与不确定性

除 Markdown、阿拉伯编号和全大写标题外，索引器支持 `III.A Methods`、`IV. Experimental Results`、`A. Methods`。对 Introduction/Methods/Results/Discussion/Conclusion 等常见无编号短 Title Case 结构标题，只有满足行长、词数、无句末标点及后续正文约束才采纳；普通长正文不会因编号前缀被切节。顶层索引 `warnings` 记录 `heading_review`（启发式采纳待复核）与 `heading_rejected`（疑似标题未采纳），使用锚点前须回看原文。

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

除 §/¶ 存在性与 quote 严格核对外，还检查必填覆盖、section 自身锚点、章节双向全集与空锚点全集；报告含 `index_sections`、`result_sections`、`missing_sections`、`extra_sections`，以及 `checked`、`valid_checked`、`warnings`、`errors`。

## 实际正反回归

```bash
python3 src/reproduce.py
```

自检仅使用 Python 标准库与 `tempfile`：实际调用索引脚本处理含 preamble、阿拉伯/罗马/字母编号和无编号标题的合成论文，再调用校验脚本测试全覆盖成功，以及漏节、伪造 ¶ID、改 quote、漏 paper_card 锚点、partial 静默漏节、success 占位、额外章节、错误自身锚点等失败；partial 逐节 uncertain 占位且存在其他有效核心锚点时 warning 通过。逐项打印实际/期望退出码；全部临时输入、JSON、报告和 manifest 在退出时清理，不污染提交目录。
