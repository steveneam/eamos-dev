-- Cover the saved_variant.folder_id foreign key for parent folder delete/update
-- maintenance. The user-folder composite index serves app reads but does not
-- cover FK checks by folder_id alone.
create index if not exists idx_saved_variant_folder_id
on public.saved_variant(folder_id)
where folder_id is not null;
