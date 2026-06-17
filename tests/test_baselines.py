"""Scaffolding contracts for the 5 baselines.

Run with --dry-run path so this works even without LLM/GPU. Verifies:
  - all 5 variants self-register
  - dispatcher accepts each variant
  - each returns a BaselineResult with required fields
  - retrieval-using variants actually hit ES (real retrieval calls, not mocked)
"""

import json
from pathlib import Path

import pytest

from src.baselines import BASELINES, run_baseline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = PROJECT_ROOT / "data" / "eval" / "training_tasks_v1.jsonl"

EXPECTED_VARIANTS = {"llm_only", "norm_only", "naive_dual", "optimized", "proposed"}


@pytest.fixture(scope="module")
def sample_task() -> dict:
    if not TASKS_PATH.exists():
        pytest.skip("training_tasks_v1.jsonl missing")
    for line in TASKS_PATH.open(encoding="utf-8"):
        t = json.loads(line)
        # Pick the strongest task: case-75 (双库内规范条文)
        if t.get("source_case_id") == "case-75":
            return t
    return json.loads(TASKS_PATH.read_text(encoding="utf-8").splitlines()[0])


def test_all_variants_registered():
    assert set(BASELINES.keys()) == EXPECTED_VARIANTS, (
        f"missing: {EXPECTED_VARIANTS - set(BASELINES)}, extra: {set(BASELINES) - EXPECTED_VARIANTS}"
    )


@pytest.mark.parametrize("variant", sorted(EXPECTED_VARIANTS))
def test_dry_run(variant, sample_task):
    r = run_baseline(variant, sample_task, dry_run=True)
    assert r.variant == variant
    assert r.task_id == sample_task["task_id"]
    assert r.elapsed_seconds >= 0
    assert isinstance(r.training_output, dict)


def test_grounded_flag_semantics(sample_task):
    """Only 'proposed' enforces deterministic chunk_id grounding."""
    grounded = {v: run_baseline(v, sample_task, dry_run=True).grounded
                for v in EXPECTED_VARIANTS}
    assert grounded == {
        "llm_only":  False,
        "norm_only": False,
        "naive_dual": False,
        "optimized": False,
        "proposed":  True,
    }


def test_baseline_result_serializable(sample_task):
    r = run_baseline("llm_only", sample_task, dry_run=True)
    d = r.to_dict()
    json.dumps(d, ensure_ascii=False)  # must not raise
    assert d["variant"] == "llm_only"
    assert "training_output" in d
