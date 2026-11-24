# Nanopublication 断言样例（标注为示例，非正式案例）

> 以下 20 条均为**示意**，用于说明断言拆解、关系词表、证据绑定与来源元数据的格式，不冒充正式评测案例结果。

1. `(Treatment A, reduces, tumor size)` · 限定 `by 30%, p<0.05, in mice` · 证据 `§3 ¶2` · direct
2. `(Treatment A, improves, survival)` · 限定 `in mice` · 证据 `§3 ¶2` · direct
3. `(Gene G, expressed_in, tissue T)` · 证据 `§2 Fig.1` · direct
4. `(Protein P, binds_to, receptor R)` · 限定 `in vitro` · 证据 `§4 ¶1` · direct
5. `(Model M, measured_as, accuracy 0.81)` · 限定 `dataset D` · 证据 `§5 Table 2` · direct
6. `(Model M, increases, accuracy)` · 限定 `vs baseline 0.79, p<0.05` · 证据 `§5 Table 2` · direct
7. `(X, causes, Y)` · 证据 `§2 ¶3` · direct（原文明确因果）
8. `(X, is_associated_with, Y)` · 证据 `§4 ¶2` · direct（原文仅相关，不写因果）
9. `(Sample S, consists_of, n=1000 items)` · 证据 `§3 ¶1` · direct
10. `(Method M2, is_a, deep learning model)` · 证据 `§2 ¶1` · direct
11. `(Temperature T, measured_as, 4.2 K)` · 限定 `field 0.5 T` · 证据 `§4 Eq.(7)` · direct
12. `(Coherence length ξ, extracted_from, fit)` · 证据 `§4 ¶3` · indirect（由拟合提取，推断依据记录在 basis）
13. `(Result R, holds_under, condition C)` · 证据 `§5 ¶2` · direct（保留限定）
14. `(Drug D, improves, metric M)` · 限定 `in patients, n=200` · 证据 `§6 Table 3` · direct
15. `(Mechanism M3, proposes, pathway P)` · 证据 `§5 ¶1` · direct（作者提出的机制）
16. `(Result R2, conflicts_with, prior result R1)` · 证据 `§7 ¶2` · direct（原文自述与前人结果不一致）
17. `(Limitation L, applies_to, result R)` · 限定 `single-center sample` · 证据 `§8 ¶1` · direct
18. `(Variable V, defined_as, formula F)` · 证据 `§2 Eq.(1)` · direct
19. `(Claim C, supported_by, evidence E)` · 证据 `§6 ¶4` · indirect（组合多段证据，basis 写推导步骤）
20. `(Assertion A, uncertain_because, missing data)` · 证据缺失 · status=unverified · basis "原文未报告数值，无法判定"

## 说明

- 谓词（predicate）一律取自 `references/relation-vocabulary.md` 受控词表；无合适项时用最接近项并注明，或标 `uncertain`。
- 每条 `evidence_location` 指回真实位置；`indirect` 断言在 `basis` 写明推断步骤。
- 数值、单位、显著性、限定条件逐字保留。
