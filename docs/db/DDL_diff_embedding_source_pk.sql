-- DDL差分案（MVP）：apl.item_embedding の source_hash 追加
-- NOTE: apl.item_embedding_source の複合PK化は見送り

begin;

alter table apl.item_embedding
  add column if not exists source_hash varchar;

create index if not exists idx_apl_item_embedding_source_hash
  on apl.item_embedding(source_hash);

commit;

