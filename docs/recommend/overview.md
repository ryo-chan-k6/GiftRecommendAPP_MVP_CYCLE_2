# Recommendation Overview

## 1. Purpose

本ドキュメントは、本サービスにおける **レコメンド機能全体の概要** を整理し、
設計思想・処理フロー・主要コンポーネントの関係を俯瞰できるようにすることを目的とする。

- 初見の開発者が全体像を把握できる
- 各詳細設計ドキュメントへの入口となる
- 仕様・実装・運用の共通理解を作る

---

## 2. Recommendation Concept

### 2.1 基本思想

本サービスのレコメンドは、単なる「人気順」や「類似商品提示」ではなく、

> **ユーザーの文脈（Context） × 商品の意味的特徴**

を中心に据えた **コンテキスト指向レコメンド** である。

---

### 2.2 中核となる考え方

- ユーザーは「条件（Context）」を入力する
- Context を文章化し、Embedding により **ContextVector** を生成する
- 商品はあらかじめ **ItemVector** を持つ
- ベクトル類似度を軸に候補を集め、補助スコアで整え、多様性を加える

---

## 3. High-level Flow

```
[User Request]
      |
      v
[Context Generation]
      |
      v
[Embedding (ContextVector)]
      |
      v
[Vector Retrieval (pgvector)]
      |
      v
[Re-rank Scoring]
      |
      v
[MMR Diversification]
      |
      v
[Recommendation Response]
```

---

## 4. Core Components

### 4.1 Context

- イベント（event）
- 贈り先（recipient）
- 予算（budget）
- 好み / NG 条件（features_like / not_like / ng）

これらを統合した **スナップショット** が Context として保存される。

---

### 4.2 Vector (Embedding)

| Vector        | 説明                                      |
| ------------- | ----------------------------------------- |
| ContextVector | ユーザー条件を文章化し Embedding したもの |
| ItemVector    | 商品情報を文章化し Embedding したもの     |

両者は同一モデル・同一次元で生成される。

---

### 4.3 Scoring

- ベクトル類似度（S_vec）
- 人気（S_pop）
- レビュー（S_rev）

これらを正規化・重み付けして **S_final** を算出する。

---

### 4.4 Diversification (MMR)

- 類似商品が固まるのを防ぐ
- 逐次選択により「意味の被り」を抑制
- λ により多様性の強弱を制御

---

## 5. Mode & Strategy

### 5.1 Mode の役割

- クライアントは `mode` のみ指定
- mode は **内部パラメータセットへのキー**
- アルゴリズム自体は固定（Pattern A：vector_ranked_mmr）

### 5.2 Strategy Resolution

- mode → weights / λ / CandidateSize(K)
- 解決結果は response / log に必ず残す

詳細は `recommendation_mode_resolution.md` を参照。

---

## 6. Algorithm Pipeline

### 6.1 標準パイプライン（一般ユーザー）

1. Vector Retrieval
2. Re-rank
3. MMR

Algorithm enum: `vector_ranked_mmr`

### 6.2 検証用パイプライン（ADMIN）

- vector_only
- vector_ranked
- vector_ranked_mmr

---

## 7. Persistence & Observability

### 7.1 保存される情報

- context（条件スナップショット）
- recommendation（algorithm / params / mode）
- recommendation_item（rank / score / reason）

### 7.2 意図

- 結果再現
- ロジック改善
- 将来的な AB テスト基盤

---

## 8. Documents Map

本機能に関連するドキュメントは以下。

- `overview.md`（本ドキュメント）
- `recommendation_mode_resolution.md`
- `scoring_definition.md`
- `mmr_algorithm.md`
- `recommendation_flow.md`

---

## 9. Non-goals (MVP)

- ユーザー行動学習による自動最適化
- リアルタイム再計算
- 個人別モデルの学習

---

## 10. Summary

- レコメンドは **Context × Vector** を中心に設計
- mode は戦略キー、Algorithm は固定
- 観測性・再現性を重視した設計

本 Overview を起点に、詳細設計へ進む。
