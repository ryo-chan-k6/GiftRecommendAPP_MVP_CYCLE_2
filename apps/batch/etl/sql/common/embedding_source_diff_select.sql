-- Select items that need embedding (missing or source_hash changed)
-- Params: %s (model)
select
  src.item_id,
  src.source_text,
  src.source_hash
from apl.item_embedding_source src
left join apl.item_embedding emb
  on emb.item_id = src.item_id
  and emb.model = %s
where emb.item_id is null
  or emb.source_hash is distinct from src.source_hash
order by src.item_id;
