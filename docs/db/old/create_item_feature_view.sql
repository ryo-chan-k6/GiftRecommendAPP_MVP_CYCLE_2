-- item_features_view 作成SQL
-- 設計書: docs/batch/features_embedding/item_features_view_design.md

CREATE OR REPLACE VIEW apl.item_features_view AS
SELECT
    -- item基本情報
    i.id AS item_id,
    i.item_code,
    i.is_active,
    i.last_seen_at,
    i.shop_id,
    i.genre_id,
    
    -- genre情報
    g.rakuten_genre_id,
    
    -- tags（集約、rakuten_tag_idの配列）
    COALESCE(
        (SELECT array_agg(t.rakuten_tag_id ORDER BY t.rakuten_tag_id)
         FROM apl.item_tag it
         INNER JOIN apl.tag t ON it.tag_id = t.id
         WHERE it.item_id = i.id),
        '{}'::int[]
    ) AS tag_ids,
    
    -- market_snapshot（最新1件）
    m.item_price AS price_yen,
    m.point_rate,
    m.availability,
    m.gift_flag,
    m.collected_at AS market_collected_at,
    
    -- review_snapshot（最新1件）
    r.review_count,
    r.review_average,
    r.collected_at AS review_collected_at,
    
    -- rank_snapshot（最新1件、rank_type='daily'のみ）
    rank_snapshot.rank,
    'daily'::varchar AS rank_type,
    rank_snapshot.collected_at AS rank_collected_at
    
FROM apl.item i
LEFT JOIN apl.genre g ON g.id = i.genre_id
LEFT JOIN LATERAL (
    SELECT DISTINCT ON (item_id)
        item_id,
        item_price,
        point_rate,
        availability,
        gift_flag,
        collected_at
    FROM apl.item_market_snapshot
    WHERE item_id = i.id
    ORDER BY item_id, collected_at DESC
) m ON true
LEFT JOIN LATERAL (
    SELECT DISTINCT ON (item_id)
        item_id,
        review_count,
        review_average,
        collected_at
    FROM apl.item_review_snapshot
    WHERE item_id = i.id
    ORDER BY item_id, collected_at DESC
) r ON true
LEFT JOIN LATERAL (
    SELECT DISTINCT ON (item_id)
        item_id,
        rank,
        collected_at
    FROM apl.item_rank_snapshot
    WHERE item_id = i.id
        AND rank_type = 'daily'
    ORDER BY item_id, collected_at DESC
) rank_snapshot ON true;

-- コメント追加
COMMENT ON VIEW apl.item_features_view IS 'レコメンド/絞り込み/並び替えに必要な特徴量を1つの参照ポイントとして提供するVIEW。最新のmarket/review/rankスナップショットとtags/genre情報を統合。設計書: docs/batch/features_embedding/item_features_view_design.md';
