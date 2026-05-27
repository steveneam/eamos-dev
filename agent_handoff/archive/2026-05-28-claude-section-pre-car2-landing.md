# Archived Claude section — CURRENT.md (pre-CAR #2 + landing slice replace)

Archived 2026-05-28 01:31 +1000 (Claude). Replaced per README Hard Rule 9 +
Hard Rule 1 (append+archive verbatim before replacing). Successor section:
CAR #2 OPEN + landing slice `01fc466` shipped.

---

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 1/2).
Section last edited: 2026-05-28 00:41 +1000 · Claude. Prior section
(2026-05-27 23:55 /planner persist + the carried 2026-05-27 21:50 rich-HTML
copy payload `fdfa9c9` + Workbench pass-2 slice 2 `fe9e3b4`) archived
verbatim to
`agent_handoff/archive/2026-05-28-claude-section-pre-m3-live-wire.md` per
Hard Rule 1. Full incremental detail in `~/.claude/plans/next-session-eamos.md`.

**Session 2026-05-28 (early) — M-003 live-wire + ClinVar surface slice. 2 Claude commits this session.**

Branch `checkpoint/v2-batches-2026-05-17`. Origin at `eb98f8b`; local
**5 ahead of origin**: `472a7c3` (prior-session Wave-1 batch 2) → `376b736`
(prior-session M-003 integration) → `f2962b7` (prior-session M7 scaffold) →
`51dfed5` (this session M-003 live-wire) → `beb81b0` (this session ClinVar
surface slice). **Not pushed** — push remains gated. Worktree carries
Codex's uncommitted backend WIP only (Task 12 / Tasks 13-14 / 0007 RLS /
M11 contract sketch / PROGRESS / v2-backend), untouched.

Commits (oldest → newest):

- `51dfed5` **M-003 live-wire — MatrixOverture fetches `lookupSummary()`
  with mock fallback.** `ReportClient` builds a `LookupRequest` from the
  same URL params it sends to `variantLookup()` (demo / sample stays
  undefined → mock-only) and threads it through `ReportBodyProps.summaryRequest`
  to `MatrixOverture`. The overture renders its synthesized tiles
  immediately, fires `lookupSummary(request)` in a `useEffect`, and swaps
  in `response.tiles` when non-empty. `TypeError` (backend unreachable)
  stays mock — same shape as `designPrimers` / `designGuides`; other
  errors stay mock and `console.warn` for debug. Codex's M11 contract
  sketch (lineage `9a3d3a6`) already serves `/api/v1/lookup/summary`, so
  no backend change required. Files: `app/web/components/report/MatrixOverture.tsx`,
  `app/web/components/report/ReportClient.tsx`.
- `beb81b0` **ClinVar surface slice — mount `ClassificationBadge` +
  reviewStars in EvidenceTable.** New `app/web/lib/clinvar-review-status.ts`
  maps the 6 canonical ClinVar review-status strings to 0-4 stars
  (`practice guideline` → 4★ down through `no assertion criteria provided`
  → 0★). `EvidenceTable.tsx` detects the `clinvar` row, renders a small
  `ClinVarHeader` strip above the flat key:value list with
  `<ClassificationBadge classification={summary.classification} reviewStars={...} />`
  + the raw review-status text, and passes `CLINVAR_HEADER_KEYS` skip set
  to `renderSummaryValue` so `classification` + `review_status` don't
  duplicate. **Mounts the deferred M3.5** (`ClassificationBadge.reviewStars`)
  on a ClinVar-specific surface — the existing VariantHeader badge stays on
  the merged Eamos ACMG verdict (correct attribution). Files:
  `app/web/lib/clinvar-review-status.ts` (new),
  `app/web/components/report/EvidenceTable.tsx`.

Verified:
- `cd app/web && ./node_modules/.bin/tsc --noEmit` silent after each
  commit.
- DL-019 honored on both commits — explicit `git add -- <paths>` only;
  staged file list verified before commit.
