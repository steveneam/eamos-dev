# Eamos — Roadmap

> Updated 2026-05-16 (Session 16/17) after a whole-project Codex adversarial
> review + a deepthink sessionized-plan pass. State is accurate to the working
> tree; **nothing is committed** (standing "no commit unless asked"). The
> resumable execution plan lives in
> `C:\Users\seamegdool\.claude\plans\next-session-eamos-hardening.md`.

## Product surfaces

| Surface | Route | Status |
| ------- | ----- | ------ |
| **Landing** | `/` | v2 shipped |
| **Variant report** | `/report` | v2 shipped + variant-search engine **live-verified** (real APIs resolve RPE65 c.260A>G end-to-end) |
| **Workbench** | `/workbench` | v1 partial — sequence viewer + click-to-edit shipped (FE-4/5); Primer/CRISPR/Align/Compare panels + AskEamos pill pending (FE-6/7/8) |
| **Patient report (Layer 2)** | `/runs` | **Feature-frozen** v1 design — no new features, BUT receiving a security patch (auth) this cycle (a feature freeze is not a security freeze) |

---

## Layer 1 — DONE & live-verified

- **v1:** fixture-backed pipeline + React/Vite scaffolding, all lookup report sections.
- **v2:** Landing v2, Report v2 modules (LocusContext / InSilicoGrid / AcmgCriteriaFold /
  CuratedVariantsGrid / AssociatedConditions / PublicationsCallout), variant header v2.
- **Variant-search engine (BE-8…BE-13 + FE-14):** input normalization, VariantValidator
  strict GRCh38 coords, strict-genomic plugin loop, LitVar2/PubMed publications, frozen
  warnings contract, persistent variant cache, frontend search robustness. **Live-verified
  2026-05-16:** `genomic_hg38=1-68444869-T-C`, gnomAD/VariantValidator live, 10 live
  PubMed articles, cache + `?refresh=true` correct. Offline 80/4 pytest, contract 40/40,
  vitest 21/21.

---

## Workbench v1 (active)

Source: `Eamos Workbench v1.html` + `Workbench/*.{js,css}`. Plan: `plans/v2-frontend.md`.

| ID | Milestone | Status |
| -- | --------- | ------ |
| FE-4 | Workbench shell — layout chrome, tool state, context strip | ✅ Done |
| FE-5 | Sequence Viewer + click-to-edit — codon table, tracks, popover, scratchpad | ✅ Done |
| FE-6 | Primer + CRISPR panels — segmented mode tabs, output tables, HDR ssODN | ⏳ Pending (Session 3) |
| FE-7 | Alignment + Comparator — Canvas chromatogram, pairwise, 2–3 variant grid | ⏳ Pending (Session 4) |
| FE-8 | AskEamos pill (tool-aware) — floating panel, per-tool chips, persistent | ⏳ Pending (Session 5) |
| BE-4 | Workbench engine stubs — `/api/v1/primer | /crispr | /align` | ✅ Done |
| BE-5 | Test sweep — `test_frontend_contract.py` v2 schema | ✅ Done (40/40) |

---

## Hardening cycle (active — from the whole-project Codex review, 2026-05-16)

Risk-ordered: patient-data security → evidence correctness → invariant hardening →
features → docs. Lanes: Codex owns `app/backend/**`, Claude owns `app/frontend/**`;
the lanes don't share files so they run concurrently.

| Sev | Finding | Owner | Session |
| --- | ------- | ----- | ------- |
| CRITICAL | C1/C2 — `/runs,/reports,/reviews,/search` unauthenticated; `/reports/upload` open | Codex | **1 — ✅ fixed & verified** |
| HIGH | H1 — `/report?q=` silently rendered the RPE65 demo for arbitrary queries | Claude | **1 — ✅ fixed** |
| HIGH | H2 — `spliceai.py` violates strict-genomic invariant (re-queries by gene instead of `live_stub`) | Codex | **2 — ✅ fixed & verified** |
| HIGH | H3 — `variant_validator.py` `_mutate_variant()` fabricates consequence/variation_type when no coords | Codex | **2 — ✅ fixed & verified** |
| MED | M1 — `variant_cache_repo` select-then-insert race → IntegrityError | Codex | **2 — ✅ fixed (atomic upsert)** |
| MED | M2 — `pubmed.py` miss path returns `raw=None` vs zero-schema (`{}`) | Codex | **2 — ✅ fixed** |
| MED | M3 — `base.py` `load_fixture()` unprotected JSON read breaks never-raise | Codex | **2 — ✅ fixed** |
| MED | M4 — PublicationsCallout AI-summary button was a dead control | Claude | **1 — ✅ fixed** |
| LOW | L1 — Report card meta hardcoded `RPE65 · NM_000329.3` | Claude | **1 — ✅ fixed** |
| LOW | L2 — inert Workbench settings button (no onClick/aria-label) | Claude | **1 — ✅ fixed** |
| LOW | L3 — `plans/v2-backend.md:11` stale BE-5 sentence | Codex | **2 — ✅ fixed** |
| LOW | L4 — `plans/v2-frontend.md:317` obsolete FE-3.6 "remaining" block | Claude | **1 — ✅ fixed** |

