"""Query rewriter: safe-degrade + success contract (LLM mocked)."""

import src.agents.query_rewriter as qr
from src.schema.training import QueryRewriteOutput


def test_disabled_is_passthrough(monkeypatch):
    monkeypatch.setattr(qr, "QUERY_REWRITE_ENABLED", False)
    out = qr.run_query_rewriter({"norm_queries": ["q"], "case_queries": ["c"]})
    assert out == {}


def test_empty_queries_passthrough(monkeypatch):
    monkeypatch.setattr(qr, "QUERY_REWRITE_ENABLED", True)
    assert qr.run_query_rewriter({"norm_queries": [], "case_queries": []}) == {}


def test_success_rewrites_both_paths(monkeypatch):
    monkeypatch.setattr(qr, "QUERY_REWRITE_ENABLED", True)
    monkeypatch.setattr(
        qr,
        "call_llm_json",
        lambda *a, **k: QueryRewriteOutput(
            norm_queries=["临边作业 防护栏杆 高度 设置要求"],
            case_queries=["脚手架拆除 高处坠落 未挂安全带"],
        ),
    )
    out = qr.run_query_rewriter(
        {"norm_queries": ["高处作业风险"], "case_queries": ["坠落"], "hazards_identified": ["高处坠落"]}
    )
    assert out["norm_queries"] == ["临边作业 防护栏杆 高度 设置要求"]
    assert out["case_queries"] == ["脚手架拆除 高处坠落 未挂安全带"]


def test_llm_failure_degrades_to_original(monkeypatch):
    monkeypatch.setattr(qr, "QUERY_REWRITE_ENABLED", True)

    def _boom(*a, **k):
        raise ValueError("bad json")

    monkeypatch.setattr(qr, "call_llm_json", _boom)
    out = qr.run_query_rewriter({"norm_queries": ["q1"], "case_queries": ["c1"]})
    assert out == {"norm_queries": ["q1"], "case_queries": ["c1"]}


def test_rewrite_queries_core_returns_inputs_on_empty():
    assert qr.rewrite_queries([], []) == ([], [])
