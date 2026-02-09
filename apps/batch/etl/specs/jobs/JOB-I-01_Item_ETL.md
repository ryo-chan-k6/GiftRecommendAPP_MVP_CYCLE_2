# ジョブ仕様書（JOB-I-01 Item ETL）

## 1. 概要

| 項目 | 内容 |
| --- | --- |
| ジョブID | JOB-I-01 |
| ジョブ名 | Item ETL |
| 目的 | 商品rawを取得し、hash差分のみS3にimmutable保存しつつ、**staging（最新台帳）**と **apl（参照テーブル）**を更新する |
| 主要成果物 | apl.staging(entity=item) / apl.item / apl.item_tag / apl.item_image / apl.item_market_snapshot / apl.item_review_snapshot / apl.shop |
| 再実行特性 | 同一入力で何度実行しても最終状態が一致（冪等） |

## 2. 重要ルール（責務境界）

### 2.1 このジョブが更新してよいもの

**DB**

- apl.staging（ただし entity=item の行）
- apl.item
- apl.item_tag
- apl.item_image
- apl.item_market_snapshot
- apl.item_review_snapshot
- apl.shop

**S3**

- `raw/source=rakuten/entity=item/...` 配下への put（immutable、削除しない）

### 2.2 このジョブが更新してはいけないもの

- apl.item_rank_snapshot（JOB-R-01のみ）
- apl.genre（JOB-G-01のみ）
- apl.tag / apl.tag_group（JOB-T-01のみ）
- apl.item.is_active（JOB-A-01のみ）
- ランキングの有効/無効（item の is_active を join で判定）

## 3. 前提・依存

### 3.1 前提ジョブ

- 原則：JOB-R-01（Ranking ETL）完了後に実行  
  理由：MVP入力集合が「ランキングで見えた item_code」起点のため。

### 3.2 外部依存

- Rakuten API：[楽天市場商品検索API](https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601)
- S3：raw bucket（env分離）
- DB：Supabase Postgres（apl schema）

### 3.3 設計前提（引継ぎメモ由来の確定）

- rawはS3に immutable 保存（削除しない）
- 差分判定は hash
- staging は最新台帳（履歴を持たない）
- DB整合性はFKではなくETLで担保

## 4. 当日処理対象（入力集合の定義）

### 4.1 入力集合（MVP）

優先順位付きで入力集合を定義する。

- 第一候補（推奨）：apl.item_rank_snapshot から当日（0:00以降）に登場した rakuten_item_code を抽出
- 第二候補：ランキングETLが出力した rakuten_item_code を別途キュー/テーブルで受ける（将来拡張）
- 第三候補（保険）：手動で rakuten_item_code を渡す（CLI引数）

ここでは第一候補をMVP標準とする。

### 4.2 抽出仕様（例）

- 取得件数：上限 N（例：ランキング上位×カテゴリ数）
- 重複排除：DISTINCT rakuten_item_code
- 並び順：rank昇順、取得時間降順 等（運用で決める）
- 抽出条件（MVP）：item_rank_snapshot.fetched_at が当日0:00以降

※ 正確なSQLは apl.item_rank_snapshot のカラム設計に依存するため、**「入力SQLは差し替え可能」**として interface を固定する（C-2でpolicyに逃がす）。

## 5. 処理フロー（ステップ定義）

### 5.1 ステップ一覧

- 対象 rakuten_item_code 集合を取得（policy）
- rakuten_item_code ごとに Rakuten API を呼び出し raw JSON を取得
- raw JSON を正規化（hashの安定化のため）
- 正規化結果から content_hash を生成
- apl.staging を参照し、content_hash が既存か判定
- 差分ありのみ S3へ put（keyは後述）
- apl.staging を upsert（最新台帳更新）
- apl.item を upsert（商品参照テーブル更新）
- apl.item_tag を upsert（ジョブ専管の中間テーブル更新）
- 結果集計・ログ出力（成功/失敗/差分/保存件数）

## 6. Rakuten API 呼び出し仕様

### 6.1 入力パラメーター

