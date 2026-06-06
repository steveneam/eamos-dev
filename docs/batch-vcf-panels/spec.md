# Batch VCF + Gene Panels — Implementation Spec (Frontend)

> Surface: nav label **"Batch"** → route **`/compare`** (route name unchanged; there is **no** `/batch` Next page route — `/batch*` strings are the `/api/v1/batch` API).
> App: Next.js 16 at `app/web/` (active frontend). `app/frontend/` is the legacy Vite reference; `/runs` is frozen v1.
> Source of truth for the gap: `docs/batch-vcf-panels/design.md` (§0 audit verified by the orchestrator 2026-06-06) + `plans/batch-vcf-and-panels/{spec,plan}.md`.
> This doc is the **buildable** layer below the design: exact files, line anchors, types, behaviour, invariants, tests, Codex deps, and gated decisions. Authored 2026-06-06. **Edits no code — review gate before implementation.**
> Design system: `DESIGN.md` + `app/web/app/globals.css`. Icons: `app/web/components/icons/Icon.tsx` + `workbench/ToolIcon.tsx` only — no new icon system.

---

## §0 Scope & non-goals

### In scope (FE, this spec)
1. **Large-VCF intake** — wire the existing-but-dead `uploadBatch` (`app/web/lib/batch.ts:45-53`) into a real intake path with a client-parse vs server-parse threshold; raise the 50-variant client cap for the small path only.
2. **Panel-filter UX completeness** — two-layer source provenance in the picker; per-chip source/version affordance; the NL custom-panel builder (Tier A live, Tier B gated) reusing `CustomPanelBuilder`.
3. **Pro/Max/Free tiering gate UI** — a rail "Tier & quota" section + a confirm step that enforces the large-VCF rule (Pro filter-required, Max capped, Free upsell), reading an FE tier accessor that degrades to a dev default until Codex exposes the real source.
4. **At-scale results** — virtualize `BatchResultsTable` (1000+ rows), pin P/LP, add a class filter + post-lookup AF filter, a determinate progress state, an error state, and a cohort summary tab + cohort export.

### Non-goals (inherit plans/spec §11)
- No read alignment / variant calling (Eamos ingests CALLED variants; DWGSIM-class tools out of scope).
- No per-sample genotype splitting / trio analysis (one VCF = one specimen in v1; D-5).
- No SV/CNV (SNV + small indel only).
- No liftover — hg19 is **refused** with a clear message, not converted.
- No cross-user panel sharing (save/clone only — and save itself is a Codex/Supabase dep, §6).
- **No backend work.** This spec touches only `app/web/**` + this doc. `BatchService`, the interval filter, the real catalogue, the tier source = Codex lane (§6).

---

## §1 Contracts & types

### 1.1 Existing contract to reuse (already landed both sides — do not redefine)
All batch/panel types live in `app/web/lib/backend.ts:1762-1916`, mirroring `app/backend/app/schemas/{panels,batch}.py`, canaried by `app/backend/tests/test_frontend_contract.py`. Reuse verbatim:

| Type | Anchor | Used for |
| ---- | ------ | -------- |
| `PanelSource` / `PanelConfidence` / `PanelValidity` / `PanelMinimumValidity` | `backend.ts:1768-1779` | panel provenance + builder validity dropdown |
| `PanelGene` / `PanelSummary` / `Panel` | `backend.ts:1781-1815` | picker rows + resolved gene lists |
| `PanelResolveRequest` | `backend.ts:1821-1826` (`disease_mondo` / `symbols` / `upload_ref` / `min_validity`) | NL/keyword builder |
| `ParsedVariant` (backend shape) | `backend.ts:1838-1853` (carries `chrom/pos/ref/alt/filter/info_af/sample_id/genotype`) | server-parse cohort rows |
| `BatchFilters` | `backend.ts:1855-1860` | scope → job payload (already mapped, `CompareClient.tsx:36-46`) |
| `BatchUploadResponse` `{ upload_ref }` | `backend.ts:1862-1864` | large-VCF upload negotiation |
| `BatchCreateRequest` (`variants?` \| `upload_ref?` + `filters?`) | `backend.ts:1866-1870` | both intake paths |
| `BatchCreateResponse` (`job_id/n_input/n_to_lookup/est_seconds`) | `backend.ts:1872-1877` | scope-gate counts |
| `BatchJob` (`status/done/total/results/page/n_after_filters?`) | `backend.ts:1904-1916` | poll + progress + final count |
| `BatchResult` (`variant_key/state/gene/hgvs_c/hgvs_p/clinvar_verdict/gnomad_af/predictor_ensemble/acmg_classification/report_href`) | `backend.ts:1890-1902` | results table rows |
| `BatchVariantState` (7-state enum) | `backend.ts:1829-1836` | per-variant progress counts |

