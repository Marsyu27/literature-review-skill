# result.json / JSON-LD 字段契约（Output Schema）

## 硬性要求

1. `case_id` 原样回填；`status` + `status_reason` 必填。
2. **output_contract**：`/input/case.json` 里 `output_contract` 声明的每个字段都要出现，字段名与类型一致。
3. 断言可机器读取：每条 = `assertion`(subject/predicate/object) + `evidence` + `provenance`，序列化形态固定。

## 字段定义

```json
{
  "case_id": "<回填>",
  "status": "success | partial | unable",
  "status_reason": "<unable/partial 时必填>",
  "pubinfo": {"paper_title":"…","authors":["…"],"year":"…","version":"…","identifier":"…"},
  "nanopublications": [
    {
      "id": "np-001",
      "assertion": {"subject":"…","predicate":"…","object":"…","condition":"…"},
      "evidence": {"evidence_text":"…","evidence_location":"§3 ¶2","evidence_type":"direct|indirect"},
      "provenance": {"assertion":"np-001","evidence":"§3 ¶2","paper":"…","author":"…","year":"…","version":"…"},
      "status": "ok | uncertain | unverified | conflict",
      "basis": "判定依据"
    }
  ],
  "uncertainties": ["需要人工确认的清单"],
  "tool_commands": ["实际执行的命令，用于复现与审计"]
}
```

## JSON-LD 导出

每条 nanopublication 对应一个 JSON-LD 文档。**必须含 `@context`**，否则不是可序列化的 RDF。约定：

- `@context`：schema.org + 自定义 `np` 命名空间（`https://example.org/nanopub-skill/ns#`，承载词表谓词与 nanopub 结构键）。
- `@id` 规则：`urn:nanopub:<case_id>:<n>`（n 从 1 起按断言序号递增），各 named graph 在其后分别缀 `#assertion` / `#evidence` / `#provenance` / `#pubinfo`。
- 用 `@graph` 给出四个 named graph 键：`assertion`（主体-谓词-客体，谓词取受控词表，写作 `np:<predicate>`）、`evidence`（最小充分证据 + 位置 + 直接/间接）、`provenance`（证据来源 + 抽取方法"由该 Skill 从论文 X 抽取"）、`pubinfo`（论文元数据 + 标识符 + 许可）。

最小完整示例：

```json
{
  "@context": {
    "schema": "https://schema.org/",
    "np": "https://example.org/nanopub-skill/ns#",
    "assertion": "np:assertion",
    "evidence": "np:evidence",
    "provenance": "np:provenance",
    "pubinfo": "np:pubinfo"
  },
  "@id": "urn:nanopub:<case_id>:1",
  "@graph": [
    {
      "@id": "urn:nanopub:<case_id>:1#assertion",
      "@type": "np:Assertion",
      "np:subject": "Treatment A",
      "np:predicate": "np:reduces",
      "np:object": "tumor size",
      "np:condition": "by 30%, p<0.05, in mice"
    },
    {
      "@id": "urn:nanopub:<case_id>:1#evidence",
      "@type": "np:Evidence",
      "np:evidence_text": "<最小充分原文片段>",
      "np:evidence_location": "§3 ¶2",
      "np:evidence_type": "direct"
    },
    {
      "@id": "urn:nanopub:<case_id>:1#provenance",
      "@type": "np:Provenance",
      "np:wasDerivedFrom": "urn:nanopub:<case_id>:1#evidence",
      "np:extractionMethod": "由 nanopublication-extraction Skill 从论文 <paper_title> 抽取"
    },
    {
      "@id": "urn:nanopub:<case_id>:1#pubinfo",
      "@type": "schema:ScholarlyArticle",
      "schema:name": "<paper_title>",
      "schema:author": ["<authors>"],
      "schema:datePublished": "<year>",
      "schema:identifier": "<DOI/标识符>",
      "schema:license": "<许可>"
    }
  ]
}
```

下游程序可直接解析，无需人工清洗。

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` / `status` / `status_reason` | 是 | 运行状态三件套 |
| `pubinfo` | 是 | 论文级来源元数据——"追得回" |
| `nanopublications[].assertion` | 是 | 主体/谓词/客体 + 条件——"拆得细" |
| `nanopublications[].evidence` | 是 | 最小充分证据 + 位置 + 直接/间接——"对得上" |
| `nanopublications[].status` / `basis` | 是 | 断言状态与判定依据 |
| `uncertainties` | 是 | 无法判断/需人工确认项 |
| `tool_commands` | 推荐 | 实际命令，用于复现 |

## 状态与降级

- `success`：所有 output_contract 字段有值，断言可复核。
- `partial`：部分完成（个别断言证据缺失/冲突）。
- `unable`：无法处理（材料缺失/加密/无文本层），写明原因，不编造。

## 诚实原则

数值、单位、限定词逐字保留；证据不足 → `unverified`；原文矛盾 → `conflict` 保留两处原文；关系方向不明 → `uncertain`，不补造。
