#!/usr/bin/env python3
"""Build v1 training task set (deterministic, zero LLM).

One task per accident case that cites ≥1 in-library norm article. Per
research_plan §9.2 each task carries: scenario / expected_hazards /
expected_norm_refs / expected_case_refs / expected_training_points.

Training points are *extracted* — not generated — from the cited norm articles'
mandatory clauses (必须|应|不得|严禁|禁止|不应|宜). This is what we want for an
auto-evaluation gold set: deterministic, reproducible, auditable, model-bias-free.

Output:
    data/eval/training_tasks_v1.jsonl
    data/eval/training_tasks_v1_report.json

Usage:
    NO_PROXY=localhost,127.0.0.1 python scripts/build_training_tasks.py
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data_pipeline.case_chunker import load_case_chunks
from src.retrieval.es_store import fetch_norm_chunks_by_refs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "eval" / "training_tasks_v1.jsonl"
REPORT_PATH = PROJECT_ROOT / "data" / "eval" / "training_tasks_v1_report.json"

# Theme assignment priority: more specific tags win, in this order.
THEME_PRIORITY = [
    ("脚手架", {"脚手架搭设", "脚手架拆除", "脚手架使用", "模板支架"}),
    ("临时用电", {"临时用电", "配电箱", "漏电保护", "接地接零", "触电"}),
    ("起重吊装", {"起重吊装", "塔式起重机", "施工升降机", "施工机械", "机械伤害", "起重伤害"}),
    ("高处作业", {
        "高处作业", "临边作业", "洞口作业", "攀登作业", "悬空作业",
        "安全带", "安全网", "坠落防护", "操作平台", "高处坠落",
    }),
]
THEME_FALLBACK_BY_ACCIDENT = {
    "高处坠落": "高处作业",
    "物体打击": "高处作业",
    "坍塌": "脚手架",
    "起重伤害": "起重吊装",
    "机械伤害": "起重吊装",
    "触电": "临时用电",
}

# Mandatory-clause keywords. Order matters for ranking strength (强制 > 推荐).
MANDATORY_KW = re.compile(r"(必须|严禁|禁止|不得|不应|应当|应|宜)")
SCENARIO_TRUNC = 220  # max chars of case.process retained as task.scenario_summary


def assign_theme(scenario_tags: list[str], accident_type: str) -> str | None:
    """Route to one of 4 themes. Uses scenario_tags + accident_type ONLY —
    hazard_tags is excluded because keyword-based auto-tagging produces false
    positives (e.g. 电梯→触电) that misroute non-electric cases."""
    if accident_type == "触电":
        return "临时用电"
    tagset = set(scenario_tags)
    for theme, keys in THEME_PRIORITY:
        if tagset & keys:
            return theme
    return THEME_FALLBACK_BY_ACCIDENT.get(accident_type)


def _clean_ocr_noise(s: str) -> str:
    """Strip OCR/PDF-extraction artifacts (curly quotes, stray asterisks/
    commas-before-punctuation, runs of whitespace) without touching legitimate
    Chinese punctuation."""
    s = s.replace("”", "").replace("“", "").replace("’", "").replace("‘", "")
    s = s.replace("*", "")
    s = re.sub(r",\s*[\*]", "", s)
    s = re.sub(r"\s+", "", s)  # tighten — all whitespace inside a clause is OCR noise
    s = re.sub(r"^[,，、]+", "", s)
    return s


def extract_mandatory_clauses(norm_text: str, max_clauses: int = 2) -> list[str]:
    """Pull 1–2 mandatory-clause sentences from a norm article body."""
    m = re.search(r"正文：?\s*(.*)", norm_text, re.DOTALL)
    body = (m.group(1) if m else norm_text).strip()
    # Strip leading article number "4.1.19 "
    body = re.sub(r"^\d+(?:\.\d+)+\s*", "", body)
    # Sentence-segment on Chinese sentence terminators ONLY. OCR often inserts
    # spurious newlines mid-sentence (e.g. "并经检查\n确认无误"), so do NOT
    # split on \n — _clean_ocr_noise will collapse those.
    sentences = [s.strip() for s in re.split(r"[。；]+", body) if s.strip()]
    out: list[str] = []
    for s in sentences:
        cleaned = _clean_ocr_noise(s)
        if len(cleaned) < 8:
            continue
        if MANDATORY_KW.search(cleaned):
            out.append(cleaned)
            if len(out) >= max_clauses:
                break
    if not out:
        for s in sentences:
            cleaned = _clean_ocr_noise(s)
            if len(cleaned) >= 12:
                out.append(cleaned)
                break
    return out


def _proxy_articles_for_standard(standard_code: str, case, k: int = 2) -> list[str]:
    """Find the top-k most retrieval-relevant articles within `standard_code`
    for cases that only cite the code (no article). Uses ES BM25 against the
    case's accident_type + hazard_tags as query."""
    from src.config import ES_NORM_INDEX
    from src.retrieval.es_store import get_es_client

    query_terms = [case.accident_type or ""] + list(case.hazard_tags or [])
    query = " ".join(t for t in query_terms if t).strip()
    if not query:
        return []
    client = get_es_client()
    try:
        resp = client.search(
            index=ES_NORM_INDEX,
            size=k,
            query={
                "bool": {
                    "must": [{"match": {"text": query}}],
                    "filter": [{"term": {"standard_code": standard_code}}],
                }
            },
        )
    except Exception:
        return []
    out = []
    for hit in resp.get("hits", {}).get("hits", []):
        src = hit.get("_source", {})
        code = src.get("standard_code")
        art = src.get("article_id")
        if code and art:
            out.append(f"{code}:{art}")
    return out


