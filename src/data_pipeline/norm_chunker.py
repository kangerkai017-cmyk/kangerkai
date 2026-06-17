import hashlib
import json
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from src.schema import NormChunk
from src.tags import (
    hazard_fallback,
    hazard_tags_for_text,
    scenario_fallback,
    scenario_tags_for_text,
)

SCHEMA_VERSION = "norm_v1"
PIPELINE_VERSION = "norm_chunker_v2"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOTS = [
    PROJECT_ROOT / "rag_data" / "rag_data",
    PROJECT_ROOT / "脚手架规范文表图切分" / "脚手架规范文表图切分",
]
CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "extracted"
CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"
NORM_CHUNKS_PATH = CHUNKS_DIR / "norm_chunks.jsonl"
IMPORT_REPORT_PATH = CHUNKS_DIR / "norm_import_report.json"

JGJ33_CODE = "JGJ-33-2012"
JGJ33_KEEP_CHAPTERS = {"01", "02", "04"}
JGJ33_KEEP_SECTION_PREFIXES = ("8.4.", "8.5.")
JGJ33_RELEVANT_TABLE_TERMS = ("混凝土泵", "泵车", "支腿", "输送管")
ALLOW_DUP_CHUNK_KINDS = {"table", "figure", "formula"}
FROZEN_STANDARD_CODES = {"JGJ-202-2010"}
EXCLUDED_STANDARD_CODES = {"JGJ-196-2010"}

JGJT46_CODE = "JGJ-T46-2024"
NORMATIVE_VERBS = ("应", "不得", "必须", "严禁", "宜", "不应")

# Articles explicitly cited as violated norms by accident cases.  These are
# kept unconditionally even when OCR-introduced artifacts (stray "TREE" in a
# table caption, garbled punctuation) would otherwise trigger a noise filter.
# Only add entries that are (a) case-cited in data/事故案例收集.md AND (b)
# confirmed present in the source OCR/PDF with real normative text.
CASE_CITED_RESCUE_ARTICLES: frozenset[tuple[str, str]] = frozenset({
    ("JGJ-T46-2024", "8.1.6"),   # case-22 触电: 外电隔离防护措施; OCR table artifact [TSTREETaRE]
    ("GB-50194-2014", "7.5.4"),  # case-22 触电: 外电架空线路隔离防护; OCR garbled table below body
})

WHITELISTED_STANDARD_RULES = {
    "JGJ-276-2012": {
        "prefixes": (
            "1.0.",
            "2.1.",
            "3.0.",
            "4.1.",
            "4.2.",
            "4.3.",
            "4.4.",
            "4.5.",
            "5.1.",
            "5.2.",
            "5.3.",
            "5.4.",
            "6.1.",
            "6.2.",
            "6.3.",
            "6.4.",
        ),
        "keywords": ("吊装", "起重", "吊索", "索具", "钢丝绳", "地锚", "吊具", "吊点"),
        "policy": "keep general requirements, lifting machines, rigging/anchors, and concrete/steel structure hoisting; skip grid/appendix calculation-heavy material",
    },
    "JGJ-59-2011": {
        "prefixes": (
            "1.0.",
            "3.1.",
            "3.3.",
            "3.7.",
            "3.8.",
            "3.12.",
            "3.13.",
            "3.14.",
            "3.15.",
            "3.16.",
            "3.17.",
            "3.18.",
            "4.0.",
            "5.0.",
        ),
        "keywords": (
            "安全管理检查评分表",
            "扣件式钢管脚手架",
            "模板支架",
            "施工用电",
            "物料提升机",
            "施工升降机",
            "塔式起重机",
            "起重吊装检查评分表",
            "高处作业",
            "安全技术交底",
            "安全检查",
            "安全教育",
        ),
        "policy": "keep safety-management and high-risk work inspection items only; skip weakly related inspection tables",
    },
    "GB-50656-2011": {
        "articles": (
            "1.0.1",
            "1.0.3",
            "2.0.5",
            "2.0.6",
            "2.0.7",
            "2.0.8",
            "3.0.2",
            "3.0.4",
            "3.0.5",
            "3.0.6",
            "3.0.7",
            "3.0.8",
            "3.0.9",
            "3.0.10",
            "5.0.1",
            "5.0.3",
            "5.0.4",
            "6.0.1",
            "6.0.2",
            "6.0.3",
            "7.0.4",
            "7.0.5",
            "7.0.6",
            "7.0.7",
            "7.0.8",
            "9.0.1",
            "9.0.2",
            "9.0.4",
            "9.0.5",
            "9.0.6",
            "10.0.1",
            "10.0.3",
            "10.0.4",
            "10.0.5",
            "10.0.6",
            "10.0.7",
            "11.0.3",
            "11.0.4",
            "12.0.2",
            "12.0.3",
            "12.0.4",
            "12.0.5",
            "12.0.6",
            "12.0.7",
            "13.0.1",
            "13.0.2",
            "13.0.3",
            "13.0.4",
            "13.0.5",
            "13.0.6",
            "14.0.1",
            "14.0.2",
            "14.0.3",
            "14.0.4",
            "14.0.5",
            "14.0.6",
            "15.0.1",
            "15.0.2",
            "15.0.3",
            "15.0.4",
            "15.0.5",
            "15.0.6",
            "15.0.7",
            "15.0.8",
        ),
        "keywords": (),
        "policy": "keep lightweight enterprise safety-management evidence: responsibility, training, PPE/equipment management, technical measures, site management, emergency response, accident reporting, and hidden-hazard inspection; skip cost/accounting, awards, broad organization prose, and weakly related management material",
    },
    "JGJ-130-2011": {
        "prefixes": (
            "1.0.",
            "2.1.",
            "3.1.",
            "3.2.",
            "3.3.",
            "3.4.",
            "3.5.",
            "6.2.",
            "6.3.",
            "6.4.",
            "6.6.",
            "6.7.",
            "6.8.",
            "6.10.",
            "7.",
            "8.",
            "9.",
        ),
        "keywords": ("扣件", "脚手架", "连墙件", "剪刀撑", "搭设", "拆除", "检查验收", "安全管理", "悬挑"),
        "policy": "keep scaffold materials, key construction details, erection/dismantling, inspection/acceptance, and safety management; skip load/design calculation chapters and appendices",
    },
    "JGJ-202-2010": {
        "articles": (
            "1.0.3",
            "3.0.7",
            "3.0.9",
            "3.0.10",
            "3.0.11",
            "3.0.13",
            "3.0.15",
            "4.4.2",
            "4.6.2",
            "4.6.3",
            "4.6.9",
            "4.7.2",
            "4.7.3",
            "4.7.8",
            "4.8.2",
            "4.8.3",
            "4.8.6",
            "4.9.2",
            "4.9.3",
            "4.9.4",
            "5.3.1",
            "5.4.2",
            "5.4.4",
            "5.4.5",
            "5.5.1",   # case-01 触电: 吊篮使用前检查要求; PDF absent (frozen), add when PDF available
            "5.5.2",
            "5.5.3",
            "5.5.4",
            "5.5.7",
            "5.5.8",
            "5.5.10",
            "5.5.11",
            "5.5.15",
            "5.5.16",
            "5.5.17",
            "5.5.19",
            "5.5.20",
            "5.5.21",
            "5.6.4",
            "6.3.4",
            "6.3.9",
            "6.4.9",
            "6.5.3",
            "6.5.4",
            "6.5.5",
            "6.5.8",
            "6.5.10",
            "6.5.11",
            "6.6.2",
            "7.0.2",
            "7.0.5",
            "7.0.7",
            "7.0.8",
            "7.0.10",
            "7.0.11",
            "7.0.12",
            "7.0.14",
            "7.0.15",
            "7.0.16",
            "7.0.20",
            "8.3.1",
            "8.3.2",
        ),
        "related_articles": (
            "4.5.3",
            "8.1.3",
            "8.1.4",
            "8.2.2",
            "8.3.2",
        ),
        "keywords": (),
        "policy": "keep only tool-type scaffold safety use, installation/dismantling, lifting, management, and acceptance evidence; skip terms, design calculations, load tables, formulas, and weak OCR fragments",
    },
}

