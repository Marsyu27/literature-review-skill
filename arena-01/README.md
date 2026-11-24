# scientific-literature-translation · 文献翻译 Skill

围绕真实科研论文翻译难点开发的、可被 Agent 调用的 Skill。核心纪律：**术语稳、段落全、关系准、可核验**。

## 用途

- 科研文献中英互译，产出段落级双语对照 + 冻结术语表 + 源文快照字符区间证据映射。
- 重点改善术语一致性、长文分段翻译、双语对照、译文核验（数字/单位/公式/图表公式引用/文献引用/否定/量词/因果守恒）。

## 文件结构

```
SKILL.md                                 # 主 Skill（入口，六步流程）
scripts/check_terminology.py             # aliases 回填、context 消歧、漂移/frozen 核验
scripts/check_conservation.py            # 数字/文献引用/单位量/公式/图表公式引用守恒
scripts/validate_translation_delivery.py # 快照/ID/区间/覆盖/契约/work-final 交付门禁
references/terminology-lock.md           # 术语抽取、term+aliases、context 冲突处理
references/terminology.schema.json       # terminology.json 的 JSON Schema
references/result.schema.json            # result.json 静态 JSON Schema
references/hedge-strength.md             # 限定词强度分级与守恒
references/bilingual-alignment.md        # 双语对照、段号和快照区间约定
references/translation-verification.md   # 译文核验清单
references/output-schema.md              # result.json 完整契约、区间示例与状态门禁
examples/translation-examples.md         # 标注为示例的对照及完整 success/partial 结构
src/reproduce.py                         # 真实 CLI 行为自检（全部产物在临时目录）
```

## 调用方式

加载 Skill 后，Agent 按 SKILL.md 六步流程：读输入→术语抽取冻结→**固化源文快照并带字符区间分段**→逐段双语对照→关系守恒检查→译文及交付核验→输出 result.json。

核验命令（路径按实际工作目录调整）：

```bash
python3 scripts/check_terminology.py --terms terminology.json --segments segments.json --report work/terminology-report.json
python3 scripts/check_conservation.py --segments segments.json --report work/conservation-report.json
python3 scripts/validate_translation_delivery.py --case case.json --source-text work/source-snapshot.txt --result result.json --work-segments segments.json --report work/delivery-report.json
```

- `success`：区间从 0 到快照末尾连续全覆盖；三个脚本均退出 0；无术语 drift/未知契约类型 warning；语义人工回核也完成，才是“所有检查全绿”。
- `partial`：仍核 ID 唯一、target 非空、快照逐字切片、合法递增且不重叠区间、可选 work/final 一致性。必须有非空 `status_reason` 和精确的 `uncovered_ranges`；未跑或失败的术语/守恒/语义核验都列为缺口。delivery 退出 0 只代表结构与覆盖声明合格，不表示译文质量全绿。
- 公式按多重集合比较，只规范化空白；`ln→lg`、上下标变化会失败。`Fig/Figure`↔`图`、`Table`↔`表`、`Eq/Equation`↔`公式/式` 可跨语言映射，但类型或编号变化会失败。相关项先掩码，避免编号重复计数。

## 输出契约

最终 result 必含 `case_id`、`status`、`status_reason`、`segments` 及 case.output_contract 的全部声明字段；默认还含 `source_lang`、`target_lang`、`terminology`、`uncertainties`。每个 segment 至少含：

```
id / source / target / source_start / source_end
```

`source` 必须逐字等于 `snapshot[source_start:source_end]`，下标是 Python Unicode 字符下标而非字节数。output_contract 可推断类型的字段会核基本类型；无法推断会明确 warning，success 不得带未解决 warning。详见 `references/output-schema.md` 和 `references/result.schema.json`。

## 最小调用示例（示意，非正式案例）

输入 `case.json`：`{"case_id":"demo","output_contract":{}}`。源文快照正好是 12 个字符：`Alpha.\nBeta.`，则首段（含换行）为 `[0,7)`，第二段为 `[7,12)`。完整 result：

```json
{
  "case_id": "demo",
  "status": "success",
  "status_reason": "",
  "source_lang": "en",
  "target_lang": "zh",
  "terminology": [],
  "segments": [
    {"id":"§1 ¶1","source":"Alpha.\n","target":"阿尔法。","source_start":0,"source_end":7,"basis":"快照 [0,7) 逐句翻译","status":"ok"},
    {"id":"§2 ¶1","source":"Beta.","target":"贝塔。","source_start":7,"source_end":12,"basis":"快照 [7,12) 逐句翻译","status":"ok"}
  ],
  "uncovered_ranges": [],
  "uncertainties": [],
  "tool_commands": ["实际执行的三条核验命令及报告路径"]
}
```

若第二段未译，不能用空 target 或继续报 success；应改为 partial，只保留第一段，并声明 `"uncovered_ranges":[{"source_start":7,"source_end":12}]`，同时写清原因和未执行核验。完整可复制的 partial 示例见 `examples/translation-examples.md`。

## 自检与依赖

```bash
python3 src/reproduce.py
```

自检通过 tempfile + subprocess 实测中英正向、缺段、partial、重复 ID、work/final 漂移、公式命令/上下标、图表类型和新增 20% 等退出码。所有 case、result、report 与 manifest 只写临时目录，结束清理 `__pycache__`，不在提交目录生成测试产物。

`scripts/` 三个核验脚本及 `src/reproduce.py` 仅用 Python 标准库；翻译由加载 Skill 的 LLM 执行，`references/` 提供规则。

## 异常处理与限制

- 残缺/模糊材料 → 标 uncertain/unable，不猜译；无法翻译段保留非空说明标记并诚实降级，公式/数字/引用不补造。
- 本 Skill 只做忠实翻译，不做研究结论判断。
