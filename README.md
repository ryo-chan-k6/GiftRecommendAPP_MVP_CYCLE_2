# GiftRecommendAPP_MVP_CYCLE_2

ギフト推薦MVPのリポジトリです。Web/UI、API、推薦(Recommender)、バッチETLを単一リポジトリで管理します。

## 構成

- `apps/web`: Next.js (フロントエンド)
- `apps/api`: Express + TypeScript (API)
- `apps/reco`: FastAPI (推薦サービス)
- `apps/batch`: Python ETL (GitHub Actions)
- `docs`: 設計/仕様ドキュメント

## 必要要件

- Node.js / pnpm (`packageManager: pnpm@10.8.0`)
- Python 3.13.3 (CI実行環境)

## セットアップ

1) 依存関係のインストール

```
pnpm install
```

2) Python依存のインストール

```
python -m venv .venv
source .venv/Scripts/activate  # Windows (bash)
pip install -r apps/batch/requirements.txt
pip install -r apps/reco/requirements.txt
```

3) 環境変数の準備

- `apps/reco/.env` などの環境変数を設定
- バッチETLは `DATABASE_URL` / `RAKUTEN_APP_ID` / `AWS_*` などを利用

## 起動方法

### Webサーバ

```
pnpm dev:web
```

### APIサーバ

```
pnpm dev:api
```

### Recoサーバ

```
uvicorn reco.main:app --reload --app-dir apps/reco/src
```

### バッチジョブ (GitHub Actions)

ワークフロー: `.github/workflows/batch-etl.yml`

1) GitHub Actions画面で `batch-etl` を選択
2) `Run workflow` を押して `env` を選択 (`dev` / `prod`)
3) 必要なSecretsが設定されていることを確認

ローカルでの単体実行例:

```
cd apps/batch/etl
python -m jobs.ranking_job
```

## テスト

### バッチ単体テスト

```
cd apps/batch/etl
pytest -m "unit"
```

## CI / ワークフロー

- `ci.yaml`: 統一CI（batch / web / api / reco の単体テスト・検証 + テスト成功後のPR作成）
  - `batch-unit`: バッチ単体テスト（pytest）
  - `web-check`: Lint + Build
  - `api-check`: TypeScript型チェック
  - `reco-check`: アプリ読み込み検証
- `batch-etl.yml`: バッチETLジョブの実行（手動）

## ドキュメント

詳細な設計や仕様は `docs/` を参照してください。