**Contract is sufficient for everything in this spec.** The progress UI uses `BatchJob.done/total` (already present) and the per-state counts derivable from `results[].state`. No contract change is requested of Codex for the FE build (one optional addition flagged in §6.7).

### 1.2 New FE-only types (additive, no backend mirror)
Local to `app/web/lib/`; never sent over the wire except where they map to existing contract fields.

```ts
// lib/entitlement.ts (NEW) — FE accessor for tier + caps. NO backend source exists today
// (verified: useAuth() exposes only id/email — AuthProvider.tsx:18-21). Until Codex lands §6.7,
// this returns a dev default and reads an optional override so the gate is buildable + testable.
export type Tier = 'free' | 'pro' | 'max'        // reuse PlanId shape from lib/plans.ts:7
export interface BatchEntitlement {
  tier: Tier
  cap_unfiltered: number | null   // Pro: max N before a filter is REQUIRED. null = no cap (Max/enterprise)
  cap_total: number | null        // Max: hard whole-VCF cap; top-N-by-quality over this. null = unlimited
  used_this_period: number | null // monthly batch-variant usage; null until Codex exposes it
  quota_period: number | null     // monthly batch-variant allowance; null until exposed
  source: 'dev-default' | 'live'  // provenance flag so the UI can show "estimated" copy when dev-default
}

// lib/variant-file.ts (EXTENDED) — intake routing decision + diagnostics
export type IntakePath = 'client' | 'server'
export interface IntakeDecision { path: IntakePath; sizeBytes: number; lineCount: number; reason: string }
export interface ParseDiagnostics {        // small-path (client) diagnostics, surfaced in the intake summary
  linesTotal: number
  parsed: number
  skipped: number          // headers / malformed / comment lines
  multiAllelicSplit: number
  deduped: number
  refused?: 'hg19' | 'unreadable' | 'empty'
}
```

`CompareStash` (currently `app/web/lib/variant-file.ts:86-90`) gains an optional server-parse arm. Keep it a discriminated shape so `CompareClient` branches cleanly:

```ts
export interface CompareStash {
  savedAt: number
  source: string
  variants: ParsedVariant[]            // CLIENT path (existing) — empty for server path
  uploadRef?: string                   // SERVER path — from uploadBatch(); variants stays []
  diagnostics?: ParseDiagnostics       // client path only (server diagnostics come back on BatchJob.warnings)
}
```

> Note the **two `ParsedVariant`s**: the FE parser's narrow shape (`lib/variant-file.ts:9-16`, `raw/gene/variant/query`) and the contract shape (`backend.ts:1838-1853`). `CompareClient.toBatchVariant` (`CompareClient.tsx:31-33`) already bridges them — keep that bridge; the server path bypasses it entirely (sends `upload_ref`, no `variants`).

---

## §2 Component / file plan

### 2.1 EDIT (existing files, with current anchors)

