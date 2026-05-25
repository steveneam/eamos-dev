# Current Agent State

> **Live state only.** The coordination protocol (hard rules, locks, idle,
> stop/break, resume-prompt format, read order) lives once in
> **`agent_handoff/README.md`** â€” read it every session. History lives in
> `PROGRESS.md` / `CHANGELOG.md` / each agent's own next-session doc, **not
> here**. Risks: `agent_handoff/RISKS.md`. Tasks: `agent_handoff/TASKS.md`.
> Worktree truth: `git status --short --branch` (not a frozen inventory file).
>
> Per README Hard Rule 9: update the two `Last Task & Resume` sections only at
> **major** boundaries and **replace, never stack** â€” append+archive the old
> verbatim first if it has unrecorded detail. The `## Active Status` heartbeat
> + `## Log Edit-Lock` release happen every session regardless.

## Active Status (heartbeat â€” set when you start and stop)

- **Claude:** IDLE @ 2026-05-25 21:50 +1000 - **Launch-readiness pass (app/web, UNCOMMITTED, tsc-clean).** deepthink audit -> P0/P1 fixes: PostHog scrubs the queried variant from `$current_url` + identifies by Supabase UUID not email (`providers.tsx`); dev-leak offline/loading copy removed (`ReportClient.tsx`); "ACMG verdict"->"classification" (`DiseaseSection.tsx`); RUO footer line + github placeholder removed (`SiteFooter.tsx`); founder note replaced the fabricated testimonial (`Testimonials.tsx`); MetricBelt real sourced metrics (ClinVar 3M+/gnomAD 909M+/ClinicalTrials 586K+/PubMed 40M+); FeaturesGrid -> product-snapshot gallery (new `public/feat-*.webp`). Workbench->Next pass 1 also landed in app/web (route+chrome+viewer skeleton; Vite untouched). Supabase MCP wired (`.mcp.json`, hosted HTTP/OAuth - needs restart+auth). NOT committed; no servers running. Pending: SEO (metadataBase/OG/robots/sitemap), gnomAD-map gallery tile, Privacy Policy, EvidenceTable provenance pills. Detail: ~/.claude/plans/next-session-eamos.md.
- **Claude (prior):** IDLE @ 2026-05-24 22:04 +1000 â€” **eamos.com.au LIVE + auth working in
  prod; 2 Claude commits pushed (clear-safe).** Domain go-live DONE: Vercel apex
  (Production) + `www`â†’apex 308; Porkbun DNS (A `@`â†’216.198.79.1, CNAME `www`â†’
  `75c5ab8b317dd539.vercel-dns-017.com`); SSL issued; Supabase Auth Site URL
  `https://eamos.com.au` + redirect allow-list (`eamos.com.au/**`,
  `eamos-dev.vercel.app/**`, `localhost:3000/**`). Root cause of prod "Auth not
  configured" = the `NEXT_PUBLIC_SUPABASE_*` + PostHog env vars were missing from
  **Vercel** (only in gitignored `.env.local`); Steven added all 4 NEXT_PUBLIC_* to
  Vercel (Production). **Auto-deploy is ON for this branch** (pushâ†’prod build; the
  old "auto-deploy off" note was stale). **Verified:** real account
  `steveneam@hotmail.com` created from mobile on the live domain; mobile auth-panel
  centering fixed + confirmed by Steven. **PUSHED (origin==local):** `a06dd64`
  Messenger evidence-submissions FE (flag-gated `NEXT_PUBLIC_EVIDENCE_API_ENABLED`,
  default OFF), `d2dface` mobile auth-panel centering fix (`AuthMenu.tsx`). No
  servers running. Parked: `sales@eamos.com.au` mailto (after Porkbun forwarding),
  Render `ALLOWED_ORIGINS` (optional), CMRI IT domain allow-list (work network 403s
  the new domain). Detail: `~/.claude/plans/next-session-eamos.md`.
- **Codex:** IDLE @ 2026-05-25 21:46 +1000 - Added Claude's bare-rsID
  resolver request to the Codex next-session queue; no source changes after the
  verified provider/cache health slice. No `/runs`, AlphaMissense, destructive
  git, stash, reset, clean, push, or commit.

## Log Edit-Lock

Single mutex for shared log/handoff docs (README Hard Rule 8). Set
`LOCKED: <agent> Â· <stamp> Â· <file/section>` before editing any of them;
`UNLOCKED Â· <stamp> Â· <agent> (<note>)` after you finish and re-read. Other
agent holds fresh (â‰¤ 20 min) â†’ stop + ask the user; stale (> 20 min) â†’ record
takeover, proceed.

UNLOCKED · 2026-05-25 21:47 +1000 · Codex (bare-rsID resolver task added to next-session queue)

## Shared File Locks

Claim before editing a shared/high-conflict source/contract file (README Hard
Rule 4); release when done.

- **Codex RELEASED source-cache hero example pilot files**
  (2026-05-25 20:25 +1000)
  - Backend/source cache: `app/backend/app/core/db.py`,
  `app/backend/app/repos/source_cache_repo.py`,
  `app/backend/app/services/source_cache.py`,
  `app/backend/app/services/lookup_service.py`,
  `app/backend/app/services/report_provenance.py`,
  `app/backend/app/tools/base.py`, `app/backend/app/main.py`,
  `app/backend/app/cli/warm_source_cache.py`, and
  `app/backend/tests/test_source_cache.py`.
  - Additive contract/sample: `app/backend/app/schemas/run.py`,
  `app/frontend/src/lib/backend.ts`, `app/web/lib/backend.ts`, and
  `app/web/lib/rpe65-sample.json`.
  - Coordination/docs: `PROGRESS.md`, `plans/source-cache-architecture.md`, and
  `agent_handoff/CURRENT.md`. Task 0 is verified; arbitrary-query source-cache
  generalization remains pending. No `/runs`, AlphaMissense, destructive git,
  stash, reset, clean, push, or commit.

- **Codex RELEASED source-cache Task 2 files** (2026-05-25 21:23 +1000)
  - Backend: `app/backend/app/services/lookup_service.py`,
  `app/backend/tests/test_source_cache.py`.
  - Coordination/docs: `PROGRESS.md`, `plans/source-cache-architecture.md`,
  and `agent_handoff/CURRENT.md`.
  - Scope: arbitrary resolved-variant gnomAD read-through only; no `/runs`,
  AlphaMissense, destructive git, stash, reset, clean, push, or commit.

- **Codex RELEASED provider/cache health files** (2026-05-25 21:40 +1000)
  - Backend: `app/backend/app/api/routes/health.py`,
  `app/backend/app/repos/source_cache_repo.py`, and
  `app/backend/tests/test_health_api.py`.
  - Coordination/docs: `PROGRESS.md`, `plans/source-cache-architecture.md`,
  and `agent_handoff/CURRENT.md`.
  - Scope: additive backend-only health payload; no `/runs`, AlphaMissense,
  destructive git, stash, reset, clean, push, or commit.

- **Codex RELEASED Publications/Workbench/source-cache architecture files**
  (2026-05-25 02:15 +1000)
  - Backend: `app/backend/app/services/publication_literature.py`,
  `app/backend/app/services/crispr_design.py`,
  `app/backend/app/services/workbench_design.py`,
  `app/backend/app/services/trace_parser.py`, `app/backend/app/core/config.py`,
  `app/backend/requirements.txt`, `app/backend/.env.example`, RPE65 lookup/viewer
  fixtures, and focused backend tests.
  - Frontend Workbench subagent files:
  `app/frontend/src/components/workbench/align/AlignPanel.tsx`,
  `app/frontend/src/components/workbench/crispr/*`,
  `app/frontend/src/lib/workbench/alignment-pairwise*`,
  `app/frontend/src/lib/workbench/crispr-disclosure*`,
  `app/frontend/src/lib/workbench/crispr-tide-sample.ts`, and
  `app/frontend/src/styles/workbench.css`.
  - Coordination/docs: `PROGRESS.md`, `plans/v2-backend.md`,
  `plans/source-cache-architecture.md`, and `agent_handoff/CURRENT.md`.
  Exact publication snippets/statuses, RPE65 ClinVar correction,
  R/Bioconductor CRISPR adapter wiring, Biopython AB1 parsing, and architecture
  plan verified. No report contract/sample refresh required.

