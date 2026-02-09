from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from jobs import embedding_source_job  # noqa: E402
from repos.apl.item_embedding_source_repo import ItemFeatureRow  # noqa: E402


@pytest.mark.unit
def test_build_source_text_normalizes_inputs() -> None:
    row = ItemFeatureRow(
        item_id="item-1",
        item_name="  Foo  ",
        catchcopy="Best\tProduct",
        item_caption="<b>Great</b>\r\n\r\nPrice  1000",
        genre_name="  Snacks ",
        tag_names=[" Tag1 ", "Tag2", "Tag3"],
        item_price=1500,
        item_updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        feature_updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    source_text = embedding_source_job._build_source_text(row)

    assert "商品名: Foo" in source_text
    assert "キャッチコピー: Best Product" in source_text
    assert "商品説明: Great\nPrice 1000" in source_text
    assert "ジャンル: Snacks" in source_text
    assert "タグ: Tag1, Tag2, Tag3" in source_text
    assert "価格: 1500円" in source_text


@pytest.mark.unit
def test_build_source_text_limits_tags() -> None:
    row = ItemFeatureRow(
        item_id="item-2",
        item_name="Foo",
        catchcopy=None,
        item_caption="Caption",
        genre_name="Genre",
        tag_names=[f"t{idx}" for idx in range(1, 40)],
        item_price=None,
        item_updated_at=None,
        feature_updated_at=None,
    )

    source_text = embedding_source_job._build_source_text(row)

    assert "タグ: " in source_text
    tag_line = [line for line in source_text.split("\n") if line.startswith("タグ: ")][0]
    tags = tag_line.replace("タグ: ", "").split(", ")
    assert len(tags) == 30
    assert tags[0] == "t1"
    assert tags[-1] == "t30"


@pytest.mark.unit
def test_source_hash_is_stable_after_normalization() -> None:
    row_a = ItemFeatureRow(
        item_id="item-3",
        item_name="Foo",
        catchcopy="  Best  ",
        item_caption="Desc",
        genre_name="Genre",
        tag_names=["A", "B"],
        item_price=1000,
        item_updated_at=None,
        feature_updated_at=None,
    )
    row_b = ItemFeatureRow(
        item_id="item-3",
        item_name="Foo",
        catchcopy="\tBest",
        item_caption="Desc",
        genre_name="Genre",
        tag_names=["A", "B"],
        item_price=1000,
        item_updated_at=None,
        feature_updated_at=None,
    )

    text_a = embedding_source_job._build_source_text(row_a)
    text_b = embedding_source_job._build_source_text(row_b)

    assert (
        embedding_source_job._compute_source_hash(text_a)
        == embedding_source_job._compute_source_hash(text_b)
    )
