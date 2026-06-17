#!/usr/bin/env python3
"""Build formal accident-case chunks from data/事故案例收集.md."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data_pipeline.case_chunker import (
    CASE_CHUNKS_PATH,
    IMPORT_REPORT_PATH,
    build_case_chunks,
    validate_case_chunks,
    write_case_chunks,
)


def main() -> int:
    chunks = build_case_chunks()
    issues = validate_case_chunks(chunks)
    report = write_case_chunks(chunks)

    print(f"Wrote {len(chunks)} case chunks to {CASE_CHUNKS_PATH}")
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


if __name__ == "__main__":
    raise SystemExit(main())
