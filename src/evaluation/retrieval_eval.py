"""Retrieval evaluation for the norm library.

Bootstraps a gold set for free from the accident cases: each case's narrative is
a query, and the norm articles it cites as "violated" (case.related_standards,
resolved against the live index) are the relevant items. This needs no manual
labeling and grows automatically as more cases/standards are ingested.

Pure retrieval/data metrics (recall@k, hit@k, MRR, nDCG@k) — no LLM, so it runs
in seconds and is independent of LLM-serving speed. Use it to A/B the reranker
(RERANK off vs on) and to track retrieval quality as the corpus grows.
"""

import math
from dataclasses import dataclass, field

from src.agents.query_rewriter import rewrite_queries
from src.data_pipeline.case_chunker import load_case_chunks
from src.retrieval import es_store
from src.retrieval.es_store import fetch_norm_chunks_by_refs, retrieve_norms


@dataclass
class CaseGold:
    case_id: str
    query: str
    hazard_tags: list[str]
    expected_chunk_ids: list[str]
    total_article_refs: int
    resolved_article_refs: int


def build_case_gold() -> list[CaseGold]:
    """One gold record per case: query = accident narrative, expected = chunk_ids
    of the in-library norm articles the case cites as violated."""
    cases = load_case_chunks()
    by_case: dict[str, dict] = {}
    for c in cases:
        by_case.setdefault(c.case_id, {})[c.chunk_kind] = c

    golds: list[CaseGold] = []
    for case_id, kinds in by_case.items():
        summary = kinds.get("case_summary") or next(iter(kinds.values()))
        refs = summary.related_standards or []
        article_refs = sorted({r for r in refs if ":" in r and not r.startswith("《")})
        resolved = fetch_norm_chunks_by_refs(article_refs)
        expected_ids = [n.get("chunk_id") for n in resolved if n.get("chunk_id")]
        query = (summary.process or summary.text or summary.case_title or "").strip()
        golds.append(
            CaseGold(
                case_id=case_id,
                query=query[:400],
                hazard_tags=summary.hazard_tags or [],
                expected_chunk_ids=expected_ids,
                total_article_refs=len(article_refs),
                resolved_article_refs=len(expected_ids),
            )
        )
    return golds


def recall_at_k(retrieved: list[str], expected: set[str], k: int) -> float:
    if not expected:
        return 0.0
    return len(set(retrieved[:k]) & expected) / len(expected)


def hit_at_k(retrieved: list[str], expected: set[str], k: int) -> float:
    if not expected:
        return 0.0
    return 1.0 if set(retrieved[:k]) & expected else 0.0


def mrr(retrieved: list[str], expected: set[str]) -> float:
    if not expected:
        return 0.0
    for i, cid in enumerate(retrieved, 1):
        if cid in expected:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: list[str], expected: set[str], k: int) -> float:
    if not expected:
        return 0.0
    dcg = sum(
        1.0 / math.log2(i + 1)
        for i, cid in enumerate(retrieved[:k], 1)
        if cid in expected
    )
    ideal = min(len(expected), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal + 1))
    return dcg / idcg if idcg else 0.0


def evaluate(
    rerank_enabled: bool,
    ks: tuple[int, ...] = (1, 3, 5),
    pool_k: int = 10,
    mode: str = "rrf_hybrid",
    rewrite_enabled: bool = False,
) -> dict:
    """Run norm retrieval over the case-derived gold set, A/B-able on two levers:
    the cross-encoder reranker (es_store.RERANK_ENABLED) and the tier-aware query
    rewriter. With rewrite on, each gold query is reformulated for the norm path
    before retrieval, so the recall@k / MRR / nDCG deltas quantify the rewriter's
    contribution. A single process can sweep all four (off/off … on/on) against
    the same gold and live index.
    """
    golds = [g for g in build_case_gold() if g.expected_chunk_ids]
    es_store.RERANK_ENABLED = rerank_enabled

    per_case: list[dict] = []
    agg: dict[str, float] = {f"recall@{k}": 0.0 for k in ks}
    agg.update({f"hit@{k}": 0.0 for k in ks})
    agg.update({f"ndcg@{k}": 0.0 for k in ks})
    agg["mrr"] = 0.0

    for g in golds:
        queries = [g.query]
        if rewrite_enabled:
            norm_q, _ = rewrite_queries([g.query], [], g.hazard_tags)
            queries = norm_q or [g.query]
        results = retrieve_norms(queries, g.hazard_tags, top_k=max(pool_k, max(ks)), mode=mode)
        retrieved = [r.get("chunk_id") for r in results]
        expected = set(g.expected_chunk_ids)
        row = {"case_id": g.case_id, "expected": len(expected), "mrr": mrr(retrieved, expected)}
        for k in ks:
            row[f"recall@{k}"] = recall_at_k(retrieved, expected, k)
            row[f"hit@{k}"] = hit_at_k(retrieved, expected, k)
            row[f"ndcg@{k}"] = ndcg_at_k(retrieved, expected, k)
        per_case.append(row)
        for key in agg:
            agg[key] += row[key]

    n = len(golds) or 1
    agg = {key: round(val / n, 4) for key, val in agg.items()}
    return {
        "rerank_enabled": rerank_enabled,
        "rewrite_enabled": rewrite_enabled,
        "mode": mode,
        "evaluated_cases": len(golds),
        "aggregate": agg,
        "per_case": per_case,
    }


def link_resolution_summary() -> dict:
    """Data-quality metric: of the article-level refs the cases cite, how many
    resolve to an actual norm article in the current index (case→norm link)."""
    golds = build_case_gold()
    total = sum(g.total_article_refs for g in golds)
    resolved = sum(g.resolved_article_refs for g in golds)
    return {
        "cases": len(golds),
        "cases_with_resolved_refs": sum(1 for g in golds if g.expected_chunk_ids),
        "total_article_refs": total,
        "resolved_article_refs": resolved,
        "resolution_rate": round(resolved / total, 4) if total else 0.0,
    }
