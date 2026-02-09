from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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
class EmbeddingSourceRow:
    item_id: str
    source_text: str
    source_hash: str


class ItemEmbeddingRepo:
    def __init__(self, *, conn: Connection) -> None:
        self._conn = conn

    def fetch_diff_sources(self, *, model: str) -> Sequence[EmbeddingSourceRow]:
        sql_path = (
            Path(__file__).resolve().parents[2]
            / "sql"
            / "common"
            / "embedding_source_diff_select.sql"
        )
        sql = sql_path.read_text(encoding="utf-8")
        cur = self._conn.cursor()
        try:
            cur.execute(sql, (model,))
            rows = cur.fetchall()
        finally:
            cur.close()
        return [
            EmbeddingSourceRow(item_id=str(row[0]), source_text=row[1], source_hash=row[2])
            for row in rows
        ]

    def upsert_embedding(
        self,
        *,
        item_id: str,
        model: str,
        embedding: Sequence[float],
        source_hash: str,
    ) -> str:
        sql = (
            "insert into apl.item_embedding "
            "(item_id, model, embedding, source_hash, updated_at) "
            "values (%s, %s, %s, %s, now()) "
            "on conflict (item_id, model) do update set "
            "embedding = excluded.embedding, "
            "source_hash = excluded.source_hash, "
            "updated_at = now() "
            "where apl.item_embedding.source_hash is distinct from excluded.source_hash "
            "returning (xmax = 0) as inserted"
        )
        embedding_value = _format_embedding(embedding)
        cur = self._conn.cursor()
        try:
            cur.execute(sql, (item_id, model, embedding_value, source_hash))
            row = cur.fetchone()
        finally:
            cur.close()
        self._conn.commit()
        if not row:
            return "skipped"
        return "inserted" if bool(row[0]) else "updated"


def _format_embedding(values: Sequence[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
