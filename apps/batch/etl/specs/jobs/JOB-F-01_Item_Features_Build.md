# JOB-F-01 Item Features Build（特徴量集計）仕様書（MVP）

## 1. 目的

`apl.item_feature_view` を入力として、推薦APIで使用する特徴量を集計し  
`apl.item_features` に保存する。

## 2. 入力

### 2.1 入力ビュー
- `apl.item_feature_view`

### 2.2 対象条件（確定）
- `is_active = true`
- **当日更新分のみ**：`feature_updated_at >= :day_start`

> `:day_start` は job_start_at の当日0:00（UTC）

### 2.3 取得カラム（最低限）
- `item_id`
- `item_price`（market snapshot由来）
- `point_rate`
- `availability`
- `review_average`
- `review_count`
- `rank`
- `rakuten_genre_id`
- `rakuten_tag_ids`
- `feature_updated_at`

## 3. 出力

### 3.1 出力テーブル
- `apl.item_features`

### 3.2 一意性（確定）
- `UNIQUE (item_id)`（item_id 単独で一意）

### 3.3 カラム
| カラム | 型 | 役割 |
|---|---|---|
| item_id | uuid | apl.item の内部ID |
| price_yen | int | 価格（円） |
| price_log | float | `log(price_yen)`（price_yen > 0 のみ） |
| point_rate | int | ポイント倍率 |
| availability | int | 在庫/販売状態 |
| review_average | float | 平均レビュー |
| review_count | int | レビュー件数 |
| review_count_log | float | `log(review_count)`（review_count > 0 のみ） |
| rank | int | 最新ランキング |
| popularity_score | float | 人気度スコア（後述） |
| rakuten_genre_id | bigint | ジャンルID |
| tag_ids | int[] | 楽天タグID配列 |
| features_version | int | 特徴量ロジックのバージョン |
| created_at / updated_at | timestamptz | 監査用 |

## 4. 変換ルール

### 4.1 price_log
- `price_yen > 0` の場合のみ `log(price_yen)` を算出
- それ以外は `NULL`

### 4.2 review_count_log
- `review_count > 0` の場合のみ `log(review_count)` を算出
- それ以外は `NULL`

### 4.3 popularity_score

人気度は「レビュー件数の多さ」と「レビュー品質」を掛け合わせて算出する。

```
quality = clamp(review_average / 5.0, 0.0, 1.0)
popularity_score = quality * log1p(review_count)
```

- `review_count` が `NULL` の場合は `NULL`
- `review_count <= 0` の場合は `0.0`
- `review_average` が `NULL` の場合は `quality = 0.0`

## 5. upsert 条件（冪等性）

`apl.item_features` への反映は **差分がある場合のみ**更新する。

- `ON CONFLICT (item_id) DO UPDATE ...`
- いずれかの特徴量が `IS DISTINCT FROM` の場合のみ更新

## 6. ログ・メトリクス（最低限）

- `total_targets`
- `upsert_inserted`
- `upsert_updated`
- `skipped_no_diff`
- `failure_count`
- `failure_rate`

## 7. 実行順序（ジョブネット）

- `JOB-A-01`（is_active更新）完了後に実行する
- `JOB-E-01`（Embedding Source Build）より前に実行する
