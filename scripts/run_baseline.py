#!/usr/bin/env python3
"""Unified driver for the 5 paper baselines (Manuscript_Architecture.md §4).

Usage:
    # Single task, single variant
    python scripts/run_baseline.py --variant proposed --task-id task-起重吊装-001

    # All variants on a single task
    python scripts/run_baseline.py --task-id task-起重吊装-001

    # Full batch (all variants × all tasks)
    python scripts/run_baseline.py --tasks data/eval/training_tasks_v1.jsonl \\
        --output data/eval/baseline_runs/

    # Scaffolding test (no LLM, no GPU): dry_run skips LLM calls
    python scripts/run_baseline.py --variant proposed --task-id task-起重吊装-001 --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.baselines import BASELINES, run_baseline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = PROJECT_ROOT / "data" / "eval" / "training_tasks_v1.jsonl"


def load_tasks(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]


def find_task(tasks: list[dict], task_id: str) -> dict:
    for t in tasks:
        if t.get("task_id") == task_id:
            return t
    raise SystemExit(f"task_id {task_id!r} not in {TASKS_PATH}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=sorted(BASELINES), help="single variant; omit for all")
    ap.add_argument("--task-id", help="single task; omit to use --tasks")
    ap.add_argument("--tasks", type=Path, default=TASKS_PATH, help="tasks JSONL")
    ap.add_argument("--output", type=Path, help="output dir for batch runs (default: stdout)")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true", help="skip LLM (scaffolding test)")
    args = ap.parse_args()

    tasks = load_tasks(args.tasks)
    if args.task_id:
        tasks = [find_task(tasks, args.task_id)]
    variants = [args.variant] if args.variant else sorted(BASELINES)
    opts = {"top_k": args.top_k, "dry_run": args.dry_run}

    results = []
    for task in tasks:
        for variant in variants:
            print(f"  running {variant} on {task['task_id']}…", flush=True)
            try:
                r = run_baseline(variant, task, **opts)
                results.append(r.to_dict())
                print(f"    ✓ {variant} llm={r.llm_calls} retr={r.retrieval_calls} "
                      f"norm_hits={len(r.retrieved_norm_ids)} case_hits={len(r.retrieved_case_ids)} "
                      f"grounded={r.grounded} elapsed={r.elapsed_seconds:.2f}s", flush=True)
            except Exception as e:
                print(f"    ✗ {variant} ERR: {e}", flush=True)
                results.append({"variant": variant, "task_id": task["task_id"], "error": str(e)})

    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        out_file = args.output / "results.jsonl"
        with out_file.open("w", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nWrote {len(results)} results to {out_file}")
    else:
        print(f"\n=== Summary: {len(results)} runs ===")
        for r in results:
            if "error" in r:
                print(f"  {r['variant']} on {r['task_id']}: ERR {r['error'][:80]}")
            else:
                print(f"  {r['variant']} on {r['task_id']}: "
                      f"prompt_chars={r['prompt_chars']} elapsed={r['elapsed_seconds']:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
