#!/usr/bin/env python3
"""Build the Elasticsearch norms index from formal norm chunks."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import ES_NORM_INDEX
from src.data_pipeline.norm_chunker import NORM_CHUNKS_PATH, load_norm_chunks, validate_norm_chunks
from src.retrieval.es_store import count_index, index_norm_chunks, ping


def main() -> int:
    chunks = load_norm_chunks(NORM_CHUNKS_PATH)
    issues = validate_norm_chunks(chunks)
    if issues:
        print("Refusing to build index because chunk validation failed:")
        for issue in issues[:50]:
            print(f"  - {issue}")
        if len(issues) > 50:
            print(f"  ... {len(issues) - 50} more")
        return 1

    if not ping():
        print("Cannot connect to Elasticsearch. Check ES_URL and start Elasticsearch first.")
        return 2

    index_norm_chunks(chunks)
    count = count_index(ES_NORM_INDEX)
    print(f"Built Elasticsearch norms index from {NORM_CHUNKS_PATH}")
    print(f"index: {ES_NORM_INDEX}")
    print(f"norms count: {count}")
    if count != len(chunks):
        print(f"Count mismatch: index has {count}, JSONL has {len(chunks)}")
        return 3
    print("case index was not rebuilt and no mock cases were added.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
