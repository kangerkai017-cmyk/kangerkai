"""Deterministic generation-quality metrics for the 5 baselines.

Operationalizes the §9.3 metric list (research_plan + Manuscript_Architecture §4
"Metrics"). All metrics are LLM-free — they compute over chunk_id overlap,
norm-ref overlap, hazard-tag overlap against the gold v1 task set.

LLM-as-judge metrics (training usefulness, case relevance qualitative score)
are deferred to a separate module since they need Qwen and human review.
"""

from typing import Any


def _ref_set(d: dict, key: str) -> set:
    return set(d.get(key) or [])


def _norm_refs_from_output(training_output: dict) -> list[str]:
    """Extract STANDARD_CODE:ARTICLE_ID pairs the model cited in
    training_output.norm_requirements."""
    refs = []
    for nr in training_output.get("norm_requirements") or []:
        if not isinstance(nr, dict):
            continue
        sc = (nr.get("standard_code") or "").strip()
        art = (nr.get("article_id") or "").strip()
        if sc and art:
            refs.append(f"{sc}:{art}")
    return refs


def _cited_chunk_ids_norm(training_output: dict) -> list[str]:
    out = []
    for nr in training_output.get("norm_requirements") or []:
        if isinstance(nr, dict) and (cid := nr.get("chunk_id")):
            out.append(cid.strip())
    return out


def _cited_chunk_ids_case(training_output: dict) -> list[str]:
    out = []
    for w in training_output.get("accident_warnings") or []:
        if isinstance(w, dict) and (cid := w.get("chunk_id")):
            out.append(cid.strip())
    return out


def _norm_ref_from_chunk_id(cid: str) -> str | None:
    """Convert chunk_id like 'norm::JGJ-80-2016::article::3.0.5' → 'JGJ-80-2016:3.0.5'."""
    parts = cid.split("::")
    if len(parts) >= 4 and parts[0] == "norm" and parts[2] == "article":
        return f"{parts[1]}:{parts[3]}"
    return None


