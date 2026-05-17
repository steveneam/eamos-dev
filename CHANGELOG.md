# Eamos — Change Log

## Session 18 — 16 May 2026 — FE-5.5: Sequence Viewer v2 (Benchling-grade) + chrome relayout

At the post-Session-2 backend-first checkpoint the user redirected to the
Workbench sequence viewer: review the refreshed `Eamos Workbench v2.html` +
`Workbench v2/*` mock and the Benchling/SnapGene competition shots, form a
UI/UX opinion, and integrate 4 requested changes into the plan. Confirmed
(augment zoom; full v2 port), then executed as new milestone **FE-5.5**.

- **Plan** — `plans/v2-frontend.md`: FE-5.5 milestone added ahead of FE-6;
  FE-5 marked superseded; stale "Source mocks" pointer fixed (v1 → v2).
- **Data model** — `lib/workbench/gene-window.ts` (pure `buildFlatWindow` /
  `buildCodons` / `consequenceAt`, intron/splice-aware), `sample-rpe65-v2.ts`
  (full 14-exon/intron structure, density counts, protein features; carries
  forward the FE-5 codon-87 coherence fix), `edit-state.ts` (undo/redo
  reducer), `gene-window.test.ts` (8 tests).
- **Viewer** — React port: `SequenceViewerV2` + `ViewerToolbar`, `GeneMinimap`,
  `ExonStrip`, `CodonDetail` (wrapped 60-bp blocks), `SelectionBar`,
  `HistoryTimeline`, `EditPopoverV2`, `ZoomSlider`; new horizontal `ToolBar`;
  `CanvasHeader`/`SidePanel`/`WorkbenchShell` rewritten.
- **4 modifications** — (1) ClinVar density toggle (Tracks dropdown, grouped
  with pins); (2) collapsible side-panel exon disclosure; (3) tool selector →
  horizontal segmented control top-right, left rail removed (`.wb` 2-col);
  (4) Benchling −/+ density slider + retained Gene/Exon/Codon chips +
  minimap/exon-strip collapse + restriction-as-top-ticks / beige-band pass.
- **Cleanup** — 14 superseded FE-5 files deleted.
- **Verified** — `npx vitest run` 24/24, `npm run build` clean (tsc -b +
  vite), `test_frontend_contract.py` 40/40 (untouched — pure FE, no contract
  drift). Browser pixel-check pending a dev-server session.
- **Codex adversarial hardening pass** (`task-mp8d61ip-1zyj8k`,
  `codex:rescue --background --fresh --write`): 0 CRITICAL · 2 HIGH (drag
  listeners surviving unmount; edit popover not portalled/clamped) · 2 MED
  (history-jump cursor bounds; hard-coded intronic ClinVar pin mapping →
  data-driven) · 3 LOW (icon-button a11y; stable list keys; stale CSS rail
  comment) — **all FIXED**. Claude re-ran the authoritative verify post-Codex
  (Codex's sandbox can't run vitest/vite): vitest 24/24, build clean, contract
  40/40. **Nothing committed.**

## Session 17 — 16 May 2026 — Whole-project review → deepthink → hardening Session 1

### Inputs

- **Codex whole-project adversarial-review** (`task-mp834g2g-uochuz`): 2 CRITICAL
  (unauthenticated `/runs,/reports,/reviews,/search` — patient data + PDFs
  readable/editable/downloadable; `/reports/upload` open), 3 HIGH (`/report?q=`
  demo leak; SpliceAI strict-genomic violation; VariantValidator fabricates
  consequence), 4 MEDIUM (cache race, pubmed `raw=None`, unsafe `load_fixture`,
  dead AI button), 4 LOW, + a 7-item ranked recommendation list.
- **deepthink skill** (quick mode, confidence CERTAIN): produced the risk-ordered,
  lane-split, sessionized plan (security → correctness → invariants → features →
  docs); verified the auth-change blast radius against the actual codebase (7
  test files + no authed conftest fixture) before planning.

### Session 1 — landed this session

- **Frontend (Claude) — done, verified:**
  - **H1** `ReportPage.tsx` — `/report?q=…` (Workbench/AI fallback) no longer
    silently renders the RPE65 sample; unstructured search → `malformed` state.
    Demo now only on explicit `?demo` or a truly empty entry.
  - **M4** `PublicationsCallout.tsx` — the AI-summary button renders only when an
    `onAskSummary` handler is supplied (was an always-on dead control).
  - **L1** `ReportPage.tsx` — "Gene context" card meta derived from
    `variant_summary_rows[0]` (`geneContextMeta`) instead of hardcoded
    `RPE65 · NM_000329.3`.
  - **L2** `ToolRail.tsx` — removed the inert (no-onClick, unlabeled) settings button.
  - **L4** `plans/v2-frontend.md` — obsolete FE-3.6 "remaining" block marked historical.
  - `ROADMAP.md` fully rewritten (true state + sessionized hardening plan);
    handoff at `~/.claude/plans/next-session-eamos-hardening.md`.
  - Verified: `npx vitest run` **21/21**, `npm run build` clean.
