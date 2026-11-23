# 最小调用示例（示意，非正式案例结果）

> 本示例仅说明接口与流程；文献、摘录与数值均为虚构示意，不来自任何正式测试案例。

## 输入（示意）

`case.json` 摘要：

```json
{
  "case_id": "demo-001",
  "research_question": "方法 X 是否能提升材料 Y 的强度？",
  "output_contract": {"fields": ["case_id", "status", "research_product", "evidence_matrix", "uncertainty", "sources", "change_record"]},
  "documents": [
    {"id": "S1", "title": "...(题录 A)", "file": "papers/a.pdf"},
    {"id": "S2", "title": "...(题录 B，仅摘要)"},
    {"id": "S3", "title": "...(题录 C)"}
  ]
}
```

## 调用

Agent 加载本 Skill 后按 SKILL.md 的 P1–P8 执行：写骨架 → 纳排标准 → 筛选 → 比较矩阵与证据行 → 主题 → 草稿 → 三项审计 → 校验交付。

## 示意输出（片段，标注为示例）

`result.json`（节选）：

```json
{
  "case_id": "demo-001",
  "status": "partial",
  "research_product": {
    "research_question": "方法 X 是否能提升材料 Y 的强度？",
    "type": "review",
    "themes": [{"id": "T1", "name": "X 工艺的强化机制", "subthemes": [], "supported_by": ["S1"], "boundary": "只含实验研究，不含模拟"}],
    "sections": [{"id": "SEC1", "heading": "X 工艺的强化机制", "paragraphs": [{"claim_id": "C1", "claim": "X 可提升 Y 的抗拉强度（示意）", "strength": "suggestive", "evidence_ids": ["E1"]}]}],
    "conclusions": [{"claim_id": "C2", "statement": "初步表明 X 提升 Y 强度（示意）", "strength": "suggestive", "evidence_ids": ["E1"], "scope_note": "仅限 S1 的工艺窗口"}]
  },
  "evidence_matrix": {
    "screening_flow": {"identified": 3, "duplicates_removed": 0, "screened": 3, "excluded_irrelevant": 1, "excluded_other": 0, "abstract_only": 1, "included": 1},
    "screening_records": [
      {"id": "S1", "status": "included", "reason": "报告 X 对 Y 强度的量化结果", "evidence_location": "摘要"},
      {"id": "S2", "status": "abstract_only", "reason": "无全文", "evidence_location": "题录"},
      {"id": "S3", "status": "excluded_irrelevant", "reason": "研究对象为材料 Z", "evidence_location": "摘要"}
    ],
    "comparison_matrix": [{"source_id": "S1", "design": "实验", "population": "Y 合金", "method": "X 工艺", "metrics": "抗拉强度", "main_results": "+12%（示意）", "conclusions": "X 有效", "limitations": "单一批次"}],
    "evidence_rows": [{"id": "E1", "source_id": "S1", "excerpt": "...(逐字短引，示意)", "location": "p.4 表2", "claim": "X 提升 Y 抗拉强度（示意）", "strength": "suggestive", "note": "单一批次"}]
  },
  "audit": {
    "citation_audit": {"checked": 2, "supported": 2, "fixed": 0, "dropped": 0, "items": [{"claim_id": "C1", "verdict": "ok", "reason": "摘录覆盖论断"}, {"claim_id": "C2", "verdict": "ok", "reason": "综合结论未超出 E1 的证据范围"}]},
    "coverage_check": {"included_sources_cited": "1/1", "themes_with_evidence": "1/1", "evidence_rows_used": "1/1", "issues": []},
    "wording_audit": {"strong_wording_checked": 1, "corrected": 1, "items": [{"claim_id": "C1", "before": "证实", "after": "初步表明"}]}
  },
  "uncertainty": {"conflicts": [], "biases": [{"type": "单一数据源", "description": "仅一篇全文", "impact": "结论强度受限"}], "gaps": [{"id": "G1", "gap": "无多批次重复实验", "evidence_basis": "S1 未报告"}], "undetermined": [{"item": "S2 是否与 S1 结论一致", "reason": "仅摘要", "impact": "无法计入强度判断"}]},
  "sources": [
    {"id": "S1", "authors": "示意", "year": "2024", "title": "...(题录 A)", "venue_or_doi": "示意", "full_text_available": true},
    {"id": "S2", "authors": "示意", "year": "未知", "title": "...(题录 B)", "venue_or_doi": "未知", "full_text_available": false},
    {"id": "S3", "authors": "示意", "year": "未知", "title": "...(题录 C)", "venue_or_doi": "未知", "full_text_available": false}
  ],
  "change_record": [{"version": "v1", "changed": "audit", "reason": "措辞审计修正 1 处"}]
}
```

对该 `result.json` 运行 `python3 scripts/validate_result.py result.json` 应输出 `OK`（可有 WARNING）。
