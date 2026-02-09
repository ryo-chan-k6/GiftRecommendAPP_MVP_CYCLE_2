## 1. 目的

本ドキュメントは、Batch ETL の GitHub Actions 実行方式を定義する。

## 2. トリガー

- `workflow_dispatch`（手動実行）
- `schedule` は必要時に有効化（MVPではコメントアウト運用）

## 3. 実行順序（MVP）

```
JOB-R-01 -> JOB-I-01 -> (JOB-G-01 || JOB-T-01) -> JOB-A-01 -> JOB-E-01 -> JOB-E-02
```

## 4. 使用ワークフロー

- `.github/workflows/batch-etl.yml`

## 5. 必須Secrets（最小セット）

- `DATABASE_URL`
- `AWS_ROLE_TO_ASSUME`
- `AWS_REGION`
- `S3_BUCKET_RAW_DEV`
- `S3_BUCKET_RAW_PROD`
- `RAKUTEN_APP_ID`
- `OPENAI_API_KEY`

## 6. 任意Secrets

- `RAKUTEN_AFFILIATE_ID`
- `OPENAI_EMBEDDING_MODEL`（未指定時は `text-embedding-3-small`）
- `OPENAI_TIMEOUT_SEC`（未指定時は 30）
- `OPENAI_MAX_RETRIES`（未指定時は 5）
- `OPENAI_BACKOFF_BASE_SEC`（未指定時は 1.0）

## 7. 実行時Env（各ジョブ共通）

- `ENV`（dev/prod）
- `DATABASE_URL`

## 8. OIDC / AWS

- `aws-actions/configure-aws-credentials` を使用
- `id-token: write` が必要

## 9. 運用メモ

- Embedding系は OpenAI のレート制限に注意（429が多い場合は並列数を下げる）

