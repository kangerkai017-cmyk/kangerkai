"""Part B arbitration: deterministic deliberation + bounded routing (no LLM)."""

from src.agents.arbitration import (
    apply_decision,
    deliberate,
    get_arbitration_subgraph,
    route_after_arbitration,
)
from src.agents.graph import build_graph


def _base_state(**overrides) -> dict:
    state = {
        "consistency_passed": False,
        "retry_reason": "",
        "retry_count": 1,
        "case_index_available": True,
        "dialogue_budget": 1,
        "consistency_issues": [],
        "fused_evidence": {"case_warnings": [{"chunk_id": "case::x", "summary": "s"}]},
        "draft_training_output": {"accident_warnings": [{"chunk_id": "case::x"}]},
        "hazards_identified": ["高处坠落"],
    }
    state.update(overrides)
    return state


def test_passed_routes_to_training():
    out = deliberate(_base_state(consistency_passed=True))
    assert out["arbitration_route"] == "training_agent"
    assert out["arbitration_decision"]["type"] == "passed"


def test_norm_case_conflict_resolved_norm_over_case_and_terminal():
    state = _base_state(retry_reason="norm_case_conflict")
    decided = deliberate(state)
    assert decided["arbitration_route"] == "training_agent"  # terminal, no loop
    assert decided["requires_human_review"] is True
    assert decided["arbitration_decision"]["policy"] == "norm>case"
    # apply_decision performs the demotion based on the recorded decision
    state.update(decided)
    applied = apply_decision(state)
    assert all(c["priority"] == "supplementary" for c in applied["fused_evidence"]["case_warnings"])
    assert all("arbitration_note" in c for c in applied["draft_training_output"]["accident_warnings"])


def test_apply_decision_noop_when_not_conflict():
    state = _base_state(retry_reason="hallucination")
    state.update(deliberate(state))
    assert apply_decision(state) == {}


def test_evidence_insufficient_requests_more_within_budget():
    out = deliberate(
        _base_state(
            retry_reason="evidence_insufficient",
            dialogue_budget=1,
            consistency_issues=[
                {"type": "evidence_insufficient", "description": "缺少临边防护规范"}
            ],
        )
    )
    assert out["arbitration_route"] == "evidence_subgraph"
    assert out["dialogue_budget"] == 0  # decremented
    assert "缺少临边防护规范" in out["evidence_request"]["missing"]


def test_evidence_insufficient_converges_when_budget_exhausted():
    out = deliberate(_base_state(retry_reason="evidence_insufficient", dialogue_budget=0))
    assert out["arbitration_route"] == "training_agent"


def test_evidence_insufficient_converges_when_no_case_index():
    out = deliberate(
        _base_state(retry_reason="evidence_insufficient", dialogue_budget=1, case_index_available=False)
    )
    assert out["arbitration_route"] == "training_agent"


def test_hallucination_re_grounds_via_authoring():
    out = deliberate(_base_state(retry_reason="hallucination"))
    assert out["arbitration_route"] == "authoring_subgraph"
    assert out["arbitration_decision"]["action"] == "re_ground"


def test_exhausted_retries_force_convergence():
    out = deliberate(
        _base_state(retry_reason="evidence_insufficient", retry_count=99, dialogue_budget=1)
    )
    assert out["arbitration_route"] == "training_agent"


def test_router_reads_route_field():
    assert route_after_arbitration({"arbitration_route": "authoring_subgraph"}) == "authoring_subgraph"
    assert route_after_arbitration({}) == "training_agent"


def test_arbitration_subgraph_resolves_conflict_end_to_end():
    sub = get_arbitration_subgraph()
    out = sub.invoke(_base_state(retry_reason="norm_case_conflict"))
    assert out["arbitration_route"] == "training_agent"
    assert out["requires_human_review"] is True
    assert all(c["priority"] == "supplementary" for c in out["fused_evidence"]["case_warnings"])


def test_parent_graph_compiles_with_three_subgraphs():
    nodes = set(build_graph().nodes.keys())
    assert {
        "scenario_agent",
        "evidence_subgraph",
        "authoring_subgraph",
        "arbitration_subgraph",
        "training_agent",
    } <= nodes