- **Backend (Codex, golden rule) — ✅ done & Claude-verified** (`task-mp83i0eg-v76i3k`):
  C1/C2 authentication on `routes/{runs,reports,reviews,search}.py` via a new
  `require_authenticated_user` dep in `core/deps.py` (HTTPBearer →
  `auth_service.get_current_user`, 401 on missing/invalid, `# TODO` object-authz);
  public lookup/health/auth/primer/crispr/align/chat stay open; authed `auth_client`
  fixture added to `tests/conftest.py` + 7 test files migrated + new
  `tests/test_auth_guard.py` 401 test. **Verified independently:** offline pytest
  **81 passed / 4 skipped**, `test_frontend_contract.py` **40/40**; live smoke —
  public `/api/v1/lookup`+`/api/v1/primer` → 200 (no auth), protected
  `/api/v1/runs`+`/api/v1/reports/upload` → 401. C1/C2 patient-data exposure closed.

### Codex runtime fix (carried from Session 16)

Diagnosed + fixed the "phantom running / 3rd dispatch silently fails" class:
stale `state.json` zombie job records (dead pids from non-graceful exits) block
the single shared Codex runtime; the companion `cancel` is broken under
Git-bash (`/PID` MSYS-mangle) so they never reap. Reconciled the records;
verified dispatch round-trips. Durable fix (run `cancel` from PowerShell) +
reap procedure saved to memory.

### Session 2 — backend hardening (✅ done & Claude-verified, Codex `task-mp848are-gq0blv`)

Re-sequenced backend-first per user decision (frontend consumes the API; stub
contracts already frozen so FE is never blocked; building FE once against final
backend avoids rework). H2 (spliceai → `live_stub` when no coords, mirrors
gnomad), H3 (`variant_validator._mutate_variant` no longer fabricates
`single nucleotide variant`/`missense variant` without a `variant_id`), M1
(`variant_cache_repo.upsert` → atomic `INSERT … ON CONFLICT DO UPDATE`), M2
(`pubmed.py` miss path `raw={}`), M3 (`base.py load_fixture` guarded →
`{}` on missing/corrupt fixture), L3 (`plans/v2-backend.md` coherent). New
`tests/test_tool_invariants.py`. Verified: offline pytest **86 passed / 4
skipped**, contract 40/40; live smoke — all evidence `live`,
`genomic_hg38=1-68444869-T-C`, spliceai stays `live` on resolved path, 10
publications.

### Remaining (see ROADMAP.md / handoff)

Backend hardening complete. **Checkpoint:** M-002 real engines (Primer3 /
CRISPOR / NW+AB1 / live chat) — feasibility-gated, large; FE-6/7/8 contracts
already frozen so frontend isn't blocked. Awaiting user decision before FE
work. **Nothing committed.**

---

## Session 16 — 16 May 2026 — Variant-search-engine: cross-check + live fixes

### Phase A — Bidirectional full-project cross-check

**Why:** BE-8…BE-13 + FE-14 were offline-green but the prior session's
Claude-run live smoke found the backend was not live-functional. Before fixing,
a whole-project audit (not just the diff): Claude reviewed all `app/backend/**`
+ ran the live smoke; Codex (`task-mp81134n-3fm2ge`, read-only adversarial)
reviewed all `app/frontend/**`. Findings consolidated, severity-ranked, and
**approved by the user before any code edit**.

**Key audit outcomes:**

- **Plan diagnostics were partly stale (verified empirically):** BE-9 was
  *already fixed* in the working tree (`normalize_variant_query` +
  `CANONICAL_TRANSCRIPTS` → VariantValidator queries `NM_000329.3:c.260A>G`);
  BE-12 worked live; VEP/SpliceAI live succeeded (plan's "out of scope, broken"
  was outdated). BE-11 + BE-13 were the real remaining bugs.
- **Cross-check caught a Codex false positive:** Codex flagged
  `cleanQuery()` not stripping `_`; the regex at `variant-format.ts:30`
  (`[A-Za-z0-9_.]`) *does* include `_` and its test passes — rejected.

### Phase B — Approved fixes (HIGH + all MEDIUM)

**Backend (Codex, golden rule — 2 dispatched rounds + 1 Claude-applied):**

