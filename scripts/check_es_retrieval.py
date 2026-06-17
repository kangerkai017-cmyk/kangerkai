#!/usr/bin/env python3
"""Run ES retrieval smoke checks across bm25/vector/tag/rrf_hybrid modes."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval.es_store import count_index, fetch_norm_chunks_by_refs, ping, retrieve_norms
from src.config import ES_NORM_INDEX


QUERIES = [
    ("脚手架拆除 高处坠落 连墙件", ["高处坠落", "坍塌"]),
    ("临边作业 防护栏杆 洞口", ["高处坠落"]),
    ("安全带 坠落悬挂 技术要求", ["高处坠落"]),
    ("高处作业 分级 坠落范围半径", ["高处坠落"]),
]

SPOT_QUERIES = [
    ("混凝土泵车 支腿 垫木 支设 JGJ 33", ["机械伤害", "构件失稳"], "JGJ-33-2012"),
    ("建筑施工起重吊装 吊索具 吊装作业 安全要求 JGJ 276", ["起重伤害"], "JGJ-276-2012"),
    ("扣件式钢管脚手架 连墙件 剪刀撑 拆除 验收 JGJ 130", ["高处坠落", "坍塌"], "JGJ-130-2011"),
    ("建筑施工安全检查 起重吊装 脚手架 施工用电 高处作业 JGJ 59", ["高处坠落", "触电"], "JGJ-59-2011"),
    ("安全网 密目式 耐冲击 阻燃 技术要求 GB 5725", ["高处坠落"], "GB-5725-2009"),
    ("电力 带电作业 个体防护 绝缘手套 安全带 GB 39800.6", ["触电", "电弧伤害"], "GB-39800.6-2023"),
    ("建筑市政施工现场 高处坠落 安全防护 通用规范", ["高处坠落"], "GB-55034-2022"),
    ("附着式升降脚手架 防坠 防倾 提升 下降 检查验收 JGJ 202", ["高处坠落", "坍塌"], "JGJ-202-2010"),
    ("高处作业吊篮 安全锁 安全绳 作业人员 不超过2人 JGJ 202", ["高处坠落"], "JGJ-202-2010"),
    ("外挂防护架 提升 连墙件 安装 使用验收 JGJ 202", ["高处坠落", "坍塌"], "JGJ-202-2010"),
    ("模板支架 安装 拆除 安全管理 高处作业 JGJ 162", ["高处坠落", "坍塌"], "JGJ-162-2008"),
    ("脚手架 搭设 拆除 连墙件 安全管理 GB 51210", ["高处坠落", "坍塌"], "GB-51210-2016"),
]


def main() -> int:
    if not ping():
        print("Cannot connect to Elasticsearch. Check ES_URL and start Elasticsearch first.")
        return 2

    count = count_index(ES_NORM_INDEX)
    print(f"index: {ES_NORM_INDEX}")
    print(f"count: {count}")
    if count == 0:
        print("Index is empty. Run scripts/build_norm_index.py first.")
        return 3

    for mode in ["bm25", "vector", "tag", "rrf_hybrid"]:
        print(f"\n=== mode: {mode} ===")
        for query, hazards in QUERIES:
            results = retrieve_norms([query], hazards, top_k=5, mode=mode)
            ids = [r.get("chunk_id", "") for r in results[:5]]
            unique_ids = len(ids) == len(set(ids))
            print(f"\nQUERY: {query}")
            print(f"results: {len(results)} unique_top5: {unique_ids}")
            for i, result in enumerate(results[:5], 1):
                print(
                    f"{i}. {result.get('chunk_id')} | "
                    f"{result.get('standard_code')} | "
                    f"{result.get('chunk_kind')} | "
                    f"{result.get('article_id')}"
                )
            if not results:
                return 4
            if not unique_ids:
                return 5

    print("\n=== new standard spot checks ===")
    for query, hazards, expected_standard in SPOT_QUERIES:
        results = retrieve_norms([query], hazards, top_k=8, mode="rrf_hybrid")
        ids = [r.get("chunk_id", "") for r in results]
        standards = [r.get("standard_code", "") for r in results]
        print(f"\nQUERY: {query}")
        print(f"expected: {expected_standard} hit: {expected_standard in standards}")
        for i, result in enumerate(results[:8], 1):
            print(
                f"{i}. {result.get('chunk_id')} | "
                f"{result.get('standard_code')} | "
                f"{result.get('chunk_kind')} | "
                f"{result.get('article_id')}"
            )
        if not results:
            return 6
        if len(ids) != len(set(ids)):
            return 7
        if expected_standard not in standards:
            return 8

    print("\n=== case→norm link spot check ===")
    linked = fetch_norm_chunks_by_refs(["JGJ-33-2012:8.5.1", "JGJ-33-2012:8.5.2"])
    linked_articles = {r.get("article_id") for r in linked}
    for result in linked:
        print(
            f"{result.get('chunk_id')} | "
            f"{result.get('standard_code')} | "
            f"{result.get('chunk_kind')} | "
            f"{result.get('article_id')}"
        )
    if {"8.5.1", "8.5.2"} - linked_articles:
        return 9
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
