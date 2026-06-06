# Varsome competitive milestones M7–M10 — design + ground-truth audit

> Frontend architect design doc. Surface: `app/web` (Next.js 16 App Router) `/report`.
> Created 2026-06-06 (Claude). **Design only — no application code written.**
> Companion analysis: `docs/competitive/varsome.md`. Milestone source:
> `plans/v2-redesign-impeccable.md` §10.2 / §10.9.

---

## §0 Ground-truth audit (verified against the tree, not status docs)

`ROADMAP.md` (dated 2026-05-16) is stale and was NOT trusted. Every claim below
is verified against the live `app/web` + `app/backend` source. The plan
(`v2-redesign-impeccable.md` §10.9) claims M8 "SHIPPED `6049df1`" and M7/M9/M10a
in-flight; the tree confirms all four are **built and mounted**, but two have a
**live-data wiring gap** that the plan's "SHIPPED" label hides.

### What each milestone is (quoted from `plans/v2-redesign-impeccable.md` §10.2)

- **M7** — *"Card-matrix report header above the ruled column (matrix-as-overture).
  10–12 tiles, not Varsome's 24. Each tile = section preview (title + key value +
  mini-vis) + nav anchor. URL fragments / route segments so sections are linkable
  + back-button-friendly … Mobile: horizontal-scroll band, not stacked. Tiles use
  cheap summary fields from the initial payload; detail panels lazy-load via the
  M11 section-fetch contract."*
- **M8** — *"Calibrated in-silico verdict table. Replace `InSilicoGrid` with
  composite verdict bar + per-engine table: Engine · Calibrated label · Raw score ·
  Version. Null-calibration UX: render the engine row, but the calibrated cell
  shows neutral 'No published calibration / Not calibrated' … Composite verdict bar
  aggregates only engines with an approved calibration policy. AlphaMissense stays
  in internal calibration policy/fixtures but public display stays hidden."*
- **M9** — *"ClinGen VCEP narrative + criteria chips. New report section:
  `ExpertPanel` attribution (e.g. TP53 VCEP), criteria-met / not-met chips,
  inheritance, MONDO link, 'Evidence submitted by expert' narrative, source URL +
  version + provenance. v1 scope: public ClinGen Evidence Repository API / JSON-LD
  only … no SVI-gated / private feed."*
- **M10** — split into **M10a** *"Gene-scoped publication count toggle
  (variant-vs-gene). One boolean in the publications section header."* and **M10b**
  *"Publication index v2 (net-new pipeline). PMC / Europe PMC ingestion; LLM entity
  extraction for tag-chip generation; 'Linked by:' provenance; citation counts; tag
  chips."* (M10b is a ~1-quarter Codex pipeline, out of FE scope here.)

### Status matrix

