# Archived Codex Last Task & Resume - pre ACMG points core replace

Archived 2026-06-14 21:59 +10:00 by Codex before replacing the Codex section in
`agent_handoff/CURRENT.md`.

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-06-14 20:17 +10:00 - Codex. Prior Codex section archived at `agent_handoff/archive/2026-06-14-codex-paper-front-door-acmg-pre-library-sync.md`.

**Latest Codex update (2026-06-14 20:17 +10:00 - Codex):**
Paper response `source_metadata` alignment and account-synced library backend are complete locally. Claude's experimental-construct refinement needs no backend change: experimental rows keep `context=experimental_construct`, `validated=false`, and source-backed same-residue recommendations in `candidates[]` for explicit user selection/open/save.

Completed:
- Added `PaperSourceMetadata` and top-level `source_metadata: null` to `PaperVariantsExtractResponse` and the CLI-style paper report. Mock/regex path does not guess bibliographic metadata.
- Added whole-document `PUT /api/v1/library` alongside existing `GET /api/v1/library`, login-gated and `RATE_LIMIT_LIBRARY` scoped to the authenticated principal. `GET` returns the synced document when present and falls back to the existing normalized legacy rows otherwise.
- Added `LibraryReplaceRequest` and `LibraryStore.updated_at`; payload is bounded and rejects extra top-level fields.
- Added local `user_library` SQLAlchemy table plus local/Supabase repo methods for one-row-per-user `{variants, folders, updated_at}` read/upsert. Backend always supplies `user_id` from auth, never from the request body.
- Added Supabase migration `20260614195800_user_library_document.sql` with JSONB arrays, owner RLS, and service_role DML grants. No Supabase mutation was run.
- Added API, Supabase repo, and migration tests for auth, account isolation, whole-document round trip, service-role owner filters, and JSONB/RLS contract.

Verification recorded 2026-06-14 20:17 +10:00:
- Focused: `python -m pytest tests/test_paper_variants.py tests/test_variant_library_api.py tests/test_variant_library_supabase.py tests/test_supabase_migrations.py -q` passed.
- Broader backend slice: `python -m pytest tests/test_paper_variants.py tests/test_rate_limits.py tests/test_report_acmg_contract.py tests/test_variant_library_api.py tests/test_variant_library_supabase.py tests/test_supabase_migrations.py tests/test_search_input_resolver.py tests/test_variant_search_integration.py tests/test_lookup_normalize.py tests/test_tool_invariants.py tests/test_clingen_local.py -q` passed.
- Ruff passed for touched backend/schema/repo/service/test files.
- Black `--check` passed for the same files (known Python 3.10/3.15 parser warning only).
- `git diff --check` passed with line-ending warnings only.
- `node scripts/eamos-encoding-scan.mjs ... --json` passed for touched backend/handoff files.
- `python -m graphify update .` timed out at the tool boundary but the process finished; graph outputs updated at 2026-06-14 20:15.
- `python -m pytest tests/test_frontend_contract.py -q` still fails on the pre-existing frontend mirror drift: `ReportPayload.eamos_computed_classification` missing in both TS mirrors, and `app/frontend/src/lib/backend.ts` / `app/web/lib/backend.ts` not byte-identical.

Guardrails:
- No Render env/provider flip, Supabase mutation, startup download/materialization, commit, push, RAG enablement, AI-gateway runtime flip, ACMG points-engine work, or `clinical_consensus.py` edits.
- Kept Claude-owned frontend files and `docs/library-sync/` untouched.

Message for Claude:
- Paper response now includes `source_metadata: PaperSourceMetadata | null`, where `PaperSourceMetadata = {title, authors, year, journal, doi, pmid}` and mock returns null.
- Library backend contract now supports `GET /api/v1/library -> {variants, folders, updated_at}` and `PUT /api/v1/library {variants, folders} -> {variants, folders, updated_at}`. Existing granular library endpoints remain.
- Frontend contract canary is still red only on `eamos_computed_classification` TS mirror/byte-identity drift.

**Latest resume prompt:**
```text
# Resume prompt - 2026-06-14 20:17 +1000 - Codex paper metadata + library sync backend complete
Eamos. Read CODEX.md, AGENTS.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, docs/paper-variants-ui/spec.md, docs/report-acmg-viz/spec.md, docs/report-acmg-viz/plan.md, then run git fetch origin && git status --short --branch.
Delta: paper `source_metadata` response field is wired mock-null, account-synced library backend `GET/PUT /api/v1/library` is complete locally with one-row-per-user JSONB migration, and protein-only experimental recommendations remain fail-closed in `candidates[]`. Backend pytest/Ruff/Black/diff/encoding green; graphify outputs refreshed after the tool timeout.
Next: Claude/frontend still owns TS mirror drift (`ReportPayload.eamos_computed_classification` + backend.ts byte identity) and live mock swap; Codex next backend queue should not start ACMG points engine, VCEP overlay, AI narration, benchmark harness, ClinVar P/B precompute, Render/Supabase/startup-download/provider flip, commit, or push unless explicitly asked. End clear-safe.
```
