from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from jobs import embedding_build_job  # noqa: E402
from repos.apl.item_embedding_repo import EmbeddingSourceRow  # noqa: E402


class FakeEmbeddingRepo:
    last_instance = None

    def __init__(self, *, conn) -> None:
        self.conn = conn
        self.upsert_calls = []
        FakeEmbeddingRepo.last_instance = self

    def fetch_diff_sources(self, *, model: str):
        assert model == "text-embedding-3-small"
        return [
            EmbeddingSourceRow(
                item_id="item-1", source_text="source", source_hash="hash-1"
            )
        ]

    def upsert_embedding(self, *, item_id, model, embedding, source_hash):
        self.upsert_calls.append((item_id, model, embedding, source_hash))
        return "inserted"


class FakeOpenAIClient:
    def __init__(self, *, config) -> None:
        self.config = config
        self.calls = []

    def embed(self, *, source_text: str):
        self.calls.append(source_text)
        return [0.1, 0.2, 0.3]


@contextmanager
def fake_db_connection(*, database_url: str):
    assert database_url == "postgres://example"
    yield object()


@pytest.mark.unit
def test_run_job_inserts_embeddings(monkeypatch) -> None:
    monkeypatch.setattr(embedding_build_job, "ItemEmbeddingRepo", FakeEmbeddingRepo)
    monkeypatch.setattr(embedding_build_job, "OpenAIClient", FakeOpenAIClient)
    monkeypatch.setattr(embedding_build_job, "db_connection", fake_db_connection)

    result = embedding_build_job.run_job(
        env="dev",
        database_url="postgres://example",
        api_key="test-key",
        model="text-embedding-3-small",
        timeout_sec=1.0,
        max_retries=1,
        backoff_base_sec=0.1,
        run_id="run-1",
        dry_run=False,
    )

    assert result["total_targets"] == 1
    assert result["upsert_inserted"] == 1
    repo = FakeEmbeddingRepo.last_instance
    assert repo.upsert_calls[0][0] == "item-1"
    assert repo.upsert_calls[0][1] == "text-embedding-3-small"


@pytest.mark.unit
def test_run_job_skips_on_dry_run(monkeypatch) -> None:
    monkeypatch.setattr(embedding_build_job, "ItemEmbeddingRepo", FakeEmbeddingRepo)
    monkeypatch.setattr(embedding_build_job, "OpenAIClient", FakeOpenAIClient)
    monkeypatch.setattr(embedding_build_job, "db_connection", fake_db_connection)

    result = embedding_build_job.run_job(
        env="dev",
        database_url="postgres://example",
        api_key="test-key",
        model="text-embedding-3-small",
        timeout_sec=1.0,
        max_retries=1,
        backoff_base_sec=0.1,
        run_id="run-1",
        dry_run=True,
    )

    assert result["total_targets"] == 1
    assert result["skipped_no_diff"] == 1
