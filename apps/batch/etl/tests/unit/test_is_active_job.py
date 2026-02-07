from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.config import AppConfig  # noqa: E402
from jobs import is_active_job  # noqa: E402


class FakeCursor:
    def __init__(self, *, rowcount: int = 0) -> None:
        self.executed = []
        self.rowcount = rowcount
        self.closed = False

    def execute(self, query: str, params=None) -> None:
        self.executed.append((query, params))

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


@contextmanager
def fake_db_connection(*, database_url: str):
    assert database_url == "postgres://example"
    yield FakeConnection(FakeCursor(rowcount=3))


@contextmanager
def fake_transaction(conn):
    yield conn


@pytest.mark.unit
def test_run_job_executes_update(monkeypatch) -> None:
    monkeypatch.setattr(is_active_job, "db_connection", fake_db_connection)
    monkeypatch.setattr(is_active_job, "transaction", fake_transaction)
    monkeypatch.setattr(is_active_job, "_load_sql", lambda: "update apl.item set is_active = true")

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    result = is_active_job.run_job(config=config, run_id="run-1", dry_run=False)

    assert result["updated"] == 3


@pytest.mark.unit
def test_run_job_skips_on_dry_run(monkeypatch) -> None:
    monkeypatch.setattr(is_active_job, "db_connection", fake_db_connection)

    config = AppConfig(
        env="dev",
        database_url="postgres://example",
        rakuten_app_id="app",
        rakuten_affiliate_id=None,
        s3_bucket_raw="bucket",
        aws_region="ap-northeast-1",
    )

    result = is_active_job.run_job(config=config, run_id="run-1", dry_run=True)

    assert result == {"updated": 0}
