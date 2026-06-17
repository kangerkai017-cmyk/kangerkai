# AutCon 投稿完成计划

最后更新：2026-06-17

本文档是 `paper/Automation_in_Construction_full_draft.md` 的“实验与证据补强清单”。投稿立场、章节结构、字数、参考文献格式、作者信息、图件导出、数据与许可审查等通用投稿审计事项，统一保留在 `paper/Automation_in_Construction_submission_audit.md`。本文件只记录仍需补强的证据缺口，以及防止计划性或模拟性内容进入正式稿的验收闸门。

## 当前真实状态

- 正式投稿稿：
  `paper/Automation_in_Construction_full_draft.md`。
- 模拟预览稿：
  `paper/Automation_in_Construction_full_draft_SIMULATED_NOT_FOR_SUBMISSION.md`。
  该文件已明确标注为模拟预览稿，不得投稿、引用，或描述为已经完成的真实实验。
- 正式稿中的原始已完成模型后端：
  `Qwen3.5-9B-Q5_K_M`，通过本地 OpenAI-compatible server `localhost:51000` 运行。
- 原始 Qwen 真实实验结果，详细信息见 `paper/Automation_in_Construction_submission_audit.md`：
  - `data/eval/experiments/full_bench_20260604_0335/`
  - `data/eval/experiments/full_ablation_20260604_0714/`
  - 46 个任务、230 次 baseline run、276 次 ablation run。
- 主 46-task 双后端实验使用的语料证据：
  - 23 部规范，1,791 个 regulation chunks。
  - 76 个事故案例，152 个 accident-case chunks。
- 当前扩库后语料证据：
  - 23 部规范，1,791 个 regulation chunks。
  - 88 个事故案例，176 个 accident-case chunks。
  - 58 个 deterministic training tasks，其中 temporary electricity 17 个，temporary electricity Tier-S 13 个。
- 当前 `.env` 中的 DeepSeek 配置：
  - `OPENAI_BASE_URL=https://api.deepseek.com`
  - `LLM_MODEL=deepseek-v4-pro`
- DeepSeek v4pro 真实实验状态：
  - smoke test 已完成：
    `data/eval/experiments/deepseek_v4pro_smoke_20260616/`
  - 46-task full benchmark 已完成：
    `data/eval/experiments/deepseek_v4pro_full_bench_20260616/`
  - 46-task full ablation 已完成：
    `data/eval/experiments/deepseek_v4pro_full_ablation_20260616/`
  - Qwen3.5-9B 与 DeepSeek v4pro 对比报告已完成：
    `paper/AutCon_deepseek_qwen_comparison_20260616.md`
  - 正式稿已更新 DeepSeek v4pro 结果，并明确写明实际模型别名 `deepseek-v4-pro`。DeepSeek 结果应作为第二模型后端单独列出，不得与 Qwen 结果混合统计。
- 扩库后 58-task DeepSeek v4pro 真实实验状态：
  - 58-task full benchmark 已完成：
    `data/eval/experiments/deepseek_v4pro_58task_full_bench_20260617/`
  - 58-task full ablation 已完成：
    `data/eval/experiments/deepseek_v4pro_58task_full_ablation_20260617/`
  - 58-task 统计与扩库报告已完成：
    `paper/AutCon_deepseek_v4pro_58task_expanded_validation_20260617.md`
    `data/eval/experiments/deepseek_v4pro_58task_statistical_uncertainty_20260617/`
  - 该结果为 DeepSeek v4pro 单后端扩库验证，不得与 46-task Qwen/DeepSeek 双后端主结果混合平均。
- 扩库后 Qwen3.5-9B-Q5_K_M 真实实验状态：
  - 58-task full benchmark 尝试已中止并标记无效：
    `data/eval/experiments/qwen35_58task_full_bench_20260617_INVALID_truncated_partial/`
    `data/eval/experiments/qwen35_58task_full_bench_20260617_INVALID_raw_partial_no_summary/`
  - 失败模式：检索型变体出现 `LLM output truncated for TrainingOutput; finish_reason=length`，另有 partial run 只生成 `raw_results.jsonl` 而缺少 `metrics.csv`、`summary.json` 和 `metadata.json`；早期 run 延迟约 150-180 s/variant。
  - 这些目录只作为失败记录，不得进入正式统计或正文结果。
- 当前仓库状态：
  - 工作区存在 `.git` 目录项，但在当前环境中不可作为有效 Git 仓库读取。因此实验元数据应在可用时记录 Git commit；不可用时记录 `git_unavailable`，并同时记录任务文件 hash 和脚本 hash。

## 已完成且可写入正式稿的事项

### P0：证据边界保护