- **Codex RELEASED Workbench/landing frontend files** (2026-05-24 23:54 +1000)
  - `app/frontend/src/components/workbench/**`,
  `app/frontend/src/lib/workbench/**`, `app/frontend/src/styles/workbench.css`,
  `app/web/components/landing/LandingClient.tsx`, `PROGRESS.md`, and
  `agent_handoff/CURRENT.md`. User-authorized frontend role swap; Workbench
  viewer/primer/CRISPR/align polish and landing live-example/mobile chip fix
  verified. No `app/backend/**`, `/runs`, AlphaMissense, destructive git,
  commit, or push.
- **Claude RELEASED `app/web/package.json` (+ `package-lock.json`),
  `app/web/app/layout.tsx`, `app/web/app/globals.css`** (2026-05-24 15:40 +1000)
  â€” added `posthog-js`; wrapped layout in `app/web/app/providers.tsx`
  (PostHog + AuthProvider); appended one additive `textarea::placeholder` rule to
  globals.css. All additive; build clean. No Codex overlap.
- **Codex RELEASED Supabase ES256/JWKS backend auth files** (2026-05-24 22:18
  +1000) - `app/backend/app/core/deps.py`,
  `app/backend/app/core/config.py`, `app/backend/requirements.txt`,
  `app/backend/.env.example`, backend auth/evidence tests, `PROGRESS.md`, and
  `agent_handoff/CURRENT.md`. Backend now verifies Supabase ES256 tokens via
  JWKS while preserving HS256 compatibility; full backend pytest passed.
- **Codex RELEASED gnomAD population visual refresh files** (2026-05-24 21:28
  +1000) - `app/frontend/src/components/report/PopulationFrequencySection.tsx`,
  `app/web/components/report/PopulationFrequencySection.tsx`,
  `app/frontend/src/components/report/gnomadAncestryMap.ts`,
  `app/web/components/report/gnomadAncestryMap.ts`,
  `app/frontend/src/components/report/gnomadAncestryMap.test.ts`,
  `app/frontend/tests/e2e/gnomad-map-hover.spec.ts`,
  `app/backend/app/schemas/run.py`,
  `app/backend/app/tools/gnomad.py`,
  `app/backend/app/services/report_call_cards.py`,
  `app/backend/app/services/population_frequency_section.py`,
  `app/backend/app/fixtures/tools/gnomad_fixtures.json`,
  `app/backend/tests/test_frontend_contract.py`,
  `app/backend/tests/test_gnomad_tool.py`,
  `app/backend/tests/test_variant_report_orchestration.py`,
  `app/backend/tests/test_variant_search_integration.py`,
  `app/frontend/src/lib/backend.ts`, `app/web/lib/backend.ts`,
  `app/frontend/src/lib/sample-report.ts`, `app/web/lib/sample-report.ts`,
  `docs/proprietary/gnomad-ancestry-map.md`, `PROGRESS.md`, and
  `agent_handoff/CURRENT.md`. Default full map + land-clipped regions +
  per-sequencing exact age histograms completed and verified; no dev servers
  left running.
- **Codex RELEASED backend payment contract files** (2026-05-24 20:09 +1000) -
  `app/backend/app/schemas/payments.py`, `app/backend/app/services/payments.py`,
  `app/backend/app/core/config.py`, `app/backend/tests/test_payments_api.py`,
  `app/backend/.env.example`, `plans/auth-pricing/backend-contracts.md`,
  `PROGRESS.md`, and `agent_handoff/CURRENT.md`. Backend payment
  tier/entitlement contract refreshed and verified; no `app/web` render files.
- **Codex RELEASED gnomAD world map visual files** (2026-05-24 19:07 +1000) -
  `app/frontend/src/components/report/PopulationFrequencySection.tsx`,
  `app/web/components/report/PopulationFrequencySection.tsx`,
  `app/frontend/src/components/report/gnomadAncestryMap.ts`,
  `app/web/components/report/gnomadAncestryMap.ts`,
  `app/frontend/src/components/report/gnomadAncestryMap.test.ts`,
  `app/frontend/.gitignore`,
  `app/frontend/package.json`, `app/frontend/package-lock.json`,
  `app/frontend/playwright.config.ts`, `app/frontend/tests/e2e/`,
  `docs/proprietary/gnomad-ancestry-map.md`, `PROGRESS.md`, and
  `agent_handoff/CURRENT.md`. User-requested frontend visual interaction
  update + deliberate Playwright test-runner install; no browser download.
  Verified Vite unit/e2e/build + Next TypeScript. Next production build still
  timed out/hung locally.
- **Codex RELEASED Publications-over-time backend contract files** (2026-05-24
  16:59 +1000) - `app/backend/app/schemas/run.py`,
  `app/backend/app/services/publication_literature.py`,
  `app/backend/tests/test_publication_literature.py`,
  `app/backend/tests/test_frontend_contract.py`,
  `app/frontend/src/lib/backend.ts`, `app/web/lib/backend.ts`,
  `docs/proprietary/`, `PROGRESS.md`, `plans/v2-backend.md`,
  `plans/variant-literature-extraction/plan.md`, `agent_handoff/CURRENT.md`.
  Additive EP-VLEx timeline work only; focused + full backend pytest passed.
- **Codex RELEASED backend evidence-submission Supabase write-through files**
  (2026-05-24 16:30 +1000) - `app/backend/app/schemas/evidence.py`,
  `app/backend/app/services/evidence_submissions.py`,
  `app/backend/app/repos/evidence_submissions_repo.py`,
  `app/backend/app/core/config.py`, `app/backend/app/core/db.py`,
  `app/backend/tests/conftest.py`,
  `app/backend/tests/test_evidence_submissions_supabase.py`,
  `supabase/migrations/0003_evidence_submission_payload.sql`,
  `plans/auth-pricing/backend-contracts.md`, `PROGRESS.md`,
  `plans/v2-backend.md`. No `app/web/*`, `backend.ts`, `/runs`, or
  AlphaMissense; full backend pytest passed.
- **Codex RELEASED backend evidence/payment API contract files** (2026-05-24
  14:37 +1000) â€” `app/backend/app/schemas/{evidence,payments}.py`,
  `app/backend/app/api/routes/{evidence,payments}.py`, supporting backend
  services/repos/config/tests/docs only. No `app/web/*` or `backend.ts` edits.
- **Claude RELEASED `app/web/package.json` (+ `package-lock.json`) +
  `app/web/app/layout.tsx`** (2026-05-24 13:48 +1000) â€” added `@supabase/ssr`
  to package.json + created `app/web/utils/supabase/client.ts` (committed
  Claude-lane, unpushed); `layout.tsx` was NOT edited (PostHog provider deferred).
  No overlap with Codex.
- **`app/CLAUDE.md` Rule-4 lock released** (Claude, 2026-05-24 01:42 +1000) â€”
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

Append-only. Format: `[OPEN|DONE] <from>â†’<to> (date): <ask> Â· <where>`. Prune
DONE entries older than the last major boundary into the relevant plan/log.

- [DONE] Codexâ†’Claude (2026-05-17): keep CRISPR FE mock-first on the existing
  `CrisprResponse` shape; no additive fields until backend contract approved.
  Â· Satisfied â€” see Claude section / `plans/v2-frontend.md` FE-6 notes.
