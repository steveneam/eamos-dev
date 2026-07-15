> ARCHIVED 2026-07-15 11:19 UTC by Codex - durable database and storage
> guardrails moved to `RISKS.md` and `docs/db/supabase-inventory.md`. Original
> content follows verbatim.

---

# Database / Webserver Handoff

Scope: coordination notes for Supabase, backend webserver database wiring, private source storage, import jobs, cache persistence, and frontend/API boundaries.

This folder uses the main `agent_handoff/README.md` protocol and the single global log lock in `agent_handoff/CURRENT.md`. Do not create an independent lock protocol here.

## Rules

- No secrets in this folder: no service-role key, database URL, JWT secret, Vercel token, Render secret, or signed source URL.
- Record project identifiers, migration names, table names, endpoint contracts, checks, and smoke results only.
- Frontend/Vercel must call backend APIs for source/cache data. Do not direct the browser at `eamos_private` tables or raw source objects.
- Supabase source/cache tables and source assets are backend-owned.
- Storage buckets for genomic/protein/source files must be private. Public buckets and unrestricted uploads are blocked.
- Large assets are metadata-only until an explicit bucket/object upload plan is approved.
- Every DDL/import/storage change needs security advisors, performance advisors, and a small smoke query or import proof.
- If Claude needs a frontend contract, record the backend endpoint/status semantics here; do not expose private table schema as a UI dependency.

## What Belongs Here

- Applied Supabase migrations and advisor outcomes.
- Private schema/table inventory and row counts after smoke/import jobs.
- Source storage design decisions, bucket/object path conventions, and materialization rules.
- Import job status for Tier 2/Tier 3 sources.
- Backend env/config decisions after explicit approval.
- Claude-facing API contracts and warnings/status strings.

## What Stays Elsewhere

- Narrative session history: `PROGRESS.md`.
- Current global agent heartbeat and shared locks: `agent_handoff/CURRENT.md`.
- Risks and guardrails: `agent_handoff/RISKS.md`.
- Detailed architecture design: `docs/private-source-storage/design.md`.
