-- DDL generated from docs/db/schema-app.dbml

-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Schemas
CREATE SCHEMA IF NOT EXISTS apl;
CREATE SCHEMA IF NOT EXISTS collector;

-- ------------------------------------------------------------
-- Enum (schema: apl)
-- ------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role' AND typnamespace = 'apl'::regnamespace) THEN
    CREATE TYPE apl.user_role AS ENUM ('USER', 'ADMIN');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'gender' AND typnamespace = 'apl'::regnamespace) THEN
    CREATE TYPE apl.gender AS ENUM ('MALE', 'FEMALE');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'age_range' AND typnamespace = 'apl'::regnamespace) THEN
    CREATE TYPE apl.age_range AS ENUM ('TEEN','TWENTIES','THIRTIES','FORTIES','FIFTIES','SIXTIES','SEVENTIES_PLUS','UNKNOWN');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'relation_type' AND typnamespace = 'apl'::regnamespace) THEN
    CREATE TYPE apl.relation_type AS ENUM ('BOSS','SUBORDINATE','COWORKER','CLIENT','FRIEND','PARTNER','SPOUSE','PARENT','CHILD','SIBLING','GRANDPARENT','RELATIVE','TEACHER','OTHER','UNSPECIFIED');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_type' AND typnamespace = 'apl'::regnamespace) THEN
    CREATE TYPE apl.event_type AS ENUM ('BIRTHDAY','CHRISTMAS','VALENTINE','WHITE_DAY','MOTHERS_DAY','FATHERS_DAY','RESPECT_FOR_AGED','WEDDING','BIRTH_CELEBRATION','MOVING','PROMOTION','THANKS','APOLOGY','JOB_CHANGE','ANNIVERSARY','NONE');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'budget_range' AND typnamespace = 'apl'::regnamespace) THEN
    CREATE TYPE apl.budget_range AS ENUM ('U3000','B3000_5000','B5000_8000','B8000_12000','B12000_20000','O20000');
  END IF;
END
$$;