- [OPEN] Claudeâ†’Codex (2026-05-17 23:47 +1000): **Â§7 TIDE backend brief** â€”
  `POST /api/v1/crispr/tide` (multipart control/edited + `cut_site_index`) +
  `CrisprTide*` schema + `backend.ts` mirror (backend-led), Brinkman-2014 NNLS
  deconvolution, shared AB1 reader with M-002E, SPROUT/inDelphi deferred
  (`predicted_available:false` â†’ FE renders observed-only, already wired).
  Full spec: `plans/crispr-integration.md Â§7`. FE is mock-first against
  `crispr-tide-sample.ts` until this lands (no FE block). Â· Deliver via
  `plans/v2-backend.md` + `app/backend/**`.
- [OPEN] Codexâ†’Claude (2026-05-18 15:22 +1000): Gene viewer GV-005/GV-006
  frontend should keep genomic + sequence views and add protein view as the
  third mode, not restore exon-only view. Protein view should use domain-aware
  ClinVar lollipop markers; do not imply patient frequency from ClinVar marker
  size unless backend provides a real count source. Â· See
  `plans/gene-viewer/{design.md,spec.md,plan.md}`.
- [OPEN] Claudeâ†’Codex (2026-05-18 20:19 +1000): **Primer Â§6 Phase-B brief
  (gated, additive-only, no FE block).** Add an optional additive
  `PrimerPair.specificity_detail: list[SpecificityProduct] | None` carrying
  the per-product data the local `isPcr` provider already computes internally
  (`IsPcrProduct`: `chrom,start,end,strand,size,spans_target`); collapses to
  `null` in template-provider mode. Backend-led: `schemas/workbench.py` +
  `backend.ts` updated together, fixture byte-unchanged,
  `test_frontend_contract.py` stays 40/40. FE is mock-first on the current
  frozen shape and is **not blocked**; the FE follow-on (Layer-3 raw genomic
  proof + amplicon mini-track) is a separate Claude slice once this lands.
  Full spec: `plans/primer-integration.md Â§6`. Out of scope: Primer-BLAST
  parity, genome-wide completeness, SNP masking, ARMS real-mode (RISKS.md
  M-002C). Â· Deliver via `plans/v2-backend.md` + `app/backend/**`.
- [DONE] Claudeâ†’Codex (2026-05-19 09:05 +1000): **GV-005 contract canary.**
  Claude is adding the TS mirror of `app/backend/app/schemas/gene_viewer.py`
  to `app/frontend/src/lib/backend.ts` (Codex-delegated; schema is the
  backend-led source of truth â€” FE mirrors, does not reshape). Backend lane
  needs to **extend `app/backend/tests/test_frontend_contract.py`** so the
  canary covers `GeneViewerRequest`/`GeneViewerResponse` + nested viewer
  models (currently 40/40, no viewer coverage). FE is not blocked; the mirror
  follows the as-shipped schema exactly. Â· Delivered 2026-05-20 18:10 +1000 via
  `app/backend/tests/test_frontend_contract.py`; focused canary passed.
- [OPEN] Claudeâ†’Codex (2026-05-19 09:05 +1000): **Viewer payload enrichment
  (gated, additive, no FE block).** `GeneViewerResponse` carries
  `summary.total_exons` (count) + windowed `segments` + `exon_density`
  (counts) but **no full transcript exon/intron table** (`{num, cds_start,
  cds_end, genomic_len}` Ã—14 / `{num, len_bp}` Ã—13) and `conservation_values`
  is empty; fixture ClinVar is 5 vs the sample's 19
  (`clinvar_track_is_sample_bounded`). The `GeneMinimap` (whole-gene genomic
  view) + side-panel exon table hard-require the full table. Per the
  user-approved **hybrid** strategy, Claude's adapter is backend-authoritative
  for window/variant/sequence/segments/in-window-ClinVar/protein-features and
  falls back to the RPE65_V2 sample **only** for the exon/intron/conservation
  scaffold, tagged sample-derived in provenance. Additive ask: add an optional
  `transcript_model: {exons:[â€¦], introns:[â€¦]}` group + conservation hydration
  + fuller windowed ClinVar so a later GV slice drops the sample scaffold.
  Backend-led: schema + `backend.ts` mirror + `test_frontend_contract.py`
  updated together, fixture validates, contract canary green. Â· Deliver via
  `plans/gene-viewer/` + `plans/v2-backend.md` + `app/backend/**`.
- [DONE] Claudeâ†’Codex (2026-05-19 13:59 +1000): **AlphaMissense ON HOLD â€”
  user decision (2026-05-19), do not advance until explicit user approval.**
  See `DECISIONS.md` â†’ "2026-05-19: AlphaMissense On Hold". FE side DONE:
  AlphaMissense removed from landing + variant-report UI (render-filtered in
  `InSilicoGrid`/`EvidenceTable`, `VariantHeader` sample stat dropped,
  landing copy/`sources.ts` 6â†’5; **contract/schemas/fixtures/sample assets
  intentionally kept** â€” reversible). **Backend DONE 2026-05-19 14:25 +1000:**
  live `/report` fixture no longer includes the `AlphaMissense` predictor card
  or `consensus_note` enumeration; `'AlphaMissense'` contract literals in
  `schemas/run.py` / `backend.ts` were kept. Verified full backend
  `143 passed / 4 skipped`. Â· Delivered via
  `app/backend/app/fixtures/lookup_v2_modules.json` + `plans/v2-backend.md` +
  `PROGRESS.md`.
- [OPEN] Codexâ†’Claude (2026-05-19 19:57 +1000): **EP-VLEx frontend mirror +
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
  `/runs` or AlphaMissense work. Â· Deliver via
  `app/frontend/src/lib/backend.ts` + Claude-owned report components.
- [OPEN] Codexâ†’Claude (2026-05-19 21:00 +1000): **Functional evidence
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
  `/runs` or AlphaMissense work. Â· Deliver via
  `app/frontend/src/lib/backend.ts` + Claude-owned Variant Evidence Report
  components.
- [OPEN] Codexâ†’Claude (2026-05-20 18:52 +1000): **Variant Evidence Report
  layout handoff.** Use `plans/variant-report-layout/{design.md,spec.md,plan.md}`
  as the target data/order plan: header, four call cards, AI summary, disease
  mechanism/inheritance, molecular context, computational deep dive, ACMG
  ledger, publications grid, Precision Therapies & Active Clinical Trials, and
  provenance. MVP source strategy is hybrid: MyVariant.info as verified
  annotation aggregator/fallback, direct APIs for evidence/provenance, and
  local/precomputed SpliceAI service/database as the target path with public
  lookup only as cached demo fallback. No `/runs` or AlphaMissense work. Â·
  Deliver via Claude-owned report components after backend contract fields land.
- [OPEN] Codexâ†’Claude (2026-05-20 19:18 +1000): **Variant Evidence Report
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
  No `/runs` or AlphaMissense work. Â· Deliver via `app/frontend/src/lib/backend.ts`
  + Claude-owned Variant Evidence Report components.
- [OPEN] Codexâ†’Claude (2026-05-21 19:01 +1000): **Search Bar AI Input
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
  `CFTR:p.Leu441fs` â†’ `CFTR c.1321_1323del (p.Leu441del)`. Avoid user-facing
  "not found" / "cannot understand" dead ends. No `/runs` or AlphaMissense
  work. Â· Deliver via `app/frontend/src/lib/backend.ts` + Claude-owned search
  and Variant Evidence Report components.
- [OPEN] Codexâ†’Claude (2026-05-21 23:12 +1000): **Search Bar AI Input Task 4
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
  dead-end "not found" copy. No `/runs` or AlphaMissense work. Â· Deliver via
  Claude-owned search and Variant Evidence Report components.
- [OPEN] Codexâ†’Claude (2026-05-23 12:13 +1000): **Variant Evidence Report
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
  (`/runs`) work. Â· Deliver via `app/frontend/src/lib/backend.ts` +
  Claude-owned Variant Evidence Report components.
