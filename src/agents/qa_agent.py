from src.llm_utils import call_llm_json
from src.llm_utils import LLMTruncatedOutputError
from src.schema.qa import QACompactOutput
from src.schema.training import NormRequirement, CaseWarning
from src.prompts import qa as prompts
from src.agents.evidence_formatter import (
    format_norm_evidence,
    format_case_evidence,
    to_norm_requirements,
    to_case_warnings,
)


def run_qa_agent(state: dict) -> dict:
    question = state["question"]
    norm_evidence = state.get("norm_evidence", []) or []
    case_evidence = state.get("case_evidence", []) or []
    norm_evidence_ids = set(state.get("norm_evidence_ids", []) or [])
    case_evidence_ids = set(state.get("case_evidence_ids", []) or [])
    linked_ids = set(state.get("linked_norm_evidence_ids", []) or [])
    valid_norm_ids = norm_evidence_ids | linked_ids

    prompt = prompts.USER.format(
        question=question,
        norm_evidence=format_norm_evidence(norm_evidence),
        case_evidence=format_case_evidence(case_evidence),
    )

    llm_failed = False
    truncated = False
    try:
        result = call_llm_json(prompt, prompts.SYSTEM, response_model=QACompactOutput)
    except LLMTruncatedOutputError:
        truncated = True
        llm_failed = True
        result = QACompactOutput(
            answer_text=_fallback_answer_from_evidence(norm_evidence, case_evidence),
            confidence="low",
            evidence_gap="LLM 输出被截断，已退回基于检索证据的简要回答",
        )
    except ValueError:
        llm_failed = True
        result = QACompactOutput(
            answer_text=_fallback_answer_from_evidence(norm_evidence, case_evidence),
            confidence="low",
            evidence_gap="LLM 调用失败，无法生成回答",
        )

    selected_norm_ids = [
        cid for cid in result.cited_norm_ids
        if isinstance(cid, str) and cid in valid_norm_ids
    ]
    selected_case_ids = [
        cid for cid in result.cited_case_ids
        if isinstance(cid, str) and cid in case_evidence_ids
    ]
    norm_by_id = {n.get("chunk_id"): n for n in norm_evidence if n.get("chunk_id")}
    case_by_id = {c.get("chunk_id"): c for c in case_evidence if c.get("chunk_id")}

    cited_norms = to_norm_requirements([
        norm_by_id[cid] for cid in selected_norm_ids if cid in norm_by_id
    ])
    cited_cases = to_case_warnings([
        case_by_id[cid] for cid in selected_case_ids if cid in case_by_id
    ])

    # Backfill from grounded evidence if LLM left citations empty
    if (llm_failed or not cited_norms) and norm_evidence:
        cited_norms = [
            NormRequirement(**r).model_dump()
            for r in to_norm_requirements(norm_evidence)
        ]
    if (llm_failed or not cited_cases) and case_evidence:
        cited_cases = [
            CaseWarning(**c).model_dump()
            for c in to_case_warnings(case_evidence)
        ]

    output = {
        "answer_text": result.answer_text,
        "cited_norms": cited_norms,
        "cited_cases": cited_cases,
        "confidence": result.confidence,
        "evidence_gap": result.evidence_gap,
    }
    return {"final_qa_output": output}


def _fallback_answer_from_evidence(norm_evidence: list[dict], case_evidence: list[dict]) -> str:
    if norm_evidence:
        top = norm_evidence[0]
        article = top.get("article_id") or "相关条文"
        text = (top.get("text") or "").strip()
        if len(text) > 180:
            text = text[:180].rstrip() + "..."
        return f"根据检索到的规范依据（{article}），{text}"
    if case_evidence:
        top = case_evidence[0]
        text = (top.get("text") or top.get("process") or "").strip()
        if len(text) > 180:
            text = text[:180].rstrip() + "..."
        return f"当前未形成完整生成回答；检索到的相似事故提示：{text}"
    return "（回答生成失败，请以现场安全交底为准）"
