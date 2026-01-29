# Recommendation Mode Resolution

## 1. Purpose

本ドキュメントは、クライアントから指定される `mode`（recommendation mode）を、
サーバ内部のレコメンド戦略パラメータへ解決（resolve）するための設計仕様を定義する。

本仕様は以下を目的とする。

- フロントエンド／バックエンド間の責務分離を明確にする
- レコメンド結果の再現性・解析性を担保する
- mode 追加・調整時の影響範囲を限定する

---

## 2. Design Principles

### 2.1 Algorithm Pipeline is Fixed

- 一般ユーザー向けのレコメンド処理は **単一のパイプライン** に固定する
- パイプラインは以下で構成される

1. Vector Retrieval（pgvector cosine）
2. Re-ranking（人気・レビュー等のスコア統合）
3. Diversity Control（MMR）

### 2.2 Mode Controls Parameters, Not Algorithms

- `mode` は **アルゴリズムの分岐条件ではない**
- `mode` は以下の内部パラメータ群を切り替えるための抽象キーとする
  - weight（w_vec / w_pop / w_rev）
  - MMR λ
  - Candidate Size（K）

### 2.3 Observability First

- request では algorithm を指定させない
- response / log / DB には **解決後の Algorithm 名と params を必ず記録する**
- 結果解析・AB 比較・障害調査を容易にすることを優先する

---

## 3. Request / Response Responsibility

### 3.1 Request (Client → Server)

- 一般ユーザー
  - 指定可能: `mode`
  - 指定不可: algorithm / internal params
- ADMIN
  - `algorithmOverride` を指定可能（検証・比較用途）

### 3.2 Response (Server → Client)

- サーバは以下を必ず返却する
  - resolvedAlgorithm.name
  - resolvedAlgorithm.params
  - resolvedBy（mode / admin_override など）

---

## 4. Algorithm Definition

### 4.1 Algorithm Enum

| name              | description                                    |
| ----------------- | ---------------------------------------------- |
| vector_only       | Vector similarity only（① のみ・ADMIN 比較用） |
| vector_ranked     | Vector + Re-rank（①②・ADMIN 比較用）           |
| vector_ranked_mmr | Vector + Re-rank + MMR（①②③・標準）            |

※ Pattern A 方針では、一般ユーザーは常に `vector_ranked_mmr` を使用する。

---

## 5. Mode to Parameter Mapping (Pattern A)

### 5.1 Mode Definitions

| mode     | intent                 |
| -------- | ---------------------- |
| balanced | 品質と多様性のバランス |
| diverse  | 多様性重視（被り回避） |
| popular  | 外さない人気重視       |

### 5.2 Parameter Mapping Table

| mode     | Algorithm         | CandidateSize(K) | w_vec | w_pop | w_rev | MMR λ |
| -------- | ----------------- | ---------------- | ----- | ----- | ----- | ----- |
| balanced | vector_ranked_mmr | 120              | 0.60  | 0.20  | 0.20  | 0.55  |
| diverse  | vector_ranked_mmr | 220              | 0.65  | 0.15  | 0.20  | 0.25  |
| popular  | vector_ranked_mmr | 120              | 0.25  | 0.55  | 0.20  | 0.85  |

---

## 6. Scoring Overview

### 6.1 Vector Score (S_vec)

- ContextVector × ItemVector の cosine similarity
- Candidate 集合内で 0〜1 に正規化

### 6.2 Popularity Score (S_pop)

- ランキング順位等をベースに算出
- 逆数 or log 圧縮後、Candidate 内正規化

### 6.3 Review Score (S_rev)

- review_average × 信頼度（log(review_count)）

### 6.4 Final Re-rank Score

```
S_final = w_vec * S_vec + w_pop * S_pop + w_rev * S_rev
```

---

## 7. MMR Application

- Re-rank 上位 N 件を入力として MMR を適用
- MMR は常に有効（Pattern A）
- λ によって多様性の強弱を制御する

---

## 8. Logging & Persistence

- recommendation テーブルに以下を保存する
  - algorithm
  - params（weights / λ / K）
  - mode
- 将来的な AB テスト・モデル比較の基礎データとする

---

## 9. Extension Points

- mode の追加（例: exploratory / premium）
- popularity 定義の差し替え（sales / click / favorite）
- Algorithm enum の追加（ADMIN 検証専用）

---

## 10. Out of Scope (MVP)

- mode の UI 文言最適化
- 個人学習による重み自動最適化
- リアルタイム行動反映
