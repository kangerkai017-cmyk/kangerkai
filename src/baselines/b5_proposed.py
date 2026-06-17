"""B5: The proposed system — dual-evidence Agentic RAG (Mode A training graph).

Invokes the training subgraph DIRECTLY (`get_compiled_graph`, not
`get_compiled_unified_graph`). The unified_graph wraps training+qa under an
intent_classifier router; for the baseline comparison we always want Mode A
training, so we bypass the router (which can mis-route scenario descriptions
to qa and yield empty training output — observed on task-脚手架-001 in pilot).

The §5.5 dual-modal routing claim is exercised separately via the
intent_classifier unit tests, not via these baselines.

Compared to B4 this adds:
  - case→norm linker (§5.2 cross-document evidence chain)
  - deterministic chunk_id grounding (§5.3)
  - three-tier authoring/arbitration deliberation (§5.4)
"""

from src.agents.graph import get_compiled_graph
from src.config import DIALOGUE_BUDGET
from src.baselines.base import BaselineResult, register


def _build_initial_state(task: dict) -> dict:
    """Training-subgraph state. Skips the unified_graph router fields
    (user_input/mode/intent_reason) since we invoke the training graph directly."""
    topic = f"{task.get('theme', '')} — {task.get('scenario_summary', '')}"
    return {
        "step_count": 0, "llm_calls": 0, "retrieval_calls": 0,
        "topic": topic,
        "training_scenario": task.get("scenario_summary"),
        "hazards_identified": [],
        "fused_evidence": None,
        "draft_training_output": None,
        "consistency_passed": False, "consistency_issues": [],
        "retry_count": 0, "retry_reason": "",
        "dialogue_budget": DIALOGUE_BUDGET,
        "evidence_request": None,
        "arbitration_decision": {},
        "requires_human_review": False,
        "arbitration_route": "",
        "final_training_output": None,
        "norm_queries": [], "case_queries": [],
        "norm_evidence": [], "case_evidence": [],
        "retrieval_mode": "",
        "norm_evidence_ids": [], "case_evidence_ids": [],
        "linked_norm_evidence_ids": [],
        "case_index_available": False,
        "evidence_diagnostics": {},
    }


@register("proposed")
def run(task: dict, opts: dict) -> BaselineResult:
    if opts.get("dry_run"):
        return BaselineResult(
            variant="proposed", task_id=task.get("task_id", ""),
            training_output={"scenario_description": task.get("scenario_summary", "")},
            grounded=True,
        )
    graph = get_compiled_graph()
    init_state = _build_initial_state(task)
    final_state = graph.invoke(init_state)
    return BaselineResult(
        variant="proposed",
        task_id=task.get("task_id", ""),
        training_output=final_state.get("final_training_output") or {},
        retrieved_norm_ids=final_state.get("norm_evidence_ids", []),
        retrieved_case_ids=final_state.get("case_evidence_ids", []),
        llm_calls=int(final_state.get("llm_calls", 0)),
        retrieval_calls=int(final_state.get("retrieval_calls", 0)),
        grounded=True,        # chunk_id grounding enforced by consistency_checker
        raw_evidence={
            "linked_norm_evidence_ids": final_state.get("linked_norm_evidence_ids", []),
            "arbitration_decision": final_state.get("arbitration_decision", {}),
            "consistency_passed": final_state.get("consistency_passed", False),
        },
    )
