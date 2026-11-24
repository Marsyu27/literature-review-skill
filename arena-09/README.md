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
scripts/export_nanopub.py               # records → canonical JSON-LD 唯一导出器（纯标准库）
scripts/validate_nanopub.py             # records-only + 最终 record↔JSON-LD 严格等性质检
src/reproduce.py                        # 真实 CLI 正反回归（tempfile，无测试提交产物）
```

## 调用方式

加载 Skill 后，Agent 按 SKILL.md 六步流程：读输入→断言拆解→证据绑定→来源元数据→**records-only 质检**→**export_nanopub.py 机械导出→最终等价质检**。模型只维护 `result.nanopublications`，不再独立双写 JSON-LD 或 pubinfo graph。

```bash
python scripts/validate_nanopub.py --records-only /app/output/result.json
python scripts/export_nanopub.py /app/output/result.json --out-dir /app/output/nanopubs --update-result
python scripts/validate_nanopub.py /app/output/result.json [extra.jsonld ...]
```

每条 `id=np-NNN`（唯一且从 np-001 连续）生成一个同名 JSON-LD，URN 为 `urn:nanopub:<case_id>:<n>`。canonical 映射中 @context 固定，`@graph` 恰为 assertion/evidence/provenance/pubinfo 四对象列表：assertion 保留 SPO/condition 与 status/basis；evidence 保留三键（unverified 空值亦不删结构）；provenance 保留记录字段并派生 `<urn>#evidence` 链接和固定方法模板；pubinfo 只来自 `result.pubinfo`。完整字段映射见 `references/output-schema.md`。

## 输出契约

`/app/output/result.json` 必含：`case_id`、`status`、`status_reason`、output_contract 字段、`pubinfo`、`nanopublications[]`（assertion + evidence + provenance + status + basis）、`uncertainties`。

## 依赖

无强制第三方包；抽取由加载 Skill 的 LLM 执行，`references/` 提供规则与受控词表。

## 质检

三道交付关口（两次机检，中间只能由 exporter 机械导出）：

1. 导出前 records-only：`python scripts/validate_nanopub.py --records-only /app/output/result.json`，校验谓词、assertion/evidence/provenance、连续唯一 id 与 evidence 状态规则。仅 `status=unverified` 的空 evidence 可 warning 放行；成功输出明确不代表 Final。
2. 机械导出：`python scripts/export_nanopub.py /app/output/result.json --out-dir /app/output/nanopubs --update-result`。只从 records 和 result.pubinfo 生成规范文件，更新来源清单并清除内嵌陈旧字段；partial/unverified 也可按真实内容导出。
3. 最终等价：`python scripts/validate_nanopub.py /app/output/result.json [extra.jsonld ...]`。除 `@context`、四 graph 与 URN 形态外，严格检查文档数=record 数、URN 一一对应及全部内容映射。校验复用 `build_document` 做 canonical JSON 树全等比较（对象键序无关，数组顺序及字段/值缺多或改变均相关）。内嵌、`jsonld_files` 与 CLI 附件合并计数，重复来源及额外/缺失文档均失败；不能借附件绕过等价。

任一关口退出码非 0 时均须按错误清单修正。partial 若有输出也必须满足输出契约，并在 `status_reason`/`uncertainties` 如实列出未完成范围与 JSON-LD 等缺口；warning 不能替代最终严格质检。

## 异常处理与限制

- 无文本层 → OCR，不可靠则 uncertain；证据不足 → unverified；原文矛盾 → conflict；关系方向不明 → uncertain；限定词缺失 → 补回或 uncertain。
- 本 Skill 只做忠实拆解对齐，不推断原文没有的断言。

## 最小调用示例（示意，非正式案例）

输入 `/input/case.json`：`{"case_id":"demo","output_contract":{"format":"json-ld"},"pdf":"/input/paper.pdf"}`

输出结构见 `references/output-schema.md` 与 `examples/nanopub-examples.md`。
