from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.logging import get_logger  # noqa: E402


@pytest.mark.unit
def test_get_logger_returns_adapter_with_formatter_context() -> None:
    job_id = "job-test-logging"
    logger_name = f"etl.{job_id}"
    base_logger = logging.getLogger(logger_name)
    base_logger.handlers.clear()

    adapter = get_logger(job_id=job_id, run_id="run-1")

    assert isinstance(adapter, logging.LoggerAdapter)
    assert len(adapter.logger.handlers) == 1
    formatter = adapter.logger.handlers[0].formatter
    assert formatter is not None
    assert "job_id" in formatter._fmt
    assert "run_id" in formatter._fmt


@pytest.mark.unit
def test_get_logger_does_not_duplicate_handlers() -> None:
    job_id = "job-test-logging-dup"
    logger_name = f"etl.{job_id}"
    base_logger = logging.getLogger(logger_name)
    base_logger.handlers.clear()

    adapter = get_logger(job_id=job_id, run_id="run-1")
    _ = get_logger(job_id=job_id, run_id="run-2")

    assert len(adapter.logger.handlers) == 1
