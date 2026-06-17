#!/usr/bin/env python3
"""Build the Elasticsearch case index from formal accident-case chunks."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import ES_CASE_INDEX
from src.data_pipeline.case_chunker import (
    CASE_CHUNKS_PATH,
    load_case_chunks,
    validate_case_chunks,
)
from src.retrieval.es_store import count_index, index_case_chunks, ping


def main() -> int:
    chunks = load_case_chunks(CASE_CHUNKS_PATH)
    issues = validate_case_chunks(chunks)
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

    index_case_chunks(chunks)
    count = count_index(ES_CASE_INDEX)
    print(f"Built Elasticsearch case index from {CASE_CHUNKS_PATH}")
    print(f"index: {ES_CASE_INDEX}")
    print(f"case count: {count}")
    if count != len(chunks):
        print(f"Count mismatch: index has {count}, JSONL has {len(chunks)}")
        return 3
    print("norm index was not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
