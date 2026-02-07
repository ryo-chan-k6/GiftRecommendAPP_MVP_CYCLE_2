from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from typing import Any

from core.config import AppConfig, load_config
from core.logging import get_logger
from repos.db import db_connection, transaction

JOB_ID = "JOB-A-01"


def run_job(*, config: AppConfig, run_id: str | None = None, dry_run: bool = False) -> dict:
    job_run_id = run_id or uuid.uuid4().hex
    logger = get_logger(job_id=JOB_ID, run_id=job_run_id)

    if dry_run:
        logger.info("dry_run enabled: skip is_active update")
        return {"updated": 0}

    sql = _load_sql()
    with db_connection(database_url=config.database_url) as conn:
        with transaction(conn):
            cur = conn.cursor()
            try:
                cur.execute(sql)
                updated = cur.rowcount
            finally:
                cur.close()

    return {"updated": updated}


def _load_sql() -> str:
    sql_path = Path(__file__).resolve().parents[1] / "sql" / "common" / "item_is_active_update.sql"
    return sql_path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="JOB-A-01 Item is_active update")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id", dest="run_id", default=None)
    args = parser.parse_args()

    config = load_config()
    run_job(config=config, run_id=args.run_id, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
