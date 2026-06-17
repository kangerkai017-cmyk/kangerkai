"""Agent-facing norm evidence retriever.

This is a thin compatibility entrypoint for LangGraph nodes. The formal
retrieval implementation lives in the Elasticsearch-backed `es_store`.
"""

from src.retrieval.es_store import retrieve_norms as _retrieve_norms


def retrieve_norm_evidence(queries: list[str], hazard_tags: list[str]) -> list[dict]:
    if not queries:
        return []
    return _retrieve_norms(queries, hazard_tags)
