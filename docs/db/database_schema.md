# データベーススキーマ仕様（Supabase）

## 概要

本システムは Supabase を使用して PostgreSQL データベースに接続しています。
pgvector 拡張を使用したベクトル検索機能も実装されています。

## データベース接続情報

- **プロバイダ**: PostgreSQL
- **接続文字列**: `DATABASE_URL` 環境変数から取得
- **拡張機能**: pgvector（ベクトル検索用）

## テーブル一覧

| DB 名 | テーブル名          | テーブル名（論理名）      | 説明                                                                |
| ----- | ------------------- | ------------------------- | ------------------------------------------------------------------- |
| apl   | user_profile        | ユーザープロファイル      | ユーザー情報を管理する。                                            |
| apl   | event               | イベントマスタ            | イベント（ユーザー共通、ユーザー個別登録）を管理する。              |
| apl   | recipient           | 贈り先相手マスタ          | 贈り先相手情報を管理する。                                          |
| apl   | event_recipient     | イベント-贈り先相手マスタ | 【多対多中間 TBL】ユーザーごとのイベント-贈り先相手情報を管理する。 |
| apl   | user_context        | ユーザーコンテキスト      | ギフト選定の条件（コンテキスト）を保存管理する。                    |
| apl   | favorite            | お気に入りマスタ          | お気に入り商品を管理する。                                          |
| apl   | recommendation      | レコメンド結果            | レコメンド結果のヘッダー情報を管理する。                            |
| apl   | recommendation_item | レコメンド結果（明細）    | レコメンド結果の明細情報を管理する。                                |

## テーブル定義

### 1. apl.user_profile（ユーザープロファイル）

認証済みユーザー情報。

| カラム名   | 型         | 制約                    | 説明                         |
| ---------- | ---------- | ----------------------- | ---------------------------- |
| id         | uuid       | PK, FK → auth.users(id) | ユーザー ID（Supabase Auth） |
| name       | varchar    | NOT NULL                | ユーザー名                   |
| role       | varchar    | DEFAULT 'USER'          | ユーザーロール（USER/ADMIN） |
| created_at | timestampz | DEFAULT now()           | 作成日時                     |

**リレーション**:

- `auth.users(id)`: id

### 2.apl.event（イベントマスタ）

レコメンド可能なイベント情報。  
ユーザー共通で利用できるイベント（父の日、母の日など）と、ユーザー個別で登録できるイベント情報（サプライズプレゼントなど）を管理する。

| カラム名           | 型         | 制約                         | 説明                                                          |
| ------------------ | ---------- | ---------------------------- | ------------------------------------------------------------- |
| id                 | uuid       | PK                           | イベント ID（UUID）                                           |
| name               | varchar    | NOT NULL                     | イベント名                                                    |
| scope              | varchar    | DEFAULT 'COMMON'             | ユーザー共通イベントか否か（COMMON/PRIVATE）                  |
| start_date         | timestampz | NULL 可                      | イベント開始日                                                |
| end_date           | timestampz | NULL 可                      | イベント終了日                                                |
| default_budget_min | int        | NULL 可                      | デフォルト最小予算<br>※個別のレコメンド条件設定時に上書き可能 |
| default_budget_max | int        | NULL 可                      | デフォルト最大予算<br>※個別のレコメンド条件設定時に上書き可能 |
| created_by         | uuid       | NULL 可、FK → auth.users(id) | （COMMON なら NULL、PRIVATE なら必須）                        |
| created_at         | timestampz | DEFAULT now()                | 作成日時                                                      |
| updated_at         | timestampz | NULL 可                      | 更新日時                                                      |

**インデックス**:

- `scope`
- `created_by`

**リレーション**:

- `auth.users(id)`: user_id

### 3. apl.recipient（贈り先相手マスタ）

ギフトの贈り先相手マスタ。

| カラム名      | 型         | 制約                | 説明                         |
| ------------- | ---------- | ------------------- | ---------------------------- |
| id            | uuid       | PK                  | 贈り先相手 ID（UUID）        |
| name          | varchar    | NOT NULL            | 名前                         |
| age           | int        | NULL 可             | 年齢                         |
| birthday_date | date       | NULL 可             | 誕生日（年齢の再計算に使用） |
| gender        | varchar    | NULL 可             | 性別（MALE/FEMALE）          |
| user_id       | uuid       | FK → auth.users(id) | ユーザー ID                  |
| relation      | varchar    | NULL 可             | 関係性                       |
| note          | text       | NULL 可             | 備考                         |
| created_at    | timestampz | DEFAULT now()       | 作成日時                     |
| updated_at    | timestampz | NULL 可             | 更新日時                     |

**リレーション**:

- `apl.user`: xxx

### 4. apl.event_recipient（イベント-贈り先相手マスタ）

