from __future__ import annotations

import logging
from typing import Optional


def get_logger(*, job_id: str, run_id: str, level: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(f"etl.{job_id}")
    if logger.handlers:
        return logger

    log_level = (level or "INFO").upper()
    logger.setLevel(log_level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s job_id=%(job_id)s run_id=%(run_id)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    logger = logging.LoggerAdapter(logger, {"job_id": job_id, "run_id": run_id})
    return logger
