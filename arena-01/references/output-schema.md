# result.json 字段契约（Output Schema）

## 契约优先级与交付门禁

1. **`/input/case.json` 的 `output_contract` 字段 > 本文件定义的 Skill 默认字段**。
2. `output_contract` 声明的每个字段**缺失必补**（字段名与基本类型原样回填，不得改名或省略）。
3. 命名或类型与本文件默认可选字段冲突时，**以 `output_contract` 为准**，本文件字段仅作默认补充。若 case 另给 `optional_fields` / `optional_output_fields` 扩展声明，则仅核 result 中实际出现的字段，且不能覆盖同名 `output_contract` 声明。
4. 最终交付必须由 `scripts/validate_translation_delivery.py` 核验 case_id、契约字段、快照切片、ID/区间/覆盖及可选 work/final 漂移。静态结构另见 `references/result.schema.json`；JSON Schema 不能替代的动态检查以脚本报告为准。

## 硬性要求

1. `case_id` 原样回填；`status` + `status_reason` 必填。`partial/unable` 的原因不得为空白。
2. 最终 `result.segments` 每项至少含：`id`、`source`、`target`、`source_start`、`source_end`；默认还应有 `basis`、`status`。
3. **唯一源文快照**：把规范化后的完整原文保存为 `work/source-snapshot.txt`，保存后不再改动。下标是 Python Unicode 字符下标（不是 UTF-8 字节数），区间左闭右开，且必须逐字满足：

   ```python
   snapshot[segment["source_start"]:segment["source_end"]] == segment["source"]
   ```

4. `id` 唯一；所有区间满足 `0 <= source_start < source_end <= len(snapshot)`，按原文顺序递增、互不重叠；`target` 去首尾空白后非空。无法翻译时写明确的 unable 说明标记并降级，不能以空译文占位。
5. 段尾换行和段间分隔符也在快照中占字符。可将其并入前一段，避免 success 因段间一个换行出现未声明空洞。
6. `success` 必须从 0 到 `len(snapshot)` 连续全覆盖，`uncovered_ranges` 可省略；若提供则必须精确等于计算结果（完整成功时为空数组）。
7. `partial/unable` 必须提供 `uncovered_ranges`，其规范形式为 `[{"source_start": 17, "source_end": 34}]`，按起点递增，**精确等于**从实际分段计算出的全部未覆盖区间，不多、不少、不合并遗漏。核验器也接受 `[start, end]` 二元数组，但报告统一为对象形式。
8. 送术语/守恒检查的工作 `segments.json` 若提供给 `--work-segments`，其段数、顺序以及每项 `id/source/target/source_start/source_end` 必须与最终 `result.segments` 一致，防止送检文件和终稿漂移。

## 默认字段定义

```json
{
  "case_id": "<回填>",
  "status": "success | partial | unable",
  "status_reason": "<success 可为空字符串；partial/unable 必须为非空原因>",
  "source_lang": "en",
  "target_lang": "zh",
  "terminology": [
    {"term": "performance", "aliases": ["efficiency"], "locked": "效率", "alternates": []},
    {"term": "bank", "locked": "银行", "context": ["\\b(?:account|finance)s?\\b"]}
  ],
  "segments": [
    {
      "id": "§2 ¶3",
      "source": "<与所保存快照该区间逐字一致>",
      "target": "<非空译文>",
      "source_start": 0,
      "source_end": 20,
      "basis": "译法依据：术语/数字/单位/公式已逐字核对",
      "status": "ok | uncertain | unable"
    }
  ],
  "uncovered_ranges": [],
  "uncertainties": ["需要人工确认的清单及未执行的核验"],
  "tool_commands": ["实际执行的命令，用于复现与审计"]
}
```