- 正式稿只保留真实完成的实验。
- 不得把模拟稿中的 verifier、专家评估、bootstrap 区间、模拟多模型数据写成正式结果。
- 模拟稿继续保留醒目的 `SIMULATED` 和 `NOT FOR SUBMISSION` 标识。
- DeepSeek v4pro 已完成真实运行，可作为正式结果写入正文；但必须与 Qwen3.5-9B-Q5_K_M 分列报告，不做混合平均。
- DeepSeek v4pro 58-task 扩库验证已完成，可作为补充结果写入正文；但必须标注为单后端 expanded validation。
- Qwen 58-task partial run 为无效失败记录，不得写成结果。

### P0：DeepSeek v4pro 连通性验证

状态：已于 2026-06-16 完成。

目的：确认 API 连通性、JSON 输出兼容性、token 上限、thinking 禁用参数、错误重试与 fallback 行为是否满足后续实验需要。

实际 smoke test 输出目录：

```text
data/eval/experiments/deepseek_v4pro_smoke_20260616/
```

运行模板：

```bash
python scripts/run_benchmark.py \
  --limit 2 \
  --variants optimized proposed \
  --output data/eval/experiments/deepseek_v4pro_smoke_YYYYMMDD
```

验收结果：

- `raw_results.jsonl` 已生成。
- `metrics.csv` 已生成。
- `summary.json` 已生成。
- `metadata.json` 已生成。
- 未出现 JSON 解析崩溃。
- DeepSeek v4pro 的模型别名确认为 `deepseek-v4-pro`。
- smoke test 独立保存，未覆盖旧 Qwen 结果目录。

### P0：DeepSeek v4pro 46-task 正式对比实验

状态：已于 2026-06-16 完成。

已完成输出：

- `data/eval/experiments/deepseek_v4pro_full_bench_20260616/raw_results.jsonl`
- `data/eval/experiments/deepseek_v4pro_full_bench_20260616/metrics.csv`
- `data/eval/experiments/deepseek_v4pro_full_bench_20260616/summary.json`
- `data/eval/experiments/deepseek_v4pro_full_bench_20260616/metadata.json`
- `data/eval/experiments/deepseek_v4pro_full_ablation_20260616/metrics.csv`
- `data/eval/experiments/deepseek_v4pro_full_ablation_20260616/summary.json`
- `data/eval/experiments/deepseek_v4pro_full_ablation_20260616/metadata.json`
- `paper/AutCon_deepseek_qwen_comparison_20260616.md`

正文使用边界：

- 可写为真实第二后端实验。
- 可写为“DeepSeek v4pro 复现了 case-to-norm linking 的 norm recall 和 link-resolution 趋势”。
- 不应写为“证明所有模型均可泛化”，因为目前只有 Qwen3.5-9B-Q5_K_M 与 DeepSeek v4pro 两个后端。
- 不应写为“解决了 citation validity 问题”，因为 DeepSeek v4pro 下 `norm_citation_validity` 仍较低。

### P0：实验元数据补强

状态：已对新 DeepSeek 实验输出补充。

新输出中的 `metadata.json` 已记录：

- 模型名：`LLM_MODEL`
- base URL 域名：只记录 `api.deepseek.com`，不记录凭据。
- 运行时间戳。
- 命令行参数。
- 任务文件路径与 hash。
- 脚本 hash。
- Git 状态，不可用时记录 `git_unavailable`。
- 关键环境开关。
- Python 与平台信息。

该设计用于避免后续混淆 Qwen 与 DeepSeek 结果。

### P1：正式稿已完成的对应更新

状态：已完成。

正式稿 `paper/Automation_in_Construction_full_draft.md` 已更新：

- Abstract 中加入 Qwen3.5-9B-Q5_K_M 与 DeepSeek v4pro 两后端结果。
- 4.2 中写明 DeepSeek v4pro 的实际配置：`LLM_MODEL=deepseek-v4-pro` 与 `OPENAI_BASE_URL=https://api.deepseek.com`。
- 表 1 改为 Qwen3.5-9B-Q5_K_M 与 DeepSeek v4pro 分列。
- 表 2 和表 3 加入 DeepSeek v4pro 的 tier/theme 结果。
- 表 4 加入 DeepSeek v4pro 的 ablation 结果。
- Runtime、Failure modes、Discussion、Conclusion 已同步改为双后端表述。
- 已删除或替换“single local LLM backend”这类过时表述。
- 仍保留专家评估、统计复跑、citation verifier、arbitration stress test 未完成的边界。

## 还不能写成正式结果但必须补

### P0：真实专家评估

在声称训练材料的实用性或合规充分性之前，必须完成真实专家评估。

最低要求：

