# Eamos — Roadmap

> ⚠ **Freshness note (2026-06-06):** the header below and the "nothing is
> committed" lines are STALE — most v2 work is committed + live on
> `origin/main` `8a571eb`. The Workbench FE table (FE-6/7/8) was corrected this
> date against the real tree. Treat dated status cells as point-in-time; the
> working tree + commits are ground truth.
>
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

## Backend data live-wire roadmap

The site can move to full live data in staged backend-owned phases, not by
opening every source at once.

Current status (2026-06-01): phases 1-3 are partially implemented in the local
backend tree and dev Supabase, and the post-reference source reader-proof gate
is now closed locally. The dev Supabase project has private `eamos_private`
cache/source/job tables, RLS, service-role-only DML, advisor checks, and
backend hybrid cache wrappers for variant reports, source cache, and protein
annotation. Approved Tier 1/2/3 source downloads are locally staged, static
source readiness is `10/10`, and capped Linux native proof returned `10 proven /
0 native pending` for dbSNP, ClinVar, RepeatMasker, phyloP, hg38, MANE,
GENCODE, MONDO, HPO, ClinGen, and GenCC. The private source bucket now contains
the large dbSNP and phyloP source assets plus checksum manifests, uploaded via
hardened backend S3 multipart tooling after the 50 GiB Storage limit increase;
remote sizes match local staged files. The code still must be
committed/pushed and the Render backend must be redeployed with coordinated
private Supabase/Postgres and source-asset runtime materialization before web
searches can use the shared cache and local source reads.

1. **Supabase perimeter first:** private source metadata/status/cache schemas,
   RLS enabled, no broad anon/authenticated grants, server-only credentials,
   and advisor/policy checks.
2. **Small non-commercial imports:** Mondo, HPO, ClinGen gene validity, and
   GenCC imported through backend jobs with source version, checksum, row-count,
   provenance, and backend API smoke tests.
3. **Private large-asset storage:** immutable Supabase Storage objects with
   checksum manifests, no public bucket listing or raw genomic object reads,
   and backend local-cache verification.
4. **Bounded local-source runtime reads:** enable request-time dbSNP/ClinVar/
   RepeatMasker/phyloP/reference reads only after cache/materialization,
   timeouts, rate limits, stale/fallback behavior, and live smoke tests pass.
5. **Licensed/pro-tier sources last:** InterVar/ANNOVAR/OMIM and restricted
   predictors (SpliceAI/CADD/REVEL/PrimateAI-3D/raw dbNSFP) require commercial
   rights, product-tier gates, `licensed_enabled` policy rows, and leak tests
   proving public/free payloads cannot expose restricted fields.

Unsafe defaults: direct frontend SQL over source tables, public genomic buckets,
startup downloads on Render, unrestricted storage uploads, and request-time
restricted predictor or InterVar/OMIM use before the gates above.

---

## Protein Annotation Roadmap

The Workbench protein view needs a local/offline protein-annotation track before
it can match UniProt/Pfam-style references safely.

1. **Terms recorded:** UniProtKB is CC BY 4.0, InterPro/Pfam downloadable data
   is CC0, InterProScan core is Apache licensed, and HMMER is BSD 3-clause.
   Core commercial/local use is feasible with attribution, citation,
   retained notices, checksum/version manifests, and no endorsement claims.
2. **Core bundle staged locally:** ignored downloads are staged under
   `app/backend/data/bio_assets/protein_annotation/downloads/` for
   Swiss-Prot, Pfam-A HMM/metadata, HMMER source, and InterProScan source.
   They are not committed or public; Pfam extraction/pressing is now a
   backend prep step, but it has not been run on Render.
3. **Local annotation engine:** annotate user protein sequences by translating
   coding DNA to protein and running InterProScan standalone, or HMMER
   `hmmscan` against a local Pfam-A bundle, in a bounded backend worker with
   `--no-matches-api` or a local match lookup service.
4. **Reviewed static mirrors:** mirror only approved, release-pinned UniProtKB
   reviewed/Swiss-Prot and InterPro/Pfam data with source version, checksum,
   license/attribution text, and release metadata.
5. **ProteinDomainTrack contract:** feed protein-coordinate domain/site ranges,
   Pfam/InterPro accessions, labels, scores, and provenance into the Workbench
   protein track. Ensembl translation overlap remains a fallback, not the rich
   source of record.

