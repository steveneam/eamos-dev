# Architecture Consistency Gate Session Prompts

Last updated: 2026-06-25 18:37 +1000 - Codex.

Use these prompts when resuming the architecture consistency work. Keep each
session scoped to one gate task unless Steven explicitly expands it.

## Prompt 1 - Architecture Inventory Closeout and Task B Decision

```text
# Resume prompt - 2026-06-25 18:37 +1000 - Codex architecture consistency gate committed+pushed; start Task A checklist closeout
Eamos. Read AGENTS.md, CODEX.md, MEMORY.md, memory/eamos-architecture-consistency-gate.md, agent_handoff/README.md, agent_handoff/CURRENT.md (Codex section + Cross-Agent Requests), docs/operations/risks-and-guardrails.md, docs/architecture-consistency-gate/plan.md, docs/architecture-consistency-gate/inventory.md, docs/architecture-consistency-gate/session-prompts.md, docs/report-performance-optimization/plan.md, docs/data-architecture-duckdb-parquet/adr.md, docs/data-architecture-duckdb-parquet/plan.md, then run git fetch origin; git status --short --branch; git log -8 --oneline.
Delta: Architecture gate work is committed and pushed to origin/main; run `git log -8 --oneline` for the exact top commit. Key commits include `1a80f45 feat(report): cache lazy lookup sections`, `98e35fc docs(architecture): capture consistency gate`, and `55224cf docs(architecture): add next prompt and selom note`. The architecture gate covers backend routes, SQL/cache ownership, UI report-section registry drift, DuckDB/Parquet analytical lane, PubMed/PMC literature corpus layering, Supabase/Render storage boundaries, performance/memory proof, slow-test hygiene, and production-readiness gates. No deploy, Supabase mutation, Render mutation, DuckDB repo clone, or multi-GB materialization occurred.
Next default: start Task A by converting `docs/architecture-consistency-gate/inventory.md` into a compact actionable checklist with owners, gates, and pass/fail evidence; then start Task B frontend report section registry/stable skeletons and extend report preflight to assert required section slots before hydration. If Steven redirects to data architecture, do Task D only: tiny-fixture DuckDB/Parquet artifact layout + manifest + read-only preflight, no real corpus build.
Guardrails: no deploy unless explicitly requested; do not run vercel/vc from app/web; no Render env or Supabase mutation without explicit approval; no startup/request-time downloads; do not move single-coordinate lookup off prepared cache/tabix/SQLite; keep PubMed/PMC as layered corpus architecture: object/private storage + Parquet release layers + runtime SQLite/FTS/vector stores + report/source caches. End clear-safe with a fresh stamped resume prompt.
```

## Gate Task Order

1. Task A - Architecture inventory checklist and findings.
2. Task B - Frontend report section registry and stable skeletons.
3. Task C - Cache boundary cleanup around `variant_cache` compatibility.
4. Task D - DuckDB/Parquet tiny fixture artifact preflight.
5. Task E - Performance and memory proof.
6. Task F - Supabase production readiness review.
