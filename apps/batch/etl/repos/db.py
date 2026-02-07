from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator


def connect(*, database_url: str) -> Any:
    try:
        import psycopg2
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise ImportError(
            "psycopg2 is required for database connections"
        ) from exc
    return psycopg2.connect(database_url)


@contextmanager
def db_connection(*, database_url: str) -> Iterator[Any]:
    conn = connect(database_url=database_url)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: Any) -> Iterator[Any]:
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
