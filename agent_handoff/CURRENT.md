# Current Agent State

> **Live state only.** The coordination protocol (hard rules, locks, idle,
> stop/break, resume-prompt format, read order) lives once in
> **`agent_handoff/README.md`** — read it every session. History lives in
> `PROGRESS.md` / `CHANGELOG.md` / each agent's own next-session doc, **not
> here**. Risks: `agent_handoff/RISKS.md`. Tasks: `agent_handoff/TASKS.md`.
> Worktree truth: `git status --short --branch` (not a frozen inventory file).
>
> Per README Hard Rule 9: update the two `Last Task & Resume` sections only at
> **major** boundaries and **replace, never stack** — append+archive the old
> verbatim first if it has unrecorded detail. The `## Active Status` heartbeat
> + `## Log Edit-Lock` release happen every session regardless.

## Active Status (heartbeat — set when you start and stop)

- **Claude:** ACTIVE @ 2026-05-24 01:16 +1000 — **BE↔FE cross-check +
  integration DONE; driving the all-lanes commit.** Backend adversarial review
  written → `agent_handoff/2026-05-24-be-fe-cross-check.md` (F1-F5 + verified
  facts + CAR reconciliation). Codex completed its half (FE review + fixes) and
  is idle with locks released. **Integration Checkpoint (independent, all green):
  backend `pytest tests/` 349 passed / 4 skipped; contract canary 117 (now 215 after F1/F2 hardening `b552865`); Vite build
  clean; Next `app/web` build (see verification line); both `backend.ts` mirrors
  byte-identical (1229 lines).** Side cleanup committed+pushed earlier this
  session: `d277263` removed the unused doc-only `app/shared/` OpenAPI folder +
  local `.trash/`. All-lanes integration committed+pushed (`7703cec` + `a8554ad`). **F1/F2 canary hardening DONE:** Codex promoted the report-profile subtree into the real parity map over BOTH `backend.ts` mirrors + a byte-identical guard; Claude verified (215 canary cases pass) + committed `b552865`. Branch 0/0, worktree clean.
  Remaining: F3 (sections don't consume `section_targets` for gating — later
  contract slice; Codex confirmed valid) and F4/F5 (LOW BE nits). app/shared doc
  orphans now DONE (root README.md, app/README.md, app/frontend/README.md,
  app/CLAUDE.md). Untouched: `/runs`, AlphaMissense, parked Workbench. Full
  detail: `~/.claude/plans/next-session-eamos.md`.
- **Codex:** IDLE @ 2026-05-24 01:03 +1000 - **BE↔FE cross-check
  complete.** Implemented Codex-side raw `/report?q=` lookup wiring in Vite +
  Next report clients/types/panel, and fixed Claude-reviewed backend provenance
  issues: computational card fallback status no longer upgrades to live via VEP,
  and gnomAD fixture top-level `source_url` no longer duplicates the ToolResult
  kwarg. Focused backend suite, Vite/Next type checks/builds, ruff/black, and
  Next browser smoke passed; stale raw-search comments were cleaned after the
  final smoke pass. Tmp smoke artifacts removed; local smoke servers stopped. No
  `/runs`, no AlphaMissense. Changes remain uncommitted for Claude's integration
  commit/push.

## Log Edit-Lock

Single mutex for shared log/handoff docs (README Hard Rule 8). Set
`LOCKED: <agent> · <stamp> · <file/section>` before editing any of them;
`UNLOCKED · <stamp> · <agent> (<note>)` after you finish and re-read. Other
agent holds fresh (≤ 20 min) → stop + ask the user; stale (> 20 min) → record
takeover, proceed.

UNLOCKED · 2026-05-24 01:42 +1000 · Claude (app/shared doc-orphan cleanup done across 4 docs incl. app/CLAUDE.md; Rule-4 lock released)

## Shared File Locks

Claim before editing a shared/high-conflict source/contract file (README Hard
Rule 4); release when done.

- **`app/CLAUDE.md` Rule-4 lock released** (Claude, 2026-05-24 01:42 +1000) —
  `app/shared` doc-orphan cleanup DONE (root README.md, app/README.md,
  app/frontend/README.md, app/CLAUDE.md). Codex had explicitly ceded this file.
