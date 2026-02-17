# 楽天市場ジャンル検索API Fetch処理 仕様書

最終更新日時: 2026-02-17 14:18:43

---

## 1. 目的

楽天市場ジャンル検索APIを利用し、
ジャンルの親子構造を含めた全ジャンル情報を取得し、
Neon(PostgreSQL)へ保存するバッチ処理の仕様を定義する。

- raw_jsonは**最新1件のみ保持**
- 並列実行可能（複数プロセス対応）
- 中断・再実行可能
- テスト用に少量取得で停止可能

---

## 2. 全体アーキテクチャ

```mermaid
flowchart TD
  A[Start genre_id投入] --> B[fetch_state: PENDING]
  B --> C[claim: IN_PROGRESS(SKIP LOCKED)]
  C --> D[楽天API呼び出し]
  D --> E[genreテーブル UPSERT]
  D --> F[周辺genre_id抽出]
  F --> G[fetch_stateへPENDING投入]
  E --> H[DONE更新]
```

---

## 3. DB設計

### 3.1 rakuten_genre

カラム 型 説明

---

genre_id bigint PK 楽天ジャンルID
genre_name text ジャンル名
genre_level int 階層
parent_genre_id bigint 親ジャンルID
english_name text 英語名
link_genre_id bigint linkGenreId
chopper_flg int chopperFlg
lowest_flg int lowestFlg
raw_json jsonb APIレスポンス全文
fetched_at timestamptz 取得日時
updated_at timestamptz 更新日時

---

### 3.2 rakuten_genre_fetch_state

カラム 型 説明

---

genre_id bigint PK 処理対象ジャンル
status text PENDING / IN_PROGRESS / DONE / ERROR
try_count int リトライ回数
last_error text エラー内容
locked_by text 実行プロセス識別子
locked_at timestamptz ロック時刻
updated_at timestamptz 更新日時

---

## 4. 処理フロー

### 4.1 初期投入

- start_genre_id（通常0）をPENDINGで登録

### 4.2 claim処理

```sql
FOR UPDATE SKIP LOCKED
```

により複数プロセスで安全に並列処理可能。

### 4.3 API呼び出し

- endpoint: IchibaGenre/Search
- 必須: applicationId, genreId
- format=json

### 4.4 パース処理

レスポンス例:

- parents: \[{"parent": {...}}\]
- brothers: \[{"brother": {...}}\]
- children: \[{"child": {...}}\]
- current: {...}

取得対象: - current.genreId - parents - brothers - children

### 4.5 UPSERT

```sql
ON CONFLICT (genre_id) DO UPDATE
```

raw_jsonは常に最新で上書き。

### 4.6 次候補投入

parents / brothers / children の genreId を PENDING で投入。

---

## 5. 並列実行

複数プロンプトで同時実行可能。

```bash
python fetch_rakuten_genres.py
python fetch_rakuten_genres.py
```

DBが仕事を分配するため重複処理は発生しない。

---

## 6. テスト方法

### 6.1 件数制限

```bash
python fetch_rakuten_genres.py --max-genres 10
```

10件取得で停止。

### 6.2 スタブ利用

```bash
python fetch_rakuten_genres.py --api-mode stub --max-genres 5
```

---

## 7. エラーハンドリング

- HTTPエラー → ERRORへ遷移
- try_count増加
- 必要に応じて再実行

---

## 8. 運用上の注意

- 429対策: sleep_secを適切に設定
- 並列数はAPIレート制限内に収める
- Neon接続数上限に注意

---

## 9. 今後の拡張

- tagGroupsの正規化
- 差分検知(hash比較)
- 変更履歴保存(履歴テーブル追加)

---

以上。
