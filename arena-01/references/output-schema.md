# result.json 字段契约（Output Schema）

## 契约优先级

1. **`/input/case.json` 的 `output_contract` 字段 > 本文件定义的 Skill 默认字段**。
2. `output_contract` 声明的每个字段**缺失必补**（字段名与类型原样回填，不得改名或省略）。
3. 命名或类型与本文件默认字段冲突时，**以 `output_contract` 为准**，本文件字段仅作默认补充。

## 硬性要求

1. `case_id` 原样回填；`status` + `status_reason` 必填。
2. **output_contract**：`/input/case.json` 里 `output_contract` 声明的每个字段都要出现在 result.json，字段名与类型一致。
3. 译文每个段落可指回原文（段号 + 依据），译不准处如实标注。

## 字段定义

```json
{
  "case_id": "<回填>",
  "status": "success | partial | unable",
  "status_reason": "<unable/partial 时必填>",
  "source_lang": "en",
  "target_lang": "zh",
  "terminology": [
    {"term": "…", "translation": "…", "first_at": "§1 ¶1", "unified": true, "note": ""}
  ],
  "segments": [
    {
      "id": "§2 ¶3",
      "source": "原文段落",
      "target": "译文段落",
      "basis": "译法依据：术语/数字/单位/公式已逐字核对",
      "status": "ok | uncertain | unable"
    }
  ],
  "uncertainties": ["需要人工确认的清单"],
  "tool_commands": ["实际执行的命令，用于复现与审计"]
}
```

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `case_id` / `status` / `status_reason` | 是 | 运行状态三件套 |
| `source_lang` / `target_lang` | 是 | 源/目标语言 |
| `terminology` | 是 | 冻结的术语表 |
| `segments` | 是 | 段落级双语对照，含段号、原文、译文、依据、状态 —— "可核验"的载体 |
| `uncertainties` | 是 | 无法判断/需人工确认项；无则空数组 |
| `tool_commands` | 推荐 | 实际命令，用于复现 |
| output_contract 字段 | 是 | 按 case.json 原样回填 |

## 状态与降级

- `success`：所有 output_contract 字段有值，各段可复核。
- `partial`：部分完成（如个别段残缺、术语有冲突），`uncertainties` 说明缺口。
- `unable`：无法翻译（材料缺失/加密/无法读取），写明原因，不编造。

## 诚实原则

数字、单位、公式、引用编号逐字保留；译不出就标不确定，不补造。每条译文说明"从哪来"（段号 + 依据）。
交付前 `scripts/check_terminology.py` 与 `scripts/check_conservation.py` 必须全绿（退出码 0），两条实际命令记入 `tool_commands`，报告文件路径写入 `uncertainties` 或工作目录说明；脚本残余缺口不得隐瞒。
