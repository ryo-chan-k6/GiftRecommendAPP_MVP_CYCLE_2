# JOB-E-02 Embedding Build（OpenAI Embeddings）仕様書（MVP）

## 1. 目的
JOB-E-01 が生成した `apl.item_embedding_source` を入力として、OpenAI Embeddings APIで商品Embeddingを生成し、`apl.item_embedding` に保存する。  
差分判定は **source_hash** を基準に行い、再生成を最小化する。

---

## 2. 入力

### 2.1 入力テーブル
- `apl.item_embedding_source`

### 2.2 対象抽出（差分のみ）
対象 item は以下のいずれかを満たすもの：

1) `apl.item_embedding` に `(item_id, model)` が存在しない  
2) `apl.item_embedding.source_hash` と `apl.item_embedding_source.source_hash` が不一致

> `apl.item_embedding` に `source_hash` を追加し、差分判定を確実に行う（DDL差分あり）。

---

## 3. 出力

### 3.1 出力テーブル
- `apl.item_embedding`

### 3.2 主キー
- `(item_id, model)`（DBML通り）

### 3.3 追加カラム（必須）
- `source_hash`（差分追跡用）
- `updated_at`（上書き運用のため）

---

## 4. OpenAI Embeddings API

### 4.1 モデル（MVP推奨）
- `text-embedding-3-small`

### 4.2 入力
- `input = source_text`

### 4.3 実行方式
- MVPは **1 item = 1 API call**（失敗隔離を優先）
- 将来最適化：まとめて複数inputを1リクエストにする（スループット/コスト最適化）

### 4.4 認証・設定（環境変数）
- `OPENAI_API_KEY`（必須）
- `OPENAI_EMBEDDING_MODEL`（例：`text-embedding-3-small`）
- `OPENAI_TIMEOUT_SEC`（例：30）
- `OPENAI_MAX_RETRIES`（例：5）
- `OPENAI_BACKOFF_BASE_SEC`（例：1.0）

---

## 5. リトライ・失敗扱い（C-3整合）

### 5.1 リトライ対象
- 429（rate limit）
- 5xx
- timeout / network error

### 5.2 リトライ方式
- 指数バックオフ + ジッター（推奨）
- 最大回数を超えたら failure として記録して継続

### 5.3 ジョブ失敗判定
- `failure_rate > 1%` でジョブ失敗（Ranking/Genre/Tag同等の扱いに揃える）

---

## 6. DB更新（upsert）

### 6.1 upsertキー
- `ON CONFLICT (item_id, model) DO UPDATE`

### 6.2 更新最小化（推奨）
- `source_hash` を保持する場合：
  - `WHERE item_embedding.source_hash IS DISTINCT FROM excluded.source_hash`
- `source_hash` が無い場合：
  - 常に更新（ただし無駄更新になりやすい）

---

## 7. スループット制御（推奨）
- 同時実行は小さく開始（例：並列 2〜4）
- 429が多い場合は並列度を落とす or sleep挿入
- 1回の実行あたり処理件数上限（例：`--limit 500`）を持つと安全

---

## 8. テスト方針（Unit/Component）
- Unit：OpenAIクライアントの例外分類（429/5xx/timeout）
- Component：API失敗時にDB更新しない（または failure としてカウント）
- Component：差分対象抽出SQLが期待通り（未作成 or hash不一致のみ）
