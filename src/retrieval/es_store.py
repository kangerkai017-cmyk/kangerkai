import copy
import json
import threading
import time
import warnings
from collections import OrderedDict
from typing import Any, Optional

from elasticsearch import Elasticsearch, helpers
from sentence_transformers import SentenceTransformer

from src.config import (
    BM25_TOP_K,
    EMBEDDING_MODEL,
    ES_CASE_INDEX,
    ES_NORM_INDEX,
    ES_PASSWORD,
    ES_URL,
    ES_USERNAME,
    RERANK_ENABLED,
    RERANK_MODEL,
    RERANK_POOL,
    RETRIEVAL_CACHE_ENABLED,
    RETRIEVAL_CACHE_SIZE,
    RETRIEVAL_MODE,
    RETRIEVAL_TOP_K,
    RRF_K,
    TAG_TOP_K,
    VECTOR_TOP_K,
)
from src import metrics
from src.schema import NormChunk
from src.tags import scenario_tags_for_text
from src.trace_utils import trace_log

VECTOR_DIMS = 1024

_client: Optional[Elasticsearch] = None
_embedding_model: Optional[SentenceTransformer] = None
_reranker = None
_client_lock = threading.Lock()
_embedding_lock = threading.Lock()
_reranker_lock = threading.Lock()

# Bounded LRU for fused retrieval results, keyed on the full query signature.
_retrieval_cache: "OrderedDict[tuple, list[dict]]" = OrderedDict()
_retrieval_cache_lock = threading.Lock()


def clear_retrieval_cache() -> None:
    """Drop all cached retrieval results. Call after rebuilding an index so the
    cache cannot serve chunks from the old snapshot."""
    with _retrieval_cache_lock:
        _retrieval_cache.clear()


def get_es_client() -> Elasticsearch:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                kwargs: dict[str, Any] = {"hosts": [ES_URL], "request_timeout": 60}
                if ES_USERNAME or ES_PASSWORD:
                    kwargs["basic_auth"] = (ES_USERNAME, ES_PASSWORD)
                _client = Elasticsearch(**kwargs)
    return _client


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                t0 = time.perf_counter()
                _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
                trace_log(
                    "AGENT-RETRIEVAL",
                    f"embedding_model_loaded model={EMBEDDING_MODEL} seconds={time.perf_counter() - t0:.3f}",
                )
    return _embedding_model


def get_reranker():
    """Lazy process-singleton cross-encoder reranker (bge-reranker-v2-m3)."""
    global _reranker
    if _reranker is None:
        with _reranker_lock:
            if _reranker is None:
                from sentence_transformers import CrossEncoder

                _reranker = CrossEncoder(RERANK_MODEL)
    return _reranker


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    t0 = time.perf_counter()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    trace_log(
        "AGENT-RETRIEVAL",
        f"embedding_encode count={len(texts)} seconds={time.perf_counter() - t0:.3f}",
    )
    out = [v.tolist() for v in vectors]
    if out and len(out[0]) != VECTOR_DIMS:
        raise ValueError(
            f"Embedding model '{EMBEDDING_MODEL}' produced dim {len(out[0])} "
            f"but the index mapping expects {VECTOR_DIMS}. "
            f"Update VECTOR_DIMS and rebuild the index."
        )
    return out


def reset_norm_index() -> None:
    client = get_es_client()
    if client.indices.exists(index=ES_NORM_INDEX):
        client.indices.delete(index=ES_NORM_INDEX)
    create_chunk_index(ES_NORM_INDEX)


def reset_case_index() -> None:
    client = get_es_client()
    if client.indices.exists(index=ES_CASE_INDEX):
        client.indices.delete(index=ES_CASE_INDEX)
    create_chunk_index(ES_CASE_INDEX)


def create_chunk_index(index: str) -> None:
    client = get_es_client()
    if client.indices.exists(index=index):
        return
    client.indices.create(index=index, mappings=_chunk_mapping(), settings=_chunk_settings())


def index_norm_chunks(chunks: list[NormChunk], batch_size: int = 64) -> None:
    reset_norm_index()
    client = get_es_client()

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = embed_texts([c.text for c in batch])
        actions = []
        for chunk, vector in zip(batch, vectors):
            source = _chunk_source(chunk.model_dump(exclude_none=True), vector)
            actions.append(
                {
                    "_op_type": "index",
                    "_index": ES_NORM_INDEX,
                    "_id": chunk.chunk_id,
                    "_source": source,
                }
            )
        helpers.bulk(client, actions)
    client.indices.refresh(index=ES_NORM_INDEX)