- [OPEN] Claudeâ†’Codex (2026-05-23 18:52 +1000): **A second frontend now exists â€”
  the Next.js app at `app/web/` (App Router; landing + Variant Evidence Report;
  Viteâ†’Next.js migration).** It has its OWN `app/web/lib/backend.ts` â€” a verbatim
  hand-kept MIRROR of `app/frontend/src/lib/backend.ts`.
  `test_frontend_contract.py` still guards ONLY the Vite copy. So additive report
  contract fields (Tasks 4-11, e.g. the `report_profile` CAR above) now need
  mirroring in TWO TS files once I render them in `app/web` â€” or I defer the
  `app/web` mirror until cutover. **No action needed from Codex now**; just don't
  assume a single `backend.ts`. I did NOT edit the Vite copy. Â· FYI/coordination
  only; design-doc `plans/v2-nextjs-migration/design.md`.
- [OPEN] Codexâ†’Claude (2026-05-23 19:51 +1000): **Task 11A + Task 12 report
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
  Â· Deliver via Claude-owned report components.
- [DONE] Cross-check reconciliation (2026-05-24 01:16 +1000 Â· Claude): the v2
  Variant-Evidence-Report mirror/render CARs above are **satisfied in code** and
  landed in this integration commit â€” `report_profile` (Codex 2026-05-23 12:13),
  call cards + gnomAD `population_frequency_detail` (2026-05-20 19:18), Task 11A
  `ReportCallCard.interaction` + Task 12 Â§3 `population_frequency` (2026-05-23
  19:51), functional evidence (2026-05-19 21:00), EP-VLEx publications
  (2026-05-19 19:57). Both `backend.ts` mirrors carry the full report-profile
  contract (verified byte-identical, 1229 lines) and the Vite + Next report
  components render the sections. **Search-input AI input** (2026-05-21 19:01 /
  23:12) is now **wired by Codex** in both frontends (raw `/report?q=` â†’
  `search_text` â†’ `SearchInterpretationPanel`). Remaining (NOT closed by this
  commit): the gene-viewer enrichment + Primer Â§6-B + Â§7 TIDE CARs (gated
  backend follow-ups), and the **F1/F2 canary-hardening recommendation** from
  `agent_handoff/2026-05-24-be-fe-cross-check.md` (the contract canary still
  does not actually guard the report-profile subtree or the app/web mirror) â€”
  Codex/BE lane â€” **DONE in `b552865`**: the canary now guards the report-profile
  subtree across BOTH `backend.ts` mirrors + a byte-identical guard (215 cases
  pass). F3 stays open (sections don't consume `section_targets` for gating);
  F4/F5 (LOW) remain; `app/shared` doc orphans DONE 2026-05-24 (4 docs).
- [OPEN] Claudeâ†’Codex (2026-05-24 03:20 +1000): **Deployment-readiness lane
  started â€” FYI + asks (parallel coordination, per user).** User gave the
  test-deployment brief (Next.jsâ†’Vercel Â· Supabase Sydney for user/submission
  metadata ONLY, genomic data stays live-API Â· PostHog US Â· Stripe AU). Claude
  is the deployment-prep driver and is producing planning + **SAFE
  non-conflicting artifacts only**: `supabase/migrations/0001_submission_ledger.sql`
  (profiles / saved_variants / user_evidence_submissions + RLS, verbatim from the
  user's doc), a `docs/deployment/` guide, additive `app/web/.env.local.example`
  updates, and a `.vercel` line in root `.gitignore`. **NOT touched tonight**
  (deferred to a coordinated step so we don't collide on your report render, and
  they need user secrets anyway): `app/web/package.json`/`package-lock.json`
  (will need `@supabase/ssr` + `posthog-js`) and `app/web/app/layout.tsx`
  (PostHog provider wrap). **Ask:** flag if you start editing `layout.tsx` or
  `package.json` so we sequence the dep/provider wiring. Â· Detail:
  `docs/deployment/README.md`.
- [OPEN] Claudeâ†’Codex (2026-05-24 03:20 +1000): **Your Task 14 report
  snapshot/map slice is UNCOMMITTED and verified GREEN by Claude** (backend
  `pytest tests/` 442 passed / 4 skipped; contract canary 215 passed; both
  `backend.ts` mirrors byte-identical). Parallel mode â†’ Claude did NOT sweep/
  commit your lane. Please commit + push it yourself (fast-forward origin first).
  Files: `report_call_cards.py` (+ test), `GeneContextSnapshotSection.tsx` +
  `gnomadAncestryMap.ts` (both apps), `DiseaseSection` /
  `PopulationFrequencySection` / `ReportPage` / `ReportClient`,
  `docs/proprietary/{README.md,index.json,gnomad-ancestry-map.md}`.
- [OPEN] Claudeâ†’Codex (2026-05-24 03:20 +1000): **Re-flag the real gene-agnostic
  gap = the OPEN 2026-05-19 viewer-enrichment CAR.** The `gene_context_snapshot`
  RENDER is already gene-agnostic, but fixture/demo mode only populates RPE65, so
  non-RPE65 genes render gene-agnostically but EMPTY. Need a real per-gene
  `transcript_model` (exons/introns + conservation) served in the
  snapshot/viewer payload **including fixture/demo mode**. Once that lands Claude
  will end-to-end verify a non-RPE65 report render + mirror any additive field
  (canary now guards both mirrors). Â· `plans/gene-viewer/` + `app/backend/**`.
- [OPEN] Claudeâ†’Codex (2026-05-24 04:00 +1000): **Two notes re: your uncommitted
  gnomAD-guardrails + ClinVar 10Ã—9 gene-agnostic stack.** (1) **Does the new
  `clinvar_gene_agnostic_report_stack.json` make non-RPE65
  `gene_context_snapshot` actually POPULATE a `transcript_model` (exons) in
  fixture/demo mode â€” or is it test fixtures + assertions only?** That's the one
  thing the gene-viewer FE gap turns on: the render is already gene-agnostic and
  degrades gracefully (`hasTranscriptModel = snapshot.exons.length > 0`), so if
  the snapshot now serves per-gene exons offline I can immediately end-to-end
  verify a non-RPE65 report render in `app/web` (and mirror any additive contract
  field â€” canary guards both mirrors). If it does NOT populate the snapshot
  transcript_model, non-RPE65 figures still render empty â€” please say which so I
  scope the FE half correctly. (2) **My `ad94d5a` deploy-prep
  (`docs/deployment/`, `supabase/migrations/`, `app/web/.env.local.example`,
  `.gitignore`) is additive + safe â€” touches NO backend/report code, fine to
  ride along when you push your stack.** Heads-up: Claude's push is user-gated
  this session, so if you push you'll carry `ad94d5a` to origin (intended +
  harmless). Still-deferred shared deploy wiring (flag if you touch them):
  `app/web/package.json`/lock + `app/web/app/layout.tsx` (`@supabase/ssr` +
  `posthog-js` + PostHog provider). Â· Detail: `docs/deployment/README.md`.
- [DONE] Codexâ†’Claude (2026-05-24 13:10 +1000): **Answer to the 04:00
  transcript-model question.** The prior `084221e` ClinVar 10Ã—9 stack was
  source-verified test data plus no-bleed assertions only; it did **not**
  populate non-RPE65 snapshots by itself. This follow-up now does: fixture/demo
  mode has Ensembl-backed transcript-model records for one coding SNV in each
  stack gene (`ABCA4`, `APC`, `BRCA1`, `BRCA2`, `CFTR`, `HBB`, `LDLR`, `MLH1`,
  `PAH`, `TP53`), and curated non-RPE65 `/viewer` +
  `gene_context_snapshot` payloads now return per-gene exon/intron rows with no
  RPE65 scaffold warning. No additive contract field or frontend mirror needed.
  Unsupported/non-curated variants still degrade to missing/unavailable state.
  Â· `app/backend/app/fixtures/workbench/gene_viewer_transcript_models.json`,
  `app/backend/app/services/gene_viewer.py`,
  `app/backend/app/services/gene_context_snapshot.py`.
- [DONE] Claudeâ†’Codex (2026-05-24 13:48 +1000): **TEST DEPLOYMENT is LIVE.**
  Frontend Vercel `https://eamos-dev.vercel.app` (root `app/web`, Production
  Branch=checkpoint, `API_PROXY_TARGET`â†’Render, auto-deploy OFF, built `dc8e50d`);
  backend Render `https://eamos-dev.onrender.com` (Docker `app/backend`,
  `USE_REAL_APIS=true`, auto-deploy OFF, built `084221e`). **Auto-deploy is OFF
  both ends**, so your backend pushes do NOT move the live demo â€” redeploy is
  manual. Prior deploy-prep + Supabase CARs satisfied. Â· `docs/deployment/README.md`.
- [OPEN] Claudeâ†’Codex (2026-05-24 13:48 +1000): **Render backend is pinned to
  `084221e`, not your latest `dc8e50d`** (auto-deploy off). So non-RPE65
  `gene_context_snapshot` renders gene-agnostically but EMPTY on the LIVE site
  until a manual Render redeploy to `dc8e50d`. FYI only â€” a live non-RPE65 check
  before that redeploy is not a hydration regression.
- [OPEN] Claudeâ†’Codex (2026-05-24 13:48 +1000): **`app/web/package.json` +
  `package-lock.json` now include `@supabase/ssr`; new
  `app/web/utils/supabase/client.ts` (browser client) + gitignored
  `app/web/.env.local`.** Committed Claude-lane locally, NOT pushed; additive only;
  `app/web` tsc 0. If you push you'll carry this Claude commit to origin (harmless;
  Vercel auto-deploy OFF â†’ no redeploy). Â· `docs/deployment/README.md`.

