> ARCHIVED 2026-07-15 11:19 UTC by Codex - the stale task queue was superseded
> by `agent_handoff/CURRENT.md -> Next Action`. Original content follows
> verbatim.

---

# Agent Task Queue

## How To Use

Use this file for live task coordination only. Keep detailed implementation
plans in `plans/*`.

Each task should name:

- owner
- file scope
- status
- verification
- whether another agent may work in parallel

## Current Candidate Tasks

Section edited: 2026-06-22 00:18 +1000 - Codex.

| Task | Suggested owner | Status | Notes |
| ---- | --------------- | ------ | ----- |
| Post-M9 flip readiness phases | Direct Codex | ACTIVE | Durable phased task plan recorded in `docs/post-m9-flip-readiness/plan.md`. Phase 0 M9 flip is complete/stable; Phase 1 Task 1.1 M3 clinical source import preflight is locally complete. Next is Task 1.2 live M3 import only after Steven/operator approval. |
| Direct-Codex workflow doc sync | Claude Code | DONE 2026-05-17 | Stable docs corrected; memory synced. |
| Checkpoint commit + push | Claude Code | DONE 2026-05-17 | `9a27ef0` on `checkpoint/v2-batches-2026-05-17` (pushed); `origin/main` preserved. |
| Review + refactor Claude's folders | Direct Codex | DONE 2026-05-17 | Behavior-preserving lint/type/refactor pass on FE-5.5 frontend surface. Verified: vitest 24/24, frontend build clean, frontend contract 40/40, eslint clean. Committed separately as `Refactor Workbench frontend surface`, not pushed at handoff time. |
| FE-5.6 Workbench viewer refinement | Claude Code | Ready after Codex review | Decisions locked in `plans/v2-frontend.md` "FE-5.6". Runs before FE-6 (shares chrome). |
| FE-6 Primer + CRISPR panels | Claude Code | Gated | Build against frozen stub contracts only after user chooses to proceed. |
| FE-7 Alignment + Comparator | Claude Code | Gated | Stub data exists; wait for user direction. |
| FE-8 AskEamos pill | Claude Code, possible small Codex backend review | Gated | Can ship against mock `/api/v1/chat`; live chat is M-002. |
| M-002 real engines | Direct Codex | M-002A/B/C + optional local isPcr specificity + M-002D local deterministic CRISPR DONE 2026-05-17; M-002I planned/gated | Sequence context boundary, Workbench service extraction, real Primer3 primer provider, exact resolved-template specificity screen, opt-in local UCSC `isPcr` whole-genome specificity provider, and backend-only local deterministic SpCas9 CRISPR provider are implemented and backend-verified. M-002I post-CRISPR TIDE analytics, DeepHF weights, genome-wide Bowtie/BWA off-targets, raw sequence/genomic-region fields, and persistence remain separate approvals. |
| Gene viewer real-data contract | Direct Codex first, Claude for frontend integration | BACKEND/LIVE PARTIAL 2026-06-01 | Backend route `POST /api/v1/viewer` is verified locally and live for curated RPE65 full-gene `full_locus` payloads. Vercel Workbench Full gene mode renders RPE65 on desktop, but default window mode still falls back while SG hg38 runtime materialization is missing, and mobile Full gene has body-level horizontal overflow. Frontend/mobile polish remains Claude-owned unless Steven redirects. |
| Backend/API/pipeline task | Direct Codex | Available when scoped | Direct Codex now has verified access and can own meaningful backend work. |
| gnomAD population-frequency backend (CAR — Claude→Codex 2026-05-31 18:18 +1000) | Direct Codex | BACKEND DONE 2026-05-31; Claude FE migration DONE 2026-05-31 23:14; ready for Steven's commit gate | Codex delivered items 1/2 plus item 4/5 alignment backend-side, then item 3 after Claude finalized field names: per-group XX/XY, cohort overall total/XX/XY, optional per-group `exome`/`genome`, optional `overall.total.exome`/`.genome`, schema/report builder, RPE65 fixture, tests, and both `backend.ts` mirrors. Parallel-safe boundary remains: Codex owns `app/backend/**`; Claude owns `app/web/**`. |
| Source asset private Storage upload/runtime gate | Direct Codex | DONE TO PERSISTENT-DISK GATE 2026-06-01; pushed in `0f9396f` + hotfixed in `d60a748`/`7305fab` + hardened in live `189a01b` | Steven raised the Supabase project/global and private bucket limits to 50 GiB and configured local S3 credentials. Codex added hardened S3 multipart upload tooling, uploaded dbSNP and phyloP assets plus manifests to private `eamos-source-assets`, verified remote sizes match local files, and fixed/deployed SG source-asset lookup regressions. Windows checksum preflight and Linux WSL native proof now validate all 10 Tier 1/2/3 noncommercial sources to the persistent-disk gate. Current hg38+Pfam gate recommends 15 GB; full noncommercial tier stack recommends 60 GB. |
| Protein View runtime enablement | Direct Codex + Steven ops approval | GATED | Backend route `POST /api/v1/protein/annotate` exists and SG fail-closes with `protein_annotation_disabled`. Treat Protein View as not launch-ready until Render persistent/runtime Pfam materialization is approved, checksums/indexes are verified in the SG web-service runtime, provider-cache reports ready, and `PROTEIN_ANNOTATION_ENABLED` is enabled in a coordinated deploy. |
| Functional Evidence E1 dedicated PubMed stream | Direct Codex | PLANNED after current uncommitted slice settles | Add a dedicated USE_REAL_APIS-gated, cached, bounded, fail-closed Entrez search for functional assay PMIDs and feed results into `_FunctionalEvidenceCollector`. Dependency: surface resolved protein changes such as USH2A `p.Cys759Phe` before firing the strongest query term. E1 is recall-only and must not change `state`/verdict logic. |
| `eamos_press` truth-printer CLI | Direct Codex | DONE 2026-06-01, uncommitted | Implemented pure claim-provenance evaluator, `python -m app.cli.eamos_press`, in-process lookup evidence tap, assertion exits, demo audit, and `--input-file` batch output for 100-variant stacks. Verification logged in `PROGRESS.md` Session 103. |
| Cross-agent review | Opposite of implementer | Available when useful | One agent implements; the other reviews for regressions, missing tests, and contract drift. |