- **BE-11 / HIGH-1 — PubMed query too narrow.** `pubmed.py` term was
  `{gene}[Gene Name] AND "{cdna}"[Title/Abstract]` → live count **0** for
  RPE65 c.260A>G. Now gene + OR-group(cdna, protein, rsID) with gene-only
  fallback → **10 live articles**. (Verified real esearch: strict=0,
  broadened=121.)
- **BE-11 / MEDIUM-1 — LitVar2 query form + parser.** Free-text
  `"GENE c.xxx"` never matched LitVar2 autocomplete; now queries the
  **ClinVar-derived dbSNP rsID** (`_extract_dbsnp_rsid` from clinvar raw
  `variation_set[].variation_xrefs`), parses real `pmids`/`pmids_count`
  shape. Graceful zero return kept (rs1645931040 genuinely not in LitVar2).
- **BE-13 / MEDIUM-2 — cache poisoning.** `lookup_service` upsert guard now
  requires truthy `variant.genomic_hg38` (failed resolutions no longer
  cached/served). Regression test added.
- **BE-11 follow-up (Claude-applied — Codex 3rd dispatch failed to enqueue;
  user-approved golden-rule exception).** `publications_callout.total_count`
  collapsed to 0 when LitVar2 legitimately returned 0 even with 10 PubMed
  articles; now falls back to merged-article count when LitVar2=0. Offline
  fixture (litvar=816) unchanged.

**Frontend (Claude):**

- **HIGH-2 — client guard blocked backend-valid genomic input.**
  `variant-format.ts` `coord` regex widened to accept VCF-quad forms
  (`1-68444869-T-C`, `chr1:68444869:T:C`) the backend `normalize_variant_query`
  already accepts; 8 regression assertions added.
- **MEDIUM-3 — Workbench context/data mismatch.** `WorkbenchPage` context
  strip now reflects the rendered RPE65 fixture instead of echoing arbitrary
  URL params.
- **MEDIUM-4 — scratchpad drift.** `WorkbenchShell` per-base reset /
  revert-to-ref now drop the scratch row; re-edit replaces instead of
  duplicating.
- **MEDIUM-5 — base editor a11y.** `BaseRow` bases are now keyboard-operable
  (`role="button"`, `tabIndex`, `aria-label`, Enter/Space).

(Deferred per approved scope: LOW-1 ToolRail aria-label, LOW-2 generalised
transcript resolution, LOW-3 short dev JWT secret.)

### Phase C — Verification

**Verified:**

- Offline: `python -m pytest tests/ -q` → **80 passed, 4 skipped**;
  `test_frontend_contract.py` **40/40**; integration 816-assertion intact.
- Frontend: `npm run build` clean (tsc + vite); `npx vitest run` **21/21**.
- Claude-run live smoke (`USE_REAL_APIS=true`, `?refresh=true` bypass) — all
  Phase-C assertions PASS: `genomic_hg38==1-68444869-T-C`, gnomAD/VariantValidator
  `live`, `publications_callout.total_count==10` (was 0), 10 conforming
  `pubmed.ncbi.nlm.nih.gov/{pmid}/` URLs, 2nd call → evidence `cache`
  (not poisoned), `?refresh=true` → all `live`.

**Known / out of scope:** `tests/test_real_agent_smoke.py` (env-gated, normally
skipped) is flaky — it hard-asserts `spliceai status == "live"`, which fails on
transient SpliceAI endpoint timeouts (pre-existing brittleness; SpliceAI live
instability is explicitly out-of-scope per the plan). The pipeline itself
degrades correctly (never raises; `fallback` + `live_fetch_failed:` warning).

**Tooling note:** Codex's 3rd `codex:rescue` dispatch echoed a job ID but never
enqueued a real `task-*` job (no state file/log; broker healthy). The two
earlier apparent "hangs" were a Claude-side poll-loop JSON-shape bug, not Codex.

**Nothing committed** (per instruction). Plan rows flipped to ✅ in
`plans/v2-backend.md` (BE-8…BE-13) + `plans/v2-frontend.md` (FE-14).

---

## Session 15 — 15 May 2026 (continued)

### FE-5 — Workbench Sequence Viewer + click-to-edit

**Why:** First Workbench tool surface. Ports the sequence-viewer slice of the Claude Design mock (`Workbench/{data.js,sequence-viewer.js,side.js}`) to declarative React/TS. No backend-contract dependency — all-new frontend files.

**What changed:**

