from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from repos.apl.rank_repo import RankRepo  # noqa: E402


class FakeCursor:
    def __init__(self, *, fetchall_value=None) -> None:
        self.fetchall_value = fetchall_value or []
        self.executed = []
        self.executed_many = []
        self.rowcount = 0
        self.closed = False

    def execute(self, query: str, params=None) -> None:
        self.executed.append((query, params))

    def executemany(self, query: str, params_seq) -> None:
        self.executed_many.append((query, params_seq))
        self.rowcount = len(params_seq)

    def fetchall(self):
        return self.fetchall_value

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
def test_insert_rank_snapshot_inserts_items() -> None:
    cursor = FakeCursor()
    repo = RankRepo(conn=FakeConnection(cursor))
    ranking_items = [
        {
            "rank": 1,
            "itemCode": "shop:1",
            "lastBuildDate": "2026-01-27T04:00:00+09:00",
            "title": "Rakuten Ranking",
        },
        {
            "rank": 2,
            "itemCode": "shop:2",
            "lastBuildDate": "2026-01-27T04:00:00+09:00",
            "title": "Rakuten Ranking",
        },
    ]

    affected = repo.insert_rank_snapshot(
        run_id="run-1", genre_id=100283, ranking_items=ranking_items
    )

    assert affected == 2
    assert cursor.executed_many
    sql = cursor.executed_many[0][0]
    assert "insert into apl.item_rank_snapshot" in sql
    params = cursor.executed_many[0][1]
    assert params[0] == (
        "shop:1",
        "2026-01-27T04:00:00+09:00",
        100283,
        "Rakuten Ranking",
        "2026-01-27T04:00:00+09:00",
        1,
    )


@pytest.mark.unit
def test_insert_rank_snapshot_returns_zero_when_empty() -> None:
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    repo = RankRepo(conn=conn)

    affected = repo.insert_rank_snapshot(run_id="run-1", genre_id=100, ranking_items=[])

    assert affected == 0
    assert conn.committed is False
    assert cursor.executed_many == []


@pytest.mark.unit
def test_fetch_distinct_item_codes_since() -> None:
    cursor = FakeCursor(fetchall_value=[("item-1",), ("item-2",)])
    repo = RankRepo(conn=FakeConnection(cursor))
    since = datetime(2026, 1, 1, tzinfo=timezone.utc)

    result = repo.fetch_distinct_item_codes_since(since=since)

    assert result == ["item-1", "item-2"]
    assert cursor.executed
    assert "select distinct rakuten_item_code" in cursor.executed[0][0]
