"""Run-counter metrics: reset/incr/snapshot and attach() provenance stamping."""

from src import metrics
from src.agents.training_agent import _fill_fast_training_defaults


def test_reset_and_incr():
    metrics.reset()
    metrics.incr("llm_calls")
    metrics.incr("llm_calls")
    metrics.incr("retrieval_calls", 3)
    snap = metrics.snapshot()
    assert snap["llm_calls"] == 2
    assert snap["retrieval_calls"] == 3
    assert snap["node_steps"] == 0


def test_attach_populates_state_and_diagnostics():
    metrics.reset()
    metrics.incr("llm_calls")
    metrics.incr("retrieval_calls", 2)
    metrics.incr("node_steps", 5)
    result: dict = {}
    metrics.attach(result, 12.6, "fast")
    assert result["llm_calls"] == 1
    assert result["retrieval_calls"] == 2
    assert result["step_count"] == 5
    diag = result["evidence_diagnostics"]
    assert diag["agent_profile"] == "fast"
    assert diag["wall_seconds"] == 12.6
    assert diag["llm_calls"] == 1


def test_attach_preserves_existing_diagnostics():
    metrics.reset()
    result = {"evidence_diagnostics": {"norm_count": 7}}
    metrics.attach(result, 1.0, "full")
    diag = result["evidence_diagnostics"]
    assert diag["norm_count"] == 7  # not clobbered
    assert diag["agent_profile"] == "full"


def test_fast_fallback_is_topic_agnostic():
    final: dict = {}
    _fill_fast_training_defaults(final, "触电预防", "", ["触电"])
    import json

    blob = json.dumps(final, ensure_ascii=False)
    # No scaffold-dismantling vocabulary should leak into an unrelated topic.
    for leak in ("拆除", "杆件", "架体", "逐层"):
        assert leak not in blob
    assert "触电预防" in blob
