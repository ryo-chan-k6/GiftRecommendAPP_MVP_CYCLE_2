from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from repos.apl.item_repo import ItemRepo  # noqa: E402


class FakeCursor:
    def __init__(self, *, fetchone_values=None, fetchall_value=None) -> None:
        self.fetchone_values = list(fetchone_values or [])
        self.fetchall_value = fetchall_value or []
        self.executed = []
        self.executed_many = []
        self.rowcount = 0
        self.closed = False

    def execute(self, query: str, params=None) -> None:
        self.executed.append((query, params))
        self.rowcount = 1

    def executemany(self, query: str, params_seq) -> None:
        self.executed_many.append((query, params_seq))
        self.rowcount = len(params_seq)

    def fetchone(self):
        return self.fetchone_values.pop(0) if self.fetchone_values else None

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
def test_upsert_item_returns_id() -> None:
    cursor = FakeCursor(fetchone_values=[("item-id",)])
    repo = ItemRepo(conn=FakeConnection(cursor))
    normalized = {
        "itemCode": "shop:1",
        "itemName": "Item",
        "itemUrl": "https://example.com",
        "affiliateUrl": "https://aff.example.com",
        "catchcopy": "catch",
        "itemCaption": "caption",
        "imageFlag": 1,
        "shopCode": "shop",
        "genreId": 100,
        "creditCardFlag": 1,
    }

    item_id = repo.upsert_item(normalized_item=normalized)

    assert item_id == "item-id"
    assert cursor.executed
    assert "on conflict (rakuten_item_code)" in cursor.executed[0][0]


@pytest.mark.unit
def test_sync_item_images_deletes_and_inserts() -> None:
    cursor = FakeCursor()
    repo = ItemRepo(conn=FakeConnection(cursor))
    normalized = {
        "smallImageUrls": ["s1", "s2"],
        "mediumImageUrls": ["m1"],
    }

    affected = repo.sync_item_images(item_id="item-id", normalized_item=normalized)

    assert affected == 3
    assert "delete from apl.item_image" in cursor.executed[0][0]
    assert cursor.executed_many
    insert_params = cursor.executed_many[0][1]
    assert insert_params[0] == ("item-id", "small", "s1", 1)
    assert insert_params[1] == ("item-id", "small", "s2", 2)
    assert insert_params[2] == ("item-id", "medium", "m1", 1)


@pytest.mark.unit
def test_insert_market_snapshot_uses_collected_at() -> None:
    cursor = FakeCursor()
    repo = ItemRepo(conn=FakeConnection(cursor))
    collected_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    repo.insert_market_snapshot(
        item_id="item-id",
        collected_at=collected_at,
        normalized_item={"itemPrice": 100},
    )

    assert cursor.executed
    assert cursor.executed[0][1][1] == collected_at


@pytest.mark.unit
def test_upsert_shop_returns_id() -> None:
    cursor = FakeCursor(fetchone_values=[("shop-id",)])
    repo = ItemRepo(conn=FakeConnection(cursor))
    normalized = {"shopCode": "shop", "shopName": "Shop", "shopUrl": "https://shop"}

    shop_id = repo.upsert_shop(normalized_item=normalized)

    assert shop_id == "shop-id"
    assert "on conflict (rakuten_shop_code)" in cursor.executed[0][0]


@pytest.mark.unit
def test_fetch_distinct_genre_ids_by_source_ids_returns_ids() -> None:
    cursor = FakeCursor(fetchall_value=[(100,), (200,)])
    repo = ItemRepo(conn=FakeConnection(cursor))

    result = repo.fetch_distinct_genre_ids_by_source_ids(["item-1", "item-2"])

    assert result == [100, 200]
    assert cursor.executed
    sql = cursor.executed[0][0]
    assert "from apl.item" in sql