| param         |     型 | 必須 | 用途                                                             |
| ------------- | -----: | :--: | ---------------------------------------------------------------- |
| applicationId | string |  ✅  | 楽天アプリ ID ([楽天ウェブサービス][1])                          |
| affiliateId   | string | 任意 | 付けると `affiliateUrl` が返る（推奨） ([楽天ウェブサービス][1]) |
| format        | string | 任意 | `json` 推奨 ([楽天ウェブサービス][1])                            |
| formatVersion |    int | 任意 | 2 推奨（フラット化）                                             |
| itemCode      | string | 任意 |                                                                  |
| genreId       |   long | 任意 | ジャンルで絞る                                                   |
| keyword       | string | 任意 | 文字列検索（必要時のみ） ([楽天ウェブサービス][1])               |
| hits / page   |    int | 任意 | ページング                                                       |
| elements      | string | 任意 | 出力フィールド絞り（通信量削減）                                 |

[1]: https://webservice.rakuten.co.jp/documentation/ichiba-item-search?utm_source=chatgpt.com "Ichiba Item Search API (version:2022-06-01)"

### 6.2. レスポンス構造

### レスポンス構造（必要部分）

```jsonc
{
  "count": 123,
  "page": 1,
  "first": 1,
  "last": 30,
  "hits": 30,
  "pageCount": 5,
  "Items": [
    {
      "Item": {
        "itemCode": "shopCode:itemId",
        "itemName": "...",
        "catchcopy": "...",
        "itemCaption": "...",
        "itemPrice": 1234,
        "itemUrl": "https://...",
        "affiliateUrl": "https://...",
        "imageFlag": 1,
        "smallImageUrls": ["https://..."],
        "mediumImageUrls": ["https://..."],
        "availability": 1,
        "taxFlag": 0,
        "postageFlag": 0,
        "creditCardFlag": 1,
        "shopCode": "...",
        "shopName": "...",
        "shopUrl": "https://...",
        "genreId": 100000,
        "tagIds": [111, 222],
        "reviewCount": 10,
        "reviewAverage": 4.23,
        "pointRate": 2,
        "pointRateStartTime": "...",
        "pointRateEndTime": "...",
        "startTime": "...",
        "endTime": "...",
        "giftFlag": 1,
        "asurakuFlag": 0,
        "asurakuArea": "...",
        "asurakuClosingTime": "..."
      }
    }
  ]
}
```

※ 実際のレスポンスは `Items / Item`（大文字）になるケースがあり、実装側で両方を受け付ける。

## 6. 正規化（normalize）仕様

### 6.1 目的（事実）

Rakuten APIのレスポンスは、順序や不要フィールドでhashが揺れる可能性があるため、hash対象データを安定化する。

### 6.2 正規化方針（MVP）

- JSONのキー順を安定化（例：ソート）
- 配列の順序が意味を持たない場合はソート（例：画像URL一覧）
- hashに影響させたくないメタ情報は除外（例：取得時刻など）
- 文字列のトリム、null/空の扱いを統一

注意：どのキーを除外/整形するかは実装で必ず固定し、仕様書（共通処理仕様書）に一覧を持つ。

## 7. S3 raw 保存仕様（entity=item）

### 7.1 bucket

`giftrecommend-raw-<env>`（dev/prod分離）

### 7.2 key

`raw/source=rakuten/entity=item/source_id=<itemCode>/hash=<contentHash>.json`

### 7.3 保存条件（重要）

- apl.staging に同一 (source, entity, source_id, content_hash) が存在しない場合のみ put する
- 既存hashの場合は put しない（S3書き込みを節約、immutable原則維持）

## 8. staging 更新仕様（entity=item）

### 8.1 unique key（確定）

`(source, entity, source_id)`

### 8.2 更新内容（確定）

- content_hash
- s3_key（最新）
- saved_at
- etag（取得できる場合）

### 8.3 更新タイミング（事実）

差分なしでも upsert してよいが、**MVPは「差分ありの場合のみ upsert」**を推奨。

理由（推論）：差分なしで saved_at 等が変わると「最新台帳」の意味が揺れるため。

※ ただし「疎通確認/監視」の観点で毎回touchしたい場合は、checked_at を別カラムで持つ拡張が自然（MVPでは不要）。

