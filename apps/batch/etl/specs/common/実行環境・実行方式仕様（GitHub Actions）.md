# 実行環境・実行方式仕様（GitHub Actions）

## 1. 目的

- ETLジョブ（JOB-R/I/G/T/A）を決められた順序で定期実行し、失敗時に検知できるようにする
- 既定のジョブネット：Ranking → Item →（Genre & Tag 並列）→ is_active
- 同時多重起動を防止し、再実行で回復できる運用にする

## 2. 実行方式（ワークフロー構成）

### 2.1 ワークフロー種別

- schedule：定期実行
- workflow_dispatch：手動実行（デバッグ/即時再実行用）

### 2.2 実行順序（依存関係）

`job_ranking → job_item → (job_genre & job_tag 並列) → job_is_active`

### 2.3 多重起動防止（必須）

- concurrency を使い、同一環境（dev/prod）で同時実行を抑止する
- cancel-in-progress: true は用途次第（MVPは false推奨：途中キャンセルより完走優先）

## 3. タイムゾーンとスケジュール

### 3.1 注意（事実）

GitHub Actions の cron は UTC基準。

### 3.2 推奨スケジュール（例）

- dev：毎日 00:30 JST（UTCでは 15:30、前日扱い）
- prod：当面は schedule 実行しない（手動実行のみ）

※ cron は UTC で記述する。

## 4. Secrets / Variables / Permissions

### 4.1 Secrets（必須）

| 名称 | 用途 |
| --- | --- |
| DATABASE_URL | Supabase Postgres接続 |
| RAKUTEN_APP_ID | 楽天APIアプリID |
| RAKUTEN_AFFILIATE_ID | （必要なら）アフィリエイトID |
| AWS_REGION | S3リージョン |
| S3_BUCKET_RAW_DEV / S3_BUCKET_RAW_PROD | raw保存先 |

### 4.2 AWS認証方式（推奨：OIDC）

- GitHub Actions → AWS AssumeRole（OIDC）
- permissions: `id-token: write` が必要

代替（MVPで簡単に始めるなら）

- AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY を Secrets に置く（推奨度は下がる）

## 5. 失敗判定（C-3との整合）

### 5.1 exit code規約

- ジョブ内Pythonが exit 0：成功
- exit 1：失敗（GHA上も失敗扱い）

### 5.2 failure_rate 閾値（確定事項）

- Ranking / Genre / Tag：failure_rate > 1% で失敗扱い（exit != 0）
- Item：failure_rate > 5% で失敗扱い（exit != 0）
- is_active：SQL失敗のみ失敗（failure_rate概念なし）

## 6. 実行コマンド規約（共通）

### 6.1 コマンド（例）

- `python -m etl.jobs.ranking_job --env prod`
- `python -m etl.jobs.item_job --env prod`
- `python -m etl.jobs.genre_job --env prod`
- `python -m etl.jobs.tag_job --env prod`
- `python -m etl.jobs.is_active_job --env prod`

### 6.2 実行コンテキスト

- run_id：handlerが毎回生成（UUID）
- job_start_at：handler開始時刻を基準に、後続 policy が saved_at >= job_start_at を使う

## 7. Workflow YAML（推奨の雛形）

ファイル例：`.github/workflows/batch-etl.yml`

