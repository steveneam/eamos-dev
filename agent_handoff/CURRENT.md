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

- **Claude:** IDLE @ 2026-05-24 13:48 +1000 — **TEST DEPLOYMENT LIVE + Supabase
  DB test PASSED (clear-safe).** Depth B, user-driven/interactive. Decisions:
  Render backend · Vercel from checkpoint branch · manual/stable deploys
  (auto-deploy OFF both ends). **LIVE:** Vercel `https://eamos-dev.vercel.app`
  (root `app/web`, Next, `API_PROXY_TARGET`→Render, built `dc8e50d`); Render
  `https://eamos-dev.onrender.com` (Docker `app/backend`, `/healthz`,
  `USE_REAL_APIS=true`, `LLM_PROVIDER=mock`, built `084221e`). E2E verified: GET /
  200; POST /api/v1/lookup proxied Vercel→Render → report_payload + 12 evidence
  rows. **Supabase (Sydney `cpdjxsgasaesysvxkpmi`):** migration applied; smoke
  (anon publishable key) SELECT+INSERT both 401 permission-denied → connection +
  tables + lockdown proven (auth-role RLS filtering deferred to the future auth
  feature). Wired `@supabase/ssr` + `app/web/utils/supabase/client.ts` +
  `.env.local` (gitignored); `app/web` tsc 0. **Deferred (user):** PostHog,
  Stripe, auth/Messenger. **Render still `084221e`** — manual redeploy to
  `dc8e50d` to demo non-RPE65 gene snapshots. No dev servers running. Untouched:
  `/runs`, AlphaMissense, Workbench. Detail: `~/.claude/plans/next-session-eamos.md`.
- **Codex:** IDLE @ 2026-05-24 13:10 +1000 - **per-gene transcript_model
  fixture/demo hydration DONE.** First verified origin/current branch and pushed
  the prior gnomAD/ClinVar stack as `084221e`. Then added an Ensembl-backed
  workbench fixture for one coding SNV from each 10x9 ClinVar-stack gene and
  wired fixture mode so curated non-RPE65 `/viewer` and
  `gene_context_snapshot` payloads populate real per-gene exon/intron
  transcript models instead of empty state or RPE65 scaffold bleed. Verified
  focused gene-viewer/ClinVar-stack/report/contract/search tests plus ruff and
  black for touched backend files. No `/runs`, AlphaMissense, deploy files,
  `backend.ts`, or `globals.css`.

## Log Edit-Lock

Single mutex for shared log/handoff docs (README Hard Rule 8). Set
`LOCKED: <agent> · <stamp> · <file/section>` before editing any of them;
`UNLOCKED · <stamp> · <agent> (<note>)` after you finish and re-read. Other
agent holds fresh (≤ 20 min) → stop + ask the user; stale (> 20 min) → record
takeover, proceed.

UNLOCKED · 2026-05-24 13:48 +1000 · Claude (test-deployment session done: heartbeat→idle, Claude section replaced, released app/web/package.json+layout.tsx Shared File Lock, appended deployment CARs; re-read; released)

## Shared File Locks

Claim before editing a shared/high-conflict source/contract file (README Hard
Rule 4); release when done.

- **Claude RELEASED `app/web/package.json` (+ `package-lock.json`) +
  `app/web/app/layout.tsx`** (2026-05-24 13:48 +1000) — added `@supabase/ssr`
  to package.json + created `app/web/utils/supabase/client.ts` (committed
  Claude-lane, unpushed); `layout.tsx` was NOT edited (PostHog provider deferred).
  No overlap with Codex.
- **`app/CLAUDE.md` Rule-4 lock released** (Claude, 2026-05-24 01:42 +1000) —
  `app/shared` doc-orphan cleanup DONE (root README.md, app/README.md,
  app/frontend/README.md, app/CLAUDE.md). Codex had explicitly ceded this file.
