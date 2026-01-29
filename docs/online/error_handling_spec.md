# Error Handling Specification (MVP)

## 1. Purpose
レコメンド API の異常系を統一し、Frontend・Backend・運用（ログ調査）で
同じ判断ができるようにする。

---

## 2. Error Response Format
```json
{
  "error": {
    "code": "EMBEDDING_FAILED",
    "message": "Failed to generate embedding.",
    "details": { "retryable": true }
  }
}
```

---

## 3. HTTP Status Mapping
| code | http | retryable |
|---|---:|---|
| VALIDATION_ERROR | 400 | false |
| UNAUTHORIZED | 401 | false |
| FORBIDDEN | 403 | false |
| EMBEDDING_FAILED | 502 | true |
| VECTOR_SEARCH_FAILED | 500 | true |
| NOT_ENOUGH_CANDIDATES | 422 | false |
| INTERNAL_ERROR | 500 | maybe |

---

## 4. Retry Policy
- Embedding：最大2回（指数バックオフ）
- pgvector：1回再試行（transient想定）

---

## 5. Logging Requirements
- requestId / userId / contextHash
- resolvedAlgorithm.params（K, λ, weights）
- timings（embedding_ms, vector_search_ms, rerank_ms, mmr_ms）
- error code / stack trace
