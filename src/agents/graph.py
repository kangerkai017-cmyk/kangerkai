"""Parent orchestration (Part B): three-tier subgraph + arbitration.

    START → scenario_agent
          → [evidence_subgraph]    (取证: plan + dual retrieval + case→norm link)
          → [authoring_subgraph]   (撰写: fusion → consistency audit)
          → [arbitration_subgraph] (仲裁: deliberate → apply_decision)
                ├─ evidence_subgraph   (证据不足 → 有界定向再检索)
                ├─ authoring_subgraph  (幻觉 → 重新接地，不再检索)
                └─ training_agent → END

The arbitration tier resolves norm_case_conflict deterministically (norm>case,
case demoted + flagged for human review), negotiates more evidence within
dialogue_budget on insufficiency, and re-grounds on hallucination. Loops are
bounded by MAX_RETRIES and dialogue_budget, so the graph always terminates.
"""

from langgraph.graph import StateGraph, START, END

from src import config
from src.schema.state import TrainingState
from src.agents.scenario_agent import run_scenario_agent
from src.agents.training_agent import run_training_agent
from src.agents.arbitration import route_after_arbitration, get_arbitration_subgraph
from src.agents.subgraphs.evidence import get_evidence_subgraph
from src.agents.subgraphs.authoring import get_authoring_subgraph
from src.trace_utils import timed_node


def build_graph() -> StateGraph:
    graph = StateGraph(TrainingState)

    graph.add_node("scenario_agent", timed_node("scenario_agent", run_scenario_agent))
    graph.add_node("evidence_subgraph", get_evidence_subgraph())
    graph.add_node("authoring_subgraph", get_authoring_subgraph())
    graph.add_node("arbitration_subgraph", get_arbitration_subgraph())
    graph.add_node("training_agent", timed_node("training_agent", run_training_agent))

    graph.add_edge(START, "scenario_agent")
    graph.add_edge("scenario_agent", "evidence_subgraph")
    graph.add_edge("evidence_subgraph", "authoring_subgraph")
    # Ablation §5.4: skip arbitration even outside fast mode — treats the
    # authoring subgraph's draft as final.
    if config.AGENT_INTERACTIVE_FAST or not config.ABLATION_ARBITRATION:
        graph.add_edge("authoring_subgraph", "training_agent")
    else:
        graph.add_edge("authoring_subgraph", "arbitration_subgraph")

        graph.add_conditional_edges(
            "arbitration_subgraph",
            route_after_arbitration,
            {
                "evidence_subgraph": "evidence_subgraph",
                "authoring_subgraph": "authoring_subgraph",
                "training_agent": "training_agent",
            },
        )
    graph.add_edge("training_agent", END)
    return graph


def get_compiled_graph():
    return build_graph().compile()