- **Testable core:** `src/lib/workbench/codon-table.ts` (codon table, `translate`, parameterised pure `consequenceOf`) + `src/lib/workbench/sample-rpe65.ts` (typed RPE65 window).
- **Viewer:** 11 components under `src/components/workbench/viewer/` — orchestrating `SequenceViewer` + ruler/track rows + portalled `EditPopover` with live hover-preview of the edit consequence and an apply→scratchpad flow.
- **Wiring:** `WorkbenchShell` lifted `edits`/`scratch`/`tracksOn` state; `CanvasHeader` made controlled (track toggles now drive the viewer); `SidePanel` gained the viewer branch (active-variant facts + scratchpad + reading guide).
- **Tests:** `vitest@^3` devDep + `npm run test` script; `codon-table.test.ts` (5/5) asserting missense `p.Asp87Gly`, frameshift on del, synonymous wobble + a data-coherence guard.

**Verified:** `npm run build` green; `npm run test` 5/5; `test_frontend_contract.py` 40/40 (unchanged — no contract touch).

**Deviations logged (PROGRESS.md Session 15):** (1) 1-char sample-sequence coherence fix so codon 87 = GAC/Asp → spec `p.Asp87Gly` (source mock's literal sequence contradicted its own annotations + the rest of Eamos); (2) hover-preview added to EditPopover per plan/acceptance (source JS previewed on click only).

---

## Session 14 — 15 May 2026 (continued)

### Parallel cycle 2 — FE-3.5 closed; BE-6/BE-7 + FE-4 + FE-3.6 landed

**Why:** Session 13 left FE-3.5 (contract sync) open and the report v2 modules rendering from hard-coded SAMPLE blocks richer than the backend fixture. This cycle closes the loop: backend payload made mock-faithful (BE-6), Workbench surface scaffolded (FE-4), and the frontend reconciled to the enriched contract with the divergent SAMPLE datasets removed (FE-3.6). Second use of the parallel Codex (`--background`) workflow.

**What changed:**

- **Frontend:** FE-3.5 closed (6 components wired to `payload.*`). FE-4 — new `/workbench` route + shell chrome (`src/components/workbench/*`, `src/pages/WorkbenchPage.tsx`, scoped `src/styles/workbench.css` ported from the mock with global resets dropped, width vars remapped to FE-0 tokens, `.badge`→`.ctx-badge`). FE-3.6 — `backend.ts` + `sample-report.ts` synced to the BE-6 contract; all 6 report components rewritten to consume the enriched payload and the divergent SAMPLE datasets deleted (empty-state fallback when data absent).
- **Backend (Codex):** BE-6 — additive schema fields + full rewrite of `lookup_v2_modules.json` to mirror the frontend SAMPLE constants; `test_frontend_contract.py` extended. BE-7 — `primer/crispr/align` workbench fixtures tightened to mock-JS fidelity.
- **Plans:** `plans/v2-frontend.md` (FE-4, FE-3.6 → done) and `plans/v2-backend.md` (BE-6, BE-7 → done) status tables updated.

**Sync point closed:** `test_frontend_contract.py` now **40/40 PASS** — the Session 13 known failure is resolved. `npm run build` green.

**Decision/deviation logged:** no-param `/workbench` defaults to the RPE65 sample rather than redirecting to `/` (v2 only serves RPE65; consistent with ReportPage demo). Three Codex fixture ambiguities recorded in `PROGRESS.md` Session 14 for review (CRISPR guide count, HDR efficiency range→midpoint, alignment mismatch index).

**Codex session:** background rescue agent `a862070de2d41f104` (this Claude session `2b842353-8473-468d-88e5-05e66d4acbf4`).

---

## Session 13 — 15 May 2026

### v2 rebuild — frontend FE-0..FE-3 + backend BE-1..BE-5 landed in parallel

**Why:** First parallel-execution cycle using the `openai/codex-plugin-cc` plugin. Claude Code drove the React/Vite work; Codex executed `plans/v2-backend.md` against `app/backend/` end-to-end in 22m. Same git working tree, same auth, same filesystem — no format mismatch (the plugin delegates to the local Codex CLI).

**What changed:**

- **Frontend (FE-0..FE-3):** Foundation tokens + hairline utility + ModePill (FE-0); Franklin removed from active surfaces and replaced with AlphaMissense (FE-1); six new report v2 modules — LocusContext, InSilicoGrid, AcmgCriteriaFold, CuratedVariantsGrid, AssociatedConditions, PublicationsCallout — with ~180 lines of v2 module CSS appended to `index.css` (FE-2); VariantHeader rewritten with cross-DB chip strip, tools row, and 4-stat row (FE-3). Also fixed a pre-existing TypeScript path-alias gap in `tsconfig.app.json` (`@/*` mapping was missing — the build had been broken before this session).
- **Backend (BE-1..BE-5):** Franklin tool archived to `archive/franklin/` (BE-1); six new optional fields on `ReportPayload` with RPE65 fixture at `app/backend/app/fixtures/lookup_v2_modules.json` (BE-2); `POST /api/v1/chat` + `/chat/stream` (BE-3); `POST /api/v1/primer | /crispr | /align` returning fixture responses (BE-4); `test_franklin_removed.py` + extended `test_frontend_contract.py` (BE-5).
- **Plans:** `plans/v2-frontend.md` and `plans/v2-backend.md` updated with status tables. New "FE-3.5 — Contract sync" section in `plans/v2-frontend.md` defines the next milestone: add the matching TypeScript interfaces to `app/frontend/src/lib/backend.ts` so `test_frontend_contract.py` passes and the FE-2 components can swap from hard-coded SAMPLE blocks to payload-driven props.

**Known sync point:** `test_frontend_contract.py` is the only failing backend test — it's waiting on the FE-3.5 TypeScript interfaces. By design.

**Codex session id (resumable):** `019e26bf-c0db-7b03-aff3-a5303bac4eed`.

---

## Session 12 — 14 May 2026

### v2 rebuild plan written, Franklin archived from product

**Why:** Three Claude Design mocks (`Eamos Landing Page.html`, `Eamos Report Page v2.html`, `Eamos Workbench v1.html`) iterate Eamos into two surfaces — variant report v2 with new modules folded in, and a new Workbench (sequence viewer + Primer/CRISPR/Align/Compare tools + tool-aware AI pill). Franklin (Genoox) is the main competitor and is being removed from the product surface.

**What changed this session:**

- `plans/README.md` — parallel-work coordination doc (Claude Code frontend ↔ Codex backend, shared contract on `backend.ts` ↔ Pydantic).
- `plans/v2-frontend.md` — frontend port plan, 9 milestones (FE-0 foundation through FE-8 AskEamos pill). Built on existing Phase 0–2 scaffolding; React/Vite preserved (no Next.js migration).
- `plans/v2-backend.md` — Codex-consumable backend brief, 5 milestones (BE-1 Franklin archive through BE-5 test sweep). Self-contained — every path, schema, and verification step in the doc.
- `DESIGN.md` — full rewrite around v2 tokens (Syne/Plus Jakarta Sans/JBM, ink scale, sequence palette, AA biochem palette, 920/1180/1440 widths). Legacy `/runs` surface kept as a frozen appendix.
- `README.md` — Franklin dropped from Database Stack. Report Structure refreshed to v2 sections (locus context, in-silico grid, ACMG fold, curated variants distribution, structured conditions, publications callout). Workbench surface added.
- `ROADMAP.md` — Layer 1 v1 marked done. Two new active phases: Layer 1 v2 + Workbench. Layer 2 marked frozen at `/runs`.
- `PROGRESS.md` — Session 12 entry summarising the rebuild.

**Decisions locked in (the five conflicts surfaced):**

1. Stack: keep React + Vite. Next.js migration deferred — re-evaluate if file-based API routing becomes load-bearing.
2. Layer 2 patient report at `/runs` frozen — no design changes, no new features.
3. Workbench delivered all-at-once with sample data; real engines (Primer3, CRISPOR, Needleman–Wunsch, AB1 parser) deferred to M-002.
4. Franklin: archive to `archive/franklin/` (preserve history, remove from active code).
5. v2 mock includes a `franklin.genoox.com` "Compare elsewhere ↗" chip — dropped in implementation. We don't link to competitors.

**Not yet implemented:** plans are written; Claude Code starts FE-0, Codex picks up `plans/v2-backend.md`.

---

## Session 10 — 10 May 2026

### Changes made this session

#### 15. AlphaMissense tool implementation plan

**Why:** The Solatis workflow (explore → deepthink → plan → execute) needed a first
real test case. The original candidate (ClinicalTrials.gov integration) turned out to
be already fully implemented — `clinical_trials.py`, `GENE_THERAPY_MAP`, and the
`therapeutic_landscape` field wiring in both service layers were complete but undocumented.
AlphaMissense was chosen instead: it is listed as `_(planned)_` in README.md, has no
implementation file, and exercises all five layers the workflow is designed for
(tool file, fixture JSON, registry, service payload, frontend card).

**What changed:**
- `plans/alphamissense-tool.md` — full implementation plan: 3 milestones (M-001 tool
  foundation, M-002 pipeline wiring, M-003 frontend + docs), 7 architectural decisions
  (DL-001–DL-007), 5 rejected alternatives, 3 risks. Ready to execute.
- `plans/` directory created (commit 32a185c).

**Key decisions recorded in the plan:**
- Data shape = Point lookup only: `summary = {uniprot_id, residue, score, pathogenicity_category}`
  (user confirmed; may revisit later)
- Wire into existing `acmg_classification` string field — no new schema field
- Thresholds from Cheng et al., Science 2023 (doi:10.1126/science.adg7842, Table S5):
  `<0.34` likely_benign, `0.34–0.564` ambiguous, `>0.564` likely_pathogenic
- `alphamissense` inserted between `spliceai` and `clinvar` in the evidence tuple
  in both `lookup_service.py` and `workflow.py`

**Not yet implemented** — plan is written and QR-validated; execution is the next session task.

#### 16. Therapeutic Landscape + ClinicalTrials.gov — discovered as already complete

**Why documented:** ROADMAP listed this as a future task, but exploration revealed the
full implementation was already in place from a prior session with no changelog entry.

**What exists (undocumented until now):**
- `app/tools/clinical_trials.py` — `ClinicalTrialsTool` fetching recruiting/active trials
  from ClinicalTrials.gov REST API v2; fixture map for 4 genes (RPE65, RPGR, ABCA4, CNGA3)
- `GENE_THERAPY_MAP` in `app/services/lookup_service.py` — gene → approved therapy text
- `therapeutic_landscape` field wired in both `lookup_service.py` and `workflow.py` —
  combines `GENE_THERAPY_MAP` entry + `ClinicalTrialsTool.get_trials_summary(gene)`

#### 17. Karpathy coding guidelines added to CLAUDE.md

**Why:** Solatis optimization pass (commit 903d295) identified missing behavioral constraints.
Karpathy-style guidelines added to reduce common LLM coding mistakes: simplicity-first,
surgical changes, goal-driven execution, think-before-coding. Commit 32a185c.

---

## Session 5 — 09 May 2026

### Changes made this session

#### 8. JWT secret hardening
**Why:** The previous `config.py` had `jwt_secret: str = 'dev-insecure-change-me-please-replace'`
as a default, meaning the backend would start silently with an insecure key if `.env` was
missing. A missing JWT secret should be a hard startup failure, not a silent misconfiguration.

**What changed:**
- `app/core/config.py:31` — `jwt_secret` default removed. Field is now bare `str`, so
  `pydantic_settings` raises `ValidationError` at startup if `JWT_SECRET` is absent from `.env`.
- `.env.example` already contained `JWT_SECRET` — no example change needed.
- `.env` must be created from `.env.example` before first startup (documented in README).

#### 9. franklin.py dead-code typo removed
**Why:** `canonical_tanscript` (missing 's') was a dead variable assigned but never read.
No functional impact, but dead code is noise in a file that will be reviewed when live
Franklin API integration is wired.

**What changed:**
- `app/tools/franklin.py:92` — `canonical_tanscript` line deleted.

#### 10. Backend README rewritten
**Why:** The old README described endpoints that don't exist (`GET /healthz` → actual route
is `GET /healthz` but under wrong API prefix), omitted the actual tool/schema/service
architecture, and was generic hackathon boilerplate. Any new contributor reading it would
get a wrong mental model of the system.

