# 実行環境・実行方式仕様（GitHub Actions）

## 1. 目的

- ETLジョブ（JOB-R/I/G/T/A/E-01/E-02）を決められた順序で実行する
- 失敗時に検知できる運用にする
- 同時多重起動を抑止する

## 2. 実行方式（ワークフロー構成）

### 2.1 ワークフロー種別

- `workflow_dispatch`：手動実行
- `schedule`：必要時に有効化（MVPではコメントアウト運用）

### 2.2 実行順序（依存関係）

`job_ranking → job_item → (job_genre & job_tag 並列) → job_is_active → job_embedding_source → job_embedding_build`

### 2.3 多重起動防止

- `concurrency` を使い、同一環境（dev/prod）で同時実行を抑止する
- `cancel-in-progress: false`（完走優先）

## 3. Secrets / Permissions

### 3.1 Secrets（必須）

| 名称 | 用途 |
| --- | --- |
| DATABASE_URL | Supabase Postgres接続 |
| RAKUTEN_APP_ID | 楽天APIアプリID |
| AWS_ROLE_TO_ASSUME | OIDC AssumeRole ARN |
| AWS_REGION | S3リージョン |
| S3_BUCKET_RAW_DEV / S3_BUCKET_RAW_PROD | raw保存先 |
| OPENAI_API_KEY | Embeddings API |

### 3.2 Secrets（任意）

| 名称 | 用途 |
| --- | --- |
| RAKUTEN_AFFILIATE_ID | アフィリエイトID |
| OPENAI_EMBEDDING_MODEL | 未指定時 `text-embedding-3-small` |
| OPENAI_TIMEOUT_SEC | 未指定時 30 |
| OPENAI_MAX_RETRIES | 未指定時 5 |
| OPENAI_BACKOFF_BASE_SEC | 未指定時 1.0 |

### 3.3 Permissions

- `contents: read`
- `id-token: write`（AWS OIDC）

## 4. 実行コマンド規約

- `python -m jobs.ranking_job`
- `python -m jobs.item_job`
- `python -m jobs.genre_job`
- `python -m jobs.tag_job`
- `python -m jobs.is_active_job`
- `python -m jobs.embedding_source_job`
- `python -m jobs.embedding_build_job`

## 5. 実行コンテキスト

- run_id：handlerが毎回生成（UUID）
- job_start_at：handler開始時刻
- 当日抽出基準は `day_start`（job_start_at の当日0:00）

## 6. C-4 Done（受け入れ条件）

- 手動実行でジョブネット順序が守られる
- Secrets/権限が揃えば dev/prod を切り替えて動かせる

