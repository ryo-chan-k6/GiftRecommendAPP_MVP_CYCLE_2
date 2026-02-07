-- returns 1 row if matches; 0 rows otherwise
select 1
from apl.staging s
where s.source = :source
  and s.entity = :entity
  and s.source_id = :source_id
  and s.content_hash = :content_hash
limit 1;