| File | Current anchor | Change |
| ---- | -------------- | ------ |
| `app/web/lib/variant-file.ts` | `MAX_VARIANTS = 50` (`:18`); `parseVariantFile` (`:69-81`); `CompareStash` (`:86-90`); `stashCompareVariants` (`:92-100`) | Raise client cap to `CLIENT_MAX = 2000` (small path only; gated D-3). Add `decideIntake(file): IntakeDecision` (size/line threshold). Add hg19 refusal in `isVcf`/`parseVcf` (detect `##reference=.*GRCh37`/`hg19`/`b37` or `##contig=...assembly=GRCh37`). Return `ParseDiagnostics` from a new `parseVariantFileWithDiagnostics`. Extend `CompareStash` (+ `uploadRef`/`diagnostics`); `stashCompareVariants` gains an overload/options arg for the server arm. **Keep `parseVariantFile` signature intact** (still used by tests + EamosSearch single-variant path). |
| `app/web/components/landing/EamosSearch.tsx` | `handleFiles` (`:97-115`); `routeVariants` (`:84-95`); `accept=".vcf,.csv,..."` (`:160`) | In `handleFiles`, call `decideIntake` per file. `client` → existing parse+stash. `server` → `await uploadBatch(file)` → `stashCompareVariants([], source, { uploadRef })` → `router.push('/compare')`. Show an inline uploading affordance during the await (the search bar already tracks `dragActive`; add an `uploading` flag). **GATED — see §7.1** (changes what "drop a big file" does). |
| `app/web/components/compare/CompareClient.tsx` | `RunStatus` (`:28`); `runBatch` (`:88-127`); output switch (`:163-201`); `LoadingCard` (`:305-325`) | Branch on `stash.uploadRef`: server cohort submits `{ upload_ref, filters }` (no inline `variants`); the client-side `VariantTable` preview is **not available** for server cohorts (no rows in browser) — show an "uploaded, scope server-side" idle card instead. Add `RunStatus` member `'error'`. Replace single output with a 2-tab output (`Results` / `Cohort summary`) once `status==='done'` and real results exist. Swap `LoadingCard` for a determinate `<BatchProgress job={...}/>` fed by the poll loop. Mount `<TierQuotaGate/>` in the rail (between `ScopeGate` and `LibrarySection`, `:204-205`). |
| `app/web/components/compare/ScopeGate.tsx` | `PresetList` (`:248-309`); `FilterChip` `title` (`:330`); tab set (`:229-242`) | Group `PresetList` panel rows by source layer: a `MenuLabel` "Recognised panels" for `source==='panelapp-au'` and "Core (ClinGen/GenCC)" for `source==='clingen-gencc'`. Add a per-row source/version tag (text, via `PANEL_SOURCE_LABEL` `panels.mock.ts:109-114` + `p.version`). Accept an optional `focusTab` prop so the Pro nudge can deep-link the panel tab (`setTab('panels')`). No structural rail change. |
| `app/web/components/compare/BatchResultsTable.tsx` | whole file (`:56-112`); `copyPayload` (`:40-54`); `verdictColor` (`:16-22`) | Virtualize the `<tbody>` (windowing) for 1000+ rows. Sort P/LP to top (stable; keep input order within a class). Add a class-filter row (chips: All / P / LP / VUS / LB / B, derived from `acmg_classification`) + a post-lookup AF `≤` input that filters client-side over loaded rows. Wire a cohort-export menu (calls `lib/cohort-export.ts`). Keep `copyPayload`/`CopyButton` intact. |
| `app/web/lib/compare-filters.ts` | `applyFilters` (`:82-121`); `SECONDS_PER_VARIANT = 9` (`:55`) | No structural change. Ensure the `FilterResult` count consumed by `TierQuotaGate` is `n_to_lookup` semantics (client path: `shown.length + intervalPending` when a panel is active, since coordinate rows are pending-not-excluded — they still count toward lookups). Add a small `nToLookup(res)` helper rather than mutating `applyFilters`. |

### 2.2 CREATE (new files, proposed paths)

| File | Purpose | Key reuse |
| ---- | ------- | --------- |
| `app/web/lib/entitlement.ts` | `useEntitlement(): BatchEntitlement` hook. Dev-default `{ tier:'pro', cap_unfiltered: CAP_P, cap_total: CAP_M, source:'dev-default' }`; reads a `localStorage`/env override for dev/testing; swaps to a live fetch when §6.7 lands. Constants `CAP_P`/`CAP_M` live here as named placeholders pending D-2. | `lib/plans.ts:7` `PlanId`; `useAuth` (`AuthProvider.tsx:170`) for sign-in state. |
| `app/web/components/compare/BatchIntakeCard.tsx` | Rail card for the **server** intake arm: shows the uploaded filename + `upload_ref`, server-parse status, parse diagnostics (from `BatchJob.warnings`), and a "Replace file" affordance. For the client arm, shows the `ParseDiagnostics` summary (parsed/skipped/multi-allelic/deduped) + hg19 refusal banner. | `IconDropInto`/`IconCheck`/`IconArrowRight` (`Icon.tsx`); `WorkRailSection` (`WorkRail.tsx:71`). |
| `app/web/components/compare/TierQuotaGate.tsx` | Rail section: tier badge, quota usage bar, and the large-VCF rule enforcement. Emits a `canGenerate: boolean` + `blockReason` the `GeneratePrompt`/`Regenerate` button reads. Pro filter-required nudge (deep-links `ScopeGate` panel tab); Max over-cap "top-N by quality" notice; Free upsell card (replaces the CTA, links `/pricing`). | `useEntitlement`; `WorkRailSection`; quota tokens (§3); `IconArrowRight`. |
| `app/web/components/compare/CohortSummary.tsx` | Done-state second tab: classification distribution (reuse `StackedCountBar`), per-gene counts, SNV/indel split + 6-class substitution spectrum, panel coverage (genes hit vs none). Pure derive from `BatchResult[]` + the active `Panel`. | `StackedCountBar` (`ui/StackedCountBar.tsx`); categorical palette from `panels.mock.ts:126-131`; ACMG ramp tokens. |
| `app/web/lib/cohort-export.ts` | `cohortTsv(results): {text}` (one row/variant) + `cohortSummaryBlock(results, panel)` text. One download action. | mirror `BatchResultsTable.copyPayload` (`:40-54`) serializer shape; `report-export.ts` patterns (per-report, do not modify). |
| `app/web/components/compare/BatchProgress.tsx` | Determinate `done/total` bar + per-`BatchVariantState` counts (queued / running / completed / filtered_post_lookup / failed). Falls back to indeterminate copy when `total===0` (mock/instant path). | `BatchVariantState` (`backend.ts:1829-1836`); progress-track tokens (§3); the existing `Spinner` idiom (`CompareClient.tsx:242-259`). |

