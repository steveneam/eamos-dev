# Local-Evidence Freshness & Update Policy — Plan

Status: Draft for review (Claude-drafted at Steven's request, 2026-06-21 23:xx +1000)
Owners: per-task lane tags below — `[Codex]` backend/materialization, `[Claude]`
frontend/provenance + spec, `[Steven]` approval gates.
Trigger: Codex CAR 2026-06-21 23:22 +1000 — "local-asset freshness/update policy
for the now-live local evidence stack" (Steven's question: how do local copies
stay current when ClinVar/ClinGen/etc. publish new entries?).

## Sequencing (read first)

- **Codex** picks up its lane **after** finishing the post-M9 plan
  (`docs/post-m9-flip-readiness/plan.md`) — this is the lower-priority follow-on.
- **Claude** can start the FE provenance lane (Phase 4) **mock-first and
  independently**, since it only consumes a freshness contract (auto-upgrades to
  the live block when Codex's Phase 0 lands).
- **Phase 0 (freshness metadata) gates everything else** — you cannot alert on,
  or display, staleness you do not measure. Do it first.
- Do **not** bundle any of this into a runtime flag flip. Refresh that swaps
  clinical data on the sole live SG backend stays operator-gated + Steven-approved.

## Source Context

The M9 local-evidence stack is now LIVE on `eamos-dev-sg` (Phase 0 of the post-M9
plan executed 2026-06-21 23:10 +1000): lookups serve `source_status:"local"`
clinical consensus off local ClinVar + ClinGen, plus AlphaMissense / dbSNP /
phyloP / RepeatMasker. The repo already has guarded operator materialization
mechanisms — `eamos_source_download`, `eamos_source_storage_upload`,
`eamos_materialize_all`, `eamos_generated_artifact_upload`/`sync`, the ClinGen
fetch/materialize/preflight CLIs, and source-asset/provider-cache readiness — all
with manifests/checksums and **no startup or request-time downloads**. The gap:
**no freshness SLA, no staleness detection, no scheduled refresh, no "data as of"
provenance.**

Reuse, do not duplicate, these existing docs:

- `docs/backend-build-ledger-runtime/materialization-plan.md`
- `docs/clingen-local-materialization/spec.md`
- `docs/pubmed-corpus-materialization/spec.md`
- `docs/backend-evidence-roadmap/spec.md`
- `docs/deployment/materialization-lessons-learned.md`
- `docs/post-m9-flip-readiness/plan.md`
- `docs/operations/risks-and-guardrails.md` (sole-live-backend guardrails)

## Core principle — tier by volatility, not one global cadence

The seven live/near-live assets update on very different rhythms. A single refresh
policy is the wrong shape. Two tiers:

| Tier | Assets | Upstream cadence | Policy |
| ---- | ------ | ---------------- | ------ |
| **Volatile / clinical** | **ClinVar** (full VCF weekly, Mondays); **ClinGen** eRepo/CSpec (continuous, snapshot now `2026-06-19`) | ClinVar weekly, ClinGen ~continuous | Freshness SLA + scheduled detection + staleness alert. ClinVar is the highest-risk asset — a stale call can show a since-reclassified variant wrong, a real clinical/liability risk. |
| **Release-pinned / static** | dbSNP (build ~annual); phyloP (recomputed every few years); RepeatMasker (per genome build); AlphaMissense (frozen until DeepMind republishes) | rare, publisher-scheduled | No clock-based refresh. A periodic *"is there a newer upstream release?"* check that **notifies only**, never auto-pulls. |
| **Separate workflow** | PubMed / Literature RAG (not live yet) | deliberate corpus rebuild | Out of this loop — owned by post-M9 Phase 4 corpus-scope decision. Cross-ref only. |

Proposed SLAs: ClinVar `stale > 8d`, `overdue > 15d`; ClinGen `stale > 35d`,
`overdue > 60d`; static tier `check monthly`, no staleness state (drift = notify).

---

## Phase 0 — Freshness metadata primitive (observe before automate)

### Task 0.1 — Emit per-asset freshness metadata `[Codex, backend-led contract]`

Goal: Make staleness observable in `provider-cache` for every local asset.

Proposed approach:
- Add to each asset manifest + the `/api/v1/health/provider-cache` payload a
  `freshness` block: `materialized_at`, `upstream_version` / `upstream_released_at`
  (when known), `tier` (`volatile|static`), `sla_days`, `staleness_days`
  (computed), and `status` (`fresh|stale|overdue|unknown`).
- Keep it sanitized — no local paths, object URIs, or secrets (same guardrails as
  today's provider-cache booleans).
- Contract is backend-led (per coordination protocol); Claude mirrors the TS
  shape in Task 0.2.

Acceptance criteria:
- provider-cache emits a `freshness` block per live asset with a computed status.
- No path/secret/object-URI emission regression.
- Missing/unknown `upstream_released_at` degrades to `status:"unknown"`, never an error.

Verify: `provider-cache` 200 + focused health-API test asserting the new block.

Out of scope: the actual cron/alerting (Phase 1), any refresh (Phase 2).

### Task 0.2 — Consume freshness on the FE, mock-first `[Claude]`

Goal: TS-mirror the freshness contract and a small consumer, buildable before 0.1 ships.

Proposed approach:
- Mirror the `freshness` shape in `app/web/lib/backend.ts` (+ `app/frontend` mirror).
- Build against a `.eamos-mock` freshness fixture; auto-consume the live block when present.

Acceptance criteria: `tsc` + eslint clean; renders from mock; no hard dependency
on 0.1 being live (graceful when the block is absent).

Out of scope: the visible provenance line (Phase 4) — this is just the data plumbing.

---

## Phase 1 — Staleness detection (cheap, no full downloads) `[Codex]`

### Task 1.1 — Upstream version/release probe per source
Goal: Detect drift without downloading multi-GB assets.
Proposed approach: a probe that reads only the upstream release id/date (ClinVar
weekly VCF release date, ClinGen snapshot date, dbSNP build, UCSC/AlphaMissense
version) via HEAD/version metadata, and compares to the materialized version.
Acceptance criteria: probe returns `{source, materialized_version, latest_upstream,
drift: bool}` for each source; no full-asset download; fail-soft on upstream
unreachable (`drift: unknown`).
Verify: focused unit test over recorded upstream-version fixtures.
Out of scope: pulling/materializing anything.

### Task 1.2 — Scheduled detection + alerting
Goal: Run the probe on cadence and surface overdue assets.
Proposed approach: a **Render cron** (weekly for ClinVar; monthly for ClinGen +
the static-tier drift check) that runs Task 1.1, writes the result into the
freshness status, and emits a **Sentry** alert (Sentry is already live) when an
asset crosses its SLA into `overdue`. Detection only — no apply.
Acceptance criteria: cron runs on schedule; an artificially-stale asset produces
exactly one Sentry alert; healthy assets are silent; cron does no materialization.
Verify: manual cron trigger + Sentry event confirmation; provider-cache status flips.
Out of scope: the refresh itself (Phase 2).

---

## Phase 2 — Volatile-tier refresh runbook (operator-gated apply) `[Codex + Steven gate]`

### Task 2.1 — Document + script the end-to-end refresh `[Codex]`
Goal: One repeatable, reviewed path to refresh ClinVar/ClinGen.
Proposed approach: chain the EXISTING CLIs (`eamos_source_download` →
`eamos_materialize_all`/ClinGen materialize → checksum + preflight →
`eamos_source_storage_upload` to durable Supabase → `eamos_generated_artifact_sync`
to Render disk → provider-cache verify → redeploy). No new download paths. Mirrors
`materialization-lessons-learned.md` (env-as-code, durable object, verify-via-live-health,
metadata-reconcile-in-seeder, end-to-end dry-run before "ready").
Acceptance criteria: a runbook (`docs/local-evidence-freshness/runbook.md`) that an
operator can follow; each step has a verify; rollback = keep prior durable artifact + resync.
Out of scope: auto-apply; broadening allowed flows.

### Task 2.2 — Dry-run ClinVar refresh on SG `[Codex + Steven gate]`
Goal: Prove the runbook on the live box once, behind Steven's apply-approval.
Acceptance criteria: post-refresh provider-cache shows new ClinVar
`materialized_at`/version + `status:fresh`; RPE65 + 1 non-RPE65 lookup 200; memory
stable, no OOM/502; no path/secret/object-URI emission; prior artifact retained for rollback.
Verify: same smoke set as the M9 flip (healthz, provider-cache, lookups, get_metrics memory).
Out of scope: making it fully unattended (stays operator-gated for clinical data).

---

## Phase 3 — Static-tier drift policy `[Codex]`

### Task 3.1 — Notify-only drift handling for dbSNP / phyloP / RepeatMasker / AlphaMissense
Goal: Track new upstream releases without clock-based churn.
Proposed approach: include the static set in Task 1.2's monthly check, but only
**notify** on a new upstream release (no SLA staleness state, no auto-pull);
document the build-pinned re-materialization path for when one appears.
Acceptance criteria: a new upstream build for any static asset produces one
notification; no auto-materialization; doc names the per-asset re-pin steps.
Out of scope: any automatic refresh of static assets.

---

## Phase 4 — User-facing data provenance `[Claude]` (independently mock-first)

### Task 4.1 — Report "data as of" provenance line
Goal: Honest, trust-building data-currency on the report (Varsome/Franklin both do this).
Proposed approach: a small provenance line/tooltip — e.g. "Clinical data: ClinVar
as of <date> · ClinGen <date>" — sourced from the Phase 0 freshness metadata.
Mock-first via `.eamos-mock`; auto-fills from the live block when present.
Acceptance criteria: renders on `/report`; degrades cleanly when freshness is
absent; `tsc`/eslint clean; browser-verified; matches the design system.
Out of scope: backend metadata (Phase 0); admin dashboard (4.2).

### Task 4.2 — Internal freshness view (optional) `[Claude]`
Goal: An at-a-glance per-source freshness panel for the operator (admin/account surface).
Proposed approach: reuse the provider-cache `freshness` block; one compact table
(source · tier · materialized_at · status). Gated to the admin/account view.
Acceptance criteria: lists every live asset with its status; no secret/path leak;
reuses existing components. Out of scope: write actions (refresh stays CLI/operator).

---

## Phase 5 — PubMed / Literature-RAG corpus freshness (deferred) `[Codex]`

### Task 5.1 — Define corpus rebuild cadence once RAG is live
Cross-ref `docs/post-m9-flip-readiness/plan.md` Phase 4 + `pubmed-corpus-materialization/spec.md`.
Literature is a periodic deliberate rebuild, not part of the detection loop; fold a
freshness/rebuild-cadence note in once PubMed-local + embeddings are materialized.
Out of scope until the corpus exists.

## Global Guardrails

- No startup or request-time downloads; detection probes read version metadata only.
- Manifests + checksums for every materialized/refreshed artifact.
- **No auto-apply of clinical data** (ClinVar/ClinGen) on the live backend — apply
  stays operator-gated + Steven-approved. Detection/alerting can be automated; the swap cannot.
- Durable source = Supabase private Storage; Render disk = runtime cache only.
  Retain the prior durable artifact across a refresh for instant rollback.
- Every phase includes no-path / no-secret / no-object-URI verification.
- Never `git add -A`; keep parked/held files out of commits.
- After code changes, run `python -m graphify update .`.
