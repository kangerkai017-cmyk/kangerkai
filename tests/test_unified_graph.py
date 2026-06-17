"""Part H: dual-modal intent routing (no LLM — heuristic + structure)."""

from src.agents.intent_classifier import _heuristic_mode
from src.agents.unified_graph import build_unified_graph, route_by_intent


def test_heuristic_routes_question_to_qa():
    assert _heuristic_mode("脚手架拆除前为什么要设置警戒区？") == "qa"
    assert _heuristic_mode("安全带应该挂在哪个位置") == "qa"


def test_heuristic_routes_training_request_to_training():
    assert _heuristic_mode("脚手架拆除作业前安全培训") == "training"
    assert _heuristic_mode("给工人做一次高处作业班前教育") == "training"


def test_heuristic_training_marker_wins_over_question():
    # An explicit training request that also reads like a question stays training.
    assert _heuristic_mode("如何做一份脚手架拆除培训材料？") == "training"


def test_heuristic_bare_topic_defaults_to_training():
    assert _heuristic_mode("高处作业") == "training"


def test_route_by_intent_reads_mode():
    assert route_by_intent({"mode": "training"}) == "training"
    assert route_by_intent({"mode": "qa"}) == "qa"
    assert route_by_intent({}) == "qa"  # safe default


def test_unified_graph_compiles_with_expected_nodes():
    compiled = build_unified_graph().compile()
    nodes = set(compiled.nodes)
    assert {"intent_classifier", "training_pipeline", "qa_pipeline"} <= nodes
