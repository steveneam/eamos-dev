## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 1/2).
Section last edited: 2026-05-27 12:45 +1000 · Claude. Prior section
(2026-05-25 03:05, large `/report` + landing FE pass + stealth night)
archived verbatim to
`agent_handoff/archive/2026-05-27-claude-section-pre-workbench-and-report-restructure.md`
per Hard Rule 1. Full incremental detail in
`~/.claude/plans/next-session-eamos.md`.

**Session 2026-05-27 — Workbench pass-2 slice 1 + viewer UX + chrome diet + scratchpad + report restructure + copy-to-Excel TSV (7 commits, all LIVE).**

Branch `checkpoint/v2-batches-2026-05-17`, local==origin at `f00d1c0`
(Codex backend bundle on top of my 7 Claude/`app/web` commits). All 7
swept up to origin in Codex's `f00d1c0` push so all changes auto-deployed
to `eamos-dev.vercel.app`. Render backend unchanged.

Commits (oldest → newest):
- `248552a` **Workbench pass-2 slice 1 — real viewer parity.** Replaced
  the pass-1 skeleton `SequenceViewerV2` (141 lines) with the full Vite
  viewer (690 lines) + 6 sub-components ported verbatim with `'use
  client'`: `CodonDetail` (615), `EditPopoverV2` (221, the right-click
  "differentiator moment" per `plans/v2-redesign-impeccable.md` §5),
  `GeneMinimap` (177), `ProteinView` (296), `ViewerToolbar` (157),
  `HistoryTimeline` (47), plus `lib/workbench/codon-layout.ts` (43).
  All existing app/web helpers (`@/lib/workbench/{gene-window,
  codon-table,edit-state}`, `@/lib/backend`, `viewer-types`) already
  exported what the real viewer needs — no helper edits.
- `5caab62` **Workbench viewer UX.** Restored 2/3 viewer + 1/3 side
  panel layout (root cause: Vite→Next port lost the `--maxw` /
  `--side-w` CSS-var aliases inside `:root`, leaving the `.wb` grid
  template falling back to undefined and eating the right column).
  Dropped the Sequence/Protein toggle: now renders **GeneMinimap →
  ProteinView → CodonDetail** in order, each wrapped in a collapsible
  section header (`<SectionHeader>` w/ chevron). Added
  `max-height: 62vh` + `overflow-y: auto` on `.sv-detail` so the
  sequence panel scrolls Benchling-style internally instead of
  stretching the page. Plumbed `onToggleMinimap` callback through
  `WorkbenchShell` so the inline chevron and the legacy
  `navCollapsed`/ZoomSlider "Hide map" stay in sync.
- `4bf4b82` **Workbench chrome diet + tabbed Scratchpad in yellow.**
  Stripped the SVG bar-logo from `WorkbenchClient` (Steven read it as
  a hamburger), removed the descriptive `ContextStrip` subtitle
  ("p.Asp87Gly · NM_000329.3 · chr1:…") and the `CanvasHeader` title
  + sub ("Sequence viewer · RPE65 (ENSG…) · …"); new title is just
  `{gene} · {variant}`. Retired Gene/Exon/Codon zoom presets + Hide
  map button from `ZoomSlider`. Side panel: every section
  collapsible via chevron header (matches viewer); **Scratchpad
  promoted to top** on warm-yellow OKLCH surface
  (`oklch(98% 0.035 95)`) with tabs **Log / Notes / Ask Eamos**.
  "Exons (click to view)" disclosure restyled to share the same
  chevron pattern.