- Browser smoke deferred (pre-existing orphan dev server PID 41072 —
  Steven's "do NOT kill"). tsc-clean + targeted code review covered the
  static-correctness surface; visual smoke is queued for the next push
  + Vercel preview pass.

**Deferred from M3 brief — now fully closed (post-`c546901`):**
- ~~StackedCountBar ClinVar submitter half (other half of M3.6).~~ **DONE
  2026-05-28 01:08 +1000** — Codex closed CAR #5 backend at 01:01 by adding
  additive `summary.submitter_counts` to `app/backend/app/tools/clinvar.py`
  (fixture exposes `{ "VUS": 1 }` for RPE65; live mode derives from
  `submitter_classifications` with aggregate fallback; unsupported / no-hit
  / conflicting → `{}`). Claude's `c546901` (this session) mounts
  `StackedCountBar` inside `ClinVarHeader` reading the dict with a
  defensive `readSubmitterCounts` narrowing helper.

**Wave status (refreshed):**
- **Wave 1** — M-001 components COMPLETE (prior session); M-003
  integration now 8/8 mounted (ClinVar surface + submitter half both
  this session); M3 closure complete pending the M-004 ship-then-rip
  swap of the InSilicoGrid intermediate strip (DL-021).
- **Wave 2 (collapsed)** — Done (Codex M11 contract sketch `9a3d3a6` +
  Claude TS mirror `d0f4eae`).
- **Wave 3 (parallel)** — M7 scaffolding COMPLETE (prior session); **M7
  live-wired this session `51dfed5`**; M8 / M9 / M10a unstarted, each
  opens its CAR (#2 / #3 / #4) at slice start per DL-002.
- **Wave 4 / 5** — unchanged from §10.9.

**Coordination invariants (carry forward, DL-019):** every Claude commit
uses explicit `git add -- <paths>` only — verified honored on `51dfed5`
+ `beb81b0`. Codex's uncommitted backend WIP (Task 12 clinvar_local /
Tasks 13-14 dbSNP+RepeatMasker / 0007 RLS / M11 contract sketch /
PROGRESS / v2-backend) was never staged. M5 Workbench redesign stays a
decoupled separate lane. AskEamos stays COMING SOON. AlphaMissense stays
hidden in public display.

**Open / next-session (priority order):**
1. **M-004 / M8 calibrated in-silico table** — opens CAR #2 at slice
   start (additive `calibrated_label`, `calibration_bucket`,
   `calibration_method`, `calibration_version` on existing predictor
   rows). Builds `CalibratedInSilicoTable` + `CompositeVerdictBar`,
   replacing InSilicoGrid's per-row strip (DL-021 ship-then-rip — the
   intermediate `StackedCountBar` strip stays until M-004 lands).
2. **M-005 / M9 ClinGen VCEP narrative + criteria chips** — opens
   CAR #3 at slice start (public ClinGen Evidence Repository →
   provider-backed source-cache; keyed on CAID / ClinVar VID /
   normalized HGVS+gene).
3. **M-006 / M10a gene-scoped publication count toggle** — opens
   CAR #4 at slice start. `PublicationsCallout`'s gene toggle is
   already wired with "Loading..." placeholder + inbound `?pubScope=`
   URL param.
4. **M5 Workbench Phase 2** — decoupled lane unblocked from `fe9e3b4`.
5. **Parked / lower priority**: per-metric copy buttons; re-render
   `feat-report-cards.webp` without baked-in "alphamissense on hold"
   text; §6 landing backlog; formal `audit` + `quality-reviewer` gates
   for M2 / M3.

**Resume prompt:**
`# Resume prompt · 2026-05-28 00:41 +1000 · Claude (M-003 live-wire + ClinVar surface; 2 commits this session, 5 total ahead of origin)`
`Eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE — full state + queue), agent_handoff/README.md (protocol), agent_handoff/CURRENT.md (## Log Edit-Lock + Active Status + ## Claude + ## Cross-Agent Requests — CAR #5 ClinVar submitter_counts is OPEN), agent_handoff/DECISIONS.md, agent_handoff/RISKS.md, plans/v2-redesign-impeccable.md §10 + §10.9, then git status --short --branch && git log -9 --oneline.`
`Branch checkpoint/v2-batches-2026-05-17. Origin at eb98f8b; local 5 ahead (472a7c3 / 376b736 / f2962b7 prior + 51dfed5 / beb81b0 this session). NOT pushed. Codex backend WIP uncommitted in worktree, untouched.`
`Delta: 51dfed5 live-wires MatrixOverture to lookupSummary() with TypeError-fallback to synthesized mock tiles (LookupRequest mirrored from ReportClient's variantLookup payload + forwarded via ReportBodyProps.summaryRequest); beb81b0 mounts deferred M3.5 reviewStars on a ClinVar-specific ClassificationBadge inside EvidenceTable, with the canonical 6-string review-status→stars mapping in lib/clinvar-review-status.ts and the flat key:value list de-duped via CLINVAR_HEADER_KEYS skip set. CAR #5 opened for the deferred StackedCountBar submitter half (additive submitter_counts on ClinVar summary).`
`Next priority: (1) M-004 M8 calibrated in-silico — opens CAR #2 at slice start; (2) M-005 M9 ClinGen VCEP — opens CAR #3 at slice start; (3) M-006 M10a gene-scoped pub count — opens CAR #4 at slice start; (4) mount StackedCountBar submitter half once CAR #5 lands; (5) M5 Workbench Phase 2 decoupled lane.`
`Guardrails: no /runs, AlphaMissense display, Codex backend lane (app/backend/**), destructive git, push without OK. DL-019 honored both commits. Inline > sub-agents for integration ([[feedback_inline_over_subagents_eamos]]). AskEamos COMING SOON ([[feedback_askeamos_parked]]). End clear-safe.`

---

### Archived prior session narratives

Earlier narratives (2026-05-27 23:55 /planner persist + 2026-05-27 21:50
rich-HTML copy + Workbench pass-2 slice 2) live verbatim in
`agent_handoff/archive/2026-05-28-claude-section-pre-m3-live-wire.md` per
Hard Rule 1.