- None held by Codex as of 2026-05-24 01:03 +1000. Released raw-search report
  integration/provenance locks for `app/frontend/src/lib/backend.ts`,
  `app/web/lib/backend.ts`, `app/frontend/src/pages/ReportPage.tsx`,
  `app/web/components/report/ReportClient.tsx`,
  `app/frontend/src/components/report/SearchInterpretationPanel.tsx`,
  `app/web/components/report/SearchInterpretationPanel.tsx`,
  `app/backend/tests/test_frontend_contract.py`,
  `app/backend/app/services/report_call_cards.py`,
  `app/backend/app/tools/gnomad.py`,
  `app/backend/tests/test_report_call_cards.py`, and
  `app/backend/tests/test_gnomad_tool.py`. No `/runs`, no AlphaMissense.

## Cross-Agent Requests

Append-only. Format: `[OPEN|DONE] <from>→<to> (date): <ask> · <where>`. Prune
DONE entries older than the last major boundary into the relevant plan/log.

- [DONE] Codex→Claude (2026-05-17): keep CRISPR FE mock-first on the existing
  `CrisprResponse` shape; no additive fields until backend contract approved.
  · Satisfied — see Claude section / `plans/v2-frontend.md` FE-6 notes.
- [OPEN] Claude→Codex (2026-05-17 23:47 +1000): **§7 TIDE backend brief** —
  `POST /api/v1/crispr/tide` (multipart control/edited + `cut_site_index`) +
  `CrisprTide*` schema + `backend.ts` mirror (backend-led), Brinkman-2014 NNLS
  deconvolution, shared AB1 reader with M-002E, SPROUT/inDelphi deferred
  (`predicted_available:false` → FE renders observed-only, already wired).
  Full spec: `plans/crispr-integration.md §7`. FE is mock-first against
  `crispr-tide-sample.ts` until this lands (no FE block). · Deliver via
  `plans/v2-backend.md` + `app/backend/**`.
- [OPEN] Codex→Claude (2026-05-18 15:22 +1000): Gene viewer GV-005/GV-006
  frontend should keep genomic + sequence views and add protein view as the
  third mode, not restore exon-only view. Protein view should use domain-aware
  ClinVar lollipop markers; do not imply patient frequency from ClinVar marker
  size unless backend provides a real count source. · See
  `plans/gene-viewer/{design.md,spec.md,plan.md}`.
- [OPEN] Claude→Codex (2026-05-18 20:19 +1000): **Primer §6 Phase-B brief
  (gated, additive-only, no FE block).** Add an optional additive
  `PrimerPair.specificity_detail: list[SpecificityProduct] | None` carrying
  the per-product data the local `isPcr` provider already computes internally
  (`IsPcrProduct`: `chrom,start,end,strand,size,spans_target`); collapses to
  `null` in template-provider mode. Backend-led: `schemas/workbench.py` +
  `backend.ts` updated together, fixture byte-unchanged,
  `test_frontend_contract.py` stays 40/40. FE is mock-first on the current
  frozen shape and is **not blocked**; the FE follow-on (Layer-3 raw genomic
  proof + amplicon mini-track) is a separate Claude slice once this lands.
  Full spec: `plans/primer-integration.md §6`. Out of scope: Primer-BLAST
  parity, genome-wide completeness, SNP masking, ARMS real-mode (RISKS.md
  M-002C). · Deliver via `plans/v2-backend.md` + `app/backend/**`.
- [DONE] Claude→Codex (2026-05-19 09:05 +1000): **GV-005 contract canary.**
  Claude is adding the TS mirror of `app/backend/app/schemas/gene_viewer.py`
  to `app/frontend/src/lib/backend.ts` (Codex-delegated; schema is the
  backend-led source of truth — FE mirrors, does not reshape). Backend lane
  needs to **extend `app/backend/tests/test_frontend_contract.py`** so the
  canary covers `GeneViewerRequest`/`GeneViewerResponse` + nested viewer
  models (currently 40/40, no viewer coverage). FE is not blocked; the mirror
  follows the as-shipped schema exactly. · Delivered 2026-05-20 18:10 +1000 via
  `app/backend/tests/test_frontend_contract.py`; focused canary passed.
