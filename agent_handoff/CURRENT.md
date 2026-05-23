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

- **Claude:** idle (awaiting user) @ 2026-05-23 18:52 +1000 — **Vite→Next.js
  migration STARTED + COMPLETED + verified** (landing + Variant Evidence Report
  only). Built a NEW Next.js (App Router) app at `app/web/` — a PARALLEL dir, so
  the Vite `app/frontend/` stays intact for the parked Workbench + frozen
  `/runs`. Ported `/` + `/report` pixel-faithful and **design-agnostic** (the
  emerald "Lifestream" redesign + landing mock are a separate later effort).
  **On Next 16, not 15 — user-ratified 2026-05-23** (Next 15.5 won't build on the
  IT-managed Node 24; App Router identical, ported code byte-identical).
  Verified: `cd app/web && npm run build` clean (compile + TS + prerender
  `/`,`/report`,`/_not-found`) + browser (`next start`) `/` and `/report?demo=1`
  render identical to Vite (server stopped — no orphan). `strict:false` matches
  the Vite app's actual TS. **Untouched:** `app/frontend/**`, the contract canary
  `backend.ts`, `/runs`, AlphaMissense, Codex's lane; `app/web/lib/backend.ts` is
  a hand-kept MIRROR (see Cross-Agent Requests). Design-doc:
  `plans/v2-nextjs-migration/design.md`; full state:
  `~/.claude/plans/next-session-eamos.md`. Next (gated): await landing mock +
  brand/scope/content-realism decisions → emerald redesign on the app/web
  skeleton; mirror Codex's new report contracts into app/web. `/runs` +
  AlphaMissense + parked Workbench remain ON HOLD, untouched.
- **Codex:** idle @ 2026-05-23 21:53 +1000 - **gnomAD ancestry map + age tab
  + ClinicalTrials.gov report slice DONE+verified.** Mirrored the additive
  report contract into both Vite and Next 16, rendered Section 3 with
  SimpleMaps-backed genetic-ancestry AF heat overlays/sidebar + age
  histograms, removed the visible Limitations card, added structured
  ClinicalTrials.gov rows to the trials card, and kept `/runs`/AlphaMissense
  untouched. Full backend pytest, ruff, black, Vite build, Next build, and
  browser verification passed; Next server running on `http://localhost:3000`.

## Log Edit-Lock

Single mutex for shared log/handoff docs (README Hard Rule 8). Set
`LOCKED: <agent> · <stamp> · <file/section>` before editing any of them;
`UNLOCKED · <stamp> · <agent> (<note>)` after you finish and re-read. Other
agent holds fresh (≤ 20 min) → stop + ask the user; stale (> 20 min) → record
takeover, proceed.

UNLOCKED · 2026-05-23 21:53 +1000 · Codex (gnomAD ancestry map + trials report slice synced)

## Shared File Locks

Claim before editing a shared/high-conflict source/contract file (README Hard
Rule 4); release when done.

- none.

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
- Verification last green: frontend **vitest 73/73**, **build clean**,
  **contract canary passed with Gene Viewer + functional display metrics +
  call-card/search-input/report-profile pending-field coverage**; latest
  backend **passed 2026-05-23 19:51 +1000** for Task 11A + Task 12
  (`ruff check app tests`, `black --check --target-version py310 app tests`,
  focused report-profile/gnomAD/ACMG/search/contract/tool suites, and full
  `python -m pytest -q`; 4 skipped; existing JWT short-key warnings only;
  details in Codex section / `PROGRESS.md`).
- Gated (no auto-start): FE-7/8, M-002 follow-ups, destructive git ops.
  **FE-6 Primer Phase A and GV-005/GV-006 are DONE+verified.** Claude commits
  un-gated (a mixed-worktree checkpoint commit still warrants an explicit
  ask). See `RISKS.md`.

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 2).
Section last edited: 2026-05-23 18:51 +1000 · Claude. Prior 2026-05-19 section
(/runs auth + AlphaMissense removal + /report audit fixes) archived verbatim →
`agent_handoff/archive/2026-05-23-claude-section-pre-nextjs.md` (Rule 1/9).
Full incremental detail + gotchas in `~/.claude/plans/next-session-eamos.md`;
migration design-doc in `plans/v2-nextjs-migration/design.md`.

**Session 2026-05-23 — Vite→Next.js migration STARTED + COMPLETED + verified
(landing + Variant Evidence Report only).**

