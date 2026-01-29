# Embedding Strategy & Operations

## 1. Purpose
ContextVector / ItemVector の生成・保存・更新・バージョニング・障害時対応を定義する。

---

## 2. Vectors in This System
| Vector | Source | When | Stored in |
|---|---|---|---|
| ContextVector | user context text | レコメンド実行時（必要なら再利用） | apl.context.context_vector |
| ItemVector | item text | バッチ/ETL | apl.item_embedding / apl.item.embedding_vector（設計に合わせて） |

---

## 3. Model & Dimension
- Embedding model：`text-embedding-3-small`（例）
- Dimension：モデルに依存（DBの vector 次元と一致させる）

---

## 4. Text Construction

## 4.1 Context text（embedding_context）
- event
- recipient
- budget
- features_like / not_like / ng

テンプレ例：
- 「{event} のギフト。贈り先は {recipient}。予算は {min}〜{max} 円。{like} が好み。{not_like} は避けたい。{ng} はNG。」

## 4.2 Item text（商品側）
- title / caption / tags / genre / brand / price帯 など

---

## 5. Normalization
- cosine を前提にする場合、ベクトルは unit 正規化すると安定
- 推奨：生成後に正規化して保存（比較の再現性が高い）

---

## 6. Reuse & Context Hash
- `context_hash` で同一入力を判定し再利用
- 入力（event_id, recipient_id, budgets, features arrays, embedding_model, embedding_version）をハッシュ化

---

## 7. Versioning Policy
- `embedding_model`: text
- `embedding_version`: int（テンプレ変更や前処理変更でも上げる）

---

## 8. Failure Handling
- リトライ（例：2回、指数バックオフ）
- 失敗時は `EMBEDDING_FAILED`（MVP）

---

## 9. Performance Notes
- Context embedding は hash reuse
- Item embedding はバッチで差分更新

---

## 10. Checklist
- DB vector 次元がモデルと一致
- context_hash の入力項目が固定
- embedding_version の運用ルールがある
