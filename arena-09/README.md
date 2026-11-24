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
scripts/validate_nanopub.py             # 导出前记录质检 + 最终 JSON-LD 严格质检（纯标准库）
src/reproduce.py                        # 自检入口
```

## 调用方式

加载 Skill 后，Agent 按 SKILL.md 六步流程：读输入→断言拆解→证据绑定→来源元数据→**导出前记录质检**→**JSON-LD 导出→最终严格质检**。导出前使用 `--records-only`，最终严格质检不带该参数，两步不能互相替代。

## 输出契约

`/app/output/result.json` 必含：`case_id`、`status`、`status_reason`、output_contract 字段、`pubinfo`、`nanopublications[]`（assertion + evidence + provenance + status + basis）、`uncertainties`。

## 依赖

无强制第三方包；抽取由加载 Skill 的 LLM 执行，`references/` 提供规则与受控词表。

## 质检

分两步机检，不能只做其中一步：

1. 导出前：`python scripts/validate_nanopub.py --records-only /app/output/result.json`，校验谓词、assertion/evidence/provenance 与 evidence 状态规则。仅 `status=unverified` 的空 evidence 可 warning 放行，其他状态空 evidence 为 error。
2. JSON-LD 导出后：`python scripts/validate_nanopub.py /app/output/result.json [extra.jsonld ...]` 做最终严格质检，要求至少一个 JSON-LD，并逐文档检查 `@context`、assertion/evidence/provenance/pubinfo 四类 named graph 和 URN 顶层 `@id` 形态。完全没有 JSON-LD 为 error/退出码 1，绝不打印“@context 校验完成”。

两步退出码非 0 时均须按错误清单修正。partial 若有输出也必须满足输出契约，并在 `status_reason`/`uncertainties` 如实列出未完成范围与 JSON-LD 等缺口；warning 不能替代最终严格质检。

## 异常处理与限制

- 无文本层 → OCR，不可靠则 uncertain；证据不足 → unverified；原文矛盾 → conflict；关系方向不明 → uncertain；限定词缺失 → 补回或 uncertain。
- 本 Skill 只做忠实拆解对齐，不推断原文没有的断言。

## 最小调用示例（示意，非正式案例）

输入 `/input/case.json`：`{"case_id":"demo","output_contract":{"format":"json-ld"},"pdf":"/input/paper.pdf"}`

输出结构见 `references/output-schema.md` 与 `examples/nanopub-examples.md`。
