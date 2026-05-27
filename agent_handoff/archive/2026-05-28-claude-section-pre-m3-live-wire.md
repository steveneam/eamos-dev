# Archive — Claude section verbatim (pre-replace at 2026-05-28 00:41 +1000)

Archived per `agent_handoff/README.md` Hard Rule 1 before replacing `## Claude
— Last Task & Resume` in `agent_handoff/CURRENT.md` with the post-M-003
live-wire + ClinVar surface session state. The block below is the prior
section reproduced exactly (it was the 2026-05-27 23:55 planner-persist
narrative + the carried-over 2026-05-27 21:50 rich-HTML copy payload + Workbench
pass-2 slice 2 narrative).

---

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 1/2).
Section last edited: 2026-05-27 23:55 +1000 · Claude. Prior section
(2026-05-27 21:50, rich-HTML copy payload `fdfa9c9` + Workbench pass-2 slice 2
`fe9e3b4`) archived verbatim to
`agent_handoff/archive/2026-05-27-claude-section-pre-planner-persist.md` per
Hard Rule 1. Full incremental detail in `~/.claude/plans/next-session-eamos.md`.

**Session 2026-05-27 (late-late) — /planner persist on the post-Varsome v2 redesign sequencing. No commits, no source code changes.**

Branch `checkpoint/v2-batches-2026-05-17`, local==origin at `1a01059`
(unchanged from session start). Codex backend + handoff WIP uncommitted in
worktree (Task 12 ClinVar local adapter + Tasks 13-14 dbSNP + RepeatMasker
+ 0007 RLS migration + `lookup.py`/`schemas/lookup.py`/`services/lookup_sections.py`
M11 contract sketch + test + PROGRESS/v2-backend edits), untouched by Claude.

What this session did (no FE/BE source edits):
- Ran the `/planner` skill on the resolved post-Varsome spec. Planner
  orchestrator + architect + 11 parallel quality-reviewer verifiers; plan went
  through 2 QR fix-iterations before all groups returned PASS.
- Plan output: **21 decisions / 10 milestones / 5 waves / 30 code-intents /
  1 dataflow diagram**, persisted to a `plan.json` in tmp STATE_DIR
  (`C:\Users\seamegdool\AppData\Local\Temp\planner-fgqkndxz\plan.json`).
- Mid-session discovery during CURRENT.md re-read: **Codex had already
  delivered the M11 minimal section-fetch contract sketch at 21:31 +1000**,
  *before* my 22:55 CAR #1 opened it. The release files are
  `app/backend/app/api/routes/lookup.py`,
  `app/backend/app/schemas/lookup.py`,
  `app/backend/app/services/lookup_sections.py`,
  `app/backend/tests/test_lookup_section_fetch_contract.py`. Scope per
  Codex's lock-release note covers summary endpoint for M7 tile payloads +
  section endpoint for `publications` / `computational_deep_dive` + partial
  `clingen_vcep` expansion + per-section freshness fields + focused contract
  tests. **CAR #1 is now closed** (close note appended above the original
  CAR text in the Cross-Agent Requests thread). **Wave 2 collapses; Wave 3
  is immediately available.**
- Persisted the sequencing breakdown as `plans/v2-redesign-impeccable.md`
  §10.9 (5-wave table + decision/CAR map + sub-agent runbook + ship-then-rip
  note for M3 InSilicoGrid → M8 CalibratedInSilicoTable + commit-guard
  reminder).
- Archived prior Claude section verbatim to
  `agent_handoff/archive/2026-05-27-claude-section-pre-planner-persist.md`
  per Hard Rule 1, then replaced it with this update.

**Wave map (full detail in `plans/v2-redesign-impeccable.md` §10.9):**
- **Wave 1 (in-flight)** — M3 Report redesign + 8 Tier-1 component upgrades
  inside M3 (no scope creep; upgrades on Phase-0 primitives).
- **Wave 2 (COLLAPSED)** — M11 contract sketch already delivered by Codex
  21:31. Claude's only Wave 2 action is the TS mirror in `app/web/lib/backend.ts`
  + thin helpers in `app/web/lib/api.ts` (backend-led; FE does not reshape).
- **Wave 3 (parallel fan-out, ~3 weeks)** — M7 (FE-only matrix overture; cheap
  summary fields from initial /lookup payload; URL fragments; mobile h-scroll)
  + M8 (open CAR #2; calibrated table + composite bar; null-cal neutral cell;
  AM internal-only) + M9 (open CAR #3; ClinGen VCEP w/ all 5 cache-record
  provenance fields; public Evidence Repo only) + M10a (open CAR #4; gene-scoped
  pub count wires the `?pubScope=` URL param the M3 placeholder already honors).
