from __future__ import annotations

from typing import Protocol, Sequence


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


class ItemTagRepo:
    def __init__(self, *, conn: Connection) -> None:
        self._conn = conn

    def sync_item_tags(self, *, item_id: str, rakuten_tag_ids: Sequence[int]) -> int:
        delete_sql = "delete from apl.item_tag where item_id = %s"
        insert_sql = (
            "insert into apl.item_tag (item_id, rakuten_tag_id) "
            "values (%s, %s) "
            "on conflict (item_id, rakuten_tag_id) do nothing"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(delete_sql, (item_id,))
            if rakuten_tag_ids:
                params = [(item_id, tag_id) for tag_id in rakuten_tag_ids]
                cur.executemany(insert_sql, params)
                affected = cur.rowcount
            else:
                affected = 0
        finally:
            cur.close()
        self._conn.commit()
        return affected

    def fetch_distinct_tag_ids_by_source_ids(self, source_ids: Sequence[str]) -> Sequence[int]:
        if not source_ids:
            return []
        sql = (
            "select distinct it.rakuten_tag_id "
            "from apl.item_tag it "
            "join apl.item i on i.id = it.item_id "
            "where i.rakuten_item_code = any(%s) "
            "and it.rakuten_tag_id is not null "
            "order by it.rakuten_tag_id"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, (list(source_ids),))
            rows = cur.fetchall()
        finally:
            cur.close()
        return [row[0] for row in rows]
