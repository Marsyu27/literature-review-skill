# nanopublication-extraction · Nanopublication 抽取 Skill

围绕真实论文结论开发的可被 Agent 调用的 Skill。核心纪律：**拆得细、对得上、追得回、读得懂**。

## 用途

- 把论文段落拆成原子断言（subject-predicate-object），每条绑定最小充分证据 + 原文位置 + 来源元数据。
- 导出可机器读取的 JSON-LD/RDF 结构，下游程序可直接解析。

## 文件结构

```
SKILL.md                                # 主 Skill（入口，六步流程）
references/assertion-decomposition.md   # 断言拆解规则
references/relation-vocabulary.md       # 关系类型受控词表
references/evidence-binding.md          # 证据绑定（最小充分 + 直接/间接）
references/provenance-metadata.md       # 来源元数据与溯源链
references/quality-check.md             # 质量检查清单
references/output-schema.md             # result.json / JSON-LD 契约（含 @context 约定）
examples/nanopub-examples.md            # 20 条标注为示例的断言
scripts/validate_nanopub.py             # 结果机检：词表/字段/@context 校验（纯标准库）
src/reproduce.py                        # 自检入口
```

## 调用方式

加载 Skill 后，Agent 按 SKILL.md 六步流程：读输入→断言拆解→证据绑定→来源元数据→质量检查→JSON-LD 导出。

## 输出契约

`/app/output/result.json` 必含：`case_id`、`status`、`status_reason`、output_contract 字段、`pubinfo`、`nanopublications[]`（assertion + evidence + provenance + status + basis）、`uncertainties`。

## 依赖

无强制第三方包；抽取由加载 Skill 的 LLM 执行，`references/` 提供规则与受控词表。

## 质检

导出前运行 `python scripts/validate_nanopub.py /app/output/result.json`：校验谓词在受控词表内、每条记录 assertion/evidence/provenance 齐全且 evidence 非空、JSON-LD 输出含 `@context`；退出码非 0 时按错误清单修正。

## 异常处理与限制

- 无文本层 → OCR，不可靠则 uncertain；证据不足 → unverified；原文矛盾 → conflict；关系方向不明 → uncertain；限定词缺失 → 补回或 uncertain。
- 本 Skill 只做忠实拆解对齐，不推断原文没有的断言。

## 最小调用示例（示意，非正式案例）

输入 `/input/case.json`：`{"case_id":"demo","output_contract":{"format":"json-ld"},"pdf":"/input/paper.pdf"}`

输出结构见 `references/output-schema.md` 与 `examples/nanopub-examples.md`。