- **Wave 4 (~2 weeks)** — M11 full ship: mobile-first sweep + LazySection
  applied to publications/ClinGen/computational; trials/disease/population
  stay eager (DL-013).
- **Wave 5 (deferred)** — M10b (~quarter PMC+LLM+provenance pipeline; no FE
  stub committed now) + M12 (BE-only events primitive; hard privacy guardrails)
  + M-010 AlphaMissense re-enable trigger (no-code watch criteria recorded
  in RISKS.md when M-010 is touched; never auto-flips, always surfaces the
  question to Steven).

**Coordination invariants baked into every code-intent (DL-019):** every
Claude commit uses explicit `git add -- <paths>` (NEVER `git add -A` /
`git add .`) so Codex's uncommitted Task 12 files
(`app/backend/app/services/clinvar_local.py`,
`app/backend/app/fixtures/data_sources/`,
`app/backend/tests/test_clinvar_local_adapter.py`,
`supabase/migrations/0007_optimize_rls_auth_uid_initplan.sql`, `PROGRESS.md`,
`plans/v2-backend.md`) do not sweep into a Claude commit and violate Hard
Rule 2 (own-section-only). M5 Workbench redesign stays a decoupled separate
lane unblocked from `fe9e3b4`. AskEamos stays COMING SOON. AlphaMissense
stays hidden in public display (internal calibration policy + fixtures still
fresh for M8); never re-enable without explicit Steven approval.

**Open / next-session (priority order):**
1. **TS mirror of Codex's M11 contract sketch.** Read
   `app/backend/app/schemas/lookup.py` + `app/backend/app/api/routes/lookup.py`
   + `app/backend/app/services/lookup_sections.py`; mirror the additive
   types into `app/web/lib/backend.ts`; add thin client helpers in
   `app/web/lib/api.ts` for the section-fetch endpoints (publications +
   computational_deep_dive + clingen_vcep + the M7 summary endpoint).
   Backend-led: FE does not reshape. tsc clean on `app/web` only
   (Vite `app/frontend` out-of-scope; see `plans/v2-redesign-impeccable.md`
   §10.9 M-002 acceptance criteria).
2. **M3 Tier-1 component upgrades inside M3 (Wave 1).** No backend
   dependency — Phase-0 primitive upgrades. Build the 8 components per
   `plans/v2-redesign-impeccable.md` §10.9 M-001 code-intents:
   `app/web/components/ui/{CiteChip,StackedCountBar,StickyVariantRibbon,PublicationModal}.tsx`
   + `Card` verdict prop + `ClassificationBadge` review-star slot +
   `AcmgCriteriaFold` met/not-met coloring + the `PublicationsCallout` toggle
   placeholder that honors `?pubScope=variant|gene` URL param.
3. **M7 FE-only matrix overture (Wave 3).** Mock-first against the contract
   sketch's M7 summary endpoint until the TS mirror lands; then live wire.
   `app/web/components/report/{MatrixOverture,MatrixTile}.tsx` + page mount
   in `app/web/app/report/page.tsx`; URL fragments + mobile h-scroll band.
4. **Per-slice CARs #2/#3/#4** open when each FE slice begins (M8 → CAR #2
   for `calibrated_*` predictor fields; M9 → CAR #3 for ClinGen Evidence
   Repo source-cache; M10a → CAR #4 for gene-scoped pub count). NEVER
   batched up-front.
5. **Workbench redesign Phase 2 / M5** is still unblocked from `fe9e3b4`
   (decoupled separate lane — schedule when capacity allows; not in the
   Wave 1-5 critical path).

**Workbench / Compare / per-metric copy / `feat-report-cards.webp` re-render
/ §6 landing backlog** stay parked as they were at 21:50 — none touched
this session. See archived prior Claude section for that earlier task's
detail.

