insert into apl.staging
(source, entity, source_id, content_hash, s3_key, etag, saved_at)
values (:source, :entity, :source_id, :content_hash, :s3_key, :etag, :saved_at)
on conflict (source, entity, source_id) do update set
content_hash = excluded.content_hash,
s3_key = excluded.s3_key,
etag = excluded.etag,
saved_at = excluded.saved_at,
updated_at = now();
