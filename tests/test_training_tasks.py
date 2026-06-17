"""Contract tests for v1 training task gold set."""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = PROJECT_ROOT / "data" / "eval" / "training_tasks_v1.jsonl"
REPORT_PATH = PROJECT_ROOT / "data" / "eval" / "training_tasks_v1_report.json"
CASE_CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks" / "case_chunks.jsonl"

REQUIRED_FIELDS = {
    "task_id", "theme", "scenario_summary", "expected_hazards",
    "expected_scenario_tags", "expected_norm_refs", "expected_case_refs",
    "expected_training_points", "source_case_id", "source_case_title",
    "source_accident_type", "construction_method",
}
VALID_THEMES = {"高处作业", "脚手架", "起重吊装", "临时用电"}


@pytest.fixture(scope="module")
def tasks() -> list[dict]:
    if not TASKS_PATH.exists():
        pytest.skip(f"{TASKS_PATH} missing; run scripts/build_training_tasks.py")
    return [json.loads(line) for line in TASKS_PATH.open(encoding="utf-8") if line.strip()]


@pytest.fixture(scope="module")
def case_ids() -> set[str]:
    if not CASE_CHUNKS_PATH.exists():
        pytest.skip("case_chunks.jsonl missing")
    ids = set()
    for line in CASE_CHUNKS_PATH.open(encoding="utf-8"):
        if line.strip():
            ids.add(json.loads(line)["case_id"])
    return ids


def test_nonempty(tasks):
    assert len(tasks) >= 30, f"expected ≥30 v1 tasks, got {len(tasks)}"


def test_tier_meta_present(tasks):
    for t in tasks:
        tier = t.get("_meta", {}).get("tier")
        assert tier in {"S", "W"}, f"{t['task_id']} invalid tier {tier!r}"


def test_required_fields(tasks):
    for t in tasks:
        missing = REQUIRED_FIELDS - set(t.keys())
        assert not missing, f"{t.get('task_id')} missing fields: {missing}"


def test_task_ids_unique(tasks):
    ids = [t["task_id"] for t in tasks]
    assert len(ids) == len(set(ids)), "duplicate task_id"


def test_themes_valid(tasks):
    for t in tasks:
        assert t["theme"] in VALID_THEMES, f"{t['task_id']} invalid theme {t['theme']}"


def test_source_case_in_library(tasks, case_ids):
    for t in tasks:
        assert t["source_case_id"] in case_ids, (
            f"{t['task_id']} source_case_id {t['source_case_id']} not in case library"
        )


def test_expected_case_refs_in_library(tasks, case_ids):
    for t in tasks:
        for cid in t["expected_case_refs"]:
            assert cid in case_ids, f"{t['task_id']} expected_case_ref {cid} not in library"


def test_expected_norm_refs_format(tasks):
    """All v1 norm refs are article-level (CODE:article_id), not standard-only
    or law-name. The v1 builder requires this for deterministic extraction."""
    for t in tasks:
        assert t["expected_norm_refs"], f"{t['task_id']} has empty expected_norm_refs"
        for ref in t["expected_norm_refs"]:
            assert ":" in ref, f"{t['task_id']} non-article ref {ref}"
            assert not ref.startswith("《"), f"{t['task_id']} law-name ref {ref}"


def test_training_points_grounded(tasks):
    """Every training point must cite a norm ref that's in the task's
    expected_norm_refs set (deterministic grounding by construction)."""
    for t in tasks:
        valid_refs = set(t["expected_norm_refs"])
        assert t["expected_training_points"], f"{t['task_id']} has no training points"
        for p in t["expected_training_points"]:
            assert "text" in p and "source_norm_ref" in p
            assert p["text"].strip(), f"{t['task_id']} empty training point text"
            assert p["source_norm_ref"] in valid_refs, (
                f"{t['task_id']} training point source_norm_ref "
                f"{p['source_norm_ref']} not in expected_norm_refs"
            )


def test_scenario_summary_substantive(tasks):
    for t in tasks:
        assert len(t["scenario_summary"]) >= 20, (
            f"{t['task_id']} scenario_summary too short"
        )


def test_construction_method_consistent(tasks):
    for t in tasks:
        assert t["construction_method"] == "deterministic_v1"


def test_report_consistent_with_jsonl(tasks):
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["task_count"] == len(tasks)
    counts_by_theme: dict[str, int] = {}
    for t in tasks:
        counts_by_theme[t["theme"]] = counts_by_theme.get(t["theme"], 0) + 1
    assert report["by_theme"] == counts_by_theme
