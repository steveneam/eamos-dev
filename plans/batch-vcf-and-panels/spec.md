# Spec — Batch VCF Lookup + Clinical Gene Panels

> **Status:** authored 2026-06-03 · Claude (FE). **§8 contract ratified by Codex (BE) 2026-06-04**
> with refinements folded in (§8). Steven decisions §10 captured. Two-layer panel design — Codex concurs.
> **Slug:** `batch-vcf-and-panels` · supersedes the deferred "`/compare` Slice 2".
> **How to read:** §2 is the analytical core (why the naive build fails). §4 is the
> architecture. §5–§7 are the three features. §8 is the FE↔BE contract. §9 phases it.
> §10 is what Steven/Codex must decide before code.

---

## 1. Problem & vision

Today Eamos answers **one variant → one evidence report** (`/report`, ~9s live lookup).
This session shipped Slice 1 of multi-variant: drop a file on the search bar → parse
→ `/compare` lists the variants, each linking to its own report. No live data on that
list yet.

Steven's target:

1. **Clinicians drop their *larger* VCF files and get search results for all variants** —
   batch annotation, not one-at-a-time.
2. **Custom + preloaded clinical filters** — apply a gene panel (e.g. inherited retinal
   disease, cardiac) so results are scoped to the genes that matter for the phenotype.

These are **not two features** — they are one pipeline. See §2.

---

## 2. The central constraint (read this first)

A single lookup is **~8s warm, ~10.7s cold** (measured live on `eamos-dev.vercel.app`,
2026-06-03). Run serially over a real VCF:

| VCF kind | ~Variant count | Serial @ 9s | Verdict |
| -------- | -------------- | ----------- | ------- |
| Targeted panel VCF | 50–300 | 7–45 min | painful |
| Clinical exome (coding) | 20k–50k | **2–6 days** | impossible |
| Whole genome | 4–5M | **months** | absurd |

So "drop a large VCF, get all results" is **infeasible as a synchronous, unfiltered,
per-variant loop.** Three levers, in priority order:

1. **Reduce N *before* lookup (the big one).** A clinician dropping a genome does not want
   5M annotations — they want the variants in the genes relevant to the patient's
   phenotype. **A gene panel intersected with the VCF collapses N by 2–4 orders of
   magnitude** (genome ∩ IRD-panel ≈ tens–low-hundreds of variants). This is why the
   panel feature is the *enabling mechanism* for large-VCF, not a cosmetic filter.
   Quality (`FILTER=PASS`), region, and allele-frequency filters stack on top.

2. **Async + parallel + cached + deduped.** Batch is a *job*, not a request: submit →
   workers process a concurrency-limited pool → dedup identical variants → cache hits
   across jobs (ClinVar/gnomAD recur heavily in cohorts) → stream progress → results page.

3. **Local-first assets (Codex, in-flight).** Once dbSNP/phyloP/ClinVar are local disk
   assets (the SG rollout), per-variant cost drops from a network fan-out toward a
   disk read — the difference between "minutes" and "tens of seconds" for a filtered
   panel result. **Large-VCF feasibility is gated on this rollout; small batches work
   on the current backend.**

**Design consequence:** the canonical flow is **Drop VCF → Filter (panel first) →
Confirm scope (N + est. time) → Async job → Results dashboard.** A "whole-VCF, no panel"
path exists but is hard-capped and tier-gated (§5.3).

---

## 3. Background — VCF essentials we ingest

