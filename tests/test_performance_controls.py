import pytest

from src.agents.qa_agent import run_qa_agent
from src.agents.qa_planner import run_qa_planner
from src.agents.risk_planner import run_risk_planner
from src.agents.training_agent import run_training_agent
from src.llm_utils import LLMTruncatedOutputError
from src.schema.qa import QACompactOutput


def test_qa_agent_backfills_full_citations_from_compact_ids(monkeypatch):
    norm = {
        "chunk_id": "norm::GB-55023-2022::article::5.1.2",
        "standard_code": "GB-55023-2022",
        "article_id": "5.1.2",
        "title": "脚手架拆除警戒",
        "text": "在搭设和拆除脚手架作业时，应设置安全警戒线、警戒标志，并应由专人监护。",
        "requirement_type": "强制性要求",
        "standard_name": "施工脚手架通用规范",
        "source_path": "norm.pdf",
    }
    case = {
        "chunk_id": "case::case-07::summary",
        "case_id": "case-07",
        "case_title": "脚手架拆除高坠事故",
        "process": "作业人员在拆除脚手架过程中坠落。",
        "consequences": "1人死亡",
        "corrective_measures": "拆除作业应设警戒区并专人监护。",
        "source_org": "住建局",
        "source_path": "case.md",
    }

    def fake_llm_json(*args, **kwargs):
        assert kwargs["response_model"] is QACompactOutput
        return QACompactOutput(
            answer_text="设置警戒区是为了隔离坠物和人员误入风险。",
            cited_norm_ids=[norm["chunk_id"], "fake"],
            cited_case_ids=[case["chunk_id"]],
            confidence="high",
            evidence_gap="",
        )

    monkeypatch.setattr("src.agents.qa_agent.call_llm_json", fake_llm_json)

    result = run_qa_agent({
        "question": "脚手架拆除前为什么要设置警戒区？",
        "norm_evidence": [norm],
        "case_evidence": [case],
        "norm_evidence_ids": [norm["chunk_id"]],
        "case_evidence_ids": [case["chunk_id"]],
        "linked_norm_evidence_ids": [],
    })["final_qa_output"]

    assert result["answer_text"].startswith("设置警戒区")
    assert [item["chunk_id"] for item in result["cited_norms"]] == [norm["chunk_id"]]
    assert [item["chunk_id"] for item in result["cited_cases"]] == [case["chunk_id"]]
    assert result["cited_norms"][0]["content"].startswith("在搭设和拆除脚手架作业时")


def test_qa_agent_degrades_to_evidence_answer_when_llm_truncated(monkeypatch):
    norm = {
        "chunk_id": "norm::GB-55023-2022::article::5.1.2",
        "standard_code": "GB-55023-2022",
        "article_id": "5.1.2",
        "title": "脚手架拆除警戒",
        "text": "在搭设和拆除脚手架作业时，应设置安全警戒线、警戒标志，并应由专人监护。",
        "requirement_type": "强制性要求",
        "standard_name": "施工脚手架通用规范",
    }

    def truncated(*args, **kwargs):
        raise LLMTruncatedOutputError("QACompactOutput", "length")

    monkeypatch.setattr("src.agents.qa_agent.call_llm_json", truncated)

    result = run_qa_agent({
        "question": "脚手架拆除前为什么要设置警戒区？",
        "norm_evidence": [norm],
        "case_evidence": [],
        "norm_evidence_ids": [norm["chunk_id"]],
        "case_evidence_ids": [],
        "linked_norm_evidence_ids": [],
    })["final_qa_output"]

    assert "根据检索到的规范" in result["answer_text"]
    assert result["cited_norms"][0]["chunk_id"] == norm["chunk_id"]
    assert result["evidence_gap"] == "LLM 输出被截断，已退回基于检索证据的简要回答"