### 2.3 Component tree (done state, after edits)
```
CompareClient
├─ TopNav / NavContext (unchanged — "Batch · N variants")
└─ WorkRail surface="compare"
   ├─ (rail) BatchIntakeCard      ← NEW (client diagnostics OR server upload_ref)
   ├─ (rail) ScopeGate            ← EDITED (source-grouped picker, focusTab)
   ├─ (rail) TierQuotaGate        ← NEW (gate → canGenerate/blockReason)
   ├─ (rail) LibrarySection       (unchanged)
   └─ (output)
      ├─ idle    → GeneratePrompt | Free upsell | Pro nudge (from TierQuotaGate)
      ├─ running → BatchProgress   ← NEW (replaces LoadingCard)
      ├─ error   → ErrorCard       ← NEW
      └─ done    → Tabs[ BatchResultsTable | CohortSummary ] + export  ← EDITED + NEW
```

---

## §3 Behaviour spec

### 3.1 Large-VCF intake card (`BatchIntakeCard` + `variant-file.ts` + `EamosSearch`)

**Threshold (`decideIntake`)** — FE proposal, D-3 is Codex's call; keep the numbers in one named constant so a one-line change re-tunes them:
- `path: 'client'` when `sizeBytes ≤ 5 MB` **and** `lineCount ≤ CLIENT_MAX (2000)`.
- `path: 'server'` otherwise.
- `lineCount` cheaply estimated for huge files (sample first N KB, extrapolate) — never read a 200 MB file fully to count lines; `File.size` is the primary gate.

**Client arm (existing + raised cap):**
- `parseVariantFileWithDiagnostics` returns rows (cap `CLIENT_MAX`) + `ParseDiagnostics`.
- Intake card shows: filename · N parsed · "X skipped · Y multi-allelic (first ALT) · Z deduped". The first-ALT behaviour is unchanged (`variant-file.ts:38-40`) — surface it honestly in the diagnostic line so users know multi-allelic sites were collapsed.
- If `parsed > CLIENT_MAX`, show "Showing first 2,000 — upload the file to scope the rest server-side" with a one-click promote-to-server action (re-runs `uploadBatch` on the original file).

**Server arm (NEW, the dead-path revival):**
- On drop of a large file, `EamosSearch.handleFiles` calls `uploadBatch(file)` (`batch.ts:45-53`). While awaiting: search bar shows an `uploading` state (spinner + "Uploading VCF…"); on resolve, stash `{ variants: [], uploadRef, source }` and route to `/compare`.
- `/compare` with a `uploadRef` stash: `BatchIntakeCard` shows "Uploaded · scope server-side"; the **client preview (`VariantTable`) is suppressed** — there are no browser rows. Idle output is a card: "This VCF is scoped on the server. Add a panel, then Generate." Diagnostics arrive on `BatchJob.warnings` after submit.
- `uploadBatch` failure (offline / no backend): catch → fall back to client parse if `≤ CLIENT_MAX*2` lines is feasible, else show a `refused`-style "Server upload unavailable — try a smaller file or retry" message. Do **not** silently route to an empty `/compare`.

**Refusal states (`ParseDiagnostics.refused`):**
- `hg19` — header indicates GRCh37/hg19/b37 → block both paths. Card: "This VCF looks like GRCh37/hg19. Eamos is hg38-only and does not lift over coordinates. Re-call against GRCh38 and re-upload." (plans/spec §11 liftover refusal.)
- `unreadable` / `empty` — clear single-line message + Back to search.

**a11y:** intake card is a `<section>` with an `aria-live="polite"` status line for upload %/parse result; refusal banner uses `role="alert"`. Upload spinner `aria-hidden` with text label beside it.

### 3.2 Panel-filter UX (`ScopeGate` + `CustomPanelBuilder`, mostly built — complete)

**Selection (unchanged):** click or drag a panel row → chip in Active scope; live N + est recompute (`ScopeGate.tsx:182-205`); remove via chip ✕. Keep all of it.

