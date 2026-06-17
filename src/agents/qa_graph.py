"""Mode B: 安全问答管线（响应式 Safety Q&A）。

    START → qa_planner
          → [norm_retriever ∥ case_retriever]
          → case_norm_linker
          → qa_agent → END

共享 Mode A 的取证基础设施（ES + RRF + case→norm 链接 + 确定性 chunk_id 接地）；
无仲裁环——证据不足通过 confidence/evidence_gap 诚实标注，不重检索。
"""

from collections import defaultdict

from langgraph.graph import StateGraph, START, END

from src.config import RETRIEVAL_MODE
from src.schema.qa import QAState
from src.agents.qa_planner import run_qa_planner
from src.agents.qa_agent import run_qa_agent
from src.agents.evidence_formatter import evidence_ids, build_evidence_diagnostics
from src.retrieval.norm_retriever import retrieve_norm_evidence
from src.retrieval.case_retriever import retrieve_case_evidence
from src.retrieval.es_store import ES_CASE_INDEX, count_index, fetch_norm_chunks_by_refs
from src.trace_utils import timed_node


def _retrieve_norms(state: QAState) -> dict:
    queries = state.get("norm_queries", [])
    results = retrieve_norm_evidence(queries, hazard_tags=[])
    return {
        "norm_evidence": results,
        "norm_evidence_ids": evidence_ids(results),
    }


def _retrieve_cases(state: QAState) -> dict:
    queries = state.get("case_queries", [])
    results = retrieve_case_evidence(queries, hazard_tags=[])
    return {
        "case_evidence": results,
        "case_evidence_ids": evidence_ids(results),
        "case_index_available": count_index(ES_CASE_INDEX) > 0,
    }


def _link_case_norms(state: QAState) -> dict:
    """case→norm 跨文档链接：将检索到的事故案例引用的规范条文补充进 norm_evidence。"""
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

    diagnostics = build_evidence_diagnostics(
        retrieval_mode=RETRIEVAL_MODE,
        norm_evidence=norm_evidence,
        case_evidence=case_evidence,
        case_index_available=state.get("case_index_available", False),
    )
    diagnostics["linked_norm_count"] = len(linked_ids)

    return {
        "norm_evidence": norm_evidence,
        "norm_evidence_ids": evidence_ids(norm_evidence),
        "linked_norm_evidence_ids": linked_ids,
        "evidence_diagnostics": diagnostics,
    }


def build_qa_graph() -> StateGraph:
    graph = StateGraph(QAState)

    graph.add_node("qa_planner", timed_node("qa_planner", run_qa_planner))
    graph.add_node("norm_retriever", timed_node("qa_norm_retriever", _retrieve_norms))
    graph.add_node("case_retriever", timed_node("qa_case_retriever", _retrieve_cases))
    graph.add_node("case_norm_linker", timed_node("qa_case_norm_linker", _link_case_norms))
    graph.add_node("qa_agent", timed_node("qa_agent", run_qa_agent))

    graph.add_edge(START, "qa_planner")
    graph.add_edge("qa_planner", "norm_retriever")
    graph.add_edge("qa_planner", "case_retriever")
    graph.add_edge("norm_retriever", "case_norm_linker")
    graph.add_edge("case_retriever", "case_norm_linker")
    graph.add_edge("case_norm_linker", "qa_agent")
    graph.add_edge("qa_agent", END)

    return graph


def get_compiled_qa_graph():
    return build_qa_graph().compile()
