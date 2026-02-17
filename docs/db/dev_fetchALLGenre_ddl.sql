-- ジャンル本体（最新1件だけ保持：genre_id を PK にして upsert）
create table if not exists rakuten_genre (
  genre_id        bigint primary key,
  genre_name      text not null,
  genre_level     int  not null,
  parent_genre_id bigint null,
  english_name    text null,
  link_genre_id   bigint null,
  chopper_flg     int null,
  lowest_flg      int null,
  raw_json        jsonb not null,
  fetched_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- fetch状態（再開・並列・テスト制御の要）
create table if not exists rakuten_genre_fetch_state (
  genre_id     bigint primary key,
  status       text not null check (status in ('PENDING','IN_PROGRESS','DONE','ERROR')),
  try_count    int  not null default 0,
  last_error   text null,
  locked_by    text null,
  locked_at    timestamptz null,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index if not exists idx_rakuten_genre_fetch_state_status
  on rakuten_genre_fetch_state (status, updated_at);
