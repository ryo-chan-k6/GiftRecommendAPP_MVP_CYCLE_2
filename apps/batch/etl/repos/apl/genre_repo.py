from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


class Cursor(Protocol):
    def execute(self, query: str, params: Sequence[object] | None = None) -> None: ...
    def fetchone(self) -> Sequence[object] | None: ...
    @property
    def rowcount(self) -> int: ...
    def close(self) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> None: ...


class GenreRepo:
    def __init__(self, *, conn: Connection) -> None:
        self._conn = conn

    def upsert_genre(self, *, normalized_genre: Mapping[str, Any]) -> int:
        current = _pick_mapping(normalized_genre, "current") or normalized_genre
        genre_id = _pick(current, ("genreId", "genre_id", "rakuten_genre_id"))
        name = _pick(current, ("genreName", "genre_name", "name"))
        level = _pick(current, ("genreLevel", "genre_level", "level"))

        cur = self._conn.cursor()
        try:
            parent_id = self._resolve_parent_id(cur, normalized_genre, current)
            if parent_id is None and _pick_parents(normalized_genre):
                return 0

            current_id = self._upsert_genre_row(
                cur, genre_id=genre_id, name=name, level=level, parent_id=parent_id
            )
            if current_id is None:
                return 0
        finally:
            cur.close()
        self._conn.commit()
        return 1

    def _resolve_parent_id(
        self, cur: Cursor, normalized_genre: Mapping[str, Any], current: Mapping[str, Any]
    ) -> str | None:
        parent_id = None
        parents = _pick_parents(normalized_genre)
        if parents:
            for parent in parents:
                parent_genre_id = _pick(parent, ("genreId", "genre_id", "rakuten_genre_id"))
                parent_name = _pick(parent, ("genreName", "genre_name", "name"))
                parent_level = _pick(parent, ("genreLevel", "genre_level", "level"))
                if parent_genre_id is None:
                    return None
                parent_id = self._upsert_genre_row(
                    cur,
                    genre_id=parent_genre_id,
                    name=parent_name,
                    level=parent_level,
                    parent_id=parent_id,
                )
                if parent_id is None:
                    return None
            return parent_id
        return None

    def _upsert_genre_row(
        self,
        cur: Cursor,
        *,
        genre_id: int,
        name: str | None,
        level: int | None,
        parent_id: str | None,
    ) -> str | None:
        sql = (
            "insert into apl.genre "
            "(rakuten_genre_id, name, level, parent_id, created_at, updated_at) "
            "values (%s, %s, %s, %s, now(), now()) "
            "on conflict (rakuten_genre_id) do update set "
            "name = excluded.name, "
            "level = excluded.level, "
            "parent_id = excluded.parent_id, "
            "updated_at = now() "
            "returning id"
        )
        cur.execute(sql, (genre_id, name, level, parent_id))
        row = cur.fetchone()
        if not row:
            return None
        return row[0]



def _pick(source: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in source:
            return source[key]
    return None


def _pick_mapping(source: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = source.get(key)
    if isinstance(value, Mapping):
        return value
    return None


def _pick_parents(normalized_genre: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    parents = normalized_genre.get("parents")
    if not isinstance(parents, list) or not parents:
        return []
    return [parent for parent in parents if isinstance(parent, Mapping)]


