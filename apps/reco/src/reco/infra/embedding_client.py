import json
import os
import urllib.request
from typing import List

DEFAULT_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def embed_text(text: str, model: str | None = None) -> List[float]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    payload = json.dumps(
        {
            "model": model or DEFAULT_EMBEDDING_MODEL,
            "input": text,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
        data = json.loads(body)

    embedding = data["data"][0]["embedding"]
    return [float(v) for v in embedding]
