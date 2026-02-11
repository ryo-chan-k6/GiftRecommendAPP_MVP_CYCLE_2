from typing import Optional

from reco.domain.models import ResolvedParams

ALGORITHM_CHOICES = {
    "vector_only",
    "vector_ranked",
    "vector_ranked_mmr",
}

MODE_PARAMS = {
    "balanced": {
        "algorithm": "vector_ranked_mmr",
        "k": 120,
        "w_vec": 0.60,
        "w_pop": 0.20,
        "w_rev": 0.20,
        "mmr_lambda": 0.55,
    },
    "diverse": {
        "algorithm": "vector_ranked_mmr",
        "k": 220,
        "w_vec": 0.65,
        "w_pop": 0.15,
        "w_rev": 0.20,
        "mmr_lambda": 0.25,
    },
    "popular": {
        "algorithm": "vector_ranked_mmr",
        "k": 120,
        "w_vec": 0.25,
        "w_pop": 0.55,
        "w_rev": 0.20,
        "mmr_lambda": 0.85,
    },
}


def resolve_mode(mode: str, algorithm_override: Optional[str]) -> ResolvedParams:
    if mode not in MODE_PARAMS:
        raise ValueError(f"invalid mode: {mode}")

    if algorithm_override is not None and algorithm_override not in ALGORITHM_CHOICES:
        raise ValueError(f"invalid algorithmOverride: {algorithm_override}")

    base = MODE_PARAMS[mode]
    algorithm = algorithm_override or base["algorithm"]
    resolved_by = "admin_override" if algorithm_override else "mode"

    return ResolvedParams(
        mode=mode,
        algorithm=algorithm,
        k=base["k"],
        w_vec=base["w_vec"],
        w_pop=base["w_pop"],
        w_rev=base["w_rev"],
        mmr_lambda=base["mmr_lambda"],
        resolved_by=resolved_by,
    )
