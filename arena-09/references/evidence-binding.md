# 证据绑定（Evidence Binding）

每条断言绑定**最小充分证据**与**原文位置**。

## 最小充分性

- `evidence_text` 是真正支撑该断言的最小原文片段，不是整段复制、不是摘要。
- 判据：删去该片段中的任何一句，证据就不再充分。
- 证据不足（片段无法支撑断言）→ 标 `unverified`，不硬绑。仅这种状态允许 evidence 为空，最终脚本会留下 warning；必须在 `basis`/`uncertainties` 写明“证据缺失”，其他状态空 evidence 为 error。

## 直接 vs 间接

| 类型 | 判定 | 标注 |
|---|---|---|
| `direct` | 原文直接陈述该断言（含同义改写） | 直接引用原文 |
| `indirect` | 需要由原文推断（组合多处、逻辑推导） | 记录推断依据与步骤 |

- 间接推论必须在 `basis` 写明推导步骤，否则视为证据不足。

## 机械导出中的证据等价

Agent 只维护 record.evidence，不手工另写 evidence graph。exporter 原值映射 `evidence_text` / `evidence_location` / `evidence_type`；合法 `unverified` 空证据的三个 JSON-LD 值均为 `""`，但 evidence graph 与三键结构始终保留并产生 warning。最终 validator 复用 canonical 构造逐项比较，文本、位置或类型任一变化都失败；partial/unverified 不会因此获得豁免。

## 位置（Evidence Location）

- 格式：`page=N` + `§章节` + `¶段落` + `Fig./Table/Eq. 编号`（按可用粒度）。
- 指向**真正对应**的位置，不是笼统的"见正文"。
- 证据跨图表/跨段落 → 列出所有片段位置。
- 位置无法确定 → 标 `uncertain`，不伪造位置。

## 样例（示意）

```json
{
  "assertion": {"subject":"Treatment A","predicate":"reduces","object":"tumor size","condition":"by 30%, p<0.05, in mice"},
  "evidence": {
    "evidence_text": "Treatment A reduced tumor size by 30% (p<0.05) in mice",
    "evidence_location": "§3 ¶2",
    "evidence_type": "direct"
  }
}
```
