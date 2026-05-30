-- ============================================================================
-- Eamos - Private source asset Storage bucket
-- ============================================================================
-- Scope: create the approved private bucket for backend-owned large source
-- assets. The Storage API remains service-role/backend owned; browser access is
-- still blocked by the private bucket posture plus the private metadata tables.
--
-- Guardrail: the bucket is private, upload size and content type are bounded,
-- no public URLs are created, and backend jobs must continue to use service-role
-- Storage access plus eamos_private checksum/materialization metadata.
-- ============================================================================

insert into storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
)
values (
    'eamos-source-assets',
    'eamos-source-assets',
    false,
    1073741824,
    array['application/octet-stream']::text[]
)
on conflict (id)
do update set
    name = excluded.name,
    public = false,
    file_size_limit = greatest(
        coalesce(storage.buckets.file_size_limit, 0),
        excluded.file_size_limit
    ),
    allowed_mime_types = excluded.allowed_mime_types,
    updated_at = timezone('utc'::text, now());
