from typing import Any, Dict, List, Sequence, Set


def _jaccard(a: Sequence[int], b: Sequence[int]) -> float:
    set_a: Set[int] = set(a)
    set_b: Set[int] = set(b)
    if not set_a and not set_b:
        return 0.0
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0


def mmr_select(
    candidates: List[Dict[str, Any]],
    top_n: int,
    lam: float,
) -> List[Dict[str, Any]]:
    if not candidates:
        return []

    ranked = sorted(candidates, key=lambda x: x["score"], reverse=True)
    if top_n >= len(ranked):
        return ranked

    selected: List[Dict[str, Any]] = []
    remaining = ranked[:]

    selected.append(remaining.pop(0))

    while len(selected) < top_n and remaining:
        best_idx = 0
        best_score = float("-inf")
        for idx, cand in enumerate(remaining):
            max_sim = 0.0
            for s in selected:
                sim = _jaccard(cand.get("tag_ids", []), s.get("tag_ids", []))
                if sim > max_sim:
                    max_sim = sim
            mmr = lam * cand["score"] - (1.0 - lam) * max_sim
            if mmr > best_score:
                best_score = mmr
                best_idx = idx
        selected.append(remaining.pop(best_idx))

    return selected
