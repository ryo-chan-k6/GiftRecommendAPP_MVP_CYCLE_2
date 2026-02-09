# DB設計補足仕様（is_active / staging 運用）

## 0. 目的

- FKで厳密拘束しない前提のもと、ETL運用で整合性を担保するためのルールを明文化する
- apl.staging と apl.item.is_active を「運用上の真実」として定義する

## 1. apl.staging 運用仕様（最新版台帳）

### 1.1 位置づけ（事実）

- apl.staging は **「最新raw参照台帳」**であり、履歴は持たない
- raw履歴は S3 に immutable 保存される

### 1.2 主キー・一意制約（事実）

- unique：(source, entity, source_id)

| 列 | 意味 |
| --- | --- |
| source | データ供給源（例：rakuten） |
| entity | データ種別（ranking/item/genre/tag） |
| source_id | 供給元ID（itemCode / genreId / tagId / ranking genreId 等） |
| content_hash | 正規化済みコンテンツのhash（差分判定の真実） |
| s3_key | 最新rawのS3キー |
| etag | S3のETag（取得できる場合） |
| saved_at | S3に保存した時刻（rawの観測時刻） |

### 1.3 更新ルール（確定）

- 差分あり（hash不一致）の場合のみ更新する（MVP）
- 更新順序：S3 put 成功 → staging upsert

**差分なしの場合**

- S3 putしない
- stagingも更新しない（saved_at を動かさない）

**理由（推論）**  
stagingのsaved_atは「最新rawの観測時刻」なので、差分なしで触ると“更新されたように見える”ノイズになる。

### 1.4 「当日更新分」の定義（確定）

- “当日”は暦日で定義する（job_start_at の当日0:00）
- 後続ジョブは saved_at >= :day_start を基準に入力集合を作る
- 例：Genre/Tagは staging(item) を起点に “当日更新された item” に紐づくIDだけ処理する

### 1.5 参照ルール（重要）

- stagingは入力集合を直接持たない（属性を保持しない）
- 例：genreIdは staging(item) には無い
- 必要な属性は apl.item 等と JOIN して得る

## 2. apl.item.is_active 運用仕様（最終真偽）

### 2.1 位置づけ（事実）

- apl.item.is_active はアプリ参照時の最終的な有効/無効フラグ
- 更新専管ジョブ：JOB-A-01 のみ

### 2.2 判定条件（確定：MVP）

is_active = true の条件：

- item が参照する genre が存在する
- item が参照する shop が存在する
- tag は条件に含めない（MVP）

### 2.3 実装規約（確定）

- SQLの EXISTS で判定
- IS DISTINCT FROM を使い無駄更新を避ける
- 変更行のみ updated_at = now()

### 2.4 運用上の意味（推論）

- 「不整合（genre/shop欠落）」は、FK制約ではなく is_active=false に吸収する
- 後続（ランキング表示・レコメンド）は is_active をJOIN条件にすれば世界が崩れない

## 3. 典型パターン（運用シナリオ）

### 3.1 itemは取れたがgenreが未取得

- Item ETL → apl.item upsert
- Genre ETLが未実行 or 失敗 → apl.genre に無い
- is_active 更新 → false
- 次回Genre ETL成功 → is_active 更新で true になる

### 3.2 itemは取れたがshopが欠落（shop upsert漏れ等）

- is_active 更新で false に落ちる
- shop upsertを修正し再実行 → trueに復帰

## 4. 推奨インデックス（性能の最低限）

### 4.1 apl.staging

既存：(source, entity, source_id) unique

推奨追加：

- (entity, saved_at)（既存あり）
- (source, entity, saved_at)（当日抽出のフィルタに効く場合）

### 4.2 apl.item

- item_code unique（前提）
- rakuten_shop_code（JOIN用）
- genre_id（JOIN用）
- is_active（絞り込み用）

## 5. D-1 Done（受け入れ条件）

- stagingが「最新版台帳」であることが明文化されている
- 当日更新分の定義が day_start 基準で統一されている
- is_active の専管・判定条件・SQL規約が明文化されている

