"""Consistency checker: deterministic grounding is authoritative for hallucination."""

import src.agents.consistency_checker as cc
from src.schema.training import ConsistencyCheckOutput, ConsistencyIssueModel


def _state(cited_norm_id: str):
    return {
        "norm_evidence": [{"chunk_id": "norm::real"}],
        "case_evidence": [],
        "norm_evidence_ids": ["norm::real"],
        "case_evidence_ids": [],
        "evidence_diagnostics": {},
        "retry_count": 0,
        "draft_training_output": {
            "norm_requirements": [{"chunk_id": cited_norm_id}],
            "accident_warnings": [],
        },
    }


def test_llm_hallucination_dropped_when_grounding_clean(monkeypatch):
    # LLM cries hallucination, but the draft only cites a real, retrieved chunk_id.
    monkeypatch.setattr(
        cc,
        "call_llm_json",
        lambda *a, **k: ConsistencyCheckOutput(
            passed=False,
            issues=[ConsistencyIssueModel(type="hallucination", description="x")],
            primary_reason="hallucination",
        ),
    )
    out = cc.run_consistency_checker(_state(cited_norm_id="norm::real"))
    assert out["consistency_passed"] is True
    assert out["retry_reason"] == ""


def test_real_fabricated_citation_still_fails(monkeypatch):
    # Draft cites a chunk_id not in evidence → deterministic grounding flags it,
    # so it must fail regardless of what the LLM says.
    monkeypatch.setattr(
        cc,
        "call_llm_json",
        lambda *a, **k: ConsistencyCheckOutput(passed=True, issues=[], primary_reason=""),
    )
    out = cc.run_consistency_checker(_state(cited_norm_id="norm::fabricated"))
    assert out["consistency_passed"] is False
    assert out["retry_reason"] == "hallucination"


def test_llm_conflict_is_still_honored(monkeypatch):
    # norm_case_conflict is a judgment grounding can't make, so it must survive.
    monkeypatch.setattr(
        cc,
        "call_llm_json",
        lambda *a, **k: ConsistencyCheckOutput(
            passed=False,
            issues=[ConsistencyIssueModel(type="norm_case_conflict", description="冲突")],
            primary_reason="norm_case_conflict",
        ),
    )
    out = cc.run_consistency_checker(_state(cited_norm_id="norm::real"))
    assert out["consistency_passed"] is False
    assert out["retry_reason"] == "norm_case_conflict"
