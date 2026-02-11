from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.config import AppConfig  # noqa: E402
from jobs import tag_job  # noqa: E402


class FakeStagingRepo:
    def __init__(self, *, conn) -> None:
        self.conn = conn


class FakeItemTagRepo:
    def __init__(self, *, conn) -> None:
        self.conn = conn

    def fetch_distinct_tag_ids_by_source_ids(self, source_ids):
        return [10]


class FakeTagRepo:
    last_instance = None

    def __init__(self, *, conn) -> None:
        self.conn = conn
        self.calls = []
        FakeTagRepo.last_instance = self

    def upsert_tag_group(self, *, normalized_tag):
        self.calls.append(("group", normalized_tag))
        return 1

    def upsert_tag(self, *, normalized_tag):
        self.calls.append(("tag", normalized_tag))
        return 1


class FakeRawStore:
    def __init__(self, *, region: str) -> None:
        self.region = region


class FakeRakutenClient:
    def __init__(self, *, config) -> None:
        self.config = config

    def fetch_tag(self, *, tag_id: int):
        return {"tagGroup": {"tagGroupId": 1000, "tagGroupName": "Group", "tags": []}}


class FakeEtlService:
    last_instance = None

    def __init__(self, *, staging_repo, raw_store, s3_bucket, logger=None) -> None:
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
def test_run_job_wires_dependencies(monkeypatch) -> None:
    monkeypatch.setattr(tag_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(tag_job, "ItemTagRepo", FakeItemTagRepo)
    monkeypatch.setattr(tag_job, "TagRepo", FakeTagRepo)
    monkeypatch.setattr(tag_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(tag_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(tag_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(tag_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    result = tag_job.run_job(config=config, run_id="run-1", dry_run=True)

    assert result == {"ok": True}
    service = FakeEtlService.last_instance
    assert service.run_args["source"] == "rakuten"
    assert service.run_args["entity"] == "tag"


@pytest.mark.unit
def test_applier_upserts_group_and_tags(monkeypatch) -> None:
    monkeypatch.setattr(tag_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(tag_job, "ItemTagRepo", FakeItemTagRepo)
    monkeypatch.setattr(tag_job, "TagRepo", FakeTagRepo)
    monkeypatch.setattr(tag_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(tag_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(tag_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(tag_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    tag_job.run_job(config=config, run_id="run-1", dry_run=False)
    service = FakeEtlService.last_instance
    applier = service.run_args["applier"]

    applier({"tagGroup": {"tagGroupId": 1000}}, service.run_args["ctx"], "10")

    tag_repo = FakeTagRepo.last_instance
    assert ("group", {"tagGroup": {"tagGroupId": 1000}}) in tag_repo.calls
    assert ("tag", {"tagGroup": {"tagGroupId": 1000}}) in tag_repo.calls


@pytest.mark.unit
def test_extract_tag_group_payloads_handles_tag_groups_array() -> None:
    """tagGroups 配列形式（楽天API実レスポンス）を正しく展開する"""
    normalized = {
        "tagGroups": [
            {
                "tagGroup": {
                    "tagGroupName": "サイズ（S/M/L）",
                    "tagGroupId": 1000041,
                    "tags": [
                        {
                            "tag": {
                                "tagId": 1000317,
                                "tagName": "SS",
                                "parentTagId": 0,
                            }
                        }
                    ],
                }
            }
        ]
    }
    payloads = tag_job._extract_tag_group_payloads(normalized)
    assert len(payloads) == 1
    assert payloads[0]["tagGroup"]["tagGroupId"] == 1000041
    assert payloads[0]["tagGroup"]["tagGroupName"] == "サイズ（S/M/L）"
    assert len(payloads[0]["tagGroup"]["tags"]) == 1
    assert payloads[0]["tagGroup"]["tags"][0]["tag"]["tagId"] == 1000317


@pytest.mark.unit
def test_applier_handles_tag_groups_structure(monkeypatch) -> None:
    """tagGroups 配列形式で applier が tag_repo を正しく呼ぶ"""
    monkeypatch.setattr(tag_job, "StagingRepo", FakeStagingRepo)
    monkeypatch.setattr(tag_job, "ItemTagRepo", FakeItemTagRepo)
    monkeypatch.setattr(tag_job, "TagRepo", FakeTagRepo)
    monkeypatch.setattr(tag_job, "RawStore", FakeRawStore)
    monkeypatch.setattr(tag_job, "RakutenClient", FakeRakutenClient)
    monkeypatch.setattr(tag_job, "EtlService", FakeEtlService)
    monkeypatch.setattr(tag_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    tag_job.run_job(config=config, run_id="run-1", dry_run=False)
    service = FakeEtlService.last_instance
    applier = service.run_args["applier"]

    # 楽天API実レスポンス形式（tagGroups + tags[].tag）
    normalized = {
        "tagGroups": [
            {
                "tagGroup": {
                    "tagGroupName": "サイズ（S/M/L）",
                    "tagGroupId": 1000041,
                    "tags": [
                        {
                            "tag": {
                                "tagId": 1000317,
                                "tagName": "SS",
                                "parentTagId": 0,
                            }
                        }
                    ],
                }
            }
        ]
    }
    applier(normalized, service.run_args["ctx"], "1000317")

    tag_repo = FakeTagRepo.last_instance
    assert any(
        c[0] == "group" and c[1]["tagGroup"]["tagGroupId"] == 1000041
        for c in tag_repo.calls
    )
    assert any(
        c[0] == "tag" and c[1]["tagGroup"]["tagGroupId"] == 1000041
        for c in tag_repo.calls
    )