| カラム名     | 型         | 制約                  | 説明             |
| ------------ | ---------- | --------------------- | ---------------- |
| id           | uuid       | PK                    | 管理用 ID        |
| user_id      | uuid       | FK → auth.users(id)   | ユーザー ID      |
| event_id     | uuid       | FK → apl.event.id     | イベント ID      |
| recipient_id | uuid       | FK → apl.recipient.id | 贈り先相手 ID    |
| budget_min   | int        | NULL 可               | 予算範囲（下限） |
| budget_max   | int        | NULL 可               | 予算範囲（上限） |
| created_at   | timestampz | DEFAULT now()         | 作成日時         |

`※イベント-贈り先相手の関係を管理するマスタ`

**リレーション**:

- `auth.users(id)`: user_id
- `apl.event.id`: event_id
- `apl.recipient.id`: recipient.id

### 5. apl.context（コンテキストスナップショット）

| カラム名          | 型           | 制約                  | 説明                                                   |
| ----------------- | ------------ | --------------------- | ------------------------------------------------------ |
| id                | uuid         | PK                    | 管理用 ID                                              |
| user_id           | uuid         | FK → auth.users(id)   | ユーザー ID                                            |
| event_id          | uuid         | FK → apl.event.id     | イベント ID                                            |
| recipient_id      | uuid         | FK → apl.recipient.id | 贈り先相手 ID                                          |
| budget_min        | int          | NULL 可               | 予算範囲（下限）                                       |
| budget_max        | int          | NULL 可               | 予算範囲（上限）                                       |
| features_like     | text[]       | NOT NULL, DEFAULT {}  | Embedding テキスト作成用コンテキスト（ポジティブ要素） |
| features_not_like | text[]       | NOT NULL, DEFAULT {}  | Embedding テキスト作成用コンテキスト（ネガティブ要素） |
| features_ng       | text[]       | NOT NULL, DEFAULT {}  | フィルタ条件（NG 条件）                                |
| context_text      | text         | NOT NULL              | Embedding に渡すテキスト                               |
| context_vector    | vector(1536) |                       | コンテキストベクトル                                   |
| embedding_model   | text         | NOT NULL              | Embedding モデル                                       |
| embedding_version | int          | NOT NULL, DEFAULT 1   | バージョン                                             |
| context_hash      | text         | UNIQUE                | コンテストのハッシュ値                                 |
| created_at        | timestampz   | DEFAULT now()         | 作成日時                                               |

`※過去のレコメンド条件を参照、分析するために上書きはしない想定。そのため、updated_atカラムは持たない。（MVP初期設計）`

**リレーション**:

- `auth.users(id)`: user_id
- `apl.event.id`: event_id
- `apl.recipient.id`: recipient.id

### 6. apl.favorite（お気に入りマスタ）

商品のお気に入り情報。

| カラム名     | 型         | 制約                          | 説明                                                                                         |
| ------------ | ---------- | ----------------------------- | -------------------------------------------------------------------------------------------- |
| id           | uuid       | PK                            | UUID                                                                                         |
| user_id      | uuid       | NOT NULL, FK → auth.users(id) | ユーザー ID                                                                                  |
| event_id     | uuid       | FK → apl.event.id             | イベント ID（オプション）<br>`※FKだが、指定しない場合はユーザー単位のお気に入り登録となる`   |
| recipient_id | uuid       | FK → apl.recipient.id         | 贈り先相手 ID（オプション）<br>`※FKだが、指定しない場合はユーザー単位のお気に入り登録となる` |
| item_id      | uuid       | FK → apl.item.id              | 商品 ID                                                                                      |
| created_at   | timestampz | DEFAULT now()                 | 作成日時                                                                                     |
| updated_at   | timestampz | NULL 可                       | 更新日時                                                                                     |

`※「NULLを含むとUNIQUEが効かない」ため、COALESCEでNULLを固定値に潰してUNIQUEにする。`

```
create unique index uq_favorite_scope
  on apl.favorite(
    user_id,
    coalesce(event_id, '00000000-0000-0000-0000-000000000000'::uuid),
    coalesce(recipient_id, '00000000-0000-0000-0000-000000000000'::uuid),
    item_id
  );
```

- (A, NULL, NULL, AAA) は “同じスコープ” として重複禁止になる
- (A, 誕生日, 父, AAA) と (A, 誕生日, 母, AAA) は event/recipient が違うので共存 OK
- ※ sentinel UUID は「絶対に実在しない値」を固定で使うだけです。

**ユニークキー**:

- `(user_id, event_id, recipient_id, item_id)`

**インデックス**:

- `user_id`
- `event_id`
- `recipient_id`
- `(event_id, recipient_id)` 複合インデックス

**リレーション**:

- `auth.users(id)`: useri_id
- `apl.event.id`: event_id
- `apl.recipient.id`: recipient_id
- `apl.item.id`: item_id

