"""Process-level run counters for measuring a single agent invocation.

Why module-level (not LangGraph state): retrieval and the two retrievers run in
parallel branches, and the true LLM-call count must include JSON retries and the
json_schema→plain fallback — neither is visible to a per-node state delta. A
lock-protected counter incremented at the actual call sites (call_llm, _retrieve,
timed_node) captures the real cost. Bracket one run with reset()/snapshot().

Assumes runs are sequential within a process (this project's CLI/UI/eval are).
"""

import threading

_lock = threading.Lock()
_counts = {"llm_calls": 0, "retrieval_calls": 0, "node_steps": 0}


def reset() -> None:
    with _lock:
        for key in _counts:
            _counts[key] = 0


def incr(name: str, n: int = 1) -> None:
    with _lock:
        _counts[name] = _counts.get(name, 0) + n


def get(name: str) -> int:
    with _lock:
        return _counts.get(name, 0)


def snapshot() -> dict:
    with _lock:
        return dict(_counts)


def attach(result: dict, wall_seconds: float, profile: str) -> dict:
    """Populate the run-counter state fields and stamp run provenance onto
    evidence_diagnostics, so every result self-describes which pipeline produced
    it and what it cost. `profile` is the caller's topology label (fast/full)."""
    snap = snapshot()
    result["llm_calls"] = snap["llm_calls"]
    result["retrieval_calls"] = snap["retrieval_calls"]
    result["step_count"] = snap["node_steps"]
    diag = result.get("evidence_diagnostics")
    if not isinstance(diag, dict):
        diag = {}
    diag.update(
        {
            "agent_profile": profile,
            "wall_seconds": wall_seconds,
            "llm_calls": snap["llm_calls"],
            "retrieval_calls": snap["retrieval_calls"],
            "node_steps": snap["node_steps"],
        }
    )
    result["evidence_diagnostics"] = diag
    return result
