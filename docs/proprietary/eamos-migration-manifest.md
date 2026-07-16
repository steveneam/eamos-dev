# Eamos Migration Asset Manifest Verifier

Status: Active

Type: Operator CLI + checksum reconciliation service

Owner: Codex

Added: 2026-07-16 08:41 +0000 - Codex

Last updated: 2026-07-16 08:41 +0000 - Codex

## What It Does

Builds a deterministic manifest of the private Supabase source-asset bucket
using list/head calls and bounded reads of objects no larger than one MiB. It
also builds filesystem-tree manifests and compares source-bucket content with a
runtime manifest by SHA-256 plus byte size, independent of differing relpaths.

The source workflow fails closed when list/head sizes, actual small-object
content, content-addressed paths, adjacent sidecars, or reviewed legacy
overrides disagree. The comparison reports every runtime-only content identity
and returns a nonzero status when any is present.

## Why It Is Eamos-Original

The workflow encodes Eamos's Render-to-syd2 proof: source objects and
materialized runtime assets have intentionally different paths, while the
migration gate asks whether any bytes exist only on the disposable Render
disk. The reconciler combines multiple project-specific checksum authorities
without downloading the roughly 41 GiB source corpus during readiness checks.

## Source Of Truth

- Service: `app/backend/app/services/migration_asset_manifest.py`
- CLI: `app/backend/app/cli/eamos_migration_manifest.py`
- Reviewed legacy checksum input:
  `app/backend/app/migration-source-overrides.json`
- Tests: `app/backend/tests/test_migration_asset_manifest.py`
- Operator runbook: `docs/deployment/render-to-syd2-phase1.md`
- Entry points:
  - `python -m app.cli.eamos_migration_manifest source`
  - `python -m app.cli.eamos_migration_manifest tree --root <path>`
  - `python -m app.cli.eamos_migration_manifest compare --source <file> --runtime <file>`

## Caveats

- Supabase S3 access keys are server-side, full-access credentials. The CLI has
  no mutation operation, but the surrounding credential still requires secret
  handling and a trusted checkout.
- Existing large S3 objects do not all expose a server-verifiable SHA-256. The
  verifier relies on agreeing content-addressed paths/sidecars and one reviewed
  Pfam override; hashing downloaded destination bytes remains mandatory.
- Content comparison proves that no runtime file identity is absent from the
  source inventory. It does not prove that every source object is materialized,
  nor does it replace an exact relpath diff of the final syd2 runtime tree.