## 9. apl 反映仕様（item / item_tag）

### 9.1 apl.item

- 入力： 正規化した itemPayload
- 更新方式：upsert
- upsertキー： 
  - 入力側： itemPayload.itemCode
  - 出力側： apl.item.rakuten_item_code
- 注意：is_active は更新しない（JOB-A-01専管）

### 9.2 apl.item_tag（重要）

- 入力：
  -  正規化した itemPayload
  -  apl.item
- 更新方式：upsert（多対多）
- upsertキー： 
  - 入力側： apl.item.id, itemPayload.tagIdsの要素
  - 出力側： apl.item_tag.item_id, apl.item_tag.rakuten_tag_id

### 9.3 apl.item_image

- 入力：
  -  正規化した itemPayload
  -  apl.item
- 更新方式：delete → insert（多対多）
- トランザクション境界：item単位で delete → insert を1トランザクションにまとめる
- delete成功 → insert失敗時はロールバックし、当該itemは失敗扱い
- deleteキー： 
  - 入力側： apl.item.id
  - 出力側： apl.item_image.item_id

### 9.4 apl.item_market_snapshot

- 入力：
  -  正規化した itemPayload
  -  apl.item
- 更新方式：insert
- collected_at は job_start_at を採用（再実行時の重複抑止）

### 9.5 apl.item_review_snapshot

- 入力：
  -  正規化した itemPayload
  -  apl.item
- 更新方式：insert
- collected_at は job_start_at を採用（再実行時の重複抑止）

### 9.6 apl.shop

- 入力：
  -  正規化した itemPayload
- 更新方式：upsert
- upsertキー： 
  - 入力側： itemPayload.shopCode
  - 出力側： apl.shop.rakuten_shop_code

**方針**

- 「その item の tag を今回の取得結果で完全に置き換える」のが一貫性が高い
- 方式例：item単位で既存を削除→挿入（ただしトランザクション＋負荷注意）
<!-- - MVPではまず安全側に倒し、upsert + 不要tagの削除は後回しでも可
- ただし将来、タグ付けが変わったときに残骸が残る（推論）ため、仕様として方針を固定する必要がある
- 推奨（MVPでも）：item単位で「現行tag集合に同期」  
  実装手段は後で決めるが、仕様として「同期する」ことを明記する。 -->

## 10. 冪等性・差分耐性（期待結果）

### 10.1 同一入力で再実行した場合

- content_hash が同一 → S3 put なし
- apl.staging は変化しない（または変化させない方針）
- apl.item / apl.item_tag は upsert なので最終状態が一致

### 10.2 部分失敗時

- item単位で処理するため、1件失敗しても他件は継続可能（方針）
- ただし S3保存成功→DB失敗 のような非原子状態は起こり得る
- 次回再実行で staging が未更新なら再度S3 putが走る可能性がある
- 回避策（推論）：S3 keyが hash なので重複putしても実質同じ内容（ただしETag/課金は増える）

**MVP方針**

- S3 put 成功後に staging upsert を必ず行う（順序固定）
- DB失敗時はジョブ失敗扱い（exit code != 0）で再実行前提

## 11. ログ・メトリクス（最低限）

| 指標 | 意味 |
| --- | --- |
| targets_total | 処理対象 rakuten_item_code 数 |
| api_success / api_fail | API成功/失敗数 |
| diff_new_hash | 差分あり（新hash）件数 |
| s3_put_success / s3_put_fail | S3保存成功/失敗 |
| staging_upserted | staging更新件数 |
| item_upserted | item更新件数 |
| item_tag_upserted | item_tag更新件数 |
| duration_sec | 実行時間 |

## 12. 受け入れ条件（Done）

- 同じ入力集合で複数回実行しても最終DB状態が同じ
- 差分がない item は S3 に新規オブジェクトが増えない
- apl.staging が常に最新hashとs3_keyを指す
- apl.item_tag が「今回取得したタグ集合」と整合する（同期方針に従う）

## B-2 ジョブ入出力仕様（JOB-I-01）

### 1. 入力（DB）

