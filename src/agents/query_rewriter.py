"""Query rewriter (Part B — inside the 取证/evidence tier).

A tier-aware query reformulation module that sits between risk_planner (plans
*what* to search) and the retrievers (optimizes *how* to search). It composes
three named, ablatable strategies so the contribution is measurable and easy to
package in the paper:

  1. 路径特化改写 (path specialization) — norm-path queries are pushed toward
     standard/article terminology and protective-measure keywords; case-path
     queries toward accident-narrative phrasing (type → cause → consequence).
     Matches the dual retrieval paths of the evidence tier.
  2. 术语扩展 (terminology expansion) — queries are enriched with domain wording
     (standard codes, 条文 vocabulary) to lift BM25 + tag recall.
  3. 反馈驱动重构 (feedback-driven reformulation) — when the arbitration tier
     (tier 3) returns an evidence_request on insufficiency, the rewrite targets
     exactly the flagged gaps and diverges from the previous round, closing the
     arbitration→evidence loop.

`rewrite_queries` is the reusable core (also called by the retrieval eval to A/B
its recall@k / MRR / nDCG impact). `run_query_rewriter` is the graph-node wrapper
that honours QUERY_REWRITE_ENABLED and degrades to the planner's queries on
failure, so rewriting is a pure optimization that can never break retrieval.
"""

import json

from src.config import LLM_QUERY_TEMPERATURE, QUERY_REWRITE_ENABLED
from src.llm_utils import call_llm_json
from src.schema.training import QueryRewriteOutput
from src.prompts import query_rewriter as prompts


def rewrite_queries(
    norm_queries: list[str],
    case_queries: list[str],
    hazards: list[str] | None = None,
    evidence_request: dict | None = None,
) -> tuple[list[str], list[str]]:
    """Reformulate the two query sets. Returns (norm_queries, case_queries),
    falling back to the inputs if there is nothing to rewrite or the LLM call
    fails. Always attempts the rewrite (the QUERY_REWRITE_ENABLED gate lives in
    the node wrapper), so callers like the eval harness can force the ON arm."""
    if not norm_queries and not case_queries:
        return norm_queries, case_queries

    gap_section = ""
    if evidence_request:
        gap_section = prompts.GAP_TEMPLATE.format(
            gap=json.dumps(evidence_request, ensure_ascii=False)
        )

    prompt = prompts.USER.format(
        hazards=json.dumps(hazards or [], ensure_ascii=False),
        norm_queries=json.dumps(norm_queries, ensure_ascii=False),
        case_queries=json.dumps(case_queries, ensure_ascii=False),
        gap_section=gap_section,
    )

    try:
        result = call_llm_json(
            prompt,
            prompts.SYSTEM,
            response_model=QueryRewriteOutput,
            temperature=LLM_QUERY_TEMPERATURE,
        )
    except ValueError:
        return norm_queries, case_queries

    return (
        result.norm_queries or norm_queries,
        result.case_queries or case_queries,
    )


def run_query_rewriter(state: dict) -> dict:
    norm_queries = state.get("norm_queries", []) or []
    case_queries = state.get("case_queries", []) or []

    if not QUERY_REWRITE_ENABLED or (not norm_queries and not case_queries):
        return {}

    new_norm, new_case = rewrite_queries(
        norm_queries,
        case_queries,
        state.get("hazards_identified", []),
        state.get("evidence_request"),
    )
    return {"norm_queries": new_norm, "case_queries": new_case}