def index_case_chunks(chunks: list, batch_size: int = 64) -> None:
    reset_case_index()
    client = get_es_client()

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = embed_texts([c.text for c in batch])
        actions = []
        for chunk, vector in zip(batch, vectors):
            source = _chunk_source(chunk.model_dump(exclude_none=True), vector)
            actions.append(
                {
                    "_op_type": "index",
                    "_index": ES_CASE_INDEX,
                    "_id": chunk.chunk_id,
                    "_source": source,
                }
            )
        helpers.bulk(client, actions)
    client.indices.refresh(index=ES_CASE_INDEX)


def retrieve_norms(
    queries: list[str],
    hazard_tags: list[str],
    top_k: int = RETRIEVAL_TOP_K,
    mode: str = RETRIEVAL_MODE,
) -> list[dict]:
    return _retrieve(ES_NORM_INDEX, queries, hazard_tags, top_k, mode)


def retrieve_cases(
    queries: list[str],
    hazard_tags: list[str],
    top_k: int = RETRIEVAL_TOP_K,
    mode: str = RETRIEVAL_MODE,
) -> list[dict]:
    return _retrieve(ES_CASE_INDEX, queries, hazard_tags, top_k, mode)


def fetch_norm_chunks_by_refs(refs: list[str]) -> list[dict]:
    """Resolve case `related_standards` refs to the exact norm article chunks
    they cite. A ref is 'STANDARD_CODE:article_id' (e.g. 'JGJ-80-2016:3.0.5');
    law-name refs ('《...》') and refs whose standard/article is not in the index
    are silently skipped. This is the case→norm evidence link: a retrieved
    accident case pulls back the precise norm articles it violated."""
    t0 = time.perf_counter()
    client = get_es_client()
    if not client.indices.exists(index=ES_NORM_INDEX):
        return []
    shoulds = []
    seen: set[tuple[str, str]] = set()
    for ref in refs or []:
        if not ref or ":" not in ref or ref.startswith("《"):
            continue
        code, _, article = ref.partition(":")
        code, article = code.strip(), article.strip()
        if not code or not article or (code, article) in seen:
            continue
        seen.add((code, article))
        shoulds.append(
            {
                "bool": {
                    "must": [
                        {"term": {"standard_code": code}},
                        {"term": {"article_id": article}},
                    ]
                }
            }
        )
    if not shoulds:
        return []
    resp = client.search(
        index=ES_NORM_INDEX,
        size=len(shoulds) * 2,
        query={"bool": {"should": shoulds, "minimum_should_match": 1}},
    )
    chunks = [_hit_to_chunk(h) for h in resp["hits"]["hits"]]
    trace_log(
        "AGENT-RETRIEVAL",
        f"case_norm_link refs={len(refs or [])} results={len(chunks)} seconds={time.perf_counter() - t0:.3f}",
    )
    return chunks


def _retrieve(
    index: str,
    queries: list[str],
    hazard_tags: list[str],
    top_k: int,
    mode: str,
) -> list[dict]:
    metrics.incr("retrieval_calls")
    if not RETRIEVAL_CACHE_ENABLED:
        return _retrieve_uncached(index, queries, hazard_tags, top_k, mode)

    key = (
        index,
        tuple(q.strip() for q in queries if q and q.strip()),
        tuple(hazard_tags or ()),
        top_k,
        mode,
        RERANK_ENABLED,
    )
    with _retrieval_cache_lock:
        cached = _retrieval_cache.get(key)
        if cached is not None:
            _retrieval_cache.move_to_end(key)
            return copy.deepcopy(cached)

    result = _retrieve_uncached(index, queries, hazard_tags, top_k, mode)

    with _retrieval_cache_lock:
        _retrieval_cache[key] = copy.deepcopy(result)
        _retrieval_cache.move_to_end(key)
        while len(_retrieval_cache) > RETRIEVAL_CACHE_SIZE:
            _retrieval_cache.popitem(last=False)
    return copy.deepcopy(result)


