-- apl.item_feature_view (MVP)
-- Purpose: Single source of truth for "latest item features" used by embedding / feature builds.
-- Notes:
-- - No FK constraints assumed; ETL maintains consistency.
-- - Latest snapshots are selected by collected_at DESC LIMIT 1 via LATERAL joins.
-- - Tags are aggregated as arrays.

create or replace view apl.item_feature_view as
select
  -- item identity
  i.id                         as item_id,
  i.rakuten_item_code          as rakuten_item_code,

  -- item core
  i.item_name                  as item_name,
  i.catchcopy                  as catchcopy,
  left(i.item_caption, 2000)   as item_caption,
  i.item_url                   as item_url,
  i.affiliate_url              as affiliate_url,
  i.image_flag                 as image_flag,
  i.credit_card_flag           as credit_card_flag,

  -- relations (no FK, but ETL keeps them consistent)
  i.rakuten_shop_code          as rakuten_shop_code,
  s.shop_name                  as shop_name,
  s.shop_url                   as shop_url,

  i.rakuten_genre_id           as rakuten_genre_id,
  g.name                       as genre_name,
  g.level                      as genre_level,
  g.parent_id                  as genre_parent_id,

  -- tags (aggregated)
  coalesce(t.tags, array[]::varchar[])       as tag_names,
  coalesce(t.tag_ids, array[]::bigint[])     as rakuten_tag_ids,
  t.tag_updated_at              as tag_updated_at,

  -- latest market snapshot
  ms.collected_at              as market_collected_at,
  ms.item_price                as item_price,
  ms.tax_flag                  as tax_flag,
  ms.postage_flag              as postage_flag,
  ms.gift_flag                 as gift_flag,
  ms.availability              as availability,
  ms.asuraku_flag              as asuraku_flag,
  ms.asuraku_closing_time      as asuraku_closing_time,
  ms.asuraku_area              as asuraku_area,
  ms.start_time                as start_time,
  ms.end_time                  as end_time,
  ms.point_rate                as point_rate,
  ms.point_rate_start_time     as point_rate_start_time,
  ms.point_rate_end_time       as point_rate_end_time,

  -- latest review snapshot
  rs.collected_at              as review_collected_at,
  rs.review_count              as review_count,
  rs.review_average            as review_average,

  -- latest ranking snapshot (by rakuten_item_code)
  rks.collected_at             as rank_collected_at,
  rks.rakuten_genre_id         as rank_rakuten_genre_id,
  rks.rank                     as rank,
  rks.title                    as rank_title,

  -- features (optional; 1 row per item_id)
  f.features_version           as features_version,
  f.price_yen                  as feature_price_yen,
  f.price_log                  as feature_price_log,
  f.point_rate                 as feature_point_rate,
  f.availability               as feature_availability,
  f.review_average             as feature_review_average,
  f.review_count               as feature_review_count,
  f.review_count_log           as feature_review_count_log,
  f.rank                       as feature_rank,
  f.rakuten_genre_id            as feature_rakuten_genre_id,
  f.tag_ids                    as feature_tag_ids,
  f.popularity_score           as popularity_score,

  -- active flag
  i.is_active                  as is_active,

  -- timestamps
  i.created_at                 as item_created_at,
  i.updated_at                 as item_updated_at,
  greatest(
    i.updated_at,
    coalesce(f.updated_at, i.updated_at),
    coalesce(ms.collected_at, i.updated_at),
    coalesce(rs.collected_at, i.updated_at),
    coalesce(rks.fetched_at, i.updated_at),
    coalesce(g.updated_at, i.updated_at),
    coalesce(t.tag_updated_at, i.updated_at)
  )                            as feature_updated_at

from apl.item i
left join apl.shop s
  on s.rakuten_shop_code = i.rakuten_shop_code
left join apl.genre g
  on g.rakuten_genre_id = i.rakuten_genre_id

-- tags aggregation
left join lateral (
  select
    array_agg(tag_name order by tag_name) as tags,
    array_agg(tag_id order by tag_id) as tag_ids,
    max(tag_updated_at) as tag_updated_at
  from (
    select distinct
      tg.name as tag_name,
      it.rakuten_tag_id as tag_id,
      tg.updated_at as tag_updated_at
    from apl.item_tag it
    join apl.tag tg
      on tg.rakuten_tag_id = it.rakuten_tag_id
    where it.item_id = i.id
    order by tg.name
    limit 30
  ) limited_tags
) t on true

-- latest market snapshot per item
left join lateral (
  select *
  from apl.item_market_snapshot x
  where x.item_id = i.id
  order by x.collected_at desc
  limit 1
) ms on true

-- latest review snapshot per item
left join lateral (
  select *
  from apl.item_review_snapshot x
  where x.item_id = i.id
  order by x.collected_at desc
  limit 1
) rs on true

-- latest rank snapshot per itemCode
left join lateral (
  select *
  from apl.item_rank_snapshot x
  where x.rakuten_item_code = i.rakuten_item_code
  order by x.fetched_at desc
  limit 1
) rks on true

left join apl.item_features f
  on f.item_id = i.id
;
