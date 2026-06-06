# Varsome M7–M10 — phased build runbook

> Frontend build runbook. Surface: `app/web` (Next.js 16 App Router) `/report`.
> Created 2026-06-06 (Claude, Wave-3). **Runbook only — no application code in this doc.**
> Trust the verified inputs: `docs/varsome-m7-m10/spec.md` + `docs/varsome-m7-m10/design.md`
> (orchestrator fact-checked). Every anchor below was re-confirmed against the live tree
> on 2026-06-06.

---

## §0 How to use this runbook

Each phase below is a discrete, independently shippable unit. Execute **top to bottom**
(cheapest/safest → biggest). **Abort on the first red gate** — do not stack a broken
step onto the next.

### Standing verify gate (applies to EVERY step unless the row says otherwise)

`app/web` has **no test runner** (`package.json` scripts = `dev`/`build`/`start`/`lint`/
`gen:gnomad-map` only — verified `app/web/package.json:5-11`; no vitest/jest/playwright).
So the gate is three checks, all run from the repo root, all must pass:

| # | Gate | Command | Pass condition |
| - | ---- | ------- | -------------- |
| G1 | Typecheck | `npx --prefix app/web tsc --noEmit -p app/web/tsconfig.json` | exit 0, zero errors |
| G2 | Lint | `npm --prefix app/web run lint` | exit 0, zero errors/warnings |
| G3 | Browser-verify (`:3000`) | per-row "Browser check" column | the named condition holds |

Notes:
- **G1**: `tsc` is not a package script; invoke it directly. `typescript@^5.7` is a
  devDep (`package.json:35`) so `npx --prefix app/web tsc` resolves the local binary.
  `app/web/tsconfig.json` exists (verified). This is the prompt-mandated typecheck gate.
- **G3 preflight hatch**: the `?lazy=` query param force-fetches lazy sections. The
  whitelist `LAZY_OVERRIDE_VALID_IDS` accepts `publications` / `computational_deep_dive`
  / `clingen_vcep` (verified `ReportClient.tsx:72-76`). Use `?lazy=computational_deep_dive,clingen_vcep`
  to force both new sections through the live `/lookup/sections` path without scrolling.
- **G3 offline hatch**: `?demo` renders `RPE65_NEGATIVE_CONTROL_SAMPLE`
  (`ReportClient.tsx:39,418`) which ships full `computational_deep_dive` + `expert_panel`
  → `eagerData != null` → LazySection short-circuits (zero fetches). Use it to verify
  the eager path is unbroken.
- **Dev server**: assume `npm --prefix app/web run dev` is already serving `:3000`
  (do NOT start/kill a `:3000` server inside this runbook — see Risks R6). Live lazy
  steps additionally need the backend at `:8000` (mock provider is fine).
- **Do NOT touch** `app/backend/**`, `agent_handoff/**`, or any running `:3000` dev server.

---

## §1 Phase table (execute in order)

