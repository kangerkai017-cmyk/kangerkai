# DeepSeek v4pro vs Qwen3.5-9B comparison

Date: 2026-06-16

This report compares the existing Qwen3.5-9B-Q5_K_M experiments with the new
DeepSeek v4pro experiments over the same 46-task benchmark. The DeepSeek runs
used the current `.env` backend configuration:

- model: `deepseek-v4-pro`
- base URL domain: `api.deepseek.com`

## Experiment directories

| Role | Qwen3.5-9B-Q5_K_M | DeepSeek v4pro |
|---|---|---|
| Full benchmark | `data/eval/experiments/full_bench_20260604_0335/` | `data/eval/experiments/deepseek_v4pro_full_bench_20260616/` |
| Ablation | `data/eval/experiments/full_ablation_20260604_0714/` | `data/eval/experiments/deepseek_v4pro_full_ablation_20260616/` |
| Smoke test | not applicable | `data/eval/experiments/deepseek_v4pro_smoke_20260616/` |

DeepSeek benchmark outputs include `raw_results.jsonl`, `metrics.csv`,
`summary.json`, and `metadata.json`. DeepSeek ablation outputs include
`metrics.csv`, `summary.json`, and `metadata.json`, matching the existing
ablation runner output pattern.

## Full benchmark summary

| Variant | Model | n | Grounding | Norm citation validity | Hazard coverage | Case relevance | Norm recall@k | Link resolution | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_only | Qwen3.5-9B | 46 | 0.0000 | 0.0000 | 0.0326 | 0.0000 | 0.0000 | 0.0000 | 41.2862 |
| llm_only | DeepSeek v4pro | 46 | 0.0000 | 0.0000 | 0.0362 | 0.0000 | 0.0000 | 0.0000 | 32.2299 |
| naive_dual | Qwen3.5-9B | 46 | 0.7741 | 0.0000 | 0.0000 | 0.2681 | 0.0870 | 0.0000 | 54.5830 |
| naive_dual | DeepSeek v4pro | 46 | 0.8891 | 0.0000 | 0.0000 | 0.2736 | 0.0870 | 0.0000 | 11.6270 |
| norm_only | Qwen3.5-9B | 46 | 0.1957 | 0.0024 | 0.0000 | 0.0000 | 0.0870 | 0.0000 | 49.6275 |
| norm_only | DeepSeek v4pro | 46 | 0.1522 | 0.0000 | 0.0000 | 0.0000 | 0.0870 | 0.0000 | 9.5229 |
| optimized | Qwen3.5-9B | 46 | 0.7695 | 0.0000 | 0.0000 | 0.3188 | 0.1275 | 0.0000 | 58.5537 |
| optimized | DeepSeek v4pro | 46 | 0.8587 | 0.0000 | 0.0000 | 0.3388 | 0.1275 | 0.0000 | 14.7468 |
| proposed | Qwen3.5-9B | 46 | 1.0000 | 0.1515 | 0.2681 | 0.3279 | 0.6739 | 0.3933 | 67.8369 |
| proposed | DeepSeek v4pro | 46 | 1.0000 | 0.1464 | 0.3243 | 0.3279 | 0.6739 | 0.3903 | 21.6633 |

## Full benchmark interpretation

- The main architectural trend is reproduced under DeepSeek v4pro. The
  proposed workflow remains the only full-benchmark variant with
  `norm_recall_at_k_mean = 0.6739` and non-zero link resolution.
- DeepSeek v4pro gives nearly the same proposed-method norm citation validity
  as Qwen3.5-9B: 0.1464 vs 0.1515. This confirms that final article selection
  remains the main limitation and is not solved by only switching model
  backends.
- DeepSeek v4pro improves proposed-method hazard coverage from 0.2681 to
  0.3243 while preserving case relevance at 0.3279.
- Retrieval-side recall values are identical where expected because the
  retrieval substrate and task set are unchanged. The model mostly changes
  generation, citation selection, and output formatting behavior.
- DeepSeek v4pro is substantially faster in this run: proposed mean latency
  falls from 67.8369 s to 21.6633 s. Runtime should still be interpreted as
  environment-dependent.

## Ablation summary

