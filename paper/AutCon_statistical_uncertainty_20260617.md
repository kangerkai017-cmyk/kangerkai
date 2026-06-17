# Statistical uncertainty report

This report uses task-level metrics from completed experiment CSV files only. It does not infer results for unrun datasets.

## Inputs

| Dataset | Family | Metrics CSV |
|---|---|---|
| qwen46_benchmark | benchmark | `data/eval/experiments/full_bench_20260604_0335/metrics.csv` |
| deepseek46_benchmark | benchmark | `data/eval/experiments/deepseek_v4pro_full_bench_20260616/metrics.csv` |
| qwen46_ablation | ablation | `data/eval/experiments/full_ablation_20260604_0714/metrics.csv` |
| deepseek46_ablation | ablation | `data/eval/experiments/deepseek_v4pro_full_ablation_20260616/metrics.csv` |

## Bootstrap confidence intervals

Non-parametric bootstrap 95% confidence intervals are reported for group means.

### Benchmark `grounding_rate`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| qwen46_benchmark | proposed | 46 | 1.000 | [1.000, 1.000] |
| deepseek46_benchmark | proposed | 46 | 1.000 | [1.000, 1.000] |

### Benchmark `norm_recall_at_k`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| qwen46_benchmark | proposed | 46 | 0.674 | [0.522, 0.804] |
| deepseek46_benchmark | proposed | 46 | 0.674 | [0.543, 0.804] |

### Benchmark `norm_citation_validity`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| qwen46_benchmark | proposed | 46 | 0.152 | [0.112, 0.195] |
| deepseek46_benchmark | proposed | 46 | 0.146 | [0.109, 0.187] |

### Benchmark `link_resolution_rate`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| qwen46_benchmark | proposed | 46 | 0.393 | [0.342, 0.444] |
| deepseek46_benchmark | proposed | 46 | 0.390 | [0.332, 0.450] |

### Benchmark `elapsed_seconds`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| qwen46_benchmark | proposed | 46 | 67.837 | [65.836, 69.639] |
| deepseek46_benchmark | proposed | 46 | 21.663 | [20.942, 22.401] |

### Ablation `grounding_rate`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| qwen46_ablation | full | 46 | 1.000 | [1.000, 1.000] |
| qwen46_ablation | no_case_evidence | 46 | 1.000 | [1.000, 1.000] |
| qwen46_ablation | no_case_norm_linker | 46 | 1.000 | [1.000, 1.000] |
| deepseek46_ablation | full | 46 | 1.000 | [1.000, 1.000] |
| deepseek46_ablation | no_case_evidence | 46 | 1.000 | [1.000, 1.000] |
| deepseek46_ablation | no_case_norm_linker | 46 | 1.000 | [1.000, 1.000] |

### Ablation `norm_recall_at_k`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| qwen46_ablation | full | 46 | 0.674 | [0.543, 0.804] |
| qwen46_ablation | no_case_evidence | 46 | 0.073 | [0.014, 0.149] |
| qwen46_ablation | no_case_norm_linker | 46 | 0.073 | [0.014, 0.149] |
| deepseek46_ablation | full | 46 | 0.674 | [0.543, 0.804] |
| deepseek46_ablation | no_case_evidence | 46 | 0.073 | [0.014, 0.146] |
| deepseek46_ablation | no_case_norm_linker | 46 | 0.073 | [0.014, 0.146] |

### Ablation `norm_citation_validity`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| qwen46_ablation | full | 46 | 0.143 | [0.106, 0.182] |
| qwen46_ablation | no_case_evidence | 46 | 0.027 | [0.005, 0.053] |
| qwen46_ablation | no_case_norm_linker | 46 | 0.028 | [0.005, 0.054] |
| deepseek46_ablation | full | 46 | 0.147 | [0.110, 0.185] |
| deepseek46_ablation | no_case_evidence | 46 | 0.029 | [0.007, 0.057] |
| deepseek46_ablation | no_case_norm_linker | 46 | 0.026 | [0.004, 0.052] |

### Ablation `link_resolution_rate`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| qwen46_ablation | full | 46 | 0.365 | [0.314, 0.414] |
| qwen46_ablation | no_case_evidence | 46 | 0.000 | [0.000, 0.000] |
| qwen46_ablation | no_case_norm_linker | 46 | 0.000 | [0.000, 0.000] |
| deepseek46_ablation | full | 46 | 0.374 | [0.318, 0.428] |
| deepseek46_ablation | no_case_evidence | 46 | 0.000 | [0.000, 0.000] |
| deepseek46_ablation | no_case_norm_linker | 46 | 0.000 | [0.000, 0.000] |

### Ablation `elapsed_seconds`

