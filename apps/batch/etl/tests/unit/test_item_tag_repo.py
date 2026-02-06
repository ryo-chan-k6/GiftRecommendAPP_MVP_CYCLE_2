from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from repos.apl.item_tag_repo import ItemTagRepo  # noqa: E402


class FakeCursor:
    def __init__(self) -> None:
        self.executed = []
        self.executed_many = []
        self.rowcount = 0
        self.closed = False

    def execute(self, query: str, params=None) -> None:
        self.executed.append((query, params))

    def executemany(self, query: str, params_seq) -> None:
        self.executed_many.append((query, params_seq))
        self.rowcount = len(params_seq)

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
def test_sync_item_tags_deletes_and_inserts() -> None:
    cursor = FakeCursor()
    repo = ItemTagRepo(conn=FakeConnection(cursor))

    affected = repo.sync_item_tags(item_id="item-id", rakuten_tag_ids=[1, 2, 3])

    assert affected == 3
    assert cursor.executed
    assert "delete from apl.item_tag" in cursor.executed[0][0]
    assert cursor.executed_many


@pytest.mark.unit
def test_sync_item_tags_handles_empty_tags() -> None:
    cursor = FakeCursor()
    repo = ItemTagRepo(conn=FakeConnection(cursor))

    affected = repo.sync_item_tags(item_id="item-id", rakuten_tag_ids=[])

    assert affected == 0
    assert cursor.executed
    assert cursor.executed_many == []