| Milestone | Status | Evidence (`file:line`) |
| --------- | ------ | ---------------------- |
| **M7** card-matrix overture | **BUILT + live-wired** | Component `app/web/components/report/MatrixOverture.tsx:55` + `MatrixTile.tsx:38`; mounted `ReportClient.tsx:687`; calls `lookupSummary()` (`lib/api.ts:132`) hitting `POST /lookup/summary` (`backend/app/api/routes/lookup.py:57`); synthesizes 12 tiles offline (`MatrixOverture.tsx:125`); deep-links via URL fragment (`MatrixOverture.tsx:42-44`); premium≠no-data treatment (`MatrixTile.tsx:24-61`, DL-017). |
| **M8** calibrated in-silico table | **BUILT, but LIVE-DATA GAP** | `CalibratedInSilicoTable.tsx:51` + `CompositeVerdictBar.tsx:20` mounted `ReportClient.tsx:737-738`; reads `payload.report_profile?.computational_deep_dive?.predictors`. Backend calibration real: `computational_calibration.py:18-35`, fields on `run.py:587-588` (`calibrated_label`, `calibration_bucket: RampVerdict`). **GAP:** `computational_deep_dive` is stripped from the default eager `/lookup` response (`lookup.py:26-34` `LOOKUP_EAGER_RESPONSE_EXCLUDE`) and the table is **NOT** lazy-wired → live renders "No in-silico predictions" (`CalibratedInSilicoTable.tsx:56-62`). Works only in the offline RPE65 fixture (ships full payload). |
| **M9** ClinGen VCEP section | **PARTIAL — built, live-data gap + cache not integrated** | `ExpertPanelSection.tsx:118` mounted `ReportClient.tsx:775`; reads `payload.report_profile?.expert_panel`; backend builder real (`variant_report_orchestrator.py:641 _build_expert_panel`, schema `run.py:489`). **GAP 1:** `expert_panel` stripped from eager `/lookup` (`lookup.py:32`); component NOT lazy-wired → returns `null` live (`ExpertPanelSection.tsx:123`). **GAP 2:** Evidence-Repository source-cache not integrated — section-fetch falls back to the ACMG worksheet with warning `clingen_vcep_evidence_repo_source_cache_not_integrated` (`lookup_sections.py:176`), status `partial`. **TYPE DRIFT:** two parallel shapes — backend `ExpertPanelSection` (`lib/backend.ts:789`) vs slimmer local `ExpertPanelData` (`expert-panel-sample.ts:50`) the component is typed against. |
| **M10a** variant-vs-gene pub toggle | **BUILT + live-wired** | `PublicationsCallout.tsx:18` (toggle `:61-78`, `?pubScope=` inbound `:20-29`) mounted inside `PubMedSection.tsx:136` (the live §6, `ReportClient.tsx:897-920`). Backend `scope_counts` real (`publication_literature.py:534`, schema `run.py:417`). Publications **correctly** lazy-wired via `LazySection.tsx` so the eager-exclude does not break it. |
| **M10b** publication index v2 | **MISSING (by design — Codex quarter)** | No PMC/Europe-PMC ingestion, tag-chip, or "Linked by:" provenance pipeline. NOT a FE deliverable; tracked Wave 5 / deferred (§10.9 M-008). |

### M11 / Tier-1 dependencies (verified — they underpin M7–M10)

- **M11 section-fetch plumbing — BUILT.** `LazySection.tsx` (IntersectionObserver
  one-shot), `fetchLookupSections()` (`lib/api.ts:143`), backend
  `lookup_sections.py` + `POST /lookup/sections`. `LookupSectionId =
  publications | computational_deep_dive | clingen_vcep` (`backend.ts:325`).
- **Tier-1 upgrades — BUILT.** `CiteChip.tsx` (mounted globally `providers.tsx:40`),
  `StackedCountBar.tsx`, `PublicationModal.tsx` (`?pub=PMID:N`), `StickyVariantRibbon.tsx`,
  `Card` `verdict` prop (left-edge accent, `ReportClient.tsx:746`), ClinVar review
  stars (`clinvar-review-status.ts`, `ClinVarBlock.tsx`).

### The one structural truth the plan obscures

The plan marks M8 "SHIPPED" and M7/M9/M10a in flight. **Reality: all four FE
components exist and three are correctly wired; M8 and M9 have a shared
live-data defect** — their payload slices are deliberately stripped by
`LOOKUP_EAGER_RESPONSE_EXCLUDE` (a perf optimization for M11 lazy loading) but
the two components were left mounted on the *eager* payload path instead of
being migrated to `LazySection` the way publications was. Net effect: **on a
real backend lookup, the in-silico table and the expert-panel block are empty.**
This is the highest-priority item in this doc. Everything else is polish.

---

## §1 Problem & goals

Per `docs/competitive/varsome.md` §9, these four milestones each close a named
competitive gap. The Eamos thesis stays "Reading Room" — close the gap *without*
adopting Varsome's Bloomberg-terminal density or its pay-to-see-the-answer gating.

