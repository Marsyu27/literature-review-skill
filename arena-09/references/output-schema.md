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

## Canonical JSON-LD 机械导出

**模型只编写 records，不独立编写或同步第二份 JSON-LD。** 完成 records-only 质检后，唯一允许的导出路径是：

```bash
python scripts/validate_nanopub.py --records-only /app/output/result.json
python scripts/export_nanopub.py /app/output/result.json \
  --out-dir /app/output/nanopubs --update-result
python scripts/validate_nanopub.py /app/output/result.json [extra.jsonld ...]
```

每条 `result.nanopublications` 对应 `np-NNN.jsonld`。`id` 必须唯一、按数组顺序从 `np-001` 连续编号，并映射到 `urn:nanopub:<case_id>:1` 等；`case_id` 不得含冒号或空白。`--update-result` 只把 `jsonld_files` 改为本次规范文件的相对路径清单，并删除陈旧内嵌 `jsonld` / `json_ld` 字段，不删除其他 result 字段或目录中的其他文件。`partial` / `unverified` 同样按真实 records 导出，不填写推测内容。

### 唯一 canonical 映射

- `@context` 固定为下方示例中的 schema.org + `np` 六项定义；顶层只有 `@context`、`@id`、`@graph`。
- `@graph` **固定为四对象列表**，顺序恰为 `assertion`、`evidence`、`provenance`、`pubinfo`；各项 `@id` 分别带规范 URN 后缀 `#assertion` / `#evidence` / `#provenance` / `#pubinfo`，四类型固定为 `np:Assertion` / `np:Evidence` / `np:Provenance` / `schema:ScholarlyArticle`。
- assertion graph：`subject` / `predicate` / `object` / `condition` 分别映射 `np:subject` / `np:predicate`（确保 `np:` 前缀）/ `np:object` / `np:condition`；空 condition 省略。`record.status` / `basis` 同图保留为 `np:status` / `np:basis`。
- evidence graph：`evidence_text` / `evidence_location` / `evidence_type` 原值映射同名 `np:` 键。即使 unverified 空证据也保留三键，空值导出为 `""`，不删 graph 或字段。
- provenance graph：保留 `record.provenance` 的 `assertion` / `evidence` / `paper` / `author` / `year` / `version`，其余普通扩展字段也稳定映射为同名 `np:` 键；输入中的 `wasDerivedFrom` 与 `extractionMethod` 不作为自由文本来源。`np:wasDerivedFrom` 强制派生为当前 `<urn>#evidence`，`np:extractionMethod` 固定生成为 `由 nanopublication-extraction Skill 从论文 <result.pubinfo.paper_title> 抽取`。
- pubinfo graph：**不再由 Agent 另写**。由 `result.pubinfo` 确定性映射 `paper_title` → `schema:name`、`authors` → `schema:author`、`year` → `schema:datePublished`、`version` → `schema:version`、`identifier` → `schema:identifier`；缺省标准为对应空字符串或作者空数组，`license` 存在时映射 `schema:license`。

最小完整示例（顶层 `@id` 实际为 `urn:nanopub:demo:1`）：

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
  "@id": "urn:nanopub:demo:1",
  "@graph": [
    {
      "@id": "urn:nanopub:demo:1#assertion",
      "@type": "np:Assertion",
      "np:subject": "Treatment A",
      "np:predicate": "np:reduces",
      "np:object": "tumor size",
      "np:status": "ok",
      "np:basis": "原文直接给出方向、数值与限定条件。",
      "np:condition": "by 30%, p<0.05, in mice"
    },
    {
      "@id": "urn:nanopub:demo:1#evidence",
      "@type": "np:Evidence",
      "np:evidence_text": "Treatment A reduced tumor size by 30% (p<0.05) in mice",
      "np:evidence_location": "§3 ¶2",
      "np:evidence_type": "direct"
    },
    {
      "@id": "urn:nanopub:demo:1#provenance",
      "@type": "np:Provenance",
      "np:assertion": "np-001",
      "np:evidence": "§3 ¶2",
      "np:paper": "A Demonstration Study",
      "np:author": "A. Author",
      "np:year": "2025",
      "np:version": "arXiv v2",
      "np:wasDerivedFrom": "urn:nanopub:demo:1#evidence",
      "np:extractionMethod": "由 nanopublication-extraction Skill 从论文 A Demonstration Study 抽取"
    },
    {
      "@id": "urn:nanopub:demo:1#pubinfo",
      "@type": "schema:ScholarlyArticle",
      "schema:name": "A Demonstration Study",
      "schema:author": ["A. Author", "B. Author"],
      "schema:datePublished": "2025",
      "schema:version": "arXiv v2",
      "schema:identifier": "arXiv:2501.00000",
      "schema:license": "CC-BY-4.0"
    }
  ]
}
```

### 严格全等而不是外壳检查

最终质检复用 exporter 的 `build_document(result, rec)`，对每个实际文档与 records 现算出的 canonical 文档做 **JSON 树严格全等比较**：对象键顺序不影响等价；数组顺序、额外/缺失字段、任何值变化都影响等价。因此 alternate JSON-LD 外壳即使语义相似也不被接受。所有内嵌 `jsonld` / `json_ld`、`jsonld_files` 和命令行附件合并计数；文档数必须等于 record 数，不允许缺失、额外或重复 URN，也不能用附件绕过某一 record 的逐项映射。下游程序可直接解析 canonical 文件，无需人工清洗。

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
- `partial`：部分完成（个别断言证据缺失/冲突）；已有输出仍须满足字段契约并通过最终严格质检，`status_reason` 与 `uncertainties` 明列覆盖范围及所有缺口，不能用 warning 掩盖缺少 JSON-LD。
- `unable`：无法处理（材料缺失/加密/无文本层），写明原因，不编造。

## 诚实原则

数值、单位、限定词逐字保留；证据不足 → `unverified`，此时允许空 evidence，但脚本会给 warning，且必须在 `basis`/`uncertainties` 写明“证据缺失”；其他状态空 evidence 为 error。原文矛盾 → `conflict` 保留两处原文；关系方向不明 → `uncertain`，不补造。

## 两步机检

1. 导出前 records-only 质检：`python scripts/validate_nanopub.py --records-only /app/output/result.json`，不宣称已导出或检查 JSON-LD，更不宣称 Final 通过。
2. `export_nanopub.py ... --out-dir ... --update-result` 机械导出后，运行 `python scripts/validate_nanopub.py /app/output/result.json [extra.jsonld ...]`。最终校验除 `@context`、四 graph 与 URN 形态外，还严格比较数量、连续 id、URN 一一对应以及 SPO/condition、evidence、status/basis、provenance、pubinfo；任何不一致均退出非 0。
