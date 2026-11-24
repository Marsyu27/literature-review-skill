# 来源绑定与证据强度（Source Binding）

每个节点、每条边都能**回得去**原文。

## 必填来源字段

| 字段 | 含义 |
|---|---|
| `evidence_text` | 支撑该节点/边的原文片段 |
| `evidence_location` | 论文标识 + 章节/图表/段落位置（如 `paper=D, §3 ¶2, Table 2`） |
| `evidence_strength` | strong / medium / weak |

## 证据强度

| 强度 | 判定 |
|---|---|
| `strong` | 原文直接陈述 |
| `medium` | 由原文推断（组合多处、逻辑推导，`basis` 写明步骤） |
| `weak` | 转述、综述、共现、推测 |

## 规则

1. 位置指向**真正对应**位置，不写笼统的"见正文"。
2. 证据跨图表/段落 → 列出所有位置。
3. 无法确定位置 → 标 `uncertain`，不伪造。
4. 转述/综述证据 → 标 `weak` 并注明"非作者结论"。

## 样例（示意）

```json
{"evidence_text":"Model M achieves 0.81 accuracy on dataset D, outperforming baseline 0.79 (p<0.05)",
 "evidence_location":"paper=Demo, §5 Table 2", "evidence_strength":"strong"}
```