Per user "proceed". Built a NEW Next.js (App Router) app at **`app/web/`** — a
**parallel** dir so the Vite `app/frontend/` stays intact for the parked
Workbench + frozen `/runs`. Ported landing (`/`) and the Variant Evidence
Report (`/report`) **pixel-faithful and design-agnostic** (the emerald
"Lifestream" redesign + landing mock are a separate later effort).

- **What:** scaffold (next.config.mjs `/api/*`→:8000 rewrite, tsconfig,
  postcss/Tailwind v4, layout, globals.css ported verbatim, icon.svg) + 28
  in-scope files copied verbatim + 6 App-Router edits (`lib/api.ts` lookup
  subset, `ModePill`/`LandingClient`/`ReportClient` on `next/link`+
  `next/navigation`, two route files with `<Suspense>` around `useSearchParams`).
- **Next 16, NOT 15 — user-ratified 2026-05-23.** Next 15.5 won't build on the
  IT Node 24 (`SyntaxError` on a trivial app); Next 16.2.6 builds clean, App
  Router identical, ported code byte-identical.
- **Verified:** `cd app/web && npm run build` clean (compile + TS + prerender
  `/`,`/report`,`/_not-found`); browser (`next start`) — `/` and
  `/report?demo=1` render identical to Vite. Server stopped, no orphan.
- **`strict: false`** in app/web/tsconfig.json to match the Vite app's actual
  non-strict TS (verbatim code compiles identically); flip to strict later.
- **Untouched:** `app/frontend/**`, the contract canary's `backend.ts`, `/runs`,
  AlphaMissense, Codex's backend lane. `app/web/lib/backend.ts` is a hand-kept
  mirror (see the Cross-Agent Request above).

**Carry-forward (uncommitted, Claude lane):** all prior verified work (GV-005/6,
FE-6 Primer/CRISPR, FE-5.6, /runs-auth, AlphaMissense removal, /report audit
fixes — see archive) PLUS this session's `app/web/**` Next.js app +
`plans/v2-nextjs-migration/design.md` (both untracked). Nothing committed.

**Next (all gated — user direction):** await landing mock + brand/scope/
content-realism decisions → emerald redesign on the app/web skeleton · mirror
Codex's additive report contracts into app/web/lib/backend.ts + render new
sections (mind the dual backend.ts) · strict-TS hardening pass · cutover
(make app/web canonical) — later. `/runs`, AlphaMissense, Workbench: do not
touch (on hold).

**Resume prompt:**
`# Resume prompt · 2026-05-23 18:52 +1000 · Claude (Vite→Next.js migration DONE+verified — break)
Eamos. Read ~/.claude/plans/next-session-eamos.md (full state), then
agent_handoff/README.md, agent_handoff/CURRENT.md (## Claude + Active Status +
Locks + Cross-Agent Requests), agent_handoff/DECISIONS.md, agent_handoff/RISKS.md,
agent_handoff/on_hold/register.md, plans/v2-nextjs-migration/design.md, then
git status --short --branch.
Delta: STARTED+COMPLETED the Vite→Next.js migration. NEW parallel app app/web/
(App Router) — landing + Variant Evidence Report ported pixel-faithful,
design-agnostic; Vite app/frontend untouched (Workbench+/runs still there).
Build clean + browser-verified. On Next 16 (user-ratified; 15.5 won't build on
IT Node 24). app/web has its OWN backend.ts mirror (canary guards only the Vite
copy). CURRENT.md synced this session. Next: await landing mock + brand/scope
decisions → emerald "Lifestream" redesign on the app/web skeleton; mirror
Codex's new report contracts into app/web. Do NOT touch /runs, AlphaMissense,
parked Workbench. FE Vite checkpoint = 205eaae. End clear-safe.`

## Codex — Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule
1/2). Section last edited: 2026-05-23 21:53 +1000 - Codex.

**Latest Codex update (2026-05-23 21:53 +1000 - Codex):** implemented and
verified the user-directed Variant Evidence Report frontend/backend slice for
gnomAD ancestry visualization, age distribution disclosure, ClinicalTrials.gov
rows, and removal of the visible limitations section. This was an explicit
role redirect from the earlier backend-only handoff.

**Implementation completed:**
- Mirrored the additive report contract in both `app/frontend/src/lib/backend.ts`
  and `app/web/lib/backend.ts`, including `TrialMatch`,
  `TherapiesTrialsSection`, report profile sections, call-card interactions,
  and `population_frequency`.
- Added `PopulationFrequencySection` in both Vite and Next 16 report mirrors:
  SimpleMaps `/world.svg` basemap, proprietary EAMOS genetic-ancestry anchor
  layer, relative AF heat scale, hover/focus sidebar rows with exact AF/AN/AC,
  and a tabbed age-distribution view using source age histograms.
