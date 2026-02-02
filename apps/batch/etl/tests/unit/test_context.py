from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from services.context import build_context  # noqa: E402


@pytest.mark.unit
def test_build_context_sets_job_start_at_and_defaults() -> None:
    ctx = build_context(job_id="job-r-01", env="dev", run_id="run-1")

    assert ctx.job_id == "job-r-01"
    assert ctx.env == "dev"
    assert ctx.run_id == "run-1"
    assert ctx.job_start_at.tzinfo is not None
    assert ctx.dry_run is False


@pytest.mark.unit
def test_build_context_sets_dry_run_when_enabled() -> None:
    ctx = build_context(job_id="job-i-01", env="prod", run_id="run-2", dry_run=True)

    assert ctx.dry_run is True
