#!/usr/bin/env python3
"""A/B retrieval evaluation: norm retrieval quality with reranker OFF vs ON.

Gold is bootstrapped from accident cases (query = narrative, relevant = the norm
articles the case cites as violated). Prints a before/after table of
recall@k / hit@k / nDCG@k / MRR — the numbers for "adding rerank improves X→Y".

No LLM involved. Embedding + reranker run on the GPU; pin a free card with
CUDA_VISIBLE_DEVICES and bypass the proxy for local ES, e.g.:

    NO_PROXY=localhost,127.0.0.1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    CUDA_VISIBLE_DEVICES=1 python scripts/eval_retrieval.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import ES_NORM_INDEX
from src.evaluation.retrieval_eval import evaluate, link_resolution_summary
from src.retrieval.es_store import count_index, ping


KS = (1, 3, 5)


def _fmt_row(label: str, agg: dict) -> str:
    cells = [f"recall@{k}={agg[f'recall@{k}']:.3f}" for k in KS]
    cells += [f"ndcg@{k}={agg[f'ndcg@{k}']:.3f}" for k in KS]
    cells.append(f"mrr={agg['mrr']:.3f}")
    return f"{label:<14} " + "  ".join(cells)


def main() -> int:
    if not ping():
        print("Cannot connect to Elasticsearch. Start it first.")
        return 2
    if count_index(ES_NORM_INDEX) == 0:
        print("Norm index is empty. Run scripts/build_norm_index.py first.")
        return 3

    link = link_resolution_summary()
    print("=== case→norm 链接解析率 ===")
    print(json.dumps(link, ensure_ascii=False, indent=2))

    print("\n=== 检索评测（gold 来自案例 related_standards）===")
    base = evaluate(rerank_enabled=False, ks=KS)
    print(f"评测案例数: {base['evaluated_cases']} | mode: {base['mode']}")
    print(_fmt_row("baseline", base["aggregate"]))

    # Lever 1: tier-aware query rewriting (needs the LLM).
    try:
        rw = evaluate(rerank_enabled=False, ks=KS, rewrite_enabled=True)
        print(_fmt_row("+rewrite", rw["aggregate"]))
        delta = {k: round(rw["aggregate"][k] - base["aggregate"][k], 4) for k in base["aggregate"]}
        print(_fmt_row("  Δ rewrite", delta))
    except Exception as exc:
        print(f"[+rewrite 跳过] 查询改写不可用（LLM 未启动？）：{exc}")

    # Lever 2: cross-encoder rerank (needs the rerank model).
    try:
        rr = evaluate(rerank_enabled=True, ks=KS)
        print(_fmt_row("+rerank", rr["aggregate"]))
        delta = {k: round(rr["aggregate"][k] - base["aggregate"][k], 4) for k in base["aggregate"]}
        print(_fmt_row("  Δ rerank", delta))
    except Exception as exc:
        print(f"[+rerank 跳过] reranker 不可用（模型未下载？）：{exc}")

    # Both levers stacked.
    try:
        both = evaluate(rerank_enabled=True, ks=KS, rewrite_enabled=True)
        print(_fmt_row("+both", both["aggregate"]))
        delta = {k: round(both["aggregate"][k] - base["aggregate"][k], 4) for k in base["aggregate"]}
        print(_fmt_row("  Δ both", delta))
    except Exception as exc:
        print(f"[+both 跳过]：{exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
