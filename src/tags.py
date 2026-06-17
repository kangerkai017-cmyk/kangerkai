"""Shared tag taxonomy and keyword→tag mapping rules.

Both the chunk pipeline (`norm_chunker`) and the retrieval layer (`es_store`)
use these helpers so scenario_tags / hazard_tags stay identical at index time
and query time.

The vocabulary lives in `data/taxonomy/tags.yaml` (the single human-maintained
extension point). When a new tag/standard is needed, edit that file, then
regenerate chunks and rebuild the ES index. If the YAML is missing, the
hardcoded defaults below are used.
"""

from pathlib import Path

_TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "data" / "taxonomy" / "tags.yaml"

_DEFAULTS: dict = {
    "scenario_rules": [
        ["临边", "临边作业"], ["洞口", "洞口作业"], ["攀登", "攀登作业"],
        ["悬空", "悬空作业"], ["操作平台", "操作平台"], ["交叉", "交叉作业"],
        ["安全带", "安全带"], ["安全网", "安全网"], ["坠落防护", "坠落防护"],
        ["脚手架搭设", "脚手架搭设"], ["搭设", "脚手架搭设"],
        ["脚手架拆除", "脚手架拆除"], ["拆除", "脚手架拆除"],
        ["验收", "检查验收"], ["检查", "检查验收"],
        ["材料", "材料构配件"], ["构配件", "材料构配件"],
        ["模板", "模板支架"], ["支架", "模板支架"],
    ],
    "hazard_rules": [
        ["坠落", "高处坠落"], ["高处", "高处坠落"], ["物体打击", "物体打击"],
        ["坠物", "物体打击"], ["坍塌", "坍塌"], ["失稳", "构件失稳"],
        ["承载", "构件失稳"], ["荷载", "构件失稳"], ["电", "触电"],
    ],
    "high_altitude_keywords": ["高处", "坠落", "临边", "洞口", "安全带", "安全网", "攀登", "悬空"],
    "high_altitude_scenario_tags": [
        "高处作业", "临边作业", "洞口作业", "攀登作业", "悬空作业", "安全带", "安全网", "坠落防护",
    ],
    "collapse_scenario_tags": ["脚手架搭设", "脚手架拆除", "模板支架"],
    "standard_tag_hints": {},
    "scenario_fallback": ["脚手架使用"],
    "hazard_fallback": ["构件失稳"],
}


def _load_taxonomy() -> dict:
    try:
        import yaml

        with _TAXONOMY_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in data.items() if v is not None})
    return merged


_TAX = _load_taxonomy()

# Backward-compatible exports (tuples for the legacy ordered_tags signature).
SCENARIO_KEYWORD_RULES: list[tuple[str, str]] = [tuple(r) for r in _TAX["scenario_rules"]]
HAZARD_KEYWORD_RULES: list[tuple[str, str]] = [tuple(r) for r in _TAX["hazard_rules"]]


def ordered_tags(
    defaults: list[str],
    rules: list[tuple[str, str]],
    text: str,
) -> list[str]:
    """Apply keyword rules to text, keeping `defaults` at the front."""
    tags: list[str] = []
    for tag in defaults:
        if tag not in tags:
            tags.append(tag)
    for needle, tag in rules:
        if needle in text and tag not in tags:
            tags.append(tag)
    return tags


def scenario_tags_for_text(text: str, standard_code: str = "") -> list[str]:
    """Infer scenario tags from arbitrary text (chunk body or user query).

    Shared by the chunk pipeline and the retrieval layer so index-time and
    query-time tags are consistent.
    """
    defaults = (
        ["高处作业"]
        if any(k in text for k in _TAX["high_altitude_keywords"])
        else []
    )
    tags = ordered_tags(defaults, SCENARIO_KEYWORD_RULES, text)
    if "脚手架" in text and "脚手架使用" not in tags:
        tags.append("脚手架使用")
    for tag in _standard_hint(standard_code, "scenario"):
        if tag not in tags:
            tags.append(tag)
    return tags


def hazard_tags_for_text(
    text: str,
    scenario_tags: list[str],
    standard_code: str = "",
) -> list[str]:
    """Infer hazard tags from text + already-inferred scenario tags."""
    tags = ordered_tags([], HAZARD_KEYWORD_RULES, text)
    if set(_TAX["high_altitude_scenario_tags"]).intersection(scenario_tags):
        if "高处坠落" not in tags:
            tags.insert(0, "高处坠落")
    if any(t in scenario_tags for t in _TAX["collapse_scenario_tags"]):
        if "坍塌" not in tags:
            tags.append("坍塌")
    for tag in _standard_hint(standard_code, "hazard"):
        if tag not in tags:
            tags.append(tag)
    return tags


def scenario_fallback() -> list[str]:
    return list(_TAX["scenario_fallback"])


def hazard_fallback(scenario_tags: list[str]) -> list[str]:
    if "高处坠落" in hazard_from_scenario_defaults(scenario_tags):
        return ["高处坠落"]
    if any(t in scenario_tags for t in _TAX["high_altitude_scenario_tags"]):
        return ["高处坠落"]
    return list(_TAX["hazard_fallback"])


def hazard_from_scenario_defaults(scenario_tags: list[str]) -> list[str]:
    if any(t in scenario_tags for t in _TAX["high_altitude_scenario_tags"]):
        return ["高处坠落"]
    return []


def _standard_hint(standard_code: str, kind: str) -> list[str]:
    if not standard_code:
        return []
    hints = _TAX.get("standard_tag_hints", {}) or {}
    for prefix, payload in hints.items():
        if standard_code.startswith(prefix):
            return list((payload or {}).get(kind, []) or [])
    return []
