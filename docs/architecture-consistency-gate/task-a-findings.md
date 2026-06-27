# Task A Architecture Inventory Findings

Last updated: 2026-06-27 19:42 +1000 - Codex.
Status: Read-only static inventory. No deploy, Render env mutation, Supabase
mutation, Vercel command, startup/request-time download, or materialization ran.

Machine-readable artifact:

- `docs/architecture-consistency-gate/inventory.json`

Inventory scope:

- 63 backend route handlers under `app/backend/app/api/routes`;
- 19 SQLAlchemy tables from `app/backend/app/core/db.py::Base.metadata`;
- 8 cache/identity tables called out explicitly;
- 31 source-registry rows from `DEFAULT_DATA_SOURCE_REGISTRY`;
- 7 report-section registry entries;
- workbench/report frontend surfaces and preflight/health surfaces.

## Findings

1. Route coverage is now machine-readable, but rate-limit posture still needs
   route-family decisions.

   Static scan found 19 non-health handlers without an inline
   `enforce_rate_limit(...)` call. Most are authenticated report/run/search
   routes where auth may be the intended perimeter, but batch create/read and
   panel lookup remain the clearest review targets because they are not
   route-authenticated in the static scan.

2. Local SQLAlchemy FK index coverage passes static inspection.

   The generated artifact found no SQLAlchemy foreign-key columns without an
   index or primary-key coverage. This is local metadata only; Supabase remote
   schema/advisor proof is still Task F.

3. Report cache ownership is explicit.

   `normalized_variant`, `report_shell_cache`, `report_section_cache`,
   `source_result_cache`, and `section_hydration_status` are present with
   schema-version, status/freshness, uniqueness, and lookup indexes. Legacy
   `variant_cache.publication_data` remains compatibility state, not the target
   owner for new section payloads.

4. The frontend report registry exists and has the required state copy fields.

   `app/web/lib/report-section-registry.json` defines seven stable desktop
   report slots, registry anchors, required/preflight flags, lazy section IDs,
   and empty/partial/failed/stale copy. Task B should harden the runtime state
   mapping and preflight assertions rather than introduce the registry from
   scratch.

5. Health and preflight surfaces are present but not a production sign-off.

   `/healthz`, `/api/v1/health/provider-cache`, backend preflight CLIs, and
   `scripts/eamos-report-preflight.mjs` are inventoried. They prove local code
   surface coverage only; live readiness still needs approved reruns when a
   deploy or remote mutation is actually requested.

6. Supabase production readiness is unproven by design.

   The static inventory cannot prove remote RLS, grants, advisors, storage
   policies, exposed schema settings, FK/composite indexes, or secret exposure.
   Task F must remain a read-only runbook until Steven explicitly approves a
   remote Supabase action.

7. Task E production closeout is now captured.

   The original static inventory preserved the pre-deploy live gap. The
   deployed 2026-06-27 rerun now proves
   `/api/v1/lookup/sections?include=therapies_trials` returns HTTP 200 with an
   available payload, with timing/payload/preflight/RSS evidence recorded in
   `docs/architecture-consistency-gate/task-e-performance-memory-evidence.md`.
