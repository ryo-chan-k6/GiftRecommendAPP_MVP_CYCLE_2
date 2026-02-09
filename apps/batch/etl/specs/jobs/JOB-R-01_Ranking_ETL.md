# ジョブ仕様書（JOB-R-01 Ranking ETL）

## 1. 概要

| 項目 | 内容 |
| --- | --- |
| ジョブID | JOB-R-01 |
| ジョブ名 | Ranking ETL |
| 目的 | 楽天ランキングAPIから取得したランキング結果を raw としてS3にimmutable保存し、参照用の `apl.item_rank_snapshot` を更新する |
| 主な役割 | 「当日どの商品が市場に露出しているか」を確定させ、後続ETL（Item ETL）の入力集合を作る |
| 再実行特性 | 冪等（hash差分＋snapshot設計により再実行安全） |

## 2. 重要ルール（責務境界）

### 2.1 更新してよいもの

**S3**

- `raw/source=rakuten/entity=ranking/...`

**DB**

- apl.staging（entity=ranking）
- apl.item_rank_snapshot

### 2.2 更新してはいけないもの

- apl.item / apl.item_tag
- apl.genre / apl.tag / apl.tag_group
- apl.item.is_active

Ranking ETL は「事実としてのランキング結果を記録するだけ」。  
商品の正規化・有効性判断は一切しない。

## 3. 前提・依存

### 3.1 前提ジョブ

なし（最初に実行されるジョブ）

### 3.2 外部依存

- Rakuten API：[楽天市場ランキングAPI](https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20220601)
- S3：raw bucket
- DB：Supabase Postgres（apl schema）

## 4. 当日処理対象（入力集合）

### 4.1 入力定義

- ランキングAPIの取得単位：ジャンル単位
- 総合ランキング / カテゴリランキング
- 対象ジャンル：MVPでは固定ジャンルIDリスト（apl.target_genre_config）

※ どのジャンルを回すかは policy 層に閉じる。

## 5. 処理フロー

- 対象ジャンルID一覧を取得（policy）  
    対象ジャンルは、apl.target_genre_configの`is_enabled = true`の`rakuten_genre_id`。
- ジャンルごとに Rakuten Ranking API を呼び出し
- レスポンスは `Items / Item`（大文字）と `items`（小文字）の両方を許容
- レスポンスを正規化
- 正規化JSONから content_hash を生成
- apl.staging(entity=ranking) を参照し hash差分判定
- 差分ありのみ S3 に raw 保存
- apl.staging を upsert
- ランキング結果を apl.item_rank_snapshot に反映
- 結果件数をログ出力

## 6. 正規化・hash方針

- JSONキー順の安定化
- 順位配列は rank順で固定
- hash対象外
  - API取得時刻
  - pagination情報

## 7. S3 raw 保存仕様（ranking）

| 項目 | 内容 |
| --- | --- |
| bucket | giftrecommend-raw-<env> |
| key | raw/source=rakuten/entity=ranking/source_id=<genreId>/hash=<contentHash>.json |
| 保存条件 | stagingに同一hashが存在しない場合のみ |

## 8. staging 更新仕様（entity=ranking）

| 項目 | 内容 |
| --- | --- |
| unique key | (source, entity, source_id) |
| source_id | genreId |
| 更新内容 | content_hash, s3_key, saved_at, etag |

## 9. apl 反映仕様（重要）

### 9.1 apl.item_rank_snapshot

- 性質：スナップショット（当日・当runの市場露出）
- 更新方式：insert

**推奨（MVP）**

- 入力： 正規化した itemPayload
- 更新方式：insert
- lastBuildDate を apl.item_rank_snapshot.last_build_date に保存する
- 同一 genre に対して、APIの lastBuildDate が既存の last_build_date と一致する場合は insert しない（重複防止）
- collected_at は last_build_date と同一値を採用する（同一ランキングの重複insertをDB制約で防止）
- fetched_at は ETL の job_start_at を保存する（後続の Item ETL 入力抽出で使用）
- insert は ON CONFLICT DO NOTHING を許容する

「今日はこのitemがrank何位だった」という事実ログ。  
後続の Item ETL はこのテーブルだけを見ればよい。

## 10. 冪等性・再実行時の期待結果

- 同一ランキング結果 → hash一致 → S3 putなし
- 再実行しても：
  - stagingは最新hashを維持
  - last_build_date が同一なら item_rank_snapshot は追加されない

## 11. ログ・メトリクス

| 指標 | 内容 |
| --- | --- |
| genre_total | 対象ジャンル数 |
| api_success / api_fail | API成功/失敗 |
| diff_new_hash | 差分あり件数 |
| ranking_items_total | ランキング取得 item 数 |
| snapshot_inserted | snapshot登録件数 |
| duration_sec | 実行時間 |

## 12. Done定義

- rawがimmutableで蓄積されている
- stagingが最新rankingを指す
- apl.item_rank_snapshot から Item ETLの入力集合が作れる

## B-2 ジョブ入出力仕様（JOB-R-01）

### 1. 入力（API）

| API | 単位 | 主キー | 用途 |
| --- | --- | --- | --- |
| Rakuten Ranking API | genre | genreId | 市場露出item抽出 |

### 2. 出力（S3 raw）

| entity | key pattern |
| --- | --- |
| ranking | raw/source=rakuten/entity=ranking/source_id=<genreId>/hash=<contentHash>.json |

### 3. 出力（DB：apl.staging）

| 列 | 内容 |
| --- | --- |
| source | rakuten |
| entity | ranking |
| source_id | genreId |
| content_hash | 正規化hash |
| s3_key | raw key |
| saved_at / etag | S3由来 |

### 4. 出力（DB：apl）

#### 4.1 apl.item_rank_snapshot

| 更新種別 | キー | 内容 |
| --- | --- | --- |
| insert | (rakuten_genre_id, rakuten_item_code, collected_at) | 全項目 |

※ Item ETL の入力抽出は `fetched_at` が当日0:00以降のレコードを対象とする。

