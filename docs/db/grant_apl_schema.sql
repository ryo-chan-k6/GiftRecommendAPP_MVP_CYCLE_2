-- apl スキーマの GRANT 設定
-- Supabase Data API (PostgREST) 経由で apl にアクセスするために必要
--
-- 実行方法: Supabase Dashboard → SQL Editor で実行
--
-- 前提:
-- - Settings → API → Exposed schemas に apl を追加済みであること
-- - database_schema.sql で apl スキーマ・テーブルが作成済みであること

-- ------------------------------------------------------------
-- 1. スキーマへの USAGE
-- ------------------------------------------------------------
GRANT USAGE ON SCHEMA apl TO service_role;
GRANT USAGE ON SCHEMA apl TO anon;
GRANT USAGE ON SCHEMA apl TO authenticated;

-- ------------------------------------------------------------
-- 2. 全テーブルへの権限（service_role: サーバーサイド API / Reco 用）
-- ------------------------------------------------------------
GRANT ALL ON ALL TABLES IN SCHEMA apl TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA apl TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA apl TO service_role;

-- ------------------------------------------------------------
-- 3. 将来作成されるテーブルにも自動付与
-- ------------------------------------------------------------
ALTER DEFAULT PRIVILEGES IN SCHEMA apl
  GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA apl
  GRANT ALL ON SEQUENCES TO service_role;

-- ------------------------------------------------------------
-- 4. anon / authenticated の権限（オプション）
-- RLS ポリシーで制御する場合は SELECT 等を最小限に
-- 現状は API が service_role を使用するため、必須ではない
-- ------------------------------------------------------------
-- GRANT SELECT ON ALL TABLES IN SCHEMA apl TO anon;
-- GRANT SELECT ON ALL TABLES IN SCHEMA apl TO authenticated;