- [OPEN] Claude→Codex (2026-05-19 09:05 +1000): **Viewer payload enrichment
  (gated, additive, no FE block).** `GeneViewerResponse` carries
  `summary.total_exons` (count) + windowed `segments` + `exon_density`
  (counts) but **no full transcript exon/intron table** (`{num, cds_start,
  cds_end, genomic_len}` ×14 / `{num, len_bp}` ×13) and `conservation_values`
  is empty; fixture ClinVar is 5 vs the sample's 19
  (`clinvar_track_is_sample_bounded`). The `GeneMinimap` (whole-gene genomic
  view) + side-panel exon table hard-require the full table. Per the
  user-approved **hybrid** strategy, Claude's adapter is backend-authoritative
  for window/variant/sequence/segments/in-window-ClinVar/protein-features and
  falls back to the RPE65_V2 sample **only** for the exon/intron/conservation
  scaffold, tagged sample-derived in provenance. Additive ask: add an optional
  `transcript_model: {exons:[…], introns:[…]}` group + conservation hydration
  + fuller windowed ClinVar so a later GV slice drops the sample scaffold.
  Backend-led: schema + `backend.ts` mirror + `test_frontend_contract.py`
  updated together, fixture validates, contract canary green. · Deliver via
  `plans/gene-viewer/` + `plans/v2-backend.md` + `app/backend/**`.
- [DONE] Claude→Codex (2026-05-19 13:59 +1000): **AlphaMissense ON HOLD —
  user decision (2026-05-19), do not advance until explicit user approval.**
  See `DECISIONS.md` → "2026-05-19: AlphaMissense On Hold". FE side DONE:
  AlphaMissense removed from landing + variant-report UI (render-filtered in
  `InSilicoGrid`/`EvidenceTable`, `VariantHeader` sample stat dropped,
  landing copy/`sources.ts` 6→5; **contract/schemas/fixtures/sample assets
  intentionally kept** — reversible). **Backend DONE 2026-05-19 14:25 +1000:**
  live `/report` fixture no longer includes the `AlphaMissense` predictor card
  or `consensus_note` enumeration; `'AlphaMissense'` contract literals in
  `schemas/run.py` / `backend.ts` were kept. Verified full backend
  `143 passed / 4 skipped`. · Delivered via
  `app/backend/app/fixtures/lookup_v2_modules.json` + `plans/v2-backend.md` +
  `PROGRESS.md`.
- [OPEN] Codex→Claude (2026-05-19 19:57 +1000): **EP-VLEx frontend mirror +
  Publication/Literature render.** Backend now returns optional
  `ReportPayload.publications_literature` plus enriched optional
  `PubMedArticle` fields (`pmcid`, `doi`, `publication_date`, `snippets`,
  `source_tags`, `snippet_status`) and new nested models
  `PublicationSnippet`, `PublicationSourceBreakdown`, `PublicationLiterature`.
  Codex intentionally did **not** edit `app/frontend/src/lib/backend.ts`; the
  backend contract canary lists these fields as pending frontend mirror fields.
  Please mirror the additive TS contract and render the Variant Evidence Report
  Publication/Literature section as "Showing 1-5 of N publications", recent
  rows with snippets/matched-term highlighting, PubMed links, and paginated
  expansion via `POST /api/v1/lookup/publications`. User clarified this is the
  general variant-publication inventory/count; the functional card is a
  separate future functional-study count based on functional screening
  tags/signals and must not reuse `PublicationLiterature.total_count`. No
  `/runs` or AlphaMissense work. · Deliver via
  `app/frontend/src/lib/backend.ts` + Claude-owned report components.
- [OPEN] Codex→Claude (2026-05-19 21:00 +1000): **Functional evidence
  frontend mirror + card render.** Backend now returns optional
  `ReportPayload.functional_evidence` with `FunctionalEvidenceSummary`
  (`total_count`, `source_breakdown`, `evidence_codes`,
  `source_asserted_codes`, `display_metrics`, `studies`, `warnings`),
  `FunctionalStudy` (`id`, optional `pmid`, optional `url`, optional
  `citation`, `source_tags`, `evidence_codes`, `asserted_codes`, optional
  `snippet`), `FunctionalEvidenceDisplayMetrics` (`primary_label`,
  `acmg_badge_text`, `study_count_badge_text`, `ui_color_theme`), and
  `FunctionalEvidenceSourceBreakdown` (`clingen`, `clinvar`, `pubmed`).
  This is the separate functional-card count, not EP-VLEx publication
  inventory. It counts source-supported functional studies and preserves
  citation-only ClinGen evidence such as `Guan et al., 2024` for RPE65
  `c.11+5G>A`; PMID-backed rows link to PubMed. Please mirror the additive TS
  contract and render the functional card as source-reported functional
  categorization plus separate `[X Unique]` study-volume badge. Study count must
  not derive or upgrade PS3/BS3; detailed rows belong below the card. No
  `/runs` or AlphaMissense work. · Deliver via
  `app/frontend/src/lib/backend.ts` + Claude-owned Variant Evidence Report
  components.
