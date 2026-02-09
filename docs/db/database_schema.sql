-- DDL generated from docs/db/database_schema.dbml
-- NOTE: auth.users is managed by Supabase (not created here).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS apl;

-- ------------------------------------------------------------
-- apl (ユーザー系)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS apl.user_profile (
  id uuid PRIMARY KEY REFERENCES auth.users(id),
  name varchar NOT NULL,
  role varchar DEFAULT 'USER',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar NOT NULL,
  scope varchar DEFAULT 'COMMON',
  start_date timestamptz NULL,
  end_date timestamptz NULL,
  default_budget_min int NULL,
  default_budget_max int NULL,
  created_by uuid NULL REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_apl_event_scope ON apl.event (scope);
CREATE INDEX IF NOT EXISTS idx_apl_event_created_by ON apl.event (created_by);

CREATE TABLE IF NOT EXISTS apl.recipient (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar NOT NULL,
  age int NULL,
  birthday_date date NULL,
  gender varchar NULL,
  user_id uuid NULL REFERENCES auth.users(id),
  relation varchar NULL,
  note text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.event_recipient (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NULL REFERENCES auth.users(id),
  event_id uuid NULL REFERENCES apl.event(id),
  recipient_id uuid NULL REFERENCES apl.recipient(id),
  budget_min int NULL,
  budget_max int NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.context (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NULL REFERENCES auth.users(id),
  event_id uuid NULL REFERENCES apl.event(id),
  recipient_id uuid NULL REFERENCES apl.recipient(id),
  budget_min int NULL,
  budget_max int NULL,
  features_like text[] NOT NULL DEFAULT '{}'::text[],
  features_not_like text[] NOT NULL DEFAULT '{}'::text[],
  features_ng text[] NOT NULL DEFAULT '{}'::text[],
  context_text text NOT NULL,
  context_vector vector(1536) NULL,
  embedding_model text NOT NULL,
  embedding_version int NOT NULL DEFAULT 1,
  context_hash text UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- apl (商品系)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS apl.item_rank_snapshot (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rakuten_item_code varchar NOT NULL,
  collected_at timestamptz NOT NULL,
  fetched_at timestamptz NOT NULL DEFAULT now(),
  rakuten_genre_id bigint NULL,
  title varchar NULL,
  last_build_date timestamptz NOT NULL,
  rank int NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_item_rank_snapshot_genre_item_collected
  ON apl.item_rank_snapshot (rakuten_genre_id, rakuten_item_code, collected_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_rank_snapshot_collected
  ON apl.item_rank_snapshot (collected_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_rank_snapshot_fetched
  ON apl.item_rank_snapshot (fetched_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_rank_snapshot_genre_collected
  ON apl.item_rank_snapshot (rakuten_genre_id, collected_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_rank_snapshot_genre_rank_collected
  ON apl.item_rank_snapshot (rakuten_genre_id, rank, collected_at);

CREATE TABLE IF NOT EXISTS apl.item (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rakuten_item_code varchar NOT NULL UNIQUE,
  item_name varchar NOT NULL,
  item_url text NOT NULL,
  affiliate_url text NULL,
  catchcopy text NULL,
  item_caption text NULL,
  image_flag int NULL,
  rakuten_shop_code varchar NOT NULL,
  rakuten_genre_id bigint NULL,
  credit_card_flag int NULL,
  is_active bool NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_apl_item_rakuten_genre_id ON apl.item (rakuten_genre_id);
CREATE INDEX IF NOT EXISTS idx_apl_item_rakuten_shop_code ON apl.item (rakuten_shop_code);
CREATE INDEX IF NOT EXISTS idx_apl_item_is_active ON apl.item (is_active);

CREATE TABLE IF NOT EXISTS apl.item_tag (
  item_id uuid NOT NULL REFERENCES apl.item(id),
  rakuten_tag_id bigint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (item_id, rakuten_tag_id)
);
CREATE INDEX IF NOT EXISTS idx_apl_item_tag_rakuten_tag_id ON apl.item_tag (rakuten_tag_id);

CREATE TABLE IF NOT EXISTS apl.item_image (
  id bigserial PRIMARY KEY,
  item_id uuid NOT NULL REFERENCES apl.item(id),
  size varchar NOT NULL,
  url text NOT NULL,
  sort_order int NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_apl_item_image_item_id ON apl.item_image (item_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_item_image_item_size_sort
  ON apl.item_image (item_id, size, sort_order);

CREATE TABLE IF NOT EXISTS apl.item_market_snapshot (
  id bigserial PRIMARY KEY,
  item_id uuid NOT NULL REFERENCES apl.item(id),
  collected_at timestamptz NOT NULL DEFAULT now(),
  item_price int NULL,
  tax_flag int NULL,
  postage_flag int NULL,
  gift_flag int NULL,
  availability int NULL,
  asuraku_flag int NULL,
  asuraku_closing_time varchar NULL,
  asuraku_area varchar NULL,
  start_time timestamptz NULL,
  end_time timestamptz NULL,
  point_rate int NULL,
  point_rate_start_time timestamptz NULL,
  point_rate_end_time timestamptz NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_item_market_snapshot_item_collected
  ON apl.item_market_snapshot (item_id, collected_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_market_snapshot_collected
  ON apl.item_market_snapshot (collected_at);

CREATE TABLE IF NOT EXISTS apl.item_review_snapshot (
  id bigserial PRIMARY KEY,
  item_id uuid NOT NULL REFERENCES apl.item(id),
  collected_at timestamptz NOT NULL DEFAULT now(),
  review_count int NULL,
  review_average float NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_item_review_snapshot_item_collected
  ON apl.item_review_snapshot (item_id, collected_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_review_snapshot_collected
  ON apl.item_review_snapshot (collected_at);

CREATE TABLE IF NOT EXISTS apl.shop (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rakuten_shop_code varchar NOT NULL UNIQUE,
  shop_name varchar NOT NULL,
  shop_url text NOT NULL,
  shop_of_the_year_flag int NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.genre (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rakuten_genre_id bigint NOT NULL UNIQUE,
  name varchar NOT NULL,
  level int NOT NULL,
  parent_id uuid NULL REFERENCES apl.genre(id),
  last_source_hash varchar NULL,
  last_source_version int NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_apl_genre_parent_id ON apl.genre (parent_id);
CREATE INDEX IF NOT EXISTS idx_apl_genre_level ON apl.genre (level);

CREATE TABLE IF NOT EXISTS apl.tag_group (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rakuten_tag_group_id bigint NOT NULL UNIQUE,
  name varchar NOT NULL,
  last_source_hash varchar NULL,
  last_source_version int NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.tag (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rakuten_tag_id bigint NOT NULL UNIQUE,
  name varchar NOT NULL,
  group_id uuid NOT NULL REFERENCES apl.tag_group(id),
  parent_id uuid NULL REFERENCES apl.tag(id),
  last_source_hash varchar NULL,
  last_source_version int NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_apl_tag_group_id ON apl.tag (group_id);
CREATE INDEX IF NOT EXISTS idx_apl_tag_parent_id ON apl.tag (parent_id);

CREATE TABLE IF NOT EXISTS apl.item_features (
  item_id uuid PRIMARY KEY REFERENCES apl.item(id),
  price_yen int NULL,
  price_log float NULL,
  point_rate int NULL,
  availability int NULL,
  review_average float NULL,
  review_count int NULL,
  review_count_log float NULL,
  rank int NULL,
  popularity_score float NULL,
  rakuten_genre_id bigint NULL,
  tag_ids int[] NULL,
  features_version int NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_apl_item_features_created_at ON apl.item_features (created_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_features_version ON apl.item_features (features_version);
CREATE INDEX IF NOT EXISTS idx_apl_item_features_popularity ON apl.item_features (popularity_score);

CREATE TABLE IF NOT EXISTS apl.item_embedding_source (
  item_id uuid PRIMARY KEY REFERENCES apl.item(id),
  source_text text NOT NULL,
  source_hash varchar NOT NULL,
  source_version int NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.item_embedding (
  item_id uuid NOT NULL REFERENCES apl.item(id),
  model varchar NOT NULL,
  embedding vector NOT NULL,
  source_hash varchar NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (item_id, model)
);
CREATE INDEX IF NOT EXISTS idx_apl_item_embedding_model ON apl.item_embedding (model);
CREATE INDEX IF NOT EXISTS idx_apl_item_embedding_source_hash ON apl.item_embedding (source_hash);

-- ------------------------------------------------------------
-- apl (推薦・お気に入り)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS apl.favorite (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id),
  event_id uuid NULL REFERENCES apl.event(id),
  recipient_id uuid NULL REFERENCES apl.recipient(id),
  item_id uuid NULL REFERENCES apl.item(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_apl_favorite_user_id ON apl.favorite (user_id);
CREATE INDEX IF NOT EXISTS idx_apl_favorite_event_id ON apl.favorite (event_id);
CREATE INDEX IF NOT EXISTS idx_apl_favorite_recipient_id ON apl.favorite (recipient_id);
CREATE INDEX IF NOT EXISTS idx_apl_favorite_event_recipient ON apl.favorite (event_id, recipient_id);

CREATE TABLE IF NOT EXISTS apl.recommendation (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NULL REFERENCES auth.users(id),
  context_id uuid NULL REFERENCES apl.context(id),
  algorithm text NULL,
  params jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.recommendation_item (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_id uuid NULL REFERENCES apl.recommendation(id),
  item_id uuid NULL REFERENCES apl.item(id),
  rank int NULL,
  score float NULL,
  vector_score float NULL,
  rerank_score float NULL,
  reason jsonb NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_recommendation_item_rank
  ON apl.recommendation_item (recommendation_id, rank);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_recommendation_item_item
  ON apl.recommendation_item (recommendation_id, item_id);

CREATE TABLE IF NOT EXISTS apl.staging (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source varchar NOT NULL,
  entity varchar NOT NULL,
  source_id varchar NOT NULL,
  content_hash text NOT NULL,
  s3_key text NOT NULL,
  etag text NULL,
  saved_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_staging_source_entity_source_id
  ON apl.staging (source, entity, source_id);
CREATE INDEX IF NOT EXISTS idx_apl_staging_source_entity
  ON apl.staging (source, entity);
CREATE INDEX IF NOT EXISTS idx_apl_staging_entity_saved_at
  ON apl.staging (entity, saved_at);

CREATE TABLE IF NOT EXISTS apl.target_genre_config (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rakuten_genre_id bigint NULL,
  is_enabled bool DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
