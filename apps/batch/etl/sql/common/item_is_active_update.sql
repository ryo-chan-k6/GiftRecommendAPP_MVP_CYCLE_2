with computed as (
  select
    i.id,
    (
      exists (select 1 from apl.genre g where g.rakuten_genre_id = i.rakuten_genre_id)
      and
      exists (select 1 from apl.shop s where s.rakuten_shop_code = i.rakuten_shop_code)
    ) as next_is_active
  from apl.item i
)
update apl.item i
set
  is_active  = c.next_is_active,
  updated_at = now()
from computed c
where i.id = c.id
  and i.is_active is distinct from c.next_is_active;
