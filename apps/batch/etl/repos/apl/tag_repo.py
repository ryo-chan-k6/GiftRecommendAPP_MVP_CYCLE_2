from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


class Cursor(Protocol):
    def execute(self, query: str, params: Sequence[object] | None = None) -> None: ...
    def fetchone(self) -> Sequence[object] | None: ...
    def close(self) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> None: ...


class TagRepo:
    def __init__(self, *, conn: Connection) -> None:
        self._conn = conn

    def upsert_tag_group(self, *, normalized_tag: Mapping[str, Any]) -> int:
        tag_group = _pick_tag_group(normalized_tag)
        if not tag_group:
            return 0
        group_id = _pick(
            tag_group, ("tagGroupId", "tag_group_id", "rakuten_tag_group_id")
        )
        name = _pick(tag_group, ("tagGroupName", "tag_group_name", "name"))
        if group_id is None:
            return 0

        sql = (
            "insert into apl.tag_group "
            "(rakuten_tag_group_id, name, created_at, updated_at) "
            "values (%s, %s, now(), now()) "
            "on conflict (rakuten_tag_group_id) do update set "
            "name = excluded.name, "
            "updated_at = now() "
            "returning id"
        )
        cur = self._conn.cursor()
        try:
            cur.execute(sql, (group_id, name))
            row = cur.fetchone()
        finally:
            cur.close()
        if not row:
            return 0
        self._conn.commit()
        return 1

    def upsert_tag(self, *, normalized_tag: Mapping[str, Any]) -> int:
        tag_group = _pick_tag_group(normalized_tag)
        if not tag_group:
            return 0
        group_id = _pick(
            tag_group, ("tagGroupId", "tag_group_id", "rakuten_tag_group_id")
        )
        if group_id is None:
            return 0
        tags = _pick_tags(tag_group, normalized_tag)
        if not tags:
            return 0

        cur = self._conn.cursor()
        try:
            group_row_id = _fetch_group_id(cur, group_id)
            if group_row_id is None:
                return 0

            tag_map = {
                _pick(tag, ("tagId", "tag_id", "rakuten_tag_id")): tag
                for tag in tags
                if isinstance(tag, Mapping)
                and _pick(tag, ("tagId", "tag_id", "rakuten_tag_id")) is not None
            }
            visited: dict[int, str | None] = {}
            visiting: set[int] = set()
            inserted = 0
            for tag_id in tag_map:
                _, added = _ensure_tag(
                    cur=cur,
                    tag_id=tag_id,
                    group_row_id=group_row_id,
                    tag_map=tag_map,
                    visited=visited,
                    visiting=visiting,
                )
                inserted += added
        finally:
            cur.close()
        self._conn.commit()
        return inserted


def _fetch_group_id(cur: Cursor, group_id: int) -> str | None:
    sql = "select id from apl.tag_group where rakuten_tag_group_id = %s"
    cur.execute(sql, (group_id,))
    row = cur.fetchone()
    if not row:
        return None
    return row[0]


def _ensure_tag(
    *,
    cur: Cursor,
    tag_id: int,
    group_row_id: str,
    tag_map: Mapping[int, Mapping[str, Any]],
    visited: dict[int, str | None],
    visiting: set[int],
) -> tuple[str | None, int]:
    if tag_id in visited:
        return visited[tag_id], 0
    if tag_id in visiting:
        visited[tag_id] = None
        return None, 0
    visiting.add(tag_id)
    tag = tag_map[tag_id]
    parent_tag_id = _pick(tag, ("parentTagId", "parent_tag_id"))
    parent_id = None
    inserted = 0
    if parent_tag_id not in (None, 0):
        if parent_tag_id not in tag_map:
            visiting.remove(tag_id)
            visited[tag_id] = None
            return None, 0
        parent_id, parent_added = _ensure_tag(
            cur=cur,
            tag_id=parent_tag_id,
            group_row_id=group_row_id,
            tag_map=tag_map,
            visited=visited,
            visiting=visiting,
        )
        inserted += parent_added
        if parent_id is None:
            visiting.remove(tag_id)
            visited[tag_id] = None
            return None, inserted

    sql = (
        "insert into apl.tag "
        "(rakuten_tag_id, name, group_id, parent_id, created_at, updated_at) "
        "values (%s, %s, %s, %s, now(), now()) "
        "on conflict (rakuten_tag_id) do update set "
        "name = excluded.name, "
        "group_id = excluded.group_id, "
        "parent_id = excluded.parent_id, "
        "updated_at = now() "
        "returning id, (xmax = 0) as inserted"
    )
    name = _pick(tag, ("tagName", "tag_name", "name"))
    cur.execute(sql, (tag_id, name, group_row_id, parent_id))
    row = cur.fetchone()
    visiting.remove(tag_id)
    tag_row_id = row[0] if row else None
    was_inserted = bool(row[1]) if row and len(row) > 1 else False
    visited[tag_id] = tag_row_id
    if was_inserted:
        inserted += 1
    return tag_row_id, inserted


def _pick(source: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in source:
            return source[key]
    return None


def _pick_tag_group(normalized_tag: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for key in ("tagGroup", "tag_group"):
        value = normalized_tag.get(key)
        if isinstance(value, Mapping):
            return value
    if isinstance(normalized_tag.get("tagGroupId"), (int, str)):
        return normalized_tag
    return None


def _pick_tags(
    tag_group: Mapping[str, Any], normalized_tag: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    for key in ("tags",):
        value = tag_group.get(key)
        if isinstance(value, list):
            return _unwrap_tags(value)
    value = normalized_tag.get("tags")
    if isinstance(value, list):
        return _unwrap_tags(value)
    return []


def _unwrap_tags(tags_raw: list) -> list[Mapping[str, Any]]:
    """Unwrap tags[].tag structure. Handles both {tag: {tagId,...}} and flat {tagId,...}."""
    result: list[Mapping[str, Any]] = []
    for t in tags_raw:
        if not isinstance(t, Mapping):
            continue
        inner = t.get("tag") if isinstance(t.get("tag"), Mapping) else t
        if (
            isinstance(inner, Mapping)
            and _pick(inner, ("tagId", "tag_id", "rakuten_tag_id")) is not None
        ):
            result.append(inner)
    return result
