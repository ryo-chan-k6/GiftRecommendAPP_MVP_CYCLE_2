from __future__ import annotations

import math

import pytest

from jobs import item_features_job  # noqa: E402


@pytest.mark.unit
def test_compute_log_value_handles_none_and_zero() -> None:
    assert item_features_job._compute_log_value(None) is None
    assert item_features_job._compute_log_value(0) is None
    assert item_features_job._compute_log_value(-1) is None
    assert item_features_job._compute_log_value(10) == math.log(10)


@pytest.mark.unit
def test_compute_popularity_score_rules() -> None:
    assert item_features_job._compute_popularity_score(
        review_average=None, review_count=None
    ) is None
    assert (
        item_features_job._compute_popularity_score(
            review_average=None, review_count=0
        )
        == 0.0
    )
    score = item_features_job._compute_popularity_score(
        review_average=4.0, review_count=9
    )
    assert score is not None
    assert score > 0.0
