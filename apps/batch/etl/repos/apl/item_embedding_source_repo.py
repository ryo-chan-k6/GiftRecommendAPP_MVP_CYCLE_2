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
    item_name: Optional[str]
    catchcopy: Optional[str]
    item_caption: Optional[str]
    genre_name: Optional[str]
    tag_names: Sequence[str]
    item_price: Optional[int]
    item_updated_at: Optional[datetime]
    feature_updated_at: Optional[datetime]


class ItemEmbeddingSourceRepo:
    def __init__(self, *, conn: Connection) -> None:
        self._conn = conn

    def fetch_feature_rows(self, *, since: datetime) -> Sequence[ItemFeatureRow]:
        sql = (
            "select "
            "item_id, item_name, catchcopy, item_caption, genre_name, tag_names, "
            "item_price, item_updated_at, feature_updated_at "
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
                item_name=row[1],
                catchcopy=row[2],
                item_caption=row[3],
                genre_name=row[4],
                tag_names=row[5] or [],
                item_price=row[6],
                item_updated_at=row[7],
                feature_updated_at=row[8],
            )
            for row in rows
        ]

    def upsert_source(
        self,
        *,
        item_id: str,
        source_version: int,
        source_text: str,
        source_hash: str,
    ) -> str:
        sql = (
            "insert into apl.item_embedding_source "
            "(item_id, source_version, source_text, source_hash, updated_at) "
            "values (%s, %s, %s, %s, now()) "
            "on conflict (item_id) do update set "
            "source_version = excluded.source_version, "
            "source_text = excluded.source_text, "
            "source_hash = excluded.source_hash, "
            "updated_at = now() "
            "where apl.item_embedding_source.source_hash is distinct from excluded.source_hash "
            "returning (xmax = 0) as inserted"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, (item_id, source_version, source_text, source_hash))
            row = cur.fetchone()
        finally:
            cur.close()
        self._conn.commit()
        if not row:
            return "skipped"
        return "inserted" if bool(row[0]) else "updated"
