# Batch VCF + Gene Panels — Frontend Design

> Surface: nav label **"Batch"** → route **`/compare`** (route name unchanged; there is **no** `/batch` page route — `/batch*` strings in the codebase are the `/api/v1/batch` API, not a Next route).
> App: Next.js 16 at `app/web/` (the active frontend). `app/frontend/` is the legacy Vite reference; `/runs` is frozen v1.
> Scope: design the GAP from the (substantial) current state to a complete, shippable Batch surface — large-VCF intake, the panel-filter UX, Pro/Max tiering, and results at scale.
> Status of inputs: `plans/batch-vcf-and-panels/spec.md` (authored 2026-06-03, §8 ratified by Codex 2026-06-04) and `plan.md` (2026-06-04) are **largely accurate** to the current tree — most of P1–P3 has shipped. Reconciliation notes are inline in §0. Authored 2026-06-06.

---

## §0 Ground-truth audit

Verified against the tree on 2026-06-06. Status legend: **BUILT** = real, functional; **MOCK-WIRED** = real component talking to a live-or-mock backend that returns placeholder data; **STUB** = exists but does not do the real work; **MISSING** = not found.

### Frontend (`app/web/`)

| Item | Status | Evidence (`file:line`) | Notes |
| ---- | ------ | ---------------------- | ----- |
| `/compare` route ("Batch") | BUILT | `app/web/app/compare/page.tsx:1-12` | Suspense-wrapped `CompareClient`. |
| `/batch` page route | MISSING | — | No `app/web/app/batch/**` exists. Nav "Batch" → `/compare`. |
| `CompareClient` (orchestrator) | MOCK-WIRED | `app/web/components/compare/CompareClient.tsx:48-211` | Full idle→running→done flow; submits `createBatch`, polls + pages `getBatchJob`; falls back to client-side `VariantTable` when offline / `mock-` job. |
| `ScopeGate` (filter rail) | BUILT | `app/web/components/compare/ScopeGate.tsx:47-246` | Active-scope chips + "Add a filter" tabs (Gene panels / Keywords / LLM); drag-to-add; live N + est-time summary; PASS/region/AF marked server-side. |
| `VariantTable` (client preview) | BUILT | `app/web/components/compare/VariantTable.tsx:83-333` | Sticky header, sort, split-pane, drag-select, save-to-library, copy-for-spreadsheet. Comment notes virtualization is the follow-up for 1000+ rows (`:24-26`). |
| `BatchResultsTable` (server results) | BUILT | `app/web/components/compare/BatchResultsTable.tsx:56-112` | Gene · HGVS · ClinVar · ACMG · gnomAD AF · report link; copy-for-spreadsheet. Renders only when a real job returns rows. |
| `CustomPanelBuilder` (Tier A + Tier B) | MOCK-WIRED | `app/web/components/compare/CustomPanelBuilder.tsx:16-250` | `KeywordPanelBuilder` (type/paste/attach → `resolvePanel`) + `LlmPanelComingSoon` (COMING SOON card). |
| `lib/panels.ts` (API client) | MOCK-WIRED | `app/web/lib/panels.ts:14-62` | `getPanels`/`getPanel`/`resolvePanel` hit `/api/v1/panels*`, fall back to `panels.mock.ts`. |
| `lib/panels.mock.ts` | BUILT (mock data) | `app/web/lib/panels.mock.ts:16-229` | IRD / Cardiac / Hereditary-cancer illustrative panels; deterministic keyword resolver; per-panel badge palette. |
| `lib/batch.ts` (job client) | BUILT | `app/web/lib/batch.ts:13-53` | `createBatch`, `getBatchJob` (paged), `uploadBatch` (multipart → `/batch/uploads`). |
| `uploadBatch` wired into any UI | **MISSING** | grep `uploadBatch`/`upload_ref` in `app/web/components` → 0 hits | The large-VCF upload-ref path exists in the lib but **no component calls it**. Intake is search-bar client-parse only. |
| `lib/compare-filters.ts` | BUILT | `app/web/lib/compare-filters.ts:13-142` | Active-filter model, `applyFilters` (panel = client gene-symbol membership; PASS/region/AF tallied server-side), est-time (`SECONDS_PER_VARIANT = 9`). |
| `lib/variant-file.ts` (parser) | BUILT, **capped at 50** | `app/web/lib/variant-file.ts:18, 69-81` | `MAX_VARIANTS = 50`; VCF takes first ALT only (`:40`); sync in-memory; dedup; sessionStorage stash. |
| `lib/backend.ts` batch/panel contract types | BUILT | `app/web/lib/backend.ts:1763-1916` | Full §8 contract mirrored: `Panel*`, `BatchFilters`, `BatchCreateRequest/Response`, `BatchJob`, `BatchResult`, `BatchPage`, `ParsedVariant` (carries `chrom/pos/ref/alt/filter/info_af/sample_id/genotype`). |
| `lib/plans.ts` (pricing) | BUILT | `app/web/lib/plans.ts:25-70` | free/pro/max; Pro = "VCF upload (batch variants)", Max = "Bulk VCF uploads". **No caps, no current-tier accessor.** |
| Current-user tier accessor (FE) | **MISSING** | grep `getTier`/`currentTier`/`entitlement` in `app/web/lib` → 0 hits | FE cannot read the signed-in user's tier today; tiering UI has no live source. |
| Intake = search bar | BUILT | `app/web/components/landing/EamosSearch.tsx:84-126, 157-166` | Paperclip + drag-drop → `parseVariantFile` → 1 variant routes to `/report`, list stashes → `/compare`. `accept=".vcf,.csv,.tsv,.txt"`. |
| Scope-confirmation gate (N · est · quota/tier) | PARTIAL | `ScopeGate.tsx:170-205` | Shows N + est time. **No quota/tier impact, no explicit confirm, no large-VCF hard cap.** Spec §5.3 only half-built. |
| Tiering / quota / Pro-Max gating UI | **MISSING** | grep `tier`/`quota`/`Pro`/`Max`/`cap_` in `components/compare` → 0 functional hits | Not started. |
| Cohort summaries (§5.5b: class distribution, per-gene, SNV/indel, panel coverage) | **MISSING** | grep `cohort`/`distribution` in `components/compare` → only JSDoc text | Not started. |
| Cohort export (§5.6) | **MISSING** | `app/web/lib/report-export.ts` exists but is **per-report**; no cohort serializer | Not started. |
| Icon system | BUILT | `app/web/components/icons/Icon.tsx:37-150` (IconPin/Remove/Bookmark/FolderMove/DropInto/Rename/ArrowRight/Plus/Check/Sparkle/Chevron); `app/web/components/workbench/ToolIcon.tsx:13` | Reuse these. One ad-hoc Unicode glyph in use: drag handle `⠿` (`ScopeGate.tsx:349`) and split-view `⊟` (`VariantTable.tsx:274`) — pre-existing, flag only. |

