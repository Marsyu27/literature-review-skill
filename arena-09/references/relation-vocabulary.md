# 关系类型受控词表（Relation Vocabulary）

谓词（predicate）从下表取值，**不自由发挥**；主体/客体方向必须准确。

## 核心关系

| predicate | 含义 | 方向 |
|---|---|---|
| `causes` | 引起/导致 | A → B（A 是原因） |
| `increases` | 使…增加 | A → 某量 |
| `decreases` | 使…减少 | A → 某量 |
| `is_associated_with` | 与…相关（非因果） | A ↔ B |
| `correlates_with` | 与…相关 | A ↔ B |
| `improves` | 改善 | A → 指标 |
| `reduces` | 降低 | A → 指标 |
| `consists_of` | 由…组成 | 整体 → 部分 |
| `is_a` / `instance_of` | 属于/是…的实例 | 子 → 类 |
| `has_property` | 具有属性 | 主体 → 属性 |
| `measured_as` | 测量值为 | 变量 → 数值 |
| `located_in` | 位于 | 主体 → 位置 |
| `binds_to` | 结合到 | 分子 → 靶点 |
| `expressed_in` | 在…中表达 | 基因 → 组织 |

## 规则

1. **方向准确**：`X causes Y` 与 `Y causes X` 完全不同；`A increases B` 主体是 A。
2. **因果 vs 相关**：`associated with` / `correlates with` 不得写成 `causes`；反向也不得。
3. **无合适词表项** → 用最接近项并在 `note` 说明，或标 `uncertain`，不造新关系。
4. 客体是数值时用 `measured_as` / `has_property`，不把数值当主体。

## 主体/客体规范化

- 主体、客体用规范化术语（缩写与全称统一），与术语表一致。
- 主体混淆（同一段里两个候选主体）→ 标 `uncertain`，不猜测。
