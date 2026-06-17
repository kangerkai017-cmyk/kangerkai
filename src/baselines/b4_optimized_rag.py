"""B4: Optimized RAG. Hybrid BM25+vector retrieval with RRF + cross-encoder
rerank for both norms and cases. NO case→norm linker, NO consistency check,
NO arbitration — isolating the contribution of those agentic mechanisms when
compared against B5.

The 'mode=hybrid' branch in es_store already does BM25+vector+RRF; rerank is
gated by RERANK_ENABLED env. We force-enable rerank here for this baseline.
"""

import os

from src.config import RETRIEVAL_TOP_K
from src.llm_utils import call_llm_json
from src.retrieval.es_store import retrieve_cases, retrieve_norms
from src.schema.training import TrainingOutput
from src.baselines.base import BaselineResult, OUTPUT_BUDGET, register
from src.baselines.b3_naive_dual_rag import SYSTEM, USER_TEMPLATE, _fmt_norms, _fmt_cases


@register("optimized")
def run(task: dict, opts: dict) -> BaselineResult:
    if opts.get("dry_run"):
        return BaselineResult(
            variant="optimized", task_id=task.get("task_id", ""),
            training_output={"scenario_description": task.get("scenario_summary", "")},
            grounded=False,
        )
    top_k = opts.get("top_k", RETRIEVAL_TOP_K)
    query = task.get("scenario_summary") or task.get("theme", "")
    hazards = task.get("expected_hazards", [])
    # Force rerank on for this variant
    prev_rerank = os.environ.get("RERANK_ENABLED")
    os.environ["RERANK_ENABLED"] = "true"
    try:
        norms = retrieve_norms([query], hazards, top_k=top_k, mode="rrf_hybrid")
        cases = retrieve_cases([query], hazards, top_k=top_k, mode="rrf_hybrid")
    finally:
        if prev_rerank is None:
            os.environ.pop("RERANK_ENABLED", None)
        else:
            os.environ["RERANK_ENABLED"] = prev_rerank
    prompt = USER_TEMPLATE.format(
        theme=task.get("theme",""),
        scenario=task.get("scenario_summary",""),
        norms=_fmt_norms(norms),
        cases=_fmt_cases(cases),
    ) + OUTPUT_BUDGET
    result = BaselineResult(
        variant="optimized",
        task_id=task.get("task_id",""),
        training_output={},
        retrieved_norm_ids=[n.get("chunk_id") for n in norms if n.get("chunk_id")],
        retrieved_case_ids=[c.get("chunk_id") for c in cases if c.get("chunk_id")],
        retrieval_calls=2,
        prompt_chars=len(prompt),
        grounded=False,
        raw_evidence={"norms": norms[:5], "cases": cases[:5]},
    )
    try:
        out = call_llm_json(prompt, SYSTEM, response_model=TrainingOutput)
        result.training_output = out.model_dump()
        result.llm_calls = 1
    except Exception as e:
        result.training_output = {"_error": str(e)}
    return result
