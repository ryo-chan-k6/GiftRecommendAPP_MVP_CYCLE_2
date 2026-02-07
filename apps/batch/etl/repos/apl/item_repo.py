from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional, Protocol, Sequence


class Cursor(Protocol):
    def execute(self, query: str, params: Sequence[object] | None = None) -> None: ...
    def executemany(self, query: str, params_seq: Sequence[Sequence[object]]) -> None: ...
    def fetchall(self) -> Sequence[Sequence[object]]: ...
    def fetchone(self) -> Optional[Sequence[object]]: ...
    @property
    def rowcount(self) -> int: ...
    def close(self) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> None: ...


class ItemRepo:
    def __init__(self, *, conn: Connection) -> None:
        self._conn = conn

    def upsert_item(self, *, normalized_item: Mapping[str, Any]) -> str:
        sql = (
            "insert into apl.item "
            "(rakuten_item_code, item_name, item_url, affiliate_url, catchcopy, "
            "item_caption, image_flag, rakuten_shop_code, rakuten_genre_id, credit_card_flag) "
            "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "on conflict (rakuten_item_code) do update set "
            "item_name = excluded.item_name, "
            "item_url = excluded.item_url, "
            "affiliate_url = excluded.affiliate_url, "
            "catchcopy = excluded.catchcopy, "
            "item_caption = excluded.item_caption, "
            "image_flag = excluded.image_flag, "
            "rakuten_shop_code = excluded.rakuten_shop_code, "
            "rakuten_genre_id = excluded.rakuten_genre_id, "
            "credit_card_flag = excluded.credit_card_flag, "
            "updated_at = now() "
            "returning id"
        )
        params = (
            normalized_item.get("itemCode"),
            normalized_item.get("itemName"),
            normalized_item.get("itemUrl"),
            normalized_item.get("affiliateUrl"),
            normalized_item.get("catchcopy"),
            normalized_item.get("itemCaption"),
            normalized_item.get("imageFlag"),
            normalized_item.get("shopCode"),
            normalized_item.get("genreId"),
            normalized_item.get("creditCardFlag"),
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params)
            row = cur.fetchone()
        finally:
            cur.close()
        if not row:
            raise RuntimeError("failed to upsert item")
        self._conn.commit()
        return str(row[0])

    def sync_item_images(self, *, item_id: str, normalized_item: Mapping[str, Any]) -> int:
        delete_sql = "delete from apl.item_image where item_id = %s"
        images = _extract_images(normalized_item)
        insert_sql = (
            "insert into apl.item_image (item_id, size, url, sort_order) "
            "values (%s, %s, %s, %s)"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(delete_sql, (item_id,))
            if images:
                cur.executemany(insert_sql, [(item_id, *row) for row in images])
                affected = cur.rowcount
            else:
                affected = 0
        finally:
            cur.close()
        self._conn.commit()
        return affected

    def insert_market_snapshot(
        self, *, item_id: str, collected_at: datetime, normalized_item: Mapping[str, Any]
    ) -> int:
        sql = (
            "insert into apl.item_market_snapshot "
            "(item_id, collected_at, item_price, tax_flag, postage_flag, gift_flag, "
            "availability, asuraku_flag, asuraku_closing_time, asuraku_area, start_time, "
            "end_time, point_rate, point_rate_start_time, point_rate_end_time) "
            "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        params = (
            item_id,
            collected_at,
            normalized_item.get("itemPrice"),
            normalized_item.get("taxFlag"),
            normalized_item.get("postageFlag"),
            normalized_item.get("giftFlag"),
            normalized_item.get("availability"),
            normalized_item.get("asurakuFlag"),
            normalized_item.get("asurakuClosingTime"),
            normalized_item.get("asurakuArea"),
            normalized_item.get("startTime"),
            normalized_item.get("endTime"),
            normalized_item.get("pointRate"),
            normalized_item.get("pointRateStartTime"),
            normalized_item.get("pointRateEndTime"),
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params)
            affected = cur.rowcount
        finally:
            cur.close()
        self._conn.commit()
        return affected

    def insert_review_snapshot(
        self, *, item_id: str, collected_at: datetime, normalized_item: Mapping[str, Any]
    ) -> int:
        sql = (
            "insert into apl.item_review_snapshot "
            "(item_id, collected_at, review_count, review_average) "
            "values (%s, %s, %s, %s)"
        )
        params = (
            item_id,
            collected_at,
            normalized_item.get("reviewCount"),
            normalized_item.get("reviewAverage"),
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params)
            affected = cur.rowcount
        finally:
            cur.close()
        self._conn.commit()
        return affected

    def upsert_shop(self, *, normalized_item: Mapping[str, Any]) -> str:
        sql = (
            "insert into apl.shop "
            "(rakuten_shop_code, shop_name, shop_url, shop_of_the_year_flag) "
            "values (%s, %s, %s, %s) "
            "on conflict (rakuten_shop_code) do update set "
            "shop_name = excluded.shop_name, "
            "shop_url = excluded.shop_url, "
            "shop_of_the_year_flag = excluded.shop_of_the_year_flag, "
            "updated_at = now() "
            "returning id"
        )
        params = (
            normalized_item.get("shopCode"),
            normalized_item.get("shopName"),
            normalized_item.get("shopUrl"),
            normalized_item.get("shopOfTheYearFlag"),
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params)
            row = cur.fetchone()
        finally:
            cur.close()
        if not row:
            raise RuntimeError("failed to upsert shop")
        self._conn.commit()
        return str(row[0])

    def fetch_distinct_genre_ids_by_source_ids(self, source_ids: Sequence[str]) -> Sequence[int]:
        if not source_ids:
            return []
        sql = (
            "select distinct rakuten_genre_id "
            "from apl.item "
            "where rakuten_item_code = any(%s) "
            "and rakuten_genre_id is not null "
            "order by rakuten_genre_id"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, (list(source_ids),))
            rows = cur.fetchall()
        finally:
            cur.close()
        return [row[0] for row in rows]


def _extract_images(normalized_item: Mapping[str, Any]) -> list[tuple[str, str, int]]:
    images: list[tuple[str, str, int]] = []
    for size_key, size_label in (("smallImageUrls", "small"), ("mediumImageUrls", "medium")):
        urls = normalized_item.get(size_key) or []
        for idx, entry in enumerate(urls, start=1):
            if isinstance(entry, dict):
                url = entry.get("imageUrl")
            else:
                url = entry
            if url:
                images.append((size_label, str(url), idx))
    return images
