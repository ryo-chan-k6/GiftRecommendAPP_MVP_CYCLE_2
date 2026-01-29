# OpenAPI Recommendation Contract

## 1. Purpose

本ドキュメントは、レコメンド API の **リクエスト／レスポンス契約**を「例つき」で固定する。
実装（Backend/Frontend）およびテスト（Cursor AI）で迷いが出ないことを最優先とする。

- 一般ユーザー：`mode` でのみ制御（Algorithm は指定不可）
- ADMIN：`algorithmOverride` を指定可能（比較・実験目的）
- サーバは必ず `resolvedAlgorithm` を返す（再現性・解析性）

参照：

- `recommendation_mode_resolution.md`
- `scoring_definition.md`
- `mmr_algorithm.md`
- `recommendation_flow.md`

---

## 2. Endpoint Overview

### 2.1 Create recommendation

- **POST** `/recommendations`

主用途：Context（条件）からレコメンド結果を生成し、永続化し、結果を返す。

### 2.2 Get recommendation

- **GET** `/recommendations/{recommendationId}`

主用途：過去結果の参照（同一結果の再表示、分析）。

### 2.3 List recommendations

- **GET** `/recommendations?eventId=&recipientId=&page=&pageSize=`

主用途：履歴一覧。

### 2.4 Admin only: experiment

- **POST** `/admin/recommendations`

主用途：`algorithmOverride` や sweep パラメータによる検証。

---

## 3. Shared Types

## 3.1 Mode

`mode` は「内部パラメータセットへのキー」。

- `popular`
- `balanced`
- `diverse`

## 3.2 Algorithm (Response / Log)

Algorithm enum（返却・ログ用）：

- `vector_only`（ADMIN 比較用）
- `vector_ranked`（ADMIN 比較用）
- `vector_ranked_mmr`（一般ユーザー固定：Pattern A）

## 3.3 ResolvedAlgorithm

サーバが実際に使った戦略を表す。

- `name`: Algorithm enum
- `params`: 以下を含む
  - `candidateSizeK`
  - `weights`: `{ wVec, wPop, wRev }`
  - `mmr`: `{ lambda, topNIn, topNOut }`
  - `embedding`: `{ model, version }`
- `resolvedBy`: `"mode" | "admin_override"`

---

## 4. POST /recommendations

### 4.1 Request Body（一般ユーザー）

```json
{
  "mode": "balanced",
  "eventId": "uuid",
  "recipientId": "uuid",
  "budgetMin": 3000,
  "budgetMax": 8000,
  "featuresLike": ["落ち着いた", "実用的", "黒"],
  "featuresNotLike": ["派手"],
  "featuresNg": ["生もの"]
}
```

**Notes**

- budget はハードフィルタ
- `features*` は Context 文章生成に利用

### 4.2 Response（一般ユーザー）

```json
{
  "recommendationId": "uuid",
  "mode": "balanced",
  "resolvedAlgorithm": {
    "name": "vector_ranked_mmr",
    "resolvedBy": "mode",
    "params": {
      "candidateSizeK": 120,
      "weights": { "wVec": 0.6, "wPop": 0.2, "wRev": 0.2 },
      "mmr": { "lambda": 0.55, "topNIn": 50, "topNOut": 20 },
      "embedding": { "model": "text-embedding-3-small", "version": 1 }
    }
  },
  "context": {
    "contextId": "uuid",
    "contextHash": "sha256:...",
    "embeddingContext": "父の日のギフト。贈り先は父。予算は3000〜8000円。落ち着いた、実用的、黒が好み。派手なものは避けたい。生ものはNG。"
  },
  "items": [
    {
      "rank": 1,
      "itemId": "uuid",
      "title": "…",
      "price": 5980,
      "imageUrl": "…",
      "affiliateUrl": "…",
      "reason": {
        "highSimilarity": true,
        "budgetFit": true,
        "popularRank": { "rank": 12 },
        "review": { "average": 4.6, "count": 215 },
        "matchedHints": ["実用的", "落ち着いた"]
      }
    }
  ]
}
```

### 4.3 Response（ADMIN debug on）

ADMIN のみ `debug=true` を許可し、スコア内訳を返せる。

```json
{
  "items": [
    {
      "rank": 1,
      "itemId": "uuid",
      "debug": {
        "scores": {
          "sVec": 0.82,
          "sPop": 0.44,
          "sRev": 0.71,
          "sFinal": 0.71,
          "mmrPenalty": 0.18
        }
      }
    }
  ]
}
```

---

## 5. Admin Override（POST /admin/recommendations）

### 5.1 Request

```json
{
  "mode": "balanced",
  "algorithmOverride": "vector_only",
  "candidateSizeKOverride": 200,
  "mmrLambdaOverride": 0.3,
  "eventId": "uuid",
  "recipientId": "uuid"
}
```

### 5.2 Rules

- `algorithmOverride` は ADMIN のみ
- Pattern A の一般ユーザーは `algorithmOverride` 不可

---

## 6. Error Contract

### 6.1 Error Body

```json
{
  "error": {
    "code": "EMBEDDING_FAILED",
    "message": "Failed to generate embedding.",
    "details": { "retryable": true }
  }
}
```

### 6.2 Suggested Codes

- `VALIDATION_ERROR`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `EMBEDDING_FAILED`
- `VECTOR_SEARCH_FAILED`
- `NOT_ENOUGH_CANDIDATES`
- `INTERNAL_ERROR`

---

## 7. Acceptance Checklist

- 一般ユーザーは `mode` のみで制御できる
- 常に `resolvedAlgorithm` が返る
- ADMIN は `vector_only` 等で比較できる
- エラーが機械的に扱える（code 固定）
