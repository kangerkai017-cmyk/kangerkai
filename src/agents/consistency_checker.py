import json
from src.llm_utils import call_llm_json
from src.schema.training import ConsistencyCheckOutput
from src.prompts import checker as prompts
from src.agents.evidence_formatter import (
    compact_draft_for_prompt,
    format_case_evidence_index,
    format_norm_evidence_index,
)

_REASON_PRIORITY = ["hallucination", "norm_case_conflict", "evidence_insufficient"]


def _referenced_ids(items: list) -> list[str]:
    out: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            cid = str(item.get("chunk_id") or "").strip()
            if cid:
                out.append(cid)
    return out


def _ground_against_evidence(state: dict) -> list[dict]:
    """Deterministic grounding: every chunk_id cited in the draft must exist in
    the evidence actually retrieved this round. Catches both fabricated ids and
    empty/uncited output that the LLM check may wave through."""
    draft = state.get("draft_training_output", {}) or {}
    valid_norm = set(state.get("norm_evidence_ids", []) or [])
    valid_case = set(state.get("case_evidence_ids", []) or [])
    has_norm_evidence = bool(state.get("norm_evidence", []))

    issues: list[dict] = []

    norm_refs = _referenced_ids(draft.get("norm_requirements"))
    bad_norm = [c for c in norm_refs if c not in valid_norm]
    for cid in bad_norm:
        issues.append({
            "type": "hallucination",
            "description": f"规范引用 chunk_id={cid} 不在本轮检索证据中",
            "location": "norm_requirements",
        })
    if has_norm_evidence and not [c for c in norm_refs if c in valid_norm]:
        issues.append({
            "type": "evidence_insufficient",
            "description": "本轮检索到规范证据，但草稿未引用任何有效规范 chunk_id",
            "location": "norm_requirements",
        })

    case_refs = _referenced_ids(draft.get("accident_warnings"))
    bad_case = [c for c in case_refs if c not in valid_case]
    for cid in bad_case:
        issues.append({
            "type": "hallucination",
            "description": f"案例引用 chunk_id={cid} 不在本轮检索证据中",
            "location": "accident_warnings",
        })
    return issues


def run_consistency_checker(state: dict) -> dict:
    from src import config as _cfg

    norm_evidence = state.get("norm_evidence", [])
    case_evidence = state.get("case_evidence", [])
    draft = state.get("draft_training_output", {})
    retry_count = state.get("retry_count", 0)

    # Feed only a compact citation skeleton (chunk_id + standard/article + title
    # + short hint), not full article text — the LLM check just verifies the
    # draft's chunk_ids are traceable, and the deterministic grounding below does
    # the authoritative chunk_id membership check.
    prompt = prompts.USER.format(
        draft=json.dumps(compact_draft_for_prompt(draft), ensure_ascii=False, separators=(",", ":")),
        norm_evidence=format_norm_evidence_index(norm_evidence),
        case_evidence=format_case_evidence_index(case_evidence),
        evidence_diagnostics=json.dumps(
            state.get("evidence_diagnostics", {}), ensure_ascii=False, separators=(",", ":")
        ),
    )

    try:
        result = call_llm_json(prompt, prompts.SYSTEM, response_model=ConsistencyCheckOutput)
        llm_issues = [i.model_dump() for i in result.issues]
    except ValueError:
        # Checker itself failed to produce JSON: don't block the pipeline,
        # rely on the deterministic grounding check below.
        llm_issues = []

    # Ablation §5.3: skip deterministic chunk_id grounding, rely only on the
    # LLM's self-judgment. This isolates the contribution of code-side grounding.
    if _cfg.ABLATION_DETERMINISTIC_GROUND:
        grounding_issues = _ground_against_evidence(state)
    else:
        grounding_issues = []
    grounding_types = {i.get("type") for i in grounding_issues}

    # Deterministic chunk_id grounding is authoritative for hallucination: a
    # fabricated citation is exactly an out-of-evidence chunk_id, which the
    # grounding check detects precisely. Drop any LLM hallucination flag it did
    # not corroborate — otherwise a clean grounding gets overridden by an LLM
    # false-positive, which previously spun the re-ground retry loop to no end.
    # The LLM still owns the judgments grounding can't make (norm_case_conflict,
    # semantic evidence_insufficient).
    kept_llm_issues = [
        i
        for i in llm_issues
        if i.get("type") != "hallucination" or "hallucination" in grounding_types
    ]

    issues = kept_llm_issues + grounding_issues
    passed = not issues

    reason = ""
    if not passed:
        present = {i.get("type") for i in issues}
        for r in _REASON_PRIORITY:
            if r in present:
                reason = r
                break

    new_retry_count = retry_count + 1 if not passed else retry_count
    return {
        "consistency_passed": passed,
        "consistency_issues": issues,
        "retry_count": new_retry_count,
        "retry_reason": reason,
    }