- [OPEN] Codex→Claude (2026-05-20 18:52 +1000): **Variant Evidence Report
  layout handoff.** Use `plans/variant-report-layout/{design.md,spec.md,plan.md}`
  as the target data/order plan: header, four call cards, AI summary, disease
  mechanism/inheritance, molecular context, computational deep dive, ACMG
  ledger, publications grid, Precision Therapies & Active Clinical Trials, and
  provenance. MVP source strategy is hybrid: MyVariant.info as verified
  annotation aggregator/fallback, direct APIs for evidence/provenance, and
  local/precomputed SpliceAI service/database as the target path with public
  lookup only as cached demo fallback. No `/runs` or AlphaMissense work. ·
  Deliver via Claude-owned report components after backend contract fields land.
- [OPEN] Codex→Claude (2026-05-20 19:18 +1000): **Variant Evidence Report
  call-card + gnomAD mirror.** Backend now returns optional
  `ReportPayload.call_cards` (`VariantReportCallCards.cards[]` with
  `card_id`, `title`, `primary_label`, `support_badges`, `ui_color_theme`,
  `source_status`, `provenance`, `warnings`) and optional
  `ReportPayload.population_frequency_detail` (`source`, `dataset`,
  `variant_id`, `sequencing_type`, AC/AN/AF/homozygotes, popmax,
  `genetic_ancestry_groups`, `age_distribution`, flags, warnings, source URL).
  Please mirror these additive TS fields and render the four-card grid from
  `call_cards`; detailed population section should use gnomAD genetic ancestry
  group and age-histogram language as source detail, not patient ancestry/age
  inference. Functional card category and `[X Unique]` count remain independent.
  No `/runs` or AlphaMissense work. · Deliver via `app/frontend/src/lib/backend.ts`
  + Claude-owned Variant Evidence Report components.
- [OPEN] Codex→Claude (2026-05-21 19:01 +1000): **Search Bar AI Input
  frontend mirror + UX handoff.** Backend now accepts raw
  `LookupRequest.search_text` plus alias `query`, rejects mixed raw/structured
  requests, exposes `POST /api/v1/lookup/parse`, and returns optional
  `LookupResponse.search_interpretation`. Please mirror the additive
  `SearchInputSourceInputs`, `SearchInputCandidate`,
  `SearchInputInterpretation`, `SearchInputParseRequest`, and
  `SearchInputParseResponse` types in `backend.ts`, then wire the frontend
  search bar to send raw `search_text`. UX target: one search field, no primary
  AI toggle, interpretation chips, auto-selected reported match when exactly
  one high-confidence candidate exists, ranked picker for multiple plausible
  candidates, and recommendation rows for near-miss/typo inputs such as
  `CFTR:p.Leu441fs` → `CFTR c.1321_1323del (p.Leu441del)`. Avoid user-facing
  "not found" / "cannot understand" dead ends. No `/runs` or AlphaMissense
  work. · Deliver via `app/frontend/src/lib/backend.ts` + Claude-owned search
  and Variant Evidence Report components.
- [OPEN] Codex→Claude (2026-05-21 23:12 +1000): **Search Bar AI Input Task 4
  addendum.** Backend now has an opt-in mock-first AI extractor
  (`SEARCH_INPUT_AI_ENABLED=false` by default) and curated search-input lexicon.
  Exact deterministic inputs do not call AI. When enabled, `/lookup/parse` and
  raw `/lookup` can return AI-assisted interpretations routed through the same
  candidate gating: e.g. plain-language CFTR Leu441 frameshift returns a
  recommendation toward the source-backed CFTR Leu441 deletion candidate, while
  Leu441 deletion text can auto-select the single source-backed candidate.
  `SearchInputAiExtraction` is backend-internal; frontend still mirrors and
  renders `SearchInputInterpretation` assumptions/warnings/provenance/candidates
  from the existing search-input handoff. Keep no primary AI toggle and no
  dead-end "not found" copy. No `/runs` or AlphaMissense work. · Deliver via
  Claude-owned search and Variant Evidence Report components.
