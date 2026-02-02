from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class JobContext:
    job_id: str
    env: str
    run_id: str
    job_start_at: datetime
    dry_run: bool = False


def build_context(*, job_id: str, env: str, run_id: str, dry_run: bool = False) -> JobContext:
    return JobContext(
        job_id=job_id,
        env=env,
        run_id=run_id,
        job_start_at=datetime.now(timezone.utc),
        dry_run=dry_run,
    )
