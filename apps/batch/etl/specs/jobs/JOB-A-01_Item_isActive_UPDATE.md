# ジョブ仕様書（JOB-A-01 Item is_active 更新）

## 1. 概要

| 項目 | 内容 |
| --- | --- |
| ジョブID | JOB-A-01 |
| ジョブ名 | Item is_active 更新 |
| 目的 | apl.item に対して is_active を一元的に確定する |
| 主な役割 | 「アプリ世界に存在してよい item かどうか」を最終判断する |
| 再実行特性 | 冪等（何度実行しても結果は同一） |

## 2. 重要ルール（責務境界）

### 2.1 更新してよいもの

**DB**

- apl.item.is_active
- apl.item.updated_at

### 2.2 更新してはいけないもの

- apl.item のその他カラム
- apl.item_tag
- apl.genre
- apl.tag / apl.tag_group
- apl.item_rank_snapshot
- apl.staging
- S3（一切触らない）

is_active はこのジョブだけが更新する。  
他ジョブは「触らない」ことで整合性を担保する。

## 3. 前提・依存

### 3.1 前提ジョブ（必須）

- JOB-R-01（Item ETL）
- JOB-I-01（Item ETL）
- JOB-G-01（Genre ETL）
- JOB-T-01（Tag ETL）

is_active は全データが揃ったあとにのみ確定するため、必ず最後に実行する。

## 4. 対象レコード（更新対象）

### 4.1 対象テーブル

- apl.item（MVPでは全件対象）

MVPでは「当日更新分だけ」ではなく、毎回全itemを再評価する方針とする。

**理由（事実＋推論）**

- 条件が JOIN 依存（genre / shop）
- 過去itemの状態が変わる可能性がある
- 件数がまだ小さい前提

## 5. is_active 判定仕様（確定）

### 5.1 判定条件（MVP）

apl.item.is_active = true となる条件：

- genre が存在する
- shop が存在する
- tag は MVPでは is_active 条件に含めない

### 5.2 判定ロジック（概念）

```
if exists(apl.genre where genre.rakuten_genre_id = item.rakuten_genre_id)
   and exists(apl.shop where shop.rakuten_shop_code = item.rakuten_shop_code)
then
   is_active = true
else
   is_active = false
```

## 6. 実装方針（重要）

### 6.1 SQLで一括更新

- ループ処理は禁止
- 1本の UPDATE 文で完結させる

### 6.2 無駄更新防止

- IS DISTINCT FROM を使用し、値が変わらない行は更新しない

### 6.3 updated_at の扱い

- 更新対象になった行のみ updated_at = now() を明示設定

## 7. 処理フロー

1. apl.item を対象に UPDATE 文を実行
2. is_active を条件に応じて true / false に設定
3. 更新件数を取得
4. ログ出力
5. 正常終了

## 8. SQL仕様（概念）

```sql
update apl.item i
set
  is_active = case
    when exists (
      select 1
      from apl.genre g
      where g.rakuten_genre_id = i.rakuten_genre_id
    )
    and exists (
      select 1
      from apl.shop s
      where s.rakuten_shop_code = i.rakuten_shop_code
    )
    then true
    else false
  end,
  updated_at = now()
where
  i.is_active is distinct from
  case
    when exists (
      select 1
      from apl.genre g
      where g.rakuten_genre_id = i.rakuten_genre_id
    )
    and exists (
      select 1
      from apl.shop s
      where s.rakuten_shop_code = i.rakuten_shop_code
    )
    then true
    else false
  end;
```

※ 実SQLは `sql/item_is_active_update.sql` として切り出す想定。

## 9. 冪等性・再実行時の期待結果

再実行しても：

- is_active の値は変わらない
- updated_at は「変化があった行のみ」更新
- 他テーブルに副作用なし

## 10. ログ・メトリクス

| 指標 | 内容 |
| --- | --- |
| items_total | item総数 |
| items_updated | is_activeが変更された件数 |
| active_items | is_active=true件数 |
| inactive_items | is_active=false件数 |
| duration_sec | 実行時間 |

## 11. エラー時の扱い

| 事象 | 方針 |
| --- | --- |
| SQL失敗 | ジョブ失敗（exit != 0） |
| 一部失敗 | 発生しない（単一UPDATE） |
| 再実行 | 常に安全 |

## 12. Done定義

- is_active が定義通り一意に確定している
- 再実行しても結果が変わらない
- アプリ・ランキング参照時に is_active だけを見れば良い状態

## B-2 ジョブ入出力仕様（JOB-A-01）

### 1. 入力（DB）

| ソース | テーブル | 用途 |
| --- | --- | --- |
| DB | apl.item | is_active更新対象 |
| DB | apl.genre | genre存在確認 |
| DB | apl.shop | shop存在確認 |

### 2. 入力（API / S3）

なし

### 3. 出力（DB）

#### 3.1 apl.item

| 更新種別 | カラム | 内容 |
| --- | --- | --- |
| update | is_active | 判定条件に基づき true / false |
| update | updated_at | 変更があった行のみ now() |

### 4. 出力（S3）

なし
