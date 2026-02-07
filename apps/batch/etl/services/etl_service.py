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
    def __call__(self, normalized: Mapping[str, Any], ctx: JobContext) -> None: ...


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
    ) -> dict:
        targets = list(target_provider(ctx))
        total_targets = len(targets)
        success_count = 0
        failure_count = 0

        for target in targets:
            try:
                raw = fetcher(target)
                normalized = normalize(entity, raw)
                content_hash = compute_content_hash(normalized)
                if self._staging_repo.exists_hash(
                    source=source,
                    entity=entity,
                    source_id=str(target),
                    content_hash=content_hash,
                ):
                    success_count += 1
                    continue

                if ctx.dry_run:
                    success_count += 1
                    continue

                s3_key = self._raw_store.build_key(
                    source=source,
                    entity=entity,
                    source_id=str(target),
                    content_hash=content_hash,
                )
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
                self._staging_repo.batch_upsert(rows=[row])
                applier(normalized, ctx)
                success_count += 1
            except Exception:
                failure_count += 1
                self._logger.exception(
                    "ETL failed for target=%s source=%s entity=%s", target, source, entity
                )

        failure_rate = failure_count / total_targets if total_targets else 0
        return {
            "total_targets": total_targets,
            "success_count": success_count,
            "failure_count": failure_count,
            "failure_rate": failure_rate,
        }
