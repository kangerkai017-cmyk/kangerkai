#!/usr/bin/env python3
"""Generate ablation figures from a completed ablation run.

Outputs:
    fig_ablation_deltas.png      — Δ-from-full grouped bar across 5 ablations × 6 metrics
    fig_link_by_ablation.png     — link_resolution_rate per ablation (boxplot)
    fig_ablation_radar.png       — radar overlay of all 6 conditions

Usage:
    python scripts/make_ablation_figures.py \
        --ablation-dir data/eval/experiments/full_ablation_20260604_0714
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ABL_ORDER = [
    "full", "no_query_rewrite", "no_case_evidence",
    "no_case_norm_linker", "no_deterministic_ground", "no_arbitration",
]
ABL_LABELS = {
    "full": "Full (proposed)",
    "no_query_rewrite": "− query rewrite",
    "no_case_evidence": "− case evidence",
    "no_case_norm_linker": "− case→norm linker",
    "no_deterministic_ground": "− deterministic ground",
    "no_arbitration": "− arbitration",
}
METRIC_LABELS = {
    "grounding_rate":         "Grounding rate",
    "norm_citation_validity": "Norm citation validity",
    "hazard_coverage":        "Hazard coverage",
    "case_relevance":         "Case relevance",
    "norm_recall_at_k":       "Norm recall@k",
    "link_resolution_rate":   "Link resolution rate",
}

plt.rcParams.update({
    "font.family": "DejaVu Serif",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def load_metrics(csv_path: Path):
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    by_ab = defaultdict(lambda: defaultdict(list))
    for r in rows:
        ab = r["ablation"]
        for k in METRIC_LABELS:
            by_ab[ab][k].append(float(r[k]))
    means = {ab: {k: (sum(v) / len(v)) if v else 0.0 for k, v in mv.items()}
             for ab, mv in by_ab.items()}
    return by_ab, means


def fig_deltas(means, out_path: Path):
    """Δ from full per (ablation × metric)."""
    metrics = list(METRIC_LABELS.keys())
    abls = [a for a in ABL_ORDER if a != "full"]
    full = means["full"]
    deltas = np.array([[means[a][m] - full[m] for m in metrics] for a in abls])

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(metrics))
    width = 0.16
    colors = ["#9c9c9c", "#5990c4", "#2a4a7f", "#8a4a4a", "#c43c3c"]
    for i, ab in enumerate(abls):
        ax.bar(x + (i - 2) * width, deltas[i], width,
               label=ABL_LABELS[ab], color=colors[i])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([METRIC_LABELS[m] for m in metrics], rotation=14, ha="right")
    ax.set_ylabel("Δ from full proposed (negative = mechanism contributed)")
    ax.set_ylim(-0.7, 0.1)
    ax.legend(loc="lower left", frameon=False, fontsize=9, ncol=2)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_title("Per-mechanism contribution (ablation Δ across 46 tasks)")
    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {out_path}")


def fig_link_box(by_ab, out_path: Path):
    """Boxplot of link_resolution_rate per ablation."""
    abls = ABL_ORDER
    vals = [by_ab[a]["link_resolution_rate"] for a in abls]
    fig, ax = plt.subplots(figsize=(10, 5))
    bp = ax.boxplot(
        vals, labels=[ABL_LABELS[a] for a in abls],
        showmeans=True, meanline=True,
        boxprops=dict(facecolor="#dbe7f1"), patch_artist=True,
        medianprops=dict(color="#2a4a7f"),
        meanprops=dict(color="#c43c3c", linewidth=2),
    )
    ax.set_ylabel("Link resolution rate")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Link resolution rate by ablation (§5.2 mechanism isolation)")
    ax.tick_params(axis="x", rotation=14)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {out_path}")


def fig_radar(means, out_path: Path):
    metrics = list(METRIC_LABELS.keys())
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"projection": "polar"})
    colors = {"full": "#c43c3c",
              "no_query_rewrite": "#9c9c9c",
              "no_case_evidence": "#2a4a7f",
              "no_case_norm_linker": "#5990c4",
              "no_deterministic_ground": "#8a4a4a",
              "no_arbitration": "#5b8a4a"}
    for ab in ABL_ORDER:
        vals = [means[ab][m] for m in metrics] + [means[ab][metrics[0]]]
        lw = 2.4 if ab == "full" else 1.3
        ax.plot(angles, vals, "-o", label=ABL_LABELS[ab],
                color=colors[ab], linewidth=lw, markersize=4)
        if ab == "full":
            ax.fill(angles, vals, alpha=0.10, color=colors[ab])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([METRIC_LABELS[m] for m in metrics], fontsize=9)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels([".25", ".50", ".75", "1.0"])
    ax.grid(alpha=0.4)
    ax.legend(loc="upper right", bbox_to_anchor=(1.45, 1.10), frameon=False, fontsize=9)
    ax.set_title("Ablation overlay on 6 metrics", pad=24)
    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ablation-dir", type=Path, required=True)
    args = ap.parse_args()
    csv_path = args.ablation_dir / "metrics.csv"
    if not csv_path.exists():
        raise SystemExit(f"missing {csv_path}")
    by_ab, means = load_metrics(csv_path)
    out_dir = args.ablation_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig_deltas(means, out_dir / "fig_ablation_deltas.png")
    fig_link_box(by_ab, out_dir / "fig_link_by_ablation.png")
    fig_radar(means, out_dir / "fig_ablation_radar.png")
    print(f"  figures → {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
