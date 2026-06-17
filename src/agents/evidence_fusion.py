import json
from src.llm_utils import call_llm_json
from src.schema.training import FusionCompactResult
from src.prompts import fusion as prompts
from src.agents.evidence_formatter import (
    build_evidence_diagnostics,
    format_case_evidence,
    format_norm_evidence,
    to_case_warnings,
    to_norm_requirements,
)


def run_evidence_fusion(state: dict) -> dict:
    scenario = state["training_scenario"]
    hazards = state.get("hazards_identified", [])
    norm_evidence = state.get("norm_evidence", [])
    case_evidence = state.get("case_evidence", [])
    retry_count = state.get("retry_count", 0)
    consistency_issues = state.get("consistency_issues", [])
    retrieval_mode = state.get("retrieval_mode", "")
    case_index_available = state.get("case_index_available", False)

    diagnostics = build_evidence_diagnostics(
        retrieval_mode=retrieval_mode,
        norm_evidence=norm_evidence,
        case_evidence=case_evidence,
        case_index_available=case_index_available,
    )
    norm_str = format_norm_evidence(norm_evidence)
    case_str = format_case_evidence(case_evidence)

    if retry_count > 0 and consistency_issues:
        issues_str = json.dumps(consistency_issues, ensure_ascii=False, separators=(",", ":"))
        prompt = prompts.USER_RETRY.format(
            scenario=scenario,
            hazards=json.dumps(hazards, ensure_ascii=False),
            norm_evidence=norm_str,
            case_evidence=case_str,
            evidence_diagnostics=json.dumps(diagnostics, ensure_ascii=False, separators=(",", ":")),
            consistency_issues=issues_str,
        )
    else:
        prompt = prompts.USER.format(
            scenario=scenario,
            hazards=json.dumps(hazards, ensure_ascii=False),
            norm_evidence=norm_str,
            case_evidence=case_str,
            evidence_diagnostics=json.dumps(diagnostics, ensure_ascii=False, separators=(",", ":")),
        )

    try:
        result = call_llm_json(prompt, prompts.SYSTEM, response_model=FusionCompactResult)
    except ValueError:
        result = FusionCompactResult()

    # Ground the structured citation lists to the chunks actually retrieved.
    # The LLM only *selects* which chunk_ids are relevant; the citation metadata
    # and content are rebuilt verbatim from the retrieved chunks via to_*(),
    # which also carries case→norm provenance (linked_from_case). This keeps
    # citations authoritative even though the LLM-facing prompt omits source_path
    # etc., and backfills from all evidence if the LLM cited nothing valid.
    norm_by_id = {n.get("chunk_id"): n for n in norm_evidence if n.get("chunk_id")}
    case_by_id = {c.get("chunk_id"): c for c in case_evidence if c.get("chunk_id")}

    def _selected(refs, valid_ids):
        seen: set[str] = set()
        out: list[str] = []
        for ref in refs:
            cid = ref.chunk_id
            if cid in valid_ids and cid not in seen:
                seen.add(cid)
                out.append(cid)
        return out

    norm_ids = _selected(result.fused_evidence.norm_requirements, norm_by_id)
    norm_reqs = to_norm_requirements([norm_by_id[c] for c in norm_ids]) or to_norm_requirements(norm_evidence)
    case_ids = _selected(result.fused_evidence.case_warnings, case_by_id)
    case_warns = to_case_warnings([case_by_id[c] for c in case_ids]) or to_case_warnings(case_evidence)

    fused_dump = result.fused_evidence.model_dump()
    fused_dump["norm_requirements"] = norm_reqs
    fused_dump["case_warnings"] = case_warns
    draft_dump = result.draft_training_output.model_dump()
    draft_dump["norm_requirements"] = norm_reqs
    draft_dump["accident_warnings"] = case_warns

    return {
        "fused_evidence": fused_dump,
        "draft_training_output": draft_dump,
        "evidence_diagnostics": diagnostics,
    }