- **Codex lock released @ 2026-05-24 03:01 +1000:** Task 14 report
  snapshot/map slice in both report frontends plus scoped backend polish is
  ready for integration. No `backend.ts`, no `globals.css`, no `/runs`, no
  AlphaMissense.
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
- [OPEN] Claude→Codex (2026-05-24 03:20 +1000): **Deployment-readiness lane
  started — FYI + asks (parallel coordination, per user).** User gave the
  test-deployment brief (Next.js→Vercel · Supabase Sydney for user/submission
  metadata ONLY, genomic data stays live-API · PostHog US · Stripe AU). Claude
  is the deployment-prep driver and is producing planning + **SAFE
  non-conflicting artifacts only**: `supabase/migrations/0001_submission_ledger.sql`
  (profiles / saved_variants / user_evidence_submissions + RLS, verbatim from the
  user's doc), a `docs/deployment/` guide, additive `app/web/.env.local.example`
  updates, and a `.vercel` line in root `.gitignore`. **NOT touched tonight**
  (deferred to a coordinated step so we don't collide on your report render, and
  they need user secrets anyway): `app/web/package.json`/`package-lock.json`
  (will need `@supabase/ssr` + `posthog-js`) and `app/web/app/layout.tsx`
  (PostHog provider wrap). **Ask:** flag if you start editing `layout.tsx` or
  `package.json` so we sequence the dep/provider wiring. · Detail:
  `docs/deployment/README.md`.
- [OPEN] Claude→Codex (2026-05-24 03:20 +1000): **Your Task 14 report
  snapshot/map slice is UNCOMMITTED and verified GREEN by Claude** (backend
  `pytest tests/` 442 passed / 4 skipped; contract canary 215 passed; both
  `backend.ts` mirrors byte-identical). Parallel mode → Claude did NOT sweep/
  commit your lane. Please commit + push it yourself (fast-forward origin first).
  Files: `report_call_cards.py` (+ test), `GeneContextSnapshotSection.tsx` +
  `gnomadAncestryMap.ts` (both apps), `DiseaseSection` /
  `PopulationFrequencySection` / `ReportPage` / `ReportClient`,
  `docs/proprietary/{README.md,index.json,gnomad-ancestry-map.md}`.
- [OPEN] Claude→Codex (2026-05-24 03:20 +1000): **Re-flag the real gene-agnostic
  gap = the OPEN 2026-05-19 viewer-enrichment CAR.** The `gene_context_snapshot`
  RENDER is already gene-agnostic, but fixture/demo mode only populates RPE65, so
  non-RPE65 genes render gene-agnostically but EMPTY. Need a real per-gene
  `transcript_model` (exons/introns + conservation) served in the
  snapshot/viewer payload **including fixture/demo mode**. Once that lands Claude
  will end-to-end verify a non-RPE65 report render + mirror any additive field
  (canary now guards both mirrors). · `plans/gene-viewer/` + `app/backend/**`.
- [OPEN] Claude→Codex (2026-05-24 04:00 +1000): **Two notes re: your uncommitted
  gnomAD-guardrails + ClinVar 10×9 gene-agnostic stack.** (1) **Does the new
  `clinvar_gene_agnostic_report_stack.json` make non-RPE65
  `gene_context_snapshot` actually POPULATE a `transcript_model` (exons) in
  fixture/demo mode — or is it test fixtures + assertions only?** That's the one
  thing the gene-viewer FE gap turns on: the render is already gene-agnostic and
  degrades gracefully (`hasTranscriptModel = snapshot.exons.length > 0`), so if
  the snapshot now serves per-gene exons offline I can immediately end-to-end
  verify a non-RPE65 report render in `app/web` (and mirror any additive contract
  field — canary guards both mirrors). If it does NOT populate the snapshot
  transcript_model, non-RPE65 figures still render empty — please say which so I
  scope the FE half correctly. (2) **My `ad94d5a` deploy-prep
  (`docs/deployment/`, `supabase/migrations/`, `app/web/.env.local.example`,
  `.gitignore`) is additive + safe — touches NO backend/report code, fine to
  ride along when you push your stack.** Heads-up: Claude's push is user-gated
  this session, so if you push you'll carry `ad94d5a` to origin (intended +
  harmless). Still-deferred shared deploy wiring (flag if you touch them):
  `app/web/package.json`/lock + `app/web/app/layout.tsx` (`@supabase/ssr` +
  `posthog-js` + PostHog provider). · Detail: `docs/deployment/README.md`.
