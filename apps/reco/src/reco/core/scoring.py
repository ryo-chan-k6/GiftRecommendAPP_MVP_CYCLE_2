from typing import Any, Dict, List, Optional
import math


def _normalize_0_1(values: List[float]) -> List[float]:
    if not values:
        return []
    v_min = min(values)
    v_max = max(values)
    if v_max == v_min:
        return [0.0 for _ in values]
    return [(v - v_min) / (v_max - v_min) for v in values]


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def score_candidates(rows: List[Dict[str, Any]], params: Any) -> List[Dict[str, Any]]:
    vec_raw = []
    pop_raw = []
    rev_raw = []

    filtered_rows = [
        r for r in rows
        if _safe_float(r.get("vector_score")) is not None
    ]
    if not filtered_rows:
        return []

    review_counts = [
        _safe_float(r.get("review_count")) or 0.0
        for r in filtered_rows
    ]
    max_review_count = max(review_counts) if review_counts else 0.0

    for r in filtered_rows:
        vector_score = _safe_float(r.get("vector_score"))
        vec_raw.append(vector_score)

        popularity_score = _safe_float(r.get("popularity_score"))
        if popularity_score is None:
            rank = _safe_float(r.get("rank"))
            popularity_score = 1.0 / (rank + 1.0) if rank is not None else 0.0
        pop_raw.append(popularity_score)

        review_avg = _safe_float(r.get("review_average")) or 0.0
        review_count = _safe_float(r.get("review_count")) or 0.0
        quality = max(0.0, min(review_avg / 5.0, 1.0))
        if max_review_count > 0:
            confidence = math.log(1.0 + review_count) / math.log(1.0 + max_review_count)
        else:
            confidence = 0.0
        rev_raw.append(quality * confidence)

    vec_norm = _normalize_0_1(vec_raw)
    pop_norm = _normalize_0_1(pop_raw)
    rev_norm = _normalize_0_1(rev_raw)

    scored = []
    for i, r in enumerate(filtered_rows):
        s_vec = vec_norm[i] if vec_norm else 0.0
        s_pop = pop_norm[i] if pop_norm else 0.0
        s_rev = rev_norm[i] if rev_norm else 0.0
        s_final = (
            params.w_vec * s_vec
            + params.w_pop * s_pop
            + params.w_rev * s_rev
        )

        scored.append(
            {
                "item_id": r.get("item_id"),
                "score": s_final,
                "vector_score": s_vec,
                "rerank_score": s_final,
                "tag_ids": r.get("tag_ids") or [],
                "reason": {
                    "type": "scoring",
                    "scores": {
                        "s_vec": s_vec,
                        "s_pop": s_pop,
                        "s_rev": s_rev,
                    },
                },
            }
        )

    return scored
