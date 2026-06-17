from pydantic import BaseModel
from typing import Literal, Optional


class NormChunk(BaseModel):
    doc_type: Literal["norm"] = "norm"
    chunk_id: str
    standard_name: str
    chapter: Optional[str] = None
    article_id: Optional[str] = None
    text: str
    scenario_tags: list[str] = []
    hazard_tags: list[str] = []
    requirement_type: Optional[str] = None
    source: Optional[str] = None
    schema_version: str = "norm_v1"
    chunk_kind: Optional[str] = None
    source_name: Optional[str] = None
    source_path: Optional[str] = None
    standard_code: Optional[str] = None
    year: Optional[str] = None
    chapter_no: Optional[str] = None
    chapter_title: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    title: Optional[str] = None
    asset_path: Optional[str] = None
    related_article_id: Optional[str] = None
    content_hash: Optional[str] = None
    pipeline_version: Optional[str] = None


class CaseChunk(BaseModel):
    doc_type: Literal["case"] = "case"
    chunk_id: str
    case_title: str
    accident_type: Optional[str] = None
    scenario_tags: list[str] = []
    hazard_tags: list[str] = []
    process: Optional[str] = None
    causes: Optional[str] = None
    consequences: Optional[str] = None
    corrective_measures: Optional[str] = None
    text: str
    source: Optional[str] = None
    schema_version: str = "case_v1"
    chunk_kind: Optional[str] = None
    case_id: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    related_standards: list[str] = []
    source_org: Optional[str] = None
    source_date: Optional[str] = None
    source_url: Optional[str] = None
    source_path: Optional[str] = None
    content_hash: Optional[str] = None
    pipeline_version: Optional[str] = None
