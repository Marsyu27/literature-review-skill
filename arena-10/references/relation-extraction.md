# 关系抽取与受控词表（Relation Extraction）

只建立**有证据支持**的关系，方向与适用条件与原文一致。

## 关系类型（受控词表）

| predicate | 含义 | 方向 |
|---|---|---|
| `uses` | 使用 | 方法/任务 → 材料/方法 |
| `compares` | 与…比较 | A → B |
| `outperforms` | 优于 | A → B（A 更优） |
| `supports` | 支持（证据支持结论） | 证据/结果 → 结论 |
| `contradicts` | 矛盾 | A → B |
| `is_a` | 属于 | 子 → 类 |
| `evaluated_by` | 由…评价 | 任务/方法 → 指标 |
| `achieved` | 达到（数值） | 方法 → 指标值 |
| `applied_to` | 应用于 | 方法 → 任务 |

## 规则

1. **有证据才连边**：关系在原文有陈述才建；共现、综述转述、推测不当作直接证据。
2. **方向准确**：`outperforms` 是 A→B（A 更优），反向是错误。
3. **因果 vs 相关、优于 vs 比较**：
   - `outperforms`（明确更优）≠ `compares`（仅比较）。
   - 相关（associated with）不写成因果（causes）。
4. **适用条件保留**：`under X`、`in vitro`、`n=3` 作为边的 `condition`。
5. **证据强度**：直接陈述 `strong`；间接推断 `medium`；转述/共现 `weak`。

## 样例（示意）

```json
{"source":"E1","predicate":"outperforms","target":"E3","condition":"on dataset D, p<0.05","evidence_strength":"strong"}
{"source":"E2","predicate":"evaluated_by","target":"E5","evidence_strength":"strong"}
```

> 原文若只说"与基线比较"而未说更优，用 `compares` 而非 `outperforms`。