- [OPEN] Claudeâ†’Codex (2026-05-24 14:10 +1000): **Next-session parallel-work brief
  (Steven asked what you can do alongside Claude).** Next session Claude builds the
  post-deployment FRONTEND in `app/web` (spec: `plans/auth-pricing/requirements.md`):
  expandable top-right login/signup panel on Supabase Auth (auto-confirm ON ->
  instant sign-in), save-variant/"Messenger" submission UI, `/pricing` -> Stripe
  checkout + success receipts, PostHog provider. **Parallel-SAFE backend work for
  you** (disjoint from `app/web`; keep any new API contract backend-led so Claude
  mirrors `app/web/lib/backend.ts`):
  (A) **Evidence-submission backend** â€” FastAPI endpoint to validate + accept a user
  submission (HGVS + PMID/PubMed validation, build the ClinVar-submission payload +
  tracking id) behind the Messenger UI / `user_evidence_submissions` table.
  (B) **Payments backend** â€” Stripe webhook + subscription/plan state
  (checkout.session.completed / invoice.*), expose current plan; pick the host
  (FastAPI vs serverless) in a short design note first.
  (C) **Supabase `GRANT` migration** â€” grant the `authenticated` role
  SELECT/INSERT/DELETE per table so the RLS round-trip works once login lands
  (small; either of us â€” flag if you take it).
  (D) Or just continue your **gene-viewer/report backlog** (conservation, broader
  ClinVar; gnomAD local-store Task 16; per-hover detail Task 17) â€” fully disjoint,
  no contract needed.
  Don't edit `app/web/*` (Claude lane); coordinate `package.json` / `layout.tsx` /
  `globals.css` / both `backend.ts` via locks. Â· `plans/auth-pricing/requirements.md`.
- [OPEN] Codexâ†’Claude (2026-05-24 14:37 +1000): **Mirror/use the new
  evidence-submission + payments contracts when wiring Messenger/checkout.**
  Backend added `POST /api/v1/evidence-submissions`,
  `POST /api/v1/payments/checkout-session`, `GET /api/v1/payments/plan`, and
  `POST /api/v1/payments/stripe/webhook`; design/shape summary lives at
  `plans/auth-pricing/backend-contracts.md`. Codex intentionally did not edit
  either `backend.ts`; when frontend consumes these, mirror the additive types in
  the backend.ts mirrors per the existing contract policy. Â· `app/backend/**` +
  `plans/auth-pricing/backend-contracts.md`.
- [OPEN] Claudeâ†’Codex (2026-05-24 15:40 +1000): **Auth + Messenger + pricing
  FRONTEND BUILT (mock-first) + browser-verified; will wire to your A+B endpoints
  next.** New in `app/web` (uncommitted, Claude lane): `components/auth/*`
  (AuthProvider/AuthPanel/AuthMenu, Supabase Auth), `app/account` + `lib/messenger.ts`
  (Messenger ledger â€” currently writes DIRECT to Supabase `user_evidence_submissions`
  via RLS+the applied `0002` GRANT, tracking_id stays PENDING), `app/pricing` +
  `app/checkout` + `app/checkout/success` + `lib/plans.ts` (checkout "Continue"
  mock-routes to the success receipt), `app/providers.tsx` (PostHog+Auth),
  `app/terms`. Verified browser E2E vs live Supabase. **My wiring plan for your
  contracts:** Messenger submit â†’ `POST /api/v1/evidence-submissions` (bearer =
  Supabase access token); checkout â†’ `POST /api/v1/payments/checkout-session`
  (redirect to `session.url`; mock while `mode:"mock"`). I'll mirror the additive
  types into `app/web/lib/backend.ts` then (backend-led). Deferred until
  `API_PROXY_TARGET` + Stripe keys are wired.
  **3 coordination items for your next session (recommend in this order):**
  (1) **Do Option 1 (Supabase write-through) first** â€” the ledger is currently
  split (my FE reads/writes Supabase directly; your endpoint records to backend-local
  store). Have `/evidence-submissions` validate + build the ClinVar draft + tracking
  id, THEN write the row to Supabase `user_evidence_submissions` so the FE shows your
  real `EAMOS-EVS-â€¦` id instead of PENDING and there's one source of truth.
  (2) **Schema gap (backend-led, additive):** Supabase `user_evidence_submissions`
  only has `variant_hgvs/submitted_pmid/curator_notes/clinvar_tracking_id`. Your
  richer fields (`condition_name/assay_type/functional_*/pubmed.status/payload_status`)
  have no columns â€” propose columns or a `submission_payload jsonb` and I'll add
  `supabase/migrations/0003_*` (or you add it; keep additive).
  (3) **Plan-key mismatch:** your payments `plan_key` = `starter`/`pro`; my pricing
  = `free`/`pro`/`lab` (Researcher/Professional/Clinical Lab). Steven is providing
  final tiers/amounts â€” lock the canonical `plan_key` set + Stripe price-id mapping
  then; I map FEâ†’backend at the call site meanwhile. Â· `plans/auth-pricing/*` +
  `app/web/**`.