- 招募 2-3 位施工安全、安全工程或现场管理专家。
- 每位专家盲评 20-30 份系统输出。
- 评分项至少包括：
  - usefulness
  - compliance adequacy
  - traceability
  - clarity
  - misleading risk
- 计算评分一致性，例如 ICC 或 Krippendorff's alpha。
- 真实评估完成并归档前，专家评分不得进入正式稿。

### P0：统计不确定性

状态：部分完成。

已完成：

- 对既有 46-task Qwen/DeepSeek 真实结果完成 task-level bootstrap 95% CI、paired Wilcoxon、Cliff's delta 和 Holm-Bonferroni 校正：
  - `paper/AutCon_statistical_uncertainty_20260617.md`
  - `data/eval/experiments/statistical_uncertainty_20260617/`
- 对 58-task DeepSeek v4pro 扩库结果完成同类统计：
  - `paper/AutCon_deepseek_v4pro_58task_expanded_validation_20260617.md`
  - `data/eval/experiments/deepseek_v4pro_58task_statistical_uncertainty_20260617/`

仍未完成：

- 严格意义上的 repeated-run variance：每个关键配置 3-5 次独立复跑尚未完成。
- 因此正文可以报告 task-level bootstrap CI 和 paired tests，但不得写成多次随机复跑的运行方差。

### P0：citation verifier 真实实现

当前只有 verifier 设计计划，尚未完成真实实现和实验。

建议新增后处理变体：`proposed+verifier`。

约束：

- verifier 只能在当前 run 已检索或已链接的 norm evidence 内重排、删除或替换 citation。
- 不得检索新证据。
- 不得编造 standard name、article ID、chunk ID 或条文内容。
- 证据不足时应标记 insufficiency，不得伪造替代引用。

主要指标：

- `norm_citation_validity`
- `grounding_rate`
- `link_resolution_rate`
- runtime/latency
- verifier 修改次数

### P1：arbitration stress test

在声称 arbitration 能提升困难场景下的安全性之前，必须构造压力测试。

建议：

- 构造 24-30 个 stress tasks。
- 覆盖 evidence-insufficient cases。
- 覆盖 hallucinated-citation pressure。
- 覆盖 norm-case conflict。
- 报告 route accuracy、safe-release rate、human-review flag rate 和 unnecessary-retry rate。

### P1：no-deterministic-grounding 对抗测试

在强声称 deterministic grounding 的价值之前，必须补充对抗任务。

建议：

- 构造诱导模型引用非法 `chunk_id`、不存在条款或看似合理但语料中不存在规范要求的任务。
- 比较 grounded 与 no-grounding 条件下的 invalid-citation rate 和 unsupported-clause rate。

### P1：任务集扩充

状态：已完成第一阶段扩充。

已完成：

- 事故案例从 76 个扩到 88 个。
- accident-case chunks 从 152 个扩到 176 个。
- deterministic training tasks 从 46 个扩到 58 个。
- temporary electricity 从 2 个任务扩到 17 个任务，其中 Tier-S 13 个。
- DeepSeek v4pro 已完成 58-task benchmark 和 ablation。

边界：

- 当前扩库规模仍低于原建议的 80-100 个任务，因此不应写成最终全主题 benchmark。
- temporary electricity 已不再是 2-task anecdote，但仍应写成 expanded diagnostic/theme-level validation，而不是最终泛化结论。
- 本地 Qwen 58-task 仍需修复截断后再复跑，当前无有效 Qwen 58-task 数字。

### P2：投稿格式与作者信息

不要在本文件重复完整编辑清单。以下事项统一在 `paper/Automation_in_Construction_submission_audit.md` 中跟踪：

- 作者、单位、通讯作者信息。
- Funding、Acknowledgements、CRediT roles。
- 图件导出、编号和分辨率检查。
- 参考文献格式、标点、作者缩写、DOI 格式。
- Markdown 转 Word 或 LaTeX 投稿格式。
- 标准与事故报告文本的数据许可和再分发限制。

本文件只在这些事项影响实验 claim 或证据边界时更新。

## DeepSeek v4pro 实验路线状态

### Stage A：连通性验证

状态：已完成。

输出目录：

```text
data/eval/experiments/deepseek_v4pro_smoke_20260616/
```

验收：

- 无 API authentication/model-name failure。
- 无 JSON parsing crash。
- 无 truncation-induced schema failure。
- `raw_results.jsonl`、`metrics.csv`、`summary.json`、`metadata.json` 均存在。
- metadata 记录 `deepseek-v4-pro` 和 `api.deepseek.com`。

### Stage B：Tier-S 小样本

状态：由 full benchmark 覆盖。

原目标：

- 运行 `optimized` 与 `proposed`。
- verifier 完成后再运行 `proposed+verifier`。
- 确认 DeepSeek v4pro 下 norm recall 与 link resolution 趋势是否保持。

