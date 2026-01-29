export const ALGORITHM_OVERRIDES = [
  "vector_only",
  "vector_ranked",
  "vector_ranked_mmr",
] as const;

export type AlgorithmOverride = (typeof ALGORITHM_OVERRIDES)[number];

export const MODES = ["popular", "balanced", "diverse"] as const;
export type RecommendationMode = (typeof MODES)[number];
