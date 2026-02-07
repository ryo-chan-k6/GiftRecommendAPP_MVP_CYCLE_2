from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from repos.apl.tag_repo import TagRepo  # noqa: E402


class FakeCursor:
    def __init__(self, *, fetchone_values=None) -> None:
        self._fetchone_values = list(fetchone_values or [])
        self.executed = []
        self.closed = False

    def execute(self, query: str, params=None) -> None:
        self.executed.append((query, params))

    def fetchone(self):
        if not self._fetchone_values:
            return None
        return self._fetchone_values.pop(0)

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self) -> None:
        self.committed = True


@pytest.mark.unit
def test_upsert_tag_group_inserts() -> None:
    cursor = FakeCursor(fetchone_values=[("group-uuid",)])
    conn = FakeConnection(cursor)
    repo = TagRepo(conn=conn)
    normalized = {"tagGroup": {"tagGroupId": 1000, "tagGroupName": "Sweets", "tags": []}}

    affected = repo.upsert_tag_group(normalized_tag=normalized)

    assert affected == 1
    assert conn.committed is True
    assert cursor.executed
    assert "insert into apl.tag_group" in cursor.executed[0][0]


@pytest.mark.unit
def test_upsert_tag_inserts_parent_then_child() -> None:
    cursor = FakeCursor(
        fetchone_values=[
            ("group-uuid",),
            ("parent-uuid", True),
            ("child-uuid", True),
        ]
    )
    conn = FakeConnection(cursor)
    repo = TagRepo(conn=conn)
    normalized = {
        "tagGroup": {
            "tagGroupId": 1000,
            "tagGroupName": "Sweets",
            "tags": [
                {"tagId": 200, "tagName": "Parent", "parentTagId": 0},
                {"tagId": 201, "tagName": "Child", "parentTagId": 200},
            ],
        }
    }

    affected = repo.upsert_tag(normalized_tag=normalized)

    assert affected == 2
    assert conn.committed is True
    assert len(cursor.executed) == 3
    assert "select id from apl.tag_group" in cursor.executed[0][0]
    assert "insert into apl.tag" in cursor.executed[1][0]
    assert "insert into apl.tag" in cursor.executed[2][0]


@pytest.mark.unit
def test_upsert_tag_skips_when_parent_missing() -> None:
    cursor = FakeCursor(fetchone_values=[("group-uuid",)])
    conn = FakeConnection(cursor)
    repo = TagRepo(conn=conn)
    normalized = {
        "tagGroup": {
            "tagGroupId": 1000,
            "tagGroupName": "Sweets",
            "tags": [{"tagId": 201, "tagName": "Child", "parentTagId": 200}],
        }
    }

    affected = repo.upsert_tag(normalized_tag=normalized)

    assert affected == 0
    assert conn.committed is True
    assert len(cursor.executed) == 1
    assert "select id from apl.tag_group" in cursor.executed[0][0]
