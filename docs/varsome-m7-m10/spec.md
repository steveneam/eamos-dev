# Varsome competitive milestones M7–M10 — implementation spec

> Frontend implementation spec. Surface: `app/web` (Next.js 16 App Router) `/report`.
> Created 2026-06-06 (Claude, Wave-2). **Spec only — no application code in this doc.**
> Companion design (trust its §0 audit): `docs/varsome-m7-m10/design.md`.
> Milestone source: `plans/v2-redesign-impeccable.md` §10.2 / §10.9.
> Competitive analysis: `docs/competitive/varsome.md`.

All line anchors below were re-verified against the live tree on 2026-06-06.

---

## §0 Scope & non-goals

### In scope (this spec)

1. **M8 live-data fix** — lazy-wire `CompositeVerdictBar` + `CalibratedInSilicoTable`
   (`ReportClient.tsx:737-738`) through `<LazySection sectionId="computational_deep_dive">`
   so the §2 in-silico table populates on a real backend lookup. **Centerpiece.**
2. **M9 live-data fix** — lazy-wire `ExpertPanelSection` (`ReportClient.tsx:775`)
   through `<LazySection sectionId="clingen_vcep">` so the §3 expert-panel block
   populates on a real backend lookup. **Centerpiece.**
3. **M9 type-drift reconcile** — collapse the duplicate `ExpertPanel*` type sets
   (local `expert-panel-sample.ts` vs contract `lib/backend.ts:737-798`) onto the
   contract types; handle the `partial` (ACMG-worksheet fallback) envelope shape.
4. **M7 anchor-id fix** — three synthesized tiles in `MatrixOverture.tsx` point at
   `target_section_id`s with no matching DOM anchor; clicks scroll nowhere. Map
   them to real section anchors.

### Out of scope (explicit non-goals)

- **M10a** (`PublicationsCallout.tsx`) — BUILT + correctly lazy-wired; **do not touch.**
- **M10b** publication-index v2 — net-new PMC/Europe-PMC + LLM-tag pipeline,
  ~1 Codex quarter. Not a FE deliverable.
- **M7 redesign** — the matrix IA, tile visuals, mobile carousel, premium-vs-no-data
  treatment are all built and correct. Only the broken anchor map is touched here.
- **M8/M9 visual redesign** — both components are visually complete and on-token.
  This is wiring + a type collapse, not greenfield.
- **AlphaMissense** stays hidden (filtered at `CalibratedInSilicoTable.tsx:54`;
  do not re-enable). **AskEamos** stays parked.
- **Backend changes** — no edits to `app/backend/**`. The M9 Evidence-Repository
  source-cache (§6) is a Codex dependency, flagged not designed here.
- **New design tokens** — none required (see §3). Any token addition is GATED (§7).
- **MONDO disease link / inheritance mode** on the M9 contract — additive backend
  field, not present today; deferred to the post-cache contract (§6, §8 Q4).

---

## §1 Contracts & types

### 1.1 The `/lookup/sections` section-fetch contract (verified)

The lazy path is fully built and is the same one publications already uses.

- **Frontend caller:** `fetchLookupSections(payload)` (`lib/api.ts:143-152`) →
  `POST /api/v1/lookup/sections`. Request body =
  `LookupSectionFetchRequest = LookupRequest & { include: LookupSectionId[] }`
  (`lib/backend.ts:361-363`).
- **Backend route:** `lookup_sections()` (`app/backend/app/api/routes/lookup.py:74-89`)
  → `build_lookup_section_fetch_response()` (`lookup_sections.py:66-76`).
- **Response:** `LookupSectionFetchResponse` (`lib/backend.ts:381-386`) →
  `sections: Partial<Record<LookupSectionId, LookupSectionEnvelope>>`.
- **Envelope:** `LookupSectionEnvelope` (`lib/backend.ts:373-379`):
  `{ section_id, status: 'available'|'partial'|'missing', payload?: Record<string,unknown>|null, freshness, warnings }`.
- **`LookupSectionId`** (`lib/backend.ts:325-328`): `'publications' | 'computational_deep_dive' | 'clingen_vcep'`.
  All three already whitelisted in the `?lazy=` hatch (`ReportClient.tsx:72-76`).