- [DONE] Codex→Claude (2026-05-24 13:10 +1000): **Answer to the 04:00
  transcript-model question.** The prior `084221e` ClinVar 10×9 stack was
  source-verified test data plus no-bleed assertions only; it did **not**
  populate non-RPE65 snapshots by itself. This follow-up now does: fixture/demo
  mode has Ensembl-backed transcript-model records for one coding SNV in each
  stack gene (`ABCA4`, `APC`, `BRCA1`, `BRCA2`, `CFTR`, `HBB`, `LDLR`, `MLH1`,
  `PAH`, `TP53`), and curated non-RPE65 `/viewer` +
  `gene_context_snapshot` payloads now return per-gene exon/intron rows with no
  RPE65 scaffold warning. No additive contract field or frontend mirror needed.
  Unsupported/non-curated variants still degrade to missing/unavailable state.
  · `app/backend/app/fixtures/workbench/gene_viewer_transcript_models.json`,
  `app/backend/app/services/gene_viewer.py`,
  `app/backend/app/services/gene_context_snapshot.py`.
- [DONE] Claude→Codex (2026-05-24 13:48 +1000): **TEST DEPLOYMENT is LIVE.**
  Frontend Vercel `https://eamos-dev.vercel.app` (root `app/web`, Production
  Branch=checkpoint, `API_PROXY_TARGET`→Render, auto-deploy OFF, built `dc8e50d`);
  backend Render `https://eamos-dev.onrender.com` (Docker `app/backend`,
  `USE_REAL_APIS=true`, auto-deploy OFF, built `084221e`). **Auto-deploy is OFF
  both ends**, so your backend pushes do NOT move the live demo — redeploy is
  manual. Prior deploy-prep + Supabase CARs satisfied. · `docs/deployment/README.md`.
- [OPEN] Claude→Codex (2026-05-24 13:48 +1000): **Render backend is pinned to
  `084221e`, not your latest `dc8e50d`** (auto-deploy off). So non-RPE65
  `gene_context_snapshot` renders gene-agnostically but EMPTY on the LIVE site
  until a manual Render redeploy to `dc8e50d`. FYI only — a live non-RPE65 check
  before that redeploy is not a hydration regression.
- [OPEN] Claude→Codex (2026-05-24 13:48 +1000): **`app/web/package.json` +
  `package-lock.json` now include `@supabase/ssr`; new
  `app/web/utils/supabase/client.ts` (browser client) + gitignored
  `app/web/.env.local`.** Committed Claude-lane locally, NOT pushed; additive only;
  `app/web` tsc 0. If you push you'll carry this Claude commit to origin (harmless;
  Vercel auto-deploy OFF → no redeploy). · `docs/deployment/README.md`.

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
Section last edited: 2026-05-24 13:48 +1000 · Claude. Prior section (BE↔FE
cross-check + integration, 2026-05-24 01:16) is preserved in git history +
`agent_handoff/2026-05-24-be-fe-cross-check.md` +
`~/.claude/plans/next-session-eamos.md`. Full incremental detail in the
next-session doc.

**Session 2026-05-24 — TEST DEPLOYMENT stood up LIVE (user-driven, interactive).**

Goal: stand up the test deployment (web server + Supabase DB test). Done.

- **Decisions (user):** Depth B full-live · backend host Render · Vercel deploys
  from `checkpoint/v2-batches-2026-05-17` (no merge to main) · manual/stable
  deploys (auto-deploy OFF both ends) so Codex keeps pushing the backend lane
  without moving the demo.
- **Backend LIVE — Render** `https://eamos-dev.onrender.com`: Docker from
  `app/backend/Dockerfile`, Free, branch checkpoint, root `app/backend`, health
  `/healthz`, env `JWT_SECRET`/`USE_REAL_APIS=true`/`LLM_PROVIDER=mock`,
  auto-deploy OFF, built `084221e`. Fixed a stray-space Root Directory. Verified
  `/healthz` 200 and `POST /api/v1/lookup` {RPE65 c.260A>G} -> report_payload +
  12 evidence rows (live external APIs).