**What changed:**
- `app/backend/README.md` — complete rewrite. Architecture diagram, all API routes
  (actual routes with correct prefixes), tools table, config table, setup instructions.

#### 11. CLAUDE.md created at E:\HSIL-2026
**Why:** The E: drive copy of the project was missing CLAUDE.md — the single source of
truth for what Eamos is, what has been built, and what the rules are. Without it, future
Claude sessions would have no project context.

**What changed:**
- `CLAUDE.md` — written fresh. Reflects all session 4 completions, updated next-task list,
  current tech stack, database stack, report structure, HGVS table, critical rules.

#### 12. PubMed publications tool
**Why:** "Publications" was listed as a required report section in the spec but had no
backend implementation. The fixture-backed pattern established for ClinVar/VEP/SpliceAI/
Franklin transfers directly: one class, one fixture file, live NCBI E-utilities path.

**What changed:**
- New `app/tools/pubmed.py` — `PubmedTool` using `FixtureBackedTool` base class.
  Live path: esearch (gene + cdna term against PubMed) → esummary → article list with
  PMID, title, authors (first author + et al.), journal, year, PubMed URL.
  Falls back to fixture if `USE_REAL_APIS=false` or on any network exception.
- New `app/fixtures/tools/pubmed_fixtures.json` — 3 representative RPE65 articles.
- `app/tools/registry.py` — `PubmedTool` registered under key `"pubmed"`.
- `app/schemas/run.py` — `PubMedArticle` Pydantic schema added; `pubmed_articles:
  list[PubMedArticle] | None` field added to `ReportPayload`.