| # | Phase | Gated? | Files to EDIT (line anchors) | Change (intent — NOT a diff) | Verify gate (G1+G2 always, plus this Browser check) |
| - | ----- | ------ | ---------------------------- | ---------------------------- | --------------------------------------------------- |
| **P1** | **M7 anchor-id fix** | ungated (3 literal swaps, no structural/visual change) | `app/web/components/report/MatrixOverture.tsx:250`, `:295`, `:309` | Change three `target_section_id` string literals to real DOM anchors: `:250` `'gene_context_snapshot'`→`'gene_context'`; `:295` `'clingen_vcep'`→`'clinical_evidence'`; `:309` `'computational_deep_dive'`→`'evidence_by_source'`. Touch ONLY the `target_section_id` literal on each tile. Do NOT touch `fetch_section_id` (`:297`/`:311` correctly stay `clingen_vcep`/`computational_deep_dive` for the M11 tile-detail contract), `target_panel_id`, or any premium/visual logic. | **Browser** (`/report?demo`): click each of the 12 overture tiles → every tile scrolls to a visible section header and the URL fragment updates; none silently no-op. Specifically tiles "Gene context", "ClinGen VCEP", "Deep dive" now scroll (they were dead before). |
| **P2** | **M9 type-drift reconcile** | ungated (pure type collapse, zero render change) | `app/web/components/report/ExpertPanelSection.tsx:5-9` (import), `:11-13` (prop type), `:44` + `:71` (chip param types); **DELETE** `app/web/components/report/expert-panel-sample.ts` | Repoint the type import from `'./expert-panel-sample'` to `'@/lib/backend'`, importing `ExpertPanelClassification`, `ExpertPanelCriterion`, and `ExpertPanelSection` (the contract interface, `lib/backend.ts:737-798`). Alias the type to avoid clashing with the same-named component function: `import { …, ExpertPanelSection as ExpertPanelSectionData } from '@/lib/backend'`. Retype `ExpertPanelSectionProps.data` (`:11-13`), `FreshnessChip`'s `data` param (`:44`), `CriterionChip`'s `criterion` param (`:71`) onto the contract types. No render change: the component reads only fields common to both shapes (`code`/`applied_strength`/`default_strength`/`state`/`rationale`/`freshness`/`freshness_reason`); the contract's extra `assertion_level`/`source`/`warnings` (`backend.ts:774,776,778`) are unused by render. Then **delete** `expert-panel-sample.ts` (type-only, no runtime export — verified `:1-59`; sole importer is `ExpertPanelSection.tsx:9`, confirmed by grep). | **Browser** (`/report?demo`): §3 Clinical evidence renders the RPE65 expert-panel block identically to before (narrative + criteria chips + `§` override markers + freshness chip). No visual diff. G1/G2 are the real teeth here (catches the deleted file's orphaned import + the alias). |
| **P3** | **M8 lazy-wire** (§2 in-silico) | **⚠ GATED — alters live hydration path** | `app/web/components/report/ReportClient.tsx:58-65` (type import), `:737-738` (wrap) | Add `ComputationalDeepDiveSection` to the `@/lib/backend` type import (`:58-65`). Wrap the two existing children `CompositeVerdictBar` + `CalibratedInSilicoTable` (`:737-738`) in a `<LazySection<ComputationalDeepDiveSection>>`, mirroring publications (`:897-920`) byte-for-byte in structure: `key={`insilico-${variantKey}${lazyOverrides.has('computational_deep_dive') ? '-lazy' : ''}`}`; `eagerData={lazyOverrides.has('computational_deep_dive') ? null : payload.report_profile?.computational_deep_dive}`; `sectionId="computational_deep_dive"`; `request={effectiveSummaryRequest ?? null}`; `forceLoad={lazyOverrides.has('computational_deep_dive')}`; `unwrap={(env) => (env.payload as ComputationalDeepDiveSection | null) ?? null}`; children `(section) => <><CompositeVerdictBar predictors={section.predictors} /><CalibratedInSilicoTable predictors={section.predictors} /></>`. Default error/empty views are fine for M8 (single payload shape, no expected non-error fallback). Do NOT move the `<div id="evidence_by_source">` anchor (`:722`) or the `<Card>` wrapper — the LazySection goes INSIDE the Card body, replacing the two bare children. | **Browser A** (`/report?demo`): §2 renders predictor rows immediately, **zero** `POST /api/v1/lookup/sections` in the Network panel (eager short-circuit). **Browser B** (`/report?lazy=computational_deep_dive`, backend up): exactly one `POST /api/v1/lookup/sections` with `include:["computational_deep_dive"]`; §2 populates with predictor rows (not "No in-silico predictions"); AlphaMissense still absent (filter at `CalibratedInSilicoTable.tsx:54` intact). |
| **P4** | **M9 lazy-wire** (§3 expert panel) | **⚠ GATED — alters live hydration path + partial-state note** | `app/web/components/report/ReportClient.tsx:58-65` (type import), `:775` (wrap) | Add `ExpertPanelSection as ExpertPanelSectionData` to the `@/lib/backend` type import (`:58-65`) — alias because the component `ExpertPanelSection` is already imported at `:31`. Wrap ONLY the `<ExpertPanelSection>` component (`:775`) in `<LazySection<ExpertPanelSectionData>>`. **`ClinVarBlock` (`:776`) and `AcmgCriteriaFold` (`:777`) stay OUTSIDE** the LazySection (they read eager `data.evidence` + `acmg_criteria_scaffold` and must never be gated by the expert-panel fetch — Invariant §4.2). Props: `key={`vcep-${variantKey}${lazyOverrides.has('clingen_vcep') ? '-lazy' : ''}`}`; `eagerData={lazyOverrides.has('clingen_vcep') ? null : payload.report_profile?.expert_panel}`; `sectionId="clingen_vcep"`; `request={effectiveSummaryRequest ?? null}`; `forceLoad={lazyOverrides.has('clingen_vcep')}`; `unwrap={(env) => env.status === 'available' ? (env.payload as ExpertPanelSectionData | null) ?? null : null}` (the `status==='available'` guard rejects the live `partial` ACMG-worksheet shape — §1.2 of spec); children `(section) => <ExpertPanelSection data={section} />` (prop is `data`, `ExpertPanelSection.tsx:11-13`). Because the live default is `partial` → `unwrap` returns null → LazySection takes its error path → pass BOTH `errorView` and `emptyView` rendering the honest partial note (NOT a red banner): a `<div role="note">` styled with `--warn-tint`/`--warn-bdr`/`--ink-3` (FreshnessChip "Stale" at `ExpertPanelSection.tsx:44-67` is the visual reference) with the copy from spec §3-C ("…derived from the current clinical-consensus snapshot, not the ClinGen Evidence Repository. Full VCEP attribution lands when the Evidence-Repository source-cache is integrated."). `role="note"` not `role="alert"` so SRs don't announce an error for the expected partial state. | **Browser A** (`/report?demo`): §3 renders the rich RPE65 expert-panel block, **zero** section-fetch calls; `ClinVarBlock` + `AcmgCriteriaFold` render below it unchanged. **Browser B** (`/report?lazy=clingen_vcep`, backend up): exactly one `POST /api/v1/lookup/sections` with `include:["clingen_vcep"]`; §3 shows the **partial-state note** (`role="note"`, warn-tint, NOT red, NOT the rich block — because live status is `partial` today); `ClinVarBlock`/`AcmgCriteriaFold` still render below. Confirm console shows no `role="alert"` for §3. |