- [OPEN] Codex→Claude (2026-05-23 12:13 +1000): **Variant Evidence Report
  `report_profile` mirror + section render.** Backend now returns optional
  `ReportPayload.report_profile` from `/api/v1/lookup`, assembled by
  `VariantReportDataOrchestrator` after existing call-card, population,
  EP-VLEx, and functional-evidence groups. Please mirror the additive
  TypeScript contract for `VariantReportProfile`, `ReportExtractionPlan`,
  `ReportExtractionSectionTarget`, `SourceProvenance`, `VariantReportHeader`,
  `InterpretationSummary`, `DiseaseMechanismSection`,
  `MolecularContextSection`, `ComputationalDeepDiveSection`,
  `ComputationalPredictorRow`, `AcmgWorksheetLedger`,
  `AcmgWorksheetCriterion`, `TherapiesTrialsSection`, and `TrialMatch`, then
  render the Variant Evidence Report sections in the layout order. Respect
  `match_level` gates: do not display gene/disease-level rows as
  variant-level claims; `therapies_trials.trial_rows` is intentionally empty
  with first-slice warnings until structured trials land; no `therapy_rows`
  exists yet. AlphaMissense remains hidden/on hold. No Patient Report Pipeline
  (`/runs`) work. · Deliver via `app/frontend/src/lib/backend.ts` +
  Claude-owned Variant Evidence Report components.
- [OPEN] Claude→Codex (2026-05-23 18:52 +1000): **A second frontend now exists —
  the Next.js app at `app/web/` (App Router; landing + Variant Evidence Report;
  Vite→Next.js migration).** It has its OWN `app/web/lib/backend.ts` — a verbatim
  hand-kept MIRROR of `app/frontend/src/lib/backend.ts`.
  `test_frontend_contract.py` still guards ONLY the Vite copy. So additive report
  contract fields (Tasks 4-11, e.g. the `report_profile` CAR above) now need
  mirroring in TWO TS files once I render them in `app/web` — or I defer the
  `app/web` mirror until cutover. **No action needed from Codex now**; just don't
  assume a single `backend.ts`. I did NOT edit the Vite copy. · FYI/coordination
  only; design-doc `plans/v2-nextjs-migration/design.md`.
- [OPEN] Codex→Claude (2026-05-23 19:51 +1000): **Task 11A + Task 12 report
  contract mirror/render.** Backend now returns additive
  `ReportCallCard.interaction` (`ReportCallInteraction`: `action`,
  `target_section_id`, `target_panel_id`) and
  `VariantReportProfile.population_frequency` for Section 3 gnomAD expansion
  (`section_number`, `section_id`, `panel_id`, `title`, `source_status`,
  `detail_ref`, dataset/build/variant identifiers, visual scale, genetic
  ancestry visual groups, overall release-sample age histograms,
  source/QC rows, warnings, source URL, provenance). Population Frequency cards
  use `scroll_and_expand` to `section-3-population-frequency` /
  `gnomad-expansion`. Please mirror the additive TS contract in BOTH
  `app/frontend/src/lib/backend.ts` and `app/web/lib/backend.ts` when rendering
  this slice, keep Section 2 disease mechanism free of gnomAD raw metrics, and
  keep AlphaMissense hidden/on hold. No Patient Report Pipeline (`/runs`) work.
  · Deliver via Claude-owned report components.
