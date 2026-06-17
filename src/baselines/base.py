"""Common types and dispatcher for the 5 baselines."""

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable


# Shared output-length budget for the non-agentic baselines (b1-b4). These ask
# the LLM to emit a *full* TrainingOutput, so without a budget a verbose model
# (notably the local Qwen server at --parallel 1) copies whole retrieved
# norm/case texts into the content fields and runs past max_tokens, producing
# finish_reason=length truncation (-> LLMTruncatedOutputError, invalid rows).
# The budget bounds output length only; it does NOT change the evidence
# assembly mechanism, so the naive-RAG character of these baselines is
# preserved. We deliberately keep them on the full-content path and do NOT give
# them the compact chunk_id + deterministic rehydration of the proposed method,
# which would contaminate the proposed-vs-baseline comparison.
# Knobs are env-tunable for reproducibility; defaults match RETRIEVAL_TOP_K=5.
_BUDGET_HAZARDS = int(os.getenv("BASELINE_MAX_HAZARDS", "6"))
_BUDGET_NORMS = int(os.getenv("BASELINE_MAX_NORMS", "5"))
_BUDGET_CASES = int(os.getenv("BASELINE_MAX_CASES", "5"))
_BUDGET_OPS = int(os.getenv("BASELINE_MAX_OPS", "8"))
_BUDGET_QUIZ = int(os.getenv("BASELINE_MAX_QUIZ", "4"))
_BUDGET_CONTENT_CHARS = int(os.getenv("BASELINE_MAX_CONTENT_CHARS", "80"))

# NOTE: contains a literal '}' — concatenate AFTER USER_TEMPLATE.format(...),
# never embed inside a string that is itself .format()-ed.
OUTPUT_BUDGET = (
    "\n\n【输出长度约束，必须严格遵守】"
    f"expected_hazards 最多 {_BUDGET_HAZARDS} 项；"
    f"norm_requirements 最多 {_BUDGET_NORMS} 项，每项 content 用要点式摘要、"
    f"≤{_BUDGET_CONTENT_CHARS} 字（不要照抄整段条文原文）；"
    f"accident_warnings 最多 {_BUDGET_CASES} 项，每项 summary 与 lesson 各 "
    f"≤{_BUDGET_CONTENT_CHARS} 字；"
    f"operation_points 最多 {_BUDGET_OPS} 项，每项 ≤40 字；"
    f"quiz_questions 最多 {_BUDGET_QUIZ} 题。"
    "其余文本字段简明扼要。最重要：必须输出完整且语法闭合的 JSON（以 } 结束），"
    "不得中途截断。"
)


@dataclass
class BaselineResult:
    """Uniform return shape across all 5 baselines."""
    variant: str
    task_id: str
    training_output: dict           # TrainingOutput-shaped dict
    retrieved_norm_ids: list[str] = field(default_factory=list)
    retrieved_case_ids: list[str] = field(default_factory=list)
    llm_calls: int = 0
    retrieval_calls: int = 0
    elapsed_seconds: float = 0.0
    prompt_chars: int = 0           # captured for cost analysis
    grounded: bool = False          # whether deterministic chunk_id grounding was applied
    raw_evidence: dict = field(default_factory=dict)  # for debugging

    def to_dict(self) -> dict:
        return {
            "variant": self.variant,
            "task_id": self.task_id,
            "training_output": self.training_output,
            "retrieved_norm_ids": self.retrieved_norm_ids,
            "retrieved_case_ids": self.retrieved_case_ids,
            "llm_calls": self.llm_calls,
            "retrieval_calls": self.retrieval_calls,
            "elapsed_seconds": self.elapsed_seconds,
            "prompt_chars": self.prompt_chars,
            "grounded": self.grounded,
        }


# Variant registry filled by each baseline module's import.
BASELINES: dict[str, Callable[[dict, dict[str, Any]], BaselineResult]] = {}


def register(name: str):
    def deco(fn):
        BASELINES[name] = fn
        return fn
    return deco


def run_baseline(variant: str, task: dict, **opts) -> BaselineResult:
    """Top-level dispatch. `task` is a record from training_tasks_v1.jsonl;
    `opts` carries per-variant tunables (e.g. dry_run, top_k)."""
    if variant not in BASELINES:
        raise ValueError(f"unknown variant {variant!r}; choose from {sorted(BASELINES)}")
    t0 = time.perf_counter()
    result = BASELINES[variant](task, opts)
    result.elapsed_seconds = time.perf_counter() - t0
    return result


# Import all baselines so they self-register
from . import b1_llm_only        # noqa: F401,E402
from . import b2_norm_only_rag   # noqa: F401,E402
from . import b3_naive_dual_rag  # noqa: F401,E402
from . import b4_optimized_rag   # noqa: F401,E402
from . import b5_proposed        # noqa: F401,E402