```yaml
name: batch-etl

on:
  workflow_dispatch:
    inputs:
      env:
        description: "Target env"
        required: true
        default: "dev"
        type: choice
        options: ["dev", "prod"]
  schedule:
    # NOTE: cron is UTC. Example: 00:10 JST = 15:10 UTC (previous day)
    - cron: "10 * * * *"  # every hour at :10 UTC (example)

concurrency:
  group: batch-etl-${{ github.workflow }}-${{ inputs.env || 'prod' }}
  cancel-in-progress: false

permissions:
  contents: read
  id-token: write  # for AWS OIDC (recommended)

jobs:
  job_ranking:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install deps
        run: |
          pip install -r collector/requirements.txt
      - name: Configure AWS (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ secrets.AWS_REGION }}
      - name: Run JOB-R-01
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          RAKUTEN_APP_ID: ${{ secrets.RAKUTEN_APP_ID }}
          RAKUTEN_AFFILIATE_ID: ${{ secrets.RAKUTEN_AFFILIATE_ID }}
          S3_BUCKET_RAW_DEV: ${{ secrets.S3_BUCKET_RAW_DEV }}
          S3_BUCKET_RAW_PROD: ${{ secrets.S3_BUCKET_RAW_PROD }}
        run: |
          python -m collector.jobs.ranking_job --env ${{ inputs.env || 'prod' }}

  job_item:
    runs-on: ubuntu-latest
    needs: [job_ranking]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install deps
        run: |
          pip install -r collector/requirements.txt
      - name: Configure AWS (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ secrets.AWS_REGION }}
      - name: Run JOB-I-01
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          RAKUTEN_APP_ID: ${{ secrets.RAKUTEN_APP_ID }}
          RAKUTEN_AFFILIATE_ID: ${{ secrets.RAKUTEN_AFFILIATE_ID }}
          S3_BUCKET_RAW_DEV: ${{ secrets.S3_BUCKET_RAW_DEV }}
          S3_BUCKET_RAW_PROD: ${{ secrets.S3_BUCKET_RAW_PROD }}
        run: |
          python -m collector.jobs.item_job --env ${{ inputs.env || 'prod' }}

  job_genre:
    runs-on: ubuntu-latest
    needs: [job_item]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install deps
        run: |
          pip install -r collector/requirements.txt
      - name: Configure AWS (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ secrets.AWS_REGION }}
      - name: Run JOB-G-01
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          RAKUTEN_APP_ID: ${{ secrets.RAKUTEN_APP_ID }}
          S3_BUCKET_RAW_DEV: ${{ secrets.S3_BUCKET_RAW_DEV }}
          S3_BUCKET_RAW_PROD: ${{ secrets.S3_BUCKET_RAW_PROD }}
        run: |
          python -m collector.jobs.genre_job --env ${{ inputs.env || 'prod' }}

  job_tag:
    runs-on: ubuntu-latest
    needs: [job_item]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install deps
        run: |
          pip install -r collector/requirements.txt
      - name: Configure AWS (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: ${{ secrets.AWS_REGION }}
      - name: Run JOB-T-01
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          RAKUTEN_APP_ID: ${{ secrets.RAKUTEN_APP_ID }}
          S3_BUCKET_RAW_DEV: ${{ secrets.S3_BUCKET_RAW_DEV }}
          S3_BUCKET_RAW_PROD: ${{ secrets.S3_BUCKET_RAW_PROD }}
        run: |
          python -m collector.jobs.tag_job --env ${{ inputs.env || 'prod' }}

  job_is_active:
    runs-on: ubuntu-latest
    needs: [job_genre, job_tag]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install deps
        run: |
          pip install -r collector/requirements.txt
      - name: Run JOB-A-01
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          python -m collector.jobs.is_active_job --env ${{ inputs.env || 'prod' }}
```

## 8. 運用ルール（MVP）

### 8.1 再実行

- 個別ジョブは workflow_dispatch で再実行可能
- 冪等性は staging hash と S3 immutable により担保

### 8.2 通知（最低限）

- MVPではまず GitHub Actions の失敗通知（メール等）でよい
- 将来：Slack通知などを追加（別途）

### 8.3 並列性

- Genre/Tag は並列実行（needs: job_item）
- is_active は必ず最後（needs: job_genre + job_tag）

## 9. C-4 Done（受け入れ条件）

- 定期実行と手動実行ができる
- ジョブネット通りの順序が守られる
- 多重起動が抑止される
- Ranking/Genre/Tag は failure_rate > 1% で失敗扱いになる
- Secrets/権限が揃えば dev/prod を切り替えて動かせる

