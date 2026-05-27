> Archived verbatim from `agent_handoff/CURRENT.md` "## Claude — Last Task & Resume"
> on 2026-05-27 23:55 +1000 by Claude before replacing the section with the
> planner-persist update (per README Hard Rule 1 / Hard Rule 9: append+archive
> the old verbatim first if it has unrecorded detail, then replace — do not stack).
>
> This is the 2026-05-27 21:50 +1000 Claude section that covered the rich-HTML
> copy payload (`fdfa9c9`) + Workbench pass-2 slice 2 (`fe9e3b4`) commits.

---

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 1/2).
Section last edited: 2026-05-27 21:50 +1000 · Claude. Prior section
(2026-05-27 12:45, 7-commit Workbench+Report restructure) archived verbatim to
`agent_handoff/archive/2026-05-27-claude-section-pre-rich-html-and-workbench-slice2.md`
per Hard Rule 1. Full incremental detail in
`~/.claude/plans/next-session-eamos.md`.

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