JGJ202_CODE = "JGJ-202-2010"

CURATED_ARTICLE_WHITELIST = {
    "JGJ-130-2011": {
        "1.0.1",
        "1.0.2",
        "2.1.1",
        "2.1.2",
        "2.1.3",
        "2.1.4",
        "2.1.5",
        "2.1.6",
        "2.1.7",
        "2.1.8",
        "3.1.1",
        "3.2.1",
        "3.2.2",
        "3.2.3",
        "3.3.1",
        "3.4.1",
        "3.4.2",
        "3.4.3",
        "3.5.1",
        "6.2.1",
        "6.2.2",
        "6.2.3",
        "6.2.4",
        "6.3.1",
        "6.3.2",
        "6.3.3",
        "6.3.4",
        "6.3.5",
        "6.3.6",
        "6.4.1",
        "6.4.2",
        "6.4.3",
        "6.6.1",
        "6.6.2",
        "6.6.3",
        "6.6.4",
        "6.6.5",
        "6.7.1",
        "6.7.2",
        "6.7.3",
        "6.8.1",
        "6.8.2",
        "6.8.3",
        "6.8.4",
        "6.10.1",
        "6.10.2",
        "6.10.3",
        "6.10.4",
        "7.1.1",
        "7.1.2",
        "7.2.1",
        "7.2.2",
        "7.3.1",
        "7.3.2",
        "7.3.3",
        "7.3.4",
        "7.3.5",
        "7.3.6",
        "7.4.1",
        "7.4.2",
        "7.4.3",
        "7.4.4",
        "7.4.5",
        "8.1.1",
        "8.1.2",
        "8.1.3",
        "8.2.1",
        "8.2.2",
        "8.2.3",
        "8.2.4",
        "8.2.5",
        "9.0.1",
        "9.0.2",
        "9.0.3",
        "9.0.4",
        "9.0.5",
        "9.0.6",
        "9.0.7",
        "9.0.8",
        "9.0.9",
        "9.0.10",
        "9.0.11",
        "9.0.12",
        "9.0.13",
    },
    "GB-51210-2016": {
        "1.0.1",
        "1.0.2",
        "1.0.3",
        "1.0.4",
        "3.1.1",
        "3.1.2",
        "3.1.3",
        "3.1.4",
        "3.2.1",
        "3.2.2",
        "3.2.3",
        "4.0.1",
        "4.0.2",
        "4.0.3",
        "4.0.4",
        "4.0.5",
        "4.0.6",
        "4.0.7",
        "8.2.1",
        "8.2.2",
        "8.2.3",
        "8.2.4",
        "8.2.5",
        "8.2.6",
        "8.2.7",
        "9.0.1",
        "9.0.2",
        "9.0.3",
        "9.0.4",
        "9.0.5",
        "9.0.6",
        "9.0.7",
        "9.0.8",
        "9.0.9",
        "9.0.10",
        "11.1.1",
        "11.1.2",
        "11.1.3",
        "11.1.4",
        "11.1.5",
        "11.1.6",
        "11.1.7",
        "11.2.1",
        "11.2.2",
        "11.2.3",
        "11.2.4",
        "11.2.5",
        "11.2.10",  # case-22 触电: 脚手架与架空输电线路安全距离
    },
    "JGJ-162-2008": {
        "6.1.1",
        "6.1.2",
        "6.1.3",
        "6.1.4",
        "6.1.5",
        "6.1.6",
        "6.2.1",
        "6.2.2",
        "6.2.3",
        "6.2.4",
        "6.2.5",
        "6.2.6",
        "6.2.7",
        "6.2.8",
        "6.2.9",
        "6.2.10",
        "6.2.11",
        "6.2.12",
        "6.2.13",
        "6.2.14",
        "6.2.15",
        "7.1.1",
        "7.1.2",
        "7.1.3",
        "7.1.4",
        "7.1.5",
        "7.2.1",
        "7.2.2",
        "7.2.3",
        "7.2.4",
        "7.2.5",
        "7.2.6",
        "7.2.7",
        "7.2.8",
        "7.2.9",
        "7.2.10",
        "7.2.11",
        "7.2.12",
        "7.2.13",
        "7.2.14",
        "7.2.15",
        "7.2.16",
        "7.2.17",
        "7.2.18",
        "7.2.19",
        "8.0.1",
        "8.0.2",
        "8.0.3",
        "8.0.4",
        "8.0.5",
        "8.0.6",
        "8.0.7",
        "8.0.8",
        "8.0.9",
        "8.0.10",
        "8.0.11",
        "8.0.12",
        "8.0.13",
        "8.0.14",
        "8.0.15",
        "8.0.16",
        "8.0.17",
        "8.0.18",
        "8.0.19",
        "8.0.20",
        "8.0.21",
        "8.0.22",
        "8.0.23",
        "8.0.24",
        "8.0.25",
        "8.0.26",
        "8.0.27",
        "8.0.28",
        "8.0.29",
        "8.0.30",
    },
}

CURATED_RELATED_ARTICLE_WHITELIST = {
    "GB-51210-2016": {"3.2.1"},
    "JGJ-162-2008": {"8.0.22"},
}

JGJ130_STRICT_KEEP_ARTICLES = {
    "1.0.1",
    "1.0.2",
    "3.2.1",
    "6.2.3",
    "6.4.3",
    "6.6.4",
    "6.6.5",
    "6.8.4",
    "7.3.1",
    "7.3.2",
    "7.3.3",
    "7.3.4",
    "7.3.5",
    "7.3.6",
    "7.4.1",
    "7.4.2",
    "7.4.3",
    "8.2.2",
    "8.2.3",
    "9.0.6",
    "9.0.7",
    "9.0.12",
    "9.0.13",
}


@dataclass(frozen=True)
class SourceInfo:
    path: Path
    standard_code: str
    standard_name: str
    year: str
    chapter: str
    chapter_no: str
    chapter_title: str
    asset_path: str


def build_norm_chunks(source_roots: list[Path] | None = None) -> list[NormChunk]:
    chunks, _diagnostics = build_norm_chunks_with_diagnostics(source_roots)
    return chunks