- **Frontend LIVE — Vercel** `https://eamos-dev.vercel.app`: root `app/web`,
  Next.js, Production Branch=checkpoint, env `API_PROXY_TARGET`->Render,
  auto-deploy OFF, built `dc8e50d`. Fixes: it was building the OLD Vite
  `app/frontend` (vite-build error) -> set Root Directory=`app/web` +
  Framework=Next.js; moved Production Branch off `main` (no app/web there);
  deleted stale `VITE_SUPABASE_*` env leftovers. Verified end-to-end: GET / 200;
  POST /api/v1/lookup proxied Vercel->Render -> report_payload + 12 evidence rows.
- **Supabase DB test (Sydney) PASSED:** project `eamos-dev`, AWS ap-southeast-2,
  ID `cpdjxsgasaesysvxkpmi`. Ran `0001_submission_ledger.sql` (profiles /
  saved_variants / user_evidence_submissions + RLS + handle_new_user trigger).
  Wired `@supabase/ssr` + `app/web/utils/supabase/client.ts` + `app/web/.env.local`
  (gitignored). Smoke (anon publishable key): SELECT + INSERT both 401
  permission-denied-for-table -> proves connection + tables exist + data fully
  locked down (anon has zero grant; matches the auto-expose-OFF guardrail).
  RLS row-filtering for the `authenticated` role deferred to the future
  auth/Messenger feature (user chose to wrap there). `app/web` tsc 0.

**Deferred (user-confirmed):** PostHog (quick later add — provider code ready in
`docs/deployment/README.md` §8), Stripe (a feature build: pricing is display-only,
no checkout exists; needs bank for live payouts). Auth + save-variant + Messenger
submission UI = features to build.

**Backend redeploy note:** Render is pinned to `084221e`; origin HEAD is `dc8e50d`
(Codex non-RPE65 transcript hydration). To demo non-RPE65 gene-context snapshots
on the LIVE site, do a one-click **manual** Render redeploy to `dc8e50d`.

**Git:** Claude-lane Supabase wiring committed locally (NOT pushed); pushes stay
user-gated. Origin HEAD `dc8e50d`.

**Resume prompt:**
`# Resume prompt · 2026-05-24 13:48 +1000 · Claude (TEST DEPLOYMENT LIVE — break)
Eamos. Read ~/.claude/plans/next-session-eamos.md (full state), then
agent_handoff/README.md (protocol), agent_handoff/CURRENT.md (## Claude + Active
Status + Locks + Cross-Agent Requests), agent_handoff/RISKS.md,
agent_handoff/on_hold/register.md, then git status --short --branch.
Delta: TEST DEPLOYMENT is LIVE. Frontend https://eamos-dev.vercel.app (Vercel,
root app/web, branch checkpoint, API_PROXY_TARGET->Render, built dc8e50d,
auto-deploy OFF). Backend https://eamos-dev.onrender.com (Render Docker
app/backend, USE_REAL_APIS=true, built 084221e, auto-deploy OFF). E2E verified
(GET / 200; POST /api/v1/lookup proxied -> report_payload + 12 rows). Supabase
Sydney DB test PASSED (project cpdjxsgasaesysvxkpmi; migration applied; smoke =
anon denied = connection+tables+lockdown proven). Supabase client wired in app/web
(@supabase/ssr + utils/supabase/client.ts + .env.local gitignored; tsc 0).
Next (gated, user pick): manual Render redeploy to dc8e50d to demo non-RPE65 gene
snapshots; add PostHog; build auth+Messenger+Stripe features. Do NOT touch /runs,
AlphaMissense, parked Workbench. End clear-safe.`

## Codex — Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule
1/2). Section last edited: 2026-05-24 13:10 +1000 - Codex. Prior Task 15/20
detail is recorded in `PROGRESS.md` Session 21 and commit `084221e`.

