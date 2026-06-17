"""Five baseline systems for paper §4 comparison (Manuscript_Architecture.md §4):

    B1 llm_only       — No retrieval; raw LLM generates from task scenario.
    B2 norm_only_rag  — Norm retrieval only, naive prompt → generate.
    B3 naive_dual_rag — Norm + case retrieval, naive concat prompt; no
                        consistency check, no arbitration.
    B4 optimized_rag  — Hybrid retrieval (BM25 + vector + RRF) + cross-encoder
                        rerank; no consistency check; no arbitration.
    B5 proposed       — Full agentic graph (existing unified_graph Mode A).

Each baseline returns a TrainingOutput-shaped dict so downstream evaluation
can score them uniformly. Common variant dispatch via `run_baseline()`.
"""

from .base import BaselineResult, run_baseline, BASELINES

__all__ = ["BaselineResult", "run_baseline", "BASELINES"]
