# JOB-E-01 Embedding Source Build（商品ベクトル入力テキスト生成）仕様書（MVP）

## 1. 目的
`apl.item_feature_view` を入力として、商品ベクトル生成用の **source_text** を作成し、差分判定用の **source_hash** を算出して `apl.item_embedding_source` に保存する。  
後続の JOB-E-02（Embedding Build）は **source_hash 差分**を基準に、必要な商品だけEmbedding再生成する。

---

## 2. 入力

### 2.1 入力ビュー
- `apl.item_feature_view`

### 2.2 対象条件（確定）
- `is_active = true`
- **当日更新分のみ**：`feature_updated_at >= :job_start_at`

> `feature_updated_at` は `apl.item_feature_view` にて、item/market/review/ranking/genre/tag の更新時刻を合成した値を利用する。

### 2.3 取得カラム（最低限）
- `item_id`
- `item_name`
- `catchcopy`
- `item_caption`
- `genre_name`
- `tag_names`（配列）
- `item_price`（= price_yen）
- `item_updated_at`
- `feature_updated_at`

---

## 3. 出力

### 3.1 出力テーブル
- `apl.item_embedding_source`

### 3.2 一意性（確定）
- `UNIQUE (item_id)`（MVPでは item_id 単独で一意にする）

### 3.3 カラム
| カラム | 型 | 役割 |
|---|---|---|
| item_id | uuid | apl.item の内部ID |
| source_version | int | 生成ロジックのバージョン（テンプレ変更時にインクリメント） |
| source_text | text | Embedding入力テキスト |
| source_hash | varchar | `sha256(source_text)` |
| created_at / updated_at | timestamptz | 監査用 |

---

## 4. source_text 生成ルール（確定）

### 4.1 引数（確定）
- `item_name: 商品名`
- `catchcopy: キャッチコピー`
- `item_caption: 商品説明`
- `genre_name: ジャンル名`
- `tag_names: タグ名リスト（最大30件）`
- `price_yen: 価格（円）`

### 4.2 正規化（推奨・実装必須）
| 対象 | ルール |
|---|---|
| 改行 | `\r\n` → `\n` に統一 |
| 空白 | 連続空白を1つに圧縮（タブ含む） |
| HTML | 簡易でOK：`<...>` を除去（タグ除去） |
| caption | 最大 **2000文字**にトリム（末尾切り捨て） |
| tag_names | 最大 **30件**まで（超過は先頭30件） |

> `apl.item_feature_view` 側でも `caption` と `tag_names` の上限を適用し、二重で安全側に寄せる。

### 4.3 テンプレ（確定）
空値は「その行を出さない（行ごと省略）」を推奨。

```text
商品名: {item_name}
キャッチコピー: {catchcopy}
商品説明: {item_caption}

ジャンル: {genre_name}
タグ: {tag_names_csv}
価格: {price_yen}円
```

- `tag_names_csv` は `", "` 区切り（例：`タグ: A, B, C`）
- `price_yen` は整数（NULLの場合は価格行を省略）

---

## 5. 差分判定（冪等性）

### 5.1 hash算出
- `source_hash = sha256(source_text)`（16進文字列）

### 5.2 upsert条件
- `ON CONFLICT (item_id, source_version) DO UPDATE ...`
- 更新は **source_hash が変化した場合のみ**行う（無駄更新防止）

推奨SQL例：

```sql
insert into apl.item_embedding_source (item_id, source_version, source_text, source_hash, updated_at)
values (:item_id, :source_version, :source_text, :source_hash, now())
on conflict (item_id, source_version) do update
set
  source_text = excluded.source_text,
  source_hash = excluded.source_hash,
  updated_at = now()
where
  apl.item_embedding_source.source_hash is distinct from excluded.source_hash;
```

---

## 6. 例外・エラーハンドリング
- 入力不足（item_name など必須相当が空）：
  - MVPでは **空文字でも生成して良い**（ただしsource_textが極端に短い場合はログにWARN）
- DBエラー：
  - 対象itemを failure としてカウントし継続（JOB単位の failure_rate 判定はC-3に従う）

---

## 7. ログ・メトリクス（最低限）
- `total_targets`
- `upsert_inserted`
- `upsert_updated`
- `skipped_no_diff`
- `failure_count`
- `failure_rate`

---

## 8. テスト方針（Unit/Component）
- Unit：正規化が安定する（順序揺れ/空白/HTML混入で同じsource_textになる）
- Unit：同一source_textで hash が同一
- Component：差分なしで `WHERE ... IS DISTINCT FROM` が効いて updated_at が変わらない