- `app/services/workflow.py` — `"pubmed"` added to the tool loop; pubmed evidence
  extracted and coerced to `list[PubMedArticle]`; set on `base_payload.pubmed_articles`.

#### 13. Frontend publications section
**Why:** PubMed articles are now returned by the backend but nothing rendered them.
The spec requires: 3 articles shown by default, "Show N more" toggle, dotted-underline
links, "View all on PubMed" gene-search link.

**What changed:**
- `app/frontend/src/lib/backend.ts` — `PubMedArticle` TypeScript interface added;
  `pubmed_articles?: PubMedArticle[]` added to `ReportPayload` interface.
- `app/frontend/src/App.tsx` — `buildPublicationsSection()` function added.
  Renders after the Limitations section. 3 articles default, "Show N more" toggle.
  Each article: title as dotted-underline link to PubMed, authors + journal + year.
  "View all on PubMed" gene-search link top right. Renders nothing when field is empty.

#### 14. Species selector
**Why:** The spec requires a species toggle (Human hg38 / Mouse mm39) visible before the
search/submit bar. Mouse is not yet built but needs to be visible to signal roadmap intent.
Placing it in the submit bar keeps it always visible without adding a separate header row.

**What changed:**
- `app/frontend/src/App.tsx` — pill toggle added in the submit bar above "Submit reports".
  Human (hg38): active/teal. Mouse (mm39): disabled, 45% opacity, "soon" badge.
  `selectedSpecies` state (default: `"human"`). No backend changes — mouse database stack
  not built yet; toggle is UI scaffolding only.

