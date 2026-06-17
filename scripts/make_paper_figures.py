#!/usr/bin/env python3
"""Generate paper §5 figures from a completed benchmark run.

Outputs:
    fig_bar_metrics.png        — 5 variants × 6 metrics grouped bar chart
    fig_radar_proposed_vs_b4.png — radar comparing proposed vs strongest baseline
    fig_link_resolution.png    — per-task link_resolution histogram (proposed only)

Usage:
    python scripts/make_paper_figures.py \
        --bench-dir data/eval/experiments/full_bench_20260604_0335
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.evaluation.baseline_metrics import compute_metrics

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = PROJECT_ROOT / "data" / "eval" / "training_tasks_v1.jsonl"

VARIANT_ORDER = ["llm_only", "norm_only", "naive_dual", "optimized", "proposed"]
VARIANT_LABELS = {
    "llm_only":  "B1 LLM only",
    "norm_only": "B2 Norm-only RAG",
    "naive_dual":"B3 Naive dual RAG",
    "optimized": "B4 Optimized RAG",
    "proposed":  "B5 Proposed",
}
METRIC_LABELS = {
    "grounding_rate":          "Grounding rate",
    "norm_citation_validity":  "Norm citation validity",
    "hazard_coverage":         "Hazard coverage",
    "case_relevance":          "Case relevance",
    "norm_recall_at_k":        "Norm recall@k",
    "link_resolution_rate":    "Link resolution rate (§5.2)",
}

# Use serif for paper look. matplotlib default DejaVu Sans handles Chinese on Linux
# only if a CJK font is installed; we keep figure text English for portability.
plt.rcParams.update({
    "font.family": "DejaVu Serif",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def load_metrics(bench_dir: Path):
    rows = [json.loads(l) for l in (bench_dir / "raw_results.jsonl").open(encoding="utf-8")]
    tasks = {json.loads(l)["task_id"]: json.loads(l)
             for l in TASKS_PATH.open(encoding="utf-8")}
    out = []
    for r in rows:
        t = tasks.get(r["task_id"])
        if not t:
            continue
        out.append(compute_metrics(r, t))
    return out


def aggregate(rows, metric):
    by_v = {v: [] for v in VARIANT_ORDER}
    for r in rows:
        if r["variant"] in by_v:
            by_v[r["variant"]].append(r[metric])
    return {v: (sum(vals) / len(vals)) if vals else 0.0 for v, vals in by_v.items()}


def fig_bar(rows, out_path: Path):
    metrics = list(METRIC_LABELS.keys())
    data = np.array([[aggregate(rows, m)[v] for m in metrics]
                     for v in VARIANT_ORDER])

    x = np.arange(len(metrics))
    width = 0.16
    fig, ax = plt.subplots(figsize=(11, 5))
    colors = ["#bbbbbb", "#7eb2dd", "#5990c4", "#356b9a", "#c43c3c"]
    for i, v in enumerate(VARIANT_ORDER):
        bars = ax.bar(x + (i - 2) * width, data[i], width,
                      label=VARIANT_LABELS[v], color=colors[i],
                      edgecolor="black" if v == "proposed" else None,
                      linewidth=1.2 if v == "proposed" else 0)
    ax.set_xticks(x)
    ax.set_xticklabels([METRIC_LABELS[m] for m in metrics], rotation=14, ha="right")
    ax.set_ylabel("Mean over 46 tasks")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_title("Five-baseline comparison on training material generation quality")
    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {out_path}")


def fig_radar(rows, out_path: Path):
    """Radar: proposed vs strongest baseline (B4 optimized)."""
    metrics = ["grounding_rate", "norm_citation_validity", "hazard_coverage",
               "case_relevance", "norm_recall_at_k", "link_resolution_rate"]
    aggs = {m: aggregate(rows, m) for m in metrics}
    labels = [METRIC_LABELS[m] for m in metrics]

    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})
    for variant, color, lw in [("optimized", "#356b9a", 1.6), ("proposed", "#c43c3c", 2.2)]:
        vals = [aggs[m][variant] for m in metrics] + [aggs[metrics[0]][variant]]
        ax.plot(angles, vals, "-o", label=VARIANT_LABELS[variant],
                color=color, linewidth=lw, markersize=5)
        ax.fill(angles, vals, alpha=0.10, color=color)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels([".25", ".50", ".75", "1.0"])
    ax.grid(alpha=0.4)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.08), frameon=False)
    ax.set_title("Proposed vs strongest baseline (B4)", pad=24)
    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {out_path}")


def fig_link(rows, out_path: Path):
    """Per-task link_resolution_rate for proposed only."""
    vals = sorted(r["link_resolution_rate"] for r in rows if r["variant"] == "proposed")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(vals, bins=20, color="#c43c3c", edgecolor="black", linewidth=0.6)
    ax.set_xlabel("Link resolution rate")
    ax.set_ylabel("Number of tasks")
    ax.set_xlim(0, 1.0)
    ax.set_title("Case→norm link resolution per task (B5 proposed, n=46)")
    mean_v = sum(vals) / len(vals) if vals else 0
    ax.axvline(mean_v, color="black", linestyle="--", linewidth=1, label=f"mean = {mean_v:.3f}")
    ax.legend(frameon=False)
    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-dir", type=Path, required=True)
    args = ap.parse_args()

    out_dir = args.bench_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_metrics(args.bench_dir)
    print(f"  loaded {len(rows)} metric rows from {args.bench_dir}")

    fig_bar(rows, out_dir / "fig_bar_metrics.png")
    fig_radar(rows, out_dir / "fig_radar_proposed_vs_b4.png")
    fig_link(rows, out_dir / "fig_link_resolution.png")
    print(f"  figures → {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