## Functional Evidence E1 - Dedicated Stream-3 PubMed Functional Query

Claude relay accepted by Codex 2026-06-01 19:50 +1000. Steven confirmed the
current conflict rule: ClinVar is a valid standalone source, so
`PS3 - via ClinVar` is not a conflict. Conflict only means ClinGen and ClinVar
actively disagree. Current `_display_metrics` behavior already matches this;
no code change is needed for the accepted six-state slice.

Planned enhancement E1, tracked in `plans/functional-card/spec.md`:
- Today Stream 3 re-filters PubMed articles already present in the payload or
  evidence map. That makes the functional-study count an honest floor because
  functional-assay papers that rank low in the general publication query can be
  missed.
- Add a dedicated live PubMed functional query using bounded Entrez `esearch`:
  `"{GENE} AND {aa_change} AND (functional assay OR luciferase OR western blot OR activity OR expression OR patch-clamp OR splicing OR minigene OR enzyme activity OR in vitro OR rescue)"`.
- Feed returned PMIDs into the same `_FunctionalEvidenceCollector` so they
  dedupe by PMID against ClinGen/ClinVar and existing PubMed hits.
- Requirements: bounded result size, cached with provenance, fail-closed,
  `USE_REAL_APIS` gated, and reuse EP-VLEx fetch plumbing.
- Dependency first: surface resolved protein changes already derivable from
  `molecular_context`; USH2A currently derives `p.Cys759Phe` but renders
  `protein_change=null`, which weakens the E1 query.
- E1 is recall-only. It can raise `study_count_badge_text`, but it must not
  change `state`, `verdict_source`, PS3/BS3 choice, or conflict logic.

## gnomAD PopFreq — Codex Action Required (Claude→Codex, 2026-05-31 18:18 +1000)

The `/report` gnomAD PopulationFrequencySection FE redesign is complete and UNCOMMITTED
(Claude owns `app/web/**`). It is built + seeded against data the backend doesn't expose
yet. FE contract types for 1–2 are already in `app/web/lib/backend.ts` — MATCH names in
`app/backend/app/schemas/run.py`. Full detail in Claude's `~/.claude/plans/next-session-eamos.md`
("BACKEND / CODEX COORDINATION"). Parallel-safe (disjoint: backend vs `app/web`).