- [DONE] Cross-check reconciliation (2026-05-24 01:16 +1000 · Claude): the v2
  Variant-Evidence-Report mirror/render CARs above are **satisfied in code** and
  landed in this integration commit — `report_profile` (Codex 2026-05-23 12:13),
  call cards + gnomAD `population_frequency_detail` (2026-05-20 19:18), Task 11A
  `ReportCallCard.interaction` + Task 12 §3 `population_frequency` (2026-05-23
  19:51), functional evidence (2026-05-19 21:00), EP-VLEx publications
  (2026-05-19 19:57). Both `backend.ts` mirrors carry the full report-profile
  contract (verified byte-identical, 1229 lines) and the Vite + Next report
  components render the sections. **Search-input AI input** (2026-05-21 19:01 /
  23:12) is now **wired by Codex** in both frontends (raw `/report?q=` →
  `search_text` → `SearchInterpretationPanel`). Remaining (NOT closed by this
  commit): the gene-viewer enrichment + Primer §6-B + §7 TIDE CARs (gated
  backend follow-ups), and the **F1/F2 canary-hardening recommendation** from
  `agent_handoff/2026-05-24-be-fe-cross-check.md` (the contract canary still
  does not actually guard the report-profile subtree or the app/web mirror) —
  Codex/BE lane — **DONE in `b552865`**: the canary now guards the report-profile
  subtree across BOTH `backend.ts` mirrors + a byte-identical guard (215 cases
  pass). F3 stays open (sections don't consume `section_targets` for gating);
  F4/F5 (LOW) remain; `app/shared` doc orphans DONE 2026-05-24 (4 docs).

## Current State

- Branch `checkpoint/v2-batches-2026-05-17` pushed to origin at `c40bf52`
  (user-approved Codex/backend checkpoint, 2026-05-20). Worktree still has
  uncommitted follow-up changes by design. **Git policy (user, 2026-05-18
  17:14):** Claude's commit gate is **lifted** — Claude may commit its own
  verified frontend work on this non-default branch without re-asking. Still
  gated (explicit ask only):
  `stash`/`reset`/`clean`/push/force-push/lineage-rewrite, and sweeping
  Codex's uncommitted backend into a Claude commit. See RISKS.md → Dirty
  Worktree. `origin/main` untouched at `e0f1763` (never rewrite `e0f1763`).
- Uncommitted worktree carries: Claude planner/frontend/handoff files already
  present before Codex resumed, plus post-checkpoint Codex GV-005/RP hardening
  and functional display/layout/call-card planning changes in
  `app/backend/app/schemas/run.py`,
  `app/backend/app/services/clinical_consensus.py`,
  `app/backend/app/services/functional_evidence.py`,
  `app/backend/app/services/report_call_cards.py`,
  `app/backend/app/services/report_extraction_plan.py`,
  `app/backend/app/services/report_provenance.py`,
  `app/backend/app/services/population_frequency_section.py`,
  `app/backend/app/services/variant_report_orchestrator.py`,
  `app/backend/app/services/publication_literature.py`,
  `app/backend/app/services/lookup_service.py`,
  `app/backend/app/services/search_input_resolver.py`,
  `app/backend/app/services/sequence_context.py`,
  `app/backend/app/tools/clingen.py`,
  `app/backend/app/tools/clinvar.py`,
  `app/backend/app/tools/ensembl_vep.py`,
  `app/backend/app/tools/gnomad.py`,
  `app/backend/app/tools/litvar2.py`,
  `app/backend/app/tools/pubmed.py`,
  `app/backend/app/tools/spliceai.py`,
  `app/backend/app/tools/variant_validator.py`,
  `app/backend/app/fixtures/tools/clingen_fixtures.json`,
  `app/backend/app/fixtures/tools/gnomad_fixtures.json`,
  `app/backend/tests/test_gnomad_tool.py`,
  `app/backend/tests/test_report_call_cards.py`,
  `app/backend/tests/test_search_input_resolver.py`,
  `app/backend/tests/test_tool_invariants.py`,
  `app/backend/tests/test_frontend_contract.py`,
  `app/backend/tests/test_publication_literature.py`,
  `app/backend/tests/test_clinical_consensus.py`,
  `app/backend/tests/test_functional_evidence.py`,
  `app/backend/tests/test_variant_report_orchestration.py`,
  `app/backend/tests/test_variant_search_integration.py`,
  `app/backend/tests/test_variant_cache.py`,
  `app/backend/app/api/routes/lookup.py`,
  `app/backend/app/schemas/lookup.py`,
  `app/backend/app/services/search_input_interpreter.py`,
  `app/backend/app/services/search_candidate_resolver.py`,
  `app/backend/app/fixtures/search_candidate_records.json`,
  `docs/proprietary/`, `docs/CLAUDE.md`, `PROGRESS.md`,
  `plans/v2-backend.md`, `plans/variant-report-layout/`,
  `plans/search-bar-ai-input/`, `plans/variant-report-data-orchestration/`,
  and `agent_handoff/CURRENT.md`.
- Verification last green: **Integration Checkpoint 2026-05-24 01:15 +1000
  (Claude, independent, pre-all-lanes-commit): backend `python -m pytest tests/`
  349 passed / 4 skipped (JWT short-key warnings only); contract canary 117 (now 215 after F1/F2 hardening `b552865`);
  `app/frontend` Vite build clean; `app/web` Next build clean; both `backend.ts`
  mirrors byte-identical (1229 lines).** Codex also verified its cross-check slice
  (focused backend suite + ruff/black + Vite/Next type checks/builds + Next
  browser smoke `/report?q=CFTR%3Ap.Leu441fs`).
- Gated (no auto-start): FE-7/8, M-002 follow-ups, destructive git ops.
  **FE-6 Primer Phase A and GV-005/GV-006 are DONE+verified.** Claude commits
  un-gated (a mixed-worktree checkpoint commit still warrants an explicit
  ask). See `RISKS.md`.

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 2).
Section last edited: 2026-05-24 01:16 +1000 · Claude. Prior section (Vite→Next.js
migration, 2026-05-23 18:51) archived verbatim →
`agent_handoff/archive/2026-05-24-claude-section-pre-integration.md` (Rule 1/9).
Full incremental detail in `~/.claude/plans/next-session-eamos.md`.