def find_similar_cases(target_case_id: str, all_cases: list, k: int = 3) -> list[str]:
    """Same-accident-type cases as cheap 'similar case' references."""
    target = next(c for c in all_cases if c.case_id == target_case_id)
    same_type = [
        c.case_id for c in all_cases
        if c.accident_type == target.accident_type
        and c.case_id != target_case_id
        and c.chunk_kind == "case_summary"
    ]
    return same_type[:k]


def build_tasks() -> tuple[list[dict], dict]:
    chunks = load_case_chunks()
    summaries = [c for c in chunks if c.chunk_kind == "case_summary"]

    tasks: list[dict] = []
    skipped: dict[str, list[str]] = defaultdict(list)
    theme_counter: Counter = Counter()

    for case in summaries:
        case_id = case.case_id

        article_refs = sorted({
            r for r in (case.related_standards or [])
            if ":" in r and not r.startswith("《")
        })
        # Fallback: standard-only refs (case cites a code with no article) —
        # if the code is in library, pull the most retrieval-relevant article
        # for the case's accident_type as a proxy. Marked in _meta so eval can
        # weight Tier-S (article-cited) vs Tier-W (standard-only) tasks.
        standard_only_used: list[str] = []
        if not article_refs:
            standard_refs = [
                r for r in (case.related_standards or [])
                if r and ":" not in r and not r.startswith("《")
            ]
            for sref in standard_refs:
                proxies = _proxy_articles_for_standard(sref, case)
                for ref in proxies:
                    if ref not in article_refs:
                        article_refs.append(ref)
                        standard_only_used.append(sref)
            if not article_refs:
                skipped["no_article_refs"].append(case_id)
                continue

        resolved_chunks = fetch_norm_chunks_by_refs(article_refs)
        if not resolved_chunks:
            skipped["no_resolved_norm_chunks"].append(case_id)
            continue

        theme = assign_theme(case.scenario_tags or [], case.accident_type)
        if theme is None:
            skipped["no_theme"].append(case_id)
            continue

        training_points: list[dict] = []
        resolved_refs: list[str] = []
        for nc in resolved_chunks:
            code = nc.get("standard_code")
            art = nc.get("article_id")
            if not (code and art):
                continue
            ref = f"{code}:{art}"
            clauses = extract_mandatory_clauses(nc.get("text", ""))
            for cl in clauses:
                training_points.append({"text": cl, "source_norm_ref": ref})
            if ref not in resolved_refs:
                resolved_refs.append(ref)

        if not training_points:
            skipped["no_extractable_clauses"].append(case_id)
            continue

        scenario_summary = (case.process or "").strip()
        if len(scenario_summary) > SCENARIO_TRUNC:
            scenario_summary = scenario_summary[:SCENARIO_TRUNC].rstrip() + "..."

        theme_counter[theme] += 1
        task_id = f"task-{theme}-{theme_counter[theme]:03d}"

        tasks.append({
            "task_id": task_id,
            "theme": theme,
            "scenario_summary": scenario_summary,
            "expected_hazards": list(case.hazard_tags or []),
            "expected_scenario_tags": list(case.scenario_tags or []),
            "expected_norm_refs": resolved_refs,
            "expected_case_refs": [case_id] + find_similar_cases(case_id, summaries),
            "expected_training_points": training_points,
            "source_case_id": case_id,
            "source_case_title": case.case_title,
            "source_accident_type": case.accident_type,
            "construction_method": "deterministic_v1",
            "_meta": {
                "raw_related_standards": list(case.related_standards or []),
                "article_refs_attempted": article_refs,
                "article_refs_resolved": resolved_refs,
                "norm_chunks_resolved": len(resolved_chunks),
                "training_points_count": len(training_points),
                "tier": "S" if not standard_only_used else "W",
                "standard_only_fallback": sorted(set(standard_only_used)),
            },
        })

    report = {
        "schema_version": "training_task_v1",
        "task_count": len(tasks),
        "by_theme": dict(theme_counter),
        "skipped_counts": {k: len(v) for k, v in skipped.items()},
        "skipped_case_ids": dict(skipped),
        "total_cases_seen": len(summaries),
    }
    return tasks, report


def write(tasks: list[dict], report: dict) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        for t in tasks:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    tasks, report = build_tasks()
    write(tasks, report)
    print(f"Wrote {len(tasks)} tasks to {OUTPUT_PATH}")
    print(f"Wrote report to {REPORT_PATH}")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
