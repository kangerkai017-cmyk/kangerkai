#!/usr/bin/env python3
"""End-to-end benchmark runner: 5 baselines × N tasks → metrics CSV + summary.

Wraps run_baseline + baseline_metrics into one pass. Results persist as JSONL
(raw runs) + CSV (per-task metrics) + JSON (aggregate summary).

Usage:
    # Pilot — 10 tasks, all 5 variants
    python scripts/run_benchmark.py --limit 10 --output data/eval/bench_pilot/

    # Full batch
    python scripts/run_benchmark.py --output data/eval/bench_full/

    # Specific theme only
    python scripts/run_benchmark.py --theme 起重吊装 --output data/eval/bench_lift/
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.baselines import BASELINES, run_baseline
from src.config import LLM_MODEL, OPENAI_BASE_URL
from src.evaluation.baseline_metrics import compute_metrics, aggregate_metrics
from scripts.experiment_metadata import build_metadata, safe_base_url_domain, write_metadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = PROJECT_ROOT / "data" / "eval" / "training_tasks_v1.jsonl"


def load_tasks(path: Path, limit: int | None, theme: str | None, tier: str | None) -> list[dict]:
    tasks = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    if theme:
        tasks = [t for t in tasks if t["theme"] == theme]
    if tier:
        tasks = [t for t in tasks if (t.get("_meta") or {}).get("tier") == tier]
    if limit:
        tasks = tasks[:limit]
    return tasks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, default=TASKS_PATH)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--variants", nargs="+", choices=sorted(BASELINES),
                    default=sorted(BASELINES))
    ap.add_argument("--limit", type=int, help="limit number of tasks")
    ap.add_argument("--theme", help="filter by theme")
    ap.add_argument("--tier", choices=["S", "W"], help="filter by gold tier")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--continue-on-error", action="store_true", default=True)
    args = ap.parse_args()

    tasks = load_tasks(args.tasks, args.limit, args.theme, args.tier)
    args.output.mkdir(parents=True, exist_ok=True)
    print(f"  running {len(args.variants)} variants × {len(tasks)} tasks = "
          f"{len(args.variants) * len(tasks)} runs")
    print(f"  output: {args.output}")

    raw_path = args.output / "raw_results.jsonl"
    metrics_csv = args.output / "metrics.csv"
    summary_path = args.output / "summary.json"
    metadata_path = args.output / "metadata.json"

    raw_rows: list[dict] = []
    metric_rows: list[dict] = []
    opts = {"top_k": args.top_k, "dry_run": args.dry_run}

    with raw_path.open("w", encoding="utf-8") as raw_fh:
        for ti, task in enumerate(tasks, 1):
            for variant in args.variants:
                print(f"  [{ti}/{len(tasks)}] {variant} on {task['task_id']}…", flush=True)
                try:
                    r = run_baseline(variant, task, **opts)
                    rd = r.to_dict()
                    raw_fh.write(json.dumps(rd, ensure_ascii=False) + "\n")
                    raw_fh.flush()
                    raw_rows.append(rd)
                    m = compute_metrics(rd, task)
                    m["model"] = LLM_MODEL
                    m["base_url_domain"] = safe_base_url_domain(OPENAI_BASE_URL)
                    metric_rows.append(m)
                    print(f"    ✓ ground={m['grounding_rate']:.2f} "
                          f"norm_val={m['norm_citation_validity']:.2f} "
                          f"haz_cov={m['hazard_coverage']:.2f} "
                          f"elapsed={m['elapsed_seconds']:.1f}s", flush=True)
                except Exception as e:
                    print(f"    ✗ ERR: {e}", flush=True)
                    if not args.continue_on_error:
                        raise

    # CSV
    if metric_rows:
        keys = list(metric_rows[0].keys())
        with metrics_csv.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(metric_rows)

    # Aggregate summary
    summary = aggregate_metrics(metric_rows)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_metadata(
        args.output,
        build_metadata(
            project_root=PROJECT_ROOT,
            command=sys.argv,
            tasks_path=args.tasks,
            script_path=Path(__file__).resolve(),
            run_kind="benchmark",
            variants=args.variants,
        ),
    )

    print(f"\n=== Summary ({len(metric_rows)} runs) ===")
    print(f"raw_results: {raw_path}")
    print(f"metrics_csv: {metrics_csv}")
    print(f"summary:     {summary_path}")
    print(f"metadata:    {metadata_path}")
    print()
    for variant, agg in summary.items():
        print(f"  [{variant}] n={agg['n_tasks']}")
        for k in ("grounding_rate_mean", "norm_citation_validity_mean",
                  "hazard_coverage_mean", "case_relevance_mean",
                  "norm_recall_at_k_mean", "elapsed_seconds_mean"):
            if k in agg:
                print(f"    {k}: {agg[k]:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