### Backend (`app/backend/`) — Codex lane, audited read-only for contract truth

| Item | Status | Evidence | Notes |
| ---- | ------ | -------- | ----- |
| `/api/v1/panels` routes | BUILT | `app/backend/app/api/routes/panels.py:11-29` | list / `{slug}` / resolve, registered `app/backend/app/main.py:172,195`. |
| `/api/v1/batch` routes | BUILT | `app/backend/app/api/routes/batch.py:17-57` | uploads / create / `{job_id}` (paged), registered `main.py:173-196`. |
| `PanelService` | MOCK-WIRED | `app/backend/app/services/panels.py:20-106, 109-184` | 4 **hard-coded** launch panels (IRD/Cardiac/Cancer/Project-100); `source` is `"custom"`, not `"panelapp-au"` (the FE mock says `panelapp-au`). Disease→MONDO is 2 seeded ids only. Warnings explicitly say "external PanelApp/ClinGen/GenCC materialized source pending" (`:15-17`). |
| `BatchService.create_job` | STUB (no real lookup) | `app/backend/app/services/batch.py:79-107, 198-215` | Returns `status="completed"` **synchronously**; `_result_from_variant` echoes parsed fields — `acmg_classification=None`, `predictor_ensemble={}`, ClinVar/HGVS-p scraped from INFO only. **Does NOT call `lookup_service.lookup()`.** No async, no worker pool, no cache, no Supabase persistence (in-memory `dict`). |
| Panel filter = interval intersection | **MISSING** | `batch.py:142-173` | Panel filter matches by **gene symbol only**. A genomic-coordinate VCF row (no gene) is *kept* with a warning, never interval-matched. No MANE→hg38 BED. This is the spec's "correctness floor" (§6.4) and it is absent. |
| `n_after_filters` post-lookup (gnomAD AF) | STUB | `batch.py:94` | Set eagerly to result count at create time; not a real post-lookup AF pass. |
| VCF upload ingest | BUILT (parse only) | `app/backend/app/services/vcf_ingest.py` (exists); `batch.py:60-77` | `store_upload` parses bytes, writes a JSON snapshot to disk. In-memory upload registry; no object storage. |
| Mock VCF generator | PARTIAL / RENAMED | `app/backend/scripts/generate_project_100_mock_vcf.py` exists; spec's `make_test_vcf.py` is **MISSING** | Only the Project-100 stack generator exists; the general `--n/--panel/--mix/--malformed/--with-genotypes` generator (spec §7) is not built. |
| Tests | BUILT | `app/backend/tests/test_batch_api.py`, `test_panels_api.py`, `test_batch_panel_schemas.py` | Contract + API tests exist. |