**`<LazySection>` consumption contract** (`LazySection.tsx`):

- `eagerData != null` → renders `children(eagerData)` immediately, **no fetch,
  no observer** (`LazySection.tsx:82`). This is the offline-fixture path.
- `eagerData == null` + `request` present → mounts the IntersectionObserver
  sentinel; on intersect (or `forceLoad`) fires `fetchLookupSections({ ...request, include: [sectionId] })`
  (`LazySection.tsx:137`), then `unwrap(response.sections[sectionId])`
  (`LazySection.tsx:139-149`).
- `unwrap` returning `null` → **error state** (`"payload could not be narrowed"`,
  `LazySection.tsx:145-147`), not empty. Empty content is the children's job.
- `eagerData == null` + no `request` → renders `emptyView` (`LazySection.tsx:85`).

**How publications consumes it (the pattern to mirror)** —
`ReportClient.tsx:897-920`:

```
<LazySection<PublicationLiterature>
  key={`pubs-${variantKey}${lazyOverrides.has('publications') ? '-lazy' : ''}`}
  eagerData={lazyOverrides.has('publications') ? null : payload.publications_literature}
  sectionId="publications"
  request={effectiveSummaryRequest ?? null}
  unwrap={(env) => (env.payload as PublicationLiterature | null) ?? null}
  forceLoad={lazyOverrides.has('publications')}
>
  {(lit) => <PubMedSection payload={{ ...payload, publications_literature: lit }} … />}
</LazySection>
```

### 1.2 Per-section envelope payload shapes (verified against the backend builder)

**`computational_deep_dive`** (`lookup_sections.py:129-147`):
- `status: 'available'` when predictors/conservation/spliceAI present, else `'missing'`.
- `payload` = `ComputationalDeepDiveSection.model_dump(mode="json")` — exactly the
  FE `ComputationalDeepDiveSection` type (`lib/backend.ts:880-887`), whose
  `.predictors` is `ComputationalPredictorRow[]` (`lib/backend.ts:865-878`) — the
  same array the table already consumes via `payload.report_profile?.computational_deep_dive?.predictors`.
- **Single shape.** No fallback variant. `unwrap` returns the whole section; the
  call site reads `.predictors` off it.

**`clingen_vcep`** (`lookup_sections.py:150-185`) — **TWO payload shapes by status:**
- `status: 'available'` (`:153-160`) → `payload = ExpertPanelSection.model_dump(mode="json")`
  — exactly the contract `ExpertPanelSection` (`lib/backend.ts:789-798`). This is
  the real VCEP path (only once the Codex source-cache lands).
- `status: 'partial'` (`:172-185`) → **payload is an `AcmgWorksheetLedger` dump**
  (`run.py:615-618`) with two patched keys: `narrative` (= `acmg_classification`,
  a string) and `source_scope = "current_clinical_consensus_snapshot"`, plus the
  warning `clingen_vcep_evidence_repo_source_cache_not_integrated`. **This shape is
  NOT an `ExpertPanelSection`** — no `vcep`, no `final_classification`, no
  `criteria` in the expert-panel shape, no `provenance`/`freshness`. **This is the
  shape served live today.**
- `status: 'missing'` (`:163-170`) → `payload: null`.

**Contract consequence (load-bearing):** the M9 `unwrap` MUST distinguish the two.
For `status !== 'available'` it returns `null` → the component renders nothing
**and** the `<LazySection>` shows its error view by default. To avoid a false
error banner on the (currently universal) `partial` path, the call site MUST pass
a custom `errorView` (or `emptyView`) that renders the honest "derived from
consensus, not the ClinGen Evidence Repository" note instead of a red error. See
§3-C for the exact decision. **Until the source-cache lands, M9 will never render
the rich expert-panel block on live data** — it can only render the partial-state
note. This is correct and honest (§7 gate, §8 Q5).

### 1.3 M9 type-drift reconcile (verified)

Two parallel, same-named type families exist:

| Type | Local (`components/report/expert-panel-sample.ts`) | Contract (`lib/backend.ts`) | Drift |
| ---- | ------------------------------------------------- | --------------------------- | ----- |
| `ExpertPanelClassification` | `:9-16` | `:737-744` | identical |
| `ExpertPanelFreshness` / `…Reason` | `:18-23` | `:745-749` | identical |
| `ExpertPanelVcep` | `:34-40` | `:761-767` | identical |
| `ExpertPanelCriterion` | `:25-32` | `:769-779` | **contract has 3 extra fields:** `assertion_level: EvidenceAssertionLevel` (**required**), `source?: string\|null`, `warnings: string[]` |
| `ExpertPanelProvenance` | `:42-48` | `:781-787` | identical |
| `ExpertPanelData` (local) vs `ExpertPanelSection` (contract) | `:50-59` | `:789-798` | identical fields, different NAME |

The component imports the **slim local** types (`ExpertPanelSection.tsx:5-9`), but
the mount passes the **contract** type: `payload.report_profile?.expert_panel`
is `ExpertPanelSection | null` (`lib/backend.ts:1135`). It compiles today only
because the contract criterion is a structural superset of the local one (extra
fields are tolerated when assigning to the narrower target).

**Resolution:** component types against the contract; delete the local duplicate
structural types; keep only display-enum helpers if any are local-only (none are —
the component's `CLASSIFICATION_DISPLAY` / `CRITERION_STATE_TINT` maps key off the
contract enums unchanged). Details in §2.3.

---

## §2 Component / file plan (exact edits)

**Files edited: 3 application files + 1 deletion.** No new components. No new files.

### 2.1 `app/web/components/report/ReportClient.tsx` — the centerpiece

**Imports (top block, lines 18-19, 31, 58-65):**
- Add `ComputationalDeepDiveSection` and `ExpertPanelSection` to the type import
  from `@/lib/backend` (`:58-65`). `ExpertPanelSection` is both a *type* (the
  contract interface) and the *component* name already imported at `:31` — import
  the type with an alias to avoid the name clash, e.g.
  `ExpertPanelSection as ExpertPanelSectionData`.
- `LazySection` (`:17`), `CalibratedInSilicoTable` (`:18`), `CompositeVerdictBar`
  (`:19`), `ExpertPanelSection` component (`:31`) already imported — no change.

**M8 edit — §2 In-silico card (`:723-739`):** wrap the two children
(`CompositeVerdictBar` + `CalibratedInSilicoTable`, `:737-738`) in a
`<LazySection<ComputationalDeepDiveSection>>`, mirroring publications:
- `key={`insilico-${variantKey}${lazyOverrides.has('computational_deep_dive') ? '-lazy' : ''}`}`
- `eagerData={lazyOverrides.has('computational_deep_dive') ? null : payload.report_profile?.computational_deep_dive}`
  — non-null in the offline fixture (renders immediately), null/undefined on the
  live eager response (lazy fetch fires).
- `sectionId="computational_deep_dive"`, `request={effectiveSummaryRequest ?? null}`,
  `forceLoad={lazyOverrides.has('computational_deep_dive')}`.
