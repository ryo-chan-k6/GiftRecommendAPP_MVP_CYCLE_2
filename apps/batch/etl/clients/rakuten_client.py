from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional


class RakutenClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class RakutenClientConfig:
    application_id: str
    affiliate_id: Optional[str]
    timeout_sec: float = 10.0
    max_attempts: int = 5
    base_backoff_sec: float = 1.0


class RakutenClient:
    def __init__(self, *, config: RakutenClientConfig) -> None:
        self._config = config

    def fetch_ranking(self, *, genre_id: int) -> Mapping[str, Any]:
        return self._get_json(
            endpoint="https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20220601",
            params={"genreId": genre_id},
        )

    def fetch_item(self, *, item_code: str) -> Mapping[str, Any]:
        return self._get_json(
            endpoint="https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601",
            params={"itemCode": item_code, "hits": 1, "page": 1},
        )

    def fetch_genre(self, *, genre_id: int) -> Mapping[str, Any]:
        return self._get_json(
            endpoint="https://app.rakuten.co.jp/services/api/IchibaGenre/Search/20140222",
            params={"genreId": genre_id},
        )

    def fetch_tag(self, *, tag_id: int) -> Mapping[str, Any]:
        return self._get_json(
            endpoint="https://app.rakuten.co.jp/services/api/IchibaTag/Search/20140222",
            params={"tagId": tag_id},
        )

    def _get_json(self, *, endpoint: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        base_params = {
            "applicationId": self._config.application_id,
            "format": "json",
            "formatVersion": 2,
        }
        if self._config.affiliate_id:
            base_params["affiliateId"] = self._config.affiliate_id

        merged_params = {**base_params, **params}
        query = urllib.parse.urlencode(merged_params)
        url = f"{endpoint}?{query}"

        for attempt in range(1, self._config.max_attempts + 1):
            try:
                with urllib.request.urlopen(url, timeout=self._config.timeout_sec) as res:
                    payload = res.read().decode("utf-8")
                    return json.loads(payload)
            except urllib.error.HTTPError as exc:
                status = exc.code
                if status in (401, 403):
                    raise RakutenClientError(f"Rakuten API auth error: {status}") from exc
                if status == 429 or 500 <= status < 600:
                    self._sleep_backoff(exc.headers.get("Retry-After"), attempt)
                    continue
                raise RakutenClientError(f"Rakuten API error: {status}") from exc
            except urllib.error.URLError as exc:
                self._sleep_backoff(None, attempt)
                continue

        raise RakutenClientError("Rakuten API retries exhausted")

    def _sleep_backoff(self, retry_after: Optional[str], attempt: int) -> None:
        if retry_after:
            try:
                delay = float(retry_after)
            except ValueError:
                delay = self._config.base_backoff_sec * (2 ** (attempt - 1))
        else:
            delay = self._config.base_backoff_sec * (2 ** (attempt - 1))
        time.sleep(delay)