**Two-layer source provenance (NEW affordance, GATED §7.3 for real PanelApp branding):**
- Group `PresetList` (`ScopeGate.tsx:248-309`) under two `MenuLabel`s by `PanelSummary.source`: **"Recognised panels"** (`panelapp-au`) and **"Core · ClinGen/GenCC"** (`clingen-gencc`). Custom/user panels (`custom`) get a third group when saved panels land (§6 dep).
- Each row gains a source/version tag: `${PANEL_SOURCE_LABEL[p.source]} · ${p.version}` (text, muted mono — no new glyph). `FilterChip` already shows this on `title` hover (`ScopeGate.tsx:330`); make it visible inline on menu rows.
- **Provenance honesty:** the mock currently labels IRD/Cardiac `panelapp-au` (`panels.mock.ts:20,46`) while the backend serves `source:"custom"` (design §0). Until Codex's overlay (§6.3) serves real attribution, the picker must render whatever `source` the **live** catalogue returns (`getPanels`, `panels.ts:14-24`) — so when offline it shows the mock's `panelapp-au`, but against the live backend it shows `custom` truthfully. Do **not** hard-code "PanelApp Australia" labels independent of the data.

**NL custom-panel builder (reuse `CustomPanelBuilder`, no rewrite):**
- **Tier A — `KeywordPanelBuilder`** (`CustomPanelBuilder.tsx:16-212`) stays the `keywords` tab default. It already does type/paste/attach → `resolvePanel({ symbols })` → draft → "Add as filter" (`:27-51`). Keep as-is. Optional: add the `min_validity` dropdown (definitive/strong — `PanelMinimumValidity`, `backend.ts:1779`) to the builder and pass it through `resolvePanel` (the field already exists in `PanelResolveRequest`, `backend.ts:1825`).
- **Tier B — `LlmPanelComingSoon`** (`CustomPanelBuilder.tsx:214-250`) stays the `llm` tab, COMING SOON. **Do not wire** — gated on AskEamos funding (D-6, memory `feedback_askeamos_parked`). No change.

**a11y:** picker rows are already `<button>`s with text; add the source tag inside the existing label so it's read. Tab set already `role="tablist"` (`ScopeGate.tsx:229`).

### 3.3 Pro/Max/Free tiering gate (`TierQuotaGate` + `entitlement.ts`) — GATED §7.2

`useEntitlement()` returns `{ tier, cap_unfiltered, cap_total, used_this_period, quota_period, source }`. `n_to_lookup` comes from `compare-filters.nToLookup(res)`. Behaviour by tier:

| Tier | When | UI | Generate |
| ---- | ---- | -- | -------- |
| **Free** | always | Upsell card replaces the CTA: "Batch VCF is a Pro feature" + "See plans →" (`/pricing`). | **blocked** |
| **Pro** | `n_to_lookup ≤ cap_unfiltered` OR a panel/region/AF filter is active | Quota line: "Pro · {used}/{quota} this month · running N (~est)". | **allowed** (explicit confirm line when N large) |
| **Pro** | `n_to_lookup > cap_unfiltered` AND no filter active | Inline nudge: "Add a gene panel to scope this VCF" + button → `ScopeGate` panel tab (`focusTab='panels'`). | **blocked** until a filter is added |
| **Max** | `n_to_lookup ≤ cap_total` | Quota line as Pro. | **allowed** |
| **Max** | `n_to_lookup > cap_total` | Notice: "Over the {cap_total} cap — running top-{cap_total} by quality." | **allowed** (capped) |

- **Confirm line:** when `n_to_lookup` ≥ a "large" threshold (e.g. 200), show above Generate: "This will run {N} lookups (~{est}). Generate to start." Generate itself remains the explicit confirm (already gated, `CompareClient.tsx:168-185`).
- **Quota source:** when `entitlement.source === 'dev-default'` or `used_this_period == null`, show the tier + caps but render usage as "—" with an "(estimated)" tag — never show a fake usage number. Real numbers arrive with §6.7.
- **`canGenerate`/`blockReason`** flow up to `CompareClient` so the Generate/Regenerate button (`CompareClient.tsx:170-184`) is `disabled` with the right reason; the idle `GeneratePrompt` (`:280-303`) is replaced by the upsell/nudge card when blocked.

**Edge cases:** signed-out user (`useAuth().user == null`) → treat as Free (upsell + "Sign in to run batch"). `configured===false` (no Supabase env, `AuthProvider.tsx:30`) → dev-default tier so local dev is never blocked.

**a11y:** quota bar `role="img"` + `aria-label` (mirror `StackedCountBar`); block reason as `aria-describedby` on the disabled Generate button so screen readers get the reason.

### 3.4 At-scale results (`BatchResultsTable` + `CohortSummary` + `BatchProgress`)

