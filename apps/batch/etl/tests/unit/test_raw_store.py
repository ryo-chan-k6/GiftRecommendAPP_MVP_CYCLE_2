from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pytest
from botocore.stub import Stubber

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.raw_store import RawStore  # noqa: E402


@pytest.mark.unit
def test_build_key_uses_expected_format() -> None:
    store = RawStore(region="ap-northeast-1")

    key = store.build_key(
        source="rakuten",
        entity="item",
        source_id="shop:123",
        content_hash="hash123",
    )

    assert key == "raw/source=rakuten/entity=item/source_id=shop:123/hash=hash123.json"


@pytest.mark.unit
def test_put_json_returns_etag_and_saved_at() -> None:
    store = RawStore(region="ap-northeast-1")
    stubber = Stubber(store._client)
    stubber.add_response(
        "put_object",
        {"ETag": '"etag-value"'},
        {
            "Bucket": "bucket",
            "Key": "path/to.json",
            "Body": b'{"a":1}',
            "ContentType": "application/json",
        },
    )

    with stubber:
        result = store.put_json(bucket="bucket", s3_key="path/to.json", body={"a": 1})

    assert result.etag == '"etag-value"'
    assert result.s3_key == "path/to.json"
    assert isinstance(result.saved_at, datetime)
    assert result.saved_at.tzinfo == timezone.utc
