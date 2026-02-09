# ジョブ仕様書（JOB-T-01 Tag ETL）

## 1. 概要

| 項目 | 内容 |
| --- | --- |
| ジョブID | JOB-T-01 |
| ジョブ名 | Tag ETL |
| 目的 | 楽天タグ情報を取得し、rawをS3にimmutable保存しつつ、参照用の apl.tag_group / apl.tag を最新状態に更新する |
| 主な役割 | 商品に付与されるタグ定義（グループ＋詳細）の正規化・最新化 |
| 再実行特性 | 冪等（hash差分＋upsertにより再実行安全） |

## 2. 重要ルール（責務境界）

### 2.1 更新してよいもの

**S3**

- `raw/source=rakuten/entity=tag/...`

**DB**

- apl.staging（entity=tag）
- apl.tag_group
- apl.tag

### 2.2 更新してはいけないもの

- apl.item / apl.item_tag（※ item_tagはJOB-I-01専管）
- apl.genre
- apl.item.is_active
- apl.item_rank_snapshot

Tag ETL は「タグ定義そのもの」だけを管理する。  
「どの商品にどのタグが付くか」は一切関与しない。

## 3. 前提・依存

### 3.1 前提ジョブ

- JOB-I-01（Item ETL）完了後  
  理由：処理対象タグは item に実際に付与された tagId のみとするため。

### 3.2 外部依存

- Rakuten API：[楽天市場タグ検索API](https://app.rakuten.co.jp/services/api/IchibaTag/Search/20140222)
- S3：raw bucket
- DB：Supabase Postgres（apl schema）

## 4. 当日処理対象（入力集合の定義）

### 4.1 入力集合（確定）

**基準テーブル**

- apl.staging(entity=item)：当日更新された item の集合定義
- apl.item_tag：item に付与された tagId の参照

**抽出ロジック（重要）**

1. apl.staging(entity=item) から当日更新された itemCode を抽出
2. itemCode → item_id を解決
3. apl.item_tag と JOIN し、付与された rakuten_tag_id を取得
4. DISTINCT で tagId 一覧を作成

**SQLイメージ（概念）**

```sql
select distinct it.rakuten_tag_id
from apl.staging s
join apl.item i
  on i.rakuten_item_code = s.source_id
join apl.item_tag it
  on it.item_id = i.id
where s.source = 'rakuten'
  and s.entity = 'item'
and s.saved_at >= :day_start
  and it.rakuten_tag_id is not null;
```

「当日更新された item に実際に付与された tag だけ」を対象とする  
＝ 無駄な全タグクロールをしない
  - `:day_start` は `job_start_at` の当日0:00（UTC）を採用

## 5. 処理フロー

1. 当日更新された itemCode を apl.staging(entity=item) から抽出
2. apl.item / apl.item_tag と JOIN して tagId 一覧を取得
3. tagId ごとに Rakuten Tag API を呼び出し
4. レスポンスを正規化
5. 正規化JSONから content_hash を生成
6. apl.staging(entity=tag) を参照し hash差分判定
7. 差分ありのみ S3 に raw 保存
8. apl.staging(entity=tag) を upsert
9. apl.tag_group を upsert
10. apl.tag を upsert
11. 件数・差分数をログ出力

## 6. 正規化・hash方針

### 6.1 正規化目的

タグ定義は比較的安定しているが、以下が変わり得るため定義単位でhash管理する。

- 表示名
- グループ構成
- 並び順

### 6.2 正規化ルール（MVP）

- JSONキー順の安定化
- tag_group → tag の親子構造を明示
- 取得時刻・APIメタ情報は hash対象外

## 7. S3 raw 保存仕様（tag）

| 項目 | 内容 |
| --- | --- |
| bucket | giftrecommend-raw-<env> |
| key | raw/source=rakuten/entity=tag/source_id=<tagId>/hash=<contentHash>.json |
| 保存条件 | stagingに同一hashが存在しない場合のみ |

## 8. staging 更新仕様（entity=tag）

| 項目 | 内容 |
| --- | --- |
| unique key | (source, entity, source_id) |
| source_id | tagId |
| 更新内容 | content_hash, s3_key, saved_at, etag |

※ 差分なしの場合は staging を更新しない（MVP方針）

## 9. apl 反映仕様（重要）

### 9.1 apl.tag_group

| 項目 | 内容 |
| --- | --- |
| 更新方式 | upsert |
| 主キー | rakuten_tag_group_id（想定） |
| 保持内容 | group_name / sort_order 等 |

### 9.2 apl.tag

| 項目 | 内容 |
| --- | --- |
| 更新方式 | upsert |
| 主キー | rakuten_tag_id |
| 保持内容 | tag_name / group_id / sort_order 等 |

### 9.3 グループ・タグの整合性

- tag_group → tag の順で upsert
- 親 group が未登録でも同一ジョブ内で解決
- FKではなく ETL順序で整合性担保
- tag.parent_id がある場合は親tagを先に upsert する
- 親tagが取得できない場合は当該tagをスキップし、ログに記録する

## 10. 冪等性・再実行時の期待結果

- 同一タグ定義 → hash一致 → S3 putなし
- 再実行しても：
  - apl.tag_group / apl.tag の最終状態は同一
  - staging は常に最新hashを指す

## 11. ログ・メトリクス

| 指標 | 内容 |
| --- | --- |
| tag_targets | 対象タグ数 |
| api_success / api_fail | API成功/失敗 |
| diff_new_hash | 差分ありタグ数 |
| s3_put_success | S3保存件数 |
| tag_group_upserted | tag_group更新件数 |
| tag_upserted | tag更新件数 |
| duration_sec | 実行時間 |

## 12. Done定義

- 当日更新された item に紐づくタグ定義がすべて apl.tag に存在する
- 再実行してもタグ定義が壊れない
- 後続（is_active / レコメンド）が安全に参照できる

## B-2 ジョブ入出力仕様（JOB-T-01）

### 1. 入力（DB）

| ソース | テーブル | 取得項目 | 用途 |
| --- | --- | --- | --- |
| DB | apl.staging | source_id, saved_at | 当日更新された itemCode 抽出 |
| DB | apl.item | id | itemCode → item_id 解決 |
| DB | apl.item_tag | rakuten_tag_id | itemに付与された tagId 抽出 |

条件：

- apl.staging：`source='rakuten' AND entity='item' AND saved_at >= :day_start`
- apl.item_tag：`rakuten_tag_id IS NOT NULL`

### 2. 入力（API）

| entity | API | 主キー | 用途 |
| --- | --- | --- | --- |
| tag | Rakuten Tag API | tagId | タグ定義取得 |

### 3. 出力（S3 raw）

| entity | key pattern |
| --- | --- |
| tag | raw/source=rakuten/entity=tag/source_id=<tagId>/hash=<contentHash>.json |

### 4. 出力（DB：apl.staging）

| 列 | 内容 |
| --- | --- |
| source | rakuten |
| entity | tag |
| source_id | tagId |
| content_hash | 正規化hash |
| s3_key | raw key |
| saved_at / etag | S3由来 |

### 5. 出力（DB：apl）

#### 5.1 apl.tag_group

| 更新種別 | キー | 更新内容 | 備考 |
| --- | --- | --- | --- |
| upsert | rakuten_tag_group_id | グループ属性 | 親 |

#### 5.2 apl.tag

| 更新種別 | キー | 更新内容 | 備考 |
| --- | --- | --- | --- |
| upsert | rakuten_tag_id | タグ属性 | group参照 |