**Results table (EDIT `BatchResultsTable`):**
- **Virtualize** the body for 1000+ rows (windowed render; keep the sticky `<thead>` `:114-136` and the `maxHeight:560` scroll container `:68`). Row height is fixed → simple windowing, no measurement needed.
- **Pin P/LP to top:** stable sort by ACMG class rank (P, LP first; then VUS, LB, B; then null), preserving input order within a class. `verdictColor` (`:16-22`) already maps the colours.
- **Class filter row:** chips All / P / LP / VUS / LB / B over `acmg_classification`; counts per chip. Filters the rendered set.
- **Post-lookup AF filter:** an `AF ≤` input (default off) filtering loaded rows by `gnomad_af` — this is the post-lookup AF pass the contract defers (`n_after_filters`, `backend.ts:1909`); client-side over loaded rows is honest because the server may not have applied it.
- **Export menu:** "Export cohort (TSV)" → `cohort-export.cohortTsv` download + copy. Keep the existing `CopyButton` (`:65`).

**Cohort summary (NEW `CohortSummary`):**
- **Classification distribution** — `StackedCountBar` (`ui/StackedCountBar.tsx`) keyed P/LP/VUS/LB/B; the headline.
- **Per-gene counts** — bar list (genes hit, count desc) using `--bg`/`--line` frames + categorical palette.
- **SNV/indel + 6-class substitution spectrum** — derived from `variant_key` (`CHROM-POS-REF-ALT`); REF/ALT length → SNV vs indel; SNV → one of 6 substitution classes. Categorical palette, no new hues.
- **Panel coverage** — for the active `Panel.genes`, which had ≥1 variant vs none (covered/uncovered counts + uncovered gene list). Pure derive; no backend call.
- All charts are flex/grid bars — **no charting dependency** (DESIGN.md: no new deps without cause).

**Progress (NEW `BatchProgress`):**
- Determinate bar `done/total` (`BatchJob.done/total`, `backend.ts:1911-1912`) + per-state counts from `results[].state` (`BatchVariantState`).
- Poll-first (the existing loop, `CompareClient.tsx:99-118`, already polls `getBatchJob`); SSE is a later Codex add (§6.4, plans/spec §8 ordering) — design the component to consume a `BatchJob` snapshot so swapping poll→SSE is a data-source change only.
- `total===0` (instant in-memory / mock path) → indeterminate "Running…" copy (current `LoadingCard` text, `:319-322`).

