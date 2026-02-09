from __future__ import annotations

import argparse
import uuid
from typing import Any, Mapping

from clients.rakuten_client import RakutenClient, RakutenClientConfig
from core.config import AppConfig, load_config
from core.logging import get_logger
from core.raw_store import RawStore
from repos.apl.rank_repo import RankRepo
from repos.apl.target_genre_config_repo import TargetGenreConfigRepo
from repos.db import db_connection
from repos.staging_repo import StagingRepo
from services import policy
from services.context import JobContext, build_context
from services.etl_service import EtlService

JOB_ID = "JOB-R-01"


def run_job(*, config: AppConfig, run_id: str | None = None, dry_run: bool = False) -> dict:
    job_run_id = run_id or uuid.uuid4().hex
    ctx = build_context(job_id=JOB_ID, env=config.env, run_id=job_run_id, dry_run=dry_run)
    logger = get_logger(job_id=JOB_ID, run_id=ctx.run_id)

    with db_connection(database_url=config.database_url) as conn:
        target_genre_config_repo = TargetGenreConfigRepo(conn=conn)
        staging_repo = StagingRepo(conn=conn)
        rank_repo = RankRepo(conn=conn)
        raw_store = RawStore(region=config.aws_region)
        client = RakutenClient(
            config=RakutenClientConfig(
                application_id=config.rakuten_app_id,
                affiliate_id=config.rakuten_affiliate_id,
            )
        )
        service = EtlService(
            staging_repo=staging_repo,
            raw_store=raw_store,
            s3_bucket=config.s3_bucket_raw,
            logger=logger,
        )

        def target_provider(job_ctx: JobContext):
            return policy.targets_ranking_genre_ids(
                job_ctx, target_genre_config_repo=target_genre_config_repo
            )

        def fetcher(target: str) -> Mapping[str, Any]:
            return client.fetch_ranking(genre_id=int(target))

        def applier(normalized: Mapping[str, Any], job_ctx: JobContext, target: str) -> None:
            items = normalized.get("items")
            if not isinstance(items, list):
                items = normalized.get("Items")
            if not isinstance(items, list):
                items = []
            title = normalized.get("title")
            last_build_date = normalized.get("lastBuildDate")
            enriched = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                entry = item.get("Item") if "Item" in item else item
                if not isinstance(entry, dict):
                    continue
                entry = dict(entry)
                if title is not None and "title" not in entry:
                    entry["title"] = title
                if last_build_date is not None and "lastBuildDate" not in entry:
                    entry["lastBuildDate"] = last_build_date
                enriched.append(entry)
            if not enriched:
                return
            rank_repo.insert_rank_snapshot(
                run_id=job_ctx.run_id,
                genre_id=int(target),
                ranking_items=enriched,
                fetched_at=job_ctx.job_start_at,
            )

        return service.run_entity_etl(
            ctx=ctx,
            source="rakuten",
            entity="ranking",
            target_provider=target_provider,
            fetcher=fetcher,
            applier=applier,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="JOB-R-01 Ranking ETL")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id", dest="run_id", default=None)
    args = parser.parse_args()

    config = load_config()
    run_job(config=config, run_id=args.run_id, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
