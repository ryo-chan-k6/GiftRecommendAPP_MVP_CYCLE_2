from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from core.normalize import normalize  # noqa: E402


@pytest.mark.unit
def test_normalize_item_sorts_keys_and_arrays_and_excludes_meta() -> None:
    raw = {
        "itemCode": "shop:123",
        "mediumImageUrls": ["b", "a"],
        "smallImageUrls": ["2", "1"],
        "tagIds": [3, 1, 2],
        "request_id": "drop-me",
        "fetched_at": "2026-01-01T00:00:00Z",
        "nested": {"b": " B ", "a": "A"},
    }

    normalized = normalize("item", raw)

    assert "request_id" not in normalized
    assert "fetched_at" not in normalized
    assert normalized["smallImageUrls"] == ["1", "2"]
    assert normalized["mediumImageUrls"] == ["a", "b"]
    assert normalized["tagIds"] == [1, 2, 3]
    assert list(normalized["nested"].keys()) == ["a", "b"]
    assert normalized["nested"]["b"] == "B"


@pytest.mark.unit
def test_normalize_preserves_list_order_for_non_sorted_entity() -> None:
    raw = {"items": [3, 2, 1]}

    normalized = normalize("ranking", raw)

    assert normalized["items"] == [3, 2, 1]


@pytest.mark.unit
def test_normalize_trims_and_nulls_empty_strings() -> None:
    raw = {"name": "  hello  ", "empty": "   "}

    normalized = normalize("item", raw)

    assert normalized["name"] == "hello"
    assert normalized["empty"] is None