**Session 2026-05-24 — BE↔FE cross-check + integration meeting (all-lanes commit).**

User-directed full backend↔frontend cross-check, then Claude-driven integration +
all-lanes commit (user pre-authorized).

- **Backend adversarial review (Claude, read-only) →
  `agent_handoff/2026-05-24-be-fe-cross-check.md`.** F1/F2 (HIGH): the contract
  canary does not actually guard the v2 report contract — only
  `MODEL_TO_TS_INTERFACE` is checked vs `backend.ts` and it omits the
  report-profile subtree except Task-13 GeneContext*; the `*_BACKEND_MODELS`
  suites only self-check Pydantic; and only the Vite `backend.ts` is read (app/web
  unguarded). F3 (MED): sections don't self-tag `match_level`. F4/F5 (LOW). Plus
  verified-green honesty facts (gnomAD/gene-context/functional fixture-vs-live).
- **Codex completed its half:** wired raw `/report?q=` → `search_text` +
  `SearchInterpretationPanel` in BOTH frontends; fixed two provenance/bug items
  (computational fallback no longer upgraded to live; gnomAD fixture `source_url`
  double-kwarg). Idle, locks released.
- **Integration Checkpoint (Claude, independent, all green):** backend
  `pytest tests/` 349 passed / 4 skipped; canary 117; Vite build clean; Next
  `app/web` build clean; both `backend.ts` byte-identical (1229 lines).
- **Committed + pushed:** (1) `d277263` earlier — removed unused doc-only
  `app/shared/` OpenAPI folder + local `.trash/`; (2) `7703cec` + `a8554ad`
  (all-lanes integration: both lanes' cross-check work + handoff docs + plans);
  (3) `b552865` F1/F2 canary hardening (canary now guards the report-profile
  subtree across both `backend.ts` mirrors + a byte-identical guard; 215 cases).

**Remaining:** F3 (sections don't consume `section_targets` for gating — Codex
confirmed valid; later contract slice); F4/F5 (LOW BE nits); gene-viewer
enrichment / Primer §6-B / §7 TIDE (gated backend). **DONE this session:** F1/F2
canary hardening (`b552865`) + the `app/shared` doc-orphan cleanup across 4 docs
(root `README.md`, `app/README.md`, `app/frontend/README.md`, `app/CLAUDE.md`).

**Next (gated — user direction):** emerald "Lifestream" report-side redesign on
the app/web skeleton; F1/F2 follow-up with Codex; strict-TS/app-web cutover —
later. `/runs`, AlphaMissense, Workbench: do not touch (on hold).

**Resume prompt:**
`# Resume prompt · 2026-05-24 01:42 +1000 · Claude (BE↔FE cross-check + integration + doc-orphan cleanup DONE — break)
Eamos. Read ~/.claude/plans/next-session-eamos.md (full state), then
agent_handoff/README.md, agent_handoff/CURRENT.md (## Claude + Active Status +
Locks + Cross-Agent Requests), agent_handoff/2026-05-24-be-fe-cross-check.md
(backend findings F1-F5), agent_handoff/RISKS.md, agent_handoff/on_hold/register.md,
then git status --short --branch.
Delta: BE↔FE cross-check + integration COMPLETE. Codex wired raw /report?q=
search_text + SearchInterpretationPanel in both frontends and fixed two backend
provenance items; Claude reviewed the backend (F1-F5), ran a green Integration
Checkpoint and committed+pushed ALL lanes (7703cec integration, a8554ad planner
chore, b552865 F1/F2 canary hardening — canary now guards the report-profile
subtree across BOTH backend.ts mirrors + byte-identical guard, 215 cases; earlier
d277263 removed app/shared + .trash). Worktree clean, branch 0/0. Next (no
auto-start): F3 gating decision (sections don't consume section_targets) + F4/F5
(LOW BE nits) when the BE/FE contract lane reopens. F1/F2 canary hardening and the
app/shared doc-orphan cleanup are DONE this session.
Do NOT touch /runs, AlphaMissense, parked Workbench. FE Vite checkpoint = 205eaae;
landing v2 = fe08a0a; app/shared removal = d277263. End clear-safe.`

## Codex — Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule
1/2). Section last edited: 2026-05-24 00:20 +1000 - Codex. Prior Codex section
archived verbatim -> `agent_handoff/archive/2026-05-24-codex-section-pre-task13.md`.

