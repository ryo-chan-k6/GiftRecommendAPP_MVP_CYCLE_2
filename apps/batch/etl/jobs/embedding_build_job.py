from __future__ import annotations

import argparse
import os
import uuid

from clients.openai_client import OpenAIClient, OpenAIClientConfig
from core.logging import get_logger
from repos.apl.item_embedding_repo import ItemEmbeddingRepo
from repos.db import db_connection
from services.context import build_context

JOB_ID = "JOB-E-02"


def run_job(
    *,
    env: str,
    database_url: str,
    api_key: str,
    model: str,
    timeout_sec: float,
    max_retries: int,
    backoff_base_sec: float,
    run_id: str | None = None,
    dry_run: bool = False,
) -> dict:
    job_run_id = run_id or uuid.uuid4().hex
    ctx = build_context(job_id=JOB_ID, env=env, run_id=job_run_id, dry_run=dry_run)
    logger = get_logger(job_id=JOB_ID, run_id=ctx.run_id)

    client = OpenAIClient(
        config=OpenAIClientConfig(
            api_key=api_key,
            model=model,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
            backoff_base_sec=backoff_base_sec,
        )
    )

    with db_connection(database_url=database_url) as conn:
        repo = ItemEmbeddingRepo(conn=conn)
        targets = repo.fetch_diff_sources(model=model)
        total_targets = len(targets)
        upsert_inserted = 0
        upsert_updated = 0
        skipped_no_diff = 0
        failure_count = 0

        for row in targets:
            try:
                if ctx.dry_run:
                    skipped_no_diff += 1
                    continue
                embedding = client.embed(source_text=row.source_text)
                result = repo.upsert_embedding(
                    item_id=row.item_id,
                    model=model,
                    embedding=embedding,
                    source_hash=row.source_hash,
                )
                if result == "inserted":
                    upsert_inserted += 1
                elif result == "updated":
                    upsert_updated += 1
                else:
                    skipped_no_diff += 1
            except Exception:
                failure_count += 1
                logger.exception("embedding build failed: item_id=%s", row.item_id)

        failure_rate = failure_count / total_targets if total_targets else 0
        summary = {
            "total_targets": total_targets,
            "upsert_inserted": upsert_inserted,
            "upsert_updated": upsert_updated,
            "skipped_no_diff": skipped_no_diff,
            "failure_count": failure_count,
            "failure_rate": failure_rate,
        }
        logger.info("embedding build summary: %s", summary)
        return summary


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid float env var: {name}") from exc


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid int env var: {name}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="JOB-E-02 Embedding Build")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id", dest="run_id", default=None)
    args = parser.parse_args()

    env = _require("ENV")
    database_url = _require("DATABASE_URL")
    api_key = _require("OPENAI_API_KEY")
    model = os.getenv("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small"
    timeout_sec = _get_float("OPENAI_TIMEOUT_SEC", 30.0)
    max_retries = _get_int("OPENAI_MAX_RETRIES", 5)
    backoff_base_sec = _get_float("OPENAI_BACKOFF_BASE_SEC", 1.0)

    run_job(
        env=env,
        database_url=database_url,
        api_key=api_key,
        model=model,
        timeout_sec=timeout_sec,
        max_retries=max_retries,
        backoff_base_sec=backoff_base_sec,
        run_id=args.run_id,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
