from datetime import datetime, timezone
import uuid

from fastapi import HTTPException

import json
import math
from typing import Any, Dict, List

from reco.api.schemas import RecommendationRequest, RecommendationResponse, RecommendedItem, ResolvedAlgorithm
from reco.core.mmr import mmr_select
from reco.core.mode_resolver import resolve_mode
from reco.core.scoring import score_candidates
from reco.infra.embedding_client import DEFAULT_EMBEDDING_MODEL, embed_text
from reco.infra.supabase_client import get_supabase_admin


def _build_context_text(req: RecommendationRequest) -> str:
    parts = []
    if req.featuresLike:
        parts.append(f"like: {', '.join(req.featuresLike)}")
    if req.featuresNotLike:
        parts.append(f"not_like: {', '.join(req.featuresNotLike)}")
    if req.featuresNg:
        parts.append(f"ng: {', '.join(req.featuresNg)}")
    return " / ".join(parts)


def _parse_embedding(value: Any) -> List[float] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [float(v) for v in value]
    if isinstance(value, str):
        try:
            return [float(v) for v in json.loads(value)]
        except json.JSONDecodeError:
            return None
    return None


def _cosine_similarity(a: List[float], b: List[float]) -> float | None:
    if not a or not b or len(a) != len(b):
        return None
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return None
    return dot / (norm_a * norm_b)


def recommend(req: RecommendationRequest) -> RecommendationResponse:
    request_id = str(uuid.uuid4())
    embedding_version = 1

    try:
        resolved = resolve_mode(req.mode, req.algorithmOverride)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    context_text = _build_context_text(req)
    try:
        context_vector = embed_text(context_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"embedding failed: {e}")

    sb = get_supabase_admin()
    try:
        feature_query = (
            sb.schema("apl")
            .table("item_features")
            .select(
                "item_id, price_yen, rank, popularity_score, review_average, "
                "review_count, tag_ids, item: item_id (id, is_active)"
            )
            .eq("item.is_active", True)
        )
        if req.budgetMin is not None:
            feature_query = feature_query.gte("price_yen", req.budgetMin)
        if req.budgetMax is not None:
            feature_query = feature_query.lte("price_yen", req.budgetMax)

        feature_resp = feature_query.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"supabase query failed: {e}")

    rows = feature_resp.data or []
    if not rows:
        raise HTTPException(status_code=500, detail="apl.item_features has no rows")

    item_ids = [r.get("item_id") for r in rows if r.get("item_id")]
    if not item_ids:
        raise HTTPException(status_code=500, detail="no item_id in features result")
    try:
        embedding_resp = (
            sb.schema("apl")
            .table("item_embedding")
            .select("item_id, embedding")
            .eq("model", DEFAULT_EMBEDDING_MODEL)
            .in_("item_id", item_ids)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"item_embedding query failed: {e}")

    embeddings = {}
    for r in embedding_resp.data or []:
        emb = _parse_embedding(r.get("embedding"))
        if emb is not None:
            embeddings[r.get("item_id")] = emb

    rows_with_vector: List[Dict[str, Any]] = []
    for r in rows:
        emb = embeddings.get(r.get("item_id"))
        if not emb:
            continue
        sim = _cosine_similarity(context_vector, emb)
        if sim is None:
            continue
        row = dict(r)
        row["vector_score"] = sim
        rows_with_vector.append(row)

    if not rows_with_vector:
        raise HTTPException(status_code=500, detail="no items with embeddings")

    rows_with_vector.sort(key=lambda x: x["vector_score"], reverse=True)
    rows_topk = rows_with_vector[: resolved.k]

    scored = score_candidates(rows_topk, resolved)
    if resolved.algorithm == "vector_only":
        ranked = sorted(scored, key=lambda x: x["vector_score"], reverse=True)
        final = ranked[:resolved.n_out]
    elif resolved.algorithm == "vector_ranked":
        ranked = sorted(scored, key=lambda x: x["score"], reverse=True)
        final = ranked[:resolved.n_out]
    else:
        ranked = sorted(scored, key=lambda x: x["score"], reverse=True)
        mmr_input = ranked[: resolved.n_in]
        final = mmr_select(mmr_input, resolved.n_out, resolved.mmr_lambda)

    items = [
        RecommendedItem(
            itemId=item["item_id"],
            rank=idx + 1,
            score=item["score"],
            vectorScore=item.get("vector_score"),
            rerankScore=item.get("rerank_score"),
            reason=item["reason"],
        )
        for idx, item in enumerate(final)
    ]

    resolved_payload = ResolvedAlgorithm(
        name=resolved.algorithm,
        params=resolved.to_response_params(),
        resolvedBy=resolved.resolved_by,
    )

    return RecommendationResponse(
        requestId=request_id,
        context={
            "contextText": context_text,
            "contextVector": context_vector,
            "embeddingModel": DEFAULT_EMBEDDING_MODEL,
            "embeddingVersion": embedding_version,
        },
        resolved=resolved_payload,
        items=items,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )
