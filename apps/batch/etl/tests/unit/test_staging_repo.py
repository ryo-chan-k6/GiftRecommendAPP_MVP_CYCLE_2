from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from repos.staging_repo import StagingRepo, StagingRow  # noqa: E402


class FakeCursor:
    def __init__(self, *, fetchone_value=None, rowcount=0) -> None:
        self.fetchone_value = fetchone_value
        self.rowcount = rowcount
        self.executed = []
        self.executed_many = []
        self.closed = False

    def execute(self, query: str, params=None) -> None:
        self.executed.append((query, params))

    def executemany(self, query: str, params_seq) -> None:
        self.executed_many.append((query, params_seq))

    def fetchone(self):
        return self.fetchone_value

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self) -> None:
        self.committed = True


@pytest.mark.unit
def test_exists_hash_returns_true_when_latest_hash_matches() -> None:
    cursor = FakeCursor(fetchone_value=("hash-1",))
    repo = StagingRepo(conn=FakeConnection(cursor))

    assert repo.exists_hash(
        source="rakuten", entity="item", source_id="shop:1", content_hash="hash-1"
    )
    assert cursor.closed is True


@pytest.mark.unit
def test_exists_hash_returns_false_when_no_row() -> None:
    cursor = FakeCursor(fetchone_value=None)
    repo = StagingRepo(conn=FakeConnection(cursor))

    assert (
        repo.exists_hash(
            source="rakuten", entity="item", source_id="shop:1", content_hash="hash-1"
        )
        is False
    )


@pytest.mark.unit
def test_batch_upsert_inserts_rows_and_commits() -> None:
    cursor = FakeCursor(rowcount=2)
    conn = FakeConnection(cursor)
    repo = StagingRepo(conn=conn)
    rows = [
        StagingRow(
            source="rakuten",
            entity="item",
            source_id="shop:1",
            content_hash="hash-1",
            s3_key="key-1",
            etag="etag-1",
            saved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        StagingRow(
            source="rakuten",
            entity="item",
            source_id="shop:2",
            content_hash="hash-2",
            s3_key="key-2",
            etag=None,
            saved_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ),
    ]

    affected = repo.batch_upsert(rows=rows)

    assert affected == 2
    assert conn.committed is True
    assert cursor.closed is True
    assert cursor.executed_many
    sql = cursor.executed_many[0][0]
    assert "on conflict (source, entity, source_id)" in sql
