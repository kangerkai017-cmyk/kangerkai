"""Arbitration subgraph (Part B — tier 3: 仲裁).

The deliberation tier. Replaces the old hard-coded `_check_reroute` heuristic
with an explicit two-step subgraph that *decides* then *acts*:

    deliberate → apply_decision

deliberate (judgement, no side effects on evidence):
  - norm_case_conflict → deterministic **norm > case** decision, terminal.
  - evidence_insufficient → if dialogue_budget allows and the case index is live,
    emit a structured evidence_request, spend one budget unit, route back to the
    evidence tier for a bounded targeted re-retrieval; else converge.
  - hallucination → route back to the authoring tier to re-fuse/re-ground the
    same evidence (no new retrieval).
  - passed / budget exhausted / unknown → converge to the training agent.

apply_decision (acts on the decision):
  - norm_case_conflict → demote the conflicting case experience to a supplementary
    warning (norm requirement stays authoritative) and flag the case for human
    review.

All loops are bounded by retry_count ≤ MAX_RETRIES and dialogue_budget, so the
graph always terminates.
"""

from langgraph.graph import StateGraph, START, END

from src.config import MAX_RETRIES
from src.schema.state import TrainingState
from src.trace_utils import timed_node

SUPPLEMENTARY_NOTE = "补充警示：本案例经验仅作参考，安全要求以规范条文为准。"


def deliberate(state: dict) -> dict:
    """Pure judgement: pick the route and record the decision. No mutation of the
    evidence in flight (that is apply_decision's job)."""
    passed = state.get("consistency_passed", True)
    reason = state.get("retry_reason", "")
    retry_count = state.get("retry_count", 0)
    case_available = state.get("case_index_available", False)
    budget = state.get("dialogue_budget", 0)

    if passed:
        return {
            "arbitration_route": "training_agent",
            "arbitration_decision": {"type": "passed", "action": "proceed"},
        }

    if retry_count > MAX_RETRIES:
        return {
            "arbitration_route": "training_agent",
            "arbitration_decision": {
                "type": reason or "exhausted",
                "action": "proceed",
                "note": "retry budget exhausted",
            },
        }

    if reason == "norm_case_conflict":
        return {
            "arbitration_route": "training_agent",
            "requires_human_review": True,
            "arbitration_decision": {
                "type": "norm_case_conflict",
                "policy": "norm>case",
                "action": "resolved",
                "rationale": (
                    "规范条文为强制性安全要求，优先级高于事故案例中的经验性做法；"
                    "冲突的案例经验降级为补充警示，规范要求为准。"
                ),
            },
        }

    if reason == "evidence_insufficient":
        if budget > 0 and case_available:
            request = _build_evidence_request(state)
            return {
                "arbitration_route": "evidence_subgraph",
                "dialogue_budget": budget - 1,
                "evidence_request": request,
                "arbitration_decision": {
                    "type": "evidence_insufficient",
                    "action": "request_more_evidence",
                    "request": request,
                    "budget_left": budget - 1,
                },
            }
        return {
            "arbitration_route": "training_agent",
            "arbitration_decision": {
                "type": "evidence_insufficient",
                "action": "proceed",
                "note": "dialogue budget exhausted or case index unavailable",
            },
        }

    if reason == "hallucination":
        return {
            "arbitration_route": "authoring_subgraph",
            "arbitration_decision": {"type": "hallucination", "action": "re_ground"},
        }

    return {
        "arbitration_route": "training_agent",
        "arbitration_decision": {"type": reason or "unknown", "action": "proceed"},
    }


def apply_decision(state: dict) -> dict:
    """Act on the recorded decision. Currently only the norm>case resolution has
    a side effect on the evidence: demote conflicting case experience so the
    training agent renders norms as authoritative and cases as supplementary."""
    decision = state.get("arbitration_decision", {}) or {}
    if decision.get("type") != "norm_case_conflict":
        return {}
    return _demote_cases_to_supplementary(state)


def route_after_arbitration(state: dict) -> str:
    return state.get("arbitration_route") or "training_agent"


def build_arbitration_subgraph() -> StateGraph:
    graph = StateGraph(TrainingState)
    graph.add_node("deliberate", timed_node("arbitration_deliberate", deliberate))
    graph.add_node("apply_decision", timed_node("arbitration_apply_decision", apply_decision))
    graph.add_edge(START, "deliberate")
    graph.add_edge("deliberate", "apply_decision")
    graph.add_edge("apply_decision", END)
    return graph


def get_arbitration_subgraph():
    return build_arbitration_subgraph().compile()


# --- helpers ---------------------------------------------------------------


def _mark_supplementary(items: list) -> list:
    out = []
    for item in items or []:
        item = dict(item)
        item["priority"] = "supplementary"
        item["arbitration_note"] = SUPPLEMENTARY_NOTE
        out.append(item)
    return out


def _demote_cases_to_supplementary(state: dict) -> dict:
    fused = dict(state.get("fused_evidence") or {})
    draft = dict(state.get("draft_training_output") or {})
    updates: dict = {}
    if fused.get("case_warnings"):
        fused["case_warnings"] = _mark_supplementary(fused["case_warnings"])
        updates["fused_evidence"] = fused
    if draft.get("accident_warnings"):
        draft["accident_warnings"] = _mark_supplementary(draft["accident_warnings"])
        updates["draft_training_output"] = draft
    return updates


def _build_evidence_request(state: dict) -> dict:
    issues = state.get("consistency_issues", []) or []
    missing = [
        i.get("description", "")
        for i in issues
        if i.get("type") == "evidence_insufficient"
    ]
    return {
        "reason": "evidence_insufficient",
        "missing": missing,
        "hazards": state.get("hazards_identified", []),
        "instruction": (
            "针对上述未被充分支撑的危险源/要求，生成与上一轮明显不同的检索查询，"
            "补充规范条文与事故案例证据。"
        ),
    }
