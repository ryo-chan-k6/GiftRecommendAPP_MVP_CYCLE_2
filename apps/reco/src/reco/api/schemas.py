from typing import List, Literal, Optional, Dict, Any

from pydantic import BaseModel, Field

Mode = Literal["popular", "balanced", "diverse"]
AlgorithmOverride = Literal["vector_only", "vector_ranked", "vector_ranked_mmr"]


class RecommendationRequest(BaseModel):
    mode: Mode = Field(..., description="User-facing recommendation mode")

    eventId: Optional[str] = None
    recipientId: Optional[str] = None

    budgetMin: Optional[int] = Field(None, ge=0)
    budgetMax: Optional[int] = Field(None, ge=0)

    featuresLike: List[str] = Field(default_factory=list)
    featuresNotLike: List[str] = Field(default_factory=list)
    featuresNg: List[str] = Field(default_factory=list)

    algorithmOverride: Optional[AlgorithmOverride] = None


class RecommendedItem(BaseModel):
    itemId: str
    rank: int
    score: float
    vectorScore: Optional[float] = None
    rerankScore: Optional[float] = None
    reason: Dict[str, Any]


class ResolvedAlgorithm(BaseModel):
    name: str
    params: Dict[str, Any]
    resolvedBy: str


class RecommendationResponse(BaseModel):
    requestId: str
    context: Dict[str, Any]
    resolved: ResolvedAlgorithm
    items: List[RecommendedItem]
    generatedAt: str
