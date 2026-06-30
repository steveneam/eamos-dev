# Frontend Rebuild Plan

> Superseded historical plan. Do not execute for live Eamos frontend work.
> The active frontend source of truth is the Next.js app in `app/web`.
> `app/frontend` is a frozen Vite reference retained only for comparison until
> Steven approves an exact deletion or regeneration task.

Rebuilding the Eamos frontend to match the Claude Design mocks (`Eamos Landing Page.html` and `Eamos Report Page.html`). React/Vite stack is kept (not migrated to Next.js). Design mocks are at `c:\Users\seamegdool\Downloads\`.

## Status

- **Phase 0** — COMPLETE. Foundation files written, TypeScript clean.
- **Phase 1** — COMPLETE. All 6 chunks built. TypeScript clean. Backend streaming endpoint live at `POST /api/v1/runs/{run_id}/chat/stream`.
- **Phase 2** — COMPLETE. `pages/LandingPage.tsx` + `pages/ReportPage.tsx` written. Old App.tsx moved to `pages/LegacyRunsApp.tsx` (default export renamed). New `App.tsx` is a thin BrowserRouter shell: `/` → LandingPage, `/report` → ReportPage, `/runs` → LegacyRunsApp. `tsc --noEmit` clean; Vite dev server transforms all three pages with HTTP 200 and no error events.
- **Integration hardening pass** — COMPLETE (M-001/2/3). Plus planner-skill Windows fix.
  - M-001: ReportPage detects `TypeError` from `fetch` → renders ErrorBlock `variant="offline"` with "Backend offline" copy + uvicorn command in `<code>`; sample-report link suppressed in offline branch.
  - M-002: `/healthz` now returns `llm_provider` + `use_real_apis`. `HealthzResponse` interface appended to `backend.ts`. New test `tests/test_health_api.py`.
  - M-003: New `tests/test_frontend_contract.py` — 7 parametrized cases asserting every Pydantic field on `LookupResponse`/`RunChatRequest`/`RunChatResponse`/`ReportPayload`/`EvidenceSourceSummary`/`VariantSummaryRow`/`PubMedArticle` appears in its TS interface in `backend.ts`. Verified failure mode (renaming a field fails the test).
  - Planner skill Windows fix: added `_filelock.py` shim (msvcrt on Windows, fcntl on POSIX), updated `qr.py` + `qr_commands.py` imports, restored missing `planner/resources/plan-json-schema.md`.

---

## Phase 0 — Foundation (COMPLETE)

All files written. `tsc --noEmit` passes.

| File | Status |
|------|--------|
| `src/index.css` | Done — new design tokens + backward-compat old vars |
| `vite.config.ts` | Done — `@/` alias + `/api` proxy to localhost:8000 |
| `src/components/ui/Card.tsx` | Done |
| `src/components/ui/ClassificationBadge.tsx` | Done — 5 variants |
| `src/components/ui/StatusPill.tsx` | Done — recruit/active/phase |
| `src/components/ui/Hairline.tsx` | Done |
| `src/components/brand/EamosLogo.tsx` | Done — sparkle mark + wordmark |
| `src/lib/variant-format.ts` | Done — `classify()` + `FORMAT_HINTS` |
| `src/lib/sources.ts` | Done — 6 source metadata objects |
| `src/lib/sample-report.ts` | Done — RPE65 p.Asp87Gly mock LookupResponse |
| `src/lib/chat.ts` | Done — `streamChat()` + `sendChat()` |

---

## Phase 1 — Component Tree (6 parallel chunks)

These 6 chunks are independent and can be built simultaneously by parallel agents.

### Chunk A — Nav + Search bar

**Files to create:**
- `src/components/layout/TopNav.tsx`

**What it does:** Sticky top nav with EamosLogo left, ghost "Patient reports" button right (links to the old workflow). Height 56px, 0.5px bottom hairline border.

**Search bar** (`src/components/search/SearchShell.tsx`):
- Mode toggle: "Gene variant" (default) | "AI" — changes submit button color and input placeholder
- Gene variant mode: two-field input (gene name + variant / HGVS)
- AI mode: single freetext input
- Chip hints below input: show `FORMAT_HINTS[classify(query)]` label as user types
- Submit button: teal in gene mode, ink-2 in AI mode
- On submit: calls `variantLookup()` from `src/lib/api.ts`, shows loading state

**Reference:** HTML mock lines 60–160 (`.ns-shell`, `.ns-input`, `.ns-submit`, `.chip`)

---

### Chunk B — Landing page sections

**Files to create:**
- `src/components/landing/SourceStrip.tsx`
- `src/components/landing/FeaturesGrid.tsx`
- `src/components/landing/HowItWorks.tsx`
- `src/components/landing/SiteFooter.tsx`

**SourceStrip:** Horizontal row of 6 source labels (ClinVar, VEP, SpliceAI, gnomAD, Franklin, PubMed) using `SOURCES` from `src/lib/sources.ts`. Each is a subtle link. Label "Powered by" on the left. 0.5px top + bottom borders.

**FeaturesGrid:** 3-column grid of feature cards. Features (from mock):
1. "One search, six databases" — aggregates ClinVar, gnomAD, VEP, SpliceAI, Franklin, PubMed
2. "ACMG-aligned classification" — criteria PM1, PM2, PP3 explained
3. "AI narrative" — plain-language clinical summary
4. "Variant decoder" — translates HGVS into amino acid change explanation
5. "Trial finder" — ClinicalTrials.gov active studies
6. "Cite-as-you-go" — every claim linked to its source

**HowItWorks:** Numbered steps (1→2→3) with teal circle numbers (reuse `Card` component number prop pattern). Steps: "Enter variant" → "Eamos queries 6 databases" → "Read your report".

**SiteFooter:** Simple footer — Eamos logo left, "Built for genomic medicine" tagline, links (About, GitHub, Contact). `var(--bg-soft2)` background.

**Reference:** HTML mock lines 330–600 (source strip, features, how-it-works, footer sections)

---

### Chunk C — Variant header + decoder

**Files to create:**
- `src/components/report/VariantHeader.tsx`
- `src/components/report/VariantDecoder.tsx`

**VariantHeader:** Shows gene name (large, teal-deep), protein change, transcript HGVS, genomic coordinate. Uses `ClassificationBadge` for ACMG. Breadcrumb: "Search › RPE65 › p.Asp87Gly". Uses `VariantSummaryRow[]` from `ReportPayload`.

**VariantDecoder:** Card (use `Card` component, number=1 or no number) with `report_payload.variant_decoder` text. Renders plain text with inline `<strong>` for key terms. Only renders if `variant_decoder` is non-null.

**Reference:** HTML mock lines 190–260 (`.v-header`, `.v-tag`, `.v-title`, `.v-sub`) and section after evidence table for decoder.

---

### Chunk D — AIStack + chat

**Files to create:**
- `src/components/aistack/EvidenceSummary.tsx`
- `src/components/aistack/AskEamos.tsx`
- `src/components/aistack/AIStack.tsx`

**EvidenceSummary:** Top half of AIStack. Shows `report_payload.ai_clinical_summary` as flowing prose. Inline citation superscripts `[CV]`, `[AM]` etc. linked to source URLs. Header: sparkle icon + "Eamos summary". Background: `var(--ink)` dark panel, white text.

**AskEamos:** Bottom half of AIStack fused seamlessly to EvidenceSummary (no visible border between them). Chat input at bottom, streaming response above. Uses `streamChat()` from `src/lib/chat.ts`. Requires `runId` prop — pass null for lookup mode (disable chat with placeholder "Save a patient run to ask questions").

**AIStack:** Composes `EvidenceSummary` + `AskEamos` with no seam. The two halves share one rounded-2xl container, ink-dark background top half, slightly lighter bottom half.

**Reference:** HTML mock lines 760–870 (`.ai-shell`, `.ai-body`, `.ai-summary`, `.ask-shell`, `.ask-input`)

---

### Chunk E — Report sections 2–6

**Files to create:**
- `src/components/report/EvidenceTable.tsx`
- `src/components/report/DiseaseSection.tsx`
- `src/components/report/TrialsSection.tsx`
- `src/components/report/PubMedSection.tsx`
- `src/components/report/LimitationsSection.tsx`

**EvidenceTable:** Tabular view of `evidence[]` array. Columns: Source | Status | Key findings | Link. Status shown as dot (green=completed, amber=fallback, red=blocked). Key findings pulled from `summary` object per source. Each row links to `source_url`.

**DiseaseSection:** Uses `Card`. Shows `clinical_phenotype`, `clinical_integration`, `expected_symptoms`, `recommendations` as labelled paragraphs. ACMG classification shown with `ClassificationBadge`.

**TrialsSection:** Uses `Card`. Shows `therapeutic_landscape` text + list of trials from `report_payload` (if available). Each trial shows NCT ID (mono font), title, description, `StatusPill` for phase/recruiting status.

**PubMedSection:** Uses `Card`. Renders `pubmed_articles[]` — each article as title (link), authors, journal + year.

**LimitationsSection:** Uses `Card`. Shows `limitations` text in italic, muted style. Small disclaimer.

**Reference:** HTML mock lines 790–960 (evidence table, disease section, trials list, pubmed, limitations card)

---

### Chunk F — FastAPI /api/v1/chat streaming endpoint (BACKEND)

**File to modify:** `app/backend/app/api/routes/` (check exact path — probably `runs.py` or `chat.py`)

**What to add:** `POST /api/v1/runs/{run_id}/chat` endpoint that:
1. Accepts `RunChatRequest` (already defined in `backend.ts` and presumably `app/schemas/`)
2. Retrieves the run's `report_payload` from the database
3. Calls `claude-haiku-4-5-20251001` (or whichever fast model) with the report as context
4. Streams the response as plain text (`StreamingResponse`, `media_type="text/plain"`)
5. Returns `RunChatResponse` shape for non-streaming fallback

**Note:** Check `app/backend/app/` structure before writing. The `RunChatResponse` type already exists in `backend.ts`. Verify the backend schema file has the matching Pydantic model.

---

## Phase 2 — Page Assembly

After Phase 1 chunks are complete.

### Files to create:
- `src/pages/LandingPage.tsx` — composes TopNav + SearchShell + SourceStrip + FeaturesGrid + HowItWorks + SiteFooter
- `src/pages/ReportPage.tsx` — composes TopNav + VariantHeader + AIStack + (VariantDecoder, EvidenceTable, DiseaseSection, TrialsSection, PubMedSection, LimitationsSection)

### Files to modify:
- `src/App.tsx` — replace monolithic component with React Router routes: `/` → LandingPage, `/report` → ReportPage. Preserve the old patient report workflow behind a ghost button or `/runs` route.
- `src/lib/api.ts` — verify `variantLookup()` sends correct request shape; add `chatStream()` wrapper if needed.

### Routing:
- `/` — LandingPage with SearchShell
- `/report?gene=RPE65&cdna=c.260A%3EG` — ReportPage showing lookup result
- `/runs` — old patient report flow (keep existing App.tsx sections behind this route)

---

## Design Token Reference

From HTML mocks (`Eamos Report Page.html`):

```
--bg: #ffffff           --bg-soft: #f8fafc      --bg-soft2: #f1f5f9
--ink: #0b1a2b          --ink-2: #1e3a5f        --ink-3: #475569
--ink-4: #94a3b8        --ink-5: #cbd5e1
--teal: #1D9E75         --teal-deep: #156b50    --teal-tint: #f0f7f4
--line: #e2e8f0         --line-2: #cbd5e1
--warn: #BA7517         --warn-tint: #FAEEDA    --warn-bdr: #FAC775
Fonts: Syne (display), Plus Jakarta Sans (body), JetBrains Mono (mono)
Hairline borders: 0.5px solid var(--line)
Border radius: 2xl (16px) for cards, full for pills/badges
```

## Key Constraints

- **Windows filesystem**: case-insensitive — no `Badge.tsx` alongside `badge.tsx`. New badge is `ClassificationBadge.tsx`.
- **Backward compat**: `App.tsx` uses old CSS vars (`--canvas`, `--muted-ink`, `--teal-ghost`, etc.) — these are preserved in `index.css`. Don't remove them until Phase 2 rewrites App.tsx.
- **Tailwind v4**: No `tailwind.config.ts`. Tokens go in `@theme inline {}` in `index.css`. Already done.
- **Stack**: React/Vite — do NOT migrate to Next.js despite the handoff spec saying so.
- **Backend mock mode**: `USE_REAL_APIS=false` (default). Use `sample-report.ts` for UI development without hitting real APIs.
- **Node.js path**: `C:\Program Files\nodejs\` — IT-managed system install, already on PATH. No PATH prepend needed.