def _retrieve_uncached(
    index: str,
    queries: list[str],
    hazard_tags: list[str],
    top_k: int,
    mode: str,
) -> list[dict]:
    t0 = time.perf_counter()
    client = get_es_client()
    if not client.indices.exists(index=index):
        return []

    clean_queries = [q.strip() for q in queries if q and q.strip()]
    if not clean_queries:
        return []

    # Scenario tags inferred from the union of queries (for the tag route).
    merged_query = " ".join(clean_queries)
    scenario_tags = scenario_tags_for_text(merged_query)

    # Each query produces its own ranked list per route; RRF fuses all of them
    # so distinct hazards are not averaged into one diluted bag-of-terms.
    result_lists: list[list[dict]] = []
    if mode in ("bm25", "rrf_hybrid"):
        result_lists += [retrieve_bm25(index, q, BM25_TOP_K) for q in clean_queries]
    if mode in ("vector", "rrf_hybrid"):
        result_lists += [retrieve_vector(index, q, VECTOR_TOP_K) for q in clean_queries]
    if mode in ("tag", "rrf_hybrid"):
        result_lists.append(retrieve_tag(index, hazard_tags, scenario_tags, TAG_TOP_K))

    fused = rrf_fuse(
        result_lists,
        hazard_tags=hazard_tags,
        scenario_tags=scenario_tags,
        rrf_k=RRF_K,
    )
    if RERANK_ENABLED:
        fused = rerank(clean_queries, fused, top_k)
        chunks = [_hit_to_chunk(item["hit"]) for item in fused]
        trace_log(
            "AGENT-RETRIEVAL",
            f"retrieve index={index} mode={mode} queries={len(clean_queries)} rerank=true results={len(chunks)} seconds={time.perf_counter() - t0:.3f}",
        )
        return chunks
    chunks = [_hit_to_chunk(item["hit"]) for item in fused[:top_k]]
    trace_log(
        "AGENT-RETRIEVAL",
        f"retrieve index={index} mode={mode} queries={len(clean_queries)} rerank=false results={len(chunks)} seconds={time.perf_counter() - t0:.3f}",
    )
    return chunks


def rerank(queries: list[str], fused: list[dict], top_k: int) -> list[dict]:
    """Cross-encode the RRF top-`RERANK_POOL` candidates and reorder by relevance.

    Each candidate is scored against every query (max over queries) so multi-
    hazard retrieval is not penalized. Returns the top_k reordered fused items
    (same {"hit": ...} shape as rrf_fuse, so the caller is unchanged)."""
    if not fused or not queries:
        return fused[:top_k]
    pool = fused[: max(RERANK_POOL, top_k)]
    texts = [_hit_to_chunk(item["hit"]).get("text", "") for item in pool]
    pairs = [(q, t) for t in texts for q in queries]
    t0 = time.perf_counter()
    scores = get_reranker().predict(pairs)
    trace_log(
        "AGENT-RETRIEVAL",
        f"rerank pairs={len(pairs)} pool={len(pool)} seconds={time.perf_counter() - t0:.3f}",
    )
    nq = len(queries)
    scored = []
    for i, item in enumerate(pool):
        window = scores[i * nq : (i + 1) * nq]
        item = {**item, "rerank_score": float(max(window))}
        scored.append(item)
    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored[:top_k]


def retrieve_bm25(index: str, query: str, top_k: int) -> list[dict]:
    client = get_es_client()
    resp = client.search(
        index=index,
        size=top_k,
        query={
            "multi_match": {
                "query": query,
                "fields": [
                    "text^4",
                    "title^3",
                    "article_id^5",
                    "standard_code^3",
                    "scenario_tags^2",
                    "hazard_tags^2",
                    "requirement_type",
                    "chunk_kind",
                ],
                "type": "best_fields",
            }
        },
    )
    return list(resp["hits"]["hits"])


def retrieve_vector(index: str, query: str, top_k: int) -> list[dict]:
    client = get_es_client()
    query_vector = embed_texts([query])[0]
    resp = client.search(
        index=index,
        size=top_k,
        knn={
            "field": "text_vector",
            "query_vector": query_vector,
            "k": top_k,
            "num_candidates": max(top_k * 5, 50),
        },
    )
    return list(resp["hits"]["hits"])


