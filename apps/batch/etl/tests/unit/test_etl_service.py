from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.raw_store import RawPutResult  # noqa: E402
from services.context import build_context  # noqa: E402
from services.etl_service import EtlService  # noqa: E402


class FakeStagingRepo:
    def __init__(self, *, exists: bool) -> None:
        self.exists = exists
        self.upsert_rows = []

    def exists_hash(self, *, source: str, entity: str, source_id: str, content_hash: str) -> bool:
        return self.exists

    def batch_upsert(self, *, rows) -> int:
        self.upsert_rows.extend(rows)
        return len(rows)


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
    staging = FakeStagingRepo(exists=False)
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
    staging = FakeStagingRepo(exists=True)
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
    staging = FakeStagingRepo(exists=False)
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
    staging = FakeStagingRepo(exists=False)
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
