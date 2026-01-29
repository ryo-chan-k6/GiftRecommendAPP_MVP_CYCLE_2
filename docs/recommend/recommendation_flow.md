# Recommendation Flow (End-to-End)

## 1. Purpose
本ドキュメントは、レコメンド機能の **エンドツーエンド処理フロー**を、
API / DB / ベクトル検索 / スコアリング / MMR / 永続化の観点で整理する。

- 実装担当（FE/BE/DB/Batch）が責務を理解できる
- どこで何が起きるか（データの流れ）を明確にする
- ログ調査・障害切り分けを容易にする

---

## 2. Actors & Responsibilities

| Actor | Responsibility |
|------|----------------|
| Frontend | mode と Context 入力を組み立て、API を呼ぶ |
| Backend API | 認証・入力整形・永続化・レスポンス生成 |
| Reco Service | mode 解決、検索、スコアリング、MMR、レスポンス生成 |
| Postgres (Supabase) | Context/Result 永続化、pgvector 検索、参照系クエリ |
| Batch/Collector | Item データの整備（rank/review 等の外部データ反映、ItemVector 生成/更新） |
| Admin | algorithmOverride / パラメータ検証（実験） |

---

## 3. High-level Sequence (Happy Path)

```
Frontend
  |
  | 1) POST /recommendations  (mode + context params)
  v
Backend API
  |
| 2) Resolve mode -> params (weights, λ, K)
  |
| 3) Build or reuse Context snapshot
  |
| 4) Compute ContextVector (embedding)
 |
| 5) Pre-filter (budget, is_active)
 |
| 6) Vector retrieval (cosine similarity): TopK candidates
 |
| 7) Fetch candidate features (rank, reviews, price, tags...)
 |
| 8) Apply hard filters (NG conditions)
  |
| 9) Re-rank scoring (S_vec, S_pop, S_rev -> S_final)
 |
| 10) MMR diversification (TopN_in -> TopN_out)
 |
| 11) Persist recommendation header & items
 |
| 12) Return response (items + resolvedAlgorithm + debug fields)
  v
Frontend
  |
  | 12) Render list + reasons + mode label
  v
User
```

---

## 4. Detailed Flow (Step-by-step)

## 4.1 Request Intake (Frontend → Backend)

### Inputs
- mode: `popular | balanced | diverse`
- context params:
  - event_id
  - recipient_id
  - budget_min / budget_max
  - features_like / features_not_like / features_ng

### Notes
- 一般ユーザーは algorithm を指定しない
- ADMIN は `algorithmOverride` を指定可能

---

## 4.2 Resolve Mode → Internal Params

参照: `recommendation_mode_resolution.md`

Resolved params:
- Algorithm: `vector_ranked_mmr`（一般ユーザー固定 / Pattern A）
- weights: w_vec / w_pop / w_rev
- mmr_lambda
- candidate_size_k

---

## 4.3 Context Snapshot (DB)

### DB entity
- apl.context（スナップショット）
  - embedding_context（テキスト）
  - context_vector（vector）
  - context_hash（再利用用）

### Processing
- context_hash を生成（同一入力の再利用）
- 既存があれば reuse / なければ insert

---

## 4.4 ContextVector Generation (Embedding)

### Processing
- embedding_context を組み立て（テンプレート）
- Embedding API を呼び出しベクトル化
- pgvector 型へ格納

### Observability
- embedding_model, embedding_version を context に保存
- 実行時間・失敗理由をログ化

---

## 4.5 Pre-filter (budget, is_active)

### Processing
- 予算（budget_min / budget_max）を満たす item を抽出
- is_active=true の item のみ対象

### Notes
- 予算のみ DB 側で先に絞る方針
- features_ng は後段で適用

---

## 4.6 Candidate Retrieval (cosine similarity)

### Query
- cosine similarity で TopK を取得（アプリ層 or DB いずれでも可）
- 取得フィールド:
  - item_id
  - vector_score（sim または distance から算出）

### Notes
- ここで返るのは「候補集合」だけ
- まだ人気/レビュー/予算フィルタ等は反映しない

---

## 4.7 Candidate Enrichment (DB Fetch)

TopK items の付加情報を取得する。
- rank（ランキング順位等）
- review_average / review_count
- price
- tags / brand / genre など表示・理由生成用属性

---

## 4.8 Hard Filters

### Budget filter (MVP)
- **4.5 で実施済み**

### NG filters
- ※MVP では実装対象外（将来、検索/embedding で高度化）

---

## 4.9 Re-rank Scoring (②)

参照: `scoring_definition.md`

Compute:
- S_vec
- S_pop
- S_rev
- S_final = weighted sum

Output:
- rerank_score = S_final
- vector_score = S_vec（保存・解析用）

---

## 4.10 MMR Diversification (③)

参照: `mmr_algorithm.md`

Inputs:
- Candidates sorted by S_final
- Take TopN_in (e.g. 50)
- Apply MMR to select TopN_out (e.g. 20)

Outputs:
- final rank
- score（最終スコア）
- rerank_score（元のS_final）
- vector_score（類似度）
- mmr diagnostics（任意）

---

## 4.11 Persistence (DB)

### recommendation (header)
- user_id
- context_id
- algorithm
- params（weights, λ, K, N_in, N_out）
- created_at

### recommendation_item (detail)
- recommendation_id
- item_id
- rank
- score
- vector_score
- rerank_score
- reason（jsonb）

---

## 4.12 Response Construction

### Response should include
- items[]:
  - item fields for UI
  - reason（必要最低限）
  - scores（ADMIN/debug用は条件付き）
- resolvedAlgorithm:
  - name
  - params
  - resolvedBy (mode/admin_override)

---

## 5. Error Handling & Fallbacks

### Embedding failure
- リトライ（回数制限）
- 失敗時は「vectorなし」fallback を検討（MVPではエラー返却でも可）

### Too few candidates after filters
- K を増やして再検索（diverse想定）
- もしくは budget を緩める提案（UI）

### pgvector query slow
- インデックス確認
- K / N_in の調整
- candidate enrichment をバッチ化

---

## 6. Performance Notes (MVP)

- TopK（K）は mode により変更
- MMR は TopN_in のみ対象にする（例: 50）
- MMR 計算はアプリ層で行い、DBは retrieval と enrichment に集中

---

## 7. Debug & Admin Support

- ADMIN は algorithmOverride を指定可能
- vector_only を baseline として比較可能
- response に debug 情報（scores, params）を含められる（ADMINのみ推奨）

---

## 8. Related Documents

- `overview.md`
- `recommendation_mode_resolution.md`
- `scoring_definition.md`
- `mmr_algorithm.md`
- `experiments.md`
