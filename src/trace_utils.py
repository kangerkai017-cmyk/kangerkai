import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from src import metrics
from src.config import AGENT_TRACE


def trace_enabled() -> bool:
    return AGENT_TRACE


def trace_log(prefix: str, message: str) -> None:
    if trace_enabled():
        print(f"[{prefix}] {message}", flush=True)


def timed_node(name: str, fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
    @wraps(fn)
    def wrapper(state: dict) -> dict:
        metrics.incr("node_steps")
        step = metrics.get("node_steps")
        trace_log("AGENT-NODE", f"START name={name} step={step}")
        t0 = time.perf_counter()
        result = fn(state)
        elapsed = time.perf_counter() - t0
        if isinstance(result, dict):
            keys = sorted(result.keys())
            updates: dict[str, Any] = result
        else:
            keys = []
            updates = {}
        trace_log(
            "AGENT-NODE",
            f"END name={name} step={step} seconds={elapsed:.3f} update_keys={keys}",
        )
        return updates

    return wrapper


def estimate_tokens(text: str) -> int:
    # Mixed Chinese/English prompts in this project average roughly 1.5-2 chars
    # per token; this estimate is only for pre-request trace logs.
    return max(1, int(len(text) / 1.6)) if text else 0