def build_norm_chunks_with_diagnostics(
    source_roots: list[Path] | None = None,
) -> tuple[list[NormChunk], dict]:
    roots = source_roots or DEFAULT_SOURCE_ROOTS
    chunks: list[NormChunk] = []
    for path in _iter_source_files(roots):
        info = _source_info(path, roots)
        if path.suffix.lower() == ".docx":
            chunks.extend(_build_explanation_chunks(info))
        elif path.suffix.lower() == ".pdf":
            if _is_semantic_pdf(path):
                if _is_explanation_pdf(path):
                    chunks.extend(_build_explanation_chunks(info))
                else:
                    chunks.extend(_build_article_chunks(info))
    chunks.extend(_load_frozen_standard_chunks(chunks))
    filtered, filter_report = _filter_low_quality_chunks(chunks)
    destubbed, stub_report = _resolve_heading_stub_collisions(filtered)
    deduped, dedupe_report = _deduplicate_chunks(destubbed)
    diagnostics = {
        "raw_chunk_count": len(chunks),
        "after_quality_filter_count": len(filtered),
        "after_stub_resolution_count": len(destubbed),
        "final_chunk_count": len(deduped),
        "quality_filter": filter_report,
        "heading_stub_resolution": stub_report,
        "deduplication": dedupe_report,
    }
    return deduped, diagnostics


def _load_frozen_standard_chunks(current_chunks: list[NormChunk]) -> list[NormChunk]:
    """Carry forward curated chunks whose source PDFs are intentionally absent.

    The project treats standard_code/chapter/article_id/text as the formal
    provenance for these standards. If a frozen standard source is present and
    produces chunks, the freshly-built chunks win; otherwise the last verified
    JSONL entry is retained so rebuilding the index does not silently drop it.
    """
    present_codes = {chunk.standard_code for chunk in current_chunks}
    missing_codes = FROZEN_STANDARD_CODES - present_codes
    if not missing_codes or not NORM_CHUNKS_PATH.exists():
        return []
    frozen: list[NormChunk] = []
    try:
        existing = load_norm_chunks(NORM_CHUNKS_PATH)
    except Exception:
        return []
    for chunk in existing:
        if chunk.standard_code in missing_codes:
            frozen.append(chunk)
    return frozen


def write_norm_chunks(
    chunks: list[NormChunk],
    output_path: Path = NORM_CHUNKS_PATH,
    report_path: Path = IMPORT_REPORT_PATH,
    diagnostics: dict | None = None,
) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk.model_dump_json(exclude_none=True) + "\n")

    report = build_import_report(chunks)
    if diagnostics:
        report["build_diagnostics"] = diagnostics
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def load_norm_chunks(path: Path = NORM_CHUNKS_PATH) -> list[NormChunk]:
    chunks: list[NormChunk] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(NormChunk.model_validate_json(line))
            except Exception as exc:
                raise ValueError(f"Invalid norm chunk at {path}:{line_no}: {exc}") from exc
    return chunks


def validate_norm_chunks(chunks: list[NormChunk]) -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    required = [
        "schema_version",
        "chunk_id",
        "chunk_kind",
        "standard_code",
        "source_path",
        "text",
        "content_hash",
        "pipeline_version",
    ]
    for chunk in chunks:
        for field in required:
            if not getattr(chunk, field, None):
                issues.append(f"{chunk.chunk_id}: missing {field}")
        if chunk.chunk_id in seen:
            issues.append(f"{chunk.chunk_id}: duplicate chunk_id")
        seen.add(chunk.chunk_id)
        if chunk.chunk_id in {"norm_001", "case_001"}:
            issues.append(f"{chunk.chunk_id}: mock id is not allowed")
        if not chunk.scenario_tags:
            issues.append(f"{chunk.chunk_id}: missing scenario_tags")
        if not chunk.hazard_tags:
            issues.append(f"{chunk.chunk_id}: missing hazard_tags")
    return issues


def build_import_report(chunks: list[NormChunk]) -> dict:
    by_standard: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    tag_counts: dict[str, int] = {}
    duplicate_ids = len(chunks) - len({c.chunk_id for c in chunks})
    oversized = [c.chunk_id for c in chunks if len(c.text) > 1800]
    mock_ids = [c.chunk_id for c in chunks if c.chunk_id in {"norm_001", "case_001"}]
    issues = validate_norm_chunks(chunks)
    missing_source_paths = [
        c.chunk_id
        for c in chunks
        if c.source_path and not (PROJECT_ROOT / c.source_path).exists()
    ]

    for chunk in chunks:
        by_standard[chunk.standard_code or chunk.standard_name] = (
            by_standard.get(chunk.standard_code or chunk.standard_name, 0) + 1
        )
        by_kind[chunk.chunk_kind or "unknown"] = by_kind.get(chunk.chunk_kind or "unknown", 0) + 1
        for tag in chunk.scenario_tags + chunk.hazard_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "chunk_count": len(chunks),
        "by_standard": dict(sorted(by_standard.items())),
        "by_chunk_kind": dict(sorted(by_kind.items())),
        "tag_distribution": dict(sorted(tag_counts.items())),
        "duplicate_chunk_id_count": duplicate_ids,
        "oversized_chunk_count": len(oversized),
        "oversized_chunk_ids": oversized[:50],
        "mock_ids_present": mock_ids,
        "validation_issue_count": len(issues),
        "validation_issues": issues[:200],
        "missing_source_path_count": len(missing_source_paths),
        "missing_source_path_ids": missing_source_paths[:100],
    }


def _iter_source_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        files.extend(
            p
            for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in {".pdf", ".docx"}
        )
    return sorted(files)


def _source_info(path: Path, roots: list[Path]) -> SourceInfo:
    root = next((r for r in roots if path.is_relative_to(r)), path.parents[-2])
    rel = path.relative_to(root)
    standard_code = rel.parts[0]
    year_match = re.search(r"(19|20)\d{2}", standard_code)
    year = year_match.group(0) if year_match else ""
    standard_name = standard_code.replace("-", " ")

    if len(rel.parts) == 2:
        chapter_stem = path.stem
    else:
        chapter_stem = rel.parts[1]

    chapter_no, chapter_title = _split_chapter(chapter_stem)
    chapter = f"{chapter_no} {chapter_title}".strip()
    return SourceInfo(
        path=path,
        standard_code=standard_code.replace(" ", "-"),
        standard_name=standard_name,
        year=year,
        chapter=chapter,
        chapter_no=chapter_no,
        chapter_title=chapter_title,
        asset_path=_asset_path_for(path),
    )


def _split_chapter(stem: str) -> tuple[str, str]:
    match = re.match(r"^(\d+)[_、\s-]*(.+)$", stem)
    if match:
        return match.group(1), match.group(2)
    return "", stem


