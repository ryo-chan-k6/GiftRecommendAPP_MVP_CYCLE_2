from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    env: str
    database_url: str
    rakuten_app_id: str
    rakuten_affiliate_id: str | None
    s3_bucket_raw: str
    aws_region: str


def load_config() -> AppConfig:
    env = _require("ENV")
    database_url = _require("DATABASE_URL")
    rakuten_app_id = _require("RAKUTEN_APP_ID")
    rakuten_affiliate_id = os.getenv("RAKUTEN_AFFILIATE_ID")
    aws_region = _require("AWS_REGION")
    s3_bucket_raw = _require(_bucket_env_name(env))
    return AppConfig(
        env=env,
        database_url=database_url,
        rakuten_app_id=rakuten_app_id,
        rakuten_affiliate_id=rakuten_affiliate_id,
        s3_bucket_raw=s3_bucket_raw,
        aws_region=aws_region,
    )


def _bucket_env_name(env: str) -> str:
    env_key = env.upper()
    if env_key not in {"DEV", "PROD"}:
        raise ValueError("ENV must be 'dev' or 'prod'")
    return f"S3_BUCKET_RAW_{env_key}"


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value