| Ablation/control | Model | n | Grounding | Norm citation validity | Hazard coverage | Case relevance | Norm recall@k | Link resolution | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full | Qwen3.5-9B | 46 | 1.0000 | 0.1427 | 0.2862 | 0.3170 | 0.6739 | 0.3646 | 71.6889 |
| full | DeepSeek v4pro | 46 | 1.0000 | 0.1470 | 0.3551 | 0.3225 | 0.6739 | 0.3738 | 19.7042 |
| no_arbitration | Qwen3.5-9B | 46 | 1.0000 | 0.1519 | 0.2301 | 0.3225 | 0.6739 | 0.3917 | 61.9602 |
| no_arbitration | DeepSeek v4pro | 46 | 1.0000 | 0.1475 | 0.3225 | 0.3170 | 0.6739 | 0.3834 | 19.8100 |
| no_case_evidence | Qwen3.5-9B | 46 | 1.0000 | 0.0272 | 0.0725 | 0.0000 | 0.0732 | 0.0000 | 51.0489 |
| no_case_evidence | DeepSeek v4pro | 46 | 1.0000 | 0.0290 | 0.1721 | 0.0000 | 0.0732 | 0.0000 | 17.9461 |
| no_case_norm_linker | Qwen3.5-9B | 46 | 1.0000 | 0.0283 | 0.1359 | 0.3388 | 0.0732 | 0.0000 | 61.6027 |
| no_case_norm_linker | DeepSeek v4pro | 46 | 1.0000 | 0.0261 | 0.2609 | 0.3225 | 0.0732 | 0.0000 | 19.0390 |
| no_deterministic_ground | Qwen3.5-9B | 46 | 1.0000 | 0.1469 | 0.1630 | 0.3279 | 0.6739 | 0.3864 | 62.2819 |
| no_deterministic_ground | DeepSeek v4pro | 46 | 1.0000 | 0.1518 | 0.3134 | 0.3116 | 0.6739 | 0.3780 | 19.0972 |
| no_query_rewrite | Qwen3.5-9B | 46 | 1.0000 | 0.1497 | 0.2808 | 0.3333 | 0.6739 | 0.3795 | 62.8365 |
| no_query_rewrite | DeepSeek v4pro | 46 | 1.0000 | 0.1469 | 0.3569 | 0.3116 | 0.6739 | 0.3733 | 20.0070 |

## Ablation interpretation

- The key mechanism result is reproduced: removing accident-case evidence or
  the case-to-norm linker drops norm recall from 0.6739 to 0.0732 and removes
  link resolution.
- DeepSeek v4pro does not change the main causal interpretation. The retrieval
  and linking substrate, not the model backend alone, drives the norm-recall
  advantage.
- Arbitration still does not show a strong aggregate benefit on this benchmark.
  Under both models, `no_arbitration` is close to or slightly above the full
  control on link resolution and norm citation validity. Arbitration should
  remain framed as a bounded safeguard for hard cases, not as the main source of
  average benchmark gains.
- Query rewriting also remains a support module rather than the primary driver:
  removing it leaves norm recall unchanged and link resolution nearly unchanged.
- DeepSeek v4pro improves hazard coverage across several ablation conditions,
  especially `full`, `no_case_evidence`, and `no_case_norm_linker`. This is a
  generation-quality improvement, but it does not remove the need for expert
  evaluation.

## Manuscript-use guidance

These DeepSeek experiments can be used as a real second-backend comparison
against Qwen3.5-9B-Q5_K_M. They support a narrower and defensible claim:

> The case-to-norm linking advantage was reproduced with a second
> OpenAI-compatible model backend, DeepSeek v4pro, over the same 46-task
> benchmark.

They do not support the following claims yet:

- expert-rated training usefulness;
- field training effectiveness;
- statistically significant superiority without repeated runs;
- strong arbitration benefits without a stress-test set;
- corrected final citation validity without a real citation-verifier variant.

Recommended manuscript update:

- Add DeepSeek v4pro as a second-backend robustness experiment.
- Keep Qwen3.5-9B as the original local-model backend.
- Report DeepSeek and Qwen in separate columns rather than pooling them.
- State that DeepSeek reproduces the recall/linking trend but does not solve
  low final norm citation validity.
- Keep expert evaluation, repeated-run confidence intervals, verifier results,
  and arbitration stress testing as future or next-stage work until they are
  actually completed.