**Reconciliation — spec vs reality.** Spec/plan claim P1–P3 are the shipping slices; in fact **P3 (panel picker + scope gate + mock job) is shipped**, the **full §8 contract is landed both sides**, and the backend has gone *further* than "schemas only" — but its batch engine is a synchronous stub that does **not** run real lookups, and panel filtering is symbol-only (no interval intersection). So the real gaps are: (1) the **server-side correctness floor** (interval filter + real lookup) — Codex; (2) **large-VCF intake UX** (the `uploadBatch` path is dead in the FE) — Claude; (3) **tiering/quota gate** — both; (4) **cohort summaries + cohort export** — Claude. The FE mock labels IRD/Cardiac as `panelapp-au` while the backend serves them as `source: "custom"` — a visible provenance mismatch to fix when overlay lands.

---

## §1 Problem & goals

A clinician drops a VCF and wants evidence for the variants that matter — not one-at-a-time, and not 5M annotations. A single lookup is ~8–10s, so a serial unfiltered loop over a real VCF is infeasible (spec §2). The product answer is one pipeline: **Drop VCF → scope (panel first) → confirm (N · est · quota) → async job → results dashboard → export.**

**Goals (this design):**
1. **Large-VCF intake** that doesn't ship a 200MB file to the browser — wire the existing `uploadBatch` upload-ref path behind the search-bar/scope surface, with a client-parse vs server-parse threshold.
2. **Panel-filter UX completeness** — the picker, two-layer source provenance (local core + PanelApp AU overlay), and the NL custom-panel builder (Tier A now, Tier B gated).
3. **Pro/Max tiering UI** — a scope gate that shows quota/tier impact, requires confirm, and enforces the large-VCF rule (Pro = filter required; Max = capped whole-VCF).
4. **Results at scale** — virtualized per-variant table + cohort summaries + cohort export, fed by the real (async) engine.

**Non-goals (inherit spec §11):** no read alignment/calling; no per-sample genotype splitting/trio; no SV/CNV; no liftover (refuse hg19 with a clear message); no cross-user panel sharing in v1.

---

## §2 UX / IA / flows

### 2.1 Surface shape (unchanged chrome, reuse `WorkRail`)
Keep the shipped two-pane `WorkRail` layout: **controls LEFT, output RIGHT** (`CompareClient.tsx:160-206`). Intake and tiering slot **into** the existing rail/output — no new top-level route, no new persistent nav.

```
TopNav [ Search / Batch · N variants · source ]            [ Report·Workbench·Batch pill ]
┌── WorkRail (controls, left) ──────┐ ┌── output (right) ───────────────────────────────┐
│ Intake summary (file, N, parse    │ │ idle  → GeneratePrompt (CTA)                     │
│   diagnostics, hg19 refusal)      │ │ run   → progress (done/total, per-variant states)│
│ Scope                             │ │ done  → Tabs: [ Results table ] [ Cohort summary ]│
│   Active scope (chips + N/est)    │ │         + cohort export menu                      │
│   Add a filter (Panels/Kw/LLM)    │ │ empty → EmptyScope (pending server-side note)    │
│ Tier & quota (NEW)                │ │ error → ErrorCard (retry / narrow scope)         │
│ Library (saved variants)          │ │                                                  │
└───────────────────────────────────┘ └──────────────────────────────────────────────────┘
```

### 2.2 Intake flow (the big FE gap)
Two intake sizes, one decision boundary (spec §4 / D-3 — Codex owns the exact threshold; FE proposes ≤ ~5 MB / ≤ ~2k lines client-parse, larger server-parse):