---

## Session plan (deepthink output, 2026-05-16; re-sequenced backend-first)

> **Re-sequenced 2026-05-16 (user decision):** Codex completes ALL backend
> first — S2 hardening, then the M-002 real engines underpinning FE-6/7/8 —
> *then a user checkpoint* before Claude builds any FE-6/7/8 frontend.
> Rationale: frontend consumes the backend contract (never the reverse).
>
> **STATUS 2026-05-16: PAUSED at the checkpoint by user choice ("stop here
> for now").** Sessions 1 (auth) + 2 (hardening) done & verified. FE-6/7/8 and
> M-002 engines NOT started — awaiting the user's direction at the checkpoint
> (FE-6/7/8 contracts are already frozen, so frontend is unblocked whenever
> they choose to proceed).

- **Session 1 — Security + frontend cleanup + docs ✅ COMPLETE & VERIFIED.** Claude: H1,
  M4, L1, L2, L4 (vitest 21/21, build clean). Codex: C1/C2 auth on runs/reports/reviews/
  search + `current_user` dep + authed conftest fixture + 7 test files migrated +
  `test_auth_guard.py` 401 test. Verified: offline pytest 81 passed / 4 skipped, contract
  40/40; live smoke — public `/lookup`+`/primer`→200, protected `/runs`+`/reports/upload`
  →401. AuthN only; object-level authz deferred (no owner column — `# TODO`, Session 6+).
- **Session 2 — Backend correctness/invariant batch ✅ COMPLETE & VERIFIED.**
  H2 (spliceai live_stub), H3 (no fabricated consequence), M1 (atomic upsert),
  M2 (pubmed `raw={}`), M3 (safe `load_fixture`), L3 (doc). Codex job
  `task-mp848are-gq0blv`. Verified: offline pytest **86 passed / 4 skipped**,
  contract 40/40, `test_tool_invariants.py` 5 passed; live smoke — all evidence
  `live`, `genomic_hg38=1-68444869-T-C`, spliceai stays `live` on resolved path,
  10 publications.
- **Session 3 — Workbench FE-6** (Claude): Primer + CRISPR panels (BE-4 stub data exists).
- **Session 4 — Workbench FE-7** (Claude): Alignment + Comparator.
- **Session 5 — Workbench FE-8** (Claude ‖ small Codex): tool-aware AskEamos pill
  (ships against mock chat; live `/api/v1/chat` is M-002).
- **Session 6+ — M-002 follow-ups** (post-feature): real Primer3 / CRISPOR /
  Needleman–Wunsch + biopython AB1, live `/api/v1/chat`, live data feeds for the 6
  report modules, object-level authz + owner/tenant column, live-smoke CI.

---

## Future phases

- **Mouse mm39 lookup** — same architecture; DB stack swap (MGI, IMPC, VEP-mouse, dbSNP). Hidden from v2 UI.
- **Layer 2 v2 redesign** — patient report flow onto v2 design system. Out of scope this cycle.
- **Layer 3** — internal; not discussed publicly.

---

## Known blockers / hygiene

| Item | Detail |
| ---- | ------ |
| ~~Live API verification~~ | ✅ RESOLVED 2026-05-16 — variant-search engine live-verified against real APIs. |
| Uncommitted work | ~53+ working-tree changes (variant-search engine, workbench fixes, Session-1 hardening) on `master`, nothing committed. Recommended commit grouping is in the handoff file. |
| ~~Codex dispatch reliability~~ | **Historical / plugin-specific (2026-05-17).** The stale-`state.json` phantom-"running" issue was a property of the shared *plugin-mediated* Codex runtime. Direct Codex app sessions have verified full workspace + outbound-network access and don't use that runtime; cross-agent coordination is now via `agent_handoff/`. Plugin-path reaping notes retained in memory `reference-codex-parallel-workflow` for the historical flow. |
| GitHub PAT rotation | Legacy note (Session 4 token once visible in chat). Rotate + update `.env` before any push if still valid. |

---

## Architecture reference

```
Layer 1 lookup:   POST /api/v1/lookup              (public, no auth — by design)
Layer 1 chat:     POST /api/v1/chat (+ /stream)    (lookup/Workbench scoped, public)
Workbench tools:  POST /api/v1/primer|/crispr|/align (public, stub responses)
Layer 2 reports:  POST /api/v1/reports/upload → /api/v1/runs   (AUTH REQUIRED — Session 1)
Layer 2 reviews/search/run-chat:  /api/v1/reviews | /search | /runs/{id}/chat (AUTH REQUIRED — Session 1)

Default mode:     USE_REAL_APIS=false (fixture JSON) | LLM_PROVIDER=mock
                  USE_REAL_APIS=true  → live external calls (variant-search verified)
Database:         SQLite (file-backed); variant cache table active when use_real_apis=true
Dev server:       npm run dev → http://localhost:5173 ; backend uvicorn :8000
```