| ソース | テーブル | 取得項目 | 用途 | 備考 |
| --- | --- | --- | --- | --- |
| DB | apl.item_rank_snapshot | rakuten_item_code | 処理対象 rakuten_item_code 抽出 | 抽出条件はpolicyに閉じる |

※ apl.item_rank_snapshot が無い/未整備なら、代替入力（CLI引数、固定リスト）を許容。

### 2. 入力（API：Rakuten）

| entity | API種別 | 主キー | 取得目的 | 必須項目（最低限） |
| --- | --- | --- | --- | --- |
| item | 商品詳細取得 | itemCode | item / tag抽出 | itemCode, itemName, itemPrice, affiliateUrl, genreId, tagIds, shop関連 |

※ API名（IchibaItem/Search など）はあなたの実装採用に合わせてここを確定させる。  
（この仕様書では「必要フィールドが取れること」を要件として固定）

### 3. 出力（S3 raw）

| bucket | entity | key pattern | 保存対象 | 保存条件 |
| --- | --- | --- | --- | --- |
| giftrecommend-raw-<env> | item | raw/source=rakuten/entity=item/source_id=<itemCode>/hash=<contentHash>.json | 正規化済みJSON（またはraw+normalized） | stagingに同hashが無い場合のみ |

### 4. 出力（DB：apl.staging）

#### 4.1 更新対象

apl.staging のうち `source='rakuten' AND entity='item'`

| 列 | 値 | 由来 |
| --- | --- | --- |
| source | 'rakuten' | 定数 |
| entity | 'item' | 定数 |
| source_id | <itemCode> | 入力 |
| content_hash | <contentHash> | hasher |
| s3_key | 上記key | raw_store |
| saved_at | 保存時刻 | raw_store |
| etag | S3 ETag | raw_store（取得できる場合） |

### 5. 出力（DB：apl）

#### 5.1 apl.item

| 更新種別 | キー | 更新内容 | 備考 |
| --- | --- | --- | --- |
| upsert | rakuten_item_code | 商品属性一式 | is_active は触らない |

#### 5.2 apl.item_tag

| 更新種別 | キー | 更新内容 | 備考 |
| --- | --- | --- | --- |
| upsert（＋同期） | (item_id, rakuten_tag_id) | 紐付け | JOB-I-01のみ更新。同期方針を採用する |

#### 5.3 apl.item_image

| 更新種別 | キー | 更新内容 | 備考 |
| --- | --- | --- | --- |
| delete → insert | (item_id, size, sort_order) | 画像URL一覧（small/medium） | `apl.item_image` の unique は `(item_id, size, sort_order)`。再実行時に同一画像集合へ同期する方針（item単位で置換 or upsert＋不要行削除）。 |

#### 5.4 apl.item_market_snapshot

| 更新種別 | キー | 更新内容 | 備考 |
| --- | --- | --- | --- |
| insert（時系列蓄積） | (item_id, collected_at) | 価格・配送・ポイント・在庫等のスナップショット | unique は `(item_id, collected_at)`。MVPでは `collected_at` をジョブ実行時刻（例：handlerが生成する run_started_at）で明示設定することを推奨（再実行での重複抑制）。 |

#### 5.5 apl.item_review_snapshot

| 更新種別 | キー | 更新内容 | 備考 |
| --- | --- | --- | --- |
| insert（時系列蓄積） | (item_id, collected_at) | review_count / review_average のスナップショット | unique は `(item_id, collected_at)`。`collected_at` は market と同様にジョブ実行時刻を明示設定推奨。 |

#### 5.6 apl.shop

| 更新種別 | キー | 更新内容 | 備考 |
| --- | --- | --- | --- |
| upsert | rakuten_shop_code | shop_name / shop_url / shop_of_the_year_flag | `apl.item.rakuten_shop_code` の参照整合性のため、item upsert 前に shop upsert する（推奨）。 |

### 6. “当日処理対象”の入出力境界（要点）

- 入力集合の定義：apl.item_rank_snapshot 起点
- 差分判定の定義：apl.staging 起点
- 正規化/Hash：hasher規約に依存（共通処理仕様書で確定）
- 出力の正：staging（最新）＋S3（履歴）＋apl（参照）
