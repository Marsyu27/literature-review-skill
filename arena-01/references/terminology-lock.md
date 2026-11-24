# 术语表抽取、锁定与冲突处理（Terminology Lock）

## 抽取范围

1. 领域术语：出现 ≥2 次，或虽 1 次但属关键概念（标题/摘要/结论中）。
2. 缩写与全称：首现展开形式并存时，登记 `缩写 (全称)`；后续只用缩写。
3. 专有名词：人名、机构、算法/模型名、数据集名、软件名。
4. 度量单位：保持原单位，不换算。

## 字段

| 字段 | 含义 | 必填 |
|---|---|---|
| `term` | 原文术语的 canonical form | 是 |
| `aliases` | 同一概念的同义词/缩写/其他表面形式数组 | 否 |
| `context` | 多义项的语境正则字符串或正则数组；至少一项命中原文段落才采用该义 | 多义条目必填 |
| `translation` | 唯一译名（导出机读表时对应 `locked`） | 是 |
| `first_at` | 首次出现位置（段号） | 是 |
| `unified` | 是否全篇统一（true/false） | 是 |
| `note` | 冲突或特例说明 | 否 |

## 锁定规则

1. **一术语一译名**：标题、摘要、正文、图注、结论中同一术语必须用同一译名；发现漂移即回改。
2. **缩写首次展开**：原文首现为全称+缩写的，译文首次也展开，后续只用缩写。
3. **同义混用合并**：如 `efficiency` 与 `performance` 指同一量时，登记为一行：`term="performance"`、`aliases=["efficiency"]`，`translation` 取多数派译名，`note` 说明"原文混用，已按多数统一"。禁止再写成 `"performance / efficiency"` 单个字符串。
4. **术语表是冻结的**：后续翻译只能查表，不能新造译名；确需新增须回写术语表，并用 `scripts/check_terminology.py` 对全部 segments 机械重扫（回填/漂移/frozen 三项），**不依赖人工重读全篇**。

## 机读格式（terminology.json，供 check_terminology.py 强制核验）

术语表维护为上表的人类可读形式；交付前必须导出机读 `terminology.json`，每行一个术语：

| 字段 | 含义 | 必填 |
|---|---|---|
| `term` | 原文术语 canonical form（脚本按大小写不敏感、ASCII 词边界匹配 source） | 是 |
| `aliases` | 同概念其他原文表面形式数组；`term` 或任一 alias 命中都触发本条 `locked` 检查 | 否（缺省 `[]`） |
| `locked` | 唯一锁定译名；命中本条任一表面形式的段落，target 必须含 `locked` | 是 |
| `context` | 语境正则字符串或正则字符串数组，匹配 **source**；数组为 OR，至少一条命中才采用该义 | 同名多义条目必填 |
| `alternates` | 旧译/别译清单；target 出现其中任何一个即报漂移 warning | 否（缺省 `[]`） |
| `frozen` | `true` 时 `locked` 必须在 target **逐字**（区分大小写）出现，用于缩写、符号、专名 | 否（缺省 `false`） |

导出规则：`translation` → `locked`；同义表面形式 → `aliases`；多义语境 → `context`；`note` 中登记过的旧译/别译 → `alternates`；缩写与符号类条目 `frozen=true`。机器可读结构另见 `references/terminology.schema.json`。脚本报告有 error 即不得交付，修复后重跑至全绿。

**同名多义消歧（配置硬约束）**：
1. 多条目的 `term`/`aliases` 共享同一表面形式（忽略大小写）时，每条相关记录都必须有 `context`；任一条缺语境即报 `configuration_error`，退出 1，绝不会要求两个译名同时出现。
2. 逐段先匹配表面形式，再用 `context` 正则过滤。一个表面形式只能有一个候选执行回填/frozen/alternates；多个语境同时命中报 `ambiguous_context`，没有候选则该段不锁定。
3. `context` 是无效正则或不是字符串/字符串数组时同样属于配置错误。只有唯一术语的无语境简单记录继续按原规则工作。

## 冲突处理

- 原文术语本就不一致 → 以多数派为准，`uncertainties` 列出冲突点请人确认。
- 一词多义（按上下文取义不同）→ 术语表分两行登记（`term` 相同但 `context` 不同），`note` 写"上下文依赖"；不能只在自然语言 note 中注明而不配置正则。
- 无标准译名 → 给音译/意译，标"暂定译名"，放入 `uncertainties`。

## 样例（示意，非正式案例）

```json
[
  {"term": "thermal enhancement factor (TEF)", "locked": "热强化因子（TEF）", "frozen": true},
  {"term": "performance", "aliases": ["efficiency"], "locked": "效率", "alternates": ["效能"], "note": "同一量，两个原文表面形式均回填为效率"},
  {"term": "bank", "locked": "银行", "context": ["\\b(?:account|finance|financial|deposit)s?\\b"], "note": "金融语境"},
  {"term": "bank", "locked": "河岸", "context": ["\\b(?:river|stream|waterway)s?\\b"], "note": "河流语境"},
  {"term": "state-of-the-art", "locked": "当前最优", "alternates": ["最先进的"], "note": "旧式 term/locked/alternates 记录仍受支持"}
]
```
