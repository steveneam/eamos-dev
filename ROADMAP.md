# Eamos — Roadmap

## Product Layers

### Layer 1 — Variant Lookup (current)

Web tool: researcher or clinician types a gene or variant (HGVS notation) and gets an aggregated evidence report from ClinVar, VEP, SpliceAI, gnomAD, AlphaMissense, PubMed, and more — in one place.

**Status: prototype complete, mock data mode**

---

#### Completed milestones

| Session | Date | What was built |
| ------- | ---- | -------------- |
| 1–2 | pre-08 May 2026 | Hackathon prototype — widget demo, 5 IRD variants, 11 report sections, Anthropic API for AI summaries |
| 3 | 07 May 2026 | Backend architecture deep-read; all 4 tools identified as hardcoded to RPE65 |
| 4 | 08 May 2026 | DNA notation leads everywhere; plain language variant decoder; all 4 tools parameterised (gene-agnostic) |
| 5 | 09 May 2026 | JWT secret hardening; PubMed tool (fixture + live path); publications section; species selector |
| 6 | May 2026 | Report section restructure |
| 7 | May 2026 | PubMed abstract excerpts with per-article expand toggle |
| 8 | May 2026 | Eamos branding; Layer 1 lookup endpoint (`POST /api/v1/lookup`); frontend type-wired |
| 9 | May 2026 | DESIGN.md; 6 custom subagents; information hierarchy fix (Lookup = landing page; Patient Report = ghost button) |

---

#### Next for Layer 1

1. **Frontend styling pass** — finish items 2–16 from DESIGN.md:
   font weights, logo placeholder, species toggle pill shape, input border-radius,
   max-width container, card shadows, accessibility (contrast/focus),
   gene-only search mode, idle state polish, scroll-to-results, loading skeleton.

2. **Therapeutic Landscape** — wire gene therapy + trials data:
   - `GENE_THERAPY_MAP` (RPE65→Luxturna etc.) in `workflow.py` + `lookup_service.py`
   - ClinicalTrials.gov REST API v2 call (recruiting/active, filtered by gene name)
   - Populate `therapeutic_landscape` field in both `ReportPayload` builders

3. **Live API test** — set `USE_REAL_APIS=true`, run pipeline with `RPE65:c.260A>G`.
   Blocked on IT network clearance for Python outbound connections.
   Confirm SpliceAI REST endpoint accepts `GENE:c.cdna` format.

4. **Wire frontend to real backend** — replace mock data in React app with live FastAPI responses.
   Requires live API test (item 3) first.

---

### Layer 2 — Clinical Report Generation (next)

Patient-facing: upload sequencing report + clinical history → structured 11-section clinical report, AI-generated with clinician sign-off step. IRD scope. Enterprise-gated.

**Status: prototype complete in demo mode (Sarah Chen fixture, 5 IRD variants)**

Timeline TBD — depends on IT network clearance, live API stability, and governance decisions.
Access via ghost button on the variant lookup landing page. Not the primary product.

---

### Layer 3

Internal. Not discussed publicly.

---

## Known Blockers

| Blocker | Detail |
| ------- | ------ |
| IT network clearance | Python outbound connections restricted on corporate network. Blocks `USE_REAL_APIS=true` and all live database calls. |
| GitHub PAT rotation | Session 4 token was visible in chat. Generate a new one in GitHub settings, update `.env`. |
| SpliceAI REST endpoint | Web UI confirmed to accept `GENE:c.cdna`. REST API endpoint (`spliceai-38-xwkwwwxdwq-uc.a.run.app`) not yet live-tested — verify when `USE_REAL_APIS=true` runs. |

---

## Architecture Reference

```
Layer 1 lookup:   POST /api/v1/lookup  (no auth — public variant search)
Layer 2 report:   POST /api/v1/reports/upload → /api/v1/runs  (auth required)

Default mode:     USE_REAL_APIS=false  (all tools return fixture JSON)
                  LLM_PROVIDER=mock    (no OpenAI calls)
Database:         SQLite in-memory (data lost on restart — no migrations)
Node.js:          C:\temp\node\node-v22.15.0-win-x64 (portable)
Dev server:       npm run dev → http://localhost:5173
```
