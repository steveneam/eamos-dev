# Eamos — Roadmap

## Product surfaces

| Surface | Route | Status |
| ------- | ----- | ------ |
| **Landing** | `/` | v2 in progress (Session 12) — refreshed copy + cross-DB strip without Franklin |
| **Variant report** | `/report` | v2 in progress — new modules: locus context, in-silico grid, ACMG fold, curated variants distribution, structured conditions, publications callout |
| **Workbench** | `/workbench` | v1 in progress — sequence viewer + click-to-edit + Primer / CRISPR / Align / Compare + tool-aware AskEamos pill |
| **Patient report (Layer 2)** | `/runs` | **Frozen** — v1 design system. No new features. Redesign deferred to Layer 2 v2. |

---

## Layer 1 v1 (variant lookup) — DONE

Hackathon prototype → fixture-backed pipeline → React/Vite scaffolding with new design tokens, all 5 lookup report sections rendering. Phases 0–2 of the frontend rebuild complete; backend lookup endpoint live at `POST /api/v1/lookup`.

---

## Layer 1 v2 (active)

Source mocks: `e:\Web tool\Claude Design\Eamos Landing Page.html` + `Eamos Report Page v2.html`. Plan: `plans/v2-frontend.md` (Claude Code) + `plans/v2-backend.md` (Codex).

### Frontend (Claude Code)

| ID | Milestone |
| -- | --------- |
| FE-0 | Foundation refresh — token additions (canvas, sequence palette, AA palette), hairline utility, width helpers |
| FE-1 | Landing v2 — drop Franklin from source strip, refresh copy/icons |
| FE-2 | Report v2 new modules — LocusContext / InSilicoGrid / AcmgCriteriaFold / CuratedVariantsGrid / AssociatedConditions / PublicationsCallout |
| FE-3 | Variant header v2 — cross-DB strip, tools row, 4-stat row |

### Backend (Codex)

| ID | Milestone |
| -- | --------- |
| BE-1 | Franklin archive — move to `archive/franklin/`, remove from registry, services, rules, config, tests |
| BE-2 | Lookup payload v2 — six new `ReportPayload` fields with fixture data for RPE65 c.260A>G |
| BE-3 | Lookup-scoped chat endpoint — `POST /api/v1/chat` (siblings the existing run-scoped chat) |

---

## Workbench v1 (active, in parallel)

Source mock: `Eamos Workbench v1.html` + `Workbench/*.{js,css}`. Same plan files as Layer 1 v2.

### Frontend (Claude Code)

| ID | Milestone |
| -- | --------- |
| FE-4 | Workbench shell — page, layout chrome, tool state, context strip |
| FE-5 | Sequence Viewer + click-to-edit — codon table port, all tracks, edit popover, scratchpad |
| FE-6 | Primer + CRISPR panels — segmented mode tabs, output tables, HDR ssODN block |
| FE-7 | Alignment + Comparator — Canvas chromatogram, pairwise alignment, 2–3 variant grid |
| FE-8 | AskEamos pill (tool-aware) — floating panel, suggested-question chips per tool, persistent across tool switches |

### Backend (Codex)

| ID | Milestone |
| -- | --------- |
| BE-4 | Workbench engine stubs — `POST /api/v1/primer`, `/crispr`, `/align` returning canned data per variant |

### Test sweep (Codex)

| ID | Milestone |
| -- | --------- |
| BE-5 | `test_franklin_removed.py` + extend `test_frontend_contract.py` for v2 schema fields |

---

## M-002 follow-ups (after v2 ships)

- Real Primer3 invocation
- Real CRISPOR (or CHOPCHOP / Cas-OFFinder + Doench-2016) for gRNA scoring
- Real Needleman–Wunsch alignment + biopython AB1 parser
- Live `/api/v1/chat` calls to Anthropic / OpenAI (replace mock-mode response)
- Live data feeds for the six new `ReportPayload` modules (replace fixtures)
- Persist Workbench sessions keyed by anonymous session id, then account id when auth lands
- Multi-variant editing in the sequence viewer

---

## Future phases

### Mouse mm39 lookup

Same architecture as human; database stack swap (MGI, IMPC, VEP-mouse, dbSNP). Hidden from v2 UI but kept on the roadmap. The species toggle returns when the mouse pipeline is ready.

### Layer 2 v2 redesign

Patient report flow (`/runs`) brought onto the v2 design system. Out of scope for the current cycle.

### Layer 3

Internal. Not discussed publicly.

---

## Known blockers

| Blocker | Detail |
| ------- | ------ |
| Live API verification | Set `USE_REAL_APIS=true` and run pipeline with `RPE65:c.260A>G`. Confirm SpliceAI REST endpoint accepts `GENE:c.cdna` format. |
| GitHub PAT rotation | Session 4 token visible in chat — generate a new one, update `.env`. |

---

## Architecture reference

```
Layer 1 lookup:   POST /api/v1/lookup           (public, no auth)
Layer 1 chat:     POST /api/v1/chat (+ /stream) (NEW — lookup/Workbench scoped, no run id)
Workbench tools:  POST /api/v1/primer | /crispr | /align (NEW — stub responses for v2)
Layer 2 reports:  POST /api/v1/reports/upload → /api/v1/runs  (auth required, frozen)
Layer 2 chat:     POST /api/v1/runs/{run_id}/chat/stream     (unchanged)

Default mode:     USE_REAL_APIS=false  (all tools return fixture JSON)
                  LLM_PROVIDER=mock    (no OpenAI/Anthropic calls)
Database:         SQLite in-memory (data lost on restart)
Dev server:       npm run dev → http://localhost:5173
```
