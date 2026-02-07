from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from repos.apl.target_genre_config_repo import TargetGenreConfigRepo  # noqa: E402


class FakeCursor:
    def __init__(self, *, fetchall_value=None) -> None:
        self.fetchall_value = fetchall_value or []
        self.executed = []
        self.closed = False

    def execute(self, query: str, params=None) -> None:
        self.executed.append((query, params))

    def fetchall(self):
        return self.fetchall_value

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self):
        return self._cursor


@pytest.mark.unit
def test_fetch_enabled_genre_ids_returns_ids() -> None:
    cursor = FakeCursor(fetchall_value=[(100,), (200,)])
    repo = TargetGenreConfigRepo(conn=FakeConnection(cursor))

    result = repo.fetch_enabled_genre_ids()

    assert result == [100, 200]
    assert cursor.executed
    assert "from apl.target_genre_config" in cursor.executed[0][0]