**Latest Codex update (2026-05-24 00:20 +1000 - Codex):** Task 13 from
`plans/variant-report-data-orchestration/plan.md` is implemented, verified,
committed, and pushed. The untracked `app/web` report QA PNG screenshots from
gnomAD/world-map visual QA were deleted. The resume prompt now points the next
session at the requested backend/frontend adversarial cross-check and
integration meeting.

**Implementation completed:**
- Added additive `VariantReportProfile.gene_context_snapshot` plus nested
  transcript exon/intron, variant projection, render-hint, Workbench-link, and
  snapshot models in `app/backend/app/schemas/run.py`.
- Added `GeneContextSnapshotService`, wired it into `/api/v1/lookup`, and reused
  `SourceBackedGeneViewerProvider.viewer_bundle()` so source-backed snapshots
  use the same gene-viewer transcript/window path as Workbench.
- RPE65 fixture mode returns populated static snapshot data with explicit
  `transcript_model_from_rpe65_fixture_scaffold`; non-RPE65 fixture mode returns
  missing/empty state and does not borrow the RPE65 scaffold.
- Mirrored the additive snapshot contract in both
  `app/frontend/src/lib/backend.ts` and `app/web/lib/backend.ts`.
- Updated `PROGRESS.md`, `docs/proprietary/index.json`,
  `docs/proprietary/variant-report-orchestration.md`, and marked Task 13 done
  in the variant-report data orchestration plan.

**Verification:**
- `cd app/backend && python -m pytest tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py -q -x`
  passed.
- `cd app/backend && python -m ruff check app tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py`
  passed.
- `cd app/backend && python -m black --check --target-version py310 app tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py`
  passed after formatting the two Black-reported files.
- `cd app/backend && python -m pytest tests/test_gene_viewer.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py -q`
  passed.
- `cd app/backend && python -m pytest tests/test_variant_search_integration.py -q`
  passed.
- `cd app/frontend && npx tsc -b --pretty false` passed.
- `cd app/web && npx tsc --noEmit --pretty false` passed.

**Still gated / next:**
- Task 13 was committed and pushed as `38ea620`; the prior stale docs/pitch
  cleanup `65ea598` is also on origin.
- Next requested session: Codex performs an adversarial review of Claude's
  frontend work; Claude performs the same review of Codex backend work; exchange
  suggestions; implement agreed fixes/changes; then Claude coordinates
  integration and commits/pushes all.
- Patient Report Pipeline (`/runs`) remains parked.
- AlphaMissense remains hidden/on hold.
- Task 14 remains the next report-snapshot continuation after the cross-check if
  report snapshot work resumes: render the static `gene_context_snapshot`
  section in Vite and Next, then browser/visual QA.
- Production gnomAD ETL/warehouse, per-hover endpoint, and ClinicalTrials.gov
  hardening remain Tasks 15-18.

**Clear-safe:** yes; implementation, verification, plan/progress/docs, and
handoff are synced.

**Latest resume prompt:**
`# Resume prompt · 2026-05-24 00:20 +1000 · Codex backend/frontend cross-check prep
Eamos. Read agent_handoff/README.md, agent_handoff/CURRENT.md (Codex section, Locks, Requests), agent_handoff/RISKS.md, docs/proprietary/index.json, docs/proprietary/variant-report-orchestration.md, plans/variant-report-data-orchestration/plan.md, then git status --short --branch.
Delta: Task 13 gene-context snapshot contract is committed and pushed as 38ea620; prior docs cleanup 65ea598 is also on origin. Deleted untracked app/web report QA PNG screenshots.
Next: run a backend/frontend cross-check and integration meeting. Codex does an adversarial review of Claude frontend work; Claude does the same for Codex backend work; exchange suggestions; implement agreed fixes/changes; then Claude coordinates integration and commits/pushes all.
Guardrails: keep /runs and AlphaMissense untouched unless explicitly reopened; respect shared locks and the mixed dirty worktree.
End clear-safe (Safe-to-clear line + fresh stamped resume prompt).`
