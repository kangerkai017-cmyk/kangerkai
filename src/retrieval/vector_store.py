import json
import threading
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions

from src.config import CHROMA_DIR, EMBEDDING_MODEL, RETRIEVAL_TOP_K
from src.schema import NormChunk, CaseChunk

_embedding_fn: Optional[embedding_functions.SentenceTransformerEmbeddingFunction] = None
_client: Optional[chromadb.PersistentClient] = None
_embedding_lock = threading.Lock()
_client_lock = threading.Lock()

NORM_COLLECTION = "norms"
CASE_COLLECTION = "cases"


def _get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is None:
        with _embedding_lock:
            if _embedding_fn is None:
                _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=EMBEDDING_MODEL
                )
    return _embedding_fn


def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _client


def get_collection(name: str):
    client = _get_client()
    ef = _get_embedding_fn()
    return client.get_or_create_collection(name=name, embedding_function=ef)


def reset_collections():
    client = _get_client()
    for name in [NORM_COLLECTION, CASE_COLLECTION]:
        try:
            client.delete_collection(name)
        except Exception:
            pass


def add_chunks_to_store(norm_chunks: list[NormChunk], case_chunks: list[CaseChunk]):
    reset_collections()

    if norm_chunks:
        norm_collection = get_collection(NORM_COLLECTION)
        norm_collection.add(
            ids=[c.chunk_id for c in norm_chunks],
            documents=[c.text for c in norm_chunks],
            metadatas=[_norm_metadata(c) for c in norm_chunks],
        )

    if case_chunks:
        case_collection = get_collection(CASE_COLLECTION)
        case_collection.add(
            ids=[c.chunk_id for c in case_chunks],
            documents=[c.text for c in case_chunks],
            metadatas=[_case_metadata(c) for c in case_chunks],
        )


def _norm_metadata(c: NormChunk) -> dict:
    return {
        "chunk_id": c.chunk_id,
        "doc_type": "norm",
        "standard_name": c.standard_name,
        "scenario_tags": ",".join(c.scenario_tags),
        "hazard_tags": ",".join(c.hazard_tags),
        "article_id": c.article_id or "",
        "requirement_type": c.requirement_type or "",
        "_json": c.model_dump_json(),
    }


def _case_metadata(c: CaseChunk) -> dict:
    return {
        "chunk_id": c.chunk_id,
        "doc_type": "case",
        "case_title": c.case_title,
        "accident_type": c.accident_type or "",
        "scenario_tags": ",".join(c.scenario_tags),
        "hazard_tags": ",".join(c.hazard_tags),
        "_json": c.model_dump_json(),
    }


def _query_and_parse(collection, query_text: str, n_results: int) -> list[dict]:
    if collection.count() == 0:
        return []
    results = collection.query(
        query_texts=[query_text], n_results=min(n_results, collection.count())
    )
    chunks = []
    if results["ids"] and results["ids"][0]:
        for meta in results["metadatas"][0]:
            if meta and "_json" in meta:
                chunks.append(json.loads(meta["_json"]))
    return chunks


def _score_by_hazard_overlap(chunk: dict, hazard_tags: list[str]) -> int:
    chunk_tags = chunk.get("hazard_tags", [])
    if not hazard_tags or not chunk_tags:
        return 0
    return sum(1 for t in hazard_tags if t in chunk_tags)


def retrieve_norms(
    queries: list[str],
    hazard_tags: list[str],
    top_k: int = RETRIEVAL_TOP_K,
) -> list[dict]:
    collection = get_collection(NORM_COLLECTION)
    if collection.count() == 0:
        return []

    seen_ids: set[str] = set()
    all_chunks: list[dict] = []

    for query in queries:
        chunks = _query_and_parse(collection, query, top_k)
        for c in chunks:
            cid = c.get("chunk_id", "")
            if cid not in seen_ids:
                seen_ids.add(cid)
                all_chunks.append(c)

    all_chunks.sort(key=lambda c: _score_by_hazard_overlap(c, hazard_tags), reverse=True)
    return all_chunks[: top_k * 2]


def retrieve_cases(
    queries: list[str],
    hazard_tags: list[str],
    top_k: int = RETRIEVAL_TOP_K,
) -> list[dict]:
    collection = get_collection(CASE_COLLECTION)
    if collection.count() == 0:
        return []

    seen_ids: set[str] = set()
    all_chunks: list[dict] = []

    for query in queries:
        chunks = _query_and_parse(collection, query, top_k)
        for c in chunks:
            cid = c.get("chunk_id", "")
            if cid not in seen_ids:
                seen_ids.add(cid)
                all_chunks.append(c)

    all_chunks.sort(key=lambda c: _score_by_hazard_overlap(c, hazard_tags), reverse=True)
    return all_chunks[: top_k * 2]
