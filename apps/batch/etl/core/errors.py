from __future__ import annotations


class EtlError(Exception):
    """Base class for ETL domain errors."""


class RakutenError(EtlError):
    """Rakuten API related errors."""


class RakutenRateLimitError(RakutenError):
    """HTTP 429 or rate limit responses."""


class RakutenTransientError(RakutenError):
    """HTTP 5xx, timeout, or temporary network errors."""


class RakutenClientError(RakutenError):
    """HTTP 4xx errors excluding 429."""


class S3Error(EtlError):
    """S3 related errors."""


class S3TransientError(S3Error):
    """S3 5xx or timeout errors."""


class S3AuthError(S3Error):
    """S3 403 or permission errors."""


class DbError(EtlError):
    """Database related errors."""


class DbTransientError(DbError):
    """Deadlock, serialization, or timeout errors."""


class DbLogicError(DbError):
    """Constraint violations or data logic errors."""
