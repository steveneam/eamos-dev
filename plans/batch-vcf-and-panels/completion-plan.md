# Batch — Completion Plan (WES-first)

> **Status:** authored 2026-06-17 · Claude. Companion to `spec.md` (the 2026-06-03
> design spec) — does **not** supersede it. This is a *state-of-the-code* audit + the
> phased work to actually finish Batch, scoped to what the current $40/mo infra can carry.
> **Read `spec.md` first** for the product vision; this doc is "what's really built, what's
> missing, and the order to close the gap."
> **Decisions D-A…D-D (§3) need Steven/Codex sign-off before code.**

---

## 0. Scope decision (the framing for everything below)

- **WES + panel/region-filtered targeted VCFs are Eamos/Codex's lane.** They are live user
  uploads arriving at our app at runtime — they can't be anyone else's. Selom owns only the
  *offline reference assets* (panel gene→interval BEDs, local ClinVar/gnomAD, transcript
  geometry); the upstream FASTQ→VCF is the sequencing lab's, never our compute.
- **WGS is deferred.** Unfiltered whole-genome (1 GB+, 4–5M variants) cannot be parsed on a
  2 GB box and its cheap-lookup assets aren't materialized yet (Codex Tier 1 is Supabase-space
  blocked). Interim bridge for genome users: accept a WGS file **only if pre-subset** to a
  panel/region before upload (`bcftools view -R panel.bed`).
- **The real gate is `N-after-filter` + `file-size`, not the WES/WGS label** — you cannot
  detect exome-vs-genome from a VCF; there is no "exome" field. So "WES-only" is implemented
  as a size/variant-count cap, and a *panel-filtered* genome is welcome (small surviving N).

**This plan completes Batch for: panel/region-filtered cohorts, client-parseable, up to a
capped N.** Unfiltered full WES (20–50k) and native WGS are later phases.

---

## 1. Current state — verified in code (2026-06-17)

### Built and genuinely real
- **FE flow is complete (mock-first).** `app/web/components/compare/CompareClient.tsx`: drop
  → stash (`variant-file.ts`) → `ScopeGate` filter chips (panel / PASS / region / AF, live N
  preview) → **Generate** → `createBatch` → poll `getBatchJob` → page results →
  `BatchResultsTable`. Falls back to a mock job + client-side `VariantTable` when offline.
  `/compare` route live (labelled "Batch").
- **FE libs:** `batch.ts` (`createBatch`/`getBatchJob`/`uploadBatch`), `panels.ts` (+
  `panels.mock.ts`), `compare-filters.ts`, `variant-file.ts`.
- **BE VCF parser is solid.** `app/backend/app/services/vcf_ingest.py`: streaming gzip+plain
  decode with a decompressed-size cap, multiallelic split, INFO/gene/AF parsing, first-sample
  GT, `chr` normalization, malformed-row skip-with-warnings, BOM handling.
- **BE batch route wired.** `routes/batch.py`: `POST /uploads` (multipart, content-length
  guard, chunked streamed read, size limit from `settings.max_upload_mb`=20), `POST` (create),
  `GET /{job_id}` (paged). Wired in `main.py` with `coordinate_resolver` active (compact
  c.→genomic index).
- **BE contract complete.** `schemas/batch.py` matches `spec.md` §8, incl. the full
  `BatchVariantState` lifecycle enum and paged `BatchJob`.
- **Mock VCF generator + ~26 backend tests** (`test_batch_api` 9, `test_vcf_ingest` 5,
  `test_panels_api` 5, `test_batch_panel_schemas` 6, `test_project_100_mock_vcf_generator` 1).

### Built but NOT what it appears — the real gaps
1. **No real annotation (THE core gap).** `BatchService.create_job` runs synchronously,
   hardcodes `status="completed"`, and `_result_from_variant` only **passes through VCF INFO**
   (`CLNSIG`→`clinvar_verdict`, INFO `AF`→`gnomad_af`, INFO `HGVS_P`). `predictor_ensemble`
   is always `{}` and `acmg_classification` is always `None`. **It never calls
   `lookup_service`.** For the common *un-annotated* clinical VCF this returns almost nothing —
   Batch does not actually annotate.
2. **No async engine.** No background execution, no `queued→running→completed` transitions,
   no worker pool, no cache. The FE polls a loop the backend satisfies instantly *because it
   did no work*. The state enum + `done/total` exist but are unused.
3. **Panels are a hardcoded stub.** `services/panels.py` ships 4 hand-written panels (IRD,
   cardiomyopathy, hereditary cancer, project-100); no ClinGen/GenCC Layer-1 data;
   disease→MONDO is a 2-value `if`. Warnings literally say "materialized source pending".
4. **No gene→interval BED — the panel-filter correctness floor is missing.**
   `_apply_prelookup_filters` matches `variant.gene` (from INFO) against panel symbols only;
   variants with no gene symbol are *kept-for-lookup*, never intersected. The FE already
   promises "MANE→hg38 interval intersection" (see `EmptyScope` copy) that the backend does
   not do. **Most clinical VCFs carry no INFO gene → the panel filter is effectively
   non-functional for them.**
5. **FE ingest cap = 50 variants.** `variant-file.ts` `MAX_VARIANTS = 50`. Backend allows
   5000, but the FE never sends >50 and never uses `uploadBatch`. So today Batch ingests ≤50
   client-parsed variants inline — below even a small targeted panel VCF.
