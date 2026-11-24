# 质量检查清单（Quality Check）

每条断言导出前逐项检查，给出**可复现的判定依据**。

## 必查项

| # | 检查点 | 判定 |
|---|---|---|
| 1 | 断言过宽 | 一条断言只含一个主体-关系-客体；复合句已拆开 |
| 2 | 证据不足 | `evidence_text` 是最小充分片段，确实支撑断言 |
| 3 | 关系类型错误 | predicate 来自受控词表，方向准确（因果≠相关） |
| 4 | 主体混淆 | 主体唯一且明确；有歧义则标 uncertain |
| 5 | 来源缺失 | `pubinfo` 齐全，`evidence_location` 可定位 |
| 6 | 限定词丢失 | 条件/范围/显著性保留，缺失则 uncertain |
| 7 | 断言与证据冲突 | 冲突则保留两处原文并标 conflict |
| 8 | 数值/单位失真 | 数值、单位、显著性逐字保留 |
| 9 | record/JSON-LD 双源漂移 | 不手工双写；机械导出后 canonical 全等且数量、URN 一一对应 |

## 检查失败处置

- 可回第 1 步重拆 → 重拆后复检。
- 无法确定 → 标 `status=uncertain`，写入 `uncertainties`，不硬写。
- 证据不足 → 标 `status=unverified`，在 `basis`/`uncertainties` 写"证据缺失"；仅这种状态允许空 evidence，并会产生可解释 warning，其他状态空 evidence 仍是 error。

## 判定依据格式

每条断言记录 `basis`：写明"为什么这条证据充分/为什么关系方向是 A→B"，供第三方复核。

## records-only → 机械导出 → 最终等价质检

1. 先运行 `python scripts/validate_nanopub.py --records-only /app/output/result.json`。这只检查 records，**不能声称 JSON-LD 或 Final 已通过**。
2. 模型不另写 JSON-LD，运行 `python scripts/export_nanopub.py /app/output/result.json --out-dir /app/output/nanopubs --update-result`，从 records 与 `result.pubinfo` 生成 canonical 文件。
3. 运行 `python scripts/validate_nanopub.py /app/output/result.json [extra.jsonld ...]` 做最终等价质检。validator 复用 `build_document`，要求 canonical 四 graph 列表与现算文档 JSON 树严格全等，并检查文档数=record 数、id 连续唯一、URN 一一对应及 SPO/condition、evidence、status/basis、provenance、pubinfo。对象键序无关，数组顺序及额外/缺失/改变字段均会失败。
4. 内嵌 `jsonld` / `json_ld`、`jsonld_files` 和 CLI 附件都合并计数；少文档、多文档、重复 URN 或重复来源必须失败，不能借附件绕过等价。两条记录内容不同却只交一条“代表文档”同样失败。

## 样例（示意）

- 检查项 3 不通过：原文 `was associated with`（相关）被写成 `causes`（因果）→ 改回 `is_associated_with`，`basis` 记"原文为相关表述，不得写成因果"。
- 检查项 6 不通过：断言漏掉 `in vitro` → 补回限定，`basis` 记"结论仅在体外成立，不可省略"。
