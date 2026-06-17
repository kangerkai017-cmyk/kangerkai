# DeepSeek v4pro 58-task expanded validation report

This report covers the expanded benchmark after the accident corpus was increased to 88 cases, 176 accident-case chunks, and 58 deterministic training tasks. It is a DeepSeek v4pro single-backend validation and should not be pooled with the older 46-task Qwen/DeepSeek two-backend results.

Key completed outputs:

- Benchmark: `data/eval/experiments/deepseek_v4pro_58task_full_bench_20260617/`
- Ablation: `data/eval/experiments/deepseek_v4pro_58task_full_ablation_20260617/`
- Statistical tables: `data/eval/experiments/deepseek_v4pro_58task_statistical_uncertainty_20260617/`

Key benchmark result: the proposed method achieved grounding 1.000, norm citation validity 0.141, hazard coverage 0.280, case relevance 0.320, norm recall at k 0.586, link resolution 0.349, and mean elapsed time 21.5 s over 58 tasks. Optimized RAG reached norm recall at k 0.106 and link resolution 0.000 on the same task set.

Temporary-electricity subset: the proposed method achieved norm recall at k 0.235 and link resolution 0.281 over 17 temporary-electricity tasks; on the 13 Tier-S temporary-electricity tasks, it achieved norm recall at k 0.308 and link resolution 0.314.

The local Qwen expanded benchmark attempts are not included because they were partial invalid runs with truncation or malformed-output failures. They are archived as failure records at `data/eval/experiments/qwen35_58task_full_bench_20260617_INVALID_truncated_partial/` and `data/eval/experiments/qwen35_58task_full_bench_20260617_INVALID_raw_partial_no_summary/`.

## Statistical uncertainty

This report uses task-level metrics from completed experiment CSV files only. It does not infer results for unrun datasets.

## Inputs

| Dataset | Family | Metrics CSV |
|---|---|---|
| deepseek58_benchmark | benchmark | `data/eval/experiments/deepseek_v4pro_58task_full_bench_20260617/metrics.csv` |
| deepseek58_ablation | ablation | `data/eval/experiments/deepseek_v4pro_58task_full_ablation_20260617/metrics.csv` |

## Bootstrap confidence intervals

Non-parametric bootstrap 95% confidence intervals are reported for group means.

### Benchmark `grounding_rate`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| deepseek58_benchmark | proposed | 58 | 1.000 | [1.000, 1.000] |

### Benchmark `norm_recall_at_k`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| deepseek58_benchmark | proposed | 58 | 0.586 | [0.465, 0.707] |

### Benchmark `norm_citation_validity`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| deepseek58_benchmark | proposed | 58 | 0.141 | [0.105, 0.180] |

### Benchmark `link_resolution_rate`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| deepseek58_benchmark | proposed | 58 | 0.349 | [0.295, 0.402] |

### Benchmark `elapsed_seconds`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| deepseek58_benchmark | proposed | 58 | 21.455 | [20.866, 22.050] |

### Ablation `grounding_rate`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| deepseek58_ablation | full | 58 | 1.000 | [1.000, 1.000] |
| deepseek58_ablation | no_case_evidence | 58 | 1.000 | [1.000, 1.000] |
| deepseek58_ablation | no_case_norm_linker | 58 | 1.000 | [1.000, 1.000] |

### Ablation `norm_recall_at_k`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| deepseek58_ablation | full | 58 | 0.586 | [0.461, 0.707] |
| deepseek58_ablation | no_case_evidence | 58 | 0.063 | [0.017, 0.122] |
| deepseek58_ablation | no_case_norm_linker | 58 | 0.063 | [0.017, 0.122] |

### Ablation `norm_citation_validity`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| deepseek58_ablation | full | 58 | 0.147 | [0.110, 0.184] |
| deepseek58_ablation | no_case_evidence | 58 | 0.027 | [0.008, 0.050] |
| deepseek58_ablation | no_case_norm_linker | 58 | 0.028 | [0.008, 0.052] |

### Ablation `link_resolution_rate`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| deepseek58_ablation | full | 58 | 0.377 | [0.319, 0.435] |
| deepseek58_ablation | no_case_evidence | 58 | 0.000 | [0.000, 0.000] |
| deepseek58_ablation | no_case_norm_linker | 58 | 0.000 | [0.000, 0.000] |

### Ablation `elapsed_seconds`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| deepseek58_ablation | full | 58 | 17.823 | [17.217, 18.429] |
| deepseek58_ablation | no_case_evidence | 58 | 15.499 | [14.991, 16.002] |
| deepseek58_ablation | no_case_norm_linker | 58 | 17.291 | [16.734, 17.837] |

## Paired tests

Wilcoxon signed-rank tests use task-matched pairs. Holm-Bonferroni adjustment is applied within each metric and comparison scope. Cliff's delta is reported as a distributional effect-size descriptor.

### Within-dataset key comparisons

| Dataset | Metric | Reference | Comparator | n | Mean delta | p | Holm p | Cliff's delta |
|---|---|---|---|---:|---:|---:|---:|---:|
| deepseek58_benchmark | `norm_citation_validity` | proposed | optimized | 58 | 0.141 | 0.0000 | 0.0000 | 0.621 |
| deepseek58_benchmark | `norm_recall_at_k` | proposed | optimized | 58 | 0.481 | 0.0000 | 0.0000 | 0.510 |
| deepseek58_benchmark | `link_resolution_rate` | proposed | optimized | 58 | 0.349 | 0.0000 | 0.0000 | 0.810 |
| deepseek58_ablation | `norm_citation_validity` | full | no_case_evidence | 58 | 0.120 | 0.0000 | 0.0000 | 0.502 |
| deepseek58_ablation | `norm_recall_at_k` | full | no_case_evidence | 58 | 0.523 | 0.0000 | 0.0000 | 0.554 |
| deepseek58_ablation | `link_resolution_rate` | full | no_case_evidence | 58 | 0.377 | 0.0000 | 0.0000 | 0.828 |
| deepseek58_ablation | `norm_citation_validity` | full | no_case_norm_linker | 58 | 0.118 | 0.0000 | 0.0000 | 0.499 |
| deepseek58_ablation | `norm_recall_at_k` | full | no_case_norm_linker | 58 | 0.523 | 0.0000 | 0.0000 | 0.554 |
| deepseek58_ablation | `link_resolution_rate` | full | no_case_norm_linker | 58 | 0.377 | 0.0000 | 0.0000 | 0.828 |