1. **Per-group XX/XY.** `PopulationFrequencySexCell {allele_frequency, allele_count,
   allele_number, homozygote_count}`; `PopulationFrequencyVisualGroup.xx?/.xy?`. `gnomad.py`:
   XX/XY are already in the GraphQL `populations` array (ids `XX`,`XY`,`afr_XX`…) but dropped
   by `CORE_GENETIC_ANCESTRY_GROUPS` (`_genetic_ancestry_groups`, ~line 140). Parse
   `<grp>_XX`/`<grp>_XY` → `group.xx/xy`. Do NOT add XX/XY rows to `visual_groups` (drives the
   map). Add XX/XY to `fixtures/tools/gnomad_fixtures.json`.
2. **Cohort overall.** `PopulationFrequencyReportSection.overall? : {total?, xx?, xy?}`
   (`PopulationFrequencyOverall`). Parse cohort `XX`/`XY` + top-level ac/an/af/homozygote_count.
3. **Exome/Genome "Include" checkboxes on the group-frequency table/map** (gnomAD-style). FE
   not built yet; backend-gated. Stop collapsing via `_select_sequencing_type`; expose per-group
   exome AND genome cells separately `{af,ac,an,hom}` + per-dataset cohort totals. Claude will
   finalize the FE contract names before wiring.
4. **Age distribution — carriers, both tracks.** FE renders 4 charts (exome/genome × variant
   carriers/all individuals). Confirm `gnomad.py` fills `detail.age_distributions` with BOTH
   exome AND genome carrier histograms (all-individuals already via
   `GNOMAD_V4_ALL_INDIVIDUAL_AGE_DISTRIBUTIONS`); FE degrades to "not reported" per missing track.
5. **Warning-key alignment (minor).** FE has plain-language copy for the real keys
   (`allele_number_unavailable`, `genetic_ancestry_groups_unavailable`,
   `age_distribution_unavailable`, `age_distribution_scope:*`,
   `per_genetic_ancestry_age_distribution_not_available`, `allele_frequency_unavailable`,
   `population_frequency_detail_unavailable`) PLUS a seeded-only `low_allele_number_cohorts`
   (NOT emitted today — emit that exact key if you want a low-AN note). Unmapped keys fall back
   to prettified text.
6. **(Parked follow-up) Gene-specific BS1/PM2 thresholds (FAF95)** — Franklin-style per-gene
   thresholds vs the current fixed bands (5/1/0.1%). Steven chose "plan as follow-up." Not now.

Ping field names; Claude re-verifies the FE renders. (Heads-up: Claude's heartbeat in
`CURRENT.md ## Active Status` is stale at the `47d78c2` T1–T4 anchor — current state is this
PopFreq redesign, FE-complete/uncommitted, next = `/impeccable` on the world map.)

Codex update 2026-05-31 19:49 +1000: backend delivered items 1 and 2, verified
item 4 remains populated for both exome/genome carrier tracks where source data
exists, aligned warning keys without adding a low-AN emission, and mirrored the
additive TypeScript contract in `app/frontend/src/lib/backend.ts`. Item 3 is
not implemented because Claude explicitly deferred final field names for the
exome/genome include-checkbox contract; item 6 remains a parked follow-up.

Claude update 2026-05-31 22:08 +1000 — CAR item 3 field names FINALIZED (ready for Codex).
Steven's commit is HELD at the gate until item 3 lands, so the whole gnomAD PopFreq contract
(backend schema + BOTH `backend.ts` mirrors + FE) ships as ONE coordinated commit. The FE
(`PopulationFrequencySection.tsx`) is already built for item 3 but uses LOCAL types; it
migrates to the shared contract once Codex lands the names below.

Contract (additive, all optional; backend-led — Codex authors into `schemas/run.py` + BOTH
`backend.ts` mirrors, kept byte-identical):
- New cell type, reusing the existing 4-field shape (same as `PopulationFrequencySexCell`):
  `PopulationFrequencyDatasetCell { allele_frequency, allele_count, allele_number,
  homozygote_count }`.
