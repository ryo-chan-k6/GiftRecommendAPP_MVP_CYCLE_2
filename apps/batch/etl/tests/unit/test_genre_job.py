from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.config import AppConfig  # noqa: E402
from jobs import genre_job  # noqa: E402


class FakeStagingRepo:
    def __init__(self, *, conn) -> None:
        self.conn = conn


class FakeItemRepo:
    def __init__(self, *, conn) -> None:
        self.conn = conn

    def fetch_distinct_genre_ids_by_source_ids(self, source_ids):
        return [100]


class FakeGenreRepo:
    last_instance = None

    def __init__(self, *, conn) -> None:
        self.conn = conn
        self.calls = []
        FakeGenreRepo.last_instance = self

    def upsert_genre(self, *, normalized_genre):
        self.calls.append(normalized_genre)
        return 1


class FakeRawStore:
    def __init__(self, *, region: str) -> None:
        self.region = region


class FakeRakutenClient:
    def __init__(self, *, config) -> None:
        self.config = config

    def fetch_genre(self, *, genre_id: int):
        return {"current": {"genreId": genre_id, "genreName": "Name", "genreLevel": 1}}


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
    monkeypatch.setattr(genre_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(genre_job, "ItemRepo", FakeItemRepo)
    monkeypatch.setattr(genre_job, "GenreRepo", FakeGenreRepo)
    monkeypatch.setattr(genre_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(genre_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(genre_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(genre_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    result = genre_job.run_job(config=config, run_id="run-1", dry_run=True)

    assert result == {"ok": True}
    service = FakeEtlService.last_instance
    assert service.run_args["source"] == "rakuten"
    assert service.run_args["entity"] == "genre"


@pytest.mark.unit
def test_applier_upserts_genre(monkeypatch) -> None:
    monkeypatch.setattr(genre_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(genre_job, "ItemRepo", FakeItemRepo)
    monkeypatch.setattr(genre_job, "GenreRepo", FakeGenreRepo)
    monkeypatch.setattr(genre_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(genre_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(genre_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(genre_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    genre_job.run_job(config=config, run_id="run-1", dry_run=False)
    service = FakeEtlService.last_instance
    applier = service.run_args["applier"]

    applier({"current": {"genreId": 100}}, service.run_args["ctx"], "100")

    genre_repo = FakeGenreRepo.last_instance
    assert genre_repo.calls
