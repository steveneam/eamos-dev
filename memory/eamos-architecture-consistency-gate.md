---
type: memory
topic: architecture
date: 2026-06-25
---

# Eamos Architecture Consistency Gate

Before expanding Eamos features, keep new work aligned to the shared skeleton:
input/lookup resolution -> normalized identity -> source adapter or prepared
cache -> source/result or report/section cache -> stable frontend section slot
-> health, preflight, timing, payload-size, memory, and freshness proof.

Architecture gate docs live at:

- `docs/architecture-consistency-gate/plan.md`
- `docs/architecture-consistency-gate/inventory.md`
- `docs/architecture-consistency-gate/session-prompts.md`

Key boundaries:

- Single-coordinate lookup stays on prepared cache, tabix, SQLite, and local
  indexes unless a benchmark-backed ADR changes that.
- DuckDB/Parquet is the analytical/build lane for batch, region, cohort,
  freshness, and release-artifact work.
- PubMed/PMC needs layered corpus architecture: upstream objects/manifests,
  Parquet release layers, compact SQLite/FTS/vector runtime stores, and
  report/source caches. Do not put huge article blobs in Supabase Postgres.
- Supabase Postgres governs metadata, app/user state, cache tables, and RLS;
  private object storage holds large immutable source artifacts.

Next default from the gate: Task A checklist closeout, then Task B report
section registry/stable skeletons. If Steven redirects to data architecture,
do Task D only: tiny-fixture DuckDB/Parquet manifest/preflight, no real corpus
materialization.