---

## Session 4 — 08 May 2026

### Changes made this session

#### 5. DNA notation as primary in variant table and sidebar
**Why:** Sequencing labs report in DNA/coding notation (c.260A>G) — that is the
actual molecular finding. Protein consequence is derived and secondary. The previous
display joined both into one string with protein first, which is clinically backwards.

**What changed:**
- `buildVariantRows` in App.tsx now produces two separate fields:
  `variantDna` (transcript_hgvs → consequence fallback) and
  `variantProtein` (protein_change, nullable)
- Desktop variant table: DNA notation full-size, protein change 13px muted below
- Mobile variant table: DNA notation `font-medium`, protein change `text-sm muted`
- Sidebar "Variant Summary" card: DNA notation as primary line,
  protein change `text-xs` at reduced opacity
- Protein line only renders when non-null — no blank line for splice/frameshift variants

#### 6. Backend tool parameterisation — all four tools now gene-agnostic
**Why:** Every tool (ClinVar, VEP, SpliceAI, Franklin) was hardcoded to RPE65 p.Asp87Gly
with constants baked into the class body. Any variant other than that one would silently
return RPE65 data regardless of what was uploaded. This was the primary blocker between
fixture mode and real clinical use.

**What changed:**
- clinvar.py: removed `CLINVAR_ID = "1421454"`. Added two-step live fetch:
  esearch resolves GENE:c.cdna to a ClinVar variation ID, then esummary fetches
  classification, review status, and conditions for that ID.
- ensembl_vep.py: removed `HGVS = "NM_000329.3:c.260A>G"` and hardcoded `RPE65`
  gene filter. Uses `variant.transcript_hgvs` directly; canonical transcript
  selected by `variant.gene` with safe fallback to first result.
- spliceai.py: removed `VARIANT = "chr1-68444869-T-C"`. Constructs `GENE:c.cdna`
  string from variant fields. (Live REST endpoint format to confirm when tested.)
- franklin.py: removed `SEARCH_TEXT = "RPE65:c.260A>G"`. Same `GENE:c.cdna`
  construction for both parse_search and snp search calls.
- workflow.py: variant collection moved before tool calls. Primary variant extracted
  from report and passed into all tools via `tool.get_evidence(variant=primary_variant)`.
  All fallback behaviour preserved — variant=None falls through to fixture data.

**Also:**
- pyproject.toml: `requires-python` relaxed from `>=3.11` to `>=3.10`.
  No 3.11-specific syntax exists anywhere in the codebase; the constraint was conservative.
  Python 3.10.11 is installed and all dependencies install cleanly.

#### 7. Plain language variant decoder
**Why:** Clinicians outside core genetics (ophthalmologists, neurologists, general
geneticists) don't parse HGVS notation daily. Decoding it automatically reduces
friction and makes reports readable to a broader clinical audience.

**What changed:**
- New file `app/services/variant_decoder.py`: `decode_variant(gene, transcript_hgvs,
  protein_change)` returns a one-paragraph plain English explanation.
  Pure regex/template — no extra LLM call, works offline, deterministic.
  Handles 7 cdna types (substitution, single/multi-base deletion, insertion,
  duplication, splice site ±offset) and 3 protein types (frameshift, missense, splice).
  cdna notation tried first; protein change used as fallback.
