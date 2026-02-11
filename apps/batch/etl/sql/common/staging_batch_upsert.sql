insert into apl.staging
(source, entity, source_id, content_hash, s3_key, etag, saved_at, applied_at, applied_version)
values (:source, :entity, :source_id, :content_hash, :s3_key, :etag, :saved_at, null, null)
on conflict (source, entity, source_id) do update set
content_hash = excluded.content_hash,
s3_key = excluded.s3_key,
etag = excluded.etag,
saved_at = excluded.saved_at,
applied_at = null,
applied_version = null,
updated_at = now();
