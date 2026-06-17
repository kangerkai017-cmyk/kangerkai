#!/usr/bin/env python3
"""Statistical uncertainty analysis for benchmark and ablation metrics.

Inputs are one or more ``LABEL=path/to/metrics.csv`` files. The script writes:

- group_summary.csv: mean, SD, median, and bootstrap 95% CI by dataset/group.
- within_dataset_comparisons.csv: paired Wilcoxon tests against the reference
  group (``proposed`` for benchmarks, ``full`` for ablations).
- between_dataset_comparisons.csv: paired Wilcoxon tests for matching groups
  across datasets in the same family.
- analysis.json: machine-readable copy of all tables.
- report.md: compact manuscript-facing report.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon


DEFAULT_METRICS = [
    "grounding_rate",
    "norm_citation_validity",
    "hazard_coverage",
    "case_relevance",
    "norm_recall_at_k",
    "case_recall_at_k",
    "link_resolution_rate",
    "elapsed_seconds",
]


@dataclass(frozen=True)
class MetricInput:
    label: str
    path: Path
    family: str
    group_col: str
    df: pd.DataFrame


def parse_input_spec(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        path = Path(spec)
        return path.parent.name or path.stem, path
    label, raw_path = spec.split("=", 1)
    label = label.strip()
    if not label:
        raise SystemExit(f"empty label in input spec: {spec!r}")
    return label, Path(raw_path)


def infer_family_and_group(df: pd.DataFrame, path: Path) -> tuple[str, str]:
    if "ablation" in df.columns:
        return "ablation", "ablation"
    if "variant" in df.columns:
        return "benchmark", "variant"
    raise SystemExit(f"{path} has neither 'variant' nor 'ablation' column")


def load_input(spec: str) -> MetricInput:
    label, path = parse_input_spec(spec)
    if not path.exists():
        raise SystemExit(f"metrics file not found: {path}")
    df = pd.read_csv(path)
    family, group_col = infer_family_and_group(df, path)
    if "task_id" not in df.columns:
        raise SystemExit(f"{path} is missing task_id")
    return MetricInput(label=label, path=path, family=family, group_col=group_col, df=df)


def available_metrics(inputs: Iterable[MetricInput], requested: list[str]) -> list[str]:
    cols = set.intersection(*(set(inp.df.columns) for inp in inputs))
    metrics = [m for m in requested if m in cols]
    if not metrics:
        raise SystemExit("none of the requested metrics are present in every input")
    return metrics


def numeric_values(series: pd.Series) -> np.ndarray:
    vals = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    return vals[np.isfinite(vals)]


def bootstrap_mean_ci(
    vals: np.ndarray,
    *,
    iterations: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    if len(vals) == 0:
        return math.nan, math.nan
    if len(vals) == 1:
        return float(vals[0]), float(vals[0])
    rng = np.random.default_rng(seed)
    samples = rng.choice(vals, size=(iterations, len(vals)), replace=True)
    means = samples.mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def cliff_delta(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) == 0 or len(y) == 0:
        return math.nan
    gt = 0
    lt = 0
    for xv in x:
        gt += int(np.sum(xv > y))
        lt += int(np.sum(xv < y))
    return float((gt - lt) / (len(x) * len(y)))


def paired_wilcoxon(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    if len(x) != len(y):
        raise ValueError("paired arrays must have the same length")
    if len(x) == 0:
        return math.nan, math.nan
    diff = x - y
    if np.allclose(diff, 0):
        return 0.0, 1.0
    res = wilcoxon(x, y, alternative="two-sided", zero_method="wilcox")
    return float(res.statistic), float(res.pvalue)


def holm_bonferroni(pvals: list[float]) -> list[float]:
    indexed = [(i, p) for i, p in enumerate(pvals) if np.isfinite(p)]
    adjusted = [math.nan] * len(pvals)
    if not indexed:
        return adjusted
    indexed.sort(key=lambda item: item[1])
    m = len(indexed)
    running = 0.0
    for rank, (idx, p) in enumerate(indexed, start=1):
        adj = min(1.0, (m - rank + 1) * p)
        running = max(running, adj)
        adjusted[idx] = running
    return adjusted


def summarize_groups(
    inputs: list[MetricInput],
    metrics: list[str],
    *,
    iterations: int,
    seed: int,
) -> list[dict]:
    rows: list[dict] = []
    for input_idx, inp in enumerate(inputs):
        for group, gdf in inp.df.groupby(inp.group_col, dropna=False):
            for metric_idx, metric in enumerate(metrics):
                vals = numeric_values(gdf[metric])
                ci_lo, ci_hi = bootstrap_mean_ci(
                    vals,
                    iterations=iterations,
                    seed=seed + input_idx * 1009 + metric_idx * 101,
                )
                rows.append(
                    {
                        "dataset": inp.label,
                        "family": inp.family,
                        "source_csv": str(inp.path),
                        "group_col": inp.group_col,
                        "group": str(group),
                        "metric": metric,
                        "n": int(len(vals)),
                        "mean": round(float(np.mean(vals)), 6) if len(vals) else math.nan,
                        "sd": round(float(np.std(vals, ddof=1)), 6) if len(vals) > 1 else 0.0,
                        "median": round(float(np.median(vals)), 6) if len(vals) else math.nan,
                        "ci95_low": round(ci_lo, 6) if np.isfinite(ci_lo) else math.nan,
                        "ci95_high": round(ci_hi, 6) if np.isfinite(ci_hi) else math.nan,
                    }
                )
    return rows


def merged_pair(df: pd.DataFrame, group_col: str, ref: str, comp: str, metric: str) -> pd.DataFrame:
    ref_df = df[df[group_col] == ref][["task_id", metric]].rename(columns={metric: "ref_value"})
    comp_df = df[df[group_col] == comp][["task_id", metric]].rename(columns={metric: "comp_value"})
    merged = ref_df.merge(comp_df, on="task_id", how="inner")
    merged["ref_value"] = pd.to_numeric(merged["ref_value"], errors="coerce")
    merged["comp_value"] = pd.to_numeric(merged["comp_value"], errors="coerce")
    return merged.dropna(subset=["ref_value", "comp_value"])


def within_dataset_comparisons(inputs: list[MetricInput], metrics: list[str]) -> list[dict]:
    rows: list[dict] = []
    for inp in inputs:
        reference = "full" if inp.family == "ablation" else "proposed"
        groups = [str(g) for g in inp.df[inp.group_col].dropna().unique()]
        if reference not in groups:
            continue
        for comp in sorted(g for g in groups if g != reference):
            for metric in metrics:
                merged = merged_pair(inp.df, inp.group_col, reference, comp, metric)
                x = merged["ref_value"].to_numpy(dtype=float)
                y = merged["comp_value"].to_numpy(dtype=float)
                stat, p = paired_wilcoxon(x, y)
                delta = cliff_delta(x, y)
                rows.append(
                    {
                        "comparison_scope": "within_dataset",
                        "dataset": inp.label,
                        "family": inp.family,
                        "metric": metric,
                        "reference_group": reference,
                        "comparison_group": comp,
                        "n_pairs": int(len(merged)),
                        "reference_mean": round(float(np.mean(x)), 6) if len(x) else math.nan,
                        "comparison_mean": round(float(np.mean(y)), 6) if len(y) else math.nan,
                        "mean_delta_reference_minus_comparison": (
                            round(float(np.mean(x - y)), 6) if len(x) else math.nan
                        ),
                        "wilcoxon_statistic": round(stat, 6) if np.isfinite(stat) else math.nan,
                        "p_value": p,
                        "cliffs_delta": round(delta, 6) if np.isfinite(delta) else math.nan,
                    }
                )
    add_holm(rows)
    return rows


def between_dataset_comparisons(inputs: list[MetricInput], metrics: list[str]) -> list[dict]:
    rows: list[dict] = []
    for i, left in enumerate(inputs):
        for right in inputs[i + 1 :]:
            if left.family != right.family:
                continue
            left_groups = set(left.df[left.group_col].dropna().astype(str))
            right_groups = set(right.df[right.group_col].dropna().astype(str))
            for group in sorted(left_groups & right_groups):
                for metric in metrics:
                    ldf = left.df[left.df[left.group_col].astype(str) == group][["task_id", metric]]
                    rdf = right.df[right.df[right.group_col].astype(str) == group][["task_id", metric]]
                    merged = ldf.rename(columns={metric: "left_value"}).merge(
                        rdf.rename(columns={metric: "right_value"}),
                        on="task_id",
                        how="inner",
                    )
                    merged["left_value"] = pd.to_numeric(merged["left_value"], errors="coerce")
                    merged["right_value"] = pd.to_numeric(merged["right_value"], errors="coerce")
                    merged = merged.dropna(subset=["left_value", "right_value"])
                    x = merged["left_value"].to_numpy(dtype=float)
                    y = merged["right_value"].to_numpy(dtype=float)
                    stat, p = paired_wilcoxon(x, y)
                    delta = cliff_delta(x, y)
                    rows.append(
                        {
                            "comparison_scope": "between_dataset",
                            "family": left.family,
                            "metric": metric,
                            "group": group,
                            "left_dataset": left.label,
                            "right_dataset": right.label,
                            "n_pairs": int(len(merged)),
                            "left_mean": round(float(np.mean(x)), 6) if len(x) else math.nan,
                            "right_mean": round(float(np.mean(y)), 6) if len(y) else math.nan,
                            "mean_delta_left_minus_right": (
                                round(float(np.mean(x - y)), 6) if len(x) else math.nan
                            ),
                            "wilcoxon_statistic": round(stat, 6) if np.isfinite(stat) else math.nan,
                            "p_value": p,
                            "cliffs_delta": round(delta, 6) if np.isfinite(delta) else math.nan,
                        }
                    )
    add_holm(rows)
    return rows


def add_holm(rows: list[dict]) -> None:
    if not rows:
        return
    buckets: dict[tuple[str, str], list[int]] = {}
    for idx, row in enumerate(rows):
        buckets.setdefault((row.get("comparison_scope", ""), row["metric"]), []).append(idx)
    for indices in buckets.values():
        adjusted = holm_bonferroni([rows[i]["p_value"] for i in indices])
        for idx, adj in zip(indices, adjusted):
            rows[idx]["p_value_holm"] = adj
            rows[idx]["significant_holm_0_05"] = bool(np.isfinite(adj) and adj < 0.05)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    pd.DataFrame(rows).to_csv(path, index=False)


def clean_float_for_json(obj):
    if isinstance(obj, float) and not np.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {k: clean_float_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_float_for_json(v) for v in obj]
    return obj


def fmt(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "NA"
    try:
        if not np.isfinite(value):
            return "NA"
    except TypeError:
        return str(value)
    return f"{float(value):.{digits}f}"


def report_table(rows: list[dict], family: str, metric: str, limit_groups: set[str] | None = None) -> list[str]:
    selected = [
        r for r in rows
        if r["family"] == family
        and r["metric"] == metric
        and (limit_groups is None or r["group"] in limit_groups)
    ]
    if not selected:
        return []
    out = [
        f"### {family.title()} `{metric}`",
        "",
        "| Dataset | Group | n | Mean | 95% CI |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in selected:
        out.append(
            "| {dataset} | {group} | {n} | {mean} | [{lo}, {hi}] |".format(
                dataset=r["dataset"],
                group=r["group"],
                n=r["n"],
                mean=fmt(r["mean"]),
                lo=fmt(r["ci95_low"]),
                hi=fmt(r["ci95_high"]),
            )
        )
    out.append("")
    return out


def write_markdown_report(
    path: Path,
    inputs: list[MetricInput],
    metrics: list[str],
    summaries: list[dict],
    within: list[dict],
    between: list[dict],
) -> None:
    lines = [
        "# Statistical uncertainty report",
        "",
        "This report uses task-level metrics from completed experiment CSV files only. "
        "It does not infer results for unrun datasets.",
        "",
        "## Inputs",
        "",
        "| Dataset | Family | Metrics CSV |",
        "|---|---|---|",
    ]
    for inp in inputs:
        lines.append(f"| {inp.label} | {inp.family} | `{inp.path}` |")
    lines.extend(
        [
            "",
            "## Bootstrap confidence intervals",
            "",
            "Non-parametric bootstrap 95% confidence intervals are reported for group means.",
            "",
        ]
    )

    for family in ("benchmark", "ablation"):
        group_filter = {"proposed"} if family == "benchmark" else {"full", "no_case_evidence", "no_case_norm_linker"}
        for metric in ("grounding_rate", "norm_recall_at_k", "norm_citation_validity", "link_resolution_rate", "elapsed_seconds"):
            lines.extend(report_table(summaries, family, metric, group_filter))

    lines.extend(
        [
            "## Paired tests",
            "",
            "Wilcoxon signed-rank tests use task-matched pairs. Holm-Bonferroni "
            "adjustment is applied within each metric and comparison scope. Cliff's "
            "delta is reported as a distributional effect-size descriptor.",
            "",
        ]
    )

    key_within = [
        r for r in within
        if r["metric"] in {"norm_recall_at_k", "link_resolution_rate", "norm_citation_validity"}
        and (
            r.get("comparison_group") in {"optimized", "no_case_evidence", "no_case_norm_linker"}
        )
    ]
    if key_within:
        lines.extend(
            [
                "### Within-dataset key comparisons",
                "",
                "| Dataset | Metric | Reference | Comparator | n | Mean delta | p | Holm p | Cliff's delta |",
                "|---|---|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for r in key_within:
            lines.append(
                "| {dataset} | `{metric}` | {ref} | {comp} | {n} | {delta} | {p} | {hp} | {cd} |".format(
                    dataset=r["dataset"],
                    metric=r["metric"],
                    ref=r["reference_group"],
                    comp=r["comparison_group"],
                    n=r["n_pairs"],
                    delta=fmt(r["mean_delta_reference_minus_comparison"]),
                    p=fmt(r["p_value"], 4),
                    hp=fmt(r["p_value_holm"], 4),
                    cd=fmt(r["cliffs_delta"]),
                )
            )
        lines.append("")

    if between:
        key_between = [
            r for r in between
            if r["metric"] in {"norm_recall_at_k", "link_resolution_rate", "norm_citation_validity"}
            and r.get("group") in {"proposed", "full"}
        ]
        if key_between:
            lines.extend(
                [
                    "### Cross-backend key comparisons",
                    "",
                    "| Family | Group | Metric | Left | Right | n | Mean delta | p | Holm p |",
                    "|---|---|---|---|---|---:|---:|---:|---:|",
                ]
            )
            for r in key_between:
                lines.append(
                    "| {family} | {group} | `{metric}` | {left} | {right} | {n} | {delta} | {p} | {hp} |".format(
                        family=r["family"],
                        group=r["group"],
                        metric=r["metric"],
                        left=r["left_dataset"],
                        right=r["right_dataset"],
                        n=r["n_pairs"],
                        delta=fmt(r["mean_delta_left_minus_right"]),
                        p=fmt(r["p_value"], 4),
                        hp=fmt(r["p_value_holm"], 4),
                    )
                )
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def safe_slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", action="append", required=True, help="LABEL=path/to/metrics.csv")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--markdown", type=Path, help="optional report path; defaults to output-dir/report.md")
    ap.add_argument("--metrics", nargs="+", default=DEFAULT_METRICS)
    ap.add_argument("--bootstrap-iterations", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20260617)
    args = ap.parse_args(argv)

    inputs = [load_input(spec) for spec in args.input]
    metrics = available_metrics(inputs, args.metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summaries = summarize_groups(inputs, metrics, iterations=args.bootstrap_iterations, seed=args.seed)
    within = within_dataset_comparisons(inputs, metrics)
    between = between_dataset_comparisons(inputs, metrics)

    summary_path = args.output_dir / "group_summary.csv"
    within_path = args.output_dir / "within_dataset_comparisons.csv"
    between_path = args.output_dir / "between_dataset_comparisons.csv"
    json_path = args.output_dir / "analysis.json"
    report_path = args.markdown or (args.output_dir / "report.md")

    write_csv(summary_path, summaries)
    write_csv(within_path, within)
    write_csv(between_path, between)
    payload = {
        "inputs": [
            {"label": inp.label, "path": str(inp.path), "family": inp.family, "group_col": inp.group_col}
            for inp in inputs
        ],
        "metrics": metrics,
        "bootstrap_iterations": args.bootstrap_iterations,
        "seed": args.seed,
        "group_summary": summaries,
        "within_dataset_comparisons": within,
        "between_dataset_comparisons": between,
    }
    json_path.write_text(
        json.dumps(clean_float_for_json(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown_report(report_path, inputs, metrics, summaries, within, between)

    print(f"group_summary_csv: {summary_path}")
    print(f"within_comparisons_csv: {within_path}")
    print(f"between_comparisons_csv: {between_path}")
    print(f"analysis_json: {json_path}")
    print(f"report_md: {report_path}")
    print(f"metrics: {', '.join(metrics)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
