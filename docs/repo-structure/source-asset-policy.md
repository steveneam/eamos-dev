# Eamos source asset policy

Status: active policy for tracked `app/backend/data/source_assets`.
Created: 2026-06-30 by Codex.

## Decision

`app/backend/data/source_assets` is a reviewed, manifest-backed release asset
set. It is not a scratch area, download destination, runtime seed directory, or
frontend-readable asset bucket.

The current tracked files are kept in place for now because backend source
readers and tests already depend on them. This pass does not delete, move,
download, upload, sync, or re-materialize any asset.

## Rules

- Every tracked file under `app/backend/data/source_assets/<source_id>/` must use
  a `source_id` that exists in `app/backend/app/data_sources/registry.py`.
- Every tracked payload or checksum file must have a sibling
  `.manifest.json` file.
- New tracked source assets require a registry entry with source URL, source
  version, checksum plan or checksum, terms review, storage target, and backend
  storage policy review.
- Large generated/runtime artifacts belong in explicit materialization lanes:
  private Storage, Render disk, or ignored backend-local `data/bio_assets/**`.
  They must not be added to this tracked source asset set by convenience.
- Browser/frontend code must not read this folder directly and must not receive
  raw source asset paths, object URIs, service-role credentials, or local disk
  paths in API responses.
- Request paths must not download, seed, sync, or materialize these assets.
  Operator work uses explicit CLI/preflight flows and Steven-approved commands.

## Enforcement

`app/backend/tests/test_structure_guard.py` includes
`test_tracked_source_assets_are_manifest_backed_registered_assets`.

That guard blocks unregistered tracked source asset directories and tracked
payload/checksum files without manifest sidecars. It deliberately does not
delete existing files or decide whether the current asset set should eventually
move behind a private materialization flow.

## Follow-Up

Future source-asset cleanup should decide asset by asset:

- Keep as tracked release asset when the file is small enough, terms-reviewed,
  manifest-backed, and useful for deterministic local behavior.
- Move behind materialization when the file is large, frequently refreshed,
  generated, licensed for backend-only handling, or operationally better suited
  to private Storage and Render disk.

Any move must come with reader mapping, replacement fixtures, preflight output,
and focused tests before the old tracked file is removed.