6. **No persistence.** Jobs live in in-memory TTL registries; reload loses them; no account
   history (spec §5.4 wanted Supabase-backed).
7. **Results table is per-variant only.** `BatchResultsTable.tsx` renders the table + a
   clipboard "copy for spreadsheet". **Missing:** cohort summaries (spec §5.5b — classification
   distribution, per-gene counts, variant-type, panel coverage), P/LP-pinned-to-top, the
   post-lookup AF filter, and a real file export (§5.6).
8. **Parser accuracy gaps:** no genome-build detection (hg19 silently mis-annotated — spec §11
   says refuse hg19), no indel left-align/normalization (needed to match ClinVar/gnomAD), no
   gVCF rejection (`<NON_REF>` rows slip through as junk alts).

---

## 2. The coupling that drives the order

Real annotation (gap 1) **cannot be synchronous** — N×~9s in one request times out. So gaps
1 + 2 are a single piece: an **async background job that calls `lookup_service.lookup()` per
unique variant, with dedup + in-process cache + summary-only extraction**, transitioning
status and emitting `done/total`. The FE already polls for exactly this. Per-variant cost
drops as Codex's local assets land, but the engine **works today over the network** (just
slower) — so it is *not* blocked on Codex. That makes the async engine the first and highest-
value piece to build.

---

## 3. Decisions needed before code (Steven / Codex)

- **D-A — scope cap. DECIDED 2026-06-17 (Steven):** filter-required, cap `N_to_lookup` at
  `BATCH_MAX_VARIANTS = 5000`; raise FE `MAX_VARIANTS` 50 → match. Full unfiltered WES
  (20–50k) is a later phase.
- **D-B — annotation cost path. DECIDED 2026-06-17 (Steven):** build the async engine now,
  wired to `lookup_service`, concurrency **2–3** on the 2 GB/1 CPU box, summary-only payload
  (reuse `LOOKUP_EAGER_RESPONSE_EXCLUDE`). Works over the network today; speeds up
  transparently as local assets materialize. **Not blocked on Codex's Tier-1 materialization.**
- **D-C — interval BED. (default, Codex to time):** Real panel filtering of un-annotated VCFs
  needs MANE GFF→hg38 BED + interval intersection (Codex/offline asset). Until it lands, the
  panel filter only works on INFO-gene VCFs — *document the limitation; the FE already
  half-handles it via the `EmptyScope` "interval pending" copy.* → *Codex: time C2 relative to
  the materialization roadmap.*
- **D-D — persistence. (default):** in-memory for the MVP (zero Supabase footprint — aligns
  with current space pressure); add Supabase persistence + account history in C4, budget-gated.

---

## 4. Phased completion

| Phase | What | Owner | Depends | Verify |
| ----- | ---- | ----- | ------- | ------ |
| **C1** | **Async job engine.** `create_job` enqueues (`status=queued`); background task: filter→dedup→per-unique `lookup_service.lookup()` (summary-only)→cache→status + `done/total`. Map `LookupResponse`→`BatchResult` (clinvar_verdict, gnomad_af, predictor_ensemble, acmg_classification, report_href). Concurrency 2–3. | Codex | — | A job over the project-100 mock VCF returns **real ACMG classifications + predictor ensemble**, not INFO passthrough; `done/total` advances. |
| **C2** | **Gene→interval BED + intersection.** Build MANE→hg38 BED; replace gene-only match in `_apply_prelookup_filters` with interval intersection (gene body ± splice flank). | Codex | offline asset (D-7) | Panel filter keeps the correct variants on a **no-INFO-gene** VCF. |
| **C3** | **FE finish.** Raise `variant-file.ts` cap (50 → ~2000); wire `uploadBatch`→create-with-`upload_ref` for files above the client cap; real progress UI from `done/total`; cohort summaries (§5.5b); P/LP-pinned table + post-lookup AF filter; file export (§5.6). | Claude | C1 | Browser-verify against live backend: progress bar advances, summaries render, export downloads. |
| **C4** | **Persistence + account history** (Supabase). | Codex | budget | Job survives reload; appears in account history. |
| **C5** | **Real panels** — ClinGen/GenCC Layer-1 catalog + PanelApp AU overlay (replaces hardcoded stub). | Codex | offline assets | `/panels` returns curated, versioned, provenance-linked panels. |
| **C6** | **Parser hardening** — build detection (refuse hg19), gVCF reject, indel normalization. | Codex | — | hg19 VCF refused with a clear message; gVCF rejected; normalized keys match ClinVar. |

**Minimum "WES MVP actually usable":** **C1 + C3** (and **C2** if the BED is ready). That makes
Batch annotate a panel-filtered cohort end-to-end with real classifications. C4/C5/C6 are
follow-ons that harden and scale it.

---

## 5. Infra impact (recap)

- **C1's worker pool is the only new RAM/CPU pressure** on the 2 GB/1 CPU box — cap
  concurrency 2–3, summary-only payload, watch live `/report` latency under load.
- **No Supabase footprint until C4** — keeps Batch off the storage that's currently
  constraining Codex's Tier-1 materialization.
- **WGS stays out** (parser cap + missing local assets); pre-subset bridge documented for
  genome users.

---

## 6. Non-goals (unchanged from spec.md §11, reaffirmed)

Unfiltered whole-genome; per-sample GT / trio splitting; SV/CNV; liftover (hg38 only, refuse
hg19); panel sharing between users.
