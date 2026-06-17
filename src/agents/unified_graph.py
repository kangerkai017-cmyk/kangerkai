"""Top-level dual-modal orchestration: intent routing over a shared substrate.

    START → intent_classifier → {
              "training" → [training_pipeline]  (Mode A: 取证→撰写→仲裁→training_agent)
              "qa"       → [qa_pipeline]         (Mode B: plan→[norm∥case]→link→answer)
            } → END

One agent, one entry point. The classifier dispatches to one of two
self-contained compiled pipelines that share the same grounded evidence
substrate (RRF retrieval + case→norm linking + deterministic chunk_id
grounding). Orchestration effort scales with task stakes: training invokes the
full three-tier deliberation; q&a takes the lightweight linear path.
"""

from langgraph.graph import StateGraph, START, END

from src.schema.unified import UnifiedState
from src.agents.intent_classifier import run_intent_classifier
from src.agents.graph import get_compiled_graph
from src.agents.qa_graph import get_compiled_qa_graph
from src.trace_utils import timed_node


def route_by_intent(state: UnifiedState) -> str:
    return state.get("mode") or "qa"


def build_unified_graph() -> StateGraph:
    graph = StateGraph(UnifiedState)

    graph.add_node("intent_classifier", timed_node("intent_classifier", run_intent_classifier))
    graph.add_node("training_pipeline", get_compiled_graph())
    graph.add_node("qa_pipeline", get_compiled_qa_graph())

    graph.add_edge(START, "intent_classifier")
    graph.add_conditional_edges(
        "intent_classifier",
        route_by_intent,
        {
            "training": "training_pipeline",
            "qa": "qa_pipeline",
        },
    )
    graph.add_edge("training_pipeline", END)
    graph.add_edge("qa_pipeline", END)

    return graph


def get_compiled_unified_graph():
    return build_unified_graph().compile()
