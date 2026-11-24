# 来源元数据与溯源链（Provenance Metadata）

每条断言都能**追得回**：断言 → 证据 → 论文 → 作者 → 年份 → 版本 → 标识符。

## 必填元数据

| 字段 | 含义 |
|---|---|
| `paper_title` | 论文标题 |
| `authors` | 作者列表 |
| `year` | 发表年份 |
| `version` | 版本（arXiv v1、期刊版、预印本等） |
| `identifier` | DOI / arXiv ID / PMID 等标识符 |
| `data_source` | 数据来源（若有） |

## 溯源链完整性

1. 每条断言 → `evidence_location`（可定位原文）。
2. 每个案例 → `pubinfo`（论文级元数据，一次记录，全部断言共享）。
3. 版本差异（预印本 vs 期刊版）→ 记录 `version`，断言锚点随版本对应。

## Canonical 导出与一致性质检

- Agent 只在 record.provenance / result.pubinfo 填真实值，不再独立编写 JSON-LD provenance 或 pubinfo graph。
- exporter 将 provenance 的 `assertion` / `evidence` / `paper` / `author` / `year` / `version` 及普通扩展字段映射为 `np:` 键；`np:wasDerivedFrom` 始终由当前 nanopub URN 派生为 `<urn>#evidence`，不信任记录中可能陈旧的链接。
- `np:extractionMethod` 只按 `由 nanopublication-extraction Skill 从论文 <paper_title> 抽取` 模板生成；pubinfo graph 的 name/author/datePublished/version/identifier/license 只来自 `result.pubinfo`。
- 最终 validator 用同一个 `build_document` 现算预期文档，逐项严格比较 provenance 字段、URN 链接和 pubinfo；改 record 不改文档或改文档不改 record 都会失败。

## 去重

- 同一条断言在多篇论文中出现 → 按论文/版本分别记录，不合并来源。
- 同一论文内重复断言 → 合并为一条，记录多处位置。

## 样例（示意）

```json
{
  "pubinfo": {
    "paper_title": "A Demonstration Study",
    "authors": ["A. Author", "B. Author"],
    "year": "2025",
    "version": "arXiv v2",
    "identifier": "arXiv:2501.00000"
  }
}
```