**Resume prompt:**
`# Resume prompt · 2026-05-27 23:55 +1000 · Claude (/planner persist complete; CAR #1 closed by Codex's prior delivery; Wave 3 unblocked)`
`Eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE — full state + queue), agent_handoff/README.md (protocol), agent_handoff/CURRENT.md (## Log Edit-Lock + Active Status + ## Claude + ## Cross-Agent Requests — note CAR #1 closed by Codex's prior 21:31 release), agent_handoff/RISKS.md, plans/v2-redesign-impeccable.md §10 + §10.9 sequencing breakdown, then git status --short --branch && git log -9 --oneline.`
`Branch checkpoint/v2-batches-2026-05-17, local==origin at 1a01059 (unchanged from prior session). Codex backend + handoff WIP uncommitted in worktree (Task 12 clinvar_local + Tasks 13-14 dbSNP + RepeatMasker + 0007 RLS + M11 contract-sketch files: app/backend/app/api/routes/lookup.py, app/backend/app/schemas/lookup.py, app/backend/app/services/lookup_sections.py, app/backend/tests/test_lookup_section_fetch_contract.py), untouched.`
`Delta: /planner persist — 21 decisions / 10 milestones / 5 waves / 30 code-intents / 1 dataflow diagram captured in plans/v2-redesign-impeccable.md §10.9. CAR #1 (M11 contract sketch) closed by Codex's prior 21:31 delivery (cross-talk: my CAR opened at 22:55 after Codex shipped at 21:31). Wave 2 collapses; Wave 3 immediately available.`
`Next (priority order): (1) TS mirror Codex's M11 contract sketch into app/web/lib/backend.ts + thin helpers in app/web/lib/api.ts (backend-led; FE does not reshape; tsc clean app/web only); (2) M3 Tier-1 component upgrades inside M3 (Wave 1) — CiteChip + StackedCountBar + StickyVariantRibbon + PublicationModal (?pub= URL) + Card verdict prop + ClassificationBadge review-star slot + AcmgCriteriaFold met/not-met coloring + PublicationsCallout ?pubScope= placeholder per §10.9 M-001; (3) M7 FE-only matrix overture (Wave 3) mock-first then live wire — MatrixOverture + MatrixTile + page mount + URL fragments + mobile h-scroll; (4) per-slice CARs #2/#3/#4 open when each FE slice begins (NEVER batched); (5) M5 Workbench redesign still unblocked separate lane.`
`Plan artifacts: plan.json at C:\\Users\\seamegdool\\AppData\\Local\\Temp\\planner-fgqkndxz\\plan.json (tmp; ephemeral); persistent plan summary in plans/v2-redesign-impeccable.md §10.9. AlphaMissense stays hidden in public display (internal calibration policy + fixtures stay fresh for M8); re-enable trigger surfaces only if SpliceAI/REVEL/CADD/Primate3D all Pro-gated (Steven approval required, NEVER auto-flip).`
`Guardrails: no /runs, AlphaMissense display, Codex backend lane (app/backend/**), destructive git, push without OK. Commit Claude-lane with explicit git add -- <paths> (DL-019; baked into every code-intent in §10.9). End clear-safe.`

**Session 2026-05-27 (late) — Rich-HTML copy payload + Workbench pass-2 slice 2 (Primer + CRISPR + Align). 2 commits, both LIVE.**

Branch `checkpoint/v2-batches-2026-05-17`, local==origin at `fe9e3b4`
(two Claude/`app/web` commits on top of Codex's `f00d1c0`). Both LIVE
on `eamos-dev.vercel.app` via Vercel auto-deploy. Render backend
unchanged. Worktree carries Codex's WIP only (`PROGRESS.md`,
`agent_handoff/CURRENT.md` Codex section, `docs/local-first-…`,
`plans/v2-backend.md`, `app/backend/**`).

Commits (oldest → newest):
- `fdfa9c9` **Rich-HTML copy payload for report sections** —
  triggered by Steven's "the copy format is flat, no margins, no
  spacing, no borders, no wrap text, no class". New module
  `app/web/lib/report-html.ts` mirrors `lib/report-tsv.ts`
  function-for-function: 7 `htmlX` serializers that emit a full
  `<table>` fragment with a deep-teal banner row spanning the
  section, italic variant line under it, sub-section bands where
  the section has multiple blocks (e.g. Evidence: in-silico /
  per-source / ACMG), bordered cells with tinted thead, zebra
  rows, top-aligned wrap-text, sized columns via `<colgroup>`,
  live hyperlinks on Title/URL/NCT. Excel parses these as styled
  cells on paste. `components/ui/CopyButton.tsx` now accepts
  either `string` (legacy) or `{html, text}` and uses
  `navigator.clipboard.write([new ClipboardItem({...})])` to put
  BOTH `text/html` and `text/plain` on the clipboard — Excel /
  Sheets pick up the rich HTML, Notion / editors / AI chat get
  the TSV. `ReportClient` wires every Card's `actions` slot to
  `{html: htmlX(...), text: tsvX(...)}`.