def test_call_llm_json_does_not_retry_truncated_output(monkeypatch):
    import src.llm_utils as llm_utils

    calls = []

    def truncated(*args, **kwargs):
        calls.append(1)
        raise LLMTruncatedOutputError("IntentOutput", "length")

    monkeypatch.setattr(llm_utils, "_call_llm_with_fallback", truncated)

    with pytest.raises(LLMTruncatedOutputError):
        llm_utils.call_llm_json("prompt", response_model=QACompactOutput)

    assert len(calls) == 1


def test_qa_planner_is_deterministic_without_llm(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("QA planner should not call the LLM in interactive mode")

    monkeypatch.setattr("src.agents.qa_planner.call_llm_json", fail_if_called)

    result = run_qa_planner({"question": "脚手架拆除前为什么要设置警戒区？"})

    assert result["norm_queries"]
    assert result["case_queries"]
    assert any("脚手架拆除前为什么要设置警戒区" in q for q in result["norm_queries"])


def test_risk_planner_degrades_to_topic_queries_when_llm_truncated(monkeypatch):
    def truncated(*args, **kwargs):
        raise LLMTruncatedOutputError("RiskPlanOutput", "length")

    monkeypatch.setattr("src.agents.risk_planner.call_llm_json", truncated)

    result = run_risk_planner({
        "topic": "脚手架拆除安全培训",
        "training_scenario": "脚手架拆除作业",
        "retry_count": 0,
        "consistency_issues": [],
        "evidence_request": None,
    })

    assert "高处坠落" in result["hazards_identified"]
    assert result["norm_queries"]
    assert result["case_queries"]


def test_training_agent_fast_mode_uses_grounded_draft_without_llm(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("training fast mode should not call final LLM")

    monkeypatch.setattr("src.agents.training_agent.call_llm_json", fail_if_called)
    draft = {
        "scenario_description": "脚手架拆除作业前交底。",
        "hazard_identification_question": "有哪些风险？",
        "expected_hazards": ["高处坠落"],
        "norm_requirements": [{"chunk_id": "norm::x"}],
        "accident_warnings": [],
        "operation_points": ["作业前：设置警戒区"],
        "learner_evaluation_guide": "能说出警戒区要求即为合格。",
        "remedial_feedback_guide": "漏答警戒区时补充说明。",
        "quiz_questions": [],
    }

    result = run_training_agent({
        "topic": "脚手架拆除安全培训",
        "training_scenario": "",
        "hazards_identified": [],
        "fused_evidence": {"norm_requirements": [{"chunk_id": "norm::x"}], "case_warnings": []},
        "draft_training_output": draft,
        "consistency_passed": False,
        "consistency_issues": [],
    })["final_training_output"]

    assert result["scenario_description"] == draft["scenario_description"]
    assert result["norm_requirements"][0]["chunk_id"] == "norm::x"


def test_training_agent_fast_mode_fills_empty_draft_fields(monkeypatch):
    monkeypatch.setattr(
        "src.agents.training_agent.call_llm_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no LLM")),
    )

    result = run_training_agent({
        "topic": "脚手架拆除安全培训",
        "training_scenario": "脚手架拆除作业前，班组进行安全交底。",
        "hazards_identified": ["高处坠落", "物体打击"],
        "fused_evidence": {"norm_requirements": [{"chunk_id": "norm::x"}], "case_warnings": []},
        "draft_training_output": {
            "scenario_description": "",
            "hazard_identification_question": "",
            "expected_hazards": [],
            "norm_requirements": [],
            "accident_warnings": [],
            "operation_points": [],
            "learner_evaluation_guide": "",
            "remedial_feedback_guide": "",
            "quiz_questions": [],
        },
        "consistency_passed": False,
        "consistency_issues": [],
    })["final_training_output"]

    assert result["scenario_description"]
    assert result["operation_points"]
    assert result["learner_evaluation_guide"]
    assert result["norm_requirements"] == [{"chunk_id": "norm::x"}]