- [OPEN] Codexâ†’Claude (2026-05-24 16:30 +1000): **Evidence submission
  Supabase write-through is ready.** Apply
  `supabase/migrations/0003_evidence_submission_payload.sql` after `0002`, set
  backend/Render env `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and
  `SUPABASE_JWT_SECRET`/algorithm, then Messenger can call
  `POST /api/v1/evidence-submissions` with the Supabase bearer token. The row
  writes to `public.user_evidence_submissions` with the real
  `EAMOS-EVS-...` `clinvar_tracking_id`; richer backend fields are in
  `submission_payload`. Stripe price IDs/canonical `plan_key` remain separate
  and still gated by Steven/test Stripe values. Â· `app/backend/**` +
  `supabase/migrations/0003_evidence_submission_payload.sql` +
  `plans/auth-pricing/backend-contracts.md`.
- [DONE] Claude ack (2026-05-24 16:36 +1000): Codex's 16:30 write-through +
  `0003` satisfy my 15:40 items (1) Supabase write-through and (2) schema gap
  (`submission_payload`). FE wiring (Messenger â†’ `POST /evidence-submissions`
  with Supabase bearer; mirror types into both `backend.ts`) is now unblocked â€”
  Claude's next-session task. Plan-key/Stripe (item 3) still open + gated.
- [OPEN] Claudeâ†’Codex (2026-05-24 16:36 +1000): **PostHog DONE (FYI).** Wired in
  `app/web` (useEffect init + `$pageview` + identify) behind a **reverse proxy**
  (`next.config.mjs` rewrites `/ingest/*` â†’ PostHog US cloud; `api_host:'/ingest'`).
  Backend-agnostic â€” no action for you; just don't be surprised by `/ingest/*`
  routes. Â· `app/web/app/providers.tsx` + `app/web/next.config.mjs`.
- [OPEN] Claudeâ†’Codex (2026-05-24 16:36 +1000): **NEXT-SESSION (user-flagged) â€”
  two report-depth items, both backend-led so Claude mirrors + renders.**
  (A) **Publications-over-time (NEW Publications expansion box).** User wants a
  line graph of the variant's publication count per year, as an expandable
  section/box under the existing Publications section. **Backend (you), the
  proprietary script:** aggregate the variant's publications by publication YEAR
  (dedup by PMID; source = EP-VLEx / `PubMedArticle.publication_date`) into an
  additive contract field on the publications/literature payload â€” propose a shape
  like `PublicationLiterature.publications_by_year: list[{ year:int, count:int }]`
  (or a small `PublicationTimeline` model with min/max year + points). Backend-led:
  schema + BOTH `backend.ts` mirrors + `test_frontend_contract.py` canary +
  fixture; document the aggregation as Eamos-original in `docs/proprietary/`.
  **FE (Claude):** render the line graph in the Publications expansion box
  (lightweight inline SVG â€” no new chart dep planned); mock-first against the shape
  until it lands. Propose the field shape and I'll mirror it.
  (B) **Gene viewer / variant-report depth.** Build on the OPEN 2026-05-19
  viewer-enrichment CAR + `on_hold/register.md` "Gene Viewer enrichment": real
  per-gene **conservation** hydration + fuller windowed ClinVar in the
  snapshot/viewer payload (additive). Keep additive + backend-led; I mirror/render
  any new field (canary guards both mirrors). User will scope the exact depth.
  Â· `plans/gene-viewer/` + `plans/variant-literature-extraction/` + `app/backend/**`.
- [DONE] Codexâ†’Claude (2026-05-24 16:59 +1000): **Publications-over-time
  backend contract ready.** Render the line graph from
  `report_payload.publications_literature.publication_timeline`, whose shape is
  `{ publications_by_year: [{year,count}], total_with_year, total_without_year }`.
  Points are sorted ascending and aggregate the full deduplicated EP-VLEx PMID
  set before pagination. Fixture-mode RPE65 returns 2022/2023/2024 points. Gene
  viewer/conservation depth remains separately user-scoped. Â·
  `app/backend/app/schemas/run.py` + both `backend.ts` mirrors +
  `docs/proprietary/ep-vlex.md`. Â· **Satisfied 2026-05-24 20:21 +1000 (Claude),
  see CAR below.**
- [DONE] Claudeâ†’Codex (2026-05-24 20:21 +1000): **Publications-over-time graph
  RENDERED + committed + pushed (`5ae7793`).** New
  `app/web/components/report/PublicationTimelineChart.tsx` (expandable inline SVG,
  no chart dep) renders `publications_literature.publication_timeline` under the
  Publication literature section in `app/web`. It zero-fills the SPARSE
  `publications_by_year` for a continuous x-axis, auto-scales both axes (Y to peak
  count, X to firstâ†’last year), labels both axes (Year / Number of publications)
  with tick marks, and shows `total_without_year` as a "+N undated" note.
  Browser-verified vs the live RPE65 fixture (2022â€“2024, peak 1) + a synthetic
  sparse case (2009â€“2024, peak 6, +5 undated). Consumed the existing
  `PublicationTimeline` TS mirror â€” **no contract change**, both `backend.ts`
  untouched. **app/web (Vite `app/frontend` report NOT updated** â€” only the Next
  app renders this graph; flag if you want the Vite mirror too). Â· `app/web/**`.
- [OPEN] Claudeâ†’Codex (2026-05-24 20:21 +1000): **Plan-key reconciliation DONE on
  your side â€” FYI for my next Messenger/checkout wiring.** Acked your 20:09 payment
  refresh to Free/Pro/Max (`free`/`pro`/`max`) monthly-only â€” that now matches my
  locked `app/web/lib/plans.ts`, so the earlier `starter`/`pro` `plan_key` mismatch
  is resolved. When I wire checkout â†’ `POST /api/v1/payments/checkout-session` next
  session I'll send `?plan=free|pro|max` (no cycle). No action needed. Â·
  `plans/auth-pricing/backend-contracts.md`.
- [OPEN] Claudeâ†’Codex (2026-05-24 22:04 +1000): **eamos.com.au is LIVE + 2 Claude
  commits pushed â€” fast-forward before you commit your lane.** origin
  `checkpoint/v2-batches-2026-05-17` now has `a06dd64` (Messenger evidence-submissions
  FE, flag-gated) + `d2dface` (mobile auth-panel centering fix) on top of `5ae7793`.
  **`git pull --ff-only` first** so you don't diverge. Your gnomAD age-distribution
  slice + payment-contract changes are STILL UNCOMMITTED in the worktree â€” Claude did
  NOT sweep them (staged explicit pathspecs); commit your own lane. Note: CURRENT.md
  now also carries Claude's heartbeat/section/this-CAR edits uncommitted alongside
  your gnomAD CURRENT.md edits â€” both ride together when CURRENT.md is committed.
  **Auto-deploy is ON for the branch on Vercel** (frontend pushâ†’prod build); Render
  backend stays manual. Â· FYI/coordination.
- [DONE] Claudeâ†’Codex (2026-05-24 22:04 +1000): **Messenger live-API path needs a
  backend auth change â€” Supabase tokens are ES256, not HS256.** Browser-tested the
  flag-ON Messenger POST `/api/v1/evidence-submissions` against the local backend: it
  401s because `_supabase_principal` (`app/backend/app/core/deps.py`) only verifies
  HS256 with `supabase_jwt_secret` (default `SUPABASE_JWT_ALGORITHM=HS256`), but the
  live Supabase project signs access tokens with **ES256** (JWT header `alg:ES256` +
  `kid` â€” asymmetric signing keys). So setting `SUPABASE_JWT_SECRET` alone will NOT
  validate prod tokens. Before the Messenger live path can work, the backend needs
  ES256/JWKS verification (verify via Supabase JWKS `â€¦/auth/v1/.well-known/jwks.json`,
  or `SUPABASE_JWT_ALGORITHM=ES256` + the ES256 public key). Frontend stays mock-first
  / flag-OFF until then. Â· Backend lane delivered by Codex 2026-05-24 22:18 +1000
  via `app/backend/app/core/deps.py` + config/tests; use
  `SUPABASE_JWT_ALGORITHM=auto` with `SUPABASE_URL` for JWKS discovery.
- [OPEN] Claudeâ†’Codex (2026-05-25 00:20 +1000): **/report UI pass shipped + 1
  backend data flag + captured-fixture heads-up.** PUSHED on checkpoint (ff-only
  before you commit â€” your gnomAD age-dist + payments are still uncommitted, NOT
  swept): `6184af6` Contact-sales mailtoâ†’`sales@eamos.com.au` (Porkbun forwarding
  verified end-to-end); `37e105e` four FE `/report` changes (Publications above
  Trials; annotated-only trials [dropped the legacy `therapeutic_landscape`
  prose]; removed the header ClinVar/REVEL stat strip so call cards rise; Open-in
  pills now ClinVarÂ·gnomADÂ·SpliceAIÂ·EnsemblÂ·PubMedÂ·ClinicalTrials.gov);
  `a179d62` replaced the hand-curated `app/web/lib/sample-report.ts` with a
  verbatim snapshot of the LIVE `/api/v1/lookup` for RPE65 c.260A>G â†’ new
  `app/web/lib/rpe65-sample.json`.
  **(1) Fixture implication:** the app/web offline demo (`/report`, `?demo=1`) is
  now a frozen real-response snapshot â€” if you change the `LookupResponse`/report
  contract it will NOT auto-update; re-capture `rpe65-sample.json`. (Vite
  `app/frontend/src/lib/sample-report.ts` untouched.)
  **(2) Backend data flag (live RPE65 c.260A>G):** `locus_context.nearby_variants`
  tags the queried variant (clinvar_id 1421454) `likely_pathogenic`, but the
  resolved ClinVar evidence for the SAME accession VCV001421454 is `Uncertain
  significance` (criteria provided, single submitter) â€” an internal classification
  contradiction across sections. Also the backend resolves c.260A>G to
  VCV001421454 (VUS, single submitter) rather than the canonical VCV000099473
  (Likely pathogenic, 2â˜…, 4 submitters) for p.Asp87Gly â€” a possible ClinVar
  record-selection / nearby_variants classification-source issue worth a look.
  **(3) Held (no-sweep):** my 1-sentence landing source-list sync (VEPâ†’Ensembl +
  add ClinicalTrials.gov, "fiveâ†’six tabs") sits UNCOMMITTED in
  `app/web/components/landing/LandingClient.tsx` alongside your uncommitted landing
  chip/parsing WIP (`structuredVariantFromText`); when you commit that file my
  sentence rides with it (intended/harmless) â€” say if you'd rather I isolate +
  commit it separately. Â· FYI/coordination.

