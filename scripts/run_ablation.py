#!/usr/bin/env python3
"""5-way ablation driver for the proposed system (Manuscript_Architecture.md §4).

Each ablation flips ONE env switch before invoking the proposed baseline (B5).
Output is a benchmark-style metrics CSV directly comparable to baseline runs.

Ablations:
    A1 no_case_evidence       — ABLATION_CASE_EVIDENCE=false
    A2 no_case_norm_linker    — ABLATION_CASE_NORM_LINKER=false
    A3 no_query_rewrite       — QUERY_REWRITE_ENABLED=false
    A4 no_deterministic_ground — ABLATION_DETERMINISTIC_GROUND=false
    A5 no_arbitration         — ABLATION_ARBITRATION=false

Per-ablation results subtracted from the full B5 baseline isolate the
contribution of each mechanism.

Usage:
    python scripts/run_ablation.py --task-id task-起重吊装-009
    python scripts/run_ablation.py --limit 5 --output data/eval/ablation_pilot/
"""

import argparse
import copy
import csv
import importlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.experiment_metadata import build_metadata, safe_base_url_domain, write_metadata


ABLATIONS = {
    "full":                   {},                                                # control = full proposed
    "no_case_evidence":       {"ABLATION_CASE_EVIDENCE":      "false"},
    "no_case_norm_linker":    {"ABLATION_CASE_NORM_LINKER":   "false"},
    "no_query_rewrite":       {"QUERY_REWRITE_ENABLED":       "false"},
    "no_deterministic_ground":{"ABLATION_DETERMINISTIC_GROUND":"false"},
    "no_arbitration":         {"ABLATION_ARBITRATION":        "false"},
}


def reload_config_and_baselines():
    """Force reload so env-derived flags pick up. Re-imports the agent + baseline
    modules that closed over config values at import time."""
    import src.config
    importlib.reload(src.config)
    # Reload modules that reference config flags at module load
    for mod in [
        "src.agents.subgraphs.evidence",
        "src.agents.subgraphs.authoring",
        "src.agents.graph",
        "src.agents.unified_graph",
        "src.baselines.b5_proposed",
        "src.baselines",
    ]:
        if mod in sys.modules:
            importlib.reload(sys.modules[mod])


def run_one(task: dict, ablation: str, opts: dict) -> dict:
    saved = {k: os.environ.get(k) for k in ABLATIONS[ablation]}
    for k, v in ABLATIONS[ablation].items():
        os.environ[k] = v
    try:
        reload_config_and_baselines()
        from src.baselines import run_baseline
        r = run_baseline("proposed", task, **opts)
        d = r.to_dict()
        d["ablation"] = ablation
        return d
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-id")
    ap.add_argument("--tasks", type=Path,
                    default=Path(__file__).resolve().parents[1] / "data" / "eval" / "training_tasks_v1.jsonl")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ablations", nargs="+", choices=sorted(ABLATIONS), default=sorted(ABLATIONS))
    ap.add_argument("--output", type=Path, required=False)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tasks = [json.loads(l) for l in args.tasks.open(encoding="utf-8") if l.strip()]
    if args.task_id:
        tasks = [t for t in tasks if t["task_id"] == args.task_id]
        if not tasks:
            raise SystemExit(f"task_id {args.task_id} not found")
    if args.limit:
        tasks = tasks[:args.limit]

    print(f"  {len(args.ablations)} ablations × {len(tasks)} tasks = {len(args.ablations) * len(tasks)} runs")

    from src.evaluation.baseline_metrics import compute_metrics, aggregate_metrics
    from src.config import LLM_MODEL, OPENAI_BASE_URL

    rows = []
    for ti, task in enumerate(tasks, 1):
        for ab in args.ablations:
            print(f"  [{ti}/{len(tasks)}] {ab} on {task['task_id']}…", flush=True)
            try:
                d = run_one(task, ab, {"dry_run": args.dry_run})
                m = compute_metrics(d, task)
                m["ablation"] = ab
                m["model"] = LLM_MODEL
                m["base_url_domain"] = safe_base_url_domain(OPENAI_BASE_URL)
                rows.append(m)
                print(f"    ✓ ground={m['grounding_rate']:.2f} link={m['link_resolution_rate']:.2f} "
                      f"elapsed={m['elapsed_seconds']:.1f}s", flush=True)
            except Exception as e:
                print(f"    ✗ ERR: {e}", flush=True)

    # Per-ablation aggregation
    from collections import defaultdict
    import statistics as st
    by_ab = defaultdict(list)
    for r in rows:
        by_ab[r["ablation"]].append(r)
    summary = {}
    for ab, rs in by_ab.items():
        summary[ab] = {"n_tasks": len(rs)}
        for k in ("grounding_rate", "hallucination_rate", "norm_citation_validity",
                  "hazard_coverage", "case_relevance", "link_resolution_rate",
                  "norm_recall_at_k", "elapsed_seconds"):
            vals = [r[k] for r in rs if r.get(k) is not None]
            if vals:
                summary[ab][f"{k}_mean"] = round(st.mean(vals), 4)

    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        if rows:
            keys = list(rows[0].keys())
            with (args.output / "metrics.csv").open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
        (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        write_metadata(
            args.output,
            build_metadata(
                project_root=Path(__file__).resolve().parents[1],
                command=sys.argv,
                tasks_path=args.tasks,
                script_path=Path(__file__).resolve(),
                run_kind="ablation",
                ablations=args.ablations,
            ),
        )
        print(f"\nResults → {args.output}")

    print("\n=== Ablation summary ===")
    if "full" in summary:
        print(f"  [full]    n={summary['full']['n_tasks']}  "
              f"ground={summary['full'].get('grounding_rate_mean', 0):.3f}  "
              f"link={summary['full'].get('link_resolution_rate_mean', 0):.3f}")
        for ab, agg in summary.items():
            if ab == "full": continue
            print(f"  [{ab}]   n={agg['n_tasks']}  "
                  f"ground={agg.get('grounding_rate_mean', 0):.3f}  "
                  f"link={agg.get('link_resolution_rate_mean', 0):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