| Dataset | Group | n | Mean | 95% CI |
|---|---:|---:|---:|---:|
| qwen46_ablation | full | 46 | 71.689 | [68.587, 75.462] |
| qwen46_ablation | no_case_evidence | 46 | 51.049 | [49.061, 53.061] |
| qwen46_ablation | no_case_norm_linker | 46 | 61.603 | [59.656, 63.477] |
| deepseek46_ablation | full | 46 | 19.704 | [18.714, 20.759] |
| deepseek46_ablation | no_case_evidence | 46 | 17.946 | [17.083, 18.828] |
| deepseek46_ablation | no_case_norm_linker | 46 | 19.039 | [18.160, 19.955] |

## Paired tests

Wilcoxon signed-rank tests use task-matched pairs. Holm-Bonferroni adjustment is applied within each metric and comparison scope. Cliff's delta is reported as a distributional effect-size descriptor.

### Within-dataset key comparisons

| Dataset | Metric | Reference | Comparator | n | Mean delta | p | Holm p | Cliff's delta |
|---|---|---|---|---:|---:|---:|---:|---:|
| qwen46_benchmark | `norm_citation_validity` | proposed | optimized | 46 | 0.152 | 0.0000 | 0.0000 | 0.674 |
| qwen46_benchmark | `norm_recall_at_k` | proposed | optimized | 46 | 0.546 | 0.0000 | 0.0000 | 0.559 |
| qwen46_benchmark | `link_resolution_rate` | proposed | optimized | 46 | 0.393 | 0.0000 | 0.0000 | 0.913 |
| deepseek46_benchmark | `norm_citation_validity` | proposed | optimized | 46 | 0.146 | 0.0000 | 0.0000 | 0.674 |
| deepseek46_benchmark | `norm_recall_at_k` | proposed | optimized | 46 | 0.546 | 0.0000 | 0.0000 | 0.559 |
| deepseek46_benchmark | `link_resolution_rate` | proposed | optimized | 46 | 0.390 | 0.0000 | 0.0000 | 0.870 |
| qwen46_ablation | `norm_citation_validity` | full | no_case_evidence | 46 | 0.116 | 0.0000 | 0.0000 | 0.539 |
| qwen46_ablation | `norm_recall_at_k` | full | no_case_evidence | 46 | 0.601 | 0.0000 | 0.0000 | 0.609 |
| qwen46_ablation | `link_resolution_rate` | full | no_case_evidence | 46 | 0.365 | 0.0000 | 0.0000 | 0.891 |
| qwen46_ablation | `norm_citation_validity` | full | no_case_norm_linker | 46 | 0.114 | 0.0000 | 0.0000 | 0.534 |
| qwen46_ablation | `norm_recall_at_k` | full | no_case_norm_linker | 46 | 0.601 | 0.0000 | 0.0000 | 0.609 |
| qwen46_ablation | `link_resolution_rate` | full | no_case_norm_linker | 46 | 0.365 | 0.0000 | 0.0000 | 0.891 |
| deepseek46_ablation | `norm_citation_validity` | full | no_case_evidence | 46 | 0.118 | 0.0000 | 0.0000 | 0.539 |
| deepseek46_ablation | `norm_recall_at_k` | full | no_case_evidence | 46 | 0.601 | 0.0000 | 0.0000 | 0.609 |
| deepseek46_ablation | `link_resolution_rate` | full | no_case_evidence | 46 | 0.374 | 0.0000 | 0.0000 | 0.870 |
| deepseek46_ablation | `norm_citation_validity` | full | no_case_norm_linker | 46 | 0.121 | 0.0000 | 0.0000 | 0.551 |
| deepseek46_ablation | `norm_recall_at_k` | full | no_case_norm_linker | 46 | 0.601 | 0.0000 | 0.0000 | 0.609 |
| deepseek46_ablation | `link_resolution_rate` | full | no_case_norm_linker | 46 | 0.374 | 0.0000 | 0.0000 | 0.870 |

### Cross-backend key comparisons

| Family | Group | Metric | Left | Right | n | Mean delta | p | Holm p |
|---|---|---|---|---|---:|---:|---:|---:|
| benchmark | proposed | `norm_citation_validity` | qwen46_benchmark | deepseek46_benchmark | 46 | 0.005 | 0.5508 | 1.0000 |
| benchmark | proposed | `norm_recall_at_k` | qwen46_benchmark | deepseek46_benchmark | 46 | 0.000 | 1.0000 | 1.0000 |
| benchmark | proposed | `link_resolution_rate` | qwen46_benchmark | deepseek46_benchmark | 46 | 0.003 | 0.7227 | 1.0000 |
| ablation | full | `norm_citation_validity` | qwen46_ablation | deepseek46_ablation | 46 | -0.004 | 0.3516 | 1.0000 |
| ablation | full | `norm_recall_at_k` | qwen46_ablation | deepseek46_ablation | 46 | 0.000 | 1.0000 | 1.0000 |
| ablation | full | `link_resolution_rate` | qwen46_ablation | deepseek46_ablation | 46 | -0.009 | 0.5675 | 1.0000 |