- **Small file (client path, today + raised cap):** search-bar drop → `parseVariantFile` → stash → `/compare`. Raise `MAX_VARIANTS` from 50 to the client cap (e.g. 2k) for this path only.
- **Large file (server path, NEW):** when the dropped file exceeds the threshold, **do not parse in the browser**. Show an **"Upload to scope server-side"** intake card in the rail that calls `uploadBatch(file)` → `{ upload_ref }`, then the job is created with `upload_ref + filters` (not an inline list). Parse diagnostics (lines parsed / skipped / multi-allelic split / deduped) come back from the server on job status.

**Intake states:** `idle` (no file) · `parsing` (client) · `uploading` (server, with %/spinner) · `parsed` (summary: N, diagnostics) · `too-large-unscoped` (Pro: must add a filter — see 2.4) · `refused` (hg19 / unreadable / empty — clear message, spec §11 liftover refusal).

### 2.3 Scope flow (mostly built — complete it)
- Keep the chip model + tabs (`ScopeGate.tsx`). **Add provenance affordance:** each panel chip/menu item shows its source layer (local core vs PanelApp AU) with version on hover (`title` already exists at `ScopeGate.tsx:330` — extend the menu rows similarly).
- **Two-layer source in the picker:** group the preset list under **"Recognised panels (PanelApp AU)"** and **"Core (ClinGen/GenCC)"** with a source tag per row. Until the overlay ships, all rows render from the local core; PanelApp AU rows appear (versioned + provenance link) only when Codex's overlay is live (Task 6 / gated D-1).
- **NL builder:** Tier A (`KeywordPanelBuilder`) stays the default; Tier B (`LlmPanelComingSoon`) stays COMING SOON until chat funded (D-6).

### 2.4 Scope-confirmation gate (PARTIAL → complete) — the guardrail
Add a **"Tier & quota"** rail section + a **confirm step** before a real job runs:
- Show **N after filters · est. time · quota/tier impact** (e.g. "Pro · 1,240 / 5,000 monthly batch variants").
- **Large-VCF rule (D-2):**
  - **Pro:** if `n_to_lookup` > the unfiltered cap and no panel/region/AF filter is active → block GENERATE with an inline nudge: *"Add a gene panel to scope this VCF"* (deep-link the panel tab). This is the product nudge.
  - **Max:** allow capped whole-VCF; if over `cap_M`, show "top-N by quality" notice and proceed.
  - **Free:** batch disabled — show an upsell card ("Batch VCF is a Pro feature") instead of the GENERATE CTA.
- **Confirm:** GENERATE itself is the explicit confirm (already gated, `CompareClient.tsx:168-185`); add a one-line "This will run N lookups (~est)" confirmation above it when N is large.

### 2.5 Results flow (scale it)
- **Tabbed output (done state):** `[ Results table ]` (the existing `BatchResultsTable`, virtualized) and `[ Cohort summary ]` (NEW, §5.5b charts). Default to the table.
- **P/LP pinned to top** of the table (spec §5.5a) — actionable variants first; add a class-filter row.
- **Progress (run state):** replace the indeterminate `LoadingCard` (`CompareClient.tsx:305-325`) with a determinate `done/total` bar + per-variant state counts once the async engine streams progress (poll first, SSE later — §8 ordering).
- **Cohort export:** an export menu on the done state → one TSV (one row/variant) + a summary block (§5.6), reusing the existing copy/serialize patterns.

### 2.6 State matrix
| State | Trigger | UI |
| ----- | ------- | -- |
| Empty | no stash | `EmptyState` "No variants loaded" + Back to search (`CompareClient.tsx:327-364`). |
| Parsing/Uploading | file dropped | rail intake card: spinner + (server) % ; right pane idle. |
| Idle (scoped) | parsed, no run | `GeneratePrompt` CTA; rail shows N/est/quota. |
| Blocked (Pro, large, unscoped) | N>cap, no filter | GENERATE disabled + "Add a panel" nudge. |
| Blocked (Free) | tier=free | Upsell card replacing CTA. |
| Running | GENERATE | determinate progress (done/total + per-variant states). |
| Done (results) | job completed | tabs: Results table (P/LP pinned) + Cohort summary + export. |
| Empty scope | filters exclude all | `EmptyScope` (incl. the "scoped server-side / pending interval match" copy already at `CompareClient.tsx:366-421`). |
| Error | job failed / network | ErrorCard: message + Retry + "narrow scope" hint. |
| Partial/degraded | offline / `mock-` job | client-side `VariantTable` stands in (already handled). |

---

## §3 Visual design

Stay entirely within the Reading-Room system (`DESIGN.md`, `app/web/app/globals.css`). No new fonts; Spectral display, Inter text, `--mono` for variant keys/HGVS only.