def retrieve_tag(
    index: str,
    hazard_tags: list[str],
    scenario_tags: list[str],
    top_k: int,
) -> list[dict]:
    client = get_es_client()
    should: list[dict] = []
    # Both tag families score (no hard filter) so a single non-matching family
    # never drops an otherwise relevant chunk; hazard overlap is weighted higher
    # and exact tag-count overlap is used as an RRF tiebreaker downstream.
    if scenario_tags:
        should.append({"terms": {"scenario_tags": scenario_tags, "boost": 1.0}})
    if hazard_tags:
        should.append({"terms": {"hazard_tags": hazard_tags, "boost": 2.0}})
    if not should:
        warnings.warn(
            "retrieve_tag: no scenario_tags or hazard_tags provided; tag route will be empty."
        )
        return []
    query = {"bool": {"should": should, "minimum_should_match": 1}}
    resp = client.search(
        index=index,
        size=top_k,
        query=query,
    )
    return list(resp["hits"]["hits"])


def rrf_fuse(
    result_lists: list[list[dict]],
    hazard_tags: list[str],
    scenario_tags: list[str] | None = None,
    rrf_k: int = RRF_K,
) -> list[dict]:
    scenario_tags = scenario_tags or []
    fused: dict[str, dict] = {}

    for route_idx, hits in enumerate(result_lists):
        for rank, hit in enumerate(hits, 1):
            chunk_id = hit["_source"]["chunk_id"]
            item = fused.setdefault(
                chunk_id,
                {
                    "hit": hit,
                    "rrf_score": 0.0,
                    "best_rank": rank,
                    "route_ranks": {},
                },
            )
            item["rrf_score"] += 1.0 / (rrf_k + rank)
            item["best_rank"] = min(item["best_rank"], rank)
            item["route_ranks"][route_idx] = rank

    for item in fused.values():
        source = item["hit"]["_source"]
        item["hazard_overlap"] = _overlap(source.get("hazard_tags", []), hazard_tags)
        item["scenario_overlap"] = _overlap(source.get("scenario_tags", []), scenario_tags)

    return sorted(
        fused.values(),
        key=lambda x: (
            x["rrf_score"],
            x["hazard_overlap"],
            x["scenario_overlap"],
            -x["best_rank"],
        ),
        reverse=True,
    )


def count_index(index: str) -> int:
    client = get_es_client()
    if not client.indices.exists(index=index):
        return 0
    return int(client.count(index=index)["count"])


def ping() -> bool:
    return bool(get_es_client().ping())


def _chunk_mapping() -> dict:
    return {
        "dynamic": True,
        "properties": {
            "chunk_id": {"type": "keyword"},
            "doc_type": {"type": "keyword"},
            "schema_version": {"type": "keyword"},
            "chunk_kind": {"type": "keyword"},
            "standard_code": {"type": "keyword"},
            "case_id": {"type": "keyword"},
            "article_id": {"type": "keyword"},
            "scenario_tags": {"type": "keyword"},
            "hazard_tags": {"type": "keyword"},
            "requirement_type": {"type": "keyword"},
            "accident_type": {"type": "keyword"},
            "related_standards": {"type": "keyword"},
            "location": {"type": "text", "analyzer": "cjk"},
            "source_org": {"type": "keyword"},
            "source_date": {"type": "keyword"},
            "source_url": {"type": "keyword"},
            "source_path": {"type": "keyword"},
            "content_hash": {"type": "keyword"},
            "pipeline_version": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "cjk"},
            "text": {"type": "text", "analyzer": "cjk"},
            "text_vector": {
                "type": "dense_vector",
                "dims": VECTOR_DIMS,
                "index": True,
                "similarity": "cosine",
            },
            "_json": {"type": "text", "index": False},
        }
    }


def _chunk_settings() -> dict:
    return {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }
    }


def _chunk_source(chunk: dict, vector: list[float]) -> dict:
    return {
        **chunk,
        "scenario_tags": chunk.get("scenario_tags") or [],
        "hazard_tags": chunk.get("hazard_tags") or [],
        "text_vector": vector,
        "_json": json.dumps(chunk, ensure_ascii=False),
    }


def _hit_to_chunk(hit: dict) -> dict:
    source = hit["_source"]
    if "_json" in source:
        return json.loads(source["_json"])
    return source


def _overlap(left: list[str], right: list[str]) -> int:
    if not left or not right:
        return 0
    return len(set(left).intersection(right))
