import json

from src.agents.evidence_formatter import (
    build_evidence_diagnostics,
    compact_draft_for_prompt,
    format_case_evidence,
    format_case_evidence_index,
    format_norm_evidence,
    format_norm_evidence_index,
    to_case_warnings,
    to_norm_requirements,
)
from src.prompts import checker as checker_prompts
from src.prompts import fusion as fusion_prompts
from src.prompts import training


def _synthetic_evidence(n_norm: int = 10, n_case: int = 5):
    norm = [
        {
            "chunk_id": f"norm::JGJ-80-2016::article::{i}.0.{i}",
            "standard_code": "JGJ-80-2016",
            "article_id": f"{i}.0.{i}",
            "title": f"高处作业安全条文{i}",
            "chunk_kind": "article",
            "requirement_type": "操作要求",
            "source_name": "JGJ 80-2016",
            "source_path": "rag_data/rag_data/JGJ 80-2016/ch.pdf",
            "text": f"{i}.0.{i} 高处作业时应采取防坠落措施，作业人员必须正确佩戴安全带并高挂低用。" * 4,
        }
        for i in range(1, n_norm + 1)
    ]
    case = [
        {
            "chunk_id": f"case::case-{i:02d}::case_summary",
            "case_id": f"case-{i:02d}",
            "case_title": f"某工地高处坠落事故{i}",
            "accident_type": "高处坠落",
            "chunk_kind": "case_summary",
            "source_org": "某住建局",
            "source_date": "2023-01-01",
            "source_path": "data/事故案例收集.md",
            "process": "工人在脚手架作业未系安全带发生坠落" * 5,
            "causes": "未系挂安全带、临边无防护" * 4,
            "consequences": "1人死亡",
            "corrective_measures": "落实临边防护与安全带使用",
        }
        for i in range(1, n_case + 1)
    ]
    return norm, case


def test_agent_prompts_stay_within_token_budget():
    """Part F: each LLM-facing prompt must stay well under the speed budget
    (~6000 tokens). Catches regressions like re-stuffing full evidence indexes
    or restoring indent=2 / 2000-char evidence."""
    norm, case = _synthetic_evidence()
    diag = build_evidence_diagnostics(
        retrieval_mode="rrf_hybrid",
        norm_evidence=norm,
        case_evidence=case,
        case_index_available=True,
    )
    nr = to_norm_requirements(norm)
    cw = to_case_warnings(case)
    fused = {
        "scene_summary": "脚手架拆除高处作业",
        "risk_analysis": "高坠风险",
        "norm_requirements": nr,
        "case_warnings": cw,
        "preventive_measures": ["系好安全带", "设置临边防护"],
    }
    draft = {
        "scenario_description": "脚手架拆除",
        "hazard_identification_question": "有哪些风险",
        "expected_hazards": ["高处坠落"],
        "norm_requirements": nr,
        "accident_warnings": cw,
        "operation_points": ["作业前检查"] * 5,
        "learner_evaluation_guide": "x",
        "remedial_feedback_guide": "y",
        "quiz_questions": [],
    }
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))

    fusion_prompt = fusion_prompts.USER.format(
        scenario="s",
        hazards="[]",
        norm_evidence=format_norm_evidence(norm),
        case_evidence=format_case_evidence(case),
        evidence_diagnostics=j(diag),
    )
    checker_prompt = checker_prompts.USER.format(
        draft=j(compact_draft_for_prompt(draft)),
        norm_evidence=format_norm_evidence_index(norm),
        case_evidence=format_case_evidence_index(case),
        evidence_diagnostics=j(diag),
    )
    training_prompt = training.USER.format(
        topic="t",
        scenario="s",
        hazards="[]",
        fused_evidence=j(fused),
        evidence_diagnostics=j(diag),
        consistency_passed="是",
        consistency_issues="[]",
        draft=j(compact_draft_for_prompt(draft)),
    )

    # ~1.6 chars/token for mixed zh; assert a conservative token ceiling.
    for name, prompt in [
        ("fusion", fusion_prompt),
        ("checker", checker_prompt),
        ("training", training_prompt),
    ]:
        est_tokens = len(prompt) / 1.6
        assert est_tokens < 6500, f"{name} prompt too large: ~{est_tokens:.0f} tokens"


def test_training_prompt_placeholders_match_training_agent_inputs():
    # Training relies on the already-grounded fused_evidence; the full evidence
    # indexes were removed to compress the prompt (Part F).
    prompt = training.USER.format(
        topic="脚手架拆除",
        scenario="场景",
        hazards="[]",
        fused_evidence='{"norm_requirements":[{"chunk_id":"norm::demo"}]}',
        evidence_diagnostics="{}",
        consistency_passed="是",
        consistency_issues="[]",
        draft="{}",
    )

    assert "norm::demo" in prompt
    assert "融合后的培训证据" in prompt
    # the duplicated full-evidence indexes must no longer be stuffed in
    assert "原始规范证据索引" not in prompt
    assert "{norm_evidence_index}" not in prompt