def _asset_path_for(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return _rel(path)
    if path.suffix.lower() == ".docx":
        pdfs = sorted(path.parent.glob("*.pdf"))
        if pdfs:
            return _rel(pdfs[0])
    return ""


def _is_semantic_pdf(path: Path) -> bool:
    name = path.name
    parent = path.parent.name
    if parent.endswith("_表格") or parent.endswith("_图像"):
        return False
    if "表格提取与说明" in str(path.parent) or "图提取与说明" in str(path.parent):
        if name.startswith("表") or name.startswith("附录A-图"):
            return False
        return any(key in name for key in ["说明", "公式", "图"])
    return True


def _is_explanation_pdf(path: Path) -> bool:
    name = path.name
    return any(key in name for key in ["说明", "补充", "公式", "图、公式"])


def _build_article_chunks(info: SourceInfo) -> list[NormChunk]:
    raw_text = _extract_text(info.path)
    text = _normalize_text(_repair_article_breaks(raw_text))
    if not text:
        return []

    article_parts = _split_articles(text)
    if not article_parts:
        # Whole-chapter fallback would mix unrelated articles into one blob and
        # wreck precise retrieval. Window the chapter into bounded parts instead,
        # each kept under the long-text limit, rather than emitting one mega chunk.
        base_id = f"ch-{info.chapter_no or 'x'}-{info.chapter_title or info.path.stem}"
        title = info.chapter_title or info.path.stem
        article_parts = [(base_id, title, text)]

    chunks: list[NormChunk] = []
    for article_id, title, body in article_parts:
        if _is_garbled(body):
            continue
        parts = _split_long_text(body)
        for part_no, part in enumerate(parts, 1):
            suffix = f"{article_id or f'ch-{info.chapter_no or 'x'}'}"
            if len(parts) > 1:
                suffix = f"{suffix}-part-{part_no}"
            chunks.append(
                _make_chunk(
                    info=info,
                    chunk_kind=_kind_for_article(info, article_id, part),
                    item_id=suffix,
                    title=title,
                    article_id=article_id or None,
                    related_article_id=None,
                    body=part,
                )
            )
    return chunks


def _build_explanation_chunks(info: SourceInfo) -> list[NormChunk]:
    raw_text = _extract_text(info.path)
    text = _normalize_text(raw_text)
    if not text:
        return []

    parts = _split_explanations(text)
    if not parts:
        parts = [("", info.path.stem, text)]

    chunks: list[NormChunk] = []
    for idx, (item_id, title, body) in enumerate(parts, 1):
        chunk_kind = _kind_for_explanation(item_id, title, info.path)
        safe_id = item_id or f"item-{idx}"
        related = _related_article_from_text(title + " " + body)
        chunks.append(
            _make_chunk(
                info=info,
                chunk_kind=chunk_kind,
                item_id=safe_id,
                title=title or safe_id,
                article_id=None,
                related_article_id=related,
                body=body,
            )
        )
    return chunks


def _make_chunk(
    info: SourceInfo,
    chunk_kind: str,
    item_id: str,
    title: str,
    article_id: str | None,
    related_article_id: str | None,
    body: str,
) -> NormChunk:
    title = _repair_standard_ocr(info, title)
    body = _repair_standard_ocr(info, body)
    body = _repair_article_body(info, article_id, body)
    scenario_tags, hazard_tags = _tags_for(info, title, body)
    requirement_type = _requirement_type_for(chunk_kind, info, body)
    item = _slug(item_id or title or "chunk")
    chunk_id = f"norm::{info.standard_code}::{chunk_kind}::{item}"
    source = _rel(info.path)
    normalized_body = _normalize_text(body)
    text = _format_text(
        info=info,
        item_id=article_id or title or item_id,
        body=normalized_body,
    )
    content_hash = _sha256("|".join([text, source, SCHEMA_VERSION]))
    return NormChunk(
        schema_version=SCHEMA_VERSION,
        doc_type="norm",
        chunk_id=chunk_id,
        chunk_kind=chunk_kind,
        standard_name=info.standard_name,
        standard_code=info.standard_code,
        year=info.year,
        source_name=info.standard_name,
        source_path=source,
        source=info.standard_name,
        chapter=info.chapter,
        chapter_no=info.chapter_no or None,
        chapter_title=info.chapter_title or None,
        article_id=article_id,
        page_start=None,
        page_end=None,
        title=title,
        text=text,
        scenario_tags=scenario_tags,
        hazard_tags=hazard_tags,
        requirement_type=requirement_type,
        asset_path=info.asset_path,
        related_article_id=related_article_id,
        content_hash=content_hash,
        pipeline_version=PIPELINE_VERSION,
    )


def _repair_article_body(info: SourceInfo, article_id: str | None, body: str) -> str:
    if info.standard_code != "JGJ-130-2011" or not article_id:
        return body
    repairs = {
        "6.2.3": "6.2.3 主节点处必须设置一根横向水平杆，用直角扣件扣接且严禁拆除。",
        "7.4.2": (
            "7.4.2 单、双排脚手架拆除作业必须由上而下逐层进行，严禁上下同时作业；"
            "连墙件必须随脚手架逐层拆除，严禁先将连墙件整层或数层拆除后再拆脚手架；"
            "分段拆除高差大于两步时，应增设连墙件加固。"
        ),
        "9.0.7": "9.0.7 满堂支撑架顶部的实际荷载不得超过设计规定。",
        "9.0.13": (
            "9.0.13 在脚手架使用期间，严禁拆除下列杆件："
            "1 主节点处的纵、横向水平杆，纵、横向扫地杆；2 连墙件。"
        ),
    }
    return repairs.get(article_id, body)


def _repair_standard_ocr(info: SourceInfo, text: str) -> str:
    if not text:
        return text
    if info.standard_code in {"GB-51210-2016", "JGJ-130-2011"}:
        common = {
            "脚于架": "脚手架",
            "脚子架": "脚手架",
            "脚手锅": "脚手架",
            "措设": "搭设",
            "措完": "搭完",
            "符人台": "符合",
            "宣按": "宜按",
            "连埔": "连墙",
            "横癌": "横向",
            "起过": "超过",
            "缆凤绳": "缆风绳",
            "脚于板": "脚手板",
            "脚于架结构": "脚手架结构",
        }
        for old, new in common.items():
            text = text.replace(old, new)
        if info.standard_code == "JGJ-130-2011":
            text = _dedupe_consecutive_pdf_lines(text)
    if info.standard_code == "GB-50656-2011":
        replacements = {
            "满定": "满足",
            "安全技\\n术": "安全技术",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
    if info.standard_code != JGJ202_CODE:
        return text
    replacements = {
        "脚于架": "脚手架",
        "脚子架": "脚手架",
        "升降剧手架": "升降脚手架",
        "丹降": "升降",
        "刀阵": "升降",
        "附辛辛式": "附着式",
        "附辛辛": "附着",
        "附着主革": "附着支承",
        "水平主革珩架": "水平支承桁架",
        "水平主承材j架": "水平支承桁架",
        "本平主承1ir架": "水平支承桁架",
        "升降机梅": "升降机构",
        "合恪": "合格",
        "设肯": "设置",
        "陆具": "吊具",
        "规泣": "规定",
        "井应": "并应",
        "山符合": "应符合",
        "撞地": "接地",
        "如除": "拆除",
        "节降": "下降",
        "君主中": "空中",
        "录用": "采用",
        "商处作业吊篮": "高处作业吊篮",
        "女装": "安装",
        "相架": "桁架",
        "和T架": "桁架",
        "连援": "连接",
        "片山将": "并应将",
        "吊篮_iE常": "吊篮正常",
        "大算": "大雾",
        "8. l.4": "8.1.4",
        "作业z": "作业：",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _dedupe_consecutive_pdf_lines(text: str) -> str:
    """Remove repeated text-layer lines produced by some scanned PDFs.

    Keep this deliberately conservative: only adjacent lines with the same
    compact text are collapsed, so repeated normative words inside a sentence
    are not rewritten.
    """
    lines = text.splitlines()
    deduped: list[str] = []
    previous = ""
    for line in lines:
        compact = re.sub(r"\s+", "", line)
        if compact and compact == previous:
            continue
        deduped.append(line)
        previous = compact
    return "\n".join(deduped)


def _extract_text(path: Path) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".pdf":
        sidecar = path.with_suffix(".txt")
        if sidecar.exists():
            return sidecar.read_text(encoding="utf-8")

    stat = path.stat()
    cache_key = _sha256(f"{path.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{PIPELINE_VERSION}")
    cache_path = CACHE_DIR / f"{cache_key}.txt"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".docx":
        text = _extract_docx_text(path)
    elif path.suffix.lower() == ".pdf":
        text = _extract_pdf_text(path)
    else:
        text = ""

    cache_path.write_text(text, encoding="utf-8")
    return text


def _extract_docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception:
        return ""
    text = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    text = re.sub(r"</w:p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    replacements = {
        "&lt;": "<",
        "&gt;": ">",
        "&amp;": "&",
        "&quot;": '"',
        "&apos;": "'",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _extract_pdf_text(path: Path) -> str:
    try:
        import fitz

        with fitz.open(path) as doc:
            return "\n".join(page.get_text("text") for page in doc)
    except Exception:
        pass

    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        return ""


def _repair_article_breaks(text: str) -> str:
    """Repair PDF-extraction artifacts inside article numbers so structural
    splitting works. Handles both line breaks ('3.\\n6' -> '3.6') and stray
    spaces ('1. 0. 1' -> '1.0.1', common in GB/JGJ 总则 numbered as N.0.M).
    Only a digit-dot directly followed by (optional space/newline) + digit is
    joined, so normal prose is essentially unaffected. Runs a few passes to fix
    chained multi-level numbers like '1. 0. 1'."""
    if not text:
        return text
    # Anchor on the dot (not the leading digit) so adjacent levels like
    # '1.0. 2' don't share/consume a digit and stall the substitution.
    out = text
    # OCR/bad text layers misread the middle '0' of an N.0.M chapter-term number
    # as the letter 'o'/'O' ('2. o. 2' for '2.0.2'). Only fire when the 'o' sits
    # between 'digit.' and '.digit', which is unambiguously an article number,
    # never prose. Do this before the dot-join pass so the recovered 0 joins up.
    out = re.sub(r"(\d)\.[ \t]*[oO][ \t]*\.[ \t]*(\d)", r"\1.0.\2", out)
    for _ in range(4):
        new = re.sub(r"\.[ \t]*\n?[ \t]*(\d)", r".\1", out)
        if new == out:
            break
        out = new
    return out


_UNIT_PREFIX = re.compile(
    r"^(?:mm|cm|km|kV|kA|mA|kVA|kW|kN|MPa|Hz|min|kg|m[²2³]?|[VAWgsth]|°C|℃)"
    r"(?![A-Za-z])"
)


def _starts_with_unit(first_line: str) -> bool:
    return bool(_UNIT_PREFIX.match(first_line.strip()))


def _split_articles(text: str) -> list[tuple[str, str, str]]:
    pattern = re.compile(r"(?m)^\s*((?:\d+\.)+\d+)\s+(.+)$")
    matches = list(pattern.finditer(text))
    if not matches:
        # OCR output often drops the space between the article number and the
        # body ("1.0.1为..."). Keep the original strict matcher for normal PDFs
        # to avoid table-of-contents false positives, and only fall back here
        # when strict structural splitting finds nothing.
        pattern = re.compile(r"(?m)^\s*((?:\d+\.)+\d+)[\s。．、]*(.+)$")
        matches = [
            match
            for match in pattern.finditer(text)
            if len(match.group(1).split(".")) >= 3
        ]
    # A line like "2.5 mm 的绝缘导线..." is a measurement wrapped to line start,
    # not an article ("2.5"); dropping these keeps the text with the real
    # preceding article instead of emitting a bogus fragment chunk.
    matches = [m for m in matches if not _starts_with_unit(m.group(2))]
    if not matches:
        return []

    parts: list[tuple[str, str, str]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        article_id = match.group(1).strip()
        first_line = match.group(2).strip()
        parts.append((article_id, first_line[:80], block))
    return parts


def _split_explanations(text: str) -> list[tuple[str, str, str]]:
    patterns = [
        r"(?=表格说明\d*[:：])",
        r"(?=图像说明\d*[:：])",
        r"(?=【(?:表|图|公式)[^】]+】)",
    ]
    split_re = re.compile("|".join(patterns))
    starts = [m.start() for m in split_re.finditer(text)]
    if not starts:
        return []

    parts: list[tuple[str, str, str]] = []
    starts.append(len(text))
    for i in range(len(starts) - 1):
        block = text[starts[i] : starts[i + 1]].strip()
        if len(block) < 20:
            continue
        title = _first_sentence(block)
        item_match = re.search(r"(表\d+(?:\.\d+)*|图[A-Za-z]?\d+(?:\.\d+)*(?:-\d+)?|图\d+(?:\.\d+)*(?:-\d+)?|公式\d+(?:\.\d+)*)", block)
        item_id = item_match.group(1) if item_match else title[:24]
        parts.append((item_id, title[:120], block))
    return parts


def _split_long_text(text: str, limit: int = 1200) -> list[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text]
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    parts: list[str] = []
    buf = ""
    for para in paragraphs:
        if buf and len(buf) + len(para) + 1 > limit:
            parts.append(buf)
            buf = para
        else:
            buf = f"{buf}\n{para}".strip()
    if buf:
        parts.append(buf)
    return parts or [text]


def _kind_for_article(info: SourceInfo, article_id: str, text: str) -> str:
    combined = f"{info.chapter} {article_id} {text}"
    if "术语" in combined:
        return "term"
    return "article"


def _kind_for_explanation(item_id: str, title: str, path: Path) -> str:
    combined = f"{item_id} {title} {path.name} {path.parent.name}"
    item_text = f"{item_id} {title}"
    if "公式" in item_text:
        return "formula"
    if "图" in item_text or "图像" in item_text:
        return "figure"
    if "表" in item_text:
        return "table"
    if "公式" in combined:
        return "formula"
    if "图" in combined or "图像" in combined:
        return "figure"
    if "表" in combined:
        return "table"
    if "补充" in combined:
        return "supplement"
    return "supplement"


def _tags_for(info: SourceInfo, title: str, body: str) -> tuple[list[str], list[str]]:
    # Tag inference is fully driven by data/taxonomy/tags.yaml (shared with the
    # retrieval layer), including per-standard hints for standards whose body
    # text lacks the trigger keywords (e.g. GB-6095 -> 安全带/坠落防护).
    combined = f"{info.standard_code} {info.chapter} {title} {body}"
    scenario_tags = scenario_tags_for_text(combined, info.standard_code)
    hazard_tags = hazard_tags_for_text(combined, scenario_tags, info.standard_code)
    if not scenario_tags:
        scenario_tags = scenario_fallback()
    if not hazard_tags:
        hazard_tags = hazard_fallback(scenario_tags)
    return scenario_tags, hazard_tags


def _requirement_type_for(chunk_kind: str, info: SourceInfo, text: str) -> str:
    combined = f"{info.chapter} {text}"
    if chunk_kind in {"table", "figure", "formula"}:
        return "计算参数" if any(k in combined for k in ["荷载", "距离", "分级", "半径", "公式", "标准值"]) else "补充说明"
    if "术语" in combined:
        return "术语定义"
    if any(k in combined for k in ["严禁", "不得"]):
        return "禁止行为"
    if any(k in combined for k in ["必须", "应", "不应"]):
        return "强制性要求"
    if any(k in combined for k in ["检查", "验收"]):
        return "检查验收"
    if any(k in combined for k in ["试验", "测试"]):
        return "试验检测"
    return "一般要求"


def _format_text(info: SourceInfo, item_id: str, body: str) -> str:
    # scenario_tags/hazard_tags/chunk_kind live in dedicated ES keyword fields,
    # so they are intentionally omitted here to keep the embedded/BM25 text
    # focused on the standard, location and article body (higher signal ratio,
    # especially for short articles).
    header = [f"标准：{info.standard_name}", f"章节：{info.chapter}"]
    if item_id:
        header.append(f"编号：{item_id}")
    header.append(f"正文：{body}")
    return "\n".join(header)


def _related_article_from_text(text: str) -> str | None:
    match = re.search(r"(?:第)?((?:\d+\.)+\d+)(?:条|款)?", text)
    return match.group(1) if match else None


def _first_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", "", text)
    for sep in ["。", "；", "\n"]:
        if sep in cleaned:
            return cleaned.split(sep, 1)[0]
    return cleaned[:120]


def _normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_garbled(text: str) -> bool:
    if not text:
        return True
    if "住房城乡建设部信息公开" in text or "浏览专用" in text:
        watermark_stripped = re.sub(
            r"(住房城乡建设部信息公开|浏览专用|\s)+",
            "",
            text,
        )
        if len(watermark_stripped) < 50:
            return True
    control_count = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t")
    if control_count:
        return True
    suspicious = sum(1 for ch in text if 0x80 <= ord(ch) <= 0x9F)
    if suspicious:
        return True
    meaningful = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff" or ch.isalnum())
    if meaningful / max(len(text), 1) < 0.35:
        return True
    return False


def _filter_low_quality_chunks(chunks: list[NormChunk]) -> tuple[list[NormChunk], dict]:
    kept: list[NormChunk] = []
    excluded: dict[str, list[str]] = {
        "pseudo_article_number": [],
        "jgj33_section_title": [],
        "jgj33_not_whitelisted": [],
        "bibliography": [],
        "appendix": [],
        "whole_chapter_fallback": [],
        "malformed_article_id": [],
        "ocr_garble": [],
        "preface_or_publisher": [],
        "known_ocr_garble_v2": [],
        "section_title_stub": [],
        "formula_design_noise": [],
        "standard_not_in_scope": [],
        "curated_standard_not_whitelisted": [],
        "contentless_fragment": [],
        "managed_standard_section_title": [],
        "managed_standard_not_whitelisted": [],
    }
    jgj33_keep = 0
    jgj33_exclude = 0
    managed_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"kept": 0, "excluded": 0})

    for chunk in chunks:
        reason = ""
        if (chunk.standard_code, chunk.article_id) in CASE_CITED_RESCUE_ARTICLES:
            pass  # keep unconditionally — case-cited articles with real normative content
        elif chunk.standard_code in EXCLUDED_STANDARD_CODES:
            reason = "standard_not_in_scope"
        elif _has_overlarge_article_level(chunk):
            reason = "pseudo_article_number"
        elif _is_jgj33_pure_section_title(chunk):
            reason = "jgj33_section_title"
        elif _is_jgj33_chunk(chunk) and not _is_jgj33_whitelisted(chunk):
            reason = "jgj33_not_whitelisted"
        elif _is_bibliography(chunk):
            reason = "bibliography"
        elif _is_appendix(chunk):
            reason = "appendix"
        elif _is_whole_chapter_fallback(chunk):
            reason = "whole_chapter_fallback"
        elif _has_malformed_article_id(chunk):
            reason = "malformed_article_id"
        elif _has_ocr_garble(chunk):
            reason = "ocr_garble"
        elif _is_preface_or_publisher(chunk):
            reason = "preface_or_publisher"
        elif _has_known_ocr_garble_v2(chunk):
            reason = "known_ocr_garble_v2"
        elif _is_formula_design_noise(chunk):
            reason = "formula_design_noise"
        elif _is_contentless_fragment(chunk):
            reason = "contentless_fragment"
        elif _is_section_title_stub(chunk):
            reason = "section_title_stub"
        elif _is_curated_standard(chunk) and not _is_curated_standard_whitelisted(chunk):
            reason = "curated_standard_not_whitelisted"
        elif _is_whitelist_managed_standard(chunk) and _is_pure_section_title(chunk):
            reason = "managed_standard_section_title"
        elif _is_whitelist_managed_standard(chunk) and not _is_managed_standard_whitelisted(chunk):
            reason = "managed_standard_not_whitelisted"

        if reason:
            excluded[reason].append(chunk.chunk_id)
            if _is_jgj33_chunk(chunk):
                jgj33_exclude += 1
            if _is_whitelist_managed_standard(chunk):
                managed_stats[chunk.standard_code or ""]["excluded"] += 1
            continue

        if _is_jgj33_chunk(chunk):
            jgj33_keep += 1
        if _is_whitelist_managed_standard(chunk):
            managed_stats[chunk.standard_code or ""]["kept"] += 1
        kept.append(chunk)

    return kept, {
        "excluded_counts": {reason: len(ids) for reason, ids in excluded.items()},
        "excluded_samples": {reason: ids[:30] for reason, ids in excluded.items()},
        "jgj33_whitelist": {
            "kept": jgj33_keep,
            "excluded": jgj33_exclude,
            "policy": "keep chapters 01/02/04 and article sections 8.4.x/8.5.x; keep relevant chapter-08 table/figure/formula notes",
        },
        "managed_standard_whitelist": {
            code: {
                **counts,
                "policy": WHITELISTED_STANDARD_RULES[code]["policy"],
            }
            for code, counts in sorted(managed_stats.items())
        },
    }


def _has_overlarge_article_level(chunk: NormChunk) -> bool:
    if chunk.chunk_kind not in {"article", "term"} or not chunk.article_id:
        return False
    levels = re.findall(r"\d+", chunk.article_id)
    return bool(levels and any(int(level) > 99 for level in levels))


def _is_bibliography(chunk: NormChunk) -> bool:
    """A 参考文献 chapter chunk — a list of cited documents, never normative."""
    return "参考文献" in (chunk.chapter or "")


def _is_appendix(chunk: NormChunk) -> bool:
    """Appendices are calculation examples, test appendices, or reference tables.
    They are useful for manual lookup, but too broad/noisy for the formal ES
    evidence pool when we want only precise article-level training evidence."""
    combined = " ".join(
        [
            chunk.chunk_id or "",
            chunk.chapter or "",
            chunk.title or "",
            chunk.source_path or "",
            chunk.asset_path or "",
            chunk.related_article_id or "",
        ]
    )
    return "附录" in combined or bool(re.search(r"(?:图|表|公式)[A-Z]\.", combined))


def _is_whole_chapter_fallback(chunk: NormChunk) -> bool:
    """Drop fallback chunks such as ch-04-附录A or ch-05-... that were created
    when structural article splitting failed. The source files stay available,
    but these chunks are not precise enough for the ES index."""
    return bool(
        chunk.chunk_kind in {"article", "term"}
        and chunk.article_id
        and str(chunk.article_id).startswith("ch-")
    )


def _has_malformed_article_id(chunk: NormChunk) -> bool:
    if chunk.chunk_kind not in {"article", "term"} or not chunk.article_id:
        return False
    article_id = str(chunk.article_id)
    levels = re.findall(r"\d+", article_id)
    if re.match(r"^0\.", article_id):
        return True
    if re.fullmatch(r"[1-9]\.0", article_id):
        return True
    if any(len(level) >= 4 for level in levels):
        return True
    if len(levels) >= 5 and len(article_id) > 16:
        return True
    return False


def _has_ocr_garble(chunk: NormChunk) -> bool:
    body = _body_from_formatted_text(chunk.text)
    garble_patterns = [
        r"十HH|二-HH|二二市|织旭|发E|剖动|主人带|安全者珊|吝诸|人坠落悬挂",
        r"clirect|EPE\)|1\.k|e：这posed|protectiye|naturaJ|electrodε|s\. o\.4|安全火员|接她",
        r"Ais hist|bupfloghypyipt|BAARHER|BERRY|AO GPE|MIRE ME|KX|HOR C|OAR AS|FIED",
        r"FETE|64044L|维修电王|信永|人亚控|防送电|绝缘胶闽|防静蝎|嫩塞|面音|户人Mt|剖应",
        r"[、,\.．]\s*[、,\.．]\s*[、,\.．].{0,30}[、,\.．]\s*[、,\.．]",
    ]
    return any(re.search(pattern, body) for pattern in garble_patterns)


def _is_preface_or_publisher(chunk: NormChunk) -> bool:
    combined = f"{chunk.title or ''} {chunk.text or ''}"
    return bool(
        re.search(
            r"本标准主编|本标准参编|主要起草人员|主要审查人员|"
            r"出版\s*发行|邮政编码|住房和城乡建设部负责管理|"
            r"标准编制组经广泛调查研究|根据住房和城乡建设部",
            combined,
        )
    )


def _has_known_ocr_garble_v2(chunk: NormChunk) -> bool:
    combined = f"{chunk.title or ''} {_body_from_formatted_text(chunk.text)}"
    patterns = [
        r"BANS\s*POH|IGF\s*PAY|符人台|HI00|xXx|满蔡|横癌|挠诬",
        r"NV7个|TREE|锡为术架|撑风|涩JJJ|维修寺f1c|操fl人员",
        r"脚于架|脚子架",
        r"[A-Za-z]{2,}\s*[，,]\s*[A-Za-z]{2,}\s*[，,]\s*[A-Za-z]{2,}",
    ]
    return any(re.search(pattern, combined) for pattern in patterns)


def _is_formula_design_noise(chunk: NormChunk) -> bool:
    if chunk.standard_code not in {"JGJ-130-2011", "GB-51210-2016", "JGJ-162-2008"}:
        return False
    if chunk.chunk_kind in {"figure"}:
        return True
    combined = f"{chunk.chapter or ''} {chunk.title or ''} {_body_from_formatted_text(chunk.text)}"
    if chunk.standard_code == "JGJ-162-2008" and chunk.chapter_no in {"04", "05"}:
        return True
    if chunk.standard_code == "GB-51210-2016" and chunk.chapter_no in {"05", "06", "07"}:
        return True
    if chunk.standard_code == "JGJ-130-2011" and (
        (chunk.article_id or "").startswith(("4.", "5."))
        or chunk.article_id in {"18.4", "6.9.6.9.5"}
    ):
        return True
    design_terms = (
        "公式",
        "计算",
        "设计值",
        "标准值",
        "荷载组合",
        "截面",
        "惯性矩",
        "弹性模量",
        "抗弯",
        "挠度",
        "承载力计算",
    )
    design_hits = sum(1 for term in design_terms if term in combined)
    symbol_hits = len(re.findall(r"≤|≥|σ|ϕ|λ|\bEI\b|\bkN\b|\bmm\b", combined))
    return design_hits >= 3 or symbol_hits >= 8


def _is_section_title_stub(chunk: NormChunk) -> bool:
    if chunk.chunk_kind not in {"article", "term"} or not chunk.article_id:
        return False
    body = _body_from_formatted_text(chunk.text)
    if body.startswith(chunk.article_id):
        body = body[len(chunk.article_id) :].strip()
    compact_body = re.sub(r"\s+", "", body)
    compact_title = re.sub(r"\s+", "", chunk.title or "")
    if len(compact_body) <= 1:
        return True
    if len(compact_body) <= 24 and compact_body == compact_title:
        return not any(v in body for v in NORMATIVE_VERBS + ("检查", "验收"))
    if len(compact_body) <= 16 and not any(v in body for v in NORMATIVE_VERBS + ("检查", "验收")):
        return True
    return False


def _is_curated_standard(chunk: NormChunk) -> bool:
    return bool(chunk.standard_code in CURATED_ARTICLE_WHITELIST)


def _is_curated_standard_whitelisted(chunk: NormChunk) -> bool:
    article_id = chunk.article_id or ""
    if chunk.standard_code == "JGJ-130-2011":
        return bool(article_id in JGJ130_STRICT_KEEP_ARTICLES)
    if article_id and article_id in CURATED_ARTICLE_WHITELIST.get(chunk.standard_code or "", set()):
        return True
    related = chunk.related_article_id or ""
    if related and related in CURATED_RELATED_ARTICLE_WHITELIST.get(chunk.standard_code or "", set()):
        return True
    return False


def _is_contentless_fragment(chunk: NormChunk) -> bool:
    """An article/term chunk whose body (after the article number) carries no
    actual text — only stray digits, math/punctuation OCR scraps, e.g. '35',
    '66~110', '7.0 (', '（5.2.5—14）'. These are mis-numbered table cells or
    formula crumbs, not requirements, so they only add retrieval noise."""
    if chunk.chunk_kind not in {"article", "term"}:
        return False
    body = _body_from_formatted_text(chunk.text)
    if chunk.article_id and body.startswith(chunk.article_id):
        body = body[len(chunk.article_id):].strip()
    cjk = sum(1 for ch in body if "一" <= ch <= "鿿")
    latin_words = re.findall(r"[A-Za-z]{3,}", body)
    return cjk < 2 and not latin_words


def _is_jgj33_chunk(chunk: NormChunk) -> bool:
    return chunk.standard_code == JGJ33_CODE


def _is_jgj33_pure_section_title(chunk: NormChunk) -> bool:
    if not _is_jgj33_chunk(chunk) or chunk.chunk_kind != "article" or not chunk.article_id:
        return False
    if not re.fullmatch(r"\d+\.\d+", chunk.article_id):
        return False
    body = _body_from_formatted_text(chunk.text)
    compact_body = re.sub(r"\s+", "", body)
    compact_title = re.sub(r"\s+", "", chunk.title or "")
    compact_article = re.sub(r"\s+", "", chunk.article_id)
    expected = f"{compact_article}{compact_title}"
    return compact_body == expected or (
        compact_body.startswith(compact_article)
        and len(compact_body) <= len(compact_article) + len(compact_title) + 4
        and not any(key in body for key in ["应", "必须", "不得", "严禁", "不应", "检查"])
    )


def _is_jgj33_whitelisted(chunk: NormChunk) -> bool:
    if chunk.chapter_no in JGJ33_KEEP_CHAPTERS:
        return True
    article_id = chunk.article_id or ""
    if article_id.startswith(JGJ33_KEEP_SECTION_PREFIXES):
        return True
    if chunk.chunk_kind in ALLOW_DUP_CHUNK_KINDS and chunk.chapter_no == "08":
        combined = f"{chunk.title or ''} {chunk.text or ''}"
        return any(term in combined for term in JGJ33_RELEVANT_TABLE_TERMS)
    return False


def _is_whitelist_managed_standard(chunk: NormChunk) -> bool:
    return bool(chunk.standard_code in WHITELISTED_STANDARD_RULES)


def _is_managed_standard_whitelisted(chunk: NormChunk) -> bool:
    rule = WHITELISTED_STANDARD_RULES.get(chunk.standard_code or "")
    if not rule:
        return True
    article_id = chunk.article_id or ""
    if article_id and article_id in rule.get("articles", ()):
        return True
    if article_id and any(article_id.startswith(prefix) for prefix in rule.get("prefixes", ())):
        return True
    if chunk.related_article_id and chunk.related_article_id in rule.get("related_articles", ()):
        return True
    combined = f"{chunk.title or ''} {chunk.text or ''}"
    return any(keyword in combined for keyword in rule.get("keywords", ()))


def _is_pure_section_title(chunk: NormChunk) -> bool:
    if chunk.chunk_kind != "article" or not chunk.article_id:
        return False
    if not re.fullmatch(r"\d+(?:\.\d+){1,2}", chunk.article_id):
        return False
    body = _body_from_formatted_text(chunk.text)
    compact_body = re.sub(r"\s+", "", body)
    compact_title = re.sub(r"\s+", "", chunk.title or "")
    compact_article = re.sub(r"\s+", "", chunk.article_id)
    has_normative_signal = any(key in body for key in NORMATIVE_VERBS + ("检查", "验收"))
    rule = WHITELISTED_STANDARD_RULES.get(chunk.standard_code or "", {})
    keep_exact_short_whitelisted_article = (
        chunk.standard_code in {"JGJ-130-2011", "GB-50656-2011"}
        and (
            chunk.article_id in JGJ130_STRICT_KEEP_ARTICLES
            or chunk.article_id in rule.get("articles", ())
        )
        and has_normative_signal
    )
    return (
        compact_body == f"{compact_article}{compact_title}"
        and not keep_exact_short_whitelisted_article
    ) or (
        compact_body.startswith(compact_article)
        and len(compact_body) <= len(compact_article) + len(compact_title) + 4
        and not has_normative_signal
    )


def _body_from_formatted_text(text: str) -> str:
    marker = "正文："
    if marker not in text:
        return text.strip()
    return text.split(marker, 1)[1].strip()


def _is_heading_stub(chunk: NormChunk) -> bool:
    """A JGJ-T46 article chunk whose body is just a section heading or a
    cross-reference fragment (short, no normative verb, no sentence
    punctuation) — e.g. '照明装置', '电缆线路', '8.1.4 条的规定'. These carry no
    requirement and must not win a chunk_id collision over the real article."""
    if chunk.chunk_kind in ALLOW_DUP_CHUNK_KINDS or not chunk.article_id:
        return False
    body = _body_from_formatted_text(chunk.text)
    if body.startswith(chunk.article_id):
        body = body[len(chunk.article_id):].strip()
    if len(body) > 16:
        return False
    return not any(v in body for v in NORMATIVE_VERBS) and "。" not in body and "：" not in body


def _resolve_heading_stub_collisions(chunks: list[NormChunk]) -> tuple[list[NormChunk], dict]:
    """JGJ-T46 OCR sometimes emits a heading/cross-ref stub that shares an
    article_id with the real article. First-wins dedup can then keep the stub
    and discard the requirement (e.g. kept '8.1.4 条的规定', dropped the actual
    crane/overhead-line clearance rule). Drop such stubs, but only when a
    substantive sibling with the same chunk_id exists, so a genuine standalone
    heading is never removed. Scoped to JGJ-T46: in other standards the
    colliding non-heading chunk is often OCR/formula garbage, so dropping the
    heading there would keep the garbage instead."""
    siblings: dict[str, list[NormChunk]] = defaultdict(list)
    for chunk in chunks:
        if (
            chunk.standard_code == JGJT46_CODE
            and chunk.chunk_kind not in ALLOW_DUP_CHUNK_KINDS
            and chunk.article_id
        ):
            siblings[chunk.chunk_id].append(chunk)
    drop_stub_ids = {
        cid
        for cid, group in siblings.items()
        if len(group) >= 2 and any(not _is_heading_stub(c) for c in group)
    }
    kept: list[NormChunk] = []
    dropped: list[str] = []
    for chunk in chunks:
        if (
            chunk.standard_code == JGJT46_CODE
            and chunk.chunk_id in drop_stub_ids
            and _is_heading_stub(chunk)
        ):
            dropped.append(chunk.chunk_id)
            continue
        kept.append(chunk)
    return kept, {
        "heading_stub_discard_count": len(dropped),
        "heading_stub_discard_samples": dropped[:30],
    }


def _deduplicate_chunks(chunks: list[NormChunk]) -> tuple[list[NormChunk], dict]:
    seen: dict[str, int] = {}
    seen_semantic: set[str] = set()
    deduped: list[NormChunk] = []
    semantic_duplicates: list[str] = []
    article_collisions: list[str] = []
    legal_dup_ids: list[str] = []
    for chunk in chunks:
        # Dedupe on content, not title. Many distinct articles in technical
        # standards share a section title (测试步骤/测试结果/试样, or 要求 vs
        # 试验方法 for the same property), and long appendix tables are split
        # into multi-part chunks that all carry the same title — a title-keyed
        # dedupe silently drops that distinct content. content_hash keys on the
        # actual text, so only byte-identical repeats are removed.
        semantic_key = chunk.content_hash or _sha256(chunk.text or "")
        if semantic_key in seen_semantic:
            semantic_duplicates.append(chunk.chunk_id)
            continue
        seen_semantic.add(semantic_key)
        if chunk.chunk_id not in seen:
            seen[chunk.chunk_id] = 1
            deduped.append(chunk)
            continue
        seen[chunk.chunk_id] += 1
        if chunk.chunk_kind not in ALLOW_DUP_CHUNK_KINDS:
            article_collisions.append(chunk.chunk_id)
            continue
        data = chunk.model_dump()
        data["chunk_id"] = f"{chunk.chunk_id}-dup-{seen[chunk.chunk_id]}"
        legal_dup_ids.append(data["chunk_id"])
        deduped.append(NormChunk.model_validate(data))
    return deduped, {
        "semantic_duplicate_count": len(semantic_duplicates),
        "semantic_duplicate_samples": semantic_duplicates[:30],
        "article_collision_discard_count": len(article_collisions),
        "article_collision_discard_samples": article_collisions[:30],
        "legal_dup_count": len(legal_dup_ids),
        "legal_dup_samples": legal_dup_ids[:30],
    }


def _slug(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:80] or _sha256(text)[:12]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)
