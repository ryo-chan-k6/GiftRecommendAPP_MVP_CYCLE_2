# レコメンドページ 認証不要 MVP 仕様書

## 1. 目的

本ドキュメントは、**初期 MVP 版**におけるレコメンド機能の仕様を定義する。

- ユーザビリティを重視し、ユーザー・イベント・贈り先の登録機能を持たない
- レコメンドに必要なコンテキスト情報を直接入力し、**ステートレス**にレコメンド結果を返す
- **認証不要**で誰でも利用可能とする

---

## 2. 基本方針

| 項目 | 方針 |
|------|------|
| 認証 | 不要（誰でも利用可能） |
| 永続化 | **行う**（チューニング・利用情報収集・事業改善のため） |
| ユーザー登録 | なし |
| イベント登録 | なし |
| 贈り先登録 | なし |
| 履歴一覧・詳細 | MVP では提供しない（認証なしのため「自分の」一覧は取得不可） |

---

## 3. 対象範囲

### 3.1 対象コンポーネント

| コンポーネント | 変更内容 |
|----------------|----------|
| Web: `/recommend` ページ | 認証削除、結果を同一ページに表示 |
| API: POST `/recommendations` | 認証不要、**永続化あり**（user_id=null で保存） |
| API: GET `/recommendations/:id` | 認証不要で取得可能（recommendationId を知っていれば誰でも閲覧） |
| API: GET `/recommendations/list` | MVP では非提供（認証なしのため「自分の」一覧は取得不可） |

### 3.2 非対象（変更なし）

- Reco サービス（既にステートレスで動作）
- 認証・ユーザー管理機能（他画面で継続利用する場合は維持）

---

## 4. 入力項目

### 4.1 必須・任意

| 項目 | 必須 | 型 | 説明 |
|------|------|-----|------|
| mode | ○ | `popular` \| `balanced` \| `diverse` | レコメンド戦略 |
| budgetMin | - | number (optional) | 予算下限（円） |
| budgetMax | - | number (optional) | 予算上限（円） |
| eventName | - | string (optional) | イベント名（例: 父の日、誕生日） |
| recipientDescription | - | string (optional) | 贈り先の説明（例: 父、友人、上司） |
| featuresLike | - | string[] (optional) | 好みの特徴（カンマ区切り入力） |
| featuresNotLike | - | string[] (optional) | 避けたい特徴 |
| featuresNg | - | string[] (optional) | NG 条件（絶対に含めない） |

### 4.2 eventId / recipientId の扱い

- **MVP では eventId / recipientId（UUID）は廃止**
- 代わりに **eventName**（自由入力）と **recipientDescription**（自由入力）を使用
- 登録不要で、ユーザーがその場で入力する

---

## 5. API 仕様

### 5.1 POST /recommendations（認証不要）

#### リクエスト

- **認証**: 不要（Authorization ヘッダー不要）
- **Content-Type**: `application/json`

```json
{
  "mode": "balanced",
  "eventName": "父の日",
  "recipientDescription": "父",
  "budgetMin": 3000,
  "budgetMax": 8000,
  "featuresLike": ["落ち着いた", "実用的", "黒"],
  "featuresNotLike": ["派手"],
  "featuresNg": ["生もの"]
}
```

#### レスポンス（成功時）

- **永続化する**ため、`recommendationId` を返却する（GET で再取得可能）
- レスポンスボディに `recommendationId` と `items` を含める

```json
{
  "recommendationId": "uuid",
  "mode": "balanced",
  "resolvedAlgorithm": {
    "name": "vector_ranked_mmr",
    "resolvedBy": "mode",
    "params": { ... }
  },
  "items": [
    {
      "rank": 1,
      "itemId": "uuid",
      "title": "…",
      "price": 5980,
      "imageUrl": "…",
      "affiliateUrl": "…",
      "reason": { ... }
    }
  ]
}
```

#### 永続化の扱い

- **入力データおよび出力データを DB に保存する**（アプリチューニング・利用情報収集・事業改善のため）
- 保存先: `recommendation` / `context` / `recommendation_item` テーブル
- 認証なしのため `user_id` は **null** で保存する（DB スキーマは既に NULL 許容）
- `event_id` / `recipient_id` は null（eventName / recipientDescription は `context_text` に含める）
- `recommendationRepo` / `contextHash` は `userId` を optional（null 許容）にし、`eventName` / `recipientDescription` を扱うよう修正

### 5.2 GET /recommendations/:id

- **認証不要**で取得可能
- `recommendationId` を知っていれば誰でも閲覧できる（UUID のため推測困難）
- 永続化したデータから返却する

### 5.3 GET /recommendations/list

- **MVP では提供しない**（認証なしのため「自分の」履歴一覧を取得する手段がない）
- 将来的に認証導入時に再検討

---

## 6. Web UI 仕様

### 6.1 レコメンド実行ページ（/recommend）

#### 画面構成

1. **入力フォーム**
   - mode（セレクト）
   - budgetMin / budgetMax（数値入力）
   - eventName（テキスト、プレースホルダ例: 父の日、誕生日）
   - recipientDescription（テキスト、プレースホルダ例: 父、友人）
   - featuresLike / featuresNotLike / featuresNg（カンマ区切りテキスト）