- **Tier/quota:** use existing semantic tokens — quota OK = `--teal-tint`/`--teal-deep`; near-limit = `--warn-tint`/`--warn-text`/`--warn-bdr`; over/blocked = `--err`/`--err-tint` or `--danger*`. Server-side filter dot already uses `--warn` (`ScopeGate.tsx:355`); keep that language for "applies when the job runs".
- **Panel source layers:** reuse the categorical badge palette in `panels.mock.ts:126-138` (teal / amber / info / danger-faint) for per-row provenance tags; add a small source-layer label (text, not a new glyph) — "PanelApp AU · v4.2" vs "Core · ClinGen/GenCC".
- **Cohort summary charts:** build from `--bg`/`--line` frames + the **ACMG red→yellow→green ramp** for the classification distribution (`--err` → `--warn` → `--teal-deep`), matching the report's class ramp. SNV substitution spectrum / indel-length use the categorical palette, not new hues. No charting dependency — simple flex/grid bars (the report already does StackedCountBar: `app/web/components/ui/StackedCountBar.tsx`, reuse if it fits).
- **Icons:** reuse `Icon.tsx` set — `IconDropInto` (upload), `IconArrowRight` (open report / generate), `IconSparkle` (NL builder), `IconCheck` (done). For a progress/upload affordance, reuse existing glyphs; **do not invent a new icon system**.
- **New tokens:** **none required.** All states map to existing tokens. (If a determinate progress bar wants a track color, reuse `--bg-soft2` track + `--teal-deep` fill — already used for the split-view divider.)

---

## §4 Component plan

### Extend (existing)
| File | Change |
| ---- | ------ |
| `app/web/lib/variant-file.ts` | Raise `MAX_VARIANTS` for the client path (e.g. 2k); add a size/line threshold helper that returns `{ path: 'client' | 'server' }`; surface parse diagnostics; detect + refuse hg19 (`##reference`/`GRCh37`). |
| `app/web/components/landing/EamosSearch.tsx` | On large file, route to the server-upload intake instead of client-parse (call `uploadBatch`, stash `upload_ref` + source instead of a variant list). |
| `app/web/lib/variant-file.ts` (stash) | `CompareStash` gains an optional `upload_ref` + diagnostics so `/compare` knows it's a server-parse cohort. |
| `app/web/components/compare/CompareClient.tsx` | Branch on stash kind (inline vs `upload_ref`); add tabbed output (Results / Cohort summary); determinate progress; error state. |
| `app/web/components/compare/ScopeGate.tsx` | Group preset list by source layer; add per-row source/version provenance; deep-linkable panel tab for the Pro nudge. |
| `app/web/components/compare/BatchResultsTable.tsx` | Virtualize rows (1000+); pin P/LP to top; add class-filter + post-lookup AF filter; wire cohort export. |
| `app/web/lib/compare-filters.ts` | No structural change; ensure server-side filters feed the tier/quota count (`n_to_lookup`). |

### New (proposed paths)
| File | Purpose |
| ---- | ------- |
| `app/web/components/compare/BatchIntakeCard.tsx` | Rail card for the large-VCF server-upload path: drop/attach, `uploadBatch`, % progress, parse-diagnostics summary, hg19 refusal. |
| `app/web/components/compare/TierQuotaGate.tsx` | Rail section: tier badge, quota usage, large-VCF rule enforcement (Pro nudge / Max cap notice / Free upsell), confirm line. |
| `app/web/components/compare/CohortSummary.tsx` | §5.5b: classification distribution (ACMG ramp), per-gene counts, SNV/indel + substitution spectrum, panel coverage. |
| `app/web/lib/cohort-export.ts` | §5.6: one TSV (row/variant) + summary block, reusing report-tsv/report-export serializers. |
| `app/web/lib/entitlement.ts` | FE accessor for the current user's tier + batch caps (reads whatever Codex exposes — see §5). Until live, returns a dev/default tier. |

---

## §5 Backend deps (Codex lane)

Everything here is a Codex deliverable; the FE designs against the §8 contract + mocks and degrades offline.

