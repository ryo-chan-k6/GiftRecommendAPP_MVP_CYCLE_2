from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.config import AppConfig  # noqa: E402
from jobs import ranking_job  # noqa: E402


class FakeTargetGenreConfigRepo:
    def __init__(self, *, conn) -> None:
        self.conn = conn
        self.genre_ids = [100]

    def fetch_enabled_genre_ids(self):
        return self.genre_ids


class FakeStagingRepo:
    def __init__(self, *, conn) -> None:
        self.conn = conn


class FakeRankRepo:
    last_instance = None

    def __init__(self, *, conn) -> None:
        self.conn = conn
        self.calls = []
        FakeRankRepo.last_instance = self

    def insert_rank_snapshot(self, *, run_id: str, genre_id: int, ranking_items, fetched_at):
        self.calls.append((run_id, genre_id, ranking_items, fetched_at))
        return len(ranking_items)


class FakeRawStore:
    def __init__(self, *, region: str) -> None:
        self.region = region


class FakeRakutenClient:
    def __init__(self, *, config) -> None:
        self.config = config
        self.fetch_calls = []

    def fetch_ranking(self, *, genre_id: int):
        self.fetch_calls.append(genre_id)
        return {
            "title": "Ranking",
            "lastBuildDate": "2026-01-01T00:00:00+09:00",
            "items": [{"rank": 1, "itemCode": "shop:1"}],
        }


class FakeEtlService:
    last_instance = None

    def __init__(self, *, staging_repo, raw_store, s3_bucket, logger=None) -> None:
        self.staging_repo = staging_repo
        self.raw_store = raw_store
        self.s3_bucket = s3_bucket
        self.logger = logger
        self.run_args = None
        FakeEtlService.last_instance = self

    def run_entity_etl(
        self, *, ctx, source, entity, target_provider, fetcher, applier
    ) -> dict:
        self.run_args = {
            "ctx": ctx,
            "source": source,
            "entity": entity,
            "target_provider": target_provider,
            "fetcher": fetcher,
            "applier": applier,
        }
        return {"ok": True}


@contextmanager
def fake_db_connection(*, database_url: str):
    assert database_url == "postgres://example"
    yield object()


@pytest.mark.unit
def test_run_job_wires_dependencies_and_calls_service(monkeypatch) -> None:
    monkeypatch.setattr(ranking_job, "TargetGenreConfigRepo", FakeTargetGenreConfigRepo)
    monkeypatch.setattr(ranking_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(ranking_job, "RankRepo", FakeRankRepo)
    monkeypatch.setattr(ranking_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(ranking_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(ranking_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(ranking_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    result = ranking_job.run_job(config=config, run_id="run-1", dry_run=True)

    assert result == {"ok": True}
    service = FakeEtlService.last_instance
    assert service is not None
    assert service.run_args["source"] == "rakuten"
    assert service.run_args["entity"] == "ranking"

    targets = list(service.run_args["target_provider"](service.run_args["ctx"]))
    assert targets == [100]

    fetched = service.run_args["fetcher"](100)
    assert fetched["items"][0]["itemCode"] == "shop:1"

    applier = service.run_args["applier"]
    assert applier is not None


@pytest.mark.unit
def test_applier_enriches_items_and_inserts(monkeypatch) -> None:
    monkeypatch.setattr(ranking_job, "TargetGenreConfigRepo", FakeTargetGenreConfigRepo)
    monkeypatch.setattr(ranking_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(ranking_job, "RankRepo", FakeRankRepo)
    monkeypatch.setattr(ranking_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(ranking_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(ranking_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(ranking_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    ranking_job.run_job(config=config, run_id="run-1", dry_run=False)
    service = FakeEtlService.last_instance
    applier = service.run_args["applier"]
    ctx = service.run_args["ctx"]

    rank_repo = FakeRankRepo.last_instance

    normalized = {
        "title": "Ranking",
        "lastBuildDate": "2026-01-01T00:00:00+09:00",
        "items": [{"rank": 1, "itemCode": "shop:1"}],
    }

    applier(normalized, ctx, "100")

    assert rank_repo.calls
    run_id, genre_id, items, fetched_at = rank_repo.calls[0]
    assert run_id == "run-1"
    assert genre_id == 100
    assert fetched_at == ctx.job_start_at
    assert items[0]["title"] == "Ranking"
    assert items[0]["lastBuildDate"] == "2026-01-01T00:00:00+09:00"


@pytest.mark.unit
def test_applier_handles_capitalized_items(monkeypatch) -> None:
    monkeypatch.setattr(ranking_job, "TargetGenreConfigRepo", FakeTargetGenreConfigRepo)
    monkeypatch.setattr(ranking_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(ranking_job, "RankRepo", FakeRankRepo)
    monkeypatch.setattr(ranking_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(ranking_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(ranking_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(ranking_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    ranking_job.run_job(config=config, run_id="run-1", dry_run=False)
    service = FakeEtlService.last_instance
    applier = service.run_args["applier"]
    ctx = service.run_args["ctx"]

    rank_repo = FakeRankRepo.last_instance

    normalized = {
        "title": "Ranking",
        "lastBuildDate": "2026-01-01T00:00:00+09:00",
        "Items": [{"Item": {"rank": 1, "itemCode": "shop:1"}}],
    }

    applier(normalized, ctx, "100")

    assert rank_repo.calls
    run_id, genre_id, items, fetched_at = rank_repo.calls[-1]
    assert run_id == "run-1"
    assert genre_id == 100
    assert fetched_at == ctx.job_start_at
    assert items[0]["itemCode"] == "shop:1"
    assert items[0]["title"] == "Ranking"
    assert items[0]["lastBuildDate"] == "2026-01-01T00:00:00+09:00"
