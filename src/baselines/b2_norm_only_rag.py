"""B2: Norm-only Naive RAG. Retrieve regulation chunks, stuff into prompt,
generate. No case evidence, no consistency check, no arbitration.

Operationalizes "仅规范 Naive RAG" (research_plan §9.1).
"""

import json

from src.config import RETRIEVAL_TOP_K
from src.llm_utils import call_llm_json
from src.retrieval.es_store import retrieve_norms
from src.schema.training import TrainingOutput
from src.baselines.base import BaselineResult, OUTPUT_BUDGET, register


SYSTEM = (
    "你是建筑施工安全培训助手。基于提供的施工安全规范条文，生成一份作业前安全"
    "培训材料。仅引用提供的规范条文，不要编造。仅输出 JSON。"
)

USER_TEMPLATE = (
    "作业主题：{theme}\n作业场景：{scenario}\n\n规范条文：\n{norms}\n\n"
    "请输出 TrainingOutput JSON。norm_requirements 中的每条必须从上述检索结果中选择，"
    "并附 chunk_id；accident_warnings 留空（本对照不提供事故案例）。"
)


def _format_norm_block(norms: list[dict]) -> str:
    lines = []
    for n in norms:
        sc = n.get("standard_code", "")
        art = n.get("article_id", "")
        cid = n.get("chunk_id", "")
        text = (n.get("text") or "")[:280].replace("\n", " ")
        lines.append(f"[{cid}] {sc} 第{art}条 — {text}")
    return "\n".join(lines)


@register("norm_only")
def run(task: dict, opts: dict) -> BaselineResult:
    if opts.get("dry_run"):
        return BaselineResult(
            variant="norm_only", task_id=task.get("task_id", ""),
            training_output={"scenario_description": task.get("scenario_summary", "")},
            grounded=False,
        )
    top_k = opts.get("top_k", RETRIEVAL_TOP_K)
    query = task.get("scenario_summary") or task.get("theme", "")
    hazards = task.get("expected_hazards", [])
    norms = retrieve_norms([query], hazards, top_k=top_k, mode="bm25")
    prompt = USER_TEMPLATE.format(
        theme=task.get("theme", ""),
        scenario=task.get("scenario_summary", ""),
        norms=_format_norm_block(norms),
    ) + OUTPUT_BUDGET
    result = BaselineResult(
        variant="norm_only",
        task_id=task.get("task_id", ""),
        training_output={},
        retrieved_norm_ids=[n.get("chunk_id") for n in norms if n.get("chunk_id")],
        retrieval_calls=1,
        prompt_chars=len(prompt),
        grounded=False,  # no deterministic chunk_id grounding post-check
        raw_evidence={"norms": norms[:5]},
    )
    try:
        out = call_llm_json(prompt, SYSTEM, response_model=TrainingOutput)
        result.training_output = out.model_dump()
        result.llm_calls = 1
    except Exception as e:
        result.training_output = {"_error": str(e)}
    return result
