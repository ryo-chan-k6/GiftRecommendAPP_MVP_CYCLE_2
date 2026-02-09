from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class OpenAIClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAIClientConfig:
    api_key: str
    model: str
    timeout_sec: float = 30.0
    max_retries: int = 5
    backoff_base_sec: float = 1.0


class OpenAIClient:
    def __init__(self, *, config: OpenAIClientConfig) -> None:
        self._config = config

    def embed(self, *, source_text: str) -> Sequence[float]:
        payload = {"model": self._config.model, "input": source_text}
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/embeddings", data=body, headers=headers, method="POST"
        )

        for attempt in range(1, self._config.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self._config.timeout_sec) as res:
                    raw = res.read().decode("utf-8")
                    payload = json.loads(raw)
                    return _extract_embedding(payload)
            except urllib.error.HTTPError as exc:
                status = exc.code
                if status in (401, 403):
                    raise OpenAIClientError(f"OpenAI auth error: {status}") from exc
                if status == 429 or 500 <= status < 600:
                    _sleep_backoff(exc.headers.get("Retry-After"), attempt, self._config)
                    continue
                raise OpenAIClientError(f"OpenAI API error: {status}") from exc
            except urllib.error.URLError as exc:
                _sleep_backoff(None, attempt, self._config)
                continue

        raise OpenAIClientError("OpenAI API retries exhausted")


def _extract_embedding(payload: Mapping[str, Any]) -> Sequence[float]:
    data = payload.get("data")
    if isinstance(data, list) and data:
        embedding = data[0].get("embedding") if isinstance(data[0], dict) else None
        if isinstance(embedding, list):
            return [float(value) for value in embedding]
    raise OpenAIClientError("Invalid embedding response")


def _sleep_backoff(retry_after: str | None, attempt: int, config: OpenAIClientConfig) -> None:
    if retry_after:
        try:
            delay = float(retry_after)
        except ValueError:
            delay = config.backoff_base_sec * (2 ** (attempt - 1))
    else:
        delay = config.backoff_base_sec * (2 ** (attempt - 1))
    time.sleep(delay)