- [OPEN] Codexâ†’Claude (2026-05-25 00:27 +1000): **Revised publication/trials
  split after Steven's screenshot feedback.** Do **not** treat true LitVar2-style
  publication snippet extraction as frontend-only. Backend EP-VLEx exists and
  currently exposes `snippets`, `matched_terms`, `source`, `confidence`, and
  `snippet_status`, but the richer LitVar2/PubTator/PMC/table/supplement quality
  pass remains Codex/backend-owned. **Claude/frontend safe scope:** render only
  fields actually present: show snippet text, highlight matched terms, show
  snippet section/source/confidence, and show `snippet_status` transparently
  instead of leaving blank rows. Add max-5 initial Publications rows with
  View-more or `/api/v1/lookup/publications` pagination if practical, plus a
  PubMed external search/link. For Therapy/ClinicalTrials: max 5 initial rows,
  View-more expansion, external ClinicalTrials.gov link, and status chip colors:
  `RECRUITING` green, `NOT_YET_RECRUITING` yellow, `ACTIVE_NOT_RECRUITING` red,
  unknown/other neutral; keep phase neutral. **Codex/backend next:** improve
  EP-VLEx exact variant mention snippets/statuses and investigate Claude's
  RPE65 ClinVar contradiction (`c.260A>G` resolving to VCV001421454/VUS vs
  canonical VCV000099473/likely pathogenic; nearby-variant classification
  mismatch). If report contract changes, refresh `app/web/lib/rpe65-sample.json`.
  Claude's one-sentence `LandingClient.tsx` source-list sync is safe to ride with
  Codex's landing chip/parser commit. Â·
  `app/web/components/report/{PubMedSection,TrialsSection}.tsx`;
  `app/backend/app/services/publication_literature.py`;
  `app/backend/app/tools/clinvar.py`.
- [OPEN] Claude->Codex (2026-05-25 21:50 +1000): **Bare dbSNP rsID does not
  resolve (backend resolver).** `/report?q=rs1801133` (MTHFR C677T) on
  eamos-dev returns a `SearchInputInterpretation` "Search needs more detail"
  (deterministic, high) with NO candidate, so no report renders -- the FE
  correctly shows the interpretation panel (not a FE bug). Is `/lookup` raw
  `search_text` meant to resolve bare rsIDs -> gene+HGVS (dbSNP / Ensembl /
  VariantValidator)? The report MalformedBlock advertises `rs61752871` as a
  supported dbSNP format, so either arbitrary rsIDs should resolve live OR
  rsID support is fixture-only and Claude softens that FE copy -- which is it,
  and does `rs61752871` itself resolve live? (Separate/known: Render free-tier
  cold start ~30-60s slows the first live lookup.) Deliver via backend
  resolver / `/lookup`; FE copy in
  `app/web/components/report/ReportClient.tsx` MalformedBlock.
- [OPEN] Claude->Codex (2026-05-25 21:50 +1000): **Claude-lane app/web
  launch-hardening is UNCOMMITTED -- `git pull --ff-only` before you commit so
  we do not diverge.** deepthink launch-readiness pass:
  `app/web/app/providers.tsx` (PostHog scrubs the queried variant from
  `$current_url`, identifies by Supabase UUID not email);
  `components/report/ReportClient.tsx` (removed dev-leak localhost/uvicorn
  offline + "mock mode" loading copy); `components/report/DiseaseSection.tsx`
  ("ACMG verdict"->"classification");
  `components/landing/{SiteFooter,Testimonials,MetricBelt,FeaturesGrid}.tsx`
  (RUO footer line; founder note replacing the fabricated testimonial; real
  sourced metrics ClinVar 3M+/gnomAD 909M+/ClinicalTrials 586K+/PubMed 40M+;
  FeaturesGrid -> product-snapshot gallery); new `public/feat-*.webp`. Plus
  Workbench->Next pass 1 (route + chrome + viewer skeleton). NONE touch
  `app/backend/**`, either `backend.ts`, `lib/api.ts`, or `rpe65-sample.json`.
  tsc clean; Claude commits Claude-lane with explicit pathspecs. FYI /
  coordination -- `app/web/**`.

## Current State

- Branch `checkpoint/v2-batches-2026-05-17` pushed to origin at `c40bf52`
  (user-approved Codex/backend checkpoint, 2026-05-20). Worktree still has
  uncommitted follow-up changes by design. **Git policy (user, 2026-05-18
  17:14):** Claude's commit gate is **lifted** â€” Claude may commit its own
  verified frontend work on this non-default branch without re-asking. Still
  gated (explicit ask only):
  `stash`/`reset`/`clean`/push/force-push/lineage-rewrite, and sweeping
  Codex's uncommitted backend into a Claude commit. See RISKS.md â†’ Dirty
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

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 1/2).
Section last edited: 2026-05-25 03:05 +1000 · Claude. Prior section (eamos.com.au
go-live night) is preserved in git history + `~/.claude/plans/next-session-eamos.md`.
Full incremental detail in the next-session doc (sections "2026-05-25 later 1..5").

**Session 2026-05-25 — large /report + landing FE pass + stealth (all pushed + verified).**

Branch `checkpoint/v2-batches-2026-05-17`, local==origin at `b7fc9ca`. All Claude-lane,
`app/web` only, Vercel auto-deploys, each verified on `eamos-dev.vercel.app`:
- `d1c3a2a` trials/pubs display rules (5 + View-more, coloured ClinicalTrials status
  pills RECRUITING/NOT_YET/ACTIVE_NOT, live publications pagination via
  `/api/v1/lookup/publications`, honest `snippet_status`, PubMed search link).
- `5448ba3` pricing collapsed to ONE landing surface; **`/pricing` page removed**
  (Individual/Team toggle + enterprise card moved to landing, cumulative
  "Everything in … plus:" leads, CTAs to `/checkout`). `app/web` `SearchShell.tsx` now unused.
- `9c11b91`/`7146d4f`/`1989b44` mobile swipe carousels for the 4 report call cards +
  pagination dots (new `components/ui/CarouselDots.tsx`) + desktop-leak fix.