当前结论：

- full benchmark 已确认 DeepSeek v4pro 下 `proposed` 保持 `norm_recall_at_k = 0.674`。
- Tier-S 下 DeepSeek v4pro 的 `norm_recall_at_k = 0.939`。
- verifier 尚未实现，因此 `proposed+verifier` 未完成。

### Stage C：46-task 全量

状态：已完成。

结论：

- DeepSeek v4pro full benchmark：230/230 runs 成功。
- DeepSeek v4pro full ablation：276/276 runs 成功。
- 结果未覆盖旧 Qwen 目录。
- 已生成 Qwen3.5-9B-Q5_K_M 与 DeepSeek v4pro 对比报告。

### Stage D：统计不确定性与扩库验证

状态：部分完成。

已完成：

- 46-task Qwen/DeepSeek task-level bootstrap CI 与 paired tests。
- 58-task DeepSeek expanded validation benchmark：290/290 runs 成功。
- 58-task DeepSeek expanded validation ablation：348/348 runs 成功。
- 58-task DeepSeek task-level bootstrap CI 与 paired tests。

仍未完成：

- 核心配置 3-5 次独立重复复跑。
- Qwen 58-task 有效复跑；当前 partial run 因截断无效。

### Stage E：正式稿更新

状态：部分完成。

已完成：

- DeepSeek v4pro 作为真实第二后端已写入正式稿。
- Qwen 与 DeepSeek 结果已分列，而非混合统计。
- 结果边界已同步到 Discussion 和 Conclusion。
- DeepSeek 58-task expanded validation 已写入正式稿补充小节。
- task-level bootstrap CI 和 paired tests 已形成补充报告，正文只引用完成的真实 metrics。

未完成：

- verifier 真实结果尚未写入，因为 verifier 尚未实现和测试。
- 专家评估尚未写入，因为真实盲评尚未完成。
- repeated-run 方差尚未写入，因为 3-5 次独立重复复跑尚未完成。
- arbitration stress test 尚未写入，因为压力测试集尚未构造。

## 投稿前验收标准

### 文档闸门

- `paper/AutCon_completion_plan.md` 存在。
- 本文件不包含 API key 或 credential。
- 正式稿和模拟稿保持分离。
- 正式稿不得把模拟 verifier、bootstrap、专家评估或 stress test 写成真实结果。
- 模拟稿继续保留醒目的 `NOT FOR SUBMISSION` 标识。

### 实验输出闸门

正式 benchmark 实验目录应包含：

- `raw_results.jsonl`
- `metrics.csv`
- `summary.json`
- `metadata.json` 或等价 metadata manifest
- command line 与环境开关记录
- task-file hash

说明：

- 当前 ablation runner 的既有输出模式不生成 `raw_results.jsonl`，DeepSeek ablation 也沿用这一模式，只生成 `metrics.csv`、`summary.json` 和 `metadata.json`。

### 正文闸门

- Highlights 每条不超过期刊要求的字符限制。
- Abstract、Results、Discussion、Conclusion 的 claim 保持一致。
- `grounding_rate = 1.000` 必须解释为 deterministic provenance control，不是 semantic correctness。
- temporary electricity 已扩到 17 tasks；应标注为 expanded diagnostic/theme-level validation，不得写成最终泛化结论。
- query rewriting 和 arbitration 应写为 bounded support mechanisms，不应写成主要平均性能来源。
- 参考文献排序和期刊格式通过 `paper/Automation_in_Construction_submission_audit.md` 检查；本文件只跟踪其是否影响 claim framing。

### 证据闸门

- DeepSeek v4pro 结果已经完成，可作为真实结果写入。
- 专家评分必须等真实盲评完成后才能写入。
- task-level bootstrap 置信区间和 paired tests 已可引用；repeated-run variance 必须等独立复跑完成后才能写入。
- arbitration benefit 的强 claim 必须等 stress test 完成后才能写入。
- deterministic grounding 的强 claim 必须等 adversarial no-grounding 任务完成后才能写入。

## 优先级汇总

- P0：
  - citation verifier 设计、实现与真实实验；
  - 重复运行方差；
  - 真实专家评估；
  - 正式稿与模拟稿严格分离。
- P1：
  - arbitration stress test；
  - no-deterministic-grounding adversarial test；
  - Qwen 58-task 截断修复与有效复跑；
  - 进一步扩充到 80-100 tasks 后的最终主题级 benchmark。
- P2：
  - citation-density cleanup；
  - Abstract framing 的最终投稿版压缩；
  - 参考文献、图件、格式等仅在影响证据表述时由本文件跟踪，否则统一放在 `paper/Automation_in_Construction_submission_audit.md`。
