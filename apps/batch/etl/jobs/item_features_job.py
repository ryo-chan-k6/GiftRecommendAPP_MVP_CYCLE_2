from __future__ import annotations

import argparse
import math
import os
import uuid
from typing import Optional

from core.logging import get_logger
from repos.apl.item_features_repo import ItemFeaturesRepo
from repos.db import db_connection
from services.context import build_context

JOB_ID = "JOB-F-01"
FEATURES_VERSION = 1


def run_job(
    *,
    env: str,
    database_url: str,
    run_id: str | None = None,
    dry_run: bool = False,
) -> dict:
    job_run_id = run_id or uuid.uuid4().hex
    ctx = build_context(job_id=JOB_ID, env=env, run_id=job_run_id, dry_run=dry_run)
    logger = get_logger(job_id=JOB_ID, run_id=ctx.run_id)

    since = ctx.job_start_at.replace(hour=0, minute=0, second=0, microsecond=0)

    with db_connection(database_url=database_url) as conn:
        repo = ItemFeaturesRepo(conn=conn)
        targets = repo.fetch_feature_rows(since=since)

        total_targets = len(targets)
        upsert_inserted = 0
        upsert_updated = 0
        skipped_no_diff = 0
        failure_count = 0

        for row in targets:
            try:
                price_log = _compute_log_value(row.price_yen)
                review_count_log = _compute_log_value(row.review_count)
                popularity_score = _compute_popularity_score(
                    review_average=row.review_average, review_count=row.review_count
                )

                if ctx.dry_run:
                    skipped_no_diff += 1
                    continue

                result = repo.upsert_features(
                    item_id=row.item_id,
                    price_yen=row.price_yen,
                    price_log=price_log,
                    point_rate=row.point_rate,
                    availability=row.availability,
                    review_average=row.review_average,
                    review_count=row.review_count,
                    review_count_log=review_count_log,
                    rank=row.rank,
                    popularity_score=popularity_score,
                    rakuten_genre_id=row.rakuten_genre_id,
                    tag_ids=row.tag_ids,
                    features_version=FEATURES_VERSION,
                )
                if result == "inserted":
                    upsert_inserted += 1
                elif result == "updated":
                    upsert_updated += 1
                else:
                    skipped_no_diff += 1
            except Exception:
                failure_count += 1
                logger.exception(
                    "item features build failed: item_id=%s", row.item_id
                )

        failure_rate = failure_count / total_targets if total_targets else 0
        summary = {
            "total_targets": total_targets,
            "upsert_inserted": upsert_inserted,
            "upsert_updated": upsert_updated,
            "skipped_no_diff": skipped_no_diff,
            "failure_count": failure_count,
            "failure_rate": failure_rate,
        }
        logger.info("item features build summary: %s", summary)
        _write_step_summary(summary)
        return summary


def _compute_log_value(value: Optional[int]) -> Optional[float]:
    if value is None:
        return None
    if value <= 0:
        return None
    return math.log(value)


def _compute_popularity_score(
    *, review_average: Optional[float], review_count: Optional[int]
) -> Optional[float]:
    if review_count is None:
        return None
    if review_count <= 0:
        return 0.0
    quality = 0.0
    if review_average is not None:
        quality = max(0.0, min(float(review_average) / 5.0, 1.0))
    return quality * math.log1p(review_count)


def _write_step_summary(summary: dict) -> None:
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = [
        "## JOB-F-01 Item Features Build",
        "",
        f"- total_targets: {summary.get('total_targets')}",
        f"- upsert_inserted: {summary.get('upsert_inserted')}",
        f"- upsert_updated: {summary.get('upsert_updated')}",
        f"- skipped_no_diff: {summary.get('skipped_no_diff')}",
        f"- failure_count: {summary.get('failure_count')}",
        f"- failure_rate: {summary.get('failure_rate')}",
        "",
    ]
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="JOB-F-01 Item Features Build")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id", dest="run_id", default=None)
    args = parser.parse_args()

    env = os.getenv("ENV")
    database_url = os.getenv("DATABASE_URL")
    if not env:
        raise ValueError("Missing required env var: ENV")
    if not database_url:
        raise ValueError("Missing required env var: DATABASE_URL")

    run_job(env=env, database_url=database_url, run_id=args.run_id, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
