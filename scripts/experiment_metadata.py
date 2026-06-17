"""Small metadata helpers for benchmark experiment directories."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


SAFE_ENV_KEYS = [
    "LLM_MODEL",
    "OPENAI_BASE_URL",
    "LLM_MAX_TOKENS",
    "LLM_DISABLE_THINKING",
    "LLM_USE_JSON_MODE",
    "LLM_STRUCTURED_MODE",
    "AGENT_INTERACTIVE_FAST",
    "TRAINING_MAX_LLM_CALLS",
    "RETRIEVAL_BACKEND",
    "RETRIEVAL_MODE",
    "RETRIEVAL_TOP_K",
    "QUERY_REWRITE_ENABLED",
    "ABLATION_CASE_EVIDENCE",
    "ABLATION_CASE_NORM_LINKER",
    "ABLATION_DETERMINISTIC_GROUND",
    "ABLATION_ARBITRATION",
]


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit(project_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "git_unavailable"


def safe_base_url_domain(base_url: str) -> str:
    parsed = urlparse(base_url)
    return parsed.netloc or parsed.path.split("/")[0]


def build_metadata(
    *,
    project_root: Path,
    command: list[str],
    tasks_path: Path,
    script_path: Path,
    run_kind: str,
    variants: list[str] | None = None,
    ablations: list[str] | None = None,
) -> dict:
    base_url = os.getenv("OPENAI_BASE_URL", "")
    safe_env = {
        key: (safe_base_url_domain(base_url) if key == "OPENAI_BASE_URL" else os.getenv(key, ""))
        for key in SAFE_ENV_KEYS
        if os.getenv(key) is not None
    }
    return {
        "run_kind": run_kind,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "model": os.getenv("LLM_MODEL", ""),
        "base_url_domain": safe_base_url_domain(base_url),
        "variants": variants or [],
        "ablations": ablations or [],
        "tasks_path": str(tasks_path),
        "tasks_sha256": sha256_file(tasks_path),
        "script_path": str(script_path),
        "script_sha256": sha256_file(script_path),
        "git_commit": git_commit(project_root),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "safe_environment": safe_env,
    }


def write_metadata(output_dir: Path, metadata: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