2. **実行ボタン**
   - 「レコメンドを実行」等

3. **結果表示エリア**
   - 実行成功時、**同一ページ内**に結果を表示
   - リダイレクトは行わない（同一ページで完結）
   - 商品一覧（rank, title, price, imageUrl, reason 等）
   - （任意）結果の URL（`/recommendations/:id`）を表示し、ブックマーク・共有を可能にしてもよい

#### 認証まわり

- `supabase.auth.getSession()` を呼ばない
- `Authorization` ヘッダーを付与しない
- ログイン・サインアップへの誘導は行わない（本ページ単体で完結）

#### エラー表示

- API エラー時はフォーム下にエラーメッセージを表示
- ネットワークエラー等も同様に表示

### 6.2 履歴・詳細ページの扱い

| ページ | MVP での扱い |
|--------|--------------|
| `/recommendations`（一覧） | 非表示 or リンク削除（認証なしのため一覧取得不可） |
| `/recommendations/[id]`（詳細） | **認証不要で表示可能**（recommendationId を URL で受け取り表示） |

- 一覧ページはナビゲーションから削除（認証なしでは「自分の」履歴が取れないため）
- 詳細ページは認証不要で表示（結果表示後に URL を共有・ブックマーク可能）

---

## 7. Reco サービス連携

### 7.1 リクエストマッピング

API が Reco サービスへ転送する際のパラメータ:

| API 項目 | Reco 項目 | 備考 |
|----------|-----------|------|
| mode | mode | そのまま |
| eventName | eventName | 新規（Reco 側で context 文生成に利用） |
| recipientDescription | recipientDescription | 新規（同上） |
| budgetMin / budgetMax | budgetMin / budgetMax | そのまま |
| featuresLike / NotLike / Ng | 同様 | そのまま |

### 7.2 Reco 側の変更

- `eventId` / `recipientId` を廃止し、`eventName` / `recipientDescription` を採用
- `_build_context_text` で eventName / recipientDescription を embedding 用テキストに含める
  - 例: `"父の日のギフト。贈り先は父。予算は3000〜8000円。落ち着いた、実用的、黒が好み。..."`

---

## 8. エラーハンドリング

| 状況 | 対応 |
|------|------|
| mode 不正 | 400 Bad Request |
| Reco サービス障害 | 502 Bad Gateway または 500 |
| バリデーションエラー | 400 + エラー詳細 |

---

## 9. 将来拡張（本 MVP の範囲外）

- 認証導入後の「自分の」履歴一覧の提供
- eventId / recipientId による登録済みイベント・贈り先の参照

---

## 10. 関連ドキュメント

- `docs/recommend/overview.md`
- `docs/recommend/recommendation_flow.md`
- `docs/online/openapi_recommendation_contract.md`

---

## 11. 既存仕様との差分

本 MVP 仕様は、以下の既存ドキュメントと一部異なる。

| 項目 | 既存（openapi_recommendation_contract 等） | 本 MVP |
|------|------------------------------------------|--------|
| 認証 | requireAuth 前提 | 不要 |
| eventId / recipientId | UUID で指定 | 廃止、eventName / recipientDescription に置換 |
| 永続化 | recommendation / context / recommendation_item に保存 | **保存する**（user_id=null） |
| recommendationId | 返却し、GET で取得可能 | 返却し、GET で取得可能（認証不要） |
| 結果表示 | /recommendations/:id へリダイレクト | 同一ページに表示（詳細ページは認証不要で閲覧可） |

---

## 12. 実装チェックリスト（参考）

仕様確定後、実装修正時に参照するチェックリスト。

### Web

- [ ] `supabase.auth.getSession()` の呼び出しを削除
- [ ] `Authorization` ヘッダーを付与しない
- [ ] eventId / recipientId 入力を eventName / recipientDescription に変更
- [ ] 成功時に同一ページに結果表示（リダイレクトしない）
- [ ] 結果表示用の UI コンポーネントを追加
- [ ] （任意）結果の URL を表示し、詳細ページへのリンクを提供
- [ ] ナビゲーションから履歴一覧へのリンクを削除 or 非表示（詳細ページは残す）

### API

- [ ] POST `/recommendations` から `requireAuth` ミドルウェアを削除
- [ ] `saveRecommendation` を **維持**（user_id を null で渡すよう修正）
- [ ] `recommendationRepo` / `contextHash` で userId を optional、eventName / recipientDescription を扱うよう修正
- [ ] Reco への payload に eventName / recipientDescription を渡す（eventId / recipientId は廃止）
- [ ] レスポンスに recommendationId を **含める**
- [ ] GET `/recommendations/:id` から `requireAuth` を削除（認証不要で取得可能に）
- [ ] GET `/recommendations/list` は MVP では非提供のため、404 返却 or ルート削除

### Reco

- [ ] RecommendationRequest に eventName / recipientDescription を追加
- [ ] eventId / recipientId を optional のまま廃止 or 削除
- [ ] `_build_context_text` で eventName / recipientDescription を embedding 文に含める

---

## 13. 変更履歴

| 日付 | 内容 |
|------|------|
| 2025-02-12 | 初版作成 |
| 2025-02-12 | 永続化方針を追加（チューニング・利用情報収集・事業改善のため入力・出力を保存） |