From the VCF spec ([CD Genomics](https://www.cd-genomics.com/blog/vcf-structure-tools-clinical-applications.html))
and our current parser (`app/web/lib/variant-file.ts`):

- **Header:** `##` meta lines (fileformat, reference, contig, INFO/FORMAT defs); one `#CHROM…`
  column header.
- **8 fixed columns:** `CHROM POS ID REF ALT QUAL FILTER INFO`. `POS` is 1-based.
  `ALT` may be **multi-allelic** (`A,T`). `FILTER` is `PASS` or failed-filter names.
  `INFO` carries `AF`, `DP`, `AD`, and (if the VCF was annotated by VEP/SnpEff/ANNOVAR)
  the **gene symbol / consequence** — which we can opportunistically read but must not
  *require* (many clinical VCFs are un-annotated).
- **Genotype block (optional):** a `FORMAT` column + one column per sample (`GT:AD:DP…`).
  Multi-sample VCFs (trios, cohorts) exist; v1 treats each VCF as one specimen and
  ignores per-sample genotype splitting (call it out as a future axis).
- **What we need per variant for a lookup:** a normalised hg38 key
  `CHROM-POS-REF-ALT` (we already build this; we strip `chr`). Gene/HGVS resolution
  happens server-side in the existing lookup.

**Key technical fact for panels:** raw VCF variants are *positional*, not gene-labelled.
Filtering a VCF by a gene panel therefore = **genomic-interval intersection** of each
variant's `CHROM:POS` against the panel genes' hg38 coordinate ranges (a BED-like map).
This needs a gene→interval resource (we have transcript/gene models server-side; see §6.4).
If the INFO field already carries an annotated gene symbol we can fast-path on it, but the
interval intersection is the correctness floor.

---

## 4. Architecture overview

```
            ┌─────────── FE (Claude / app/web) ───────────┐   ┌──── BE (Codex / app/backend) ────┐
 drop VCF → │ 1. parse + validate (variant-file.ts v2)     │   │                                  │
            │ 2. pick filters: PANEL + PASS/region/AF      │   │  /panels  (catalog + resolve)    │
            │ 3. scope gate: shows N, est. time, quota     │──▶│  /batch   (submit job)           │
            │ 4. progress (SSE/poll)                       │◀──│  job engine: filter→dedup→pool→  │
            │ 5. results dashboard (table + summaries)     │   │   cache→per-variant lookup()     │
            │ 6. export cohort                             │◀──│  /batch/{id} (status + results)  │
            └─────────────────────────────────────────────┘   └──────────────────────────────────┘
```

- **Filtering can run client-side for small VCFs** (we already parse in the browser) but
  **must run server-side for large VCFs** (don't ship a 200MB genome VCF to the browser).
  v1 decision: files ≤ ~5MB / ≤ ~2k variant lines parse client-side; larger files upload
  raw to the backend which parses + filters server-side. (§10 D-3.)
- **The batch job engine is Codex's lane.** FE owns upload UX, the scope gate, progress,
  the results dashboard, the panel picker. This spec proposes the contract; Codex owns
  the job model, concurrency, caching, persistence, and rate-limit interaction.

---

## 5. Feature A — Batch VCF ingestion & async lookup

### 5.1 Upload & parse (FE — extends `variant-file.ts`)
- Current parser caps at 50 variants and is sync/in-memory. v2:
  - Raise the client-parse cap (e.g. 2k) for the small-file path; above the size/line
    threshold, **stream the raw file to `POST /api/v1/batch` and let the backend parse**.
  - Keep VCF + CSV/TSV/plain-list support (already built + browser-verified this session).
  - Surface parse diagnostics: lines parsed, skipped (malformed/headers), multi-allelic
    sites split count, deduped count.

### 5.2 Filtering layer
Applied **before** any lookup. Order: panel → FILTER → region → AF.
- **Panel** (the big lever, §6): keep only variants whose locus ∈ panel gene intervals.
- **Quality:** `FILTER=PASS` only (default on, toggle).
- **Region:** optional `CHROM`/range include-list.
- **Allele frequency:** drop common variants (`INFO/AF` or post-lookup gnomAD AF >
  threshold, default e.g. 5% — clinically these are rarely the answer). Note: pre-lookup
  AF only works if INFO carries it; otherwise this is a *post-lookup* filter on the
  results table.

### 5.3 Scope-confirmation gate (FE) — the guardrail
Before a job runs, show: **N variants after filters · estimated time · quota/tier impact**,
and require explicit confirm. This is where we stop a clinician from accidentally
launching a 50k-variant job.
- **Tier caps (align to existing pricing — already product-decided):**
  Free = no batch (single lookups only). Pro = "VCF upload (batch variants)" up to cap_P.
  Max = "Bulk VCF uploads" up to cap_M. (Exact caps = §10 D-2.)
- **Large-VCF rule (Steven, 2026-06-03 — tier-split):**
  - **Pro:** above the unfiltered cap, a panel (or region/AF filter) is **required** to
    proceed — *apply the filter first*. This is the default path and the product nudge
    that keeps every job tractable AND clinically meaningful.
  - **Max:** unfiltered **whole-VCF** runs are allowed (hard-capped at cap_M, top-N by
    quality when over).
  - **Enterprise / special pricing agreement:** dedicated, uncapped whole-VCF runs — as
    the business expands or per a specific client agreement. (Infra: a dedicated/queued
    worker lane, not the shared pool.)

### 5.4 Async batch job engine (BE / Codex — contract in §8)
- `POST /api/v1/batch` → creates a job (`status=queued`), returns `job_id`. Body carries
  either the parsed variant list (small path) or a file upload + filter spec (large path).
- Engine: **filter → normalise/dedup → concurrency-limited worker pool calling the
  existing `lookup_service.lookup()` per unique variant → cache by variant key.**
  Reuse the eager/lazy split (`LOOKUP_EAGER_RESPONSE_EXCLUDE`) — batch only needs the
  *summary-level* fields (classification, gnomAD AF, predictor ensemble, ClinVar verdict),
  not the full per-variant `report_payload` (publications/deep-dive/expert-panel excluded).
  Full payload is fetched lazily when the user opens a single row's report.
- Progress: SSE stream or poll `GET /api/v1/batch/{id}` (`done/total`, per-variant states).
- Persistence: results stored (Supabase) keyed to the user so they survive reload and
  appear in account history.
- Rate-limit interaction: batch must **not** trip the per-IP `RATE_LIMIT_LOOKUP` limiter
  (§ `app/backend/app/core/rate_limit.py`) — the engine calls `lookup_service` *in-process*,
  below the HTTP rate-limit layer. New batch-scope limits gate *job submission*, not the
  internal per-variant calls.

### 5.5 Results dashboard (FE) — the deferred Slice 2, now cohort-scale
Two registers on one page:

**(a) Per-variant table** (live key metrics — the thing Slice 1 deferred):
gene · variant · ClinVar verdict · gnomAD AF · predictor ensemble · ACMG → classification
badge · "Open report →". Sortable/filterable; **P/LP variants pinned to top** (the
actionable ones). Post-lookup AF filter lives here.

**(b) Cohort summaries** (VCFshiny-inspired — the good half of that repo, ideas only,
no R/code reuse):
- classification distribution (P / LP / VUS / LB / B) — the headline.
- per-gene variant counts (which panel genes are hit).
- variant-type breakdown (SNV / indel) + SNV substitution spectrum (6-class).
- indel length distribution.
- **panel coverage**: which panel genes had ≥1 variant vs none.

### 5.6 Export
Extend the report-export built this session (`app/web/lib/report-export.ts`) to a
**cohort export**: one TSV/`.xlsx`-friendly table (one row per variant) + a summary
sheet. Reuses the existing per-section serializers.

---

## 6. Feature B — Clinical gene panels

### 6.1 Panel data model
```
Panel {
  id, name, slug,
  source: "panelapp-au" | "panelapp-gel" | "clingen-gencc" | "custom",
  version, provenance_url,
  genes: [{ symbol, hgnc_id, confidence: "green"|"amber"|"red"|null,
            moi?, disease?, mondo_id? }],
  intervals_ref: "hg38",     // resolved gene→coordinate map for VCF intersection
}
```

### 6.2 Panel sources — a two-layer model (Steven decision, 2026-06-03)
Decided as a layered architecture rather than a single source, driven by the licensing
read (§6.2.1):

**Layer 1 — commercial-safe core engine (always on, offline): local ClinGen + GenCC +
MONDO + HGNC.** All open-licence, all already on disk
(`clingen_gene_validity.csv`, `gencc-download.csv`, `mondo.json`, HGNC ids in the ClinGen
CSV). Gives gene→disease→MONDO→MOI→validity (Definitive/Strong/…). **This powers custom
panels and the natural-language builder (§6.3) with zero licensing exposure and no network
dependency** — and is what we build mock-first against.

**Layer 2 — recognisable named-panel overlay: PanelApp Australia.** AU-aligned (Eamos has
ABN + `eamos.com.au`; memory `project_domain`). Curated, **versioned**, green/amber/red
diagnostic panels per indication, with a public API explicitly intended for variant-curation
platform integration. Used for the clinician-recognisable preloaded panels (the "IRD panel"
they already trust), shown with version + provenance.

- Launch set (PanelApp AU green genes, versioned + provenance-linked): **Inherited retinal
  disease**, **Cardiac** (cardiomyopathy / arrhythmia), + a small starter spread
  (e.g. hereditary cancer, epilepsy) — final list = §10 D-1.

#### 6.2.1 Licensing notes (verify before commercial launch — §10 D-1)
- **PanelApp software** = Apache 2.0; **panel data** = publicly downloadable, reuse
  (incl. commercial) permitted, **but**: (a) Genomics England puts an **IP-verification
  responsibility on the reuser** and disclaims liability; (b) **OMIM data must be licensed
  separately** (OMIM is *not* free for commercial use) → **do not redistribute OMIM-derived
  content; use MONDO** (open, CC BY) for disease IDs in panels.
- **Mitigations baked into this design:** Layer-1 core is fully open (ClinGen CC0-ish,
  GenCC open, MONDO CC BY, HGNC open); PanelApp is an *overlay* shown with attribution +
  version, not silently re-served; OMIM is avoided in favour of MONDO throughout.
- **Honest gap:** the above is read from public summaries, not the signed ToU. Steven /
  legal to confirm the PanelApp Australia terms (esp. the OMIM carve-out) before paid launch.
  None of this blocks dev — Layer 1 is unambiguously safe to build on now.

### 6.3 Custom panels
User flows:
- **Pick a disease** → auto-resolve genes from ClinGen/GenCC (e.g. "all Definitive/Strong
  genes for MONDO:retinal dystrophy"). Show validity + MOI per gene.
- **Paste/type gene symbols** → validate against HGNC (we have HGNC ids), flag unknowns.
- **Upload a gene list** (txt/csv).
- **Describe it in natural language** → §6.3.1 (Steven's chatbot idea).
- **Save** named panels to the account (Supabase), **clone/edit**, (later) share.
- Show gene count + (later) the panel's genomic footprint.

#### 6.3.1 Natural-language panel builder (Steven, 2026-06-03)
"A client types what they want into the chatbot and we build a custom gene panel on the
spot." Strong feature — it's the highest-value, lowest-cost first use of AskEamos chat.

**Resolution pipeline** (the LLM only does step 1; steps 2–4 are our deterministic engine):
1. **NL → structured intent** (LLM, or a rules parser in the no-LLM tier): extract disease
   term(s) + constraints (validity threshold, MOI, gene-count target, include/exclude genes).
   e.g. *"early-onset retinal dystrophy, definitive genes only"* →
   `{ disease: "retinal dystrophy", onset: "early", min_validity: "definitive" }`.
2. **Disease → MONDO id** — fuzzy match against `mondo.json` synonyms.
3. **MONDO → genes** — query local ClinGen/GenCC (Layer 1), filtered by validity/MOI.
4. **Draft panel returned** (genes + per-gene validity/MOI + provenance) for the user to
   review/edit/save. Conversational edits ("add RPGR, drop the amber ones") loop back via
   the chat.

**Two-tier rollout (respects the AskEamos park — memory `feedback_askeamos_parked`):**
- **Tier A — ships now, no LLM:** a structured builder that does steps 2–4 from a typed
  disease + dropdown constraints. ~80% of the value, zero token cost, no key needed.
- **Tier B — conversational, on chat-funding:** the LLM front-end (step 1 + edit loop).
  Panel-building is a **bounded, few-hundred-token** request — a far cheaper, more
  defensible first justification for funding the chat than an open-ended assistant. Flag
  this to Steven as the concrete chat ROI case. Until funded: keep the conversational
  entry **COMING SOON**, ship Tier A.

### 6.4 Panel application semantics (the interval-intersection requirement)
- VCF variants are positional → filtering needs **panel gene hg38 intervals**. Resolve
  panel symbols → coordinate ranges **interval-first from MANE Select GFF3 + HGNC
  normalisation → an hg38 BED** (Codex, 2026-06-04). INFO gene symbols are only a fast
  path, never the correctness floor. (`app/backend/app/services/transcript_model.py` /
  gene-viewer assets can supply coordinates.) **This BED resource is a prerequisite for
  panel filtering and is a Codex/BE deliverable.**
- Fast-path: if a variant's INFO carries an annotated gene symbol matching the panel,
  accept without interval lookup (optimisation, not correctness floor).
- Edge: variants in a gene's introns/UTRs/flanks — default to gene body ± a configurable
  flank (e.g. ±20bp for splice region); document the boundary choice.

### 6.5 UI
- Panel picker lives **in the scope gate** (§5.3): "Apply a panel" → searchable list of
  preloaded panels + "Build custom" + the user's saved panels. Selecting one immediately
  re-computes N (post-filter) and the time estimate.
- On the results dashboard, the active panel + version is shown as provenance ("IRD panel
  · PanelApp AU v4.2 · 87 green genes").

---

## 7. Feature C — Mock / synthetic VCF generation for testing

You asked how to generate mock VCFs to test the pipeline. Survey + recommendation:

**Surveyed** ([search results](https://www.biostars.org/p/9571806/), refs below):
- **GeneBreaker** — gene-based **Mendelian rare-disease** variant simulation; injects known
  pathogenic / novel gene-disrupting variants into a gene. *Closest in spirit to our
  clinical use* — worth borrowing its approach (inject known-truth pathogenic into target
  genes).
- **vcfsim**, **HaploDynamics** — population-genetics VCF simulation (ploidy, LD, allele
  freqs). Overkill / wrong domain for us.
- **DWGSIM** (the repo discussed earlier) — read simulator (FASTQ), *upstream of where we
  start*. **Out of scope.**

**Recommendation: build a tiny in-repo generator, don't add a dependency.**
`app/backend/scripts/make_test_vcf.py` — emits valid hg38 VCFs from a **seed set of
known-truth variants we already hold** (RPE65/USH2A/ABCA4 known variants + sampled entries
from local ClinVar assets), because we want *deterministic, panel-aware, known-truth*
fixtures, which the population simulators don't give and which a ~150-line script does:
- flags: `--n`, `--panel <slug>` (restrict to panel genes so panel-filter tests are
  meaningful), `--mix p/lp/vus/lb/b` (classification spread), `--multiallelic`,
  `--with-genotypes` (FORMAT + sample columns), `--chr-prefix`, `--malformed` (edge-case
  lines for parser robustness), `--seed` (deterministic).
- emits a **truth manifest** alongside (expected gene/classification per variant) so
  pipeline tests assert outcomes.
- small fixtures committed under `app/backend/tests/fixtures/vcf/`; large fixtures
  generated on-the-fly in tests (never commit big VCFs).
- mirror a minimal generator for FE parser unit tests (`app/web` Vitest) covering the
  edge cases I hand-made during this session's browser verify (chr prefix, header skip,
  multi-allelic first-ALT, CSV vs VCF detection).

---

## 8. Data contracts (FE ↔ BE) — **ratified by Codex 2026-06-04**

> Per `plans/README.md`: backend lands schema first (`app/backend/app/schemas/*.py`),
> FE mirrors in `app/web/lib/backend.ts`; `test_frontend_contract.py` is the canary.
> **Codex refinements folded in (2026-06-04):** (1) upload negotiation split from job
> creation; (2) `GET /batch/{id}` paged from day one; (3) SSE only after polling works.

```ts
// Panels
GET  /api/v1/panels                        -> { panels: PanelSummary[] }
GET  /api/v1/panels/{slug}                 -> Panel            // full gene list
POST /api/v1/panels/resolve                 // custom: disease|symbols|upload -> Panel
  body: { disease_mondo?: string; symbols?: string[]; min_validity?: "definitive"|"strong" }

// Batch — upload negotiation split from job creation (Codex, 2026-06-04)
POST /api/v1/batch/uploads                  -> { upload_ref }  // large path: negotiate raw-VCF upload first
POST /api/v1/batch                          -> { job_id, n_input, n_after_filters, est_seconds }
  body: { variants?: ParsedVariant[];      // small path (inline list)
          upload_ref?: string;             // large path (from /batch/uploads)
          filters: { panel_slug?: string; pass_only?: bool; regions?: string[]; max_af?: number } }
GET  /api/v1/batch/{job_id}                 -> BatchJob        // status + results, PAGED from day one
GET  /api/v1/batch/{job_id}/stream         -> SSE progress    // optional, AFTER polling works
// BatchJob.results[i]: { variant_key, gene, hgvs_c, hgvs_p, clinvar_verdict,
//                        gnomad_af, predictor_ensemble, acmg_classification, report_href }
```

FE adds: `app/web/lib/batch.ts` (job client), `app/web/lib/panels.ts`, extends
`variant-file.ts`. New routes: `app/web/app/compare/` evolves into the results dashboard
(or a new `app/web/app/batch/[jobId]/`).

---

## 9. Phasing (shippable slices)

| Phase | What | Owner | Depends on |
| ----- | ---- | ----- | ---------- |
| **P0** | This spec + Steven decisions (§10) + Codex contract ratification | Claude+Codex | — |
| **P1** | Mock VCF generator + parser hardening + truth fixtures | Codex (gen) / Claude (FE tests) | — |
| **P2** | Panels backend: catalog from ClinGen/GenCC (offline), `/panels` endpoints, gene-interval resource | Codex | — |
| **P3** | Panel picker UI + scope gate (client-side filter on small VCFs, mock job) | Claude | P2 |
| **P4** | Batch job engine: `/batch` async, dedup, cache, progress | Codex | P1 |
| **P5** | Results dashboard: live per-variant table + cohort summaries + cohort export | Claude | P4 |
| **P6** | PanelApp Australia integration (preloaded curated panels, versioned) | Codex | P2 |
| **P7** | Large-VCF server-side parse/filter + custom-panel save (Supabase) | Codex+Claude | P4, local-asset rollout |

P3 can demo end-to-end against a **mock job** before P4 lands (mock-first, per our idle
protocol). P1+P2+P3 are shippable value without the async engine (small panel-filtered
VCFs run as sequential single lookups behind a progress bar).

---

## 10. Open decisions (Steven + Codex)

- **D-1 (Steven): panel source — DECIDED 2026-06-03** = two-layer (local
  ClinGen/GenCC/MONDO/HGNC commercial-safe core + PanelApp Australia recognisable named-panel
  overlay; §6.2). **Still open:** (a) legal/ToU confirm of PanelApp AU + the OMIM carve-out
  before paid launch; (b) the exact launch panel set (IRD + cardiac + ?).
- **D-2 (Steven): large-VCF tiering — DECIDED 2026-06-03** = Pro requires a filter first;
  Max allows capped whole-VCF; enterprise/special-agreement gets dedicated runs (§5.3).
  **Still open (parametric):** the actual numbers — Pro `cap_P` (variants/VCF), Max `cap_M`
  (bulk = ? files / ? variants), enterprise lane sizing.
- **D-6 (Steven): chat-funding for the conversational panel builder.** Tier A (deterministic,
  no LLM) ships regardless. Tier B (NL chatbot, §6.3.1) needs the AskEamos chat funded — a
  bounded, cheap use case. Go/no-go on funding the key for *this* use, even if the open-ended
  assistant stays parked?
- **D-3 (Codex): client vs server parse threshold** + upload mechanism for large files
  (file size / line-count cutoff; raw-VCF upload endpoint + storage).
- **D-4 (Codex): batch concurrency + caching model** and how hard it leans on the
  local-first asset rollout (P7 gate). What's a safe pool size on SG Standard (2GB)?
- **D-5 (Steven/Codex): genotype / multi-sample VCFs** — v1 treats one VCF = one specimen
  (ignore per-sample GT). Confirm that's acceptable for launch.

---

## 11. Non-goals (v1)

- No read alignment / variant calling (we ingest *called* variants; DWGSIM-class tools are
  out of scope — Eamos starts at the VCF, not at FASTQ).
- No per-sample genotype splitting / trio analysis (future axis).
- No structural variants / CNVs (SNV + small indel only).
- No liftover (assume hg38; flag/refuse hg19 in v1 with a clear message).
- No panel *sharing* between users in v1 (save/clone only).

---

## 12. References
- VCF structure/tools/clinical — [CD Genomics](https://www.cd-genomics.com/blog/vcf-structure-tools-clinical-applications.html)
- Mock VCF: [GeneBreaker](https://pmc.ncbi.nlm.nih.gov/articles/PMC8247879/) ·
  [vcfsim](https://www.biorxiv.org/content/10.1101/2025.01.29.635540.full.pdf) ·
  [realistic VCF in Python (biostars)](https://www.biostars.org/p/9571806/) ·
  [Learning the VCF format (Dave Tang)](http://davetang.github.io/learning_vcf_file/)
- Panels: [PanelApp Australia](https://www.australiangenomics.org.au/tools-and-resources/panelapp-australia/)
  ([instance](https://panelapp.agha.umccr.org/)) · [Genomics England PanelApp](https://www.genomicsengland.co.uk/panelapp)
  ([open-source announcement](https://www.genomicsengland.co.uk/news/panelapp-software-now-open-source))
  — software Apache 2.0; panel data publicly downloadable; reuser verifies IP + **OMIM licensed
  separately** (use MONDO). Open core: ClinGen Gene-Disease Validity, GenCC, MONDO (CC BY), HGNC.
- VCFshiny (cohort-viz idea source, not integrated): https://github.com/123xiaochen/VCFshiny
- Internal: `app/backend/app/api/routes/lookup.py`, `app/backend/app/services/lookup_service.py`,
  `app/backend/app/core/rate_limit.py`, `app/web/lib/variant-file.ts`,
  `app/backend/data/source_assets/clingen_gene_validity/`, `app/backend/data/source_assets/gencc_download/`
</content>
</invoke>