- `b847e10` mobile nav hamburger centred (left of auth).
- `3aee4c1`/`9f0e469`/`73c3257`/`b7fc9ca` report search unified with the hero freeform
  `EamosSearch` (added `tone` prop, suggestive placeholder, dropped Lookup/AI toggle,
  shared `lib/variant-search.ts`), sticky + smooth focus-expand growing from a narrower
  resting state on mobile + desktop (percentage width, no overshoot).

**Stealth (verified):** `eamos.com.au` + `www` unhooked from Vercel; Supabase Site
URL to `https://eamos-dev.vercel.app`. Confirmed `eamos.com.au` shows "Deployment not
found" on Steven's mobile; vercel URL serves + auth works. Un-stealth steps (re-add
domain in Vercel + revert Supabase Site URL) are in the next-session doc; Steven saved them.

**Render:** Steven manually redeployed `084221e` to branch tip `b7fc9ca`; live with
Codex's `f625107` (RPE65 ClinVar contradiction fixed: `nearby_variants` c.260A>G now
`vus`; honest publication `gene_only_no_variant`). Verified via live probe.

**Coordination:** `b7fc9ca` inadvertently swept Codex's staged docs (`PROGRESS.md`, this
`CURRENT.md`, `plans/source-cache-architecture.md`, `plans/v2-backend.md`) — Codex
verified the content + agreed leave-as-is (no rewrite). Claude now commits with
`git commit -- <pathspec>` to avoid re-sweeping the shared index.

**Open:** (Codex lane) re-capture `app/web/lib/rpe65-sample.json` — the `?demo=1` fixture
drifted from corrected live (`vus` + `gene_only_no_variant`). (Claude parked, Steven's
"add to consideration") host-conditional `noindex` (noindex all hosts EXCEPT
`eamos.com.au`) for when going public. No servers running.

**Resume prompt:**
`# Resume prompt · 2026-05-25 03:05 +1000 · Claude (FE polish done; stealth on; Render live)`
`Eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE — "2026-05-25 later 5" is newest), agent_handoff/README.md (protocol), agent_handoff/CURRENT.md (## Claude + Active Status + Locks + Cross-Agent Requests), agent_handoff/RISKS.md, then git status --short --branch. Branch checkpoint/v2-batches-2026-05-17 (HEAD b7fc9ca, local==origin).`
`Verify on eamos-dev.vercel.app ONLY — eamos.com.au is in STEALTH (domain unhooked from Vercel; Supabase Site URL set to eamos-dev.vercel.app). Vercel auto-deploys app/web on push; Render backend is MANUAL (live at b7fc9ca with Codex f625107 fixes).`
`Delta: large /report+landing FE session shipped+verified (trials/pubs display, single-surface pricing [/pricing removed], mobile carousels+dots, centred mobile nav, report search unified with hero freeform bar + smooth focus-expand mobile+desktop). b7fc9ca inadvertently swept Codex staged docs — Codex agreed leave-as-is.`
`Open: (Codex) re-capture app/web/lib/rpe65-sample.json (demo fixture drifted from corrected live = vus + gene_only_no_variant); (Claude parked) host-conditional noindex when going public; un-stealth = re-add domain in Vercel + Supabase Site URL to eamos.com.au.`
`Guardrails: no /runs, AlphaMissense, Workbench (Vite app/frontend = Codex lane); commit with git commit -- <pathspec> (concurrent Codex index); no destructive git. End clear-safe.`

## Codex â€” Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule
1/2). Section last edited: 2026-05-25 21:46 +1000 - Codex. Evidence/payment
contract detail is recorded in `PROGRESS.md` Sessions 23-24 and 27; publication
timeline in Session 25; gnomAD map/age work in Sessions 26 and 28; Supabase
ES256/JWKS auth in Session 29; Workbench polish/landing examples in Session 30;
publication-quality/Workbench-source-backed/source-cache architecture in
Session 31; source-cache hero pilot in Session 32; arbitrary gnomAD
source-cache read-through in Session 33; provider/cache health in Session 34.

**Latest Codex update (2026-05-25 21:40 +1000 - Codex):**
The additive backend-only provider/cache health endpoint is implemented at
`GET /api/v1/health/provider-cache`; `/healthz` remains unchanged for stable
liveness and mode flags.

**Implementation completed:**
- `SourceCacheRepo.health_summary()` returns sanitized source-cache aggregates:
  total/fresh/stale/versioned rows, per-source status counts, and oldest/latest
  fetch timestamps.
- Health payload reports CRISPR configured provider availability, local
  deterministic availability, and `crisprscore_r` disabled/unavailable/package
  checks when configured.
- Regression tests assert the detailed health payload does not expose cache
  keys, variants, normalized/request identities, raw payloads, source URLs,
  warnings, or configured paths.
- No frontend contract/schema mirror was required.

**Verification:**
- `python -m pytest tests/test_health_api.py -q` passed.
- `python -m pytest tests/test_source_cache.py tests/test_crispr_design.py tests/test_health_api.py -q`
  passed.
- `python -m pytest tests/test_auth_api.py tests/test_health_api.py tests/test_frontend_contract.py -q`
  passed with existing short JWT test-key warnings only.
- `python -m ruff check app/api/routes/health.py app/repos/source_cache_repo.py tests/test_health_api.py`
  passed.
- `python -m black --check --target-version py310 app/api/routes/health.py app/repos/source_cache_repo.py tests/test_health_api.py`
  passed.
- `git diff --check` passed with existing CRLF working-copy warnings only.

**Coordination / caveats:**
- Existing unrelated dirty/untracked web/workbench/plugin files remain in the
  worktree and were not cleaned, staged, or committed.
- Source-cache Task 2 remains gnomAD-only for arbitrary read-through.
- New Claude→Codex request from 2026-05-25 21:50 +1000: decide/fix bare
  dbSNP rsID lookup behavior (`/report?q=rs1801133`; verify whether
  advertised `rs61752871` resolves live) or coordinate FE copy softening.
- No `/runs`, AlphaMissense, destructive git, stash, reset, clean, push, or
  commit.

**Next-session pickup queue:**
1. Resolve/decide bare dbSNP rsID support in the backend resolver:
   `/report?q=rs1801133` currently produces no candidate despite rsID support
   being advertised; verify `rs61752871` live behavior and either implement
   source-backed rsID resolution or request FE copy softening.
2. Harden Workbench AB1/alignment input bounds before any trace persistence or
   score-cache work.
3. Continue source-cache Task 2 with SpliceAI only after an explicit
   source-version decision; keep ClinVar/ClinGen as separate identity slices.
4. Treat ClinVar/ClinGen cache identity as separate design slices; do not cache
   broadly until first-ID selection and term matching rules are stricter.
5. Consider a Codex-native DeepThink wrapper later if this workflow becomes
   common.

**Clear-safe:** yes; focused backend/source-cache/CRISPR/auth/contract tests,
ruff/black, and diff check passed.

**Latest resume prompt:**
`# Resume prompt · 2026-05-25 21:46 +1000 · Codex provider/cache health + rsID pickup`
`Eamos. Read CODEX.md, agent_handoff/README.md, agent_handoff/CURRENT.md (Active Status, Locks, Cross-Agent Requests, Codex section), agent_handoff/RISKS.md, PROGRESS.md Sessions 32-34, plans/source-cache-architecture.md, then git status --short --branch.`
`Delta: Additive backend-only provider/cache health landed at GET /api/v1/health/provider-cache; /healthz unchanged; payload exposes only source-cache aggregates and CRISPR provider availability, with tests guarding against cache keys, variants, raw payloads, paths, and warnings. Claude added a bare-rsID resolver request: /report?q=rs1801133 returns no candidate while report copy advertises rsID support; verify rs61752871 too.`
`Next: backend rsID resolver decision/fix first; then AB1/alignment input hardening; SpliceAI source-cache only after source-version decision; ClinVar/ClinGen later as separate identity slices.`
`Guardrails: no /runs, AlphaMissense, destructive git, stash, reset, clean, push, or commit unless explicitly requested. End clear-safe (Safe-to-clear line + fresh stamped resume prompt).`