- `fe9e3b4` **Workbench pass-2 slice 2 — Primer + CRISPR + Align
  panels.** Same verbatim-port pattern as slice 1 (`248552a`):
  8 component files (`primer/{PrimerPanel,PrimerResultCard}`;
  `crispr/{CrisprPanel,DesignTab,GuideTrack,IndelSpectrum,
  OutcomesTab}`; `align/AlignPanel`) copied from `app/frontend`
  to `app/web` with `'use client'` prepended to each. 9 lib files
  (`alignment-pairwise`, `crispr-{disclosure,guide-map,
  guide-ranking,sample,tide-sample}`, `primer-{form,metrics,
  sample}`) copied verbatim. `lib/api.ts` adds `designPrimers`,
  `designGuides`, `analyzeTide` against the frozen
  `/api/v1/{primer,crispr,crispr/tide}` contracts (mock-first
  fallback to PRIMER_SAMPLE / CRISPR_SAMPLE / CRISPR_TIDE_SAMPLE
  so panels work offline). `WorkbenchShell` replaces the four
  "deferred to pass 2" placeholders with a `renderToolPanel()`
  switch that mounts Primer / CRISPR / Align panels; Compare
  keeps the COMING SOON state. One Next.js fix in `AlignPanel`:
  `import.meta.env.VITE_*` → `process.env.NEXT_PUBLIC_*`. Also
  adds a `console.warn` in `CopyButton` for when both
  `clipboard.write` and `writeText` throw (hardening against
  silent dev-tool API hijacks; can't happen in user runtime).

Verified:
- `cd app/web && ./node_modules/.bin/tsc --noEmit` silent after
  every commit.
- Live in Chrome MCP at `http://localhost:3000` (PID 41072 orphan):
  all 7 report copy buttons present + on click button flips to
  "COPIED" + audit of captured payload shows banner + colgroup +
  borders + wrap + zebra (Pubs / Trials / Population HTML had
  10/39/1 anchors respectively). Workbench `/workbench` w/ tab
  clicks: Primer panel renders Sanger/qPCR/ARMS form; CRISPR
  renders SpCas9 Design/Outcomes tabs; Align renders pairwise
  alignment w/ AB1 + FASTA inputs.
- In-page preview of Publications HTML matched the intended Excel
  render (banner, italic variant line, summary band, header fill,
  bordered cells, wrap text, live hyperlinks).

**Operational gotcha** — when capturing clipboard via
`mcp__chrome-devtools__evaluate_script`, I monkey-patched
`navigator.clipboard.write` + `writeText` and only deleted
`window.__captured` in cleanup. The hijacks stayed bound to the
deleted variable, so a subsequent Copy click threw silently. Fixed
by reloading the page (per-tab; per-document). The post-`fe9e3b4`
`console.warn` will surface this kind of dead-silent failure next
time. **If running a clipboard-capture probe again: ALWAYS save
the originals and restore them in cleanup, or just reload after.**

**AskEamos chat (Workbench Scratchpad tab + Report §7 AI Card)
stays COMING SOON** per Steven. Codex's `/api/v1/chat` +
`/api/v1/chat/stream` are live; block is purely commercial budget
(memory: `feedback_askeamos_parked`). Do not wire until explicit
go-ahead.

**Locked UX preferences (carry forward, do not re-litigate):**
- Workbench: 3 stacked viewer windows w/ collapse chevrons LEFT;
  zoom slider hover-reveals inside Sequence only; chrome stripped
  to `{gene} · {variant}` + functional controls on the right;
  Scratchpad top of side panel on warm-yellow w/ Log/Notes/Ask
  Eamos tabs; Primer / CRISPR / Align tool panels now real (no
  more pass-2 stubs), Compare still placeholder.
- Report: 7 numbered Cards in the locked order with Locus merged
  into Gene context snapshot, AI summary last; chevrons LEFT;
  sections independent; **CopyButton in every Card header writes
  rich Excel-styled HTML (text/html) + plain TSV (text/plain) so
  Excel paste looks formatted (banner, borders, wrap, hyperlinks,
  zebra rows) while plain-text targets still get clean TSV.**

**Open / next-session (priority order):**
1. **Workbench redesign Phase 2 / M5** in
   `plans/v2-redesign-impeccable.md` — unblocked by `fe9e3b4`.
   The 4 panels (Primer / CRISPR / Align / Compare) now have real
   FE surfaces; M5 is the impeccable design pass over them.
2. **Compare tool** is still a placeholder. The Vite app has no
   ComparePanel component — needs a fresh design (was deferred
   from the start). Talk to Steven before building.
3. **Per-metric copy buttons** inside the report cards (Steven
   parked when section-level shipped). The new HTML serializers
   make this easy: each metric box / table gets its own
   `<CopyButton>` with a smaller `{html, text}` slice. Likely
   candidates: 4 Call Cards (one button each), In-Silico
   predictors table, Curated variants pivot, Associated
   conditions table.
4. Re-render `feat-report-cards.webp` without the baked
   "alphamissense on hold" text (predates 2026-05-19
   display-only-hide decision).
5. §6 landing backlog (mobile-nav blur, legal pages on warm
   surface + composed nav + breadcrumb, retire/repurpose
   `ls-drift`/`ls-shimmer`); formal impeccable `audit` +
   `quality-reviewer` gates for M2 (Landing) and M3 (Report).

Runtime notes (Codex 2026-05-27): `TwoBitReferenceGenomeStore`
proven locally, not yet wired into `/api/v1/viewer`. Viewer still
serves fixtures unless `USE_REAL_APIS=true`; live mode fetches
Ensembl REST sequence, not the 2bit reader. Tool panels just
ported run mock-first too (`PRIMER_SAMPLE` / `CRISPR_SAMPLE` /
`CRISPR_TIDE_SAMPLE`) — they'll talk to Codex's
`/api/v1/{primer,crispr}` when the backend is up and these
endpoints respond, with mocked fallback baked in. Doesn't affect
FE iteration.

**Resume prompt:**
`# Resume prompt · 2026-05-27 21:50 +1000 · Claude (2 commits LIVE; Workbench Phase 2 unblocked)`
`Eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE — full state + queue), agent_handoff/README.md (protocol), agent_handoff/CURRENT.md (## Log Edit-Lock + Active Status + ## Claude + ## Cross-Agent Requests), agent_handoff/RISKS.md, plans/v2-redesign-impeccable.md, then git status --short --branch && git log -9 --oneline.`
`Branch checkpoint/v2-batches-2026-05-17, local==origin at fe9e3b4 (2 Claude/app/web commits on top of Codex f00d1c0, both LIVE on eamos-dev.vercel.app). Codex's backend + handoff WIP uncommitted in worktree, untouched.`
`Delta: (1) fdfa9c9 rich-HTML copy payload — new lib/report-html.ts, CopyButton writes text/html + text/plain via ClipboardItem; Excel pastes the report sections as fully-styled tables (banner, borders, wrap, sized columns, zebra, hyperlinks); TSV preserved for plain-text targets. (2) fe9e3b4 Workbench pass-2 slice 2 — Primer + CRISPR + Align panels ported verbatim from app/frontend with 'use client'; 9 lib files copied; designPrimers/designGuides/analyzeTide added to lib/api.ts with mock-first fallbacks; WorkbenchShell renderToolPanel() switch replaces the 4 deferred stubs (Compare stays COMING SOON); CopyButton gains console.warn on dual-throw.`
`Op gotcha logged: when probing clipboard via Chrome MCP evaluate_script, ALWAYS restore navigator.clipboard.write/writeText in cleanup or reload the tab afterwards — leaked hijack causes silent copy failures.`
`Next: (1) Workbench redesign Phase 2 / M5 in plans/v2-redesign-impeccable.md (NOW UNBLOCKED — all 4 tool surfaces exist); (2) Compare tool design (still placeholder, discuss before building); (3) per-metric copy buttons inside cards (parked, easy w/ new html serializers); (4) feat-report-cards.webp re-render (alphamissense baked-in text); (5) landing §6 backlog + formal impeccable audit + quality-reviewer gates for M2/M3.`
`Verification toolkit: tsc via app/web/node_modules/.bin/tsc; browser via Chrome MCP on localhost:3000 (pre-existing orphan dev server PID 41072, do NOT kill); Excel-paste HTML/TSV via clipboard probe — restore APIs after! Python at C:\\Program Files\\Python310\\python.exe.`
`Guardrails: no /runs, AlphaMissense display, Codex backend lane (app/backend/**), destructive git, push without OK. Commit Claude-lane with explicit git add -- <paths>. End clear-safe.`
