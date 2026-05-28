# Archived Claude — Last Task & Resume section

Source: `agent_handoff/CURRENT.md` `## Claude — Last Task & Resume`
Archived: 2026-05-29 03:47 +1000 · Claude
Reason: replaced at major boundary after LazySection v1 ship (commit `244ba62`).
Per Hard Rule 9 of `agent_handoff/README.md`: prior section content is
preserved verbatim here so the replacement does not lose history.

Note: between this archived section's stamp (2026-05-28 02:56 +1000) and
the replace, additional Claude work landed in commits but **was not yet
folded back into a fresh Claude — Last Task & Resume narrative**:
- mobile sweep batch 1 (`013b319`)
- M-005 path exercised — `4753042`
- M-006 / M10a publication callout `00b30c2`
- Phase 2 branch rename + service flip (Active Status heartbeat IDLE @
  2026-05-29 01:25 +1000 captured the operational detail there)
- README Hard Rule 10 codified (`5c9cc68`)
- LazySection v1 ship (`244ba62`) — this archive's trigger.

The Active Status heartbeat at the top of `CURRENT.md` and the per-commit
messages remain authoritative for those intervening sessions; this archive
preserves the pre-2026-05-28 02:56 narrative content for reference.

---

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 1/2).
Section last edited: 2026-05-28 02:56 +1000 · Claude. Prior section
(2026-05-28 01:31 +1000 · CAR #2 OPEN + landing token polish) archived
verbatim to `agent_handoff/archive/2026-05-28-claude-section-pre-m4-ship.md`
per Hard Rule 9. Full incremental detail in
`~/.claude/plans/next-session-eamos.md`.

**Session 2026-05-28 (very late) — M-004 / M8 SHIPPED end-to-end (`6049df1`) · §10.9 plan flip (`33ddb04`) · parallel-safe MetricBelt live-specimen (`ac1f598`). 8 Claude commits this session total, 11 total ahead of origin since the prior push gate. CAR #2 CLOSED end-to-end.**

Branch `checkpoint/v2-batches-2026-05-17`. Origin at `eb98f8b`; local **11
ahead of origin**: `472a7c3` → `376b736` → `f2962b7` (prior-session) →
`51dfed5` (M-003 live-wire) → `beb81b0` (ClinVar surface) → `c546901`
(M3.6 submitter half) → `01fc466` (landing token polish) → `84c93bd`
(CAR #2 docs) → **`6049df1` (M-004 FE ship-then-rip)** → **`33ddb04`
(§10.9 plan flip)** → **`ac1f598` (MetricBelt live-specimen)**.
**Not pushed** — push remains gated. Codex's uncommitted backend WIP
(FGV-001 full-locus contract per their 02:41 release, CAR #2 fixtures, +
the byte-identical backend.ts mirrors) untouched on the worktree; no
Codex files ever staged (DL-019 honoured on all 8 commits).

**This-slice closes (3 commits since the prior heartbeat at 01:31):**

1. **`6049df1` — `feat(web): M-004 calibrated in-silico ship-then-rip (DL-021)`.** Consumes Codex's CAR #2 backend (delivered 02:06): `calibrated_label` / `calibration_bucket` (RampVerdict 5-tier) / `calibration_method` / `calibration_version` on each `ComputationalPredictorRow` in `ReportPayload.report_profile.computational_deep_dive.predictors`. Built `CalibratedInSilicoTable` (5-col: Engine · Calibrated label = `ClassificationBadge` on `calibration_bucket` + raw `calibrated_label` text + `calibration_method` · Raw score · Threshold · Version; null bucket = neutral "No published calibration" with raw score + version still visible) + `CompositeVerdictBar` (StackedCountBar wrapper aggregating only non-null buckets, "{N} of {M} engine(s) calibrated" micro-label). Mounted in `ReportClient` §2 above `EvidenceTable`. **`InSilicoGrid` removed end-to-end** (mount + import + file). `report-tsv.ts` / `report-html.ts` consume `payload.in_silico_predictions` directly so copy/export pipelines are unchanged. AM filtered at render in both new components per [[project_alphamissense_plan]] (two `.filter(p => p.name !== 'AlphaMissense')` calls — one-line revert each). RPE65 validates: SpliceAI 0.94 → VUS, REVEL → LP, CADD PHRED → VUS, PrimateAI-3D + MetaLR → null (no policy) render as the neutral cell.

2. **`33ddb04` — `docs(plan): M-004 / M8 + CAR #2 → SHIPPED in §10.9 wave table`.** Plan flip only — `plans/v2-redesign-impeccable.md` §10.9 wave table now marks M-004 / M8 / CAR #2 as SHIPPED / [DONE].

3. **`ac1f598` — `refactor(web): MetricBelt live-specimen — drive from RPE65 report payload`.** Parallel-safe parking slice (shipped while Codex held the FGV-001 Log Edit-Lock 02:19–02:41). `app/web/components/landing/MetricBelt.tsx` previously rendered a hand-crafted `SPECIMEN` constant with an LP-flavoured RPE65 call-card set; backend now emits a VUS call (same drift `sample-report.ts:6-10` already flagged for the report sample itself). Refactor pulls four cards + variant header from `RPE65_SAMPLE.report_payload.call_cards.cards` + `variant_summary_rows[0]` (read-only via the existing typed `sample-report.ts` import). Same policy as `CallCardsGrid`: `SUPPRESSED_WARNINGS = {alphamissense_on_hold}`, top-3 badge slice, warning-or-meta footer, identical `BADGE_TONES` map. Pure FE; no contract change; tsc clean. Landing specimen now in lockstep with what `/report` actually renders for the canonical RPE65 demo. MetricBelt drops off the parked-list.

**CAR #2 — M-004 / M8 calibrated-predictor fields — CLOSED end-to-end.**
- Opened by Claude 2026-05-28 01:31 +1000 (`84c93bd`).
- Closed by Codex 2026-05-28 02:06 +1000 with centralized policy in `app/backend/app/services/computational_calibration.py` (REVEL / CADD PHRED / canonical PrimateAI use Pejaver 2022 / ClinGen SVI PP3/BP4; SpliceAI uses Walker 2023 / ClinGen SVI splicing; MetaLR + PrimateAI-3D return explicit null). Codex's verification: focused CAR #2 pytest + full backend pytest + Ruff + Black + both frontend tsc all green.
- FE shipped by Claude 2026-05-28 02:29 +1000 (`6049df1`); already marked [DONE] in `## Cross-Agent Requests` (line 1451).

Verified:
- `cd app/web && ./node_modules/.bin/tsc --noEmit` silent after `6049df1` and again after `ac1f598`.
- DL-019 honoured on all 8 commits this session — explicit `git add -- <paths>`; staged file list verified before each commit (no Codex backend WIP swept).
- Browser smoke deferred — visual deltas (§2 `CompositeVerdictBar` above the calibrated table + the landing `MetricBelt` swap from LP-flavoured mock to live VUS) queued for next push + Vercel preview.

**Wave status (refreshed):**
- **Wave 1** — M-001 + M-003 + M3.6 all COMPLETE. **M3 fully closed this slice** via the M-004 ship-then-rip (DL-021).
- **Wave 2 (collapsed)** — Done (Codex M11 contract sketch `9a3d3a6` + Claude TS mirror `d0f4eae`).
- **Wave 3 (parallel)** — M7 live-wired (`51dfed5`); **M8 FE SHIPPED this slice (`6049df1`); CAR #2 CLOSED end-to-end**; M9 / M10a unstarted (each opens its CAR at slice start per DL-002).
- **Wave 4 / 5** — unchanged from §10.9.

**Coordination invariants (DL-019 + DL-002):** every Claude commit explicit-pathspec only — 8 commits this session, all honoured. CARs open per-slice, never batched up-front; CAR #2 closed end-to-end this slice and there is currently **no open CAR**. M5 Workbench decoupled — Codex's FGV-001 release at 02:41 is the BE contract for that lane (FE consumer surface waits for FGV-002 fixture/source hydration; calling the `window.kind="full_gene"` path before that would hit the fail-closed runtime guard Codex wired). AskEamos COMING SOON. AlphaMissense hidden in public display — the filter now lives at three render sites (`MetricBelt` + `CalibratedInSilicoTable` + `CompositeVerdictBar`); re-enable = remove the three filters, one-line revert each.

**Open / next-session (priority order):**
1. **M-005 / M9 ClinGen VCEP narrative + criteria chips** — opens **CAR #3** at slice start. Codex's preferred CAR #3 framing (per 02:58 +1000 reply): **exact source identity/keying requirements for ClinGen VCEP/EREP, expected response fields, cache freshness/provenance needs, and which report section consumes it first.** (Public ClinGen Evidence Repository → provider-backed source-cache; keyed on CAID / ClinVar VID / normalized HGVS+gene.)
2. **M-006 / M10a gene-scoped publication count toggle** — opens **CAR #4** at slice start. Codex's preferred CAR #4 framing (per 02:58 +1000 reply): **exact gene-count semantics for publication scope, whether count is variant-deduped vs gene-wide source count, and what should happen when live sources disagree or time out.** (`PublicationsCallout`'s gene toggle is already wired with "Loading…" placeholder + inbound `?pubScope=` URL param.)
3. **M5 Workbench Phase 2** — decoupled lane; Codex's FGV-001 (`window.kind="full_gene"` + optional `GeneViewerResponse.full_locus` + projection/range/codon/feature interval models + rendering hints) is the BE contract. FE consumer surface waits for FGV-002.
4. **Parallel-safe landing items still parked** (MetricBelt now DONE → removed): HowItWorks + FeaturesGrid de-templated (asymmetric/editorial — next visual win); legal pages onto warm surface + composed nav + breadcrumb; /account browser-verify; per-metric copy buttons; re-render `feat-report-cards.webp` without baked-in "alphamissense on hold" text; formal `audit` + `quality-reviewer` gates for M2 / M3.

**Resume prompt:**
`# Resume prompt · 2026-05-28 02:56 +1000 · Claude (M-004 FE SHIPPED `6049df1` + §10.9 plan flip `33ddb04` + MetricBelt live-specimen `ac1f598`; CAR #2 CLOSED end-to-end; CURRENT.md major-boundary swap landed)`
`Eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE — full state + queue), agent_handoff/README.md (protocol), agent_handoff/CURRENT.md (## Log Edit-Lock + ## Active Status + ## Claude + ## Cross-Agent Requests — no open CARs as of this stamp), agent_handoff/DECISIONS.md, agent_handoff/RISKS.md, plans/v2-redesign-impeccable.md §10 + §10.9, then git status --short --branch && git log -11 --oneline.`
`Branch checkpoint/v2-batches-2026-05-17. Origin at eb98f8b; local 11 ahead (472a7c3 / 376b736 / f2962b7 prior + 51dfed5 / beb81b0 / c546901 / 01fc466 / 84c93bd / 6049df1 / 33ddb04 / ac1f598 this session). NOT pushed. Codex backend WIP uncommitted in worktree (FGV-001 full-locus contract per their 02:41 release + CAR #2 fixtures + byte-identical backend.ts mirrors), untouched.`
`Delta tail this slice: 6049df1 = feat(web) M-004 calibrated in-silico ship-then-rip (DL-021); 33ddb04 = docs(plan) §10.9 flip; ac1f598 = refactor(web) MetricBelt live-specimen — drive from RPE65 report payload (parallel-safe parking item shipped while Codex held the FGV-001 lock 02:19–02:41). M3 fully closed.`
`Next priority: (1) M-005 M9 ClinGen VCEP — opens CAR #3 at slice start; (2) M-006 M10a gene-scoped pub count — opens CAR #4 at slice start; (3) M5 Workbench Phase 2 (Codex FGV-001 is its BE contract; FE consumer waits for FGV-002). Parallel-safe landing parked (MetricBelt now DONE): HowItWorks/FeaturesGrid de-template, legal warm surface, /account browser-verify, per-metric copy buttons, feat-report-cards.webp re-render.`
`Guardrails: no /runs, AlphaMissense display (filtered at 3 render sites now), Codex backend lane (app/backend/**), destructive git, push without OK. DL-019 honoured all 8 commits. Inline > sub-agents for integration ([[feedback_inline_over_subagents_eamos]]). AskEamos COMING SOON ([[feedback_askeamos_parked]]). Mobile-nav no-blur preserved. End clear-safe.`

---

### Archived prior session narratives

Earlier narratives:
- 2026-05-28 01:31 +1000 (CAR #2 OPEN + landing token polish) → `agent_handoff/archive/2026-05-28-claude-section-pre-m4-ship.md`
- 2026-05-28 00:41 +1000 (M-003 live-wire + ClinVar surface + M3.6 submitter half) → `agent_handoff/archive/2026-05-28-claude-section-pre-car2-landing.md`
- 2026-05-27 23:55 /planner persist + 2026-05-27 21:50 rich-HTML copy + Workbench pass-2 slice 2 → `agent_handoff/archive/2026-05-28-claude-section-pre-m3-live-wire.md`