- `unwrap={(env) => (env.payload as ComputationalDeepDiveSection | null) ?? null}`.
- children `(section) => <><CompositeVerdictBar predictors={section.predictors} /><CalibratedInSilicoTable predictors={section.predictors} /></>`.
- `emptyView` = the existing empty copy ("No in-silico predictions available for
  this variant.") so a no-request/no-data state matches the component's own empty
  state at `CalibratedInSilicoTable.tsx:56-62`.

**M9 edit — §3 Clinical evidence card (`:746-778`):** wrap `ExpertPanelSection`
component (`:775`) in `<LazySection<ExpertPanelSectionData>>`. `ClinVarBlock` (`:776`)
and `AcmgCriteriaFold` (`:777`) stay **outside** the LazySection (they read eager
payload + `data.evidence` and must never be gated by the expert-panel fetch):
- `key={`vcep-${variantKey}${lazyOverrides.has('clingen_vcep') ? '-lazy' : ''}`}`
- `eagerData={lazyOverrides.has('clingen_vcep') ? null : payload.report_profile?.expert_panel}`
- `sectionId="clingen_vcep"`, `request={effectiveSummaryRequest ?? null}`,
  `forceLoad={lazyOverrides.has('clingen_vcep')}`.
- `unwrap` (§1.2): return the payload typed as `ExpertPanelSectionData` **only when
  the envelope `status === 'available'`**; otherwise return `null`. Because
  `unwrap` only receives the envelope (not status via a separate arg — status IS on
  the envelope: `env.status`), guard on `env.status === 'available'`.
- `emptyView` AND `errorView` → render the M9 partial-state note (§3-C), NOT a red
  banner, because the `partial` path is the live default today.
- children `(section) => <ExpertPanelSection data={section} />` (component prop is
  `data`, `ExpertPanelSection.tsx:11-13`).
- **a11y:** the partial-note must be a `<div role="note">` (informational), not
  `role="alert"`, so SRs don't announce an error for the expected partial state.

### 2.2 `app/web/components/report/MatrixOverture.tsx` — M7 anchor fix

`scrollToTile` (`:34-45`) resolves `tile.target_panel_id ?? tile.target_section_id`
then `document.getElementById(targetId)`; returns early if the element is missing
(`:38`). Real DOM anchors in `ReportClient` (the `<div id=… className="scroll-mt-24" />`
markers): `population_frequency`, `evidence_by_source`, `clinical_evidence`,
`gene_context`, `associated_conditions`, `curated_variants`, `publications`,
`trials`, `ai_summary`. Three synthesized tiles miss:

| Tile (`synthesizeTilesFromPayload`) | Current `target_section_id` | Real anchor | Fix |
| ----------------------------------- | --------------------------- | ----------- | --- |
| #8 `gene_context` (`:250`) | `gene_context_snapshot` | `gene_context` (`ReportClient.tsx:787`) | change to `'gene_context'` |
| #11 `clingen_vcep` (`:295`) | `clingen_vcep` (no anchor) | `clinical_evidence` (§3 host, `:745`) | change to `'clinical_evidence'` |
| #12 `computational_deep_dive` (`:309`) | `computational_deep_dive` (no anchor) | `evidence_by_source` (§2 host, `:722`) | change to `'evidence_by_source'` |

- Edit only the `target_section_id` literals at `:250`, `:295`, `:309`. Do NOT
  touch `fetch_section_id` (those correctly stay `clingen_vcep` / `computational_deep_dive`
  for the M11 tile-detail contract) or any visual/premium logic.
- **Live-tile note:** when the backend `lookupSummary()` returns ≥8 tiles
  (`MatrixOverture.tsx:70`), live `target_section_id`s come from `call_cards`
  interaction targets (`lookup_sections.py:95-97`), not this synthesizer. The
  backend tile→anchor mapping is a separate Codex concern (§6 #2) — flag, don't fix
  here. This edit hardens the offline/fallback path that ships today.

### 2.3 `app/web/components/report/ExpertPanelSection.tsx` + delete `expert-panel-sample.ts`

- Change the type import (`:5-9`) from `'./expert-panel-sample'` to `'@/lib/backend'`,
  importing `ExpertPanelClassification`, `ExpertPanelCriterion`, and
  `ExpertPanelSection` (the contract interface). The component prop type
  `ExpertPanelSectionProps.data` (`:11-13`) becomes `ExpertPanelSection | null`
  (alias locally if the component name shadows — it does not, the function is
  `ExpertPanelSection`, so alias the **type** import: `ExpertPanelSection as ExpertPanelSectionData`).
- `FreshnessChip` (`:44-69`) and `CriterionChip` (`:71-116`) param types switch to
  the contract `ExpertPanelData`-equivalent (now `ExpertPanelSectionData`) and
  contract `ExpertPanelCriterion`. The component already only reads fields present
  on both shapes (`code`, `applied_strength`, `default_strength`, `state`,
  `rationale`) — the contract's extra `assertion_level`/`source`/`warnings` are
  unused by render, so **no rendering change**; this is a pure type swap.
- **Delete** `app/web/components/report/expert-panel-sample.ts` (type-only, no
  runtime export, no fixture — confirmed `:1-59`). Verify no other importer first
  (grep `expert-panel-sample` across `app/web`): only `ExpertPanelSection.tsx:9`
  imports it today.

---

## §3 Behaviour spec

### (A) M8 + M9 lazy-wire — populate live by mirroring publications

**Goal:** on a real backend lookup, §2 in-silico table and §3 expert-panel block
render their data (today they render empty/null because their payload slices are
stripped by `LOOKUP_EAGER_RESPONSE_EXCLUDE`, `lookup.py:26-34`, and the components
read the eager payload directly).

**Mechanism (identical for both):** `<LazySection>` short-circuits to `eagerData`
when present (offline fixture ships full payload → instant render, zero fetch),
else fires the IntersectionObserver one-shot `/lookup/sections` fetch on
scroll-approach (`rootMargin: 200px`).

**States (per `LazySection.tsx` + each child):**

| State | Trigger | Render |
| ----- | ------- | ------ |
| eager | offline fixture / any eager payload (`eagerData != null`) | child renders immediately |
| idle / loading | live, pre-intersect or fetch in flight | `DefaultPlaceholder` (`LazySection.tsx:210-226`) "Loading <id>…", `aria-busy` on the sentinel |
| ready | fetch resolved + `unwrap` non-null | child renders fetched section |
| empty (M8) | `predictors` array empty | `CalibratedInSilicoTable` own copy "No in-silico predictions available" (`:56-62`); pass same string as `emptyView` for the no-request case |
| error (M8) | network/5xx fail | `DefaultErrorView` with Retry (`LazySection.tsx:228-256`) — acceptable for M8 (no expected non-error fallback) |
| partial (M9) | live `clingen_vcep` envelope `status: 'partial'` (today's default) | M9 partial note (see C), NOT a red error |
| error (M9) | true fetch failure | M9 partial note via `errorView` (treat as honest "not available", not red) — see §8 Q5 |

**a11y:** placeholder uses `role="status"` (already). M9 partial note uses
`role="note"`. Keyboard/focus order unchanged (sections still render in DOM order;
LazySection sentinel is a plain `<div>` that's replaced on ready).

### (B) M7 anchor-id corrections

Every overture tile must scroll to a real section. After the §2.2 literal fixes,
`scrollToTile` resolves a present element for all 12 synthesized tiles. Behaviour
otherwise unchanged: smooth scroll with `SCROLL_OFFSET` (68px), `history.replaceState`
URL-fragment write for shareable deep-links (`MatrixOverture.tsx:42-44`). No tile
visual, premium, or no-data treatment changes.

**Acceptance:** click each of the 12 tiles → page scrolls to a visible section
header; the URL fragment updates; no silent no-op. Premium tiles (#11 ClinGen
VCEP, #12 Deep dive) scroll to their host card (§3 / §2) — the section that will
contain the deep content once unlocked.

### (C) M9 type-drift reconcile + partial-state honesty

- Type collapse per §2.3 — purely structural, no render change.
- **Partial-state note (the honest read):** when live `clingen_vcep` returns
  `status: 'partial'` (cache not integrated — `lookup_sections.py:176`), the rich
  VCEP block cannot render (payload is an ACMG worksheet, not an `ExpertPanelSection`).
  Render instead a compact `role="note"` inside §3:
  > "ClinGen Variant Curation Expert Panel narrative is derived from the current
  > clinical-consensus snapshot, not the ClinGen Evidence Repository. Full VCEP
  > attribution lands when the Evidence-Repository source-cache is integrated."
  Style with `--warn-tint` / `--warn-bdr` / `--ink-3` (existing tokens; the
  `FreshnessChip` "Stale" treatment, `ExpertPanelSection.tsx:44-67`, is the visual
  reference). **This is GATED** (§7 #2 / §8 Q5) — alternative is to suppress §3's
  expert-panel slot entirely until the cache lands.

---

## §4 Invariants (must not regress)

1. **M7 matrix + M10a publications stay correct.** M7 only gets 3 literal
   `target_section_id` edits; M10a is untouched. The publications `<LazySection>`
   call site (`ReportClient.tsx:897-920`) must be byte-identical after this change.
2. **Reading column untouched.** §1 population, §4 gene context, §5 disease/curated,
   §7 trials, §8 AI summary keep their current eager render. §3's `ClinVarBlock`
   and `AcmgCriteriaFold` render **outside** the M9 LazySection — never gated by
   the expert-panel fetch.
3. **Offline fixture = zero new fetches.** The RPE65 sample
   (`RPE65_NEGATIVE_CONTROL_SAMPLE`, `ReportClient.tsx:39`) ships full
   `computational_deep_dive` + `expert_panel`, so `eagerData != null` and both new
   LazySections short-circuit (no `/lookup/sections` call) — same as today's render.
4. **AlphaMissense stays filtered** (`CalibratedInSilicoTable.tsx:54`). The lazy
   wrap must not bypass that filter (it can't — it passes `section.predictors`
   through the same component).
5. **One-shot per variant.** Both new LazySections key on `variantKey`
   (`ReportClient.tsx:568`) so switching variants remounts and resets fetch state,
   exactly like `pubs-${variantKey}` and `matrix-${variantKey}`.
6. **No backend, contract, or token changes** in this milestone.

---

## §5 Test plan

**Harness reality (verified):** `app/web` has **no test runner** — `package.json`
scripts are `dev` / `build` / `lint` / `gen:gnomad-map` only; there is no vitest,
playwright, or jest config in `app/web`. (The vitest references in the design doc
are the legacy Vite `app/frontend`.) The realistic verification gates are
TypeScript (via Next build), ESLint, the `?lazy=` preflight escape-hatch, and
browser-verify. **Recommendation (GATED, §7 #4):** if Steven wants automated
coverage for the unwrap/status logic, stand up vitest + RTL in `app/web` as a
separate, scoped task — do not silently introduce a test runner under this spec.

**Mandatory gates (this spec):**

1. **Typecheck:** `npm --prefix app/web run build` passes. Catches the §2.3 type
   collapse (deleting `expert-panel-sample.ts`, the `ExpertPanelSection` type/component
   alias, the two `unwrap` casts).
2. **Lint:** `npm --prefix app/web run lint` clean (no unused imports after the
   delete; LazySection `eslint-disable` comments unchanged).
3. **Offline render (no backend):** load `/report?demo` (RPE65 fixture). §2
   in-silico table + §3 expert-panel block render with full data, **zero**
   `/lookup/sections` requests in the Network panel (eager short-circuit). M7:
   click all 12 tiles → each scrolls to a real section.
4. **Live lazy fetch (backend up):** load `/report?lazy=computational_deep_dive,clingen_vcep`
   against the live backend. Confirm:
   - one `POST /api/v1/lookup/sections` per section with `include:[…]`;
   - §2 populates from the `available` `computational_deep_dive` envelope;
   - §3 shows the **partial-state note** (live default today, `status: 'partial'`)
     — NOT a red error, NOT the rich VCEP block (until §6 #1 lands).
5. **Scroll-driven lazy (no `?lazy=`):** on a real lookup that strips the eager
   slices, scroll §2/§3 into view → fetch fires ~200px before viewport; placeholder
   → ready transition; no double-fetch (one-shot).
6. **Regression:** publications (§6) still lazy-loads; reading column unchanged;
   variant switch remounts both new sections (fetch state resets).

**Acceptance criteria (pass/fail):**
- [ ] Live `/lookup` → §2 in-silico table shows predictor rows (not "No in-silico predictions").
- [ ] Live `/lookup` → §3 shows the expert-panel block (rich when `available`, honest partial note when `partial`).
- [ ] All 12 M7 tiles scroll to a present DOM anchor; URL fragment updates.
- [ ] `expert-panel-sample.ts` deleted; build + lint green; no other importer broke.
- [ ] Offline `/report?demo` makes zero section-fetch calls; renders identically to today.

---

## §6 Backend dependencies (Codex lane — flag, do not design as present)

| # | Milestone | Dependency | State (verified) |
| - | --------- | ---------- | ---------------- |
| 1 | M9 | **ClinGen Evidence-Repository source-cache integration.** Until it lands, `clingen_vcep` returns `status: 'partial'` from the ACMG-worksheet fallback (`lookup_sections.py:172-185`, warning `clingen_vcep_evidence_repo_source_cache_not_integrated`). The rich `ExpertPanelSection` `available` payload only appears post-cache. | OPEN (§10.9 CAR #3). Scaffolding present (`source_cache.py`). **M9 renders only the partial note on live data until this ships.** |
| 2 | M7 (live path) | **Backend tile→section-anchor mapping.** When `lookupSummary()` returns ≥8 live tiles, `target_section_id` comes from `call_cards` interaction targets (`lookup_sections.py:95-97`), not the FE synthesizer. Confirm those resolve to real `/report` DOM anchors (the FE fix in §2.2 only hardens the offline/fallback synthesizer). | Confirm with Codex; not blocking the offline fix. |
| 3 | M9 | **MONDO disease link + inheritance mode** on the expert-panel contract (Varsome parity). Not in `ExpertPanelVcep` today (`lib/backend.ts:761-767` / backend `run.py:489`). | Missing field, additive. Deferred (§8 Q4). |
| 4 | M8/M9 | **Lazy-fetch contract confirmation (CAR cadence).** Endpoints exist; no backend change needed. Confirm the `computational_deep_dive` `available` shape and the `clingen_vcep` two-shape (`available` vs `partial`) contract with Codex before shipping the unwrap guards. | Endpoints shipped; FE not yet consuming these two. |

**No backend code is written by this spec.** Items 1 + 3 are Codex deliverables;
items 2 + 4 are confirm-only.

---

## §7 Gated items (need Steven's explicit OK — recommendation ≠ authorization)

1. **⚠ GATED — M8/M9 lazy-wire alters the live hydration path (structural-ish).**
   Migrating §2 in-silico and §3 expert-panel to `<LazySection>` changes how those
   sections hydrate on a live lookup: instead of arriving with the eager payload,
   they fetch on scroll-approach and pop in (placeholder → content). This is the
   *correct* fix and mirrors the already-shipped publications pattern, but it is a
   visible change to perceived load behaviour on `/report`.
   **Recommendation:** ship it — it's the minimal, consistent fix and the only way
   to make M8/M9 show live data without un-doing the M11 eager-trim perf win.
2. **⚠ GATED — M9 partial-state treatment.** Render the honest "derived from
   consensus, not ClinGen Evidence Repository" note (§3-C) vs suppress the §3
   expert-panel slot entirely until the source-cache lands.
   **Recommendation:** render the note. Suppressing hides that an expert-panel
   surface exists; the note is honest about provenance and degrades gracefully.
   (Ties to §8 Q5.)
3. **⚠ GATED — M7 premium-gated tiles with no paid tier live.** Tiles #11/#12
   show `Premium` badges (`MatrixOverture.tsx:292,307`) but there is no in-report
   paywall. Out of this spec's scope (no edit proposed beyond the anchor literal),
   but flagged: the anchor fix makes these tiles *functional* (they now scroll to
   their host card), which may sharpen the "premium with nothing behind it"
   question. Decide: keep as forward-looking, or hide until a paid tier ships.
4. **⚠ GATED — standing up a test runner in `app/web`.** §5 notes there is none.
   Do not introduce vitest/RTL under this spec; if wanted, scope separately.

---

## §8 Open questions for Steven

1. **M8/M9 — ship the lazy-wire fix this cycle?** Both render empty on a live
   lookup today (the plan marks them shipped). Treat as a bug-fix now, or schedule
   into a later M11 full-ship wave? (Gate #1.)
2. **M7 premium tiles** — keep #11/#12 `Premium` placeholders (now that they
   scroll somewhere), or hide until a paid tier exists? (Gate #3.)
3. **M10a toggle URL-push** — out of scope here, but still open from Wave-1: should
   toggling to gene scope write `?pubScope=gene` so a gene-scoped publications view
   is shareable? Today inbound-only.
4. **M9 content scope** — ship VCEP narrative + criteria only for v1, or wait for
   the Codex contract to carry MONDO disease link + inheritance mode (Varsome
   parity)? (§6 #3.)
5. **M9 partial honesty** — render the partial-state provenance note (recommended,
   gate #2) or suppress the §3 expert-panel slot until the real ClinGen Evidence
   Repository cache lands? Suppressing avoids implying VCEP authority we don't yet
   have; the note keeps the read honest while degrading gracefully.