**Error state (NEW `ErrorCard`):**
- `status==='error'` (job `status==='failed'` or a non-mock network throw that isn't the offline-mock fallback) → message + Retry (`runBatch(filters)`) + "narrow scope" hint linking the panel tab. The current `runBatch` swallows all errors into the mock fallback (`:121-123`); split real `failed` jobs out so they surface as errors instead of a silent empty done.

**a11y:** progress bar `role="progressbar"` + `aria-valuenow/min/max`; results table keeps `<th scope="col">` (`:117`); class-filter chips are `aria-pressed` toggle buttons; tab switch is a `role="tablist"`.

---

## §4 Invariants (must not break)

1. **`/compare` route name unchanged.** Nav label is "Batch" (`CompareClient.tsx:222`); the route stays `/compare`. No `app/web/app/batch/**` is created.
2. **Existing scope chips work unchanged** — add/remove/reorder/drag-to-add, live N + est (`ScopeGate.tsx:73-91, 152-205`). Source grouping is additive; the chip model and `applyFilters` semantics are untouched.
3. **Save-to-library / select / sort in the client `VariantTable`** (`VariantTable.tsx`) keep working for the client-parse path. Server-parse cohorts simply don't render `VariantTable` (no browser rows) — they never silently break it.
4. **Mock-first / offline degradation preserved.** `createBatch`/`getBatchJob`/`getPanels`/`resolvePanel` all fall back to mocks (`batch.ts:21-31`, `panels.ts:19-24,30-33,43-61`). New code must keep this: `uploadBatch` failure has a defined fallback (§3.1); `useEntitlement` returns dev-default offline.
5. **Contract parity.** No edit to `backend.ts:1762-1916` types; `test_frontend_contract.py` stays green. New types are FE-only (`entitlement.ts`, `IntakeDecision`, `ParseDiagnostics`).
6. **`parseVariantFile` signature preserved** — EamosSearch single-variant routing (`EamosSearch.tsx:86-92`) and any unit tests still call it. New diagnostics is a sibling function.
7. **No new icon system, no new font, no new color token** (design §3: all states map to existing tokens). Pre-existing ad-hoc glyphs (`⠿` `ScopeGate.tsx:349`, `⊟` `VariantTable.tsx:274`) are left as-is (out of scope).
8. **Reading-Room design system only** — Spectral display / Inter text / `--mono` for variant keys + HGVS (`DESIGN.md`, `globals.css`).

---

## §5 Test plan

| Gate | How | Pass |
| ---- | --- | ---- |
| **tsc** | `npm --prefix app/web run typecheck` (or `tsc --noEmit`) | 0 errors. New types resolve; `BatchStash` discriminant narrows. |
| **lint** | `npm --prefix app/web run lint` (`eslint-config-next@16`) | 0 errors, 0 new warnings. |
| **unit (Vitest, if present in app/web)** | `variant-file`: `decideIntake` thresholds; hg19 refusal detection; diagnostics counts (skip/multi-allelic/dedup); `CLIENT_MAX` cap. `compare-filters.nToLookup`. `cohort-export.cohortTsv`. `entitlement` dev-default + override. `CohortSummary` derive (substitution class, panel coverage). | All pass. |
| **browser (skill `browser-verify` on :3000)** | (a) drop small VCF → client diagnostics card; (b) simulated large file → server upload card + suppressed VariantTable; (c) hg19 VCF → refusal; (d) panel select → source-grouped picker + provenance tag; (e) Free tier → upsell; Pro over-cap unscoped → nudge → add panel → unblock; Max over-cap → top-N notice; (f) done → tabs, P/LP pinned, class filter, AF filter, cohort summary charts, export download; (g) error job → ErrorCard + retry. | Each state renders correctly; offline falls back to mocks. |
| **contract** | `cd app/backend && python -m pytest tests/test_frontend_contract.py` (read-only confirmation FE didn't drift the mirror) | Green (unchanged). |
| **a11y spot** | keyboard tab through rail → output; screen-reader labels on progress/quota/class-filter; refusal `role="alert"`. | No blocking issues. |

> Run `npm --prefix app/web ...` (memory: never `cd`; absolute/`--prefix`). Do not start a `:3000` dev server that conflicts with Codex's — use `browser-verify` against the existing instance or a Claude-owned port, and kill any server started before `/clear` (memory `feedback_background_process_cleanup`).

---

## §6 Backend deps (Codex lane — FE must NOT build these; flag, mock against contract)

Each is a hard blocker for the *live* version of an FE feature; the FE ships mock-first against the §1 contract and degrades offline.

1. **Real async batch engine.** `BatchService.create_job` is a synchronous stub that echoes parsed fields and never calls `lookup_service.lookup()` (`app/backend/app/services/batch.py:79-107, 198-215`). FE-facing impact: `BatchResult.acmg_classification/predictor_ensemble/clinvar_verdict/gnomad_af` are placeholder until this lands → `BatchResultsTable`/`CohortSummary` show real data only against the real engine. **Contract is already correct** (`BatchResult`, `backend.ts:1890-1902`); no shape change needed.
2. **Panel interval-intersection filter (correctness floor).** Panel filter is gene-symbol-only (`batch.py:142-173`); coordinate-only VCF rows are kept-with-warning, never interval-matched. FE already designs for this: `intervalPending` + the "scoped server-side" copy (`compare-filters.ts:69-72`, `CompareClient.tsx:386-401`). Until MANE→hg38 BED intersection lands, server-parse panel filtering is incomplete. FE shows pending-not-excluded; no FE change when it lands.
3. **Real two-layer panel catalogue.** Backend serves 4 hard-coded panels with `source:"custom"` (`app/backend/app/services/panels.py:109-184`); FE mock labels some `panelapp-au` (`panels.mock.ts:20,46`). Needs materialized ClinGen/GenCC/MONDO/HGNC core (Layer 1) + PanelApp AU overlay with real `version`/`provenance_url`/`source` (Layer 2), and real `disease_mondo`→genes (currently 2 seeded ids, `panels.py:74-93`). FE renders whatever `source`/`version` the live catalogue returns — **so this is a data fix, not an FE-contract change** (§3.2 honesty rule). Gated for branding (§7.3).
4. **Async progress + persistence.** Real `done/total` + per-variant states over polling, then SSE (`GET /batch/{id}/stream`, plans/spec §8 — "SSE only after polling works"); results persisted to Supabase keyed to the user (today in-memory dict, `batch.py:57-58`). `BatchProgress` consumes a `BatchJob` snapshot so poll→SSE is a data-source swap.
5. **`n_after_filters` post-lookup AF pass.** Set eagerly at create (`batch.py:94`); should be computed at completion. FE field exists (`BatchJob.n_after_filters`, `backend.ts:1909`); the FE post-lookup AF filter (§3.4) is an interim client-side honesty measure.
6. **Large-VCF upload storage.** `POST /batch/uploads` exists but writes a disk snapshot / in-memory registry (`app/backend/app/services/vcf_ingest.py`, `batch.py:60-77`); needs object storage + server-side parse/filter returning diagnostics on `BatchJob.warnings`. FE only holds `upload_ref` (D-3 threshold, D-7 asset registry).
7. **Tier/quota source for the FE.** No FE accessor exists (`useAuth` exposes only id/email, `AuthProvider.tsx:18-21`). Needs an endpoint or session claim exposing `{ tier, cap_unfiltered, cap_total, used_this_period, quota_period }` so `useEntitlement` reads live data, plus **job-submission-scoped** rate limits distinct from `RATE_LIMIT_LOOKUP`. **Optional contract addition** (the only one this spec requests): a `GET /api/v1/me/entitlement` (or fold into an existing session/me endpoint) matching the `BatchEntitlement` shape in §1.2. Until then `useEntitlement` is dev-default.
8. **General mock VCF generator** (`make_test_vcf.py`, plans/spec §7) for FE parser/edge-case fixtures (hg19, multi-allelic, malformed, `--with-genotypes`). Only the Project-100 generator exists (`app/backend/scripts/generate_project_100_mock_vcf.py`). FE needs a handful of fixtures for the parser/intake tests — small ones can be hand-authored under a Claude-owned test fixtures dir if Codex's generator lags.

---

## §7 Gated items (⚠ needs Steven OK before shipping — recommendations are not authorization)

### 7.1 ⚠ GATED — large-VCF server-upload as a new intake mode
**Decision:** wiring `uploadBatch` makes "drop a big file" upload-to-server instead of client-parse — a durable change to the core intake gesture and a new flow.
**Recommendation:** approve. It revives an already-built, already-contracted dead path (`batch.ts:45-53`) and is the enabling mechanism for large VCFs (plans/spec §2). Ship behind the threshold so small-file behaviour is byte-for-byte unchanged. Needs Codex §6.6 (real storage) for the live version; mock-shippable (intake card + suppressed preview) now.

### 7.2 ⚠ GATED — Pro/Max/Free tiering UI that gates GENERATE
**Decision:** blocking a real action behind tier (Free upsell, Pro filter-required nudge, Max cap) is durable, revenue-facing behaviour, and needs the actual cap numbers.
**Recommendation:** approve the gate *mechanism* now (dev-default tier, parametric `CAP_P`/`CAP_M`); hold the live enforcement until Steven sets D-2 numbers and Codex exposes §6.7. Build it so flipping `entitlement.source` to `'live'` is the only switch.

### 7.3 ⚠ GATED — PanelApp AU overlay surfacing (named, branded panels)
**Decision:** showing "PanelApp Australia · v4.x" branded panels with provenance is durable and legally sensitive (D-1: ToU + OMIM carve-out unconfirmed; MONDO only). The FE mock currently *mislabels* panels `panelapp-au`.
**Recommendation:** ship the source-grouping affordance now driven *only* by the live catalogue's `source` field (truthful: shows `custom` against the real backend) — do **not** hard-code PanelApp branding until legal confirms and Codex serves real attribution (§6.3). This makes the UI honest today and correct automatically when the overlay lands.

### 7.4 ⚠ GATED (secondary) — tabbed output + Free upsell card alter the shipped `/compare` layout
**Decision:** the single output pane becomes 2 tabs (Results / Cohort summary), and the Free CTA becomes an upsell.
**Recommendation:** fold into 7.1/7.2 for one approval — both are direct consequences of at-scale results + tiering.

---

## §8 Open questions for Steven

1. **Caps (D-2):** concrete `CAP_P` (Pro variants/VCF before a filter is required) and `CAP_M` (Max whole-VCF cap)? The gate needs real numbers; until then they're named placeholders and usage shows "(estimated)".
2. **Client/server parse threshold (D-3, Codex's call, FE copy depends on it):** confirm ~5 MB / ~2k-line boundary so the intake card messaging is accurate.
3. **NL panel builder Tier B (D-6):** go/no-go on funding AskEamos for the bounded panel-builder use? Tier A ships regardless; Tier B stays COMING SOON (no wiring) until then.
4. **PanelApp AU launch (D-1):** legal/ToU confirmation in hand? exact launch panel set (IRD + cardiac + ?)? Until confirmed, the picker shows live `source` truthfully (no hard-coded PanelApp branding).
5. **Free-tier batch:** confirm Free = no batch (pricing copy `plans.ts:48-54` implies it) → upsell card rather than a runnable gate.
6. **Multi-sample VCFs (D-5):** confirm v1 = one VCF = one specimen (ignore per-sample GT) — affects intake-summary copy.
7. **Entitlement endpoint (§6.7):** OK for Codex to add `GET /api/v1/me/entitlement` (the one new contract this spec requests), or fold tier into an existing session/me response?
8. **Saved custom panels:** in scope for this cycle (needs Supabase persistence, a Codex dep) or deferred? The builder produces drafts today; "save named panel" has no backend.
