from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.hasher import compute_content_hash  # noqa: E402
from core.normalize import normalize  # noqa: E402
from core.raw_store import RawPutResult  # noqa: E402
from repos.staging_repo import StagingStatus  # noqa: E402
from services.context import build_context  # noqa: E402
from services.etl_service import EtlService  # noqa: E402


class FakeStagingRepo:
    def __init__(self, *, latest_status: StagingStatus | None) -> None:
        self.latest_status = latest_status
        self.upsert_rows = []
        self.marked = []

    def get_latest_status(self, *, source: str, entity: str, source_id: str):
        return self.latest_status

    def batch_upsert(self, *, rows) -> int:
        self.upsert_rows.extend(rows)
        return len(rows)

    def mark_applied(
        self, *, source: str, entity: str, source_id: str, content_hash: str, applied_version: int
    ) -> int:
        self.marked.append((source, entity, source_id, content_hash, applied_version))
        return 1


class FakeRawStore:
    def __init__(self) -> None:
        self.put_calls = []

    def build_key(self, *, source: str, entity: str, source_id: str, content_hash: str) -> str:
        return f"{source}:{entity}:{source_id}:{content_hash}"

    def put_json(self, *, bucket: str, s3_key: str, body) -> RawPutResult:
        self.put_calls.append((bucket, s3_key, body))
        return RawPutResult(s3_key=s3_key, etag="etag", saved_at=datetime.now(timezone.utc))


@pytest.mark.unit
def test_run_entity_etl_writes_on_diff() -> None:
    staging = FakeStagingRepo(latest_status=None)
    raw_store = FakeRawStore()
    ctx = build_context(job_id="JOB-X", env="dev", run_id="run-1")
    service = EtlService(staging_repo=staging, raw_store=raw_store, s3_bucket="bucket")
    applier_calls = []

    def target_provider(_ctx):
        return ["id-1"]

    def fetcher(_target):
        return {"itemCode": "id-1"}

    def applier(normalized, _ctx, _target):
        applier_calls.append(normalized)

    result = service.run_entity_etl(
        ctx=ctx,
        source="rakuten",
        entity="item",
        target_provider=target_provider,
        fetcher=fetcher,
        applier=applier,
    )

    assert result["total_targets"] == 1
    assert result["success_count"] == 1
    assert result["failure_count"] == 0
    assert raw_store.put_calls
    assert staging.upsert_rows
    assert applier_calls


@pytest.mark.unit
def test_run_entity_etl_skips_when_hash_exists() -> None:
    expected_hash = compute_content_hash(
        normalize("item", {"itemCode": "id-1"})
    )
    staging = FakeStagingRepo(
        latest_status=StagingStatus(content_hash=expected_hash, applied_version=None)
    )
    raw_store = FakeRawStore()
    ctx = build_context(job_id="JOB-X", env="dev", run_id="run-1")
    service = EtlService(staging_repo=staging, raw_store=raw_store, s3_bucket="bucket")
    applier_calls = []

    def target_provider(_ctx):
        return ["id-1"]

    def fetcher(_target):
        return {"itemCode": "id-1"}

    def applier(normalized, _ctx, _target):
        applier_calls.append(normalized)

    result = service.run_entity_etl(
        ctx=ctx,
        source="rakuten",
        entity="item",
        target_provider=target_provider,
        fetcher=fetcher,
        applier=applier,
    )

    assert result["success_count"] == 1
    assert raw_store.put_calls == []
    assert staging.upsert_rows == []
    assert applier_calls == []


@pytest.mark.unit
def test_run_entity_etl_skips_writes_on_dry_run() -> None:
    staging = FakeStagingRepo(latest_status=None)
    raw_store = FakeRawStore()
    ctx = build_context(job_id="JOB-X", env="dev", run_id="run-1", dry_run=True)
    service = EtlService(staging_repo=staging, raw_store=raw_store, s3_bucket="bucket")
    applier_calls = []

    def target_provider(_ctx):
        return ["id-1"]

    def fetcher(_target):
        return {"itemCode": "id-1"}

    def applier(normalized, _ctx, _target):
        applier_calls.append(normalized)

    result = service.run_entity_etl(
        ctx=ctx,
        source="rakuten",
        entity="item",
        target_provider=target_provider,
        fetcher=fetcher,
        applier=applier,
    )

    assert result["success_count"] == 1
    assert raw_store.put_calls == []
    assert staging.upsert_rows == []
    assert applier_calls == []


@pytest.mark.unit
def test_run_entity_etl_records_failure() -> None:
    staging = FakeStagingRepo(latest_status=None)
    raw_store = FakeRawStore()
    ctx = build_context(job_id="JOB-X", env="dev", run_id="run-1")
    service = EtlService(staging_repo=staging, raw_store=raw_store, s3_bucket="bucket")

    def target_provider(_ctx):
        return ["id-1"]

    def fetcher(_target):
        raise ValueError("boom")

    def applier(normalized, _ctx, _target):
        raise AssertionError("should not run")

    result = service.run_entity_etl(
        ctx=ctx,
        source="rakuten",
        entity="item",
        target_provider=target_provider,
        fetcher=fetcher,
        applier=applier,
    )

    assert result["success_count"] == 0
    assert result["failure_count"] == 1
