# 关系类型受控词表（Relation Vocabulary）

谓词（predicate）从本词表取值，**不自由发挥**；主体/客体方向必须准确。词表 = **核心 14 项（下表）+ 扩展 8 项（方法/证据/比较类，见末节）**，两节效力相同；两节之外一律不得自造。

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

## 扩展谓词（方法/证据/比较类）

覆盖论文的方法描述、证据链与比较陈述。使用规则与核心谓词相同：方向准确、不自由发挥。

| predicate | 含义 | 方向 | 适用场景 | 示例 |
|---|---|---|---|---|
| `extracted_from` | 由…提取/拟合得到 | 结果 → 方法/数据 | 数值或参数由拟合、回归、后处理间接得到，非原文直接陈述 | `(Coherence length ξ, extracted_from, fit)` |
| `holds_under` | 在…条件下成立 | 结论 → 条件 | 断言仅在特定条件/范围内成立，限定不可省略 | `(Result R, holds_under, condition C)` |
| `proposes` | 提出（机制/假说/模型） | 工作/机制 → 对象 | 作者提出的机制、模型或假说，尚未被证实 | `(Mechanism M3, proposes, pathway P)` |
| `conflicts_with` | 与…相冲突 | 结果 ↔ 结果 | 原文自述与前人/他处结果不一致，保留两处原文 | `(Result R2, conflicts_with, prior result R1)` |
| `applies_to` | 适用于/限定于 | 限定/范围 → 结论 | 局限性、适用范围对某结论的约束 | `(Limitation L, applies_to, result R)` |
| `defined_as` | 定义为 | 变量/术语 → 定义/公式 | 符号、变量、术语的显式定义 | `(Variable V, defined_as, formula F)` |
| `supported_by` | 由…支持 | 论断 → 证据 | 论断由一段或多段证据支撑（多段组合时 evidence_type=indirect，basis 写推导步骤） | `(Claim C, supported_by, evidence E)` |
| `uncertain_because` | 因…而无法判定 | 断言 → 原因 | 证据缺失或无法判断，配套 `status=unverified`，不硬绑 | `(Assertion A, uncertain_because, missing data)` |