| Milestone | Varsome capability | Eamos gap closed | Eamos differentiator |
| --------- | ------------------ | ---------------- | -------------------- |
| M7 | 24-tile card matrix = TL;DR + nav index (`varsome.md` §2 "strongest IA pattern") | linear-only sections; no above-fold overview | 10–12 tiles, **linkable via URL fragment** (fixes Varsome's unshareable client-only state, `varsome.md` §7) |
| M8 | ~25 calibrated in-silico predictors, composite verdict bar (`varsome.md` §5) | flat predictor cards, no calibration provenance | **honest null-calibration cell** + composite aggregates only approved-calibration engines (no fake confidence) |
| M9 | ClinGen VCEP narrative + criteria chips, expert attribution (`varsome.md` §4 #17) | no expert-panel surfacing at all | **VCEP-specific strength overrides** rendered (`§` glyph) + full provenance footer |
| M10a | variant-vs-gene publication count toggle (`varsome.md` §5) | variant-count only | toggle with honest "not available" state, no inflated gene counts |

**Goal:** make all four render real data on a live lookup, finish M9's data path,
and resolve the type drift — then layer the remaining UX polish. The components
are largely done; the work is **wiring + finishing**, not greenfield design.

---

## §2 UX / IA / flows (per milestone, with states)

### M7 — Matrix overture

Already implements the intended IA: a horizontal-scroll snap band on mobile, a
3-up (`sm`) → 4-up (`lg`) grid on desktop, sitting between `VariantHeader` and
`CallCardsGrid` (`ReportClient.tsx:687`). Each tile click smooth-scrolls to its
`target_section_id` and writes a URL fragment.

States (all present in `MatrixTile.tsx`): **clickable** (verdict/count tiles,
elev-1→elev-2 hover, keyboard Enter/Space), **classification-coloured** (ACMG
ramp when `ui_color_theme === 'classification'` and label resolves to a tier),
**premium-gated** (lock glyph + `--bg-soft2`, never grey — DL-017), **no-data**
(`--cls-na-*` grey, non-interactive).

Design refinements (polish, not gating):
1. **Tile↔section count mismatch.** The overture synthesizes 12 tiles whose
   `target_section_id`s (`gene_context_snapshot`, `evidence_by_source`,
   `clingen_vcep`, `computational_deep_dive`) do not all match the 8 numbered
   section anchor IDs in `ReportClient` (`population_frequency`,
   `evidence_by_source`, `clinical_evidence`, `gene_context`,
   `associated_conditions`, `curated_variants`, `publications`, `trials`,
   `ai_summary`). Tiles pointing at `clingen_vcep` / `computational_deep_dive`
   anchors **scroll nowhere** (no element with that id exists;
   `scrollToTile` returns early at `MatrixOverture.tsx:38`). Fix: map both
   premium tiles to `#clinical_evidence` / `#evidence_by_source`, or add the
   missing anchor divs. Verify: every tile scrolls to a real section.
2. **Mobile dots** (`CarouselDots`) already present (`MatrixOverture.tsx:102`).

### M8 — Calibrated in-silico table

**Primary work = fix the live-data gap, not redesign.** The table + composite
bar are visually complete and match the spec (Engine · Calibrated label · Raw
score · Threshold · Version; null-calibration shows italic "No published
calibration"; composite bar counts only calibrated engines).

Flow change required:
- Wrap §2's `CompositeVerdictBar` + `CalibratedInSilicoTable` in a
  `<LazySection sectionId="computational_deep_dive">` exactly as §6 publications
  is wrapped, OR have `variantLookup()` request `?include_lazy_sections=true`.
  **Recommend LazySection** (preserves the M11 perf win; matches the established
  publications pattern). `unwrap` narrows the envelope payload to
  `ComputationalDeepDiveSection`.
- States: eager (offline fixture, immediate), lazy idle/loading (placeholder),
  ready (table), error (retry), empty ("No in-silico predictions").

### M9 — ClinGen VCEP section

Component is built and renders narrative + VCEP criteria chips with strength-
override `§` markers + provenance footer (`ExpertPanelSection.tsx`). Two flows
to finish:
1. **Lazy-wire it.** Same as M8 — wrap in `<LazySection sectionId="clingen_vcep">`
   inside §3 Clinical evidence, `unwrap` → `ExpertPanelSection` (backend shape).
   Today it reads the eager (stripped) payload and renders nothing live.
2. **Source-cache integration is a Codex dependency** (see §5). Until it lands,
   the section-fetch returns `status: 'partial'` from the ACMG-worksheet fallback
   with `clingen_vcep_evidence_repo_source_cache_not_integrated`. FE should
   render a **"derived from current consensus, not the ClinGen Evidence
   Repository"** provenance note when `status === 'partial'` so the read stays
   honest. The component already has a `FreshnessChip` (`stale`) to extend.

Missing-vs-Varsome content to add when the contract is richer (post-cache):
inheritance mode + MONDO disease link (spec'd in §10.2; backend
`ExpertPanelVcep` carries `affiliation_id` but no MONDO/inheritance field yet —
§5 dep). Not-met criteria chips already supported (`state: 'not_met'`).

### M10a — Variant-vs-gene toggle

Fully wired (`PublicationsCallout.tsx`). States: **variant** (count + Scholar
link), **gene** (count + PubMed gene link), **gene-unavailable** (em-dash +
"not available right now"). Inbound `?pubScope=` honoured; clicks intentionally
do NOT push to URL (M-001 scope). One open product question (§7): should the
toggle push to URL so a gene-scoped view is shareable?

---

## §3 Visual design (within the existing system)

No new design language. All four already consume frozen tokens correctly:

- **M7 tiles** — `--cls-*` ramp for classification tiles, `--cls-na-*` for
  no-data, `--bg-soft2`+lock for premium, `--elev-1`/`--elev-2` hover, `--r-md`
  radius, `--display` for the primary value, `--mono`-free uppercase micro-label.
  Matches DESIGN.md Dashboard Interaction Language.
- **M8 table** — hairline-ruled rows, `--mono` tabular nums for score/threshold,
  `ClassificationBadge` for the calibrated bucket, `StackedCountBar` (frozen ramp
  segments, white inline numerals) for the composite bar.
- **M9 block** — flattened inside §3 (no card-in-card), `--bg-soft` block,
  criterion chips in `--r-sm` with `--mono` code, `--warn-tint` for conflicting,
  `--teal-deep` `§` override marker + "View on ClinGen" link, provenance footer
  in `--ink-4` 11px.
- **M10a** — `.eamos-toggle-btn` segmented toggle, `--mono` count, Scholar/PubMed
  jump links.

**No new tokens are required.** Two micro-additions if Steven wants them (GATED,
§6): a dedicated `--premium-*` token pair (today premium reuses `--bg-soft2`);
and an explicit "partial provenance" note style for M9 (reuse `--warn-tint`).

Serif discipline: M7 tile primary value uses `--display` at 15px — this is
**below the 24px display-only floor** (DESIGN.md §2.2 hard rule). Flag for the
serif-leak guard: either bump to a card-title size or move tile values to
`--body` 600. Recommend `--body` 600 (preserves density). (Audit finding, not a
redesign.)

---

## §4 Component plan (extend vs new, per milestone)

| Milestone | Existing to extend | New files | Net work |
| --------- | ------------------ | --------- | -------- |
| **M7** | `MatrixOverture.tsx`, `MatrixTile.tsx` | none | Fix tile→anchor mapping; move tile value off serif. |
| **M8** | `CalibratedInSilicoTable.tsx`, `CompositeVerdictBar.tsx`, `ReportClient.tsx` (§2) | none | Wrap §2 in `LazySection` + `unwrap` to `ComputationalDeepDiveSection`. |
| **M9** | `ExpertPanelSection.tsx`, `ReportClient.tsx` (§3) | none | Lazy-wire; reconcile `ExpertPanelData`↔backend `ExpertPanelSection` type (delete the local slim type, import the contract type); add partial-provenance note. |
| **M10a** | `PublicationsCallout.tsx` | none | Done. Optional: URL-push the toggle (§7). |

**No new components are needed for M7–M10a.** The deliverable is wiring +
finishing on components that already exist — a strong signal the prior waves
delivered the structure but left two integration seams open.

Type-drift resolution (M9): `expert-panel-sample.ts` defines `ExpertPanelData`
(criteria lack `assertion_level`/`source`/`warnings`) while `backend.ts:789`
defines the fuller `ExpertPanelSection`. ReportClient passes the backend type
into a component typed for the slim type (structurally tolerated today). Collapse
to one: type `ExpertPanelSection` against `backend.ts` and delete the local
duplicate (keep only the display-enum helpers).

---

## §5 Backend deps (Codex lane — flag, don't design as if present)

| # | Milestone | Dependency | Current state |
| - | --------- | ---------- | ------------- |
| 1 | M8, M9 | **Eager-exclude vs lazy-fetch contract is the live path.** FE must lazy-fetch `computational_deep_dive` + `clingen_vcep` (they are stripped from eager `/lookup`, `lookup.py:26-34`). No backend change needed — endpoints exist (`/lookup/sections`) — but **the FE+BE contract assumption must be confirmed with Codex** before wiring (CAR cadence per DL-002). | Endpoints shipped; FE not consuming them for these two sections. |
| 2 | M9 | **ClinGen Evidence Repository source-cache integration (CAR #3).** Until integrated, `clingen_vcep` returns `partial` from the ACMG-worksheet fallback (`lookup_sections.py:172-185`). Real VCEP narrative/criteria/provenance need the cache. | OPEN per §10.9 CAR table; key/record scaffolding present (`source_cache.py:25`). |
| 3 | M9 | **MONDO disease link + inheritance mode** on the expert-panel contract (Varsome parity, §10.2). Not in `ExpertPanelVcep` today. | Missing field; additive. |
| 4 | M10a | **Gene-scoped count semantics (CAR #4).** `scope_counts` shipped; confirm variant-deduped vs gene-wide-source-count and timeout/disagreement behaviour. | `scope_counts` populated (`publication_literature.py:534`); CAR #4 not yet opened. |
| 5 | M10b | Net-new PMC/Europe-PMC + LLM-tag + provenance pipeline. | Out of scope (~1 Codex quarter). |

---

## §6 Gated items (need Steven's explicit OK — recommendations are not authorization)

1. **⚠ GATED — M8/M9 lazy-wire changes the live render path.** Migrating the
   in-silico table and expert-panel block to `LazySection` is a structural change
   to how §2/§3 hydrate. It is the correct fix, but it alters perceived load
   behaviour (sections pop in on scroll). Confirm before shipping.
2. **⚠ GATED — M7 premium-gated tiles.** Two tiles render `Unlock with Premium`
   / lock glyph (`MatrixTile.tsx`). There is **no paid tier live** (`/pricing`
   exists, no in-report gating). Showing premium locks on a report with nothing
   behind the wall may mislead. Decide: keep as forward-looking placeholders, or
   hide until a paid tier ships.
3. **⚠ GATED — new `--premium-*` token + M9 partial-provenance note style.**
   Any durable token addition needs sign-off (DESIGN.md is the contract).

---

## §7 Open questions for Steven

1. **M8/M9 live-data gap — fix now or schedule?** All four milestones are marked
   shipped/in-flight, but in-silico (M8) and expert-panel (M9) render empty on a
   real lookup because their payload is eager-excluded and they aren't lazy-wired.
   Treat as a bug-fix this cycle, or as a Wave-4 (M11 full-ship) item?
2. **M7 premium tiles** — keep the two `Premium` placeholder tiles, or remove
   until a paid tier exists? (Ties to gate #2.)
3. **M10a toggle URL-push** — should toggling to gene scope update `?pubScope=gene`
   so a gene-scoped publications view is shareable? Today it's inbound-only.
4. **M9 content scope** — add MONDO disease link + inheritance mode to match
   Varsome (needs a Codex contract field), or ship VCEP narrative + criteria only
   for v1?
5. **M9 partial-state honesty** — when `clingen_vcep` is `partial` (cache not
   integrated), render the section with a "derived from consensus, not ClinGen
   Evidence Repository" note, or suppress the section entirely until the real
   cache lands? (Suppressing avoids implying VCEP authority we don't yet have.)
