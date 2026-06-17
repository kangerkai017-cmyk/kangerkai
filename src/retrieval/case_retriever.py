"""Agent-facing case evidence retriever.

This thin wrapper preserves the Agent call contract. It delegates to the
Elasticsearch-backed store; `safety_case_chunks` may be empty until case data is
indexed.
"""

from src.retrieval.es_store import retrieve_cases as _retrieve_cases


def retrieve_case_evidence(queries: list[str], hazard_tags: list[str]) -> list[dict]:
    if not queries:
        return []
    return _retrieve_cases(queries, hazard_tags)
