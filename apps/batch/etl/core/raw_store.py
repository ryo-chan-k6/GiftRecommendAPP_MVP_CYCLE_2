from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import boto3


@dataclass(frozen=True)
class RawPutResult:
    s3_key: str
    etag: Optional[str]
    saved_at: datetime


class RawStore:
    def __init__(self, *, region: str) -> None:
        self._client = boto3.client("s3", region_name=region)

    def build_key(self, *, source: str, entity: str, source_id: str, content_hash: str) -> str:
        return f"raw/source={source}/entity={entity}/source_id={source_id}/hash={content_hash}.json"

    def put_json(self, *, bucket: str, s3_key: str, body: Mapping[str, Any]) -> RawPutResult:
        payload = json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        response = self._client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=payload.encode("utf-8"),
            ContentType="application/json",
        )
        etag = response.get("ETag")
        saved_at = datetime.now(timezone.utc)
        return RawPutResult(s3_key=s3_key, etag=etag, saved_at=saved_at)