### 7. apl.recommendation（ヘッダー）

| カラム名   | 型         | 制約                | 説明                             |
| ---------- | ---------- | ------------------- | -------------------------------- |
| id         | uuid       | PK                  | 管理用 ID                        |
| user_id    | uuid       | FK → auth.users(id) | ユーザー ID                      |
| context_id | uuid       | FK → apl.context.id | コンテキスト ID                  |
| algorithm  | text       |                     | `pgvector_cosine / hybrid / mmr` |
| params     | jsonb      |                     | λ や重みなど                     |
| created_at | timestampz | DEFAULT now()       | 作成日時                         |

**リレーション**:

- `auth.users(id)`: user_id
- `apl.context.id`: context_id

### 8. apl.recommendation_item（明細）

| カラム名          | 型    | 制約                       | 説明                                   |
| ----------------- | ----- | -------------------------- | -------------------------------------- |
| id                | uuid  | PK                         | 管理用 ID                              |
| recommendation_id | uuid  | FK → apl.recommendation.id | レコメンド結果の ID                    |
| item_id           | uuid  | FK → apl.item.id           | 商品 ID                                |
| rank              | int   |                            | 表示順位                               |
| score             | float |                            | 最終スコア                             |
| vector_score      | float |                            | 類似度（codine 等）                    |
| rerank_score      | float |                            | MMR 等の後段                           |
| reason            | jsonb |                            | レコメンド理由（タグ一致、価格帯など） |

**ユニークキー**

- `(recommendation_id, rank)`
- `(recommendation_id, item_id)`

**リレーション**:

- `apl.recommendation`: recommendation_id
- `apl.item.id`: item_id

---

## Enum 型定義

### UserRole

- `USER`: 一般ユーザー
- `ADMIN`: 管理者

### Gender

- `MALE`: 男性
- `FEMALE`: 女性

### AgeRange

- `TEEN`: 10 代
- `TWENTIES`: 20 代
- `THIRTIES`: 30 代
- `FORTIES`: 40 代
- `FIFTIES`: 50 代
- `SIXTIES`: 60 代
- `SEVENTIES_PLUS`: 70 代以上
- `UNKNOWN`: 不明

### RelationType

- `BOSS`: 上司
- `SUBORDINATE`: 部下
- `COWORKER`: 同僚
- `CLIENT`: クライアント
- `FRIEND`: 友人
- `PARTNER`: パートナー
- `SPOUSE`: 配偶者
- `PARENT`: 親
- `CHILD`: 子供
- `SIBLING`: 兄弟姉妹
- `GRANDPARENT`: 祖父母
- `RELATIVE`: 親戚
- `TEACHER`: 教師
- `OTHER`: その他
- `UNSPECIFIED`: 未指定

### EventType

- `BIRTHDAY`: 誕生日
- `CHRISTMAS`: クリスマス
- `VALENTINE`: バレンタイン
- `WHITE_DAY`: ホワイトデー
- `MOTHERS_DAY`: 母の日
- `FATHERS_DAY`: 父の日
- `RESPECT_FOR_AGED`: 敬老の日
- `WEDDING`: 結婚式
- `BIRTH_CELEBRATION`: 出産祝い
- `MOVING`: 引っ越し
- `PROMOTION`: 昇進
- `THANKS`: 感謝
- `APOLOGY`: 謝罪
- `JOB_CHANGE`: 転職
- `ANNIVERSARY`: 記念日
- `NONE`: なし

### BudgetRange

- `U3000`: 3000 円未満
- `B3000_5000`: 3000-5000 円
- `B5000_8000`: 5000-8000 円
- `B8000_12000`: 8000-12000 円
- `B12000_20000`: 12000-20000 円
- `O20000`: 20000 円以上

<!-- ### RiskLevel

- `SAFE`: 安全
- `A_LITTLE_UNIQUE`: 少しユニーク
- `VERY_UNIQUE`: 非常にユニーク -->

## ベクトル検索

### pgvector 拡張

- **拡張名**: `vector`
- **使用テーブル**: `ProductEmbedding`, `UserIntentVector`
- **インデックス**: HNSW（推奨）
- **類似度計算**: コサイン類似度（`<=>`演算子）

### ベクトル次元数

- **text-embedding-3-small**: 768 次元
- **text-embedding-3-large**: 1536 次元

ProductEmbedding と UserIntentVector は同じ次元数である必要があります。

## Prisma 特有の機能

### Unsupported 型

`ProductEmbedding.vector`と`UserIntentVector.vector`は`Unsupported("vector")`型として定義されており、Prisma Client では直接操作できません。生 SQL クエリ（`$executeRawUnsafe`）を使用して操作します。

### マイグレーション

Prisma Migrate を使用してスキーマ変更を管理しています。
マイグレーションファイルは `apps/api/prisma/migrations/` に格納されています。