- Per group — `PopulationFrequencyVisualGroup` gains optional `exome?` and `genome?` (each a
  `PopulationFrequencyDatasetCell`). The EXISTING flat group fields (af/ac/an/hom) STAY =
  joint (exome+genome combined). Do NOT add exome/genome rows to `visual_groups`.
- Cohort overall — `PopulationFrequencyOverall.total` gains optional `exome?` / `genome?`
  (same cell shape). `total` flat fields STAY = joint.
- NOT in scope: per-dataset XX/XY sex split (separate follow-up — inspector XX/XY stay joint).

Backend (`gnomad.py`): stop collapsing to one sequencing type via `_select_sequencing_type`
for these cells — emit per-group exome AND genome cells separately + per-dataset cohort
totals; keep the flat fields = joint. Add exome/genome cells to the RPE65 entry in
`fixtures/tools/gnomad_fixtures.json` so offline/demo renders. Update `test_gnomad_tool.py`
and `test_frontend_contract.py`.

FE consumer behavior (so the contract matches): "Include ☐ Exomes ☐ Genomes" — both on →
joint (flat); only exome → `group.exome` (fall back to flat if absent); only genome →
`group.genome`; at least one always on.

Lane/guardrails: Codex owns `app/backend/**` + BOTH `backend.ts` mirrors (keep
`test_frontend_backend_ts_mirrors_are_byte_identical` green). Do NOT touch
`app/web/components/**` or any `app/web/**` renderer (Claude's). Additive only; don't regress
items 1/2/4/5. No commit/push (Steven's gate). Verify: focused gnomAD/contract pytest + full
backend pytest, Ruff, Black, both `tsc --noEmit` (app/web + app/frontend), the mirror
byte-identical test, and `git diff --check`. Ping the field names as implemented → Claude
migrates the FE off LOCAL types and re-verifies the render at `/pf-preview`.

Codex update 2026-05-31 22:32 +1000: item 3 is implemented and verified.
Field names shipped exactly as requested: `PopulationFrequencyDatasetCell`,
`PopulationFrequencyVisualGroup.exome`, `PopulationFrequencyVisualGroup.genome`,
`PopulationFrequencyOverall.total.exome`, and
`PopulationFrequencyOverall.total.genome`. Flat group and cohort-total fields
remain joint, and no exome/genome rows were added to `visual_groups`. Existing
XX/XY inspector cells remain joint-only; per-dataset XX/XY was not added.
Live PopFreq values are sourced by backend gnomAD GraphQL, not MyVariant.
Verification passed: focused gnomAD/report/contract pytest, full backend
pytest, Ruff, Black, `app/web` and `app/frontend` `tsc --noEmit`, byte-identical
backend.ts mirror check, and `git diff --check`.

Claude update 2026-05-31 23:17 +1000 - FE item-3 MIGRATION DONE + polish.
`PopulationFrequencySection.tsx` now consumes the shared contract
(`PopulationFrequencyDatasetCell`; `selectDatasetCell` base =
`PopulationFrequencyOverallTotalCell`; group/total `.exome`/`.genome`), local
item-3 types removed. Exome/Genome Include toggle verified recomputing distinctly
across joint/exome/genome at `/pf-preview`. Plus 3 Steven-approved polish items:
(1) numerals switched to Inter + `tabular-nums`, mono reserved for codes/IDs only
(fixes dotted-"0"-reads-as-"8"); (2) duplicate cohort Total/XX/XY box removed from
the World-map tab footer (kept on Ancestry; non-geographic cohorts stay on the
map); (3) World-map deselect by clicking ocean/base-land OR anywhere outside the
component. `app/web` `tsc` 0, `lint` 8-baseline; all 3 tabs reverified in-browser.
FE-only; no backend/mirror files touched. Whole PopFreq set ready for Steven's ONE
coordinated commit (DELETE `app/web/app/pf-preview/` first).

## Parallel Work Rule

Parallel work is allowed only when file ownership is explicit and disjoint.

Examples:

- Safe: Claude owns `app/frontend/src/components/workbench/**`; Codex owns
  `app/backend/app/tools/**` and backend tests.
- Risky: both agents editing `app/frontend/src/lib/backend.ts`,
  `plans/v2-frontend.md`, or shared docs at the same time.
