from typing import Literal
from pydantic import BaseModel, Field, model_validator


class EvidenceRef(BaseModel):
    chunk_id: str = ""
    standard_code: str = ""
    article_id: str = ""
    title: str = ""
    content: str = ""
    source: str = ""
    source_path: str = ""


class NormRequirement(EvidenceRef):
    requirement_type: str = ""
    linked_from_case: list[str] = Field(default_factory=list)


class CaseWarning(BaseModel):
    chunk_id: str = ""
    case_id: str = ""
    case_title: str = ""
    summary: str = ""
    consequence: str = ""
    lesson: str = ""
    source: str = ""
    source_path: str = ""


class EvidenceIdRef(BaseModel):
    chunk_id: str = ""


class CaseIdRef(BaseModel):
    chunk_id: str = ""


class FusedEvidence(BaseModel):
    scene_summary: str = ""
    risk_analysis: str = ""
    norm_requirements: list[NormRequirement] = Field(default_factory=list)
    case_warnings: list[CaseWarning] = Field(default_factory=list)
    preventive_measures: list[str] = Field(default_factory=list)


class FusedEvidenceCompact(BaseModel):
    scene_summary: str = ""
    risk_analysis: str = ""
    norm_requirements: list[EvidenceIdRef] = Field(default_factory=list)
    case_warnings: list[CaseIdRef] = Field(default_factory=list)
    preventive_measures: list[str] = Field(default_factory=list)


class QuizItem(BaseModel):
    type: str = "choice"       # choice / true_false / short_answer
    question: str = ""
    options: list[str] = Field(default_factory=list)
    answer: str = ""
    explanation: str = ""


class ConsistencyIssueModel(BaseModel):
    type: Literal[
        "hallucination", "evidence_insufficient", "norm_case_conflict", ""
    ] = ""
    description: str = ""
    location: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_type(cls, data: dict) -> dict:
        if isinstance(data, dict) and data.get("type"):
            raw = str(data["type"]).strip().lower().replace(" ", "_")
            allowed = {"hallucination", "evidence_insufficient", "norm_case_conflict"}
            data["type"] = raw if raw in allowed else ""
        return data


class TrainingOutput(BaseModel):
    scenario_description: str = ""
    hazard_identification_question: str = ""
    expected_hazards: list[str] = Field(default_factory=list)
    norm_requirements: list[NormRequirement] = Field(default_factory=list)
    accident_warnings: list[CaseWarning] = Field(default_factory=list)
    operation_points: list[str] = Field(default_factory=list)
    learner_evaluation_guide: str = ""
    remedial_feedback_guide: str = ""
    quiz_questions: list[QuizItem] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_list_items(cls, data: dict) -> dict:
        """Weaker models (notably local Qwen on the terse RAG-baseline prompts)
        sometimes emit object-typed list fields as bare strings, e.g.
        quiz_questions=["问题1", ...] instead of [{"question": "问题1"}, ...].
        The JSON is well-formed but fails schema validation. Normalize bare
        strings into the expected sub-object so a format slip does not discard
        otherwise-usable content. This is model/variant-agnostic ingestion
        robustness; it does not alter prompts or inject evidence."""
        if not isinstance(data, dict):
            return data
        for key, str_field in (
            ("quiz_questions", "question"),
            ("norm_requirements", "content"),
            ("accident_warnings", "summary"),
        ):
            items = data.get(key)
            if isinstance(items, list):
                data[key] = [
                    {str_field: it} if isinstance(it, str) else it
                    for it in items
                ]
        return data


class TrainingCompactOutput(BaseModel):
    scenario_description: str = ""
    hazard_identification_question: str = ""
    expected_hazards: list[str] = Field(default_factory=list)
    norm_requirements: list[EvidenceIdRef] = Field(default_factory=list)
    accident_warnings: list[CaseIdRef] = Field(default_factory=list)
    operation_points: list[str] = Field(default_factory=list)
    learner_evaluation_guide: str = ""
    remedial_feedback_guide: str = ""
    quiz_questions: list[QuizItem] = Field(default_factory=list)


class FusionResult(BaseModel):
    fused_evidence: FusedEvidence = Field(default_factory=FusedEvidence)
    draft_training_output: TrainingOutput = Field(default_factory=TrainingOutput)


class FusionCompactResult(BaseModel):
    fused_evidence: FusedEvidenceCompact = Field(default_factory=FusedEvidenceCompact)
    draft_training_output: TrainingCompactOutput = Field(default_factory=TrainingCompactOutput)


class ScenarioOutput(BaseModel):
    training_scenario: str


class RiskPlanOutput(BaseModel):
    hazards_identified: list[str]
    norm_queries: list[str]
    case_queries: list[str]


class QueryRewriteOutput(BaseModel):
    norm_queries: list[str] = Field(default_factory=list)
    case_queries: list[str] = Field(default_factory=list)


class ConsistencyCheckOutput(BaseModel):
    passed: bool
    issues: list[ConsistencyIssueModel] = Field(default_factory=list)
    primary_reason: Literal[
        "hallucination", "evidence_insufficient", "norm_case_conflict", ""
    ] = ""
    summary: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_reason(cls, data: dict) -> dict:
        if isinstance(data, dict):
            raw = (data.get("primary_reason") or "").strip()
            if raw:
                key = raw.lower().replace(" ", "_")
                allowed = {"hallucination", "evidence_insufficient", "norm_case_conflict"}
                data["primary_reason"] = key if key in allowed else ""
        return data
