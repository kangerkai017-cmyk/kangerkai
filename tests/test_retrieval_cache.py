"""Retrieval LRU cache: identical query signatures skip the ES round-trip."""

from src.retrieval import es_store


def _patch_uncached(monkeypatch):
    calls = {"n": 0}

    def fake(index, queries, hazard_tags, top_k, mode):
        calls["n"] += 1
        return [{"chunk_id": f"{index}:{queries[0]}", "text": "x"}]

    monkeypatch.setattr(es_store, "_retrieve_uncached", fake)
    es_store.clear_retrieval_cache()
    return calls


def test_second_identical_query_is_cached(monkeypatch):
    calls = _patch_uncached(monkeypatch)
    a = es_store._retrieve("idx", ["高处作业"], [], 5, "rrf_hybrid")
    b = es_store._retrieve("idx", ["高处作业"], [], 5, "rrf_hybrid")
    assert a == b
    assert calls["n"] == 1  # second call served from cache


def test_different_signature_misses(monkeypatch):
    calls = _patch_uncached(monkeypatch)
    es_store._retrieve("idx", ["高处作业"], [], 5, "rrf_hybrid")
    es_store._retrieve("idx", ["脚手架"], [], 5, "rrf_hybrid")
    assert calls["n"] == 2


def test_cache_returns_isolated_copies(monkeypatch):
    _patch_uncached(monkeypatch)
    a = es_store._retrieve("idx", ["高处作业"], [], 5, "rrf_hybrid")
    a[0]["chunk_id"] = "MUTATED"
    b = es_store._retrieve("idx", ["高处作业"], [], 5, "rrf_hybrid")
    assert b[0]["chunk_id"] != "MUTATED"  # caller mutation does not poison cache


def test_disabled_cache_always_calls(monkeypatch):
    calls = _patch_uncached(monkeypatch)
    monkeypatch.setattr(es_store, "RETRIEVAL_CACHE_ENABLED", False)
    es_store._retrieve("idx", ["高处作业"], [], 5, "rrf_hybrid")
    es_store._retrieve("idx", ["高处作业"], [], 5, "rrf_hybrid")
    assert calls["n"] == 2