Still gated: live UniProt/InterPro/Pfam API dependency, startup downloads,
Render env/deploy mutation, external protein-asset materialization, and
optional InterProScan licensed apps (`SignalP`, `Phobius`, `DeepTMHMM`) until
separate provider licenses and leak tests are recorded.

### Eamos Protein Annotation Super Tool

This is the proprietary Eamos layer built on top of upstream licensed/open data
and tools. Eamos can own the worker orchestration, parsers, normalized schema,
cache, provenance model, UI contract, and live-wire policy. Eamos does not
relicense UniProtKB, Pfam/InterPro, HMMER, or InterProScan themselves.

Current implementation status (2026-05-31): the first local/offline backend
slice is implemented and verified. It includes asset preflight,
`ProteinDomainTrack`, HMMER/Pfam `domtblout` parsing, UniProtKB/Swiss-Prot
flatfile feature parsing, fail-closed runtime behavior, sequence-hash caching,
Workbench/report cache hydration hooks, and private Supabase metadata/cache
migration scaffolding. Follow-up runtime-prep work added Linux/Render HMMER
packaging plus `Pfam-A.hmm.gz` extraction and `hmmpress`; SG one-off proof now
confirms `hmmscan`/`hmmpress` are present in the image. The Pfam gz bundle is
verified in private Supabase Storage and a backend-only materialization CLI can
download, checksum, prep, and PCARE-smoke it from service-role credentials.
Render one-off proof on `4b17ce4` now confirms the full private Pfam
materialize -> extract -> `hmmpress` -> PCARE -> real ABCA4 fixture CDS smoke
path; ABCA4 is loaded from the committed transcript-model fixture
(`NM_000350.3`, `ENSP00000359245`, CDS `6822`, translated protein length
`2273`) and produced `38` Pfam features. The actual web-service provider-cache
ready state still requires persistent service-instance materialization through
Render Shell, a persistent disk, or an approved startup/runtime materialization
design plus coordinated Render env enablement. The renderer contract
intentionally separates source label, compact abbreviation, and functional
legend description so gene/protein-specific biology can be shown without
falsifying upstream provenance.

1. **Asset preflight:** verify staged Swiss-Prot, Pfam-A, HMMER, and
   InterProScan files by expected size/hash and report usable/missing status.
2. **ProteinDomainTrack contract:** define a backend contract for domains,
   sites, motifs, accession IDs, AA ranges, scores/e-values, release metadata,
   checksum provenance, and fail-closed states.
3. **Lean local worker:** translate coding DNA/protein input, run a configured
   local HMMER/Pfam interface, parse `domtblout`, normalize AA-coordinate
   features, and cache by sequence hash plus Pfam/HMMER release.
4. **Fail-closed runtime gate:** expose no live API fallback; if `hmmscan`,
   Pfam indexes, or provenance are missing, return explicit unavailable states
   rather than external calls or fabricated domains.
5. **Workbench/report read path:** feed cached local domain/site features into
   Workbench and report protein tracks with UniProt/Pfam-style provenance.
6. **Backend live wiring:** after local preflight, parser, cache, and leak
   tests pass, add private Supabase metadata/cache tables for source versions,
   checksums, jobs, and annotation results; keep frontend direct SQL and public
   buckets blocked.

---

## Workbench v1 (active)

Source: `Eamos Workbench v1.html` + `Workbench/*.{js,css}`. Plan: `plans/v2-frontend.md`.

| ID | Milestone | Status |
| -- | --------- | ------ |
| FE-4 | Workbench shell — layout chrome, tool state, context strip | ✅ Done |
| FE-5 | Sequence Viewer + click-to-edit — codon table, tracks, popover, scratchpad | ✅ Done |
| FE-6 | Primer + CRISPR panels — segmented mode tabs, output tables, HDR ssODN | ✅ Done + mock-wired (Primer **and** CRISPR; corrected 2026-06-06 — was stale "Pending"). Live engines flag-gated behind `use_real_apis`. |
| FE-7 | Alignment + Comparator — Canvas chromatogram, pairwise, 2–3 variant grid | 🟡 Alignment done + mock-wired; **Comparator NOT built** (ghost tool: `tools.ts` has meta but no component, absent from `TOOL_ORDER`). Corrected 2026-06-06. |
| FE-8 | AskEamos pill (tool-aware) — floating panel, per-tool chips, persistent | ⏳ PARKED — pill not mounted (orphaned CSS only); LLM key unfunded → "COMING SOON". |
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
