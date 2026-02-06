from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


class Cursor(Protocol):
    def execute(self, query: str, params: Sequence[object] | None = None) -> None: ...
    def executemany(self, query: str, params_seq: Sequence[Sequence[object]]) -> None: ...
    def fetchall(self) -> Sequence[Sequence[object]]: ...
    @property
    def rowcount(self) -> int: ...
    def close(self) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> None: ...


class RankRepo:
    def __init__(self, *, conn: Connection) -> None:
        self._conn = conn

    def insert_rank_snapshot(
        self,
        *,
        run_id: str,
        genre_id: int,
        ranking_items: Sequence[Mapping[str, Any]],
    ) -> int:
        if not ranking_items:
            return 0
        sql = (
            "insert into apl.item_rank_snapshot "
            "(rakuten_item_code, collected_at, rakuten_genre_id, title, last_build_date, rank) "
            "values (%s, %s, %s, %s, %s, %s) "
            "on conflict (rakuten_genre_id, rakuten_item_code, collected_at) do nothing"
        )
        params = []
        for item in ranking_items:
            item_code = _pick(item, ("itemCode", "item_code"))
            last_build_date = _pick(
                item, ("lastBuildDate", "last_build_date", "collectedAt", "collected_at")
            )
            collected_at = last_build_date
            title = _pick(item, ("title",))
            rank = item.get("rank")
            params.append((item_code, collected_at, genre_id, title, last_build_date, rank))
        cur = self._conn.cursor()
        try:
            cur.executemany(sql, params)
            affected = cur.rowcount
        finally:
            cur.close()
        self._conn.commit()
        return affected

    def fetch_distinct_item_codes_since(self, *, since) -> Sequence[str]:
        sql = (
            "select distinct rakuten_item_code "
            "from apl.item_rank_snapshot "
            "where collected_at >= %s "
            "order by rakuten_item_code"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, (since,))
            rows = cur.fetchall()
        finally:
            cur.close()
        return [row[0] for row in rows]


def _pick(item: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in item:
            return item[key]
    return None