- `app/schemas/run.py`: `variant_decoder: str | None = None` added to ReportPayload.
- `app/services/workflow.py`: decoder called for the primary variant row;
  result set on base_payload.variant_decoder before draft rendering.
- `app/frontend/src/lib/backend.ts`: `variant_decoder?: string | null` added
  to the ReportPayload TypeScript interface.
- `app/frontend/src/App.tsx`: "What this variant means" callout block inserted
  between the executive summary and the variant table. Teal label, muted body text,
  soft card style. Only renders when field is non-null.

Smoke tested against all five demo variants — all decode correctly.

#### Infrastructure: project moved to E:\HSIL-2026
- D: drive was FAT32 with ~20 MB free — could not hold node_modules
- E: drive reformatted from FAT32 to NTFS, project copied to E:\HSIL-2026
- Node.js v22.15.0 portable installed at C:\temp\node\node-v22.15.0-win-x64
- Python 3.10.11 installed via company portal; all backend deps installed
- Private dev repo created: https://github.com/steveneam/eamos-dev (account: steveneam)
  Pushes via GitHub REST API — git not installed, github.com downloads blocked by IT
- Dev server: `npm run dev` from E:\HSIL-2026\04_demo\app\frontend → localhost:5173
  (pending IT network clearance for Node.js to bind locally)

## Session 2 — 07 May 2026

### Changes made this session

#### 1. AI prompt refinement
**Why:** The original hackathon prompts were generic. They produced hedging,
passive language ("This report suggests...") instead of the active, clinician-
to-clinician tone that genomic geneticists actually use in handoff notes.
Clinicians testing the tool will lose trust immediately if the prose sounds
like a disclaimer rather than a colleague's assessment.

**What changed:**
- Added explicit instruction: "Write as a senior clinical geneticist handing
  off to a colleague — direct, active, no hedging openers"
- Instructed the model to lead with the gene and variant name, not a
  sentence about the report itself
- Tightened the clinical integration bullets: each must state a mechanism
  AND reference a specific numeric value with units (e.g. "b-wave ~18 µV;
  reference >150 µV") — not just describe findings in general terms
- Added instruction to avoid: "This report...", "Based on...", "It should
  be noted that...", "It is important to..."

#### 2. Export to standalone HTML file
**Why:** The prototype lives inside Claude's chat widget, which means only
people with this conversation can see it. The dev team needs a file they can
open in any browser, share, and use as a reference for rebuilding in React.
A standalone HTML file with no external dependencies (except the Anthropic
API call) is the simplest handoff format.

**What changed:**
- Wrapped the widget code in a full HTML document
- Added proper DOCTYPE, meta charset, viewport tag
- Kept all data and logic self-contained (no CDN dependencies)
- Added a visible file header comment explaining what the file is,
  who built it, and what each section does


## Session 3 — 07 May 2026

### Changes made this session

#### 3. Source hyperlinks in Section 4 (classification snapshot)
**Why:** Clinicians will not trust a number they cannot verify. Every data
point in the classification snapshot needs to be traceable back to its
source database in one click. This is also a regulatory requirement for
any clinical decision support tool — the evidence trail must be auditable.
Each label in Section 4 is now a hyperlink to the specific variant or gene
page on that database (ClinVar, gnomAD, SpliceAI Lookup, Franklin, OMIM,
AlphaFold).

**What changed:**
- Added URLS constant: pre-constructed deep links per variant to each
  database. Stored separately from variant data for maintainability.
- Section 4 labels now render as <a> tags pointing to the relevant
  database page, opening in a new tab.
- SpliceAI links to spliceailookup.broadinstitute.org (the correct
  public tool, not a constructed URL).
- gnomAD links to the gene page (gnomAD v4) since variant-level deep
  links require the gnomAD variant ID format (chr-pos-ref-alt) which
  we do not yet store.

#### 4. Variant / gene lookup mode (search bar)
**Why:** Clinicians and researchers frequently want to look up a variant
or gene without generating a patient report — when reviewing literature,
in a meeting, when a colleague mentions a variant. Opening six browser
tabs to cross-reference databases is the current workflow. This feature
collapses that into one search.

**What changed:**
- Added second mode to the tool: "Variant lookup" accessible from the
  landing page alongside the existing report generation flow.
- New view: 'lookup' — search bar that queries the mock variant database.
- If found: shows a condensed evidence card (classification, key scores,
  gene function) plus direct links to all databases for that variant.
- If not found: shows direct links to all external databases with the
  search term passed as a query parameter where each database supports it.
- "Generate report" button on lookup results — bridges lookup mode into
  the full report generation flow.
- This is intentionally a mock implementation. In production, this would
  hit the real database APIs directly (ClinVar, gnomAD, SpliceAI, Franklin).

