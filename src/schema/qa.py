from typing import TypedDict, Optional, Literal
from pydantic import BaseModel, Field

from src.schema.training import NormRequirement, CaseWarning


class QAState(TypedDict):
    question: str
    step_count: int
    llm_calls: int
    retrieval_calls: int
    norm_queries: list[str]
    case_queries: list[str]
    norm_evidence: list[dict]
    case_evidence: list[dict]
    norm_evidence_ids: list[str]
    case_evidence_ids: list[str]
    linked_norm_evidence_ids: list[str]
    case_index_available: bool
    evidence_diagnostics: dict
    final_qa_output: Optional[dict]


class QAPlanOutput(BaseModel):
    norm_queries: list[str] = Field(default_factory=list)
    case_queries: list[str] = Field(default_factory=list)


class QAOutput(BaseModel):
    answer_text: str = ""
    cited_norms: list[NormRequirement] = Field(default_factory=list)
    cited_cases: list[CaseWarning] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    evidence_gap: str = ""


class QACompactOutput(BaseModel):
    answer_text: str = ""
    cited_norm_ids: list[str] = Field(default_factory=list)
    cited_case_ids: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    evidence_gap: str = ""
