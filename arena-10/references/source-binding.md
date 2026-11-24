# 来源绑定与证据强度（Source Binding）

每个节点、每条边都能**回得去**原文。

## 必填锚点字段（四元组）

| 字段 | 含义 |
|---|---|
| `source_id` | 论文标识，取自输入 corpus manifest 的论文标识（如 `primary` / `secondary`），**禁止自编** |
| `paragraph_id` | 组织方 JATS 段落 ID（不是 PDF 页码，也不是自建 `§/¶`） |
| `quote` | ≤30 字原文短引，逐字摘自该段落 |
| `strength` | strong / medium / weak |

可选 `note`：human-readable 备注（如旧式 `§3 ¶2, Table 2` 的人工可读位置说明），仅作备注，不作锚点依据。

## 证据强度

| 强度 | 判定 |
|---|---|
| `strong` | 原文直接陈述 |
| `medium` | 由原文推断（组合多处、逻辑推导，`basis` 写明步骤） |
| `weak` | 转述、综述、共现、推测 |

## 规则

1. `source_id` + `paragraph_id` 指向**真正对应**的论文与 JATS 段落，不写笼统的"见正文"；`quote` 必须逐字出自该段落。
2. 证据跨段落/跨篇 → 列出所有锚点（每条各自带 `source_id` + `paragraph_id`）。
3. 无法确定位置 → 标 `uncertain`，不伪造 paragraph_id。
4. 转述/综述证据 → 标 `weak` 并注明"非作者结论"。
5. 根 DOI/title/authors 属首篇，不得套到第二篇；每篇的元数据只取自 manifest 与其自身 JATS。

## 样例（示意 ID）

```json
{"evidence":{"source_id":"primary","paragraph_id":"pri-p-0031",
 "quote":"Model M achieves 0.81 accuracy","strength":"strong",
 "note":"human-readable：§5 Table 2"}}
```