- Kept gnomAD wording aligned with the 2023 genetic-ancestry guidance: source
  groups are inferred genetic-similarity groups, not race/ethnicity, patient
  ancestry, or exact geography.
- Removed the visible `LimitationsSection` card from both report mirrors while
  preserving `limitations` as backend/API data for malformed/unresolved flows.
- Reworked the trials card in both mirrors to show structured
  ClinicalTrials.gov rows from `report_profile.therapies_trials.trial_rows`.
- Updated `ClinicalTrialsTool` / lookup orchestration so live lookups can carry
  up to 15 active/not-yet ClinicalTrials.gov rows into the report evidence and
  typed profile; fixture mode keeps a representative RPE65 text summary without
  fabricating structured eligibility rows.
- Refreshed the RPE65 demo data: ClinicalTrials.gov RPE65 sample now shows 13
  active/not-yet rows and 29 total search records; gnomAD sample wording now
  matches AC 2 / AN 125,748 / AF 0.0000159 rather than the older absent wording.
- Fixed stale report UI risks found by subagents: no static RPE65 header stats
  for non-RPE65 variants, no unavailable ClinVar badge, zero AF/age bins render
  as zero rather than fake minimum bars, and mobile report shell no longer
  compresses the nav search.

**Verification:**
- `cd app/backend && python -m pytest tests/test_variant_report_orchestration.py tests/test_clinical_trials_tool.py tests/test_variant_cache.py -q`
  passed.
- `cd app/backend && python -m pytest tests/test_variant_search_integration.py::test_lookup_fixture_mode_resolves_grch38_and_litvar_publications tests/test_variant_report_orchestration.py tests/test_clinical_trials_tool.py -q`
  passed.
- `cd app/backend && python -m ruff check .` passed.
- `cd app/backend && python -m black --check --target-version py310 .` passed.
- `cd app/backend && python -m pytest -q` passed (4 skipped; existing JWT
  short-key warnings only).
- `cd app/frontend && npx tsc -b --pretty false` passed.
- `cd app/web && npx tsc --noEmit --pretty false` passed.
- `cd app/frontend && npm run build` passed (existing Vite chunk-size warning).
- `cd app/web && npm run build` passed on Next.js 16.2.6.
- Browser verification against `http://localhost:3000/report?demo=1` passed on
  desktop and mobile: map SVG present, AF heat legend present, age tab works,
  13 ClinicalTrials.gov links render, limitations text not visible, no page
  overflow, and no uncanceled network/runtime failures.

**Still gated / next:**
- Patient Report Pipeline (`/runs`) remains parked.
- AlphaMissense remains hidden/on hold; no surfacing work was done.
- Future backend/data work remains gated: production gnomAD ETL/warehouse,
  per-hover endpoint, local DuckDB/parquet prototype, and richer exome/genome
  age-distribution source hydration.
- Next server is running on `http://localhost:3000` for user review.

**Clear-safe:** yes; implementation, verification, and handoff are synced.

**Latest resume prompt:**
`# Resume prompt · 2026-05-23 21:53 +1000 · Codex gnomAD ancestry map + trials report slice complete
Eamos. Read CODEX.md, agent_handoff/README.md, agent_handoff/CURRENT.md (Codex section, Locks, Requests), agent_handoff/on_hold/register.md, agent_handoff/RISKS.md, agent_handoff/DECISIONS.md, docs/proprietary/README.md, docs/proprietary/index.json, docs/proprietary/variant-report-orchestration.md, plans/variant-report-layout/{design.md,spec.md,plan.md}, plans/variant-report-data-orchestration/{design.md,spec.md,plan.md}, then git status --short --branch.
Delta: Codex implemented the user-directed report slice across Vite + Next 16: SimpleMaps-backed gnomAD genetic-ancestry AF heat map/sidebar, age-distribution tab, visible limitations card removed, structured ClinicalTrials.gov rows added, RPE65 demo/trials/gnomAD wording refreshed, and mobile report shell fixed.
Verification: full backend pytest passed; ruff passed; black --check --target-version py310 passed; Vite tsc/build passed; Next tsc/build passed; browser verification passed on desktop/mobile at /report?demo=1. Next server is running at http://localhost:3000.
Next: commit/push status should be checked if resuming immediately; future work remains gated for /runs, AlphaMissense, production gnomAD ETL/warehouse, per-hover endpoint, DuckDB/parquet prototype, and richer exome/genome age source hydration.
End clear-safe (Safe-to-clear line + fresh stamped resume prompt).`
