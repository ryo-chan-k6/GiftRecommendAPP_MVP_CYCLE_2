from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from services.context import JobContext  # noqa: E402
from services import policy  # noqa: E402


class FakeTargetGenreConfigRepo:
    def __init__(self, genre_ids: list[int]) -> None:
        self.genre_ids = genre_ids

    def fetch_enabled_genre_ids(self) -> list[int]:
        return self.genre_ids


class FakeRankSnapshotRepo:
    def __init__(self, item_codes: list[str]) -> None:
        self.item_codes = item_codes
        self.calls: list[datetime] = []

    def fetch_distinct_item_codes_since(self, *, since: datetime) -> list[str]:
        self.calls.append(since)
        return self.item_codes


class FakeStagingRepo:
    def __init__(self, source_ids: list[str]) -> None:
        self.source_ids = source_ids
        self.calls: list[datetime] = []

    def fetch_item_source_ids_since(self, *, since: datetime) -> list[str]:
        self.calls.append(since)
        return self.source_ids


class FakeItemRepo:
    def __init__(self, genre_ids: list[int]) -> None:
        self.genre_ids = genre_ids
        self.calls: list[list[str]] = []

    def fetch_distinct_genre_ids_by_source_ids(self, source_ids: list[str]) -> list[int]:
        self.calls.append(source_ids)
        return self.genre_ids


class FakeItemTagRepo:
    def __init__(self, tag_ids: list[int]) -> None:
        self.tag_ids = tag_ids
        self.calls: list[list[str]] = []

    def fetch_distinct_tag_ids_by_source_ids(self, source_ids: list[str]) -> list[int]:
        self.calls.append(source_ids)
        return self.tag_ids


@pytest.mark.unit
def test_targets_ranking_genre_ids_returns_enabled_ids() -> None:
    ctx = JobContext(
        job_id="job-r-01",
        env="dev",
        run_id="run-1",
        job_start_at=datetime.now(timezone.utc),
    )
    repo = FakeTargetGenreConfigRepo([1, 2, 3])

    result = list(policy.targets_ranking_genre_ids(ctx, target_genre_config_repo=repo))

    assert result == [1, 2, 3]


@pytest.mark.unit
def test_targets_item_codes_uses_job_start_at() -> None:
    started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    expected_since = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ctx = JobContext(
        job_id="job-i-01",
        env="dev",
        run_id="run-1",
        job_start_at=started_at,
    )
    repo = FakeRankSnapshotRepo(["a", "b"])

    result = list(policy.targets_item_codes(ctx, rank_snapshot_repo=repo))

    assert result == ["a", "b"]
    assert repo.calls == [expected_since]


@pytest.mark.unit
def test_targets_genre_ids_from_today_items_short_circuit_on_empty() -> None:
    started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    expected_since = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ctx = JobContext(
        job_id="job-g-01",
        env="dev",
        run_id="run-1",
        job_start_at=started_at,
    )
    staging_repo = FakeStagingRepo([])
    item_repo = FakeItemRepo([100])

    result = list(
        policy.targets_genre_ids_from_today_items(
            ctx, staging_repo=staging_repo, item_repo=item_repo
        )
    )

    assert result == []
    assert staging_repo.calls == [expected_since]
    assert item_repo.calls == []


@pytest.mark.unit
def test_targets_tag_ids_from_today_items_uses_source_ids() -> None:
    started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    expected_since = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ctx = JobContext(
        job_id="job-t-01",
        env="dev",
        run_id="run-1",
        job_start_at=started_at,
    )
    staging_repo = FakeStagingRepo(["s1", "s2"])
    item_tag_repo = FakeItemTagRepo([10, 20])

    result = list(
        policy.targets_tag_ids_from_today_items(
            ctx, staging_repo=staging_repo, item_tag_repo=item_tag_repo
        )
    )

    assert result == [10, 20]
    assert staging_repo.calls == [expected_since]
    assert item_tag_repo.calls == [["s1", "s2"]]