1. **Real batch engine (the headline).** `BatchService.create_job` must call `lookup_service.lookup()` per unique variant (in-process, below `RATE_LIMIT_LOOKUP`), async with a bounded worker pool, dedup + per-variant-key cache, and populate `acmg_classification`, `predictor_ensemble`, real `clinvar_verdict`/`gnomad_af`. Today it echoes parsed fields (`batch.py:198-215`). Until then the FE shows summary-level placeholders.
2. **Panel interval-intersection filter (correctness floor).** Resolve panel symbols → MANE Select GFF3 → hg38 BED and intersect against each VCF row's `CHROM:POS`. Today the filter is gene-symbol-only (`batch.py:142-173`), so coordinate-only VCF rows are never panel-filtered server-side. This is the *enabling mechanism* for large-VCF and is currently absent.
3. **Real panel catalogue + two-layer source.** Materialize local ClinGen/GenCC/MONDO/HGNC (Layer 1) and the PanelApp AU overlay (Layer 2, versioned + provenance). Today panels are 4 hard-coded lists with `source:"custom"` (`panels.py:109-184`); the FE expects `panelapp-au`/`clingen-gencc` provenance. Includes real `disease_mondo` → genes resolution (currently 2 seeded ids, `panels.py:74-93`).
4. **Async progress + persistence.** Real `done/total` + per-variant states over polling (then SSE per §8 ordering); results persisted to Supabase keyed to the user so they survive reload and land in account history (today in-memory `dict`, `batch.py:57-58`).
5. **`n_after_filters` post-lookup AF pass.** Compute the final count after gnomAD-AF filtering at completion (today set eagerly, `batch.py:94`).
6. **Large-VCF upload storage.** `POST /batch/uploads` → object storage (not in-memory/disk-snapshot), server-side parse + filter; the FE only ever holds the `upload_ref`. (D-3 threshold + D-7 asset registry.)
7. **Tier/quota source for the FE.** An endpoint (or session claim) exposing the signed-in user's tier + batch caps (`cap_P`, `cap_M`) so `TierQuotaGate` enforces real limits, and **job-submission-scoped** rate limits distinct from `RATE_LIMIT_LOOKUP`. No FE tier accessor exists today.
8. **General mock VCF generator** (`make_test_vcf.py`, spec §7) for FE parser/edge-case fixtures — only the Project-100 generator exists.

---

## §6 Gated items (need Steven's explicit OK before shipping — recommendations are not authorization)

1. **⚠ GATED — needs Steven OK: large-VCF server-upload intake as a durable nav/flow change.** Wiring `uploadBatch` introduces a new intake mode (upload-to-server) distinct from the current client-parse-only drop. It changes what "drop a file" does for big files. Durable UX change → confirm before building.
2. **⚠ GATED — needs Steven OK: Pro/Max/Free tiering UI that gates GENERATE.** Blocking a real action behind tier (Free upsell, Pro filter-required nudge) is a durable, revenue-facing behavior. Needs Steven's sign-off on the exact gate behavior and the cap numbers (D-2 still parametric: `cap_P`, `cap_M`).
3. **⚠ GATED — needs Steven OK: PanelApp AU overlay surfacing.** Showing "PanelApp Australia · v4.2" named panels with provenance is a durable, legally-sensitive surface (D-1: ToU + OMIM carve-out unconfirmed; MONDO only). The FE currently *mislabels* mock panels as `panelapp-au` — do not ship real PanelApp-branded panels until legal confirms and Codex serves them with attribution.

Secondary (smaller, but durable): tabbed output (Results / Cohort summary) replacing the single output pane, and the Free-tier upsell card, both alter the shipped `/compare` layout — fold into items 1–2 for one approval.

---

## §7 Open questions for Steven

1. **Caps (D-2, still parametric):** what are `cap_P` (Pro variants/VCF before a filter is required) and `cap_M` (Max whole-VCF cap)? The gate UX needs concrete numbers to show quota.
2. **Client/server parse threshold (D-3, Codex's call but affects FE copy):** confirm the ~5 MB / ~2k-line boundary so the intake card messaging is accurate.
3. **NL panel builder Tier B (D-6):** go/no-go on funding the AskEamos key for the bounded panel-builder use case? Tier A ships regardless; Tier B stays COMING SOON until then.
4. **PanelApp AU launch (D-1):** is legal/ToU confirmation in hand, and what is the exact launch panel set (IRD + cardiac + ?)? Until confirmed, the picker shows local-core panels only and drops the `panelapp-au` label from the mocks.
5. **Free-tier batch:** confirm Free = no batch (pricing copy implies it) — so the surface shows an upsell rather than a runnable gate for Free users.
6. **Multi-sample VCFs (D-5):** confirm v1 treats one VCF = one specimen (ignore per-sample GT) — affects parse diagnostics + the intake summary copy.