上面带 `<...>` 与本节占位数字的是字段模板，不是可直接交付的完整结果；实际使用见下文可运行的完整成功例。

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` / `status` / `status_reason` | 是 | 输入标识与诚实运行状态 |
| `segments` | 是 | 含唯一 ID、非空译文、快照字符区间；默认含依据和段状态 |
| `uncovered_ranges` | partial/unable 是 | 精确覆盖所有缺口；success 若提供通常为空 |
| `source_lang` / `target_lang` | 默认是 | 源/目标语言；可被 output_contract 同名异型声明覆盖 |
| `terminology` | 默认是 | 冻结术语表；aliases/context/alternates/frozen 规则见 `terminology-lock.md` |
| `uncertainties` | 默认是 | 不确定内容、脚本失败和未执行语义核验的清单；无则空数组 |
| `tool_commands` | 推荐 | 实际命令及报告路径 |
| output_contract 字段 | 是 | 每个声明字段均须存在；能推断基本类型时必须一致 |

### output_contract 基本类型机检边界

核验器支持 `"answer": "string"`、`{"type":"array"}` 等类型声明，也能从 `"lang":"zh"`、布尔/数字/数组/对象等非 null 示例值推断 JSON 基本类型。`null`、只有描述而无类型的对象等不能可靠推断时，只核字段存在性并输出 `unknown_contract_type` **warning**，不伪造类型通过。success 有任何此类未解决 warning 都必须失败；partial/unable 可过结构门禁，但须把类型待人工核验写入 `status_reason` 或 `uncertainties`。

## 状态与“全绿”口径

- **success**：所有 output_contract 字段及最小交付字段满足契约；快照连续全覆盖；术语、守恒、交付三个脚本均退出 0，且 success 不允许遗留 drift/未知类型 warning；否定、限定、因果、指代、漏译/多译等语义人工回核均已完成。
- **partial**：允许有未译范围或其他降级，但不允许空 target、重复 ID、非法/重叠区间、source 与快照不一致或静默漏段。仍须执行结构与覆盖检查；`status_reason` 非空，`uncovered_ranges` 精确，未完成的术语/守恒/语义核验及报告路径写入 `uncertainties`。delivery 脚本退出 0 只代表结构和覆盖声明合格，绝不代表“所有检查全绿”。
- **unable**：材料缺失/加密/无法读取等原因清楚，合法保留已有分段并精确声明未覆盖范围，不编造。

## 完整成功例（示意，非正式案例）

源文快照 `work/source-snapshot.txt` 精确为（含第一段末尾换行，共 34 个字符）：

```text
First paragraph.
Second paragraph.
```

对应 `case.json` 为：

```json
{"case_id":"demo","output_contract":{"answer":"string","lang":"zh"}}
```

完整 `result.json`：

```json
{
  "case_id": "demo",
  "status": "success",
  "status_reason": "",
  "source_lang": "en",
  "target_lang": "zh",
  "answer": "完整译文见 segments。",
  "lang": "zh",
  "terminology": [],
  "segments": [
    {
      "id": "§1 ¶1",
      "source": "First paragraph.\n",
      "target": "第一段。",
      "source_start": 0,
      "source_end": 17,
      "basis": "逐句翻译；段尾换行归入本段快照区间",
      "status": "ok"
    },
    {
      "id": "§2 ¶1",
      "source": "Second paragraph.",
      "target": "第二段。",
      "source_start": 17,
      "source_end": 34,
      "basis": "逐句翻译；覆盖快照末尾",
      "status": "ok"
    }
  ],
  "uncovered_ranges": [],
  "uncertainties": [],
  "tool_commands": [
    "python3 scripts/check_terminology.py --terms terminology.json --segments segments.json --report work/terminology-report.json",
    "python3 scripts/check_conservation.py --segments segments.json --report work/conservation-report.json",
    "python3 scripts/validate_translation_delivery.py --case case.json --source-text work/source-snapshot.txt --result result.json --work-segments segments.json --report work/delivery-report.json"
  ]
}
```

若只交付第一段，则同一快照下应改为 `status:"partial"`，保留第一段 `[0,17)`，填写非空 `status_reason`，并声明：

```json
"uncovered_ranges": [{"source_start": 17, "source_end": 34}]
```

同时把第二段未译、任何未执行语义核验写入 `uncertainties`。不得继续声称 success，也不得用空 target 占第二段。

## 诚实原则

数字、单位、公式、图表/公式引用类型+编号、文献引用逐字守恒；中英文标签可互译但类型不可改变。交付前必须把三个实际命令记入 `tool_commands`，报告路径写入工作目录说明。success 修复至全绿；partial 如实列残余错误、人工核验缺口和覆盖缺口，均不得隐瞒。
