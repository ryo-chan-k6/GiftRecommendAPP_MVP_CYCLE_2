# Supabase RLS Policy (Draft)

## 1. Purpose
本ドキュメントは、Supabase（Postgres）の Row Level Security（RLS）方針を定義する。
ユーザーごとのデータ隔離と、ADMIN 機能（実験・比較）を両立する。

---

## 2. Assumptions
- Auth は Supabase Auth（`auth.users`）を利用
- アプリ側の user profile は `apl.user_profile`
- `auth.uid()` が現在ログイン中のユーザー UUID を返す

---

## 3. Roles
- **authenticated**：ログイン済み一般ユーザー
- **admin**：`apl.user_profile.role = 'ADMIN'` のユーザー

> Supabase の RLS は “role string” だけでは表現しづらいので、
> `is_admin()` のような SQL function を用意するのが定石。

---

## 4. Helper Functions（推奨）
```sql
create or replace function apl.is_admin()
returns boolean
language sql
stable
as $$
  select exists (
    select 1
    from apl.user_profile p
    where p.id = auth.uid()
      and p.role = 'ADMIN'
  );
$$;
```

---

## 5. Table Policies（方針）

## 5.1 apl.user_profile
- SELECT：本人のみ
- UPDATE：本人のみ（role は ADMIN のみ変更可 or 変更不可）
- INSERT：本人のみ（signup 後にトリガで作る運用も可）

条件例：
- `id = auth.uid()`（本人一致）

---

## 5.2 apl.recipient
- SELECT：`recipient.user_id = auth.uid()`
- INSERT：`user_id = auth.uid()`
- UPDATE/DELETE：同上

---

## 5.3 apl.event
- scope = COMMON：全 authenticated が SELECT 可
- scope = PRIVATE：`created_by = auth.uid()` のみ SELECT/UPDATE/DELETE
- INSERT：
  - COMMON は原則 ADMIN のみ（運用上）
  - PRIVATE は `created_by = auth.uid()`

---

## 5.4 apl.context
- SELECT：`user_id = auth.uid()`
- INSERT：`user_id = auth.uid()`
- UPDATE：MVP は基本しない（immutable 想定）

---

## 5.5 apl.recommendation / apl.recommendation_item
- recommendation
  - SELECT：`user_id = auth.uid()`（ADMIN は全件可にしてもよいが慎重に）
  - INSERT：`user_id = auth.uid()` or `apl.is_admin()`
- recommendation_item
  - SELECT：親 recommendation が見える場合のみ
  - INSERT：サーバ経由のみ（service role）にするのが安全

---

## 5.6 apl.favorite
- SELECT：`user_id = auth.uid()`
- INSERT：`user_id = auth.uid()`
- DELETE：同上

---

## 6. Service Role / Edge Functions
- レコメンド生成は「サーバ側」実行が前提
- DB 直叩きで insert を許可しない方が安全なテーブル
  - `recommendation_item`
  - （必要なら）`context` もサーバのみ

---

## 7. Checklist
- すべてのテーブルで RLS を有効化
- policy がないと 403 になることを確認
- ADMIN の権限が過剰になっていないか確認
