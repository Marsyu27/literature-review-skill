# 术语表抽取、锁定与冲突处理（Terminology Lock）

## 抽取范围

1. 领域术语：出现 ≥2 次，或虽 1 次但属关键概念（标题/摘要/结论中）。
2. 缩写与全称：首现展开形式并存时，登记 `缩写 (全称)`；后续只用缩写。
3. 专有名词：人名、机构、算法/模型名、数据集名、软件名。
4. 度量单位：保持原单位，不换算。

## 字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `term` | 原文术语（或缩写/同义表达） | 是 |
| `translation` | 唯一译名 | 是 |
| `first_at` | 首次出现位置（段号） | 是 |
| `unified` | 是否全篇统一（true/false） | 是 |
| `note` | 冲突或特例说明 | 否 |

## 锁定规则

1. **一术语一译名**：标题、摘要、正文、图注、结论中同一术语必须用同一译名；发现漂移即回改。
2. **缩写首次展开**：原文首现为全称+缩写的，译文首次也展开，后续只用缩写。
3. **同义混用合并**：如 `efficiency` 与 `performance` 指同一量时，登记为一行，`translation` 取多数派译名，`note` 说明"原文混用，已按多数统一"。
4. **术语表是冻结的**：后续翻译只能查表，不能新造译名；确需新增须回写术语表，并用 `scripts/check_terminology.py` 对全部 segments 机械重扫（回填/漂移/frozen 三项），**不依赖人工重读全篇**。

## 机读格式（terminology.json，供 check_terminology.py 强制核验）

术语表维护为上表的人类可读形式；交付前必须导出机读 `terminology.json`，每行一个术语：

| 字段 | 含义 | 必填 |
|---|---|---|
| `term` | 原文术语（脚本按大小写不敏感、ASCII 词边界匹配 source） | 是 |
| `locked` | 唯一锁定译名；source 含 `term` 的段落，target 必须含 `locked` | 是 |
| `alternates` | 旧译/别译清单；target 出现其中任何一个即报漂移 warning | 否（缺省 `[]`） |
| `frozen` | `true` 时 `locked` 必须在 target **逐字**（区分大小写）出现，用于缩写、符号、专名 | 否（缺省 `false`） |

导出规则：`translation` → `locked`；`note` 中登记过的旧译/别译 → `alternates`；缩写与符号类条目 `frozen=true`。脚本报告有 error 即不得交付，修复后重跑至全绿。

## 冲突处理

- 原文术语本就不一致 → 以多数派为准，`uncertainties` 列出冲突点请人确认。
- 一词多义（按上下文取义不同）→ 术语表分两行登记（`term` 相同但注明语境），`note` 写"上下文依赖"。
- 无标准译名 → 给音译/意译，标"暂定译名"，放入 `uncertainties`。

## 样例（示意，非正式案例）

```json
[
  {"term": "thermal enhancement factor (TEF)", "translation": "热强化因子（TEF）", "first_at": "§1 ¶2", "unified": true},
  {"term": "state-of-the-art", "translation": "当前最优", "first_at": "§1 ¶1", "unified": true, "note": "原文 3 处连字符、2 处空格，按多数统一"},
  {"term": "performance / efficiency", "translation": "效率", "first_at": "§2 ¶1", "unified": false, "note": "原文混用，需人工确认是否同一量"}
]
```
