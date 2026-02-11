from __future__ import annotations

import logging
from typing import Any, Iterable, Mapping, Protocol

from core.hasher import compute_content_hash
from core.normalize import normalize
from core.raw_store import RawPutResult
from repos.staging_repo import StagingRow
from services.context import JobContext

Target = str


class Fetcher(Protocol):
    def __call__(self, target: Target) -> Mapping[str, Any]: ...


class Applier(Protocol):
    def __call__(self, normalized: Mapping[str, Any], ctx: JobContext, target: Target) -> None: ...


class TargetProvider(Protocol):
    def __call__(self, ctx: JobContext) -> Iterable[Target]: ...


class StagingRepo(Protocol):
    def exists_hash(self, *, source: str, entity: str, source_id: str, content_hash: str) -> bool: ...
    def batch_upsert(self, *, rows: Iterable[StagingRow]) -> int: ...


class RawStore(Protocol):
    def build_key(self, *, source: str, entity: str, source_id: str, content_hash: str) -> str: ...
    def put_json(self, *, bucket: str, s3_key: str, body: Mapping[str, Any]) -> RawPutResult: ...


class EtlService:
    def __init__(
        self,
        *,
        staging_repo: StagingRepo,
        raw_store: RawStore,
        s3_bucket: str,
        logger: logging.Logger | None = None,
    ) -> None:
        self._staging_repo = staging_repo
        self._raw_store = raw_store
        self._s3_bucket = s3_bucket
        self._logger = logger or logging.getLogger(__name__)

    def run_entity_etl(
        self,
        *,
        ctx: JobContext,
        source: str,
        entity: str,
        target_provider: TargetProvider,
        fetcher: Fetcher,
        applier: Applier,
        apply_version: int | None = None,
    ) -> dict:
        targets = list(target_provider(ctx))
        total_targets = len(targets)
        success_count = 0
        failure_count = 0
        self._logger.info(
            "etl start: source=%s entity=%s total_targets=%s dry_run=%s",
            source,
            entity,
            total_targets,
            ctx.dry_run,
        )

        for target in targets:
            try:
                self._logger.info("etl target start: target=%s", target)
                raw = fetcher(target)
                normalized = normalize(entity, raw)
                content_hash = compute_content_hash(normalized)
                self._logger.info(
                    "etl normalized: target=%s hash=%s", target, content_hash
                )
                status = self._staging_repo.get_latest_status(
                    source=source, entity=entity, source_id=str(target)
                )
                if status and status.content_hash == content_hash:
                    if apply_version is not None and status.applied_version != apply_version:
                        if ctx.dry_run:
                            self._logger.info(
                                "etl skip: target=%s reason=dry_run", target
                            )
                            success_count += 1
                            continue
                        self._logger.info(
                            "etl reapply: target=%s reason=applied_version_mismatch", target
                        )
                        applier(normalized, ctx, target)
                        self._staging_repo.mark_applied(
                            source=source,
                            entity=entity,
                            source_id=str(target),
                            content_hash=content_hash,
                            applied_version=apply_version,
                        )
                    self._logger.info(
                        "etl skip: target=%s reason=exists_hash", target
                    )
                    success_count += 1
                    continue

                if ctx.dry_run:
                    self._logger.info("etl skip: target=%s reason=dry_run", target)
                    success_count += 1
                    continue

                s3_key = self._raw_store.build_key(
                    source=source,
                    entity=entity,
                    source_id=str(target),
                    content_hash=content_hash,
                )
                self._logger.info("etl raw store: target=%s s3_key=%s", target, s3_key)
                put_result = self._raw_store.put_json(
                    bucket=self._s3_bucket, s3_key=s3_key, body=normalized
                )
                row = StagingRow(
                    source=source,
                    entity=entity,
                    source_id=str(target),
                    content_hash=content_hash,
                    s3_key=put_result.s3_key,
                    etag=put_result.etag,
                    saved_at=put_result.saved_at,
                )
                upserted = self._staging_repo.batch_upsert(rows=[row])
                self._logger.info(
                    "etl staging upsert: target=%s rows=%s", target, upserted
                )
                applier(normalized, ctx, target)
                if apply_version is not None:
                    self._staging_repo.mark_applied(
                        source=source,
                        entity=entity,
                        source_id=str(target),
                        content_hash=content_hash,
                        applied_version=apply_version,
                    )
                self._logger.info("etl applier done: target=%s", target)
                success_count += 1
            except Exception:
                failure_count += 1
                self._logger.exception(
                    "ETL failed for target=%s source=%s entity=%s", target, source, entity
                )

        failure_rate = failure_count / total_targets if total_targets else 0
        self._logger.info(
            "etl done: source=%s entity=%s success=%s failure=%s failure_rate=%s",
            source,
            entity,
            success_count,
            failure_count,
            failure_rate,
        )
        return {
            "total_targets": total_targets,
            "success_count": success_count,
            "failure_count": failure_count,
            "failure_rate": failure_rate,
        }
