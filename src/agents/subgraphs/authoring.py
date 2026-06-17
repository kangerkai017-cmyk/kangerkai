"""Authoring subgraph (Part B — tier 2: 撰写与自检).

Turns the gathered evidence into an audited draft:
    evidence_fusion → consistency_checker

evidence_fusion synthesizes the scene/risk narrative and the grounded citation
lists (norm requirements + case warnings, rebuilt verbatim from retrieved
chunks). consistency_checker then pairs an LLM review with the deterministic
chunk_id grounding check and emits the pass/fail verdict + retry_reason that the
arbitration tier deliberates on. The parent graph re-enters this subgraph (not
the evidence tier) on a hallucination verdict, to re-fuse/re-ground the same
evidence without paying for another retrieval round.
"""

from langgraph.graph import StateGraph, START, END

from src import config
from src.schema.state import TrainingState
from src.agents.evidence_fusion import run_evidence_fusion
from src.agents.consistency_checker import run_consistency_checker
from src.trace_utils import timed_node


def build_authoring_subgraph() -> StateGraph:
    graph = StateGraph(TrainingState)
    graph.add_node("evidence_fusion", timed_node("evidence_fusion", run_evidence_fusion))
    graph.add_edge(START, "evidence_fusion")
    if config.AGENT_INTERACTIVE_FAST:
        graph.add_edge("evidence_fusion", END)
    else:
        graph.add_node("consistency_checker", timed_node("consistency_checker", run_consistency_checker))
        graph.add_edge("evidence_fusion", "consistency_checker")
        graph.add_edge("consistency_checker", END)
    return graph


def get_authoring_subgraph():
    return build_authoring_subgraph().compile()
