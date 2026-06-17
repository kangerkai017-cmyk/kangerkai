"""B3: Naive Dual-Evidence RAG. Retrieve both norms and cases, naive prompt
concat, generate. No case→norm linker, no consistency check, no arbitration.

Operationalizes "规范+案例普通 RAG" (research_plan §9.1). This is the
strongest non-agentic baseline — it isolates the contribution of §5.2 case→
norm linking and §5.3 deterministic grounding when compared against B5.
"""

from src.config import RETRIEVAL_TOP_K
from src.llm_utils import call_llm_json
from src.retrieval.es_store import retrieve_cases, retrieve_norms
from src.schema.training import TrainingOutput
from src.baselines.base import BaselineResult, OUTPUT_BUDGET, register


SYSTEM = (
    "你是建筑施工安全培训助手。基于提供的规范条文和事故案例，生成一份作业前安全"
    "培训材料。仅引用提供的条文与案例，不要编造。仅输出 JSON。"
)

USER_TEMPLATE = (
    "作业主题：{theme}\n作业场景：{scenario}\n\n"
    "规范条文：\n{norms}\n\n事故案例：\n{cases}\n\n"
    "请输出 TrainingOutput JSON。norm_requirements 必须从规范条文中选；"
    "accident_warnings 必须从事故案例中选；两者各附 chunk_id。"
)


def _fmt_norms(norms: list[dict]) -> str:
    out = []
    for n in norms:
        sc, art, cid = n.get("standard_code",""), n.get("article_id",""), n.get("chunk_id","")
        txt = (n.get("text") or "")[:240].replace("\n", " ")
        out.append(f"[{cid}] {sc} 第{art}条 — {txt}")
    return "\n".join(out)


def _fmt_cases(cases: list[dict]) -> str:
    out = []
    for c in cases:
        cid = c.get("chunk_id","")
        title = c.get("case_title","")
        acc = c.get("accident_type","")
        proc = (c.get("process") or c.get("text",""))[:240].replace("\n", " ")
        out.append(f"[{cid}] {title} ({acc}) — {proc}")
    return "\n".join(out)


@register("naive_dual")
def run(task: dict, opts: dict) -> BaselineResult:
    if opts.get("dry_run"):
        return BaselineResult(
            variant="naive_dual", task_id=task.get("task_id", ""),
            training_output={"scenario_description": task.get("scenario_summary", "")},
            grounded=False,
        )
    top_k = opts.get("top_k", RETRIEVAL_TOP_K)
    query = task.get("scenario_summary") or task.get("theme", "")
    hazards = task.get("expected_hazards", [])
    norms = retrieve_norms([query], hazards, top_k=top_k, mode="bm25")
    cases = retrieve_cases([query], hazards, top_k=top_k, mode="bm25")
    prompt = USER_TEMPLATE.format(
        theme=task.get("theme",""),
        scenario=task.get("scenario_summary",""),
        norms=_fmt_norms(norms),
        cases=_fmt_cases(cases),
    ) + OUTPUT_BUDGET
    result = BaselineResult(
        variant="naive_dual",
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
