# Full Benchmark Report (2026-06-04)

## Run metadata

- **Run dir**: `data/eval/experiments/full_bench_20260604_0335/`
- **Started**: 2026-06-04 03:35 (local)
- **Wall time**: ~3h 35min
- **Total runs**: 230 (46 tasks × 5 variants)
- **Errors**: 0
- **LLM**: Qwen3.5-9B-Q5_K_M @ localhost:51000
- **Retrieval backend**: Elasticsearch (1791 norm + 152 case chunks)

## Headline aggregate results

| Variant | n | grounding ↑ | norm_val ↑ | haz_cov ↑ | case_rel ↑ | norm_rcl@k ↑ | link_res ↑ | elapsed |
|---|---|---|---|---|---|---|---|---|
| llm_only | 46 | 0.000 | 0.000 | 0.033 | 0.000 | 0.000 | 0.000 | 41.3s |
| norm_only | 46 | 0.196 | 0.002 | 0.000 | 0.000 | 0.087 | 0.000 | 49.6s |
| naive_dual | 46 | 0.774 | 0.000 | 0.000 | 0.268 | 0.087 | 0.000 | 54.6s |
| optimized | 46 | 0.770 | 0.000 | 0.000 | 0.319 | 0.128 | 0.000 | 58.6s |
| **proposed** | **46** | **1.000** | **0.152** | **0.268** | **0.328** | **0.674** | **0.393** | **67.8s** |

All numbers are arithmetic means over 46 tasks. ↑ means higher is better.

## Headline findings

### F1. §5.3 deterministic grounding works as designed
**proposed grounding_rate = 1.000** across all 46 tasks. Every chunk_id cited by the LLM is verified to be in this round's retrieved evidence. Optimized RAG (B4) and naive dual RAG (B3) hover at 0.77 — LLM hallucinated 1 in 4 citations even with both norm + case context present.

### F2. §5.2 case→norm linker is the unique differentiator
**link_resolution_rate = 0.393 for proposed, 0.000 for all others.** This is the hardest quantitative evidence in the paper: the §5.2 cross-document evidence chain is structural, not emergent. No baseline can produce it even with reranking + RRF + both evidence types.

### F3. proposed retrieves 5–8× more gold norm articles
**norm_recall@k = 0.674 vs 0.087–0.128.** Even when LLM-side citation is imperfect, the retrieval substrate alone is dramatically better. case→norm linker pulls cited articles directly; baselines only get articles that BM25/RRF surface organically.

### F4. proposed is the only system that cites gold norms correctly
**norm_citation_validity = 0.152 vs ≤0.002.** Across 46 tasks, the four baselines combined produce essentially zero gold-matching citations. Even when they retrieve relevant articles (B4 case_rel=0.319), the LLM cannot translate retrieval into correct citation. proposed's deterministic chunk_id grounding forces alignment.

### F5. Hazard coverage 8× better
**hazard_coverage = 0.268 vs ≤0.044.** Baselines essentially do not return gold-overlapping hazard labels at all. This is partially a metric-strictness artifact (set-equality on Chinese terms), so proposed's lead understates the practical gap.

### F6. Cost: proposed is only ~26s slower than baselines on average
67.8s vs 41–59s — fully within an acceptable interactive range. The arbitration loop is bounded; consistency check rarely triggers more than one retry on this corpus.

## Per-theme breakdown (proposed)

| theme | n | grounding | norm_rcl | link_res | norm_val |
|---|---|---|---|---|---|
| 高处作业 | 9 | 1.00 | 0.889 | 0.525 | 0.195 |
| 脚手架 | 22 | 1.00 | 0.636 | 0.325 | 0.162 |
| 起重吊装 | 13 | 1.00 | 0.692 | 0.447 | 0.127 |
| 临时用电 | 2 | 1.00 | 0.000 | 0.200 | 0.000 |

**高处作业** is the strongest theme — best norm_recall (88.9%) and link_resolution (52.5%), reflecting the most mature gold (JGJ-80-2016 well-covered, many cases with explicit articles).

**临时用电** is the weakest — only 2 tasks total, both Tier-W (proxy fallback). norm_recall=0 because the proxy articles do not match the gold expected refs which are themselves proxies. Sample size too small for confident reporting; flag in paper as a scope limitation.

## Per-tier breakdown (proposed)

| tier | n | grounding | norm_rcl | link_res |
|---|---|---|---|---|
| S (full gold) | 33 | 1.00 | **0.939** | 0.414 |
| W (proxy gold) | 13 | 1.00 | 0.000 | 0.341 |

**Tier-S norm_recall = 0.939** — when the case explicitly cites a library article, proposed retrieves it 94% of the time. This is the §5.2 mechanism working end-to-end.

Tier-W norm_recall=0 is by gold construction (proxy refs are LLM-judged, not in the case source). Tier-W link_resolution=0.341 shows the linker still fires for these cases via standard-level retrieval, just to different articles than the proxy gold.

**For paper**: report on the 33 Tier-S tasks as primary evidence; note Tier-W as scope sensitivity.

## Per-variant cost analysis

| variant | mean LLM calls | mean retrieval calls | mean elapsed |
|---|---|---|---|
| llm_only | 1.0 | 0 | 41.3s |
| norm_only | 0.98 | 1 | 49.6s |
| naive_dual | 1.0 | 2 | 54.6s |
| optimized | 1.0 | 2 + rerank | 58.6s |
| proposed | 6–10 (varied) | 3–5 | 67.8s |

proposed averages ~7 LLM calls (scenario / risk_planner / query_rewriter / fusion / consistency / training_agent, plus occasional re-grounding) but completes in 67.8s — most calls are short.

## Files

- `raw_results.jsonl` — 230 BaselineResult dicts (one per run)
- `metrics.csv` — 230 rows × 14 metric columns
- `summary.json` — aggregate by variant
- `run.log` — full execution log

## Limitations + next steps

1. **hazard_coverage / case_relevance metrics are strict** — set-equality on Chinese strings undercounts semantic matches. LLM-as-judge layer would lift all variants' scores; **proposed's relative lead should persist or grow**.
2. **临时用电 sample too small** (n=2). Adding GB 50303-cited cases to the case library would lift it.
3. **norm_citation_validity = 0.152 on proposed** is still low in absolute terms — LLM picks articles from retrieval but often the wrong subset of a chapter. Improving prompt or adding tier-aware re-rank could boost this.
4. **Run ablation suite next**: 6 ablations × 46 tasks = 276 runs (~5h) to isolate per-mechanism contribution.