-- ------------------------------------------------------------
-- apl（アプリDB：商品関連）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS apl.genre (
  id uuid PRIMARY KEY,
  rakuten_genre_id int NOT NULL UNIQUE,
  name varchar NOT NULL,
  level int NOT NULL,
  parent_id uuid NULL REFERENCES apl.genre(id),
  last_source_hash varchar NULL,
  last_source_version int NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_apl_genre_parent_id ON apl.genre (parent_id);
CREATE INDEX IF NOT EXISTS idx_apl_genre_level ON apl.genre (level);

CREATE TABLE IF NOT EXISTS apl.tag_group (
  id uuid PRIMARY KEY,
  rakuten_tag_group_id int NOT NULL UNIQUE,
  name varchar NOT NULL,
  last_source_hash varchar NULL,
  last_source_version int NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS apl.tag (
  id uuid PRIMARY KEY,
  rakuten_tag_id int NOT NULL UNIQUE,
  name varchar NOT NULL,
  group_id uuid NOT NULL REFERENCES apl.tag_group(id),
  parent_id uuid NULL REFERENCES apl.tag(id),
  last_source_hash varchar NULL,
  last_source_version int NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_apl_tag_group_id ON apl.tag (group_id);
CREATE INDEX IF NOT EXISTS idx_apl_tag_parent_id ON apl.tag (parent_id);

CREATE TABLE IF NOT EXISTS apl.shop (
  id uuid PRIMARY KEY,
  shop_code varchar NOT NULL UNIQUE,
  shop_name varchar NOT NULL,
  shop_url text NOT NULL,
  shop_of_the_year_flag int NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS apl.item (
  id uuid PRIMARY KEY,
  item_code varchar NOT NULL UNIQUE,
  item_name varchar NOT NULL,
  item_url text NOT NULL,
  affiliate_url text NULL,
  catchcopy text NULL,
  item_caption text NULL,
  image_flag int NULL,
  shop_id uuid NOT NULL REFERENCES apl.shop(id),
  genre_id uuid NULL REFERENCES apl.genre(id),
  credit_card_flag int NULL,
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  is_active bool NOT NULL DEFAULT true,
  last_source_hash varchar NULL,
  last_source_version int NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_apl_item_genre_id ON apl.item (genre_id);
CREATE INDEX IF NOT EXISTS idx_apl_item_shop_id ON apl.item (shop_id);
CREATE INDEX IF NOT EXISTS idx_apl_item_is_active ON apl.item (is_active);
CREATE INDEX IF NOT EXISTS idx_apl_item_last_seen_at ON apl.item (last_seen_at);

CREATE TABLE IF NOT EXISTS apl.item_tag (
  item_id uuid NOT NULL REFERENCES apl.item(id),
  tag_id uuid NOT NULL REFERENCES apl.tag(id),
  created_at timestamptz NOT NULL,
  PRIMARY KEY (item_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_apl_item_tag_tag_id ON apl.item_tag (tag_id);

CREATE TABLE IF NOT EXISTS apl.item_image (
  id bigserial PRIMARY KEY,
  item_id uuid NOT NULL REFERENCES apl.item(id),
  size varchar NOT NULL,
  url text NOT NULL,
  sort_order int NULL,
  created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_apl_item_image_item_id ON apl.item_image (item_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_item_image_item_size_sort ON apl.item_image (item_id, size, sort_order);

CREATE TABLE IF NOT EXISTS apl.item_market_snapshot (
  id bigserial PRIMARY KEY,
  item_id uuid NOT NULL REFERENCES apl.item(id),
  collected_at timestamptz NOT NULL,
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
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_item_market_snapshot_item_collected ON apl.item_market_snapshot (item_id, collected_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_market_snapshot_collected ON apl.item_market_snapshot (collected_at);

CREATE TABLE IF NOT EXISTS apl.item_review_snapshot (
  id bigserial PRIMARY KEY,
  item_id uuid NOT NULL REFERENCES apl.item(id),
  collected_at timestamptz NOT NULL,
  review_count int NULL,
  review_average float NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_item_review_snapshot_item_collected ON apl.item_review_snapshot (item_id, collected_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_review_snapshot_collected ON apl.item_review_snapshot (collected_at);

CREATE TABLE IF NOT EXISTS apl.item_rank_snapshot (
  id bigserial PRIMARY KEY,
  item_id uuid NOT NULL REFERENCES apl.item(id),
  collected_at timestamptz NOT NULL,
  rank_type varchar NOT NULL,
  genre_id uuid NULL REFERENCES apl.genre(id),
  title varchar NULL,
  rank int NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_item_rank_snapshot_rtype_genre_item_collected ON apl.item_rank_snapshot (rank_type, genre_id, item_id, collected_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_rank_snapshot_rtype_collected ON apl.item_rank_snapshot (rank_type, collected_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_rank_snapshot_rtype_genre_collected ON apl.item_rank_snapshot (rank_type, genre_id, collected_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_rank_snapshot_rtype_genre_rank_collected ON apl.item_rank_snapshot (rank_type, genre_id, rank, collected_at);

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
  rakuten_genre_id int NULL,
  tag_ids int[] NULL,
  features_version int NOT NULL,
  computed_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_apl_item_features_computed_at ON apl.item_features (computed_at);
CREATE INDEX IF NOT EXISTS idx_apl_item_features_version ON apl.item_features (features_version);
CREATE INDEX IF NOT EXISTS idx_apl_item_features_popularity ON apl.item_features (popularity_score);

CREATE TABLE IF NOT EXISTS apl.item_embedding_source (
  item_id uuid PRIMARY KEY REFERENCES apl.item(id),
  source_text text NOT NULL,
  source_hash varchar NOT NULL,
  source_version int NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS apl.item_embedding (
  item_id uuid NOT NULL REFERENCES apl.item(id),
  model varchar NOT NULL,
  embedding vector NOT NULL,
  created_at timestamptz NOT NULL,
  PRIMARY KEY (item_id, model)
);
CREATE INDEX IF NOT EXISTS idx_apl_item_embedding_model ON apl.item_embedding (model);

-- ------------------------------------------------------------
-- apl（アプリDB：ユーザー/レコメンド）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS apl.user_profile (
  id uuid PRIMARY KEY REFERENCES auth.users(id) on delete cascade,
  name varchar NOT NULL,
  role varchar NOT NULL DEFAULT 'USER',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.event (
  id uuid PRIMARY KEY,
  name varchar NOT NULL,
  scope varchar NOT NULL DEFAULT 'COMMON',
  start_date timestamptz NULL,
  end_date timestamptz NULL,
  default_budget_min int NULL,
  default_budget_max int NULL,
  created_by uuid NULL REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NULL
);
CREATE INDEX IF NOT EXISTS idx_apl_event_scope ON apl.event (scope);
CREATE INDEX IF NOT EXISTS idx_apl_event_created_by ON apl.event (created_by);

CREATE TABLE IF NOT EXISTS apl.recipient (
  id uuid PRIMARY KEY,
  name varchar NOT NULL,
  age int NULL,
  birthday_date date NULL,
  gender varchar NULL,
  user_id uuid REFERENCES auth.users(id),
  relation varchar NULL,
  note text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NULL
);

CREATE TABLE IF NOT EXISTS apl.event_recipient (
  id uuid PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id),
  event_id uuid REFERENCES apl.event(id),
  recipient_id uuid REFERENCES apl.recipient(id),
  budget_min int NULL,
  budget_max int NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.context (
  id uuid PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id),
  event_id uuid REFERENCES apl.event(id),
  recipient_id uuid REFERENCES apl.recipient(id),
  budget_min int NULL,
  budget_max int NULL,
  features_like text[] NOT NULL DEFAULT '{}'::text[],
  features_not_like text[] NOT NULL DEFAULT '{}'::text[],
  features_ng text[] NOT NULL DEFAULT '{}'::text[],
  context_text text NOT NULL,
  context_vector vector NULL,
  embedding_model text NOT NULL,
  embedding_version int NOT NULL DEFAULT 1,
  context_hash text UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.favorite (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES auth.users(id),
  event_id uuid NULL REFERENCES apl.event(id),
  recipient_id uuid NULL REFERENCES apl.recipient(id),
  item_id uuid REFERENCES apl.item(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NULL
);
CREATE INDEX IF NOT EXISTS idx_apl_favorite_user_id ON apl.favorite (user_id);
CREATE INDEX IF NOT EXISTS idx_apl_favorite_event_id ON apl.favorite (event_id);
CREATE INDEX IF NOT EXISTS idx_apl_favorite_recipient_id ON apl.favorite (recipient_id);
CREATE INDEX IF NOT EXISTS idx_apl_favorite_event_recipient ON apl.favorite (event_id, recipient_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_favorite_scope ON apl.favorite (
  user_id,
  coalesce(event_id, '00000000-0000-0000-0000-000000000000'::uuid),
  coalesce(recipient_id, '00000000-0000-0000-0000-000000000000'::uuid),
  item_id
);

CREATE TABLE IF NOT EXISTS apl.recommendation (
  id uuid PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id),
  context_id uuid REFERENCES apl.context(id),
  algorithm text NULL,
  params jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS apl.recommendation_item (
  id uuid PRIMARY KEY,
  recommendation_id uuid REFERENCES apl.recommendation(id),
  item_id uuid REFERENCES apl.item(id),
  rank int NULL,
  score float NULL,
  vector_score float NULL,
  rerank_score float NULL,
  reason jsonb NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_recommendation_item_rank ON apl.recommendation_item (recommendation_id, rank);
CREATE UNIQUE INDEX IF NOT EXISTS uq_apl_recommendation_item_item ON apl.recommendation_item (recommendation_id, item_id);

-- ------------------------------------------------------------
-- collector（楽天APIステージング）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS collector.rakuten_genre (
  genre_id int PRIMARY KEY,
  genre_name varchar NULL,
  genre_level integer NULL,
  parent_genre_id int NULL REFERENCES collector.rakuten_genre(genre_id),
  path varchar NULL,
  raw_json jsonb NOT NULL,
  source_hash varchar NULL,
  source_version int NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS collector.rakuten_tag_group (
  tag_group_id int PRIMARY KEY,
  tag_group_name varchar NULL,
  raw_json jsonb NOT NULL,
  source_hash varchar NULL,
  source_version int NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS collector.rakuten_tag_detail (
  tag_id int PRIMARY KEY,
  tag_name varchar NULL,
  tag_group_id int REFERENCES collector.rakuten_tag_group(tag_group_id),
  raw_json jsonb NOT NULL,
  source_hash varchar NULL,
  source_version int NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS collector.rakuten_genre_tag (
  genre_id int REFERENCES collector.rakuten_genre(genre_id),
  tag_group_id int REFERENCES collector.rakuten_tag_group(tag_group_id),
  tag_id int REFERENCES collector.rakuten_tag_detail(tag_id),
  raw_json jsonb NOT NULL,
  created_at timestamptz DEFAULT now(),
  PRIMARY KEY (genre_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_collector_rakuten_genre_tag_tag_id ON collector.rakuten_genre_tag (tag_id);

CREATE TABLE IF NOT EXISTS collector.rakuten_item_source (
  item_code varchar PRIMARY KEY,
  fetched_at timestamptz DEFAULT now(),
  source_hash varchar NOT NULL,
  source_version int NOT NULL,
  item_name varchar NULL,
  catchcopy varchar NULL,
  item_caption text NULL,
  item_price int NULL,
  item_url text NULL,
  affiliate_url text NULL,
  image_flag int NULL,
  availability int NULL,
  tax_flag int NULL,
  postage_flag int NULL,
  credit_card_flag int NULL,
  ship_overseas_flag int NULL,
  ship_overseas_area varchar NULL,
  asuraku_flag int NULL,
  asuraku_area varchar NULL,
  asuraku_closing_time varchar NULL,
  review_count int NULL,
  review_average numeric(5,2) NULL,
  point_rate int NULL,
  point_rate_start_time timestamptz NULL,
  point_rate_end_time timestamptz NULL,
  affiliate_rate int NULL,
  sale_start_time timestamptz NULL,
  sale_end_time timestamptz NULL,
  gift_flag int NULL,
  genre_id int NULL,
  shop_code varchar NULL,
  shop_name varchar NULL,
  shop_url text NULL,
  shop_of_the_year_flag int NULL,
  raw_json jsonb NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_collector_rakuten_item_source_fetched_at ON collector.rakuten_item_source (fetched_at);
CREATE INDEX IF NOT EXISTS idx_collector_rakuten_item_source_genre_id ON collector.rakuten_item_source (genre_id);
CREATE INDEX IF NOT EXISTS idx_collector_rakuten_item_source_shop_code ON collector.rakuten_item_source (shop_code);
CREATE INDEX IF NOT EXISTS idx_collector_rakuten_item_source_hash ON collector.rakuten_item_source (source_hash);

CREATE TABLE IF NOT EXISTS collector.rakuten_item_image_source (
  item_code varchar NOT NULL REFERENCES collector.rakuten_item_source(item_code),
  size varchar NOT NULL,
  url text NOT NULL,
  sort_order int NOT NULL,
  raw_json jsonb NOT NULL,
  created_at timestamptz DEFAULT now(),
  PRIMARY KEY (item_code, size, sort_order)
);
CREATE INDEX IF NOT EXISTS idx_collector_rakuten_item_image_source_item_code ON collector.rakuten_item_image_source (item_code);

CREATE TABLE IF NOT EXISTS collector.rakuten_item_tag (
  item_code varchar NOT NULL REFERENCES collector.rakuten_item_source(item_code),
  tag_id int NOT NULL,
  raw_json jsonb NOT NULL,
  created_at timestampz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_collector_rakuten_item_tag_item_tag ON collector.rakuten_item_tag (item_code, tag_id);

CREATE TABLE IF NOT EXISTS collector.rakuten_ranking_run (
  run_id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  fetched_at timestamptz DEFAULT now(),
  title varchar NULL,
  genre_id int NULL,
  age_group int NULL,
  sex int NULL,
  period varchar NOT NULL,
  raw_json jsonb NOT NULL,
  source_hash varchar NULL,
  source_version int NULL,
  last_etl_source_hash varchar NULL,
  last_etl_processed_at timestamptz NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_collector_rakuten_ranking_run_period_fetched ON collector.rakuten_ranking_run (period, fetched_at);
CREATE INDEX IF NOT EXISTS idx_collector_rakuten_ranking_run_genre_fetched ON collector.rakuten_ranking_run (genre_id, fetched_at);

CREATE TABLE IF NOT EXISTS collector.rakuten_ranking_item (
  run_id int NOT NULL REFERENCES collector.rakuten_ranking_run(run_id),
  rank int NOT NULL,
  item_code varchar NOT NULL,
  raw_json jsonb NOT NULL,
  created_at timestamptz DEFAULT now(),
  PRIMARY KEY (run_id, rank)
);
CREATE INDEX IF NOT EXISTS idx_collector_rakuten_ranking_item_item_code ON collector.rakuten_ranking_item (item_code);

CREATE TABLE IF NOT EXISTS collector.job_run_log (
  run_id bigserial PRIMARY KEY,
  job_name varchar NOT NULL,
  job_version int NOT NULL DEFAULT 1,
  status varchar NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz NULL,
  args_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  env_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  counts_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_code varchar NULL,
  error_summary text NULL,
  error_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  correlation_id varchar NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_collector_job_run_log_job_started ON collector.job_run_log (job_name, started_at);
CREATE INDEX IF NOT EXISTS idx_collector_job_run_log_status_started ON collector.job_run_log (status, started_at);
CREATE INDEX IF NOT EXISTS idx_collector_job_run_log_correlation_id ON collector.job_run_log (correlation_id);

CREATE TABLE IF NOT EXISTS collector.target_genre_config (
  genre_id int PRIMARY KEY,
  is_enabled bool DEFAULT true,
  use_ranking bool DEFAULT true,
  max_rank int NULL,
  use_item_search bool DEFAULT false,
  max_items_per_day int NULL,
  min_price int NULL,
  max_price int NULL,
  min_review_count int NULL,
  min_review_average numeric(3,2) NULL,
  priority int DEFAULT 5,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS collector.pending_item_fetch (
  item_code varchar PRIMARY KEY,
  reason varchar NOT NULL,
  priority int NOT NULL DEFAULT 5,
  state varchar NOT NULL DEFAULT 'NEW',
  attempts int NOT NULL DEFAULT 0,
  last_error text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_collector_pending_item_fetch_state_priority_updated ON collector.pending_item_fetch (state, priority, updated_at);
CREATE INDEX IF NOT EXISTS idx_collector_pending_item_fetch_reason_created ON collector.pending_item_fetch (reason, created_at);

CREATE TABLE IF NOT EXISTS collector.pending_task (
  task_type varchar NOT NULL,
  entity_type varchar NOT NULL,
  entity_key varchar NOT NULL,
  reason varchar NOT NULL,
  priority int NOT NULL DEFAULT 5,
  state varchar NOT NULL DEFAULT 'NEW',
  attempts int NOT NULL,
  max_attempts int NOT NULL DEFAULT 5,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  last_error text NULL,
  leased_until timestamptz NULL,
  lease_owner varchar NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_collector_pending_task_entity ON collector.pending_task (task_type, entity_type, entity_key);
