#!/usr/bin/env python3
"""Build Chroma index from sample data."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data_pipeline.sample_data import get_norm_chunks, get_case_chunks
from src.retrieval.vector_store import add_chunks_to_store, get_collection


def main():
    norms = get_norm_chunks()
    cases = get_case_chunks()
    print(f"Loading {len(norms)} norm chunks and {len(cases)} case chunks...")

    add_chunks_to_store(norms, cases)

    norm_col = get_collection("norms")
    case_col = get_collection("cases")
    print(f"Done. norms: {norm_col.count()}, cases: {case_col.count()}")


if __name__ == "__main__":
    main()
