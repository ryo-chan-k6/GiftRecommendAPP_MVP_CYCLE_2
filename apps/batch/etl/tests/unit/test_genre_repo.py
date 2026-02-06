from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from repos.apl.genre_repo import GenreRepo  # noqa: E402


class FakeCursor:
    def __init__(self, *, fetchone_values=None, rowcount=1) -> None:
        self._fetchone_values = list(fetchone_values or [])
        self.executed = []
        self.rowcount = rowcount
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
def test_upsert_genre_without_parent() -> None:
    cursor = FakeCursor(fetchone_values=[("genre-uuid",)])
    repo = GenreRepo(conn=FakeConnection(cursor))
    normalized = {
        "current": {"genreId": 100, "genreName": "Root", "genreLevel": 1},
        "parents": [],
    }

    affected = repo.upsert_genre(normalized_genre=normalized)

    assert affected == 1
    assert cursor.executed
    sql = cursor.executed[0][0]
    assert "insert into apl.genre" in sql


@pytest.mark.unit
def test_upsert_genre_with_parent_found() -> None:
    cursor = FakeCursor(fetchone_values=[("parent-uuid",), ("child-uuid",)])
    repo = GenreRepo(conn=FakeConnection(cursor))
    normalized = {
        "current": {"genreId": 200, "genreName": "Child", "genreLevel": 2},
        "parents": [{"genreId": 100, "genreName": "Root", "genreLevel": 1}],
    }

    affected = repo.upsert_genre(normalized_genre=normalized)

    assert affected == 1
    assert len(cursor.executed) == 2
    assert "insert into apl.genre" in cursor.executed[0][0]
    assert "insert into apl.genre" in cursor.executed[1][0]


@pytest.mark.unit
def test_upsert_genre_skips_when_parent_missing() -> None:
    cursor = FakeCursor(fetchone_values=[None])
    conn = FakeConnection(cursor)
    repo = GenreRepo(conn=conn)
    normalized = {
        "current": {"genreId": 200, "genreName": "Child", "genreLevel": 2},
        "parents": [{"genreId": 999, "genreName": "Missing", "genreLevel": 1}],
    }

    affected = repo.upsert_genre(normalized_genre=normalized)

    assert affected == 0
    assert conn.committed is False
    assert len(cursor.executed) == 1
    assert "insert into apl.genre" in cursor.executed[0][0]
