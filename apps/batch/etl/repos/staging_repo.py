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


@dataclass(frozen=True)
class StagingStatus:
    content_hash: str
    applied_version: int | None


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

    def get_latest_status(
        self, *, source: str, entity: str, source_id: str
    ) -> StagingStatus | None:
        sql = (
            "select content_hash, applied_version from apl.staging "
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
            return None
        return StagingStatus(content_hash=row[0], applied_version=row[1])

    def exists_hash(self, *, source: str, entity: str, source_id: str, content_hash: str) -> bool:
        status = self.get_latest_status(
            source=source, entity=entity, source_id=source_id
        )
        if not status:
            return False
        return status.content_hash == content_hash

    def batch_upsert(self, *, rows: Sequence[StagingRow]) -> int:
        if not rows:
            return 0
        sql = (
            "insert into apl.staging "
            "(source, entity, source_id, content_hash, s3_key, etag, saved_at, applied_at, applied_version) "
            "values (%s, %s, %s, %s, %s, %s, %s, null, null) "
            "on conflict (source, entity, source_id) do update set "
            "content_hash = excluded.content_hash, "
            "s3_key = excluded.s3_key, "
            "etag = excluded.etag, "
            "saved_at = excluded.saved_at, "
            "applied_at = null, "
            "applied_version = null, "
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

    def mark_applied(
        self,
        *,
        source: str,
        entity: str,
        source_id: str,
        content_hash: str,
        applied_version: int,
    ) -> int:
        sql = (
            "update apl.staging set "
            "applied_at = now(), applied_version = %s, updated_at = now() "
            "where source = %s and entity = %s and source_id = %s and content_hash = %s"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, (applied_version, source, entity, source_id, content_hash))
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
