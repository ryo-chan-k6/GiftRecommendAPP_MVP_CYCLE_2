from __future__ import annotations

import argparse
import os
import uuid
from pathlib import Path
from typing import Any

from core.logging import get_logger
from repos.db import db_connection, transaction

JOB_ID = "JOB-A-01"


def run_job(*, database_url: str, run_id: str | None = None, dry_run: bool = False) -> dict:
    job_run_id = run_id or uuid.uuid4().hex
    logger = get_logger(job_id=JOB_ID, run_id=job_run_id)

    sql = _load_sql()
    with db_connection(database_url=database_url) as conn:
        cur = conn.cursor()
        try:
            target_tables = ["apl.item", "apl.genre", "apl.shop"]
            table_counts: dict[str, int] = {}
            for table in target_tables:
                table_counts[table] = _count_table(cur, table)
                logger.info(
                    "is_active check target: table=%s count=%s",
                    table,
                    table_counts[table],
                )
        finally:
            cur.close()

        if dry_run:
            logger.info(
                "is_active update summary: updated_table=apl.item updated_count=0 dry_run=true"
            )
            return {"updated": 0}

        with transaction(conn):
            cur = conn.cursor()
            try:
                cur.execute(sql)
                updated = cur.rowcount
            finally:
                cur.close()

    logger.info(
        "is_active update summary: updated_table=apl.item updated_count=%s dry_run=false",
        updated,
    )
    return {"updated": updated}


def _load_sql() -> str:
    sql_path = Path(__file__).resolve().parents[1] / "sql" / "common" / "item_is_active_update.sql"
    return sql_path.read_text(encoding="utf-8")


def _count_table(cur, table: str) -> int:
    cur.execute(f"select count(*) from {table}")
    row = cur.fetchone()
    return int(row[0]) if row else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="JOB-A-01 Item is_active update")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id", dest="run_id", default=None)
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("Missing required env var: DATABASE_URL")
    run_job(database_url=database_url, run_id=args.run_id, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