- `18cedfd` **Zoom slider scoped to Sequence window; chevrons LEFT.**
  Moved the zoom overlay out of the outer `.viewer` (was overlapping
  the ViewerToolbar's Undo/Redo cluster) into a new
  `.sv-sequence-wrap` that wraps the Sequence section only — hover-
  revealed there. Moved every collapse chevron to the **left** of
  its title (viewer SectionHeader, side-section-head, nested
  side-nested-head Exons disclosure) — Google Docs / VS Code
  disclosure pattern.
- `760e6e1` **Report `<Card>` is collapsible.** Each `<Card>`
  instance now has its own `useState` for open state with a
  left-aligned chevron header. Defaults open. Each section is
  independent — clicking one chevron toggles only that card.
- `8cf4ea6` **Report restructure + copy-to-Excel TSV per section.**
  Section order locked: **1 Population · 2 Evidence by source · 3
  Gene context snapshot (Locus context MERGED IN as sub-header) ·
  4 Conditions · 5 Publications · 6 Trials · 7 AI evidence summary
  (LAST, was unnumbered block after call cards — now a real Card).
  VariantDecoder renders below 7 un-numbered.** Built new
  `CopyButton` primitive (`components/ui/CopyButton.tsx`,
  two-square icon → green ✓ "COPIED" for ~1.5s, hover lift,
  click-stop-propagation). Built `lib/report-tsv.ts` with seven
  per-section TSV serializers. `<Card>` switched from `<button>` to
  `<div role="button">` so the CopyButton in the `actions` slot
  isn't an invalid nested interactive control.
- `9910431` **Wire copy buttons for publications + trials.**
  `PubMedSection` and `TrialsSection` accept an optional `actions`
  slot forwarded to their internal `<Card>`; `ReportClient` passes
  CopyButtons bound to `tsvPublications` / `tsvTrials`.

Verified:
- `cd app/web && npx tsc --noEmit` clean after every commit.
- `npm run build` (Next 16 webpack) exit 0 (5.8min) once at the end
  of slice 1; subsequent commits relied on tsc + dev-server smoke.
- Browser-verified each commit on `http://localhost:3000` (pre-
  existing orphan dev server PID 41072) via Chrome MCP a11y tree +
  screenshots.
- **TSV→Excel parity** verified by overriding
  `navigator.clipboard.writeText` on the live page to capture
  copied text, then parsing through Python
  `csv.reader(io.StringIO(text), delimiter='\t')` (= what Excel does
  on paste). Publications = clean **7-col** grid (PMID · Title ·
  Authors · Journal · Year · URL · Snippet status), trials = clean
  **9-col** grid (NCT · Status · Phase · Match level · Title ·
  Conditions · Interventions · Locations · URL). Multi-value cells
  (multiple conditions / locations) use ` | ` as in-cell separator
  so they don't blow out into extra columns. Python is at
  `C:\Program Files\Python310\python.exe`.

**AskEamos chat (Workbench Scratchpad tab + Report §7 AI Card) stays
COMING SOON** per Steven. Codex confirmed backend `POST /api/v1/chat`
+ `/api/v1/chat/stream` exist with shape `{ question, variant_context:
ReportPayload, optional history, optional workbench }` — the block is
purely commercial (Steven not ready to fund OpenAI/Anthropic API key
budget). Do not wire until explicit go-ahead.

**Locked UX preferences (carry forward, do not re-litigate):**
- Workbench: 3 stacked viewer windows w/ collapse chevrons LEFT;
  zoom slider hover-reveals inside Sequence only; chrome stripped to
  `{gene} · {variant}` + functional controls on the right; Scratchpad
  top of side panel on warm-yellow w/ Log/Notes/Ask Eamos tabs.
- Report: 7 numbered Cards in the order above with Locus merged into
  Gene context snapshot, AI summary last; chevrons LEFT; sections
  independent; CopyButton in every Card header.

**Open / next-session:**
1. **Workbench pass-2 slice 2 — port the 4 tool panels.** Primer
   (`PrimerPanel` + `PrimerResultCard` + `primer-form` +
   `primer-metrics` + `primer-sample` lib), CRISPR (`CrisprPanel` +
   `DesignTab` + `GuideTrack` + `IndelSpectrum` + `OutcomesTab` +
   crispr-disclosure / crispr-guide-map / crispr-guide-ranking /
   crispr-sample / crispr-tide-sample lib), Align (`AlignPanel` +
   `alignment-pairwise` lib). Same pattern as slice 1; ~2,000+ lines
   incl. tests. Contracts confirmed stable by Codex: `/api/v1/primer`,
   `/api/v1/crispr`, `/api/v1/align` (NOT under `/workbench/*` —
   Vite `lib/api.ts` already uses these paths). Primer
   `specificity_detail` will be additive/optional; TIDE stays
   separate as `/api/v1/crispr/tide`. After slice 2, the Workbench
   redesign Phase 2 in `plans/v2-redesign-impeccable.md` M5
   unblocks.
2. **(Optional)** per-metric copy buttons inside the report cards.
   Steven said "move on" after section-level shipped — parked. Each
   metric box / table can take its own `<CopyButton>` with a smaller
   TSV slice.
3. **(Optional)** re-render `feat-report-cards.webp` without the
   baked "alphamissense on hold" text (violates 2026-05-19 display-
   only-hide decision).
4. §6 landing backlog (mobile-nav blur, legal pages on warm surface +
   composed nav + breadcrumb, retire/repurpose `ls-drift`/
   `ls-shimmer`), formal impeccable `audit` + `quality-reviewer`
   gates for M2 (Landing) and M3 (Report).

Runtime notes (Codex 2026-05-27): `TwoBitReferenceGenomeStore` is
proven locally but NOT yet wired into `/api/v1/viewer`. Viewer still
serves fixtures unless `USE_REAL_APIS=true`; live mode currently
fetches Ensembl REST sequence, not the 2bit reader. Doesn't affect FE
work — the contract / shape is stable.

**Resume prompt:**
`# Resume prompt · 2026-05-27 12:45 +1000 · Claude (7 commits LIVE; Workbench slice 2 next)`
`Eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE — full state + queue + 7-commit summary), agent_handoff/README.md (protocol), agent_handoff/CURRENT.md (## Log Edit-Lock + Active Status + ## Claude + ## Cross-Agent Requests), agent_handoff/RISKS.md, plans/v2-redesign-impeccable.md, then git status --short --branch && git log -9 --oneline.`
`Branch checkpoint/v2-batches-2026-05-17, local==origin at f00d1c0 (Codex backend bundle on top of 7 Claude/app/web commits 248552a..9910431, all LIVE on eamos-dev.vercel.app via Vercel auto-deploy).`
`Delta: Workbench pass-2 slice 1 (real viewer parity); viewer UX (2/3 width + 3 stacked windows + Benchling internal scroll); chrome diet (no logo SVG, no descriptive subtitles, no Gene/Exon/Codon, no Hide map; title = "gene · variant"); zoom slider scoped to Sequence only; all chevrons LEFT (Google Docs); Scratchpad → top of side panel on yellow w/ Log/Notes/Ask Eamos tabs; /report Cards collapsible (independent); full report restructure (1=Pop, 2=Evidence, 3=Gene context w/ Locus merged in, 4=Conditions, 5=Pubs, 6=Trials, 7=AI summary last); CopyButton primitive + per-section TSV via lib/report-tsv.ts wired into all 7 cards including pubs+trials (verified TSV→Excel via Python csv parser).`
`AskEamos stays COMING SOON — backend /api/v1/chat exists but Steven not ready to fund API key (memory: feedback_askeamos_parked). Do not wire.`
`Next: (1) Workbench pass-2 slice 2 = port Primer/CRISPR/Align tool panels from app/frontend/src/components/workbench/{primer,crispr,align}/ following the slice-1 pattern, contracts /api/v1/primer · /api/v1/crispr · /api/v1/align confirmed stable. (2) Optional per-metric copy buttons. (3) §6 landing backlog + impeccable audit gates.`
`Verification toolkit: tsc via ./node_modules/.bin/tsc in app/web; browser via Chrome MCP on localhost:3000 (pre-existing orphan dev server PID 41072, do NOT kill); TSV/Excel parity via Python at C:\\Program Files\\Python310\\python.exe — override navigator.clipboard.writeText on the live page then csv.reader(delimiter='\\t').`
`Guardrails: no /runs, AlphaMissense display, Codex backend lane (app/backend/**), destructive git, push without OK. Commit Claude-lane with explicit git add -- <paths>. End clear-safe.`

