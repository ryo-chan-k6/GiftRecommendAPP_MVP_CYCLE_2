from __future__ import annotations

import argparse
import os
import re
import uuid
from datetime import datetime
from hashlib import sha256
from typing import Iterable

from core.logging import get_logger
from repos.apl.item_embedding_source_repo import ItemEmbeddingSourceRepo, ItemFeatureRow
from repos.db import db_connection
from services.context import JobContext, build_context

JOB_ID = "JOB-E-01"
SOURCE_VERSION = 1


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

    with db_connection(database_url=database_url) as conn:
        repo = ItemEmbeddingSourceRepo(conn=conn)
        since = ctx.job_start_at.replace(hour=0, minute=0, second=0, microsecond=0)
        targets = repo.fetch_feature_rows(since=since)
        total_targets = len(targets)
        upsert_inserted = 0
        upsert_updated = 0
        skipped_no_diff = 0
        failure_count = 0

        for row in targets:
            try:
                source_text = _build_source_text(row)
                source_hash = _compute_source_hash(source_text)
                if len(source_text) < 20:
                    logger.warning(
                        "short source_text detected: item_id=%s length=%s",
                        row.item_id,
                        len(source_text),
                    )
                if ctx.dry_run:
                    skipped_no_diff += 1
                    continue
                result = repo.upsert_source(
                    item_id=row.item_id,
                    source_version=SOURCE_VERSION,
                    source_text=source_text,
                    source_hash=source_hash,
                )
                if result == "inserted":
                    upsert_inserted += 1
                elif result == "updated":
                    upsert_updated += 1
                else:
                    skipped_no_diff += 1
            except Exception:
                failure_count += 1
                logger.exception("embedding source build failed: item_id=%s", row.item_id)

        failure_rate = failure_count / total_targets if total_targets else 0
        summary = {
            "total_targets": total_targets,
            "upsert_inserted": upsert_inserted,
            "upsert_updated": upsert_updated,
            "skipped_no_diff": skipped_no_diff,
            "failure_count": failure_count,
            "failure_rate": failure_rate,
        }
        logger.info("embedding source build summary: %s", summary)
        return summary


def _build_source_text(row: ItemFeatureRow) -> str:
    item_name = _normalize_text(row.item_name)
    catchcopy = _normalize_text(row.catchcopy)
    caption = _normalize_text(row.item_caption)
    caption = _trim_text(caption, 2000)
    genre_name = _normalize_text(row.genre_name)
    tag_names = _normalize_tags(row.tag_names, limit=30)
    price_yen = _normalize_price(row.item_price)

    header_lines = _collect_lines(
        [
            ("商品名", item_name),
            ("キャッチコピー", catchcopy),
            ("商品説明", caption),
        ]
    )
    detail_lines = _collect_lines(
        [
            ("ジャンル", genre_name),
            ("タグ", ", ".join(tag_names) if tag_names else ""),
            ("価格", f"{price_yen}円" if price_yen is not None else ""),
        ]
    )

    lines: list[str] = []
    if header_lines:
        lines.extend(header_lines)
    if header_lines and detail_lines:
        lines.append("")
    if detail_lines:
        lines.extend(detail_lines)
    return "\n".join(lines)


def _collect_lines(entries: Iterable[tuple[str, str]]) -> list[str]:
    lines: list[str] = []
    for label, value in entries:
        if value:
            lines.append(f"{label}: {value}")
    return lines


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<[^>]+>", "", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join([line for line in lines if line])


def _trim_text(value: str, limit: int) -> str:
    if not value:
        return ""
    return value[:limit]


def _normalize_tags(values: Iterable[object], *, limit: int) -> list[str]:
    tags: list[str] = []
    for value in values:
        normalized = _normalize_text(value)
        if normalized:
            tags.append(normalized)
        if len(tags) >= limit:
            break
    return tags


def _normalize_price(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _compute_source_hash(source_text: str) -> str:
    return sha256(source_text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="JOB-E-01 Embedding Source Build")
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
