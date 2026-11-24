# 译文核验清单（Translation Verification）

每段译文产出后，逐项回核。**任何一项对不上，先标注、不硬改。**

## 必查项

| # | 检查点 | 判定 |
|---|---|---|
| 1 | 术语一致性 | 与术语表译名一致，标题/摘要/正文/图注/结论统一 |
| 2 | 数字 | 数值、正负号（含 Unicode −）、小数、千分位、`10^-3` 指数与 `1e-3` 科学计数**逐字**一致；既不得 missing，也不得 added |
| 3 | 单位 | 单位符号原样（`K`、`T`、`µm`、`mol/L`），不换算不改写 |
| 4 | 公式 | `$...$`、`$$...$$`、`\(...\)`、`\[...\]` 公式多重集合只规范化空白；`ln→lg`、上下标、运算符或希腊字母变化均失败 |
| 5 | 公式/图表引用类型+编号 | `Fig/Figure/图`、`Table/表`、`Eq/Equation/公式/式` 可跨语言映射；编号必须不变，Fig.2→Table2、图2→表2均失败 |
| 6 | 文献引用 | `[12]`、`(Smith, 2020)` 指向不变 |
| 7 | 否定范围 | `not all / only if / unless / except` 范围等价 |
| 8 | 量词 | `some / most / all / at least / up to` 量级不变 |
| 9 | 因果 vs 让步 | because/causes 与 although/despite 不互换 |
| 10 | 指代 | this/these/it/该/其 指代对象与原文一致 |
| 11 | 限定强度 | 按 hedge-strength.md，强度不升级、降级需记录 |
| 12 | 完整性 | 不漏段、不重复、不错位，段号一一对应 |

## 核验输出与交付门禁

- 每段在 `basis` 里写核验结论（“数字/单位/公式已逐字核对”），并用 `source_start/source_end` 指回唯一源文快照。
- 无法确定 → 标 `status=uncertain` 并写入 `uncertainties`，附“需人工确认”清单。
- 完全译不出 → 标 `status=unable`，保留原文 + 渲染图路径，target 写非空原因标记，不猜译、不用空字符串占位。
- success 要求全覆盖且术语、守恒、交付三个脚本全绿，人工语义回核也完成；partial 仍须核结构、快照、区间、覆盖及 work/final 漂移，并精确声明 `uncovered_ranges`，未做的语义核验必须写入 `status_reason` / `uncertainties`。

## 需人工确认清单（uncertainties 模板）

```json
[
  "§3 ¶2 术语 'coherence length' 在原文两处分别指不同量，译名待确认",
  "§5 ¶1 公式 (7) 的求积上限无法从文字层确定（∞ 或 n）",
  "§4 ¶3 图 2 坐标轴刻度为扫描图，未可靠识别"
]
```
