from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import repos.db as db  # noqa: E402


class FakeConnection:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


@pytest.mark.unit
def test_transaction_commits_on_success() -> None:
    conn = FakeConnection()

    with db.transaction(conn):
        pass

    assert conn.committed is True
    assert conn.rolled_back is False


@pytest.mark.unit
def test_transaction_rolls_back_on_error() -> None:
    conn = FakeConnection()

    with pytest.raises(ValueError):
        with db.transaction(conn):
            raise ValueError("boom")

    assert conn.committed is False
    assert conn.rolled_back is True


@pytest.mark.unit
def test_db_connection_closes_connection(monkeypatch) -> None:
    conn = FakeConnection()

    def fake_connect(*, database_url: str):
        assert database_url == "postgres://example"
        return conn

    monkeypatch.setattr(db, "connect", fake_connect)

    with db.db_connection(database_url="postgres://example") as result:
        assert result is conn
        assert conn.closed is False

    assert conn.closed is True
