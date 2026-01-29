# ソースフォルダ / ソースファイル構成

## 1. 前提（この構成で満たす要件）

- 5ジョブ（JOB-R/I/G/T/A）を **同一骨格（共通処理）**で実装できる
- rawはS3にimmutable保存、差分判定はhash、最新台帳はapl.staging
- ジョブ責務の分離（更新可能テーブル境界）をコード構造で強制する
- SQLは可能な限りファイル化し、差し替え可能にする

## 2. ディレクトリ構成（推奨：etl/ 配下）

```
etl/
  README.md
  pyproject.toml              # 依存管理（uv/pip/poetry等は任意で合わせる）
  requirements.txt            # 併用可（MVPはこれでもOK）

  jobs/                       # ジョブ起点（handler層：薄く保つ）
    __init__.py
    ranking_job.py            # JOB-R-01
    item_job.py               # JOB-I-01
    genre_job.py              # JOB-G-01
    tag_job.py                # JOB-T-01
    is_active_job.py          # JOB-A-01

  services/                   # フロー制御（共通ロジック）
    __init__.py
    etl_service.py            # 共通ETLフロー（差分判定→保存→反映）
    policy.py                 # 入力集合の抽出（当日更新分の定義など）
    context.py                # 実行コンテキスト（job_id, env, run_id, job_start_at 等）

  clients/                    # 外部接続（楽天APIなど）
    __init__.py
    rakuten_client.py         # API呼び出し・レート制御・リトライ（詳細はC-3）

  core/                       # 横断ユーティリティ（純粋関数/薄いラッパ）
    __init__.py
    config.py                 # 環境変数読取（S3/DB/楽天キー等）
    logging.py                # logger生成（job_id/run_idを付与）
    hasher.py                 # normalize + hash
    normalize.py              # entity別の正規化ルール。楽天APIレスポンス差分（順序揺れ / null / 欠落）を吸収。hashの安定性を保証するための唯一の場所。
    raw_store.py              # S3 put/get + key生成（案A）
    time.py                   # job_start_at生成など（任意）
    errors.py                 # 例外クラス定義（C-3で確定）

  repos/                      # DBアクセス（テーブル境界を守る）
    __init__.py
    db.py                     # コネクション/トランザクション補助
    staging_repo.py           # apl.staging専用（select_not_exists_hash / batch_upsert）

    apl/                      # apl schema repos（責務分離）
      __init__.py
      item_repo.py            # apl.item / item_image / item_market_snapshot / item_review_snapshot / shop
      item_tag_repo.py        # apl.item_tag（JOB-I-01専管を守るため分離）
      rank_repo.py            # apl.item_rank_snapshot
      genre_repo.py           # apl.genre
      tag_repo.py             # apl.tag_group / apl.tag

  sql/                        # 主要SQL（共通SQLはここに置く）
    common/
      staging_select_not_exists_hash.sql
      staging_batch_upsert.sql
      item_is_active_update.sql
    jobs/
      # ジョブ固有SQLが必要なら置く（MVPでは任意）

  specs/                      # 実装と1対1で対応する「設計の正」。コード修正時は必ずここを更新する前提とする。
    jobs/
      JOB-R-01_Ranking_ETL.md
      JOB-I-01_Item_ETL.md
      JOB-G-01_Genre_ETL.md
      JOB-T-01_Tag_ETL.md
      JOB-A-01_is_active.md
    common/
      C-1_source_structure.md
      C-2_common_processing.md
      C-3_error_retry.md
      C-4_github_actions.md

  scripts/                    # 手元実行補助（任意）
    run_local.sh
    seed_dev.sh

  tests/                      # テスト（後回しでもOK）
    test_hasher.py
    test_normalize.py
```

## 3. レイヤ責務（重要：ここで境界を固定する）

### 3.1 jobs/（handler層）

**役割**：CLI/GHAの起点  
**やること**：

- 引数解釈（env、dry-run、limit等）
- context 構築（job_start_at/run_id）
- etl_service 呼び出し
- exit code を決定

**禁止**：DBのSQL直書き、楽天APIの直叩き、S3 put の直呼び

### 3.2 services/（フロー制御）

- etl_service.py：共通の「1件単位ETL」骨格  
  fetch → normalize/hash → staging diff → S3 put → staging upsert → apl upsert
- policy.py：当日処理対象の抽出  
  staging(entity=item) 起点で「当日更新分」集合を作る（JOIN含む）

**禁止**：テーブル名直書きのSQL（repos/sqlへ）

### 3.3 clients/（外部API）

- rakuten_client.py：API呼び出しを集約
- リトライ・レート制御・タイムアウトなどは C-3 で仕様確定し、ここで実装

### 3.4 core/（純粋部品）

- hasher / normalize：差分判定のコア（再現性が命）
- raw_store：S3 key生成と put/get
- config / logging：環境依存の吸収

### 3.5 repos/（DBアクセス）

- staging_repo.py：staging専用
- repos/apl/*_repo.py：aplテーブル単位で責務分離

**狙い**：ジョブ責務境界（例：item_tagはJOB-I-01のみ）を repo分割で守る

## 4. ジョブ ↔ ファイル対応表（迷子防止）

| ジョブ | handler | 主に触るservice/policy | 主に触るrepo |
| --- | --- | --- | --- |
| JOB-R-01 | jobs/ranking_job.py | services/etl_service.py + policy(genre list) | apl/rank_repo.py + staging_repo.py |
| JOB-I-01 | jobs/item_job.py | services/etl_service.py + policy(item_code list) | apl/item_repo.py + apl/item_tag_repo.py + staging_repo.py |
| JOB-G-01 | jobs/genre_job.py | policy(staging(item)→item→genreId) | apl/genre_repo.py + staging_repo.py |
| JOB-T-01 | jobs/tag_job.py | policy(staging(item)→item→item_tag→tagId) | apl/tag_repo.py + staging_repo.py |
| JOB-A-01 | jobs/is_active_job.py | （専用のupdateフローでも可） | sql/common/item_is_active_update.sql（repo経由で実行） |

## 5. “後で決める”項目（この段階で確定しない）

- 各モジュールの Pythonシグネチャ（I/F） → C-2
- エラー種別・リトライ戦略 → C-3
- GHAのYAML・権限・Secrets命名 → C-4
- tag同期方式（置換 or upsert+削除）などの詳細 → ジョブ仕様に従いC-2で実装設計
