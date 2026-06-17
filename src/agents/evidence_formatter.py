import json
from typing import Any

NO_CASE_EVIDENCE = "当前未检索到事故案例证据；不得编造案例。"
NO_NORM_EVIDENCE = "当前未检索到规范证据；不得编造规范条文。"


def _value(data: dict, *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return str(value)
    return ""


def _page_range(data: dict) -> str:
    start = data.get("page_start")
    end = data.get("page_end")
    if start and end:
        return f"{start}-{end}"
    if start:
        return str(start)
    if end:
        return str(end)
    return ""


# Two tiers, to keep LLM prompts small without starving the final material:
#   PROMPT_EVIDENCE_TEXT_LIMIT — evidence text the LLM *reads* to author the draft
#     (fusion). Most norm articles are <300 chars, so ~220 keeps them whole and
#     only truncates long ones; this is the main lever against prompt bloat.
#   CITATION_CONTENT_LIMIT — the article excerpt that lands in the grounded
#     NormRequirement/CaseWarning and is shown in the final training material;
#     kept longer so citations stay substantive.
#   COMPACT_EVIDENCE_TEXT_LIMIT — one-line hints in the *_index skeletons.
PROMPT_EVIDENCE_TEXT_LIMIT = 220
CITATION_CONTENT_LIMIT = 480
COMPACT_EVIDENCE_TEXT_LIMIT = 160


def _trim(text: Any, limit: int = PROMPT_EVIDENCE_TEXT_LIMIT) -> str:
    value = "" if text is None else str(text).strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "..."


def evidence_ids(evidence: list[dict]) -> list[str]:
    return [str(item.get("chunk_id")) for item in evidence if item.get("chunk_id")]


def to_norm_requirements(
    norm_evidence: list[dict],
    *,
    text_limit: int = CITATION_CONTENT_LIMIT,
) -> list[dict]:
    """Build grounded NormRequirement dicts straight from retrieved chunks.

    Used to seed/backfill the structured citation list so it always reflects
    real chunk-level evidence instead of depending on the LLM to copy chunk_ids.
    """
    out: list[dict] = []
    for item in norm_evidence:
        cid = _value(item, "chunk_id")
        if not cid:
            continue
        req = {
            "chunk_id": cid,
            "standard_code": _value(item, "standard_code"),
            "article_id": _value(item, "article_id", "related_article_id"),
            "title": _value(item, "title", "chapter_title", "chapter"),
            "content": _trim(item.get("text"), text_limit),
            "requirement_type": _value(item, "requirement_type"),
            "source": _value(item, "standard_name", "source_name", "source"),
            "source_path": _value(item, "source_path", "asset_path"),
        }
        # Provenance for the case→norm evidence chain: which accident case(s)
        # cited this norm article as a violated requirement.
        linked = item.get("linked_from_case")
        if linked:
            req["linked_from_case"] = linked
        out.append(req)
    return out


def to_case_warnings(
    case_evidence: list[dict],
    *,
    text_limit: int = CITATION_CONTENT_LIMIT,
) -> list[dict]:
    out: list[dict] = []
    for item in case_evidence:
        cid = _value(item, "chunk_id")
        if not cid:
            continue
        text = item.get("text") or "\n".join(
            p for p in [_value(item, "process"), _value(item, "causes")] if p
        )
        out.append({
            "chunk_id": cid,
            "case_id": _value(item, "case_id"),
            "case_title": _value(item, "case_title", "title"),
            "summary": _trim(text, text_limit),
            "consequence": _value(item, "consequences"),
            "lesson": _value(item, "corrective_measures"),
            "source": _value(item, "source_org", "source"),
            "source_path": _value(item, "source_path"),
        })
    return out


def format_norm_evidence(
    norm_evidence: list[dict],
    *,
    text_limit: int = PROMPT_EVIDENCE_TEXT_LIMIT,
) -> str:
    if not norm_evidence:
        return NO_NORM_EVIDENCE

    blocks: list[str] = []
    for idx, item in enumerate(norm_evidence, 1):
        block = {
            "rank": idx,
            "chunk_id": _value(item, "chunk_id"),
            "standard_code": _value(item, "standard_code"),
            "article_id": _value(item, "article_id", "related_article_id"),
            "title": _value(item, "title", "chapter_title", "chapter"),
            "requirement_type": _value(item, "requirement_type"),
            "text": _trim(item.get("text"), text_limit),
        }
        blocks.append(json.dumps(block, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(blocks)


def format_case_evidence(
    case_evidence: list[dict],
    *,
    text_limit: int = PROMPT_EVIDENCE_TEXT_LIMIT,
) -> str:
    if not case_evidence:
        return NO_CASE_EVIDENCE

    blocks: list[str] = []
    for idx, item in enumerate(case_evidence, 1):
        text = item.get("text") or "\n".join(
            part
            for part in [
                _value(item, "process"),
                _value(item, "causes"),
                _value(item, "consequences"),
                _value(item, "corrective_measures"),
            ]
            if part
        )
        block = {
            "rank": idx,
            "chunk_id": _value(item, "chunk_id"),
            "case_id": _value(item, "case_id"),
            "case_title": _value(item, "case_title", "title"),
            "accident_type": _value(item, "accident_type"),
            "source_org": _value(item, "source_org", "source"),
            "source_date": _value(item, "source_date"),
            "text": _trim(text, text_limit),
        }
        blocks.append(json.dumps(block, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(blocks)


def format_norm_evidence_index(norm_evidence: list[dict]) -> str:
    if not norm_evidence:
        return NO_NORM_EVIDENCE

    blocks: list[str] = []
    for idx, item in enumerate(norm_evidence, 1):
        block = {
            "rank": idx,
            "chunk_id": _value(item, "chunk_id"),
            "standard_code": _value(item, "standard_code"),
            "article_id": _value(item, "article_id", "related_article_id"),
            "title": _value(item, "title", "chapter_title", "chapter"),
            "source": _value(item, "standard_name", "source_name", "source"),
            "source_path": _value(item, "source_path", "asset_path"),
            "text_hint": _trim(item.get("text"), COMPACT_EVIDENCE_TEXT_LIMIT),
        }
        blocks.append(json.dumps(block, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(blocks)


def format_case_evidence_index(case_evidence: list[dict]) -> str:
    if not case_evidence:
        return NO_CASE_EVIDENCE

    blocks: list[str] = []
    for idx, item in enumerate(case_evidence, 1):
        text = item.get("text") or "\n".join(
            part
            for part in [
                _value(item, "process"),
                _value(item, "causes"),
                _value(item, "consequences"),
                _value(item, "corrective_measures"),
            ]
            if part
        )
        block = {
            "rank": idx,
            "chunk_id": _value(item, "chunk_id"),
            "case_id": _value(item, "case_id"),
            "case_title": _value(item, "case_title", "title"),
            "source": _value(item, "source_org", "source"),
            "source_path": _value(item, "source_path"),
            "text_hint": _trim(text, COMPACT_EVIDENCE_TEXT_LIMIT),
        }
        blocks.append(json.dumps(block, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(blocks)


def compact_draft_for_prompt(draft: dict) -> dict:
    """Draft copy for the checker/training prompts with the heavy citation lists
    (`norm_requirements`/`accident_warnings`) reduced to chunk_id-only refs. The
    full grounded citations already travel in `fused_evidence` (training) or the
    evidence index (checker), and the deterministic grounding reads chunk_ids
    from the real draft in state — so the prompt copy only needs the ids, not the
    duplicated ~480-char content. Narrative fields are kept intact."""
    if not isinstance(draft, dict):
        return draft
    slim = dict(draft)
    for key in ("norm_requirements", "accident_warnings"):
        refs = draft.get(key)
        if isinstance(refs, list):
            slim[key] = [
                {"chunk_id": r.get("chunk_id", "")}
                for r in refs
                if isinstance(r, dict)
            ]
    return slim


def build_evidence_diagnostics(
    *,
    retrieval_mode: str,
    norm_evidence: list[dict],
    case_evidence: list[dict],
    case_index_available: bool,
) -> dict:
    diagnostics = {
        "retrieval_mode": retrieval_mode,
        "norm_count": len(norm_evidence),
        "case_count": len(case_evidence),
        "norm_evidence_ids": evidence_ids(norm_evidence),
        "case_evidence_ids": evidence_ids(case_evidence),
        "case_index_available": case_index_available,
    }
    if not case_index_available:
        diagnostics["case_note"] = "safety_case_chunks is empty or unavailable; case evidence must not be fabricated."
    elif not case_evidence:
        diagnostics["case_note"] = "No case chunks were retrieved for the current queries; case evidence must not be fabricated."
    return diagnostics
