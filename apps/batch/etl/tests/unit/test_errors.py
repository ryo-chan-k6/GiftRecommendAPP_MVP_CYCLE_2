from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core import errors  # noqa: E402


@pytest.mark.unit
def test_rakuten_errors_inherit_base() -> None:
    assert issubclass(errors.RakutenError, errors.EtlError)
    assert issubclass(errors.RakutenRateLimitError, errors.RakutenError)
    assert issubclass(errors.RakutenTransientError, errors.RakutenError)
    assert issubclass(errors.RakutenClientError, errors.RakutenError)


@pytest.mark.unit
def test_s3_errors_inherit_base() -> None:
    assert issubclass(errors.S3Error, errors.EtlError)
    assert issubclass(errors.S3TransientError, errors.S3Error)
    assert issubclass(errors.S3AuthError, errors.S3Error)


@pytest.mark.unit
def test_db_errors_inherit_base() -> None:
    assert issubclass(errors.DbError, errors.EtlError)
    assert issubclass(errors.DbTransientError, errors.DbError)
    assert issubclass(errors.DbLogicError, errors.DbError)
