from __future__ import annotations

import argparse
import uuid
from typing import Any, Mapping, Sequence

from clients.rakuten_client import RakutenClient, RakutenClientConfig
from core.config import AppConfig, load_config
from core.logging import get_logger
from core.raw_store import RawStore
from repos.apl.item_repo import ItemRepo
from repos.apl.item_tag_repo import ItemTagRepo
from repos.apl.rank_repo import RankRepo
from repos.db import db_connection
from repos.staging_repo import StagingRepo
from services import policy
from services.context import JobContext, build_context
from services.etl_service import EtlService

JOB_ID = "JOB-I-01"


def run_job(*, config: AppConfig, run_id: str | None = None, dry_run: bool = False) -> dict:
    job_run_id = run_id or uuid.uuid4().hex
    ctx = build_context(job_id=JOB_ID, env=config.env, run_id=job_run_id, dry_run=dry_run)
    logger = get_logger(job_id=JOB_ID, run_id=ctx.run_id)

    with db_connection(database_url=config.database_url) as conn:
        rank_repo = RankRepo(conn=conn)
        staging_repo = StagingRepo(conn=conn)
        item_repo = ItemRepo(conn=conn)
        item_tag_repo = ItemTagRepo(conn=conn)
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
            targets = list(policy.targets_item_codes(job_ctx, rank_snapshot_repo=rank_repo))
            logger.info(
                "item targets from ranking: count=%s since=%s",
                len(targets),
                job_ctx.job_start_at,
            )
            if targets:
                logger.debug("item target sample: %s", targets[:5])
            return targets

        def fetcher(target: str) -> Mapping[str, Any]:
            return client.fetch_item(item_code=target)

        def applier(normalized: Mapping[str, Any], job_ctx: JobContext, target: str) -> None:
            item_payload = _extract_item_payload(normalized)
            if not item_payload:
                return
            item_repo.upsert_shop(normalized_item=item_payload)
            item_id = item_repo.upsert_item(normalized_item=item_payload)
            item_repo.sync_item_images(item_id=item_id, normalized_item=item_payload)
            item_repo.insert_market_snapshot(
                item_id=item_id, collected_at=job_ctx.job_start_at, normalized_item=item_payload
            )
            item_repo.insert_review_snapshot(
                item_id=item_id, collected_at=job_ctx.job_start_at, normalized_item=item_payload
            )
            tag_ids = _extract_tag_ids(item_payload)
            item_tag_repo.sync_item_tags(item_id=item_id, rakuten_tag_ids=tag_ids)

        return service.run_entity_etl(
            ctx=ctx,
            source="rakuten",
            entity="item",
            target_provider=target_provider,
            fetcher=fetcher,
            applier=applier,
        )


def _extract_item_payload(normalized: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if "itemCode" in normalized:
        return normalized
    items = normalized.get("items")
    if not isinstance(items, list):
        items = normalized.get("Items")
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, Mapping):
            payload = first.get("Item") if "Item" in first else first
            if isinstance(payload, Mapping):
                return payload
    return None


def _extract_tag_ids(item_payload: Mapping[str, Any]) -> Sequence[int]:
    tag_ids = item_payload.get("tagIds") or []
    if not isinstance(tag_ids, list):
        return []
    extracted: list[int] = []
    for entry in tag_ids:
        if isinstance(entry, int):
            extracted.append(entry)
        elif isinstance(entry, str) and entry.isdigit():
            extracted.append(int(entry))
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser(description="JOB-I-01 Item ETL")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id", dest="run_id", default=None)
    args = parser.parse_args()

    config = load_config()
    run_job(config=config, run_id=args.run_id, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