### Codex dependency — separate lane (do NOT block P1–P4 on it)

| Lane | Owner | Item | State (verified) | Effect on this runbook |
| ---- | ----- | ---- | ---------------- | ---------------------- |
| **C1** | Codex (backend) | ClinGen Evidence-Repository **source-cache integration** (`app/backend/.../lookup_sections.py:172-185`). Until it lands, `clingen_vcep` returns `status:'partial'` from the ACMG-worksheet fallback with warning `clingen_vcep_evidence_repo_source_cache_not_integrated`. | OPEN (§10.9 CAR #3; scaffolding present in `source_cache.py`). | **Non-blocking.** P4 ships the honest partial note and is *complete* on its own. When C1 lands, the SAME P4 `unwrap` guard (`status==='available'`) automatically starts rendering the rich VCEP block — **no further FE change**. Confirm-only handoff to Codex; do NOT edit `app/backend/**`. |

---

## §2 Recommended first 3 steps

1. **P1 — M7 anchor-id fix.** Three literal swaps in `MatrixOverture.tsx:250/295/309`,
   ungated, zero structural/visual change, instantly browser-verifiable on `/report?demo`.
   Lowest risk, fixes a live-broken behaviour (3 dead tiles). Land it first.
2. **P2 — M9 type-drift reconcile.** Pure type collapse + one file deletion, ungated,
   zero render change. Do it BEFORE P4 so the M9 lazy-wire builds on the already-collapsed
   contract types (avoids re-touching the import block twice). G1/G2 prove the delete is clean.
3. **Open the P3/P4 gate with Steven, then ship P3 — M8 lazy-wire.** P3 is the centerpiece
   live-data fix and the lower-risk of the two GATED steps (single payload shape, no
   partial-note nuance). Get Steven's explicit OK on the "live sections now pop in on
   scroll" hydration change (Gate, §3 below) once, covering both P3 and P4, then ship P3.
   P4 follows immediately after (same gate, same pattern, plus the partial note).

---

## §3 Gates needing Steven's explicit OK (recommendation ≠ authorization)

| Gate | Applies to | The decision | Recommendation |
| ---- | ---------- | ------------ | -------------- |
| **GATE-A** | P3 + P4 | **Lazy-wire alters the live hydration path.** §2 in-silico and §3 expert-panel will fetch on scroll-approach and pop in (placeholder → content) instead of arriving eager. Visible change to perceived load on a live `/report`. | **Ship it.** It's the minimal, consistent fix and the only way to make M8/M9 show live data without undoing the M11 eager-trim perf win. Mirrors the already-shipped publications pattern exactly. |
| **GATE-B** | P4 | **M9 partial-state treatment.** Render the honest "derived from consensus, not ClinGen Evidence Repository" `role="note"` vs. suppress the §3 expert-panel slot entirely until C1 lands. | **Render the note.** Suppressing hides that an expert-panel surface exists; the note is honest about provenance and degrades gracefully. |
| **GATE-C** (flagged, no edit proposed) | P1 side-effect | **M7 premium tiles with no paid tier.** Tiles #11/#12 carry `Premium` badges (`MatrixOverture.tsx:292,307`) but there's no in-report paywall. P1 makes them *functional* (they now scroll to their host card), which may sharpen "premium with nothing behind it." | Out of scope to edit here; flag only. Decide separately: keep forward-looking or hide until a paid tier ships. |
| **GATE-D** (flagged, do NOT do under this runbook) | (none) | **Stand up a test runner in `app/web`.** There is none today. | Do NOT introduce vitest/RTL under this runbook. If wanted, scope as a separate task. The `?lazy=` + `?demo` browser hatches are the verification surface here. |

---

## §4 Risks

- **R1 — `eagerData` short-circuit hides live behaviour in `?demo`.** The RPE65 fixture
  ships full `computational_deep_dive` + `expert_panel`, so `?demo` will NEVER exercise the
  lazy fetch for P3/P4 (`LazySection.tsx:82`). You MUST verify the live path with
  `?lazy=…` (Browser B rows) — `?demo` alone gives a false green. **Mitigation:** every
  P3/P4 row has both a Browser A (offline, zero-fetch) and Browser B (`?lazy=`, one-fetch) check.
- **R2 — M9 `unwrap` returning null routes to the ERROR path, not empty.** `LazySection`
  treats a null `unwrap` result as `kind:'error'` (`LazySection.tsx:145-147`), whose
  default view is a red `role="alert"` (`:228-256`). On the live `partial` default this
  would show a false error. **Mitigation:** P4 MUST pass a custom `errorView` (and
  `emptyView` for the no-request case) rendering the `role="note"` partial note. This is
  load-bearing, not optional. The `ExpertPanelSection` component itself returns `null`
  (not an error) on null data (`ExpertPanelSection.tsx:123`), so the note must come from
  the LazySection wrapper, never the component.
- **R3 — Name clash on `ExpertPanelSection`.** It's both a component (imported
  `ReportClient.tsx:31`) and a contract type (`backend.ts:789`). P2 and P4 BOTH import the
  type — always alias it (`ExpertPanelSection as ExpertPanelSectionData`). Forgetting the
  alias is a guaranteed G1 failure. Do P2 first so the type import exists before P4 extends it.
