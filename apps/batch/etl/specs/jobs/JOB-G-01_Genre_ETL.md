# ジョブ仕様書（JOB-G-01 Genre ETL）

## 1. 概要

| 項目 | 内容 |
| --- | --- |
| ジョブID | JOB-G-01 |
| ジョブ名 | Genre ETL |
| 目的 | 楽天ジャンル情報を取得し、rawをS3にimmutable保存しつつ、参照用の apl.genre を最新状態に更新する |
| 主な役割 | 商品が属するジャンル階層の正規化・最新化 |
| 再実行特性 | 冪等（hash差分＋upsertにより再実行安全） |

## 2. 重要ルール（責務境界）

### 2.1 更新してよいもの

**S3**

- `raw/source=rakuten/entity=genre/...`

**DB**

- apl.staging（entity=genre）
- apl.genre

### 2.2 更新してはいけないもの

- apl.item / apl.item_tag
- apl.tag / apl.tag_group
- apl.item.is_active
- apl.item_rank_snapshot

Genre ETL は「ジャンル定義を最新化するだけ」。  
商品・ランキング・有効性には一切関与しない。

## 3. 前提・依存

### 3.1 前提ジョブ

- JOB-I-01（Item ETL）完了後  
  理由：処理対象ジャンルは item が参照している genreId のみとするため。

### 3.2 外部依存

- Rakuten API：[楽天市場ジャンル検索API](https://app.rakuten.co.jp/services/api/IchibaGenre/Search/20170711)
- S3：raw bucket
- DB：Supabase Postgres（apl schema）

## 4. 当日処理対象（入力集合の定義）

### 4.1 入力集合（確定）

**基準テーブル**

- apl.staging（entity=item） ※「当日更新された item の集合」を定義するために使用
- apl.item ※ genreId を取得するために参照
  
**抽出ロジック（重要）**

1. 当日更新された item を `apl.staging(entity=item)` から抽出
2. 抽出した itemCode（source_id）をキーに `apl.item` と JOIN
3. `apl.item.rakuten_genre_id` を DISTINCT 抽出

**SQLイメージ（概念）**

```sql
select distinct i.rakuten_genre_id
from apl.staging s
join apl.item i
  on i.rakuten_item_code = s.source_id
where s.source = 'rakuten'
  and s.entity = 'item'
  and s.saved_at >= :job_start_at
  and i.rakuten_genre_id is not null;
```

**条件**

- DISTINCT rakuten_genre_id
- NULL除外
- 対象は「当日（＝本ジョブ実行対象として更新された）item」に限定

「当日処理対象の item に紐づく genre のみを取得する」
＝ 不要な全ジャンルクロールをしない、かつ stagingを“当日集合の定義”として正しく利用する

## 5. 処理フロー

1. apl.staging(entity=item) から「当日更新された itemCode 一覧」を抽出
2. itemCode をキーに apl.item と JOIN し、 rakuten_genre_id 一覧を取得
3. genreId ごとに Rakuten Genre API を呼び出し
4. レスポンスを正規化
5. 正規化JSONから content_hash を生成
6. apl.staging(entity=genre) を参照し hash差分判定
7. 差分ありのみ S3 に raw 保存
8. apl.staging(entity=genre) を upsert
9. apl.genre を upsert（ジャンル階層含む）
10. 件数・差分数をログ出力

## 6. 正規化・hash方針

### 6.1 正規化目的

ジャンル定義は頻繁に変わらないが、以下が変わり得るため定義単位でhash管理する。

- 親子関係
- 表示名
- レベル

### 6.2 正規化ルール（MVP）

- JSONキー順の安定化
- 親ジャンルIDは明示的に null / 数値を統一
- 取得時刻・APIメタ情報は hash対象外

## 7. S3 raw 保存仕様（genre）

| 項目 | 内容 |
| --- | --- |
| bucket | giftrecommend-raw-<env> |
| key | raw/source=rakuten/entity=genre/source_id=<genreId>/hash=<contentHash>.json |
| 保存条件 | stagingに同一hashが存在しない場合のみ |

## 8. staging 更新仕様（entity=genre）

| 項目 | 内容 |
| --- | --- |
| unique key | (source, entity, source_id) |
| source_id | genreId |
| 更新内容 | content_hash, s3_key, saved_at, etag |

※ 差分なしの場合は stagingを更新しない（MVP方針）

## 9. apl 反映仕様（重要）

### 9.1 apl.genre

- 入力： 正規化した itemPayload
- 更新方式：upsert
- upsertキー： 
  - 入力側： itemPayload.genreId
  - 出力側： apl.genre.rakuten_genre_id
- 注意：is_active は更新しない（JOB-A-01専管）

### 9.2 階層構造の扱い（重要）

- 親ジャンルが未登録の場合：同一ジョブ内で upsert する
- 親→子の整合性は：FKではなく ETL順序とupsertで担保
- 親ジャンルを先に upsert し、親が取得できない場合は当該genreの反映をスキップしてログに記録する

推論：  
「親がないから子を入れられない」設計はバッチと相性が悪いため、最終的に整合すればよいという思想を採用。

## 10. 冪等性・再実行時の期待結果

- 同一ジャンル定義 → hash一致 → S3 putなし
- 再実行しても：
  - apl.genre の最終状態は同一
  - stagingは常に最新hashを指す

## 11. ログ・メトリクス

| 指標 | 内容 |
| --- | --- |
| genre_targets | 対象ジャンル数 |
| api_success / api_fail | API成功/失敗 |
| diff_new_hash | 差分ありジャンル数 |
| s3_put_success | S3保存件数 |
| genre_upserted | apl.genre更新件数 |
| duration_sec | 実行時間 |

## 12. Done定義

- 市場に登場した商品のジャンルがすべて apl.genre に存在する
- 再実行してもジャンル定義が壊れない
- 後続（Tag / is_active）が安全に参照できる

## B-2 ジョブ入出力仕様（JOB-G-01）

### 1. 入力（DB）

| ソース | テーブル | 取得項目 | 用途 |
| --- | --- | --- | --- |
| DB | apl.staging | source_id, saved_at | 当日更新された itemCode 抽出 |
| DB | apl.item | rakuten_genre_id | itemCode に紐づく genreId 取得 |

条件：
- apl.staging: `source='rakuten' AND entity='item' AND saved_at >= :job_start_at`
- apl.item: `rakuten_genre_id IS NOT NULL`

### 2. 入力（API）

| entity | API | 主キー | 用途 |
| --- | --- | --- | --- |
| genre | Rakuten Genre API | genreId | ジャンル定義取得 |

### 3. 出力（S3 raw）

| entity | key pattern |
| --- | --- |
| genre | raw/source=rakuten/entity=genre/source_id=<genreId>/hash=<contentHash>.json |

### 4. 出力（DB：apl.staging）

| 列 | 内容 |
| --- | --- |
| source | rakuten |
| entity | genre |
| source_id | genreId |
| content_hash | 正規化hash |
| s3_key | raw key |
| saved_at / etag | S3由来 |

### 5. 出力（DB：apl）

#### 5.1 apl.genre

| 更新種別 | キー | 更新内容 | 備考 |
| --- | --- | --- | --- |
| upsert | rakuten_genre_id | ジャンル属性一式 | 親子関係含む |