from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.config import AppConfig  # noqa: E402
from jobs import item_job  # noqa: E402


class FakeRankRepo:
    def __init__(self, *, conn) -> None:
        self.conn = conn

    def fetch_distinct_item_codes_since(self, *, since):
        return ["shop:1"]


class FakeStagingRepo:
    def __init__(self, *, conn) -> None:
        self.conn = conn


class FakeItemRepo:
    last_instance = None

    def __init__(self, *, conn) -> None:
        self.conn = conn
        self.calls = []
        FakeItemRepo.last_instance = self

    def upsert_shop(self, *, normalized_item):
        self.calls.append(("shop", normalized_item))
        return "shop-id"

    def upsert_item(self, *, normalized_item):
        self.calls.append(("item", normalized_item))
        return "item-id"

    def sync_item_images(self, *, item_id: str, normalized_item):
        self.calls.append(("images", item_id, normalized_item))
        return 1

    def insert_market_snapshot(self, *, item_id: str, collected_at, normalized_item):
        self.calls.append(("market", item_id, collected_at, normalized_item))
        return 1

    def insert_review_snapshot(self, *, item_id: str, collected_at, normalized_item):
        self.calls.append(("review", item_id, collected_at, normalized_item))
        return 1


class FakeItemTagRepo:
    last_instance = None

    def __init__(self, *, conn) -> None:
        self.conn = conn
        self.calls = []
        FakeItemTagRepo.last_instance = self

    def sync_item_tags(self, *, item_id: str, rakuten_tag_ids):
        self.calls.append((item_id, list(rakuten_tag_ids)))
        return len(rakuten_tag_ids)


class FakeRawStore:
    def __init__(self, *, region: str) -> None:
        self.region = region


class FakeRakutenClient:
    def __init__(self, *, config) -> None:
        self.config = config

    def fetch_item(self, *, item_code: str):
        return {"items": [{"itemCode": item_code, "tagIds": [1, 2]}]}


class FakeEtlService:
    last_instance = None

    def __init__(self, *, staging_repo, raw_store, s3_bucket, logger=None) -> None:
        self.run_args = None
        FakeEtlService.last_instance = self

    def run_entity_etl(
        self, *, ctx, source, entity, target_provider, fetcher, applier, apply_version=None
    ) -> dict:
        self.run_args = {
            "ctx": ctx,
            "source": source,
            "entity": entity,
            "target_provider": target_provider,
            "fetcher": fetcher,
            "applier": applier,
            "apply_version": apply_version,
        }
        return {"ok": True}


@contextmanager
def fake_db_connection(*, database_url: str):
    assert database_url == "postgres://example"
    yield object()


@pytest.mark.unit
def test_run_job_wires_dependencies(monkeypatch) -> None:
    monkeypatch.setattr(item_job, "RankRepo", FakeRankRepo)
    monkeypatch.setattr(item_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(item_job, "ItemRepo", FakeItemRepo)
    monkeypatch.setattr(item_job, "ItemTagRepo", FakeItemTagRepo)
    monkeypatch.setattr(item_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(item_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(item_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(item_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    result = item_job.run_job(config=config, run_id="run-1", dry_run=True)

    assert result == {"ok": True}
    service = FakeEtlService.last_instance
    assert service.run_args["source"] == "rakuten"
    assert service.run_args["entity"] == "item"


@pytest.mark.unit
def test_applier_updates_item_and_tags(monkeypatch) -> None:
    monkeypatch.setattr(item_job, "RankRepo", FakeRankRepo)
    monkeypatch.setattr(item_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(item_job, "ItemRepo", FakeItemRepo)
    monkeypatch.setattr(item_job, "ItemTagRepo", FakeItemTagRepo)
    monkeypatch.setattr(item_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(item_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(item_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(item_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    item_job.run_job(config=config, run_id="run-1", dry_run=False)
    service = FakeEtlService.last_instance
    applier = service.run_args["applier"]
    ctx = service.run_args["ctx"]

    normalized = {"items": [{"itemCode": "shop:1", "tagIds": [1, 2]}]}
    applier(normalized, ctx, "shop:1")

    item_repo = FakeItemRepo.last_instance
    tag_repo = FakeItemTagRepo.last_instance

    assert item_repo.calls[0][0] == "shop"
    assert item_repo.calls[1][0] == "item"
    assert item_repo.calls[2][0] == "images"
    assert item_repo.calls[3][0] == "market"
    assert item_repo.calls[4][0] == "review"
    assert tag_repo.calls == [("item-id", [1, 2])]


@pytest.mark.unit
def test_applier_handles_capitalized_items(monkeypatch) -> None:
    monkeypatch.setattr(item_job, "RankRepo", FakeRankRepo)
    monkeypatch.setattr(item_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(item_job, "ItemRepo", FakeItemRepo)
    monkeypatch.setattr(item_job, "ItemTagRepo", FakeItemTagRepo)
    monkeypatch.setattr(item_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(item_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(item_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(item_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    item_job.run_job(config=config, run_id="run-1", dry_run=False)
    service = FakeEtlService.last_instance
    applier = service.run_args["applier"]
    ctx = service.run_args["ctx"]

    normalized = {"Items": [{"Item": {"itemCode": "shop:1", "tagIds": [1, 2]}}]}
    applier(normalized, ctx, "shop:1")

    item_repo = FakeItemRepo.last_instance
    tag_repo = FakeItemTagRepo.last_instance

    assert item_repo.calls[0][0] == "shop"
    assert item_repo.calls[1][0] == "item"
    assert item_repo.calls[2][0] == "images"
    assert item_repo.calls[3][0] == "market"
    assert item_repo.calls[4][0] == "review"
    assert tag_repo.calls == [("item-id", [1, 2])]
