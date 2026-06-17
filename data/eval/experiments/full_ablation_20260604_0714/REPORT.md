# Full Ablation Report (2026-06-04)

## Run metadata

- **Run dir**: `data/eval/experiments/full_ablation_20260604_0714/`
- **Started**: 2026-06-04 07:14
- **Wall time**: ~5h
- **Total runs**: 276 (6 ablations × 46 tasks)
- **Errors**: 0
- **Procedure**: each ablation flips ONE env switch before invoking the
  proposed B5 system; `full` is the unmodified control.

## Aggregate (all 46 tasks)

| Ablation | n | grounding | hallucination | nrm_val | haz_cov | case_rel | **nrm_rcl@k** | **link_res** | elapsed |
|---|---|---|---|---|---|---|---|---|---|
| **full** (control) | 46 | 1.000 | 0.000 | 0.143 | 0.286 | 0.317 | 0.674 | 0.365 | 71.7s |
| no_query_rewrite | 46 | 1.000 | 0.000 | 0.150 | 0.281 | 0.333 | 0.674 | 0.380 | 62.8s |
| no_case_evidence | 46 | 1.000 | 0.000 | 0.027 | 0.072 | 0.000 | 0.073 | 0.000 | 51.0s |
| no_case_norm_linker | 46 | 1.000 | 0.000 | 0.028 | 0.136 | 0.339 | 0.073 | 0.000 | 61.6s |
| no_deterministic_ground | 46 | 1.000 | 0.000 | 0.147 | 0.163 | 0.328 | 0.674 | 0.386 | 62.3s |
| no_arbitration | 46 | 1.000 | 0.000 | 0.152 | 0.230 | 0.322 | 0.674 | 0.392 | 62.0s |

## Δ from full control (negative = mechanism contributed)

| Ablation | Δgrnd | Δnrm_val | Δhaz_cov | Δcase_rel | Δnrm_rcl | Δlink_res | Δelapsed |
|---|---|---|---|---|---|---|---|
| no_query_rewrite | +0.000 | +0.007 | -0.005 | +0.016 | 0.000 | +0.015 | -8.9s |
| **no_case_evidence** | +0.000 | **-0.116** | **-0.214** | **-0.317** | **-0.601** | **-0.365** | -20.6s |
| **no_case_norm_linker** | +0.000 | **-0.114** | -0.150 | +0.022 | **-0.601** | **-0.365** | -10.1s |
| no_deterministic_ground | +0.000 | +0.004 | -0.123 | +0.011 | 0.000 | +0.022 | -9.4s |
| no_arbitration | +0.000 | +0.009 | -0.056 | +0.005 | 0.000 | +0.027 | -9.7s |

## Mechanism-by-mechanism findings

### M1. Case→norm linker (§5.2) is the largest single contributor
**Δlink_res = -0.365, Δnrm_rcl = -0.601 when removed.** Two independent metrics zero out: removing the linker drops norm retrieval recall by 89% (from 0.674 → 0.073) and link resolution to zero (by construction). This is the cleanest mechanism-level evidence in the experiment.

The drop in `norm_citation_validity` (-0.114) confirms the linker also feeds the LLM correct articles to cite — not just retrieve.

### M2. Case evidence (§3.x) is the foundation
**no_case_evidence** is the most destructive ablation:
- Δcase_rel = -0.317 (zero, by construction)
- Δnrm_rcl = -0.601 (linker has no source case refs to follow)
- Δnrm_val = -0.116 (no case-driven norm linking)
- Δhaz_cov = -0.214 (cases contributed hazard signals)
- Δelapsed = -20.6s (entire case path skipped)

case evidence is necessary not sufficient for the linker — removing either zeros link_res.

### M3. Deterministic grounding (§5.3): subtle but real
**Δhaz_cov = -0.123, Δnrm_val = +0.004.** Grounding mostly affects hazard quality, not norm citation. Why grounding_rate unchanged? Because the metric measures whether cited chunk_ids are in retrieved set; the LLM is honest enough that grounding rarely needs to reject. The grounding mechanism's hidden value is enforcing the LLM to choose from retrieved chunks rather than free-form invent — visible in hazard_coverage because hazards are less constrained than norm citations.

### M4. Arbitration (§5.4): minimal aggregate impact
**Δhaz_cov = -0.056, others ≤0.01.** On this corpus, the consistency check usually passes first try; arbitration rarely fires. The mechanism is a safety net for harder corpora; not a primary driver here. Worth keeping for robustness but the paper should note arbitration's value is conditional on consistency failures, which our gold task set produces few of.

### M5. Query rewriting (§7.2.5): not measurably contributing
**All Δs near zero.** On this 46-task corpus the planner-generated queries are already strong; the rewriter doesn't change retrieval results. Saves ~9s by not making the extra LLM call.

**Implication for paper**: present query rewriting as a deployment option, not a key innovation. The §5.x main claims rest on case→norm linker (§5.2), deterministic grounding (§5.3), and the case evidence base — not query rewriting.

## Ranking of mechanism contribution

By Δ on the §5.2 head-line metric (link_resolution_rate):

1. **case→norm linker** (-0.365): the structural innovation
2. **case evidence** (-0.365): the data prerequisite (necessary not sufficient)
3. deterministic grounding (+0.022): no link contribution
4. arbitration (+0.027): no link contribution
5. query rewriting (+0.015): no link contribution

By Δ on norm_recall@k (retrieval quality):
1. case_evidence / case_norm_linker (both -0.601, tied; both required)
2. others (0 contribution)

By Δ on haz_cov (training quality):
1. case_evidence (-0.214)
2. case_norm_linker (-0.150)
3. deterministic_ground (-0.123)
4. arbitration (-0.056)
5. query_rewrite (-0.005)

## Paper framing recommendation

- **Headline claim**: case→norm linker (§5.2) + case evidence base (§3) jointly explain ~60% of norm recall gain and 100% of link resolution.
- **Secondary claim**: deterministic grounding (§5.3) contributes specifically to training material quality (hazard coverage), not retrieval. Frame as quality control, not retrieval enhancement.
- **Honest scoping**: query rewriting and arbitration have minimal aggregate impact on this corpus; describe as deployment-flexibility tools.

## Files

- `metrics.csv` — 276 rows × 16 metric columns
- `summary.json` — aggregate by ablation
- `run.log` — full execution log
- (figures to be added)

## Limitations

1. **grounding_rate=1.0 across all ablations** means the metric doesn't discriminate hallucination here. A stronger metric would compare cited chunk_ids against a true hallucination test set (e.g. synthetic cases with no relevant norms).
2. **Arbitration tested only on a corpus that rarely triggers it**. To stress-test arbitration, include cases with conflicting norm/case evidence (planned for §6 future work).
3. **Single LLM (Qwen3.5-9B)**. Cross-LLM replication would strengthen claims.