def compute_metrics(result_dict: dict, task: dict) -> dict:
    """Compute all deterministic metrics for one baseline result against the gold task.

    Returns a dict with these keys:
        norm_citation_validity     — cited norm refs ∈ expected_norm_refs
        grounding_rate             — cited chunk_ids ∈ retrieved chunks
        hallucination_rate         — 1 - grounding_rate (citations not retrievable)
        hazard_coverage            — output expected_hazards covers gold hazards
        case_relevance             — cited case chunk_ids ∩ expected case_ids
        norm_retrieval_recall@k    — retrieved_norm_ids contains expected refs
        link_resolution_rate       — only for proposed: linked_from_case fields populated
    """
    training_output = result_dict.get("training_output") or {}
    retrieved_norm_ids = set(result_dict.get("retrieved_norm_ids") or [])
    retrieved_case_ids = set(result_dict.get("retrieved_case_ids") or [])
    variant = result_dict.get("variant", "")

    expected_norm_refs = _ref_set(task, "expected_norm_refs")
    expected_case_refs = _ref_set(task, "expected_case_refs")
    expected_hazards = _ref_set(task, "expected_hazards")

    # 1. Norm citation validity
    cited_norm_refs = _norm_refs_from_output(training_output)
    valid_cited = [r for r in cited_norm_refs if r in expected_norm_refs]
    norm_citation_validity = (len(valid_cited) / len(cited_norm_refs)) if cited_norm_refs else 0.0

    # 2 & 3. Grounding rate: cited chunk_ids must be in retrieved chunks
    cited_n = _cited_chunk_ids_norm(training_output)
    cited_c = _cited_chunk_ids_case(training_output)
    all_cited = cited_n + cited_c
    grounded_cited = [
        cid for cid in cited_n if cid in retrieved_norm_ids
    ] + [cid for cid in cited_c if cid in retrieved_case_ids]
    grounding_rate = (len(grounded_cited) / len(all_cited)) if all_cited else 0.0
    hallucination_rate = 1.0 - grounding_rate if all_cited else 0.0

    # 4. Hazard coverage
    output_hazards = _ref_set(training_output, "expected_hazards")
    haz_overlap = expected_hazards & output_hazards
    hazard_coverage = (len(haz_overlap) / len(expected_hazards)) if expected_hazards else 0.0

    # 5. Case relevance — overlap between cited case chunks' parent case_id and expected
    cited_case_ids = set()
    for cid in cited_c:
        parts = cid.split("::")
        if len(parts) >= 2 and parts[0] == "case":
            cited_case_ids.add(parts[1])
    expected_case_id_set = expected_case_refs
    case_overlap = cited_case_ids & expected_case_id_set
    case_relevance = (len(case_overlap) / len(expected_case_id_set)) if expected_case_id_set else 0.0

    # 6. Norm retrieval recall@k — gold refs that the retriever returned
    retrieved_norm_refs = {nr for cid in retrieved_norm_ids if (nr := _norm_ref_from_chunk_id(cid))}
    norm_recall = (
        len(expected_norm_refs & retrieved_norm_refs) / len(expected_norm_refs)
        if expected_norm_refs else 0.0
    )

    # 7. Case retrieval recall@k
    retrieved_case_parent_ids = set()
    for cid in retrieved_case_ids:
        parts = cid.split("::")
        if len(parts) >= 2 and parts[0] == "case":
            retrieved_case_parent_ids.add(parts[1])
    case_recall = (
        len(expected_case_id_set & retrieved_case_parent_ids) / len(expected_case_id_set)
        if expected_case_id_set else 0.0
    )

    # Link resolution rate (proposed only) — fraction of norm citations that
    # carry a linked_from_case attribution (i.e., went through §5.2 link path)
    link_resolution_rate = 0.0
    if variant == "proposed":
        cited_w_link = sum(
            1 for nr in training_output.get("norm_requirements") or []
            if isinstance(nr, dict) and nr.get("linked_from_case")
        )
        total_cited_norm = len(training_output.get("norm_requirements") or [])
        link_resolution_rate = cited_w_link / total_cited_norm if total_cited_norm else 0.0

    return {
        "variant": variant,
        "task_id": task.get("task_id"),
        "theme": task.get("theme"),
        "tier": (task.get("_meta") or {}).get("tier"),
        # quality
        "norm_citation_validity": round(norm_citation_validity, 4),
        "grounding_rate": round(grounding_rate, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "hazard_coverage": round(hazard_coverage, 4),
        "case_relevance": round(case_relevance, 4),
        # retrieval
        "norm_recall_at_k": round(norm_recall, 4),
        "case_recall_at_k": round(case_recall, 4),
        "norm_retrieved_count": len(retrieved_norm_ids),
        "case_retrieved_count": len(retrieved_case_ids),
        # §5.2 specific
        "link_resolution_rate": round(link_resolution_rate, 4),
        # counters
        "cited_norm_count": len(cited_n),
        "cited_case_count": len(cited_c),
        # runtime/cost
        "llm_calls": result_dict.get("llm_calls", 0),
        "retrieval_calls": result_dict.get("retrieval_calls", 0),
        "elapsed_seconds": result_dict.get("elapsed_seconds", 0.0),
        "prompt_chars": result_dict.get("prompt_chars", 0),
    }


def aggregate_metrics(rows: list[dict]) -> dict:
    """Aggregate per-task metrics by (variant, theme) and overall by variant."""
    from collections import defaultdict
    import statistics as st

    METRIC_KEYS = [
        "norm_citation_validity", "grounding_rate", "hallucination_rate",
        "hazard_coverage", "case_relevance",
        "norm_recall_at_k", "case_recall_at_k",
        "link_resolution_rate",
        "llm_calls", "retrieval_calls", "elapsed_seconds",
    ]

    by_variant = defaultdict(lambda: defaultdict(list))
    for r in rows:
        v = r["variant"]
        for k in METRIC_KEYS:
            by_variant[v][k].append(r[k])

    summary = {}
    for v, mvals in by_variant.items():
        summary[v] = {
            "n_tasks": len(mvals["grounding_rate"]),
        }
        for k, vals in mvals.items():
            if not vals: continue
            summary[v][f"{k}_mean"] = round(st.mean(vals), 4)
    return summary