- **R4 — Deleting `expert-panel-sample.ts` orphans nothing only if the grep held.** Verified
  sole importer is `ExpertPanelSection.tsx:9`. If P2's retype is incomplete, the delete will
  surface as a G1 "cannot find module" — that's the gate doing its job; fix the import, don't
  un-delete. Run P2's G1 BEFORE moving on.
- **R5 — Live tile→anchor mapping is a backend concern, not fixed here.** When `lookupSummary()`
  returns ≥8 live tiles (`MatrixOverture.tsx:70`), `target_section_id` comes from backend
  `call_cards` interaction targets (`lookup_sections.py:95-97`), NOT the FE synthesizer P1
  edits. P1 only hardens the offline/fallback synthesizer (what ships today). Confirm the live
  mapping with Codex (Codex lane, not blocking) — do NOT try to "fix" it in FE.
- **R6 — Dev-server hygiene.** Do not start or kill the `:3000` dev server inside this
  runbook (orphaned dev servers have corrupted `node_modules` before). Assume it's running;
  if you must start one for verification, give Steven an explicit kill-before-`/clear` note.
- **R7 — Publications call site must stay byte-identical.** P3/P4 mirror but must not touch
  the publications `<LazySection>` (`ReportClient.tsx:897-920`) — it's the working reference
  and Invariant §4.1. Copy its shape; don't refactor it.
- **R8 — `tsc` is not a package script.** G1 invokes `npx … tsc` directly against
  `app/web/tsconfig.json`. `build` uses `next build --webpack` (`package.json:7`) which also
  typechecks but is far slower; prefer the direct `tsc --noEmit` for the per-step loop and
  reserve a full `build` for a final pre-ship confidence pass if desired.

---

## §5 Done-when (whole runbook)

- [ ] All 12 M7 overture tiles scroll to a present DOM anchor; URL fragment updates (P1).
- [ ] `expert-panel-sample.ts` deleted; G1 + G2 green; no orphaned importer (P2).
- [ ] Live `/report?lazy=computational_deep_dive` → §2 shows predictor rows, one section-fetch, AlphaMissense hidden (P3).
- [ ] Live `/report?lazy=clingen_vcep` → §3 shows the honest partial note (`role="note"`, not red), one section-fetch; `ClinVarBlock`/`AcmgCriteriaFold` unaffected (P4).
- [ ] Offline `/report?demo` makes ZERO section-fetch calls and renders §2/§3 identically to today (all phases).
- [ ] GATE-A + GATE-B signed off by Steven before P3/P4 ship.
