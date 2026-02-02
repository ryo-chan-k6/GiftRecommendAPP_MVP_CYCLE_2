from __future__ import annotations

import io
import sys
from email.message import Message
from pathlib import Path
from unittest import mock
import urllib.error

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from clients.rakuten_client import (  # noqa: E402
    RakutenClient,
    RakutenClientConfig,
    RakutenClientError,
)


def _make_response(payload: str) -> mock.MagicMock:
    response = mock.MagicMock()
    response.read.return_value = payload.encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


@pytest.mark.unit
def test_fetch_item_success_returns_json() -> None:
    client = RakutenClient(
        config=RakutenClientConfig(application_id="app", affiliate_id=None)
    )
    response = _make_response('{"items":[{"itemCode":"shop:1"}]}')

    with mock.patch("urllib.request.urlopen", return_value=response):
        result = client.fetch_item(item_code="shop:1")

    assert result["items"][0]["itemCode"] == "shop:1"


@pytest.mark.unit
def test_fetch_ranking_raises_on_auth_error() -> None:
    client = RakutenClient(
        config=RakutenClientConfig(application_id="app", affiliate_id=None)
    )
    error = urllib.error.HTTPError(
        url="http://example",
        code=401,
        msg="Unauthorized",
        hdrs=Message(),
        fp=io.BytesIO(),
    )

    with mock.patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(RakutenClientError):
            client.fetch_ranking(genre_id=1)


@pytest.mark.unit
def test_fetch_tag_retries_on_429_then_succeeds() -> None:
    client = RakutenClient(
        config=RakutenClientConfig(
            application_id="app",
            affiliate_id=None,
            max_attempts=3,
            base_backoff_sec=0.0,
        )
    )
    headers = Message()
    headers["Retry-After"] = "0"
    error = urllib.error.HTTPError(
        url="http://example",
        code=429,
        msg="Too Many Requests",
        hdrs=headers,
        fp=io.BytesIO(),
    )
    response = _make_response('{"items":[{"tagId":1}]}')

    with mock.patch("urllib.request.urlopen", side_effect=[error, response]) as mocked:
        with mock.patch("time.sleep") as sleeper:
            result = client.fetch_tag(tag_id=1)

    assert result["items"][0]["tagId"] == 1
    assert mocked.call_count == 2
    sleeper.assert_called()


@pytest.mark.unit
def test_fetch_genre_retries_then_exhausts() -> None:
    client = RakutenClient(
        config=RakutenClientConfig(
            application_id="app",
            affiliate_id=None,
            max_attempts=2,
            base_backoff_sec=0.0,
        )
    )
    error = urllib.error.URLError("timeout")

    with mock.patch("urllib.request.urlopen", side_effect=error):
        with mock.patch("time.sleep"):
            with pytest.raises(RakutenClientError):
                client.fetch_genre(genre_id=1)
