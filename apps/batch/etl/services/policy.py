from __future__ import annotations

from datetime import datetime
from typing import Iterable, Protocol, Sequence

from services.context import JobContext


class TargetGenreConfigRepo(Protocol):
    def fetch_enabled_genre_ids(self) -> Sequence[int]: ...


class RankSnapshotRepo(Protocol):
    def fetch_distinct_item_codes_since(self, *, since: datetime) -> Sequence[str]: ...


class StagingRepo(Protocol):
    def fetch_item_source_ids_since(self, *, since: datetime) -> Sequence[str]: ...


class ItemRepo(Protocol):
    def fetch_distinct_genre_ids_by_source_ids(self, source_ids: Sequence[str]) -> Sequence[int]: ...


class ItemTagRepo(Protocol):
    def fetch_distinct_tag_ids_by_source_ids(self, source_ids: Sequence[str]) -> Sequence[int]: ...


def targets_ranking_genre_ids(
    ctx: JobContext, *, target_genre_config_repo: TargetGenreConfigRepo
) -> Iterable[int]:
    return list(target_genre_config_repo.fetch_enabled_genre_ids())


def targets_item_codes(
    ctx: JobContext, *, rank_snapshot_repo: RankSnapshotRepo
) -> Iterable[str]:
    since = ctx.job_start_at.replace(hour=0, minute=0, second=0, microsecond=0)
    return list(rank_snapshot_repo.fetch_distinct_item_codes_since(since=since))


def targets_genre_ids_from_today_items(
    ctx: JobContext, *, staging_repo: StagingRepo, item_repo: ItemRepo
) -> Iterable[int]:
    source_ids = list(staging_repo.fetch_item_source_ids_since(since=ctx.job_start_at))
    if not source_ids:
        return []
    return list(item_repo.fetch_distinct_genre_ids_by_source_ids(source_ids))


def targets_tag_ids_from_today_items(
    ctx: JobContext, *, staging_repo: StagingRepo, item_tag_repo: ItemTagRepo
) -> Iterable[int]:
    source_ids = list(staging_repo.fetch_item_source_ids_since(since=ctx.job_start_at))
    if not source_ids:
        return []
    return list(item_tag_repo.fetch_distinct_tag_ids_by_source_ids(source_ids))
