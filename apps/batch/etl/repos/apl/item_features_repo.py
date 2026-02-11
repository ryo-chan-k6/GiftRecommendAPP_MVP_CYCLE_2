from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, Sequence


class Cursor(Protocol):
    def execute(self, query: str, params: Sequence[object] | None = None) -> None: ...
    def fetchall(self) -> Sequence[Sequence[object]]: ...
    def fetchone(self) -> Optional[Sequence[object]]: ...
    @property
    def rowcount(self) -> int: ...
    def close(self) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> None: ...


@dataclass(frozen=True)
class ItemFeatureRow:
    item_id: str
    price_yen: Optional[int]
    point_rate: Optional[int]
    availability: Optional[int]
    review_average: Optional[float]
    review_count: Optional[int]
    rank: Optional[int]
    rakuten_genre_id: Optional[int]
    tag_ids: Sequence[int]
    feature_updated_at: Optional[datetime]


class ItemFeaturesRepo:
    def __init__(self, *, conn: Connection) -> None:
        self._conn = conn

    def fetch_feature_rows(self, *, since: datetime) -> Sequence[ItemFeatureRow]:
        sql = (
            "select "
            "item_id, item_price, point_rate, availability, review_average, "
            "review_count, rank, rakuten_genre_id, rakuten_tag_ids, feature_updated_at "
            "from apl.item_feature_view "
            "where is_active = true and feature_updated_at >= %s "
            "order by item_id"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, (since,))
            rows = cur.fetchall()
        finally:
            cur.close()
        return [
            ItemFeatureRow(
                item_id=str(row[0]),
                price_yen=row[1],
                point_rate=row[2],
                availability=row[3],
                review_average=row[4],
                review_count=row[5],
                rank=row[6],
                rakuten_genre_id=row[7],
                tag_ids=row[8] or [],
                feature_updated_at=row[9],
            )
            for row in rows
        ]

    def upsert_features(
        self,
        *,
        item_id: str,
        price_yen: Optional[int],
        price_log: Optional[float],
        point_rate: Optional[int],
        availability: Optional[int],
        review_average: Optional[float],
        review_count: Optional[int],
        review_count_log: Optional[float],
        rank: Optional[int],
        popularity_score: Optional[float],
        rakuten_genre_id: Optional[int],
        tag_ids: Sequence[int],
        features_version: int,
    ) -> str:
        sql = (
            "insert into apl.item_features "
            "(item_id, price_yen, price_log, point_rate, availability, "
            "review_average, review_count, review_count_log, rank, "
            "popularity_score, rakuten_genre_id, tag_ids, features_version, updated_at) "
            "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()) "
            "on conflict (item_id) do update set "
            "price_yen = excluded.price_yen, "
            "price_log = excluded.price_log, "
            "point_rate = excluded.point_rate, "
            "availability = excluded.availability, "
            "review_average = excluded.review_average, "
            "review_count = excluded.review_count, "
            "review_count_log = excluded.review_count_log, "
            "rank = excluded.rank, "
            "popularity_score = excluded.popularity_score, "
            "rakuten_genre_id = excluded.rakuten_genre_id, "
            "tag_ids = excluded.tag_ids, "
            "features_version = excluded.features_version, "
            "updated_at = now() "
            "where "
            "apl.item_features.price_yen is distinct from excluded.price_yen "
            "or apl.item_features.price_log is distinct from excluded.price_log "
            "or apl.item_features.point_rate is distinct from excluded.point_rate "
            "or apl.item_features.availability is distinct from excluded.availability "
            "or apl.item_features.review_average is distinct from excluded.review_average "
            "or apl.item_features.review_count is distinct from excluded.review_count "
            "or apl.item_features.review_count_log is distinct from excluded.review_count_log "
            "or apl.item_features.rank is distinct from excluded.rank "
            "or apl.item_features.popularity_score is distinct from excluded.popularity_score "
            "or apl.item_features.rakuten_genre_id is distinct from excluded.rakuten_genre_id "
            "or apl.item_features.tag_ids is distinct from excluded.tag_ids "
            "or apl.item_features.features_version is distinct from excluded.features_version "
            "returning (xmax = 0) as inserted"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(
                sql,
                (
                    item_id,
                    price_yen,
                    price_log,
                    point_rate,
                    availability,
                    review_average,
                    review_count,
                    review_count_log,
                    rank,
                    popularity_score,
                    rakuten_genre_id,
                    list(tag_ids),
                    features_version,
                ),
            )
            row = cur.fetchone()
        finally:
            cur.close()
        self._conn.commit()
        if not row:
            return "skipped"
        return "inserted" if bool(row[0]) else "updated"
