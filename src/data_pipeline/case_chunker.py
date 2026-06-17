"""Accident-case chunk pipeline (case_v1).

Parses the human-curated `data/事故案例收集.md` (one accident per
`### 案例 N：title` heading, with `- **field**：value` rows) into CaseChunk
records and writes them to `data/chunks/case_chunks.jsonl` with an import
report. Mirrors norm_chunker's build/write/load/validate/report contract so the
case library flows through the SAME Elasticsearch/RRF retrieval path.

Per the data's shape (short, uniformly structured cases, no rectification field,
a high-value 违反规范 field) each case yields TWO chunks:
  - case_summary: overview + process + casualties + loss + violated standards
  - case_cause:   direct + indirect cause analysis
The 违反规范 field is parsed into `related_standards` (normalized
standard_code:article refs) so a retrieved case can be cross-linked back to the
norm library — the core value of the dual-evidence (norm + case) design.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.schema import CaseChunk
from src.tags import (
    hazard_fallback,
    hazard_tags_for_text,
    scenario_fallback,
    scenario_tags_for_text,
)

SCHEMA_VERSION = "case_v1"
PIPELINE_VERSION = "case_chunker_v1"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CASE_SOURCE_PATH = PROJECT_ROOT / "data" / "事故案例收集.md"
CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"
CASE_CHUNKS_PATH = CHUNKS_DIR / "case_chunks.jsonl"
IMPORT_REPORT_PATH = CHUNKS_DIR / "case_import_report.json"

# Accident-type label from the case title (most reliable signal). First match
# wins; order matters so specific types beat the generic 坠落/跌落 → 高处坠落.
ACCIDENT_TYPE_RULES: list[tuple[str, str]] = [
    ("坍塌", "坍塌"),
    ("触电", "触电"),
    ("起重伤害", "起重伤害"),
    ("机械伤害", "机械伤害"),
    ("物体打击", "物体打击"),
    ("高处坠落", "高处坠落"),
    ("高坠", "高处坠落"),
    ("坠落", "高处坠落"),
    ("跌落", "高处坠落"),
]

_FIELD_RE = re.compile(r"^[-*]\s*\*\*(.+?)\*\*\s*[:：]\s*(.*)$")
_HEADING_RE = re.compile(r"^#{2,4}\s*案例\s*(\d+)\s*[：:]\s*(.+?)\s*$")
_DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_ARTICLE_RE = re.compile(r"第?\s*(\d+(?:\.\d+)+)\s*条")
_LAW_RE = re.compile(r"《[^》]+》")
# Standard token: GB / JGJ / JG (+ optional /T), 3-5 digit number (+ optional
# .sub), dash or em-dash, 2-4 digit year. Covers 'JGJ 80-2016', 'JGJ80-2016',
# 'GB 6095-2021', 'GB/T50319-2013', 'JG/T5006-92', 'GB 39800.6—2023'.
_STD_RE = re.compile(
    r"[A-Za-z]{2,3}\s*/?\s*[Tt]?\s*\d{2,5}(?:\.\d+)?\s*[-—－]\s*\d{2,4}"
)


@dataclass
class CaseRecord:
    number: int
    title: str
    fields: dict[str, str] = field(default_factory=dict)


def build_case_chunks(source_path: Path = CASE_SOURCE_PATH) -> list[CaseChunk]:
    records = _parse_cases(source_path)
    rel_source = _rel(source_path)
    chunks: list[CaseChunk] = []
    for rec in records:
        chunks.extend(_build_case_chunks_for(rec, rel_source))
    return chunks


def _parse_cases(source_path: Path) -> list[CaseRecord]:
    text = source_path.read_text(encoding="utf-8")
    records: list[CaseRecord] = []
    current: CaseRecord | None = None
    last_field: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        heading = _HEADING_RE.match(line.strip())
        if heading:
            if current:
                records.append(current)
            current = CaseRecord(number=int(heading.group(1)), title=heading.group(2).strip())
            last_field = None
            continue
        if current is None:
            continue
        m = _FIELD_RE.match(line.strip())
        if m:
            key = m.group(1).strip()
            current.fields[key] = m.group(2).strip()
            last_field = key
            continue
        # Continuation line (multi-line field value, no leading bullet).
        stripped = line.strip()
        if last_field and stripped and not stripped.startswith("---"):
            current.fields[last_field] = (current.fields[last_field] + " " + stripped).strip()
    if current:
        records.append(current)
    return records


def _build_case_chunks_for(rec: CaseRecord, rel_source: str) -> list[CaseChunk]:
    f = rec.fields
    case_id = f"case-{rec.number:02d}"
    title = rec.title
    location = f.get("地点", "")
    process = f.get("事故经过", "")
    direct = f.get("直接原因", "")
    indirect = f.get("间接原因", "")
    casualties = f.get("伤亡情况", "")
    loss = f.get("直接经济损失", "")
    source_org = f.get("来源", "")
    source_url = _extract_url(f.get("原文链接", ""))
    source_date = _normalize_date(f.get("时间", ""))
    violated_raw = f.get("违反规范", "")
    related = _parse_related_standards(violated_raw)
    accident_type = _accident_type(title, f)

    full_text = " ".join([title, location, process, direct, indirect, violated_raw])
    scenario_tags = scenario_tags_for_text(full_text) or scenario_fallback()
    hazard_tags = hazard_tags_for_text(full_text, scenario_tags) or hazard_fallback(scenario_tags)

    causes = _join_causes(direct, indirect)
    consequences = _join_nonempty([("伤亡", casualties), ("直接经济损失", loss)], sep="；")

    summary_text = _compose_summary_text(
        title, accident_type, source_date, location, process,
        casualties, loss, violated_raw, source_org,
    )
    cause_text = _compose_cause_text(title, direct, indirect)

    base = dict(
        case_id=case_id,
        case_title=title,
        title=title,
        accident_type=accident_type,
        scenario_tags=scenario_tags,
        hazard_tags=hazard_tags,
        location=location or None,
        related_standards=related,
        source=source_org or None,
        source_org=source_org or None,
        source_date=source_date or None,
        source_url=source_url or None,
        source_path=rel_source,
        pipeline_version=PIPELINE_VERSION,
    )

    summary = CaseChunk(
        chunk_id=f"case::{case_id}::summary",
        chunk_kind="case_summary",
        process=process or None,
        consequences=consequences or None,
        text=summary_text,
        content_hash=_sha256(summary_text),
        **base,
    )
    chunks = [summary]
    if causes:
        cause = CaseChunk(
            chunk_id=f"case::{case_id}::cause",
            chunk_kind="case_cause",
            causes=causes,
            text=cause_text,
            content_hash=_sha256(cause_text),
            **base,
        )
        chunks.append(cause)
    return chunks


def _compose_summary_text(
    title, accident_type, date, location, process,
    casualties, loss, violated, source_org,
) -> str:
    lines = [f"案例：{title}"]
    meta = _join_nonempty([("类型", accident_type), ("日期", date)], sep=" | ")
    if meta:
        lines.append(meta)
    if location:
        lines.append(f"地点：{location}")
    if process:
        lines.append(f"经过：{process}")
    cons = _join_nonempty([("伤亡", casualties), ("损失", loss)], sep=" | ")
    if cons:
        lines.append(cons)
    if violated:
        lines.append(f"违反规范：{violated}")
    if source_org:
        lines.append(f"来源：{source_org}")
    return "\n".join(lines)


def _compose_cause_text(title, direct, indirect) -> str:
    lines = [f"案例：{title}（原因）"]
    if direct:
        lines.append(f"直接原因：{direct}")
    if indirect:
        lines.append(f"间接原因：{indirect}")
    return "\n".join(lines)


def _join_causes(direct: str, indirect: str) -> str:
    return _join_nonempty([("直接原因", direct), ("间接原因", indirect)], sep="；")


def _join_nonempty(pairs: list[tuple[str, str]], sep: str) -> str:
    return sep.join(f"{label}：{val}" for label, val in pairs if val)


def _accident_type(title: str, fields: dict[str, str]) -> str:
    hay = title + " " + fields.get("事故经过", "")
    for needle, label in ACCIDENT_TYPE_RULES:
        if needle in hay:
            return label
    return "其他"


def _parse_related_standards(violated: str) -> list[str]:
    """Parse the 违反规范 string into normalized 'CODE:article' refs (plus raw
    law names). Best-effort: codes are normalized toward the norm library form
    (e.g. 'JGJ 80-2016'→'JGJ-80-2016', 'JGJ/T 46-2024'→'JGJ-T46-2024')."""
    if not violated:
        return []
    out: list[str] = []
    for law in _LAW_RE.findall(violated):
        if law not in out:
            out.append(law)
    for segment in re.split(r"[；;]", violated):
        std_matches = list(_STD_RE.finditer(segment))
        if not std_matches:
            continue
        # Multi-standard segment (e.g. 顿号分隔不同规范): partition at code
        # boundaries so each code owns only the articles that follow it.
        sub_specs: list[tuple[re.Match, str]] = []
        for i, m in enumerate(std_matches):
            end = std_matches[i + 1].start() if i + 1 < len(std_matches) else len(segment)
            sub_specs.append((m, segment[m.start():end]))
        for std_match, sub in sub_specs:
            code = _normalize_std_code(std_match.group(0))
            articles = _ARTICLE_RE.findall(sub)
            if articles:
                for art in articles:
                    ref = f"{code}:{art}"
                    if ref not in out:
                        out.append(ref)
            elif code not in out:
                out.append(code)
    return out


def _normalize_std_code(raw: str) -> str:
    s = re.sub(r"\s+", "", raw).replace("—", "-").replace("－", "-").replace("／", "/")
    s = re.sub(r"^([A-Za-z]+)/?[Tt]", r"\1-T", s)  # GB/T, GBT → GB-T (only if T present)
    s = s.replace("/", "-")
    s = re.sub(r"^([A-Za-z]+(?:-T)?)(\d)", r"\1-\2", s)  # dash before number
    s = re.sub(r"-T-(\d)", r"-T\1", s)  # collapse GB-T-46 → GB-T46 to match lib JGJ-T46
    return s.upper()


def _normalize_date(raw: str) -> str:
    m = _DATE_RE.search(raw)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return raw.strip()


def _extract_url(raw: str) -> str:
    m = re.search(r"https?://[^\s\]\)）]+", raw)
    return m.group(0) if m else raw.strip()


def write_case_chunks(
    chunks: list[CaseChunk],
    output_path: Path = CASE_CHUNKS_PATH,
    report_path: Path = IMPORT_REPORT_PATH,
) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(chunk.model_dump_json(exclude_none=True) + "\n")
    report = build_import_report(chunks)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def load_case_chunks(path: Path = CASE_CHUNKS_PATH) -> list[CaseChunk]:
    chunks: list[CaseChunk] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(CaseChunk.model_validate_json(line))
            except Exception as exc:
                raise ValueError(f"Invalid case chunk at {path}:{line_no}: {exc}") from exc
    return chunks


def validate_case_chunks(chunks: list[CaseChunk]) -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    required = [
        "schema_version",
        "chunk_id",
        "chunk_kind",
        "case_id",
        "case_title",
        "text",
        "content_hash",
        "pipeline_version",
    ]
    for chunk in chunks:
        for fld in required:
            if not getattr(chunk, fld, None):
                issues.append(f"{chunk.chunk_id}: missing {fld}")
        if chunk.chunk_id in seen:
            issues.append(f"{chunk.chunk_id}: duplicate chunk_id")
        seen.add(chunk.chunk_id)
        if chunk.chunk_id in {"norm_001", "case_001"} or chunk.case_id in {"case_001"}:
            issues.append(f"{chunk.chunk_id}: mock id is not allowed")
        if not chunk.scenario_tags:
            issues.append(f"{chunk.chunk_id}: missing scenario_tags")
        if not chunk.hazard_tags:
            issues.append(f"{chunk.chunk_id}: missing hazard_tags")
    return issues


def build_import_report(chunks: list[CaseChunk]) -> dict:
    by_case: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_accident: dict[str, int] = {}
    tag_counts: dict[str, int] = {}
    duplicate_ids = len(chunks) - len({c.chunk_id for c in chunks})
    oversized = [c.chunk_id for c in chunks if len(c.text) > 1800]
    mock_ids = [c.chunk_id for c in chunks if c.chunk_id in {"norm_001", "case_001"}]
    cases_without_related = sorted(
        {c.case_id for c in chunks} - {c.case_id for c in chunks if c.related_standards}
    )
    issues = validate_case_chunks(chunks)

    for chunk in chunks:
        by_case[chunk.case_id or "?"] = by_case.get(chunk.case_id or "?", 0) + 1
        by_kind[chunk.chunk_kind or "unknown"] = by_kind.get(chunk.chunk_kind or "unknown", 0) + 1
        if chunk.accident_type:
            by_accident[chunk.accident_type] = by_accident.get(chunk.accident_type, 0) + 1
        for tag in chunk.scenario_tags + chunk.hazard_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "chunk_count": len(chunks),
        "case_count": len(by_case),
        "by_chunk_kind": by_kind,
        "by_accident_type": by_accident,
        "tag_distribution": dict(sorted(tag_counts.items())),
        "cases_without_related_standards": cases_without_related,
        "duplicate_chunk_id_count": duplicate_ids,
        "oversized_chunk_count": len(oversized),
        "oversized_chunk_ids": oversized,
        "mock_ids_present": mock_ids,
        "validation_issue_count": len(issues),
        "validation_issues": issues,
    }


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
