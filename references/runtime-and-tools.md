# 运行环境与工具使用

## 输入定位（按优先级）

1. `/input/case.json`：案例主体，含研究问题、文献清单、`output_contract`，可能还有文献文件路径。
2. `/input/task.md`：任务说明与输入约束。
3. `environment/resources.yaml`：声明的文献、数据与预装工具清单。
4. 以上路径不存在时，在当前工作目录及 `/app`、`/workspace` 下查找同名文件；交互环境中直接询问用户输入位置。**不以文件名或目录标签推断内容，一律读取后判断。**

## 文献解析

- 文本型 PDF：用 `resources.yaml` 声明的 PDF 文本工具（如 pdf-text-tool）提取全文；提取结果为空或乱码时按扫描版处理。
- 扫描版/图片型 PDF：用 OCR 工具（如 ocr-tool）；OCR 后抽查一页确认可读，不可读则标该文献 `failed` 并说明影响。
- 关键图表：文本无法承载时用渲染工具（如 pdf-render-tool）出图后查看。
- 元数据：以 PDF 首页与题录为准；冲突时在 `sources` 注明两处不一致。

## 预算管理（64 次模型请求 / 900 秒量级）

- 请求预算分配参考：读输入与骨架 ≤10%，筛选 ≤20%，比较矩阵与证据行 ≤40%，主题与冲突 ≤10%，草稿 ≤15%，审计 ≥5%。
- 语料 ≤30 篇：纳入文献全部读全文。语料更大：先用题录/摘要做完整筛选，再对纳入者分批读全文，每批结束就地更新 `result.json`。
- 每次写文件前先想好全部内容一次写完，避免反复小改消耗请求。
- 骨架先行：`result.json` 在读完输入后立即落盘（`status: "in_progress"`），之后原地更新；任何时候中断都留有可评的部分结果。

## 输出位置

- 中间产物（矩阵草稿、分批提取）放 `/app/work`。
- 交付物放 `/app/output`：`result.json`、`review.md`、`evidence_matrix.md`；有可编辑 Office/图产物时另附真实渲染的 PDF/PNG 预览。
- 交付前运行 `scripts/validate_result.py result.json`；脚本为纯 Python 标准库，无第三方依赖。
