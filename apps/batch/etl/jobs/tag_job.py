from __future__ import annotations

import argparse
import uuid
from typing import Any, Mapping

from clients.rakuten_client import RakutenClient, RakutenClientConfig
from core.config import AppConfig, load_config
from core.logging import get_logger
from core.raw_store import RawStore
from repos.apl.item_tag_repo import ItemTagRepo
from repos.apl.tag_repo import TagRepo
from repos.db import db_connection
from repos.staging_repo import StagingRepo
from services import policy
from services.context import JobContext, build_context
from services.etl_service import EtlService

JOB_ID = "JOB-T-01"


def run_job(*, config: AppConfig, run_id: str | None = None, dry_run: bool = False) -> dict:
    job_run_id = run_id or uuid.uuid4().hex
    ctx = build_context(job_id=JOB_ID, env=config.env, run_id=job_run_id, dry_run=dry_run)
    logger = get_logger(job_id=JOB_ID, run_id=ctx.run_id)

    with db_connection(database_url=config.database_url) as conn:
        staging_repo = StagingRepo(conn=conn)
        item_tag_repo = ItemTagRepo(conn=conn)
        tag_repo = TagRepo(conn=conn)
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
            return policy.targets_tag_ids_from_today_items(
                job_ctx, staging_repo=staging_repo, item_tag_repo=item_tag_repo
            )

        def fetcher(target: str) -> Mapping[str, Any]:
            return client.fetch_tag(tag_id=int(target))

        def applier(normalized: Mapping[str, Any], _job_ctx: JobContext, _target: str) -> None:
            tag_repo.upsert_tag_group(normalized_tag=normalized)
            tag_repo.upsert_tag(normalized_tag=normalized)

        return service.run_entity_etl(
            ctx=ctx,
            source="rakuten",
            entity="tag",
            target_provider=target_provider,
            fetcher=fetcher,
            applier=applier,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="JOB-T-01 Tag ETL")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id", dest="run_id", default=None)
    args = parser.parse_args()

    config = load_config()
    run_job(config=config, run_id=args.run_id, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
