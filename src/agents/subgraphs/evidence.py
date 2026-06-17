"""Evidence subgraph (Part B — tier 1: 取证).

Gathers and grounds the dual evidence for one round:
    risk_planner → query_rewriter → [norm_retriever ∥ case_retriever] → case_norm_linker

risk_planner plans *what* to search (hazards + base queries); query_rewriter
reformulates *how* to search (path-specialized + terminology-expanded +
arbitration-feedback-steered); the two paths retrieve; case_norm_linker adds the
case→norm cross-document link. Drafting/fusion lives in the authoring subgraph,
so this tier is purely about *what evidence we have*. The parent graph re-enters
this subgraph for a bounded targeted re-retrieval round when the arbiter emits an
evidence_request.
"""

from collections import defaultdict

from langgraph.graph import StateGraph, START, END

from src import config
from src.config import RETRIEVAL_MODE
from src.schema.state import TrainingState
from src.agents.risk_planner import run_risk_planner
from src.agents.query_rewriter import run_query_rewriter
from src.agents.evidence_formatter import evidence_ids
from src.retrieval.norm_retriever import retrieve_norm_evidence
from src.retrieval.case_retriever import retrieve_case_evidence
from src.retrieval.es_store import ES_CASE_INDEX, count_index, fetch_norm_chunks_by_refs
from src.trace_utils import timed_node


def _retrieve_norms(state: TrainingState) -> dict:
    queries = state.get("norm_queries", [])
    hazard_tags = state.get("hazards_identified", [])
    results = retrieve_norm_evidence(queries, hazard_tags)
    return {
        "norm_evidence": results,
        "norm_evidence_ids": evidence_ids(results),
        "retrieval_mode": RETRIEVAL_MODE,
    }


def _retrieve_cases(state: TrainingState) -> dict:
    if not config.ABLATION_CASE_EVIDENCE:
        # Ablation: skip case retrieval; downstream linker/fusion see no cases.
        return {
            "case_evidence": [],
            "case_evidence_ids": [],
            "case_index_available": False,
        }
    queries = state.get("case_queries", [])
    hazard_tags = state.get("hazards_identified", [])
    results = retrieve_case_evidence(queries, hazard_tags)
    return {
        "case_evidence": results,
        "case_evidence_ids": evidence_ids(results),
        "case_index_available": count_index(ES_CASE_INDEX) > 0,
    }


def _link_case_norms(state: TrainingState) -> dict:
    """case→norm evidence link: pull the exact norm articles cited by the
    retrieved cases' related_standards, and merge them into norm_evidence so the
    training material can show 案例→违反的规范条文→要求. Runs after both
    retrievers; dedupes by chunk_id and keeps norm_evidence_ids in sync so the
    deterministic grounding check still recognizes the linked chunks."""
    if not config.ABLATION_CASE_NORM_LINKER:
        # Ablation §5.2: keep case+norm evidence as parallel bags, no linking.
        return {
            "norm_evidence": state.get("norm_evidence", []) or [],
            "norm_evidence_ids": state.get("norm_evidence_ids", []) or [],
            "linked_norm_evidence_ids": [],
        }
    case_evidence = state.get("case_evidence", []) or []
    norm_evidence = list(state.get("norm_evidence", []) or [])

    ref_to_cases: dict[str, set] = defaultdict(set)
    refs: list[str] = []
    for case in case_evidence:
        for ref in case.get("related_standards", []) or []:
            refs.append(ref)
            if case.get("case_id"):
                ref_to_cases[ref].add(case["case_id"])

    linked = fetch_norm_chunks_by_refs(refs)
    existing_ids = {n.get("chunk_id") for n in norm_evidence}
    linked_ids: list[str] = []
    for chunk in linked:
        cid = chunk.get("chunk_id")
        if not cid or cid in existing_ids:
            continue
        key = f"{chunk.get('standard_code')}:{chunk.get('article_id')}"
        chunk = {**chunk, "linked_from_case": sorted(ref_to_cases.get(key, []))}
        norm_evidence.append(chunk)
        existing_ids.add(cid)
        linked_ids.append(cid)

    return {
        "norm_evidence": norm_evidence,
        "norm_evidence_ids": evidence_ids(norm_evidence),
        "linked_norm_evidence_ids": linked_ids,
    }


def build_evidence_subgraph() -> StateGraph:
    graph = StateGraph(TrainingState)
    graph.add_node("risk_planner", timed_node("risk_planner", run_risk_planner))
    graph.add_node("norm_retriever", timed_node("training_norm_retriever", _retrieve_norms))
    graph.add_node("case_retriever", timed_node("training_case_retriever", _retrieve_cases))
    graph.add_node("case_norm_linker", timed_node("training_case_norm_linker", _link_case_norms))

    graph.add_edge(START, "risk_planner")
    if config.AGENT_INTERACTIVE_FAST:
        # Keep the interactive path bounded; the query rewriter remains
        # available when AGENT_INTERACTIVE_FAST=false for paper/ablation runs.
        graph.add_edge("risk_planner", "norm_retriever")
        graph.add_edge("risk_planner", "case_retriever")
    else:
        graph.add_node("query_rewriter", timed_node("query_rewriter", run_query_rewriter))
        graph.add_edge("risk_planner", "query_rewriter")
        graph.add_edge("query_rewriter", "norm_retriever")
        graph.add_edge("query_rewriter", "case_retriever")
    # Parallel retrieval, then both must finish before the case→norm linker.
    graph.add_edge("norm_retriever", "case_norm_linker")
    graph.add_edge("case_retriever", "case_norm_linker")
    graph.add_edge("case_norm_linker", END)
    return graph


def get_evidence_subgraph():
    return build_evidence_subgraph().compile()
