import csv
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_metrics(path: Path) -> None:
    rows = []
    for task_num in range(1, 5):
        task_id = f"task-{task_num:03d}"
        rows.append(
            {
                "variant": "optimized",
                "task_id": task_id,
                "theme": "脚手架",
                "tier": "S",
                "grounding_rate": 1.0,
                "norm_citation_validity": 0.1,
                "hazard_coverage": 0.25,
                "case_relevance": 0.5,
                "norm_recall_at_k": 0.25,
                "case_recall_at_k": 0.5,
                "link_resolution_rate": 0.0,
                "elapsed_seconds": 10.0 + task_num,
            }
        )
        rows.append(
            {
                "variant": "proposed",
                "task_id": task_id,
                "theme": "脚手架",
                "tier": "S",
                "grounding_rate": 1.0,
                "norm_citation_validity": 0.2,
                "hazard_coverage": 0.5,
                "case_relevance": 0.75,
                "norm_recall_at_k": 0.75,
                "case_recall_at_k": 0.75,
                "link_resolution_rate": 0.5,
                "elapsed_seconds": 20.0 + task_num,
            }
        )
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_metric_uncertainty_cli_outputs_stable_fields(tmp_path):
    metrics_csv = tmp_path / "metrics.csv"
    out_dir = tmp_path / "uncertainty"
    _write_metrics(metrics_csv)

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "analyze_metric_uncertainty.py"),
            "--input",
            f"fixture={metrics_csv}",
            "--output-dir",
            str(out_dir),
            "--bootstrap-iterations",
            "200",
            "--metrics",
            "norm_recall_at_k",
            "link_resolution_rate",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    for name in (
        "group_summary.csv",
        "within_dataset_comparisons.csv",
        "between_dataset_comparisons.csv",
        "analysis.json",
        "report.md",
    ):
        assert (out_dir / name).exists(), f"missing {name}"

    analysis = json.loads((out_dir / "analysis.json").read_text(encoding="utf-8"))
    summary_row = analysis["group_summary"][0]
    for key in ("dataset", "family", "group", "metric", "n", "mean", "ci95_low", "ci95_high"):
        assert key in summary_row

    comparison = analysis["within_dataset_comparisons"][0]
    for key in ("reference_group", "comparison_group", "p_value", "p_value_holm", "cliffs_delta"):
        assert key in comparison
