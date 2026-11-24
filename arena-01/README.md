# scientific-literature-translation · 文献翻译 Skill

围绕真实科研论文翻译难点开发的、可被 Agent 调用的 Skill。核心纪律：**术语稳、段落全、关系准、可核验**。

## 用途

- 科研文献中英互译，产出段落级双语对照 + 冻结术语表 + 页级/段级证据映射。
- 重点改善术语一致性、长文分段翻译、双语对照、译文核验（数字/单位/公式/引用/否定/量词/因果守恒）。

## 文件结构

```
SKILL.md                              # 主 Skill（入口，六步流程）
scripts/check_terminology.py          # 术语回填/漂移/frozen 机械核验（纯标准库，有 error 退出码 1）
scripts/check_conservation.py         # 数字/引用/带单位量守恒逐段核验（纯标准库，missing 退出码 1）
references/terminology-lock.md        # 术语抽取、锁定与冲突处理（含 terminology.json 机读格式）
references/hedge-strength.md          # 限定词强度分级与守恒（关系准核心）
references/bilingual-alignment.md     # 段落级双语对照与段号约定
references/translation-verification.md# 译文核验清单
references/output-schema.md           # result.json 契约（含契约优先级）
examples/translation-examples.md      # 标注为示例的对照
src/reproduce.py                      # 自检入口
```

## 调用方式

加载 Skill 后，Agent 按 SKILL.md 六步流程：读输入→术语抽取冻结→长文分段→逐段双语对照→关系守恒检查→译文核验→输出 result.json。

译文核验为"机械检查先行"：先跑 `scripts/check_terminology.py` 与 `scripts/check_conservation.py`，两脚本全绿（退出码 0）才允许交付；红则修复后重跑。

## 输出契约

`/app/output/result.json` 必含：`case_id`、`status`、`status_reason`、output_contract 字段、`terminology`、`segments`（段号+原文+译文+依据+状态）、`uncertainties`。

## 依赖

无强制第三方包：`scripts/` 两个核验脚本仅用 Python 标准库；翻译由加载 Skill 的 LLM 执行，`references/` 提供规则。

## 异常处理与限制

- 残缺/模糊材料 → 标 uncertain/unable，不猜译；公式/数字/引用逐字保留；术语冲突 → 多数派为准并提示人工确认。
- 本 Skill 只做忠实翻译，不做研究结论判断。

## 最小调用示例（示意，非正式案例）

输入 `/input/case.json`：`{"case_id":"demo","output_contract":{"lang":"zh"},"pdf":"/input/paper.pdf"}`

输出结构见 `references/output-schema.md` 与 `examples/translation-examples.md`。
