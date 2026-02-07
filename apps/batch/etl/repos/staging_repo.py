from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, Sequence


@dataclass(frozen=True)
class StagingRow:
    source: str
    entity: str
    source_id: str
    content_hash: str
    s3_key: str
    etag: Optional[str]
    saved_at: datetime


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


class StagingRepo:
    def __init__(self, *, conn: Connection) -> None:
        self._conn = conn

    def exists_hash(self, *, source: str, entity: str, source_id: str, content_hash: str) -> bool:
        sql = (
            "select content_hash from apl.staging "
            "where source = %s and entity = %s and source_id = %s "
            "order by saved_at desc limit 1"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, (source, entity, source_id))
            row = cur.fetchone()
        finally:
            cur.close()
        if not row:
            return False
        return row[0] == content_hash

    def batch_upsert(self, *, rows: Sequence[StagingRow]) -> int:
        if not rows:
            return 0
        sql = (
            "insert into apl.staging "
            "(source, entity, source_id, content_hash, s3_key, etag, saved_at) "
            "values (%s, %s, %s, %s, %s, %s, %s) "
            "on conflict (source, entity, source_id) do update set "
            "content_hash = excluded.content_hash, "
            "s3_key = excluded.s3_key, "
            "etag = excluded.etag, "
            "saved_at = excluded.saved_at, "
            "updated_at = now()"
        )
        params = [
            (
                row.source,
                row.entity,
                row.source_id,
                row.content_hash,
                row.s3_key,
                row.etag,
                row.saved_at,
            )
            for row in rows
        ]
        cur = self._conn.cursor()
        try:
            cur.executemany(sql, params)
            affected = cur.rowcount
        finally:
            cur.close()
        self._conn.commit()
        return affected

    def fetch_item_source_ids_since(self, *, since: datetime) -> Sequence[str]:
        sql = (
            "select distinct source_id "
            "from apl.staging "
            "where source = %s and entity = %s and saved_at >= %s "
            "order by source_id"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, ("rakuten", "item", since))
            rows = cur.fetchall()
        finally:
            cur.close()
        return [row[0] for row in rows]
