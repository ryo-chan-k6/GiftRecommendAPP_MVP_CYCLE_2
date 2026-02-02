from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.hasher import compute_content_hash  # noqa: E402


@pytest.mark.unit
def test_compute_content_hash_is_stable_for_same_content() -> None:
    normalized_a = {"b": 2, "a": 1}
    normalized_b = {"a": 1, "b": 2}

    assert compute_content_hash(normalized_a) == compute_content_hash(normalized_b)


@pytest.mark.unit
def test_compute_content_hash_changes_when_value_changes() -> None:
    normalized_a = {"a": 1, "b": 2}
    normalized_b = {"a": 1, "b": 3}

    assert compute_content_hash(normalized_a) != compute_content_hash(normalized_b)
