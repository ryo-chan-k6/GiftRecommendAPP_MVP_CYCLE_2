from __future__ import annotations

from typing import Protocol, Sequence


class Cursor(Protocol):
    def execute(self, query: str, params: Sequence[object] | None = None) -> None: ...
    def fetchall(self) -> Sequence[Sequence[object]]: ...
    def close(self) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...


class TargetGenreConfigRepo:
    def __init__(self, *, conn: Connection) -> None:
        self._conn = conn

    def fetch_enabled_genre_ids(self) -> Sequence[int]:
        sql = (
            "select rakuten_genre_id "
            "from apl.target_genre_config "
            "where is_enabled = true "
            "order by rakuten_genre_id"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchall()
        finally:
            cur.close()
        return [row[0] for row in rows]
