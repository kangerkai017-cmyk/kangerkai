"""Scaffolding tests for the 5 ablation switches.

Verifies env switches are read and the relevant flag in src.config reflects.
Does not exercise full graph runs (those need LLM); dry-run path of
run_ablation is tested via subprocess.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def restore_env():
    saved = {k: os.environ.get(k) for k in (
        "ABLATION_CASE_EVIDENCE",
        "ABLATION_CASE_NORM_LINKER",
        "ABLATION_DETERMINISTIC_GROUND",
        "ABLATION_ARBITRATION",
        "QUERY_REWRITE_ENABLED",
    )}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    # reload config back to baseline state
    import src.config
    importlib.reload(src.config)


def test_ablation_flags_default_true(restore_env):
    for k in (
        "ABLATION_CASE_EVIDENCE",
        "ABLATION_CASE_NORM_LINKER",
        "ABLATION_DETERMINISTIC_GROUND",
        "ABLATION_ARBITRATION",
        "QUERY_REWRITE_ENABLED",
    ):
        os.environ.pop(k, None)
    import src.config
    importlib.reload(src.config)
    assert src.config.ABLATION_CASE_EVIDENCE is True
    assert src.config.ABLATION_CASE_NORM_LINKER is True
    assert src.config.ABLATION_DETERMINISTIC_GROUND is True
    assert src.config.ABLATION_ARBITRATION is True
    assert src.config.QUERY_REWRITE_ENABLED is True


@pytest.mark.parametrize("flag", [
    "ABLATION_CASE_EVIDENCE",
    "ABLATION_CASE_NORM_LINKER",
    "ABLATION_DETERMINISTIC_GROUND",
    "ABLATION_ARBITRATION",
])
def test_ablation_flag_off(flag, restore_env):
    os.environ[flag] = "false"
    import src.config
    importlib.reload(src.config)
    assert getattr(src.config, flag) is False


def test_run_ablation_cli_dry_run():
    """Smoke test that the CLI runner imports + finds a task + iterates ablations."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "run_ablation.py"),
         "--task-id", "task-起重吊装-009", "--dry-run"],
        capture_output=True, text=True, timeout=60,
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "", "NO_PROXY": "localhost,127.0.0.1"},
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}"
    out = result.stdout
    assert "Ablation summary" in out
    for ab in ("full", "no_case_evidence", "no_case_norm_linker",
               "no_deterministic_ground", "no_arbitration", "no_query_rewrite"):
        assert ab in out, f"missing {ab} in summary"