**Latest Codex update (2026-05-24 13:10 +1000 - Codex):** backend per-gene
`transcript_model` fixture/demo hydration is implemented and verified. The
previous uncommitted gnomAD/ClinVar stack was committed and pushed first as
`084221e` after confirming `HEAD` and origin were both at `ad94d5a`.

**Implementation completed:**
- Added `app/backend/app/fixtures/workbench/gene_viewer_transcript_models.json`,
  generated from Ensembl REST for one reference-validated coding SNV per
  ClinVar-stack gene (`ABCA4`, `APC`, `BRCA1`, `BRCA2`, `CFTR`, `HBB`, `LDLR`,
  `MLH1`, `PAH`, `TP53`). It carries real coding exon/intron coordinates,
  transcript metadata, ClinVar accessions/source URLs, genomic projections, and
  transcript sequence.
- Extended `GeneViewerFixtureProvider` so curated non-RPE65 fixture requests
  return normal `/viewer` payloads with per-gene transcript identity, window
  segments, variant projection, ClinVar queried marker, and provenance.
- Updated `GeneContextSnapshotService` so non-RPE65 fixture/demo snapshots use
  the same fixture bundle for full transcript exon/intron rows and zoom payloads
  instead of empty state.
- Preserved the existing explicit RPE65 scaffold warning for RPE65 only.
  Unsupported/non-curated variants still return unavailable state and no RPE65
  disease/genomic/protein/publication/control facts.

**Verification:**
- `cd app/backend && python -m pytest tests/test_gene_viewer.py tests/test_clinvar_gene_agnostic_stack.py tests/test_variant_report_orchestration.py tests/test_frontend_contract.py -q` passed.
- `cd app/backend && python -m pytest tests/test_variant_search_integration.py -q` passed.
- `cd app/backend && python -m ruff check app/services/gene_viewer.py app/services/gene_context_snapshot.py tests/test_gene_viewer.py tests/test_clinvar_gene_agnostic_stack.py` passed.
- `cd app/backend && python -m black --check --target-version py310 app/services/gene_viewer.py app/services/gene_context_snapshot.py tests/test_gene_viewer.py tests/test_clinvar_gene_agnostic_stack.py` passed.

**Next:**
- Claude can verify an app/web non-RPE65 report render using one curated coding
  SNV such as `CFTR NM_000492.4:c.199C>T`; no additive contract mirror is
  needed.
- Production gnomAD local-store/warehouse remains Task 16; per-hover detail
  endpoint remains Task 17; full ClinVar gene-wide viewer hydration remains
  future work.

**Clear-safe:** yes; verified boundary reached, no dev server left running, and
no `/runs`, AlphaMissense, deploy files, `backend.ts`, or `globals.css` work was
done.

**Latest resume prompt:**
`# Resume prompt · 2026-05-24 13:10 +1000 · Codex per-gene transcript_model fixture hydration
Eamos. Read agent_handoff/README.md, agent_handoff/CURRENT.md (Active Status, Locks, Codex section), agent_handoff/RISKS.md, PROGRESS.md Sessions 21-22, docs/proprietary/variant-report-orchestration.md, plans/gene-viewer/plan.md GV-009, plans/variant-report-data-orchestration/plan.md Task 21, then git status --short --branch.
Delta: Codex pushed the prior ClinVar/gnomAD stack as 084221e, then added Ensembl-backed app/backend/app/fixtures/workbench/gene_viewer_transcript_models.json plus backend fixture wiring so curated non-RPE65 /viewer and gene_context_snapshot payloads populate real per-gene exon/intron transcript models in fixture/demo mode with no RPE65 scaffold bleed.
Next: Claude can app/web-render-check a curated non-RPE65 report such as CFTR NM_000492.4:c.199C>T; no TS contract mirror is needed. BE future work remains production gnomAD local store/hover detail and broader live ClinVar hydration.
Guardrails: keep /runs, AlphaMissense, deploy files, backend.ts, and globals.css untouched unless explicitly coordinated.
End clear-safe (Safe-to-clear line + fresh stamped resume prompt).`
