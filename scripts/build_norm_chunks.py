#!/usr/bin/env python3
"""Build formal norm chunks from local PDF/DOCX source folders."""

import json
import os
import sys
from argparse import ArgumentParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data_pipeline.norm_chunker import (
    IMPORT_REPORT_PATH,
    NORM_CHUNKS_PATH,
    build_norm_chunks_with_diagnostics,
    validate_norm_chunks,
    write_norm_chunks,
)


def main() -> int:
    parser = ArgumentParser(description="Build formal norm chunks from local PDF/DOCX sources.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print quality-filter diagnostics without writing JSONL or import report",
    )
    args = parser.parse_args()

    chunks, diagnostics = build_norm_chunks_with_diagnostics()
    if args.dry_run:
        print_diagnostics(diagnostics)
        print(f"Dry run final chunk count: {len(chunks)}")
        return 0

    issues = validate_norm_chunks(chunks)
    report = write_norm_chunks(chunks, diagnostics=diagnostics)

    print(f"Wrote {len(chunks)} norm chunks to {NORM_CHUNKS_PATH}")
    print(f"Wrote import report to {IMPORT_REPORT_PATH}")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if issues:
        print("\nValidation failed:")
        for issue in issues[:50]:
            print(f"  - {issue}")
        if len(issues) > 50:
            print(f"  ... {len(issues) - 50} more")
        return 1
    return 0


def print_diagnostics(diagnostics: dict) -> None:
    print("Norm chunk dry-run diagnostics")
    print(f"raw_chunk_count={diagnostics['raw_chunk_count']}")
    print(f"after_quality_filter_count={diagnostics['after_quality_filter_count']}")
    print(f"final_chunk_count={diagnostics['final_chunk_count']}")

    quality = diagnostics["quality_filter"]
    print("\nQuality filter exclusions:")
    for reason, count in quality["excluded_counts"].items():
        print(f"  {reason}: {count}")
        for chunk_id in quality["excluded_samples"].get(reason, [])[:10]:
            print(f"    - {chunk_id}")

    jgj33 = quality["jgj33_whitelist"]
    print("\nJGJ-33-2012 whitelist:")
    print(f"  kept={jgj33['kept']}")
    print(f"  excluded={jgj33['excluded']}")
    print(f"  policy={jgj33['policy']}")

    dedupe = diagnostics["deduplication"]
    print("\nDeduplication:")
    print(f"  semantic_duplicate_count={dedupe['semantic_duplicate_count']}")
    print(f"  article_collision_discard_count={dedupe['article_collision_discard_count']}")
    for chunk_id in dedupe["article_collision_discard_samples"][:10]:
        print(f"    - {chunk_id}")
    print(f"  legal_dup_count={dedupe['legal_dup_count']}")
    for chunk_id in dedupe["legal_dup_samples"][:10]:
        print(f"    - {chunk_id}")


if __name__ == "__main__":
    raise SystemExit(main())
