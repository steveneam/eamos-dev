# v2 Backend Plan — Codex

## Status (2026-05-15)

| ID | Milestone | Status |
| -- | --------- | ------ |
| BE-1 | Franklin archive | ✅ Done — moved to `archive/franklin/`, removed from registry/services/rules/config/env/tests. `rg -n franklin app` returns no matches. |
| BE-2 | Lookup payload v2 | ✅ Done — six new optional fields on `ReportPayload`, RPE65 fixture at `app/backend/app/fixtures/lookup_v2_modules.json`. Lookup route returns the new modules (locus_context with 5 nearby variants + 11 codon cells, etc.). |
| BE-3 | Lookup-scoped chat endpoint | ✅ Done — `POST /api/v1/chat` and `POST /api/v1/chat/stream` live. Mock-mode returns variant-aware response. |
| BE-4 | Workbench engine stubs | ✅ Done — `POST /api/v1/primer | /crispr | /align`. Fixture responses: 3 primer pairs (one ★), 3 gRNAs + ssODN, 4 trace channels × 80 samples. |
| BE-5 | Test sweep | ✅ Done — `test_franklin_removed.py` added; `test_frontend_contract.py` extended for new models. Historical FE-3.5 sync point; superseded by BE-6's synced 40/40 PASS. |
| BE-6 | Report v2 payload mock-fidelity | ✅ Done (2026-05-15, Codex agent `a862070de2d41f104`). Additive schema fields; `lookup_v2_modules.json` rewritten to mirror the 6 frontend SAMPLE constants; `test_frontend_contract.py` extended. Synced with FE-3.6 → 40/40 PASS. |
| BE-7 | Workbench fixture fidelity | ✅ Done (2026-05-15). `primer/crispr/align_rpe65.json` tightened to mock-JS values. Ambiguities surfaced: CRISPR kept 3 guides (mock shows 6 w/ per-guide `recommended`/`cas`, no schema slot); HDR efficiency `12–18%`→midpoint `0.15`; alignment mismatch index 13→14 for internal consistency. |
| BE-8 | Input normalization | ✅ Done & live-verified (2026-05-16). `normalize_variant_query()` (gene/transcript-prefix strip + whitespace collapse, never lowercases HGVS) + `CANONICAL_TRANSCRIPTS`. `test_lookup_normalize.py` green. |
| BE-9 | VariantValidator coords-resolver | ✅ Done & live-verified (2026-05-16). Queries the transcript accession (`NM_000329.3:c.260A>G`, not the gene form) → `genomic_hg38 == 1-68444869-T-C` confirmed live. |
| BE-10 | Strict-genomic plugin loop | ✅ Done & live-verified (2026-05-16). `STRICT_GENOMIC_PLUGINS` 3-phase loop; gnomAD/SpliceAI `live` after resolver in the Claude-run smoke. |
| BE-11 | LitVar2 + Publications accuracy | ✅ Done & live-verified (2026-05-16). PubMed broadened to gene + OR(cdna/protein/rsID) with gene-only fallback → **10 live articles**; LitVar2 queries the ClinVar-derived rsID + parses `pmids`/`pmids_count`; `publications_callout.total_count` falls back to merged-article count when LitVar2 legitimately returns 0. **Zero schema change** (40/40 holds). |
| BE-12 | Search robustness / error contract | ✅ Done & live-verified (2026-05-16). Frozen `warnings` codes; never-raise graceful fallback (`live_fetch_failed:<Exc>`) confirmed live on transient gnomAD/SpliceAI timeouts. |
| BE-13 | Persistent variant cache | ✅ Done & live-verified (2026-05-16). `variant_cache_repo.py`; **upsert guarded on successful genomic resolution** (no cache poisoning); cache-hit + `?refresh=true` bypass confirmed live. |
| DEP-1 | Post-deployment backend contracts | ✅ Done (2026-05-24). Backend-only evidence-submission endpoint and Stripe payment/session/webhook contracts implemented with local persistence and focused/full backend verification. Contract details: `plans/auth-pricing/backend-contracts.md`. |
| DEP-2 | Evidence submission Supabase write-through | ✅ Done (2026-05-24). Added additive `submission_payload jsonb` migration, env-configured Supabase PostgREST write-through for accepted evidence submissions, offline local fallback, and fake-based tests. |
| RP-DEPTH-1 | Publications-over-time timeline | ✅ Done (2026-05-24). Added additive `PublicationLiterature.publication_timeline` with ascending per-year counts plus `total_with_year` / `total_without_year`, fixture dates, both `backend.ts` mirrors, contract canary coverage, and proprietary EP-VLEx docs. |

FE-3.5 (frontend contract sync + component wiring) is ✅ Done as of 2026-05-15: `backend.ts` interfaces added, `RPE65_SAMPLE` populated, the 6 components wired to `payload.*`. `tsc --noEmit` clean. This exposed the fidelity gap BE-6 closes.

Recent backend status notes (2026-05-27, Codex):
- LOCAL-EVIDENCE-RUNTIME-GATE slice is implemented backend-only as an inert
  Task 16 configuration gate. Added disabled-by-default settings
  `local_evidence_enabled`, `local_evidence_allowed_flows_raw`, and
  `local_evidence_require_real_apis`, plus internal
  `LocalEvidenceRuntimeGate` / `LocalEvidenceRuntimeDecision` dataclasses in
  `app/backend/app/services/local_evidence_orchestrator.py`. The gate
  normalizes allowed runtime flows (`lookup`, `search`, `gene_viewer`,
  `workbench`), supports per-flow opt-in or `all`, rejects unknown flows
  fail-closed, and by default requires `use_real_apis=True` before future
  runtime code can prefer local stores. It is deliberately not consumed by
  routes, source cache, live providers, public Pydantic schemas, frontend
  mirrors, or Workbench. Focused local-evidence tests, local-source adjacent
  tests, broader search/sequence/gene-viewer/workbench tests, Ruff, and Black
  passed. Backend Pydantic contract canary checks pass when the unrelated
  cross-frontend byte-identical mirror test is excluded; the full
  `test_frontend_contract.py` still fails that one mirror test because
  `app/web/lib/backend.ts` has the M11 section-fetch TS block while
  `app/frontend/src/lib/backend.ts` does not. Codex did not edit frontend
  mirrors.
- LOCAL-EVIDENCE-ORCHESTRATION first slice is implemented backend-only as an
  internal no-contract-change Task 16 proof. Added
  `app/backend/app/services/local_evidence_orchestrator.py` with plain
  dataclasses and an injectable `LocalEvidenceOrchestrator` that composes the
  existing local dbSNP, ClinVar, transcript-coordinate, RepeatMasker, and
  optional sequence-window models without touching routes, public Pydantic
  schemas, frontend mirrors, live providers, or source cache. Focused tests
  prove RPE65 `rs1645931040` resolves locally to `1-68444869-T-C`, ClinVar
  `VCV001421454`, transcript exon 4/CDS position 260, RepeatMasker no-hit, and
  an injected reference-window variant context; multiallelic `rs1801133` fails
  closed until an alternate allele is supplied; local no-hit/allele-mismatch
  states do not substitute unrelated fixture records; and `LookupResponse` /
  `GeneViewerResponse` gain no `local_evidence` contract field. Focused local
  source pytest, broader Task 16-adjacent search/sequence/gene-viewer/workbench
  pytest, frontend contract canary, Ruff, and Black passed. No route/runtime
  provider wiring, source-cache rewiring, frontend/schema mirror edits,
  production source downloads/imports, live Supabase writes, uploads/imports,
  `/runs`, AlphaMissense display/runtime scoring, restricted predictor unlocks,
  destructive git, stash, reset, clean, or Task 15 native `pyBigWig`/Linux
  proof.
- TRANSCRIPT-COORDINATE-MAP helper is implemented fixture-first after Claude's
  planner update closed M11 CAR #1 and opened no M8/M9/M10a backend CARs.
  Added `TranscriptModelStore.map_coordinate()` plus
  `TranscriptCoordinateLocation` / `TranscriptCoordinateLookup` in
  `app/backend/app/services/transcript_model.py`. The helper maps GRCh38
  coordinates against the checked-in MANE/GENCODE fixture, normalizes `chr` /
  bare chromosome / RefSeq `NC_` aliases, returns exon hits with
  transcript-oriented CDS position (including RPE65 reverse-strand math), and
  returns intron hits with flanking exon numbers in transcript order plus
  nearest-exon distance. Focused tests cover RPE65 exon 4
  `NC_000001.11:g.68444869` -> CDS position 260, RPE65/CFTR intron mapping,
  and fail-closed invalid/missing/mismatch/outside states. Focused transcript,
  sequence-window, gene-viewer pytest, Ruff, and Black passed. No
  `gffutils`/BioMart install, production MANE/GENCODE ingestion, API contract
  change, frontend/schema mirror, provider/source-cache wiring, Supabase work,
  `/runs`, AlphaMissense display/runtime scoring, destructive git, stash,
  reset, or clean. Also added the broader project-specific local-first source
  workflow to `docs/proprietary/local-first-source-model-workflows.md` and the
  proprietary catalogue index, with a caveat that primitives are known
  bioinformatics patterns while the Eamos fixture-first/provenance/fail-closed
  workflow is project-specific IP.
- SOURCE-ASSET Tasks 13 and 14 are implemented fixture-first. Added
  `app/backend/app/services/dbsnp_local.py` plus
  `app/backend/app/fixtures/data_sources/dbsnp_tiny.vcf` and
  `tests/test_dbsnp_local_adapter.py` for local dbSNP GCF
  rsID-to-GRCh38 identity lookup. The adapter preserves
  `GCF_000001405.40` provenance, normalizes `NC_000001.11` / `chr1` / `1`,
  represents multiallelic rows without selecting a single allele, and returns
  structured fail-closed no-hit/mismatch/malformed states. Added
  `app/backend/app/services/repeatmasker_local.py` plus
  `app/backend/app/fixtures/data_sources/repeatmasker_tiny.rmsk.txt` and
  `tests/test_repeatmasker_local_adapter.py` for the deterministic
  RepeatMasker `rmsk.txt` to indexed interval-table proof. This intentionally
  avoids bigBed download/conversion, UI/tool rewiring, and Supabase Storage.
  Focused dbSNP/search/report pytest, RepeatMasker/indexed-reader pytest,
  Ruff, and Black passed. Native `pysam`/`pyBigWig` proofs remain skipped on
  this Windows host pending Docker/WSL/Linux approval. Checked current backend
  env: `gffutils`, `biomart`, `pybiomart`, and `bioservices` are not installed;
  use `TranscriptModelStore` for deterministic exon/intron fixture checks now,
  and consider `gffutils` only after approved MANE/GENCODE ingestion. No
  production source downloads/imports, Supabase writes/resources/uploads,
  provider/source-cache wiring, frontend/schema mirror changes, `/runs`,
  AlphaMissense display/runtime scoring, restricted predictor unlocks,
  destructive git, stash, reset, or clean.
- M11-MINIMAL-SECTION-FETCH-SKETCH is implemented backend-only after Claude's
  22:55 CAR. Added `POST /api/v1/lookup/summary` for one-call M7 tile
  summaries from current call cards, and `POST /api/v1/lookup/sections` with
  an `include` selector for `publications`, `computational_deep_dive`, and
  `clingen_vcep`. New section envelopes include freshness fields
  (`fetched_at`, `source_version`, `stale_on_failure`, `source_status`,
  `source_url`). `clingen_vcep` is explicitly `partial` until M9 ClinGen ER /
  source-cache integration lands. Population detail, disease mechanism, and
  therapies/trials remain in the monolith until M11-full/perf data; M7 should
  use the summary tiles and lazy-fetch only the three expandable sections.
  Focused section-fetch pytest, nearby report/lookup pytest, frontend contract
  canary, Ruff, and Black passed. No frontend/backend.ts mirror edits,
  provider/source-cache wiring, live Supabase writes/resources, production
  source downloads/imports, `/runs`, AlphaMissense display/runtime scoring,
  destructive git, stash, reset, or clean.
- SUPABASE-RLS-STATIC-VERIFY is implemented. Added
  `app/backend/tests/test_supabase_migrations.py`, a focused static regression
  test for `supabase/migrations/0007_optimize_rls_auth_uid_initplan.sql`. It
  parses `0001_submission_ledger.sql` and `0007` to prove the seven original
  direct-`auth.uid()` RLS policies are recreated with the same names, target
  tables, and commands, every predicate wraps `auth.uid()` as
  `(select auth.uid())`, each recreated policy has a matching
  `DROP POLICY IF EXISTS`, and the profile update policy keeps explicit
  `WITH CHECK` ownership. Focused Supabase pytest (`13 passed` across
  migration, evidence-submission Supabase, and source-field policy tests),
  Ruff, Black check, and diff check passed. No live Supabase project
  writes/resources, SQL execution, migration application, uploads/imports,
  env/deploy mutation, production source imports/downloads, provider/source-
  cache wiring, frontend/schema mirror changes, `/runs`, AlphaMissense,
  runtime ML scoring, destructive git, stash, reset, or clean.
- SOURCE-ASSET Task 12 ClinVar VCF local adapter is implemented
  fixture-first, and the Supabase RLS performance migration is drafted
  local-only. Added `app/backend/app/services/clinvar_local.py` with a
  standalone parser/store for tiny ClinVar VCF fixtures, source and record
  provenance, GRCh38 gnomAD-style variant ID lookup, VCV/numeric Variation ID
  lookup, contig alias normalization, and structured fail-closed no-hit,
  allele-mismatch, contig-mismatch, invalid-coordinate, and malformed-row
  states. Added `app/backend/app/fixtures/data_sources/clinvar_tiny.vcf` for
  RPE65 `1-68444869-T-C` / `VCV001421454` plus
  `app/backend/tests/test_clinvar_local_adapter.py`. Added
  `supabase/migrations/0007_optimize_rls_auth_uid_initplan.sql`, which
  recreates the seven existing RLS policies with direct `auth.uid()` predicates
  rewritten as `(select auth.uid())`; it was not applied live. Focused pytest
  (`40 passed` across ClinVar local, clinical consensus, functional evidence,
  and tool invariant tests), Ruff, Black, and static migration checks passed.
  No production ClinVar download/import, Supabase project writes/resources,
  uploads/imports, env/deploy mutation, provider/source-cache wiring,
  frontend Workbench edits, schema mirror changes, `/runs`, AlphaMissense,
  runtime ML scoring, destructive git, stash, reset, or clean.
- SOURCE-ASSET Task 11 small clinical source table parsers are implemented
  fixture-first. Added `app/backend/app/services/clinical_source_tables.py`
  with normalized parsers/store helpers for MONDO JSON, HPOA disease phenotype
  rows, HPO gene-phenotype rows, ClinGen gene-validity CSV, and GenCC CSV.
  Added tiny fixtures under `app/backend/app/fixtures/source_tables/` and
  `tests/test_clinical_source_tables.py` covering provenance, MONDO disease/
  xref resolution without OMIM import, HPOA+gene phenotype linking, ClinGen
  classification/source date, GenCC assertion/submitter/source date, and
  structured malformed-row failures. Focused pytest, related source-registry/
  manifest pytest, Ruff, and Black passed. Existing indexed-reader tests still
  pass with native `pysam`/`pyBigWig` skips on Windows. A Docker/WSL native
  proof attempt is blocked pending IT approval: WSL is not installed and Docker
  Desktop local engine returned HTTP 500 on both contexts after start/restart
  attempts. No production source downloads/imports, Supabase writes/resources,
  uploads, migrations, env mutation, deploy, provider/source-cache wiring,
  frontend Workbench edits, schema mirror changes, `/runs`, AlphaMissense,
  runtime ML scoring, destructive git, stash, reset, or clean.
- SOURCE-ASSET Task 10 MANE/GENCODE transcript model store is implemented
  fixture-first. Added `app/backend/app/services/transcript_model.py` with
  `TranscriptModelStore`, structured unavailable lookup states, source
  provenance, transcript alias matching, and fixture validation for exon/CDS
  order. Added
  `app/backend/app/fixtures/transcript_models/mane_gencode_tiny.json` with
  RPE65 MANE Select `NM_000329.3` / `ENST00000262340.6` plus one non-RPE65
  CFTR control. RPE65 preserves reverse-strand transcript order and a c.260/
  exon-4 interval containing GRCh38 `1:68444869`; CFTR preserves plus-strand
  ordering. Added `tests/test_transcript_model_store.py`; focused pytest,
  related reference/sequence/gene-viewer pytest, Ruff, Black, and diff-check
  passed. No production MANE/GENCODE downloads/imports, Supabase
  writes/resources, uploads, migrations, env mutation, deploy,
  provider/source-cache wiring, frontend Workbench edits, schema mirror
  changes, `/runs`, AlphaMissense, runtime ML scoring, destructive git, stash,
  reset, or clean.
- SOURCE-ASSET Task 9 reader proof is implemented to the Windows-compatible
  boundary. Added `app/backend/app/services/indexed_sources.py` with
  fail-closed `pysam` VCF/tabix, `pyBigWig` bigWig, and RepeatMasker
  `rmsk.txt` interval-table conversion abstractions, plus
  `tests/test_indexed_source_readers.py`. Current PyPI metadata shows
  `pysam==0.24.0` and `pyBigWig==0.3.25` provide CPython 3.10 manylinux wheels
  but no Windows wheels; source-build prep failed on this Windows host, so
  native VCF/bigWig tiny proofs skip locally and should run on Linux/Render
  once dependencies install. Added Linux-only requirement pins, staged wheels
  on `C:` first, then moved the small package artifacts to ignored
  `app/backend/data/package_wheels/task9_readers` on `E:` after checking space.
  User clarified source-asset placement: smaller reviewed sources may live on
  `E:`, while dbSNP/GCF and phyloP stage on `C:`; registry/docs now mark
  phyloP for `C:` staging. Focused pytest passed (`22 passed, 4 skipped`),
  Ruff, Black, and pip dry-run passed. No production source downloads/imports,
  Supabase writes/resources, uploads, migrations, env mutation, deploy,
  provider/source-cache wiring, frontend Workbench edits, schema mirror
  changes, `/runs`, AlphaMissense, runtime ML scoring, destructive git, stash,
  reset, or clean.
- SOURCE-ASSET Task 8 registry readiness has official metadata filled for the
  named post-reference backbone after browsing official source pages/listings
  only. `DataSourceRecord` now carries `source_version`, `checksum_plan`,
  `terms_url`, and `terms_status`; `SourceAssetReadiness` exposes those fields
  while still blocking on terms review, backend storage policy review, reader
  proof, and explicit approval. Corrections captured: dbSNP official file is
  `GCF_000001405.40.gz` + `.tbi`; UCSC RepeatMasker source is `rmsk.txt.gz`
  with derived `rmsk.bb` only after conversion/bigBed proof; phyloP
  `hg38.phyloP100way.bw` is listed at 9.2 GB with `md5sum.txt`, and was later
  changed to explicit `C:` staging by user direction on 2026-05-27; MANE v1.4
  official GTF is
  `MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz` with MANE Select rows selected by
  tags; HPO starts from official annotation files and does not treat the draft
  `hp.gpad` path as verified. Focused pytest (`17 passed`), Ruff, and Black
  passed. No downloads, imports, dependency installs, Supabase writes/resources,
  uploads, migrations, env mutation, deploy, provider/source-cache wiring,
  frontend Workbench edits, schema mirror changes, `/runs`, AlphaMissense,
  runtime ML scoring, file moves/replacements, destructive git, stash, reset,
  or clean.
- SOURCE-ASSET-ROLLOUT is started after user correction that ClinVar VCF,
  dbSNP/GCF, RepeatMasker, phyloP, MANE, GENCODE, MONDO, HPOA, ClinGen gene
  validity, and GenCC are the project backbone and should precede deeper
  Workbench UI work. Added
  `docs/local-first-data-source-strategy/source-asset-rollout.md` with Task
  8-16: source manifest/approval pack, indexed reader proofs, transcript model
  store, small clinical source parsers, ClinVar local adapter, dbSNP local
  adapter, RepeatMasker proof, phyloP proof, and source-backed orchestration.
  Also added `app/backend/app/data_sources/source_manifest.py` plus
  `tests/test_source_asset_manifest.py`; the manifest enumerates the named
  post-reference Day 1 sources and reports missing approval fields,
  backend-owned storage review needs, `C:` staging, and actual-size checks.
  Focused pytest (`15 passed`), Ruff, Black, and diff-check passed. No source
  downloads, dependency installs, Supabase writes/resources, uploads,
  migrations, env mutation, deploy, provider/source-cache wiring, frontend
  Workbench edits, schema mirror changes, `/runs`, AlphaMissense, runtime ML
  scoring, commit, push, or destructive git were performed.
- LOCAL-SEQUENCE-WINDOW-MODEL is implemented and verified as a backend-only
  first slice for the Workbench local-first sequence-read contract. Added
  `app/backend/app/services/sequence_window_model.py` with
  `LocalSequenceWindowBuilder`, local reference-window/base-check/variant-window
  dataclasses, provenance, warnings, and unavailable reasons. It accepts
  already-resolved genomic alleles, reads through `ReferenceGenomeStore` or
  `TwoBitReferenceGenomeStore`, validates REF against the local reference, and
  applies ALT into a small genomic-forward window while preserving the existing
  1-based inclusive coordinate convention. Added
  `tests/test_sequence_window_model.py` for SNV, insertion, deletion,
  mismatch, unavailable-state, offset, flank-convention, and provenance
  behavior, and extended the opt-in local `hg38.2bit` smoke to prove RPE65
  `1-68444869-T-C` applies `T>C` in the local full-asset window. Focused
  pytest, opt-in full-asset smoke, related Workbench/reference pytest, Ruff,
  Black, and diff-check passed. Full backend pytest was attempted but timed
  out after 5 minutes before returning output; no Python test process remained.
  No frontend Workbench edits, schema/contract mirror changes, Supabase
  writes/resources, uploads, file moves/replacements, env mutation, deploy,
  provider/source-cache wiring, `/runs`, AlphaMissense, runtime ML scoring,
  commit, push, or destructive git were performed.
- REPORT-DEMO-ENCODING live `/report?demo=1` mojibake fix is implemented and
  verified. The backend source fixture strings decoded cleanly; the generated
  `app/web/lib/rpe65-sample.json` demo artifact carried UTF-8-as-Latin-1
  strings for em-dash and middle-dot display text. Repaired the sample as
  structured JSON and rewrote it ASCII-escaped, updated
  `FixtureBackedTool.load_fixture()` to use `encoding="utf-8"`, and added
  `tests/test_demo_payload_encoding.py` covering backend response
  content-type/clean Unicode payloads, the shipped RPE65 sample artifact, and
  UTF-8 fixture loading. Focused pytest, Ruff, Black check, no-mojibake `rg`,
  and JSON parse checks passed. No UI/component/style edits, provider wiring,
  source-cache writes, Supabase writes/resources, env mutation, deploy,
  `/runs`, AlphaMissense, or destructive git were performed.
- DATA-SOURCE-REGISTRY-TASK-7 approved 2bit reader compatibility proof is
  implemented and verified. Supabase MCP tools are visible in this Codex
  session, but no Supabase projects/storage/resources were touched. Current
  PyPI metadata was checked and `twobitreader==3.1.8` was selected over
  `py2bit` because `twobitreader` publishes a pure Python `py3-none-any` wheel
  for Python `>=3.9`, while `py2bit` is a C extension with
  POSIX/manylinux-oriented artifacts. Added the dependency to
  `app/backend/requirements.txt`, recorded the selection/rationale in the
  runtime registry `python_twobit_reader` row, and added
  `TwoBitReferenceGenomeStore` in `app/backend/app/services/reference_genome.py`.
  The adapter preserves 1-based inclusive caller coordinates, supports
  `chr1`/`1`/`NC_000001.11` aliases, reports source metadata, and fails closed
  for missing assets, checksum mismatch, unknown chromosomes, out-of-bounds
  windows, and short reads. Default tiny `.2bit` fixture tests pass without the
  full asset; the opt-in local smoke with `EAMOS_VERIFY_LOCAL_HG38_2BIT=1`
  inventoried the existing ignored `hg38.2bit` and read GRCh38 `1:68444869` as
  `T` for `NM_000329.3:c.260A>G` / `1-68444869-T-C`. Focused pytest,
  opt-in full-asset smoke, Ruff, Black check, direct proof command, and diff
  check passed. No uploads, file moves/replacements, env mutation, deploy,
  provider/source-cache wiring, Supabase writes/resources, `/runs`,
  AlphaMissense, runtime ML scoring, commit, push, or destructive git were
  performed.
- DATA-SOURCE-REGISTRY-TASK-6 production `hg38.2bit` runtime asset path
  planning/config tests are implemented and verified. Added
  `HG38_2BIT_RUNTIME_ASSET_MODE`, `HG38_2BIT_RUNTIME_ASSET_PATH`, and
  `HG38_2BIT_RUNTIME_ASSET_OBJECT_URI` settings plus `.env.example`
  documentation; defaults use the backend-local ignored asset path
  `./data/bio_assets/genomes/hg38.2bit`. Extended the `ucsc_hg38_2bit`
  registry row with supported delivery modes `local_path`,
  `object_storage_local_cache`, and `mounted_volume`, and recorded that the
  eventual reader requires a local filesystem path. Added
  `app/backend/app/data_sources/runtime_assets.py` and
  `app/backend/tests/test_hg38_runtime_asset_config.py` for pure plan/status
  inspection: ready, missing, not-file, size mismatch, checksum mismatch, and
  config error. Focused pytest, reference-store smoke, Ruff, Black check, and
  diff check passed. No asset upload, file move/replacement, env mutation,
  deploy, Supabase write/resource creation, download, install, reader
  selection, full-asset sequence read, provider wiring, source-cache write,
  commit, push, `/runs`, AlphaMissense, or destructive git were performed.
  Supabase MCP note: this Codex session can see `.mcp.json` for project
  `cpdjxsgasaesysvxkpmi`, but Supabase MCP tools are not exposed in the
  current Codex tool surface; install/enable the Codex Supabase plugin and
  restart/reload before Supabase-heavy storage proof work.
- DATA-SOURCE-REGISTRY / LOCAL-FIRST follow-up note: the two desktop
  `genomicLLM_Part1.ipynb` and `genomicLLM_Part2.ipynb` notebooks were
  reviewed read-only for relevance. They are relevant after the deterministic
  local reference-window layer lands, not before it: Part 1 informs DNA
  k-mer/tokenisation/embedding concepts, and Part 2 is the useful zero-shot
  reference-vs-alternate scoring pattern with per-token disruption profiles.
  Saved this as a deferred follow-up in
  `docs/local-first-data-source-strategy/plan.md`. Do not install
  `torch`/`transformers`, download `InstaDeepAI/nucleotide-transformer-500m-human-ref`,
  or add runtime ML scoring without a separately approved ML spike. First
  prove exact GRCh38 windows, REF allele validation, ALT-applied windows,
  flank/token-map conventions, and provenance. Treat future scores as
  research/triage evidence, not ACMG classification.
- DATA-SOURCE-REGISTRY-TASK-5 opt-in local `hg38.2bit` smoke scaffold is
  implemented and verified. Added
  `app/backend/tests/test_reference_genome_store_local_hg38.py`. The new test
  module is skipped unless `EAMOS_VERIFY_LOCAL_HG38_2BIT=1`; when opted in on
  this host, it verifies the existing ignored local
  `app/backend/data/bio_assets/genomes/hg38.2bit` path, size `835,393,456`,
  MD5 `dcc3ea27079aa6dc3f9deccd7275e0f8`, registry metadata, and local
  `md5sum.txt`. The future reader-backed RPE65 check is recorded as a pending
  skipped assertion: GRCh38 `1:68444869` should be `T` for
  `NM_000329.3:c.260A>G` / `1-68444869-T-C`. Default smoke pytest skips,
  opt-in smoke pytest, focused registry/reference pytest, Ruff, Black check,
  and diff check passed. No real 2bit reader install/selection, full
  `hg38.2bit` sequence reads, downloads, uploads, file moves/replacements,
  provider wiring, source-cache writes, Supabase writes, env mutation, deploy,
  commit, push, `/runs`, AlphaMissense, or destructive git were performed.
- DATA-SOURCE-REGISTRY-TASK-4 fixture-backed `ReferenceGenomeStore` is
  implemented and verified. Added
  `app/backend/app/services/reference_genome.py`,
  `app/backend/app/fixtures/reference_genome/hg38_tiny.json`,
  `app/backend/app/fixtures/reference_genome/README.md`, and
  `app/backend/tests/test_reference_genome_store.py`. The store uses 1-based
  inclusive caller coordinates, explicit chromosome aliases, deterministic
  synthetic sequence windows, structured reference-base validation, and
  metadata shaped like the registry/inventory records: source ID, source URL,
  source version, fixture path, checksum, reader, local `hg38.2bit` path, MD5,
  and size. The fixture README records the methods/protocol, including
  coordinate equations, alias rules, validation behavior, and checksum method.
  Focused pytest, Ruff, Black check, and diff check passed. No full
  `hg38.2bit` sequence reads, downloads, uploads, file moves/replacements,
  installs, provider wiring, source-cache writes, Supabase writes, env
  mutation, deploy, commit, push, `/runs`, AlphaMissense, or destructive git
  were performed.
- DATA-SOURCE-REGISTRY-TASK-3 existing `hg38.2bit` inventory proof is
  implemented and verified. Added
  `app/backend/app/data_sources/local_inventory.py`, exported the read-only
  inventory helpers/constants, strengthened `ucsc_hg38_2bit` registry
  validation for source URL/local path/local size/local MD5, and added
  `app/backend/tests/test_local_hg38_inventory.py`. The focused local proof
  verified the existing ignored asset at
  `app/backend/data/bio_assets/genomes/hg38.2bit` as 835,393,456 bytes with MD5
  `dcc3ea27079aa6dc3f9deccd7275e0f8`, matching registry metadata and
  `md5sum.txt`; the test skips cleanly when the ignored asset is absent.
  Focused pytest, Ruff, Black check, and diff check passed. No downloads,
  uploads, file moves/replacements, installs, provider wiring, source-cache
  writes, Supabase writes, env mutation, deploy, commit, push, `/runs`,
  AlphaMissense, or destructive git were performed.
- DATA-SOURCE-REGISTRY-TASK-2 license/field policy helper is implemented and
  verified. Added `app/backend/app/data_sources/policy.py`, exported
  `SourceFieldPolicy`/`FieldPolicyDecision`/`PolicyAction`/`ProductTier`, and
  added `app/backend/tests/test_source_field_policy.py`. The helper gives
  future adapters explicit request/cache/normalize/serialize decisions and
  recursive payload filtering. MyVariant is allowlisted to `gnomad_genome` and
  `gnomad_exome`; CADD, dbNSFP REVEL/PrimateAI, SpliceAI, REVEL, and
  PrimateAI-3D paths deny by default; public/prod policy denies restricted
  predictor rows while they remain `restricted_unlicensed`; and internal
  fixture mode preserves only warning-labeled restricted examples. Focused
  pytest, Ruff, Black check, and diff check passed. No downloads, installs,
  provider wiring, source-cache writes, Supabase writes, env mutation, deploy,
  commit, push, `/runs`, AlphaMissense, or destructive git were performed.
- DATA-SOURCE-REGISTRY-TASK-1 runtime validation is implemented and verified.
  Added `app/backend/app/data_sources/{__init__.py,registry.py}` plus
  `app/backend/tests/test_data_source_registry.py`. The runtime registry now
  carries 23 reviewed source rows without loading `plans/` at request time,
  fails closed for missing identity/license/storage/field/checksum/download
  metadata, enforces `ucsc_hg38_2bit` as `p0_first_asset_proof`, keeps
  dbSNP `GCF_000001405.40` not download-approved, and keeps
  SpliceAI/CADD/REVEL/PrimateAI-3D rows restricted/unlicensed. Focused pytest,
  Ruff, Black check, and diff check passed. No downloads, installs, Supabase
  writes, env mutation, deploy, commit, push, `/runs`, AlphaMissense, or
  destructive git were performed.
- DATA-SOURCE-REGISTRY draft is complete for review. Added
  `plans/data-source-registry/spec.md` and
  `plans/data-source-registry/source-registry.seed.json` before any downloads
  or installs. The spec preserves the corrected DOCX matrix: MyVariant is a
  gnomAD Day 1 lookup path only; restricted predictors are locked/filtered;
  dbSNP `GCF_000001405.40` is a Day 1 large asset; InterVar remains
  DOCX-intended but blocked for commercial production until InterVar/ANNOVAR/
  OMIM rights review; and assets whose actual download size exceeds 10 GB
  stage on `C:` until moved to Supabase Storage or another approved target.
  Follow-up correction: mark `hg38.2bit` as `p0_first_asset_proof` because the
  reference reader/storage path underpins sequence context, gene viewer,
  primer, CRISPR, alignment, and later indexed-asset adapters.
  The ignored local copy at `app/backend/data/bio_assets/genomes/hg38.2bit`
  exists from prior `isPcr` work and was MD5 re-verified on 2026-05-26 as
  `dcc3ea27079aa6dc3f9deccd7275e0f8`; next work should inventory/prove it, not
  redownload it.
  Follow-up design-doc pass added
  `docs/local-first-data-source-strategy/design.md`, separating the next work
  into three tracks: local reference/model layer, Supabase storage/runtime
  posture, and licensing/field policy. Per `design-doc`, review before writing
  the implementation spec and task plan.
  After design approval, added
  `docs/local-first-data-source-strategy/spec.md` for runtime registry,
  license/field policy, and fixture-first `ReferenceGenomeStore` plus existing
  local `hg38.2bit` inventory proof. Per `spec`, review before the task plan.
  After spec approval, added
  `docs/local-first-data-source-strategy/plan.md`; the plan explicitly
  separates "do not commit the binary" from "production backend must have an
  approved runtime asset path" so website tools can use fast local sequence
  reads.
- LAUNCH-ENV Render `DEBUG=false` is now directly verified by Codex. A
  read-only Render API check identified backend service `eamos-dev`
  (`srv-d896ie77f7vs73brs140`, `https://eamos-dev.onrender.com`) and confirmed
  the `DEBUG` env var is present with value `false`. No deploy or env mutation
  was performed.
- HARDENING-MANIFEST is implemented locally. Added
  `app/backend/app/fixtures/hardening/project_100_sample_manifest.json`, a
  separate project-wide manifest that resolves to 10 genes x 10 samples = 100
  total samples across landing/report/workbench hardening: one per-gene
  reference/control render sample plus all nine existing ClinVar challenge
  variants for that gene. Added validation in
  `tests/test_project_hardening_manifest.py`; focused manifest/old-stack tests,
  ruff, black, full backend pytest, and diff checks passed.
- GV-DYN dynamic variant-applied gene/protein viewer is implemented locally and
  verified. Added internal `variant_applied_model.py`, exposed
  `tracks.protein_product`, mirrored both TypeScript contracts, and wired
  Workbench gene/protein/exon rendering so variant mode can reflect
  source-backed missense/synonymous/stop-gained/stop-lost/frameshift/in-frame
  indel/dup/delins-style product effects instead of only static reference
  geometry. Simple coding SNV/indel/dup/delins window edits are applied; cross-
  segment/cross-intron edits still fail closed until multi-segment rendering is
  supported.
- GV-SEC viewer hardening is implemented locally. `/api/v1/viewer` now shares
  Workbench rate limits, viewer request/window/track fields are bounded, and
  proxy-header trust for rate-limit client IPs defaults false unless explicitly
  enabled.
- WB-SEC Workbench AB1/alignment input hardening is implemented locally and
  full backend pytest is green. Added Workbench request-size/field bounds,
  AB1 encoded/decoded/base-call/channel/finite-signal guards, ambiguous
  align-input rejection, and a pairwise-alignment matrix preflight fallback
  before Biopython is called.
- Project-wide hardening cohort correction: the existing
  `clinvar_gene_agnostic_report_stack.json` remains 90 variants plus one global
  RPE65 control. The corrected hardening matrix is now defined separately in
  `project_100_sample_manifest.json` as 10 chosen genes, each with one per-gene
  control sample plus nine challenge variants.
- LAUNCH-SEC backend hardening is implemented locally and full backend pytest is
  green. Added configurable in-memory rate limiting for auth, lookup/parse,
  chat/stream, evidence submissions, payments checkout/webhook, and Workbench
  primer/crispr/align; removed client-controlled Stripe checkout redirects; and
  changed backend `DEBUG` defaults to false. Durable Redis/private-DB/gateway
  rate limiting remains the future multi-instance path.
- SEARCH-RSID bare dbSNP resolver hardening is committed and pushed as
  `548fde7` (`fix(backend): resolve bare dbSNP rsID searches`). Raw search text
  `rs61752871` resolves to `RPE65 NM_000329.3:c.271C>T`; `rs1801133` resolves
  to source-supported `MTHFR NM_005957.5:c.665C>T`, with resolved genomic
  identity carried into `/api/v1/lookup`; Claude redeployed Render and live
  `/lookup/parse` smokes passed for both rsIDs.
- LAUNCH-BLOCKERS pickup: Claude/Steven reported Supabase 0003/0004/0005/0006
  live, Render Supabase env set, `DEBUG=false`, authenticated evidence
  write-through E2E green, and Supabase security advisors clean.
- RP-PUB-2 EP-VLEx exact snippet/status quality is done. Exact variant snippets
  now require exact variant-term text; non-exact rows expose honest
  `snippet_status` values. RPE65 ClinVar fixture contradiction corrected to
  VCV001421454/VUS; VCV000099473 is ABCA4, not RPE65.
- WB-ENG-1 CRISPR/AB1 source-backed Workbench engines are in progress.
  R/Bioconductor `crisprScore` adapter boundary plus configurable
  `CRISPR_RSCRIPT_PATH`; Biopython AB1 parser + PairwiseAligner-first alignment
  path verified against a real user AB1 file. RuleSet3/Lindel remain
  conda-gated; deterministic fallback preserved.
- DATA-1 source-cache/local evidence architecture is planned in
  `plans/source-cache-architecture.md`: source-cache rows, stale-on-failure,
  backend-only Supabase RLS posture, status vocabulary, freshness fields,
  CRISPR score cache, and local gnomAD mini-store path.

Codex session id (resumable): `019e26bf-c0db-7b03-aff3-a5303bac4eed`. Resume with `codex resume 019e26bf-c0db-7b03-aff3-a5303bac4eed`.

---

You (Codex) are picking up the backend half of the Eamos v2 rebuild. This plan is self-contained — every file path, schema, and verification step is here. You don't need to read the HTML mocks or the frontend plan.

## Context (1 paragraph)

Eamos is a genomic variant lookup tool. Frontend (React/Vite) is being expanded to render new modules on the variant report and a new "Workbench" surface (sequence viewer + design tools). Your job is to:

1. Archive the Franklin tool (Genoox is a competitor — we're cutting them out).
2. Extend `ReportPayload` with six new fields the new report modules consume.
3. Add a lookup-scoped chat endpoint (`POST /api/v1/chat`) — siblings the existing run-scoped `POST /api/v1/runs/{run_id}/chat/stream`, which stays unchanged.
4. Add three Workbench engine endpoints (`POST /api/v1/primer`, `/api/v1/crispr`, `/api/v1/align`) returning canned sample data — real engines come later.
5. Update tests.

Default mode is `USE_REAL_APIS=false` / `LLM_PROVIDER=mock`. Everything works offline against fixtures.

## Coordination with frontend (Claude Code)

Claude Code is porting design mocks in parallel. Your contract surface:

| Frontend | Backend |
| -------- | ------- |
| `app/frontend/src/lib/backend.ts` | `app/backend/app/schemas/*.py` |
| `app/frontend/src/lib/sample-report.ts` | `app/backend/app/fixtures/tools/*.json` |

When you add a new Pydantic field, expect Claude Code to add the matching TypeScript interface field. The test `app/backend/tests/test_frontend_contract.py` enforces this — it must stay passing.

**Sync point** — after each milestone, run:

```bash
cd app/backend && python -m pytest tests/ -q
```

All tests must pass before the next milestone starts.

---

## BE-1 — Franklin archive

Franklin is a competitor. Remove from the active codebase; preserve under `archive/` for reference.

**Move** (create directories as needed):

```
archive/franklin/
  franklin.py                     ← from app/backend/app/tools/franklin.py
  franklin_fixtures.json          ← from app/backend/app/fixtures/tools/franklin_fixtures.json
  franklin-api-field-guide.md     ← from docs/architecture/franklin-api-field-guide.md
```

**Delete from `app/tools/registry.py`** — remove the `"franklin"` key and its import.

**Drop from `app/services/workflow.py`** and `app/services/lookup_service.py` — remove all references to `"franklin"` in the tool loops, evidence tuples, and any helper functions.

**Drop from `app/rules/clinic_rules.py`** — any `franklin`-keyed evidence weighting.

**Drop Franklin settings from `app/core/config.py`**: any `franklin_*` fields (`franklin_email`, `franklin_password`, `franklin_api_token`, `franklin_base_url`, etc.).

**Update `.env.example`** — remove `FRANKLIN_*` lines.

**Update tests** — `app/backend/tests/test_real_agent_smoke.py`, `test_run_flow.py`, `test_search_api.py` — remove any Franklin assertions.

**Update CLAUDE.md indices** — `app/backend/app/tools/CLAUDE.md` (remove the `franklin.py` row) and `app/backend/app/fixtures/tools/CLAUDE.md`.

**Verify**:

```bash
cd app/backend
python -m pytest tests/ -q
grep -r "franklin" app/                 # should be empty
grep -r "Franklin" app/                 # should be empty
```

If `grep` returns anything in `app/`, that's a leak. (References in `docs/` / `archive/` / `CHANGELOG.md` are fine — historical context is preserved there.)

## BE-2 — Lookup payload v2

Extend `ReportPayload` (in `app/backend/app/schemas/run.py`) with six new fields that drive the new frontend report modules. Then plumb them through `app/services/lookup_service.py` so `POST /api/v1/lookup` returns them.

**Add new Pydantic models** at the top of `app/backend/app/schemas/run.py` (before `ReportPayload`):

```python
from typing import Literal

ClassificationTier = Literal["pathogenic", "likely_pathogenic", "vus", "likely_benign", "benign"]
AcmgVerdict = Literal["met", "not_met", "not_assessed"]
PredictorVerdict = Literal["damaging", "tolerated", "uncertain"]


class NearbyVariant(BaseModel):
    cds_pos: int                       # codon offset from query variant centre, -45..+45
    classification: ClassificationTier
    hgvs: str                          # e.g. "c.272A>G"
    clinvar_id: str | None = None


class CodonCell(BaseModel):
    codon_number: int                  # absolute codon number (e.g. 87 for c.260)
    aa_ref: str                        # one-letter AA
    is_query: bool = False             # the codon containing the queried variant


class LocusContext(BaseModel):
    """Region viewer payload — drives <LocusContext /> on the report."""
    gene: str
    centre_cdna: str                   # the queried variant cDNA, e.g. "c.260A>G"
    nearby_variants: list[NearbyVariant] = Field(default_factory=list)
    codon_strip: list[CodonCell] = Field(default_factory=list)  # 11 codons centred on query


class PredictorCard(BaseModel):
    """One card in the <InSilicoGrid />."""
    name: Literal["REVEL", "AlphaMissense", "MetaLR", "SpliceAI"]
    score: float                       # 0..1
    threshold: float                   # 0..1
    verdict: PredictorVerdict
    source_url: str | None = None


class InSilicoPredictions(BaseModel):
    cards: list[PredictorCard] = Field(default_factory=list)
    consensus_note: str                # e.g. "Predictors converge on damaging."


class AcmgCriterion(BaseModel):
    code: Literal[
        "PVS1",
        "PS1", "PS2", "PS3", "PS4",
        "PM1", "PM2", "PM3", "PM4", "PM5", "PM6",
        "PP1", "PP2", "PP3", "PP4", "PP5",
        "BA1",
        "BS1", "BS2", "BS3", "BS4",
        "BP1", "BP2", "BP3", "BP4", "BP5", "BP6", "BP7",
    ]
    verdict: AcmgVerdict
    note: str | None = None


class AcmgCriteriaScaffold(BaseModel):
    criteria: list[AcmgCriterion] = Field(default_factory=list)
    disclaimer: str = "Supporting evidence, not classification."


class CuratedVariantsDistribution(BaseModel):
    """3×4 heat matrix. Rows × cols flattened — 12 cells."""
    cells: dict[str, int] = Field(default_factory=dict)
    # keys: "pathogenic_lof", "pathogenic_missense", "pathogenic_noncoding",
    #       "pathogenic_synonymous", "vus_lof", "vus_missense", ...
    # 12 entries total.
    total: int
    reading: str                       # one-line summary


class AssociatedCondition(BaseModel):
    name: str
    case_count: int
    evidence_level: Literal["definitive", "strong", "moderate", "limited"]
    inheritance: Literal["AR", "AD", "XL", "MT"]
    source: str                        # e.g. "OMIM #204100"


class PublicationsCallout(BaseModel):
    total_count: int
    scholar_url: str
    ai_summary_prompt: str             # text to drop into Ask Eamos when "AI summary" clicked
```

**Add the six new optional fields** to `ReportPayload` (preserve existing fields):

```python
class ReportPayload(BaseModel):
    # ... existing fields unchanged ...
    locus_context: LocusContext | None = None
    in_silico_predictions: InSilicoPredictions | None = None
    acmg_criteria_scaffold: AcmgCriteriaScaffold | None = None
    curated_variants_distribution: CuratedVariantsDistribution | None = None
    associated_conditions: list[AssociatedCondition] = Field(default_factory=list)
    publications_callout: PublicationsCallout | None = None
```

**Populate these fields in `app/services/lookup_service.py`**. For the v2 cycle, use fixture data — real data ingestion is M-002.

Create a new fixture file `app/backend/app/fixtures/lookup_v2_modules.json` with sample data for RPE65 c.260A>G:

```json
{
  "RPE65": {
    "c.260A>G": {
      "locus_context": {
        "gene": "RPE65",
        "centre_cdna": "c.260A>G",
        "nearby_variants": [
          { "cds_pos": -30, "classification": "likely_pathogenic", "hgvs": "c.230T>C", "clinvar_id": "1234" },
          { "cds_pos": -12, "classification": "vus",                "hgvs": "c.248G>A", "clinvar_id": "5678" },
          { "cds_pos": 0,   "classification": "likely_pathogenic", "hgvs": "c.260A>G", "clinvar_id": "1421454" },
          { "cds_pos": 8,   "classification": "benign",             "hgvs": "c.268C>T", "clinvar_id": "9101" },
          { "cds_pos": 23,  "classification": "pathogenic",         "hgvs": "c.283G>A", "clinvar_id": "1121" }
        ],
        "codon_strip": [
          { "codon_number": 82, "aa_ref": "L", "is_query": false },
          { "codon_number": 83, "aa_ref": "V", "is_query": false },
          { "codon_number": 84, "aa_ref": "G", "is_query": false },
          { "codon_number": 85, "aa_ref": "K", "is_query": false },
          { "codon_number": 86, "aa_ref": "Y", "is_query": false },
          { "codon_number": 87, "aa_ref": "D", "is_query": true  },
          { "codon_number": 88, "aa_ref": "L", "is_query": false },
          { "codon_number": 89, "aa_ref": "H", "is_query": false },
          { "codon_number": 90, "aa_ref": "P", "is_query": false },
          { "codon_number": 91, "aa_ref": "I", "is_query": false },
          { "codon_number": 92, "aa_ref": "T", "is_query": false }
        ]
      },
      "in_silico_predictions": {
        "cards": [
          { "name": "REVEL",        "score": 0.78, "threshold": 0.50, "verdict": "damaging",   "source_url": "https://sites.google.com/site/revelgenomics" },
          { "name": "AlphaMissense","score": 0.71, "threshold": 0.564,"verdict": "damaging",   "source_url": "https://alphamissense.hegelab.org" },
          { "name": "MetaLR",       "score": 0.62, "threshold": 0.50, "verdict": "damaging",   "source_url": null },
          { "name": "SpliceAI",     "score": 0.12, "threshold": 0.20, "verdict": "tolerated",  "source_url": "https://spliceailookup.broadinstitute.org" }
        ],
        "consensus_note": "Three of four predictors converge on damaging; SpliceAI shows no splice impact."
      },
      "acmg_criteria_scaffold": {
        "criteria": [
          { "code": "PVS1", "verdict": "not_met",       "note": null },
          { "code": "PS1",  "verdict": "not_met",       "note": null },
          { "code": "PS2",  "verdict": "not_assessed",  "note": null },
          { "code": "PS3",  "verdict": "not_assessed",  "note": null },
          { "code": "PS4",  "verdict": "not_assessed",  "note": null },
          { "code": "PM1",  "verdict": "not_met",       "note": null },
          { "code": "PM2",  "verdict": "met",           "note": "Absent from gnomAD v4 (>250k alleles)." },
          { "code": "PM3",  "verdict": "not_assessed",  "note": null },
          { "code": "PM4",  "verdict": "not_met",       "note": null },
          { "code": "PM5",  "verdict": "met",           "note": "Different missense at same codon previously classified pathogenic." },
          { "code": "PM6",  "verdict": "not_assessed",  "note": null },
          { "code": "PP1",  "verdict": "not_assessed",  "note": null },
          { "code": "PP2",  "verdict": "not_met",       "note": null },
          { "code": "PP3",  "verdict": "met",           "note": "Multiple in-silico predictors agree on damaging." },
          { "code": "PP4",  "verdict": "met",           "note": "Phenotype highly specific for RPE65-related disease." },
          { "code": "PP5",  "verdict": "not_assessed",  "note": null },
          { "code": "BA1",  "verdict": "not_met",       "note": null },
          { "code": "BS1",  "verdict": "not_met",       "note": null },
          { "code": "BS2",  "verdict": "not_assessed",  "note": null },
          { "code": "BS3",  "verdict": "not_assessed",  "note": null },
          { "code": "BS4",  "verdict": "not_assessed",  "note": null },
          { "code": "BP1",  "verdict": "not_met",       "note": null },
          { "code": "BP2",  "verdict": "not_assessed",  "note": null },
          { "code": "BP3",  "verdict": "not_met",       "note": null },
          { "code": "BP4",  "verdict": "not_met",       "note": null },
          { "code": "BP5",  "verdict": "not_assessed",  "note": null },
          { "code": "BP6",  "verdict": "not_assessed",  "note": null },
          { "code": "BP7",  "verdict": "not_met",       "note": null }
        ],
        "disclaimer": "Supporting evidence, not classification."
      },
      "curated_variants_distribution": {
        "cells": {
          "pathogenic_lof": 42,
          "pathogenic_missense": 28,
          "pathogenic_noncoding": 9,
          "pathogenic_synonymous": 0,
          "vus_lof": 3,
          "vus_missense": 51,
          "vus_noncoding": 18,
          "vus_synonymous": 12,
          "benign_lof": 0,
          "benign_missense": 7,
          "benign_noncoding": 31,
          "benign_synonymous": 24
        },
        "total": 225,
        "reading": "Most pathogenic RPE65 variants are loss-of-function or missense in the catalytic domain."
      },
      "associated_conditions": [
        { "name": "Leber congenital amaurosis 2",      "case_count": 187, "evidence_level": "definitive", "inheritance": "AR", "source": "OMIM #204100" },
        { "name": "Retinitis pigmentosa 20",           "case_count":  62, "evidence_level": "strong",     "inheritance": "AR", "source": "OMIM #613794" }
      ],
      "publications_callout": {
        "total_count": 816,
        "scholar_url": "https://scholar.google.com/scholar?q=RPE65+c.260A%3EG",
        "ai_summary_prompt": "Summarise the key publications on RPE65 c.260A>G in plain language for a clinician."
      }
    }
  }
}
```

**In `lookup_service.py`**, after the existing `ReportPayload` is built, load this fixture keyed by `(gene, cdna)` and attach the six new fields. If no fixture entry matches, leave them as `None` / empty list.

**Verify**:

```bash
cd app/backend
python -m pytest tests/test_frontend_contract.py -q
# All seven existing parametrised cases pass. (Claude Code will extend this test for the new fields.)

curl -X POST http://localhost:8000/api/v1/lookup \
  -H "Content-Type: application/json" \
  -d '{"gene":"RPE65","cdna":"c.260A>G"}' | jq .report_payload.locus_context
# Should return the locus_context object with 5 nearby variants and 11 codon cells.
```

## BE-3 — Lookup-scoped chat endpoint

The existing endpoint `POST /api/v1/runs/{run_id}/chat/stream` is scoped to a run. The new endpoint is scoped to a lookup result (or Workbench session) — no run required.

**Create `app/backend/app/api/routes/chat.py`**:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    service = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable.",
        )
    return service.respond(payload)


@router.post("/stream")
def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    service = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable.",
        )
    return StreamingResponse(service.respond_stream(payload), media_type="text/plain")
```

**Extend `app/backend/app/schemas/chat.py`** — add request/response models for the new endpoint:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.run import ReportPayload


WorkbenchTool = Literal["viewer", "primer", "crispr", "align", "compare"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class WorkbenchEdit(BaseModel):
    position: int                      # codon offset
    ref_base: Literal["A", "T", "C", "G"]
    new_base: Literal["A", "T", "C", "G", "del"]
    consequence: str                   # "Missense p.Asp87Gly" / "Frameshift" / etc.


class WorkbenchContext(BaseModel):
    active_tool: WorkbenchTool
    scratchpad: list[WorkbenchEdit] = Field(default_factory=list)
    selected_primer_pair: int | None = None
    selected_guide: int | None = None


class ChatRequest(BaseModel):
    question: str
    variant_context: ReportPayload
    history: list[ChatMessage] = Field(default_factory=list)
    workbench: WorkbenchContext | None = None


class ChatResponse(BaseModel):
    answer: str
```

**Register the router** in `app/backend/app/main.py` — add `app.include_router(chat.router)` next to the other route registrations.

**Wire `chat_service`** in `app/main.py:create_app` — instantiate a `ChatService` and attach as `app.state.chat_service`. Reuse the existing chat logic if there's a service; otherwise create a thin wrapper:

```python
# app/backend/app/services/chat_service.py
class ChatService:
    def __init__(self, settings, llm_client):
        self.settings = settings
        self.llm = llm_client

    def respond(self, payload: ChatRequest) -> ChatResponse:
        # Mock: echo the question with variant context
        if self.settings.llm_provider == "mock":
            return ChatResponse(answer=self._mock_answer(payload))
        # Live: call LLM with system prompt extended for workbench context
        return ChatResponse(answer=self.llm.complete(self._build_prompt(payload)))

    def respond_stream(self, payload: ChatRequest):
        text = self.respond(payload).answer
        for word in text.split():
            yield word + " "

    def _mock_answer(self, payload: ChatRequest) -> str:
        gene = payload.variant_context.variant_summary_rows[0].gene if payload.variant_context.variant_summary_rows else "this variant"
        tool = payload.workbench.active_tool if payload.workbench else "lookup"
        return f"[mock] Asked about {gene} in {tool} mode: {payload.question}"

    def _build_prompt(self, payload: ChatRequest) -> str:
        base = "You are Eamos, a genomic evidence assistant. Cite source databases with bracket tags like [CV] [gn] [SA] [AM] [RV] [OM] [CT] [UP] [PP]. Never provide diagnoses."
        if payload.workbench:
            wb = payload.workbench
            base += f"\nWorkbench context: active tool = {wb.active_tool}. Scratchpad has {len(wb.scratchpad)} edits."
        return f"{base}\n\nQuestion: {payload.question}"
```

**Verify**:

```bash
cd app/backend
python -m pytest tests/ -q
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Is this pathogenic?","variant_context":{"patient_id":"demo","variant_summary_rows":[{"gene":"RPE65"}]}}'
# Returns ChatResponse with mocked answer mentioning RPE65.
```

## BE-4 — Workbench engine stubs

Three endpoints returning canned data shaped like the responses from the v2 sample data. Real engines (Primer3 / CRISPOR / Needleman–Wunsch / AB1 parser) are M-002.

**Create `app/backend/app/api/routes/workbench.py`**:

```python
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from app.schemas.workbench import (
    PrimerRequest, PrimerResponse,
    CrisprRequest, CrisprResponse,
    AlignRequest, AlignResponse,
)

router = APIRouter(prefix="/api/v1", tags=["workbench"])

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "workbench"


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


@router.post("/primer", response_model=PrimerResponse)
def design_primers(payload: PrimerRequest) -> PrimerResponse:
    return PrimerResponse(**_load("primer_rpe65.json"))


@router.post("/crispr", response_model=CrisprResponse)
def design_guides(payload: CrisprRequest) -> CrisprResponse:
    return CrisprResponse(**_load("crispr_rpe65.json"))


@router.post("/align", response_model=AlignResponse)
def align(payload: AlignRequest) -> AlignResponse:
    return AlignResponse(**_load("align_rpe65.json"))
```

**Create `app/backend/app/schemas/workbench.py`** with the request/response models. Match the field names in `e:\Web tool\Claude Design\Workbench\primer.js`, `crispr.js`, `alignment.js`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ─────────── Primer ───────────

PrimerMode = Literal["sanger", "qpcr", "arms"]


class PrimerRequest(BaseModel):
    gene: str
    cdna: str
    mode: PrimerMode = "sanger"
    tm_min: float = 58.0
    tm_max: float = 62.0
    product_size_min: int = 300
    product_size_max: int = 700
    avoid_snps: bool = True


class PrimerPair(BaseModel):
    index: int
    forward: str
    reverse: str
    tm_forward: float
    tm_reverse: float
    gc_forward: float
    gc_reverse: float
    product_size: int
    specificity_hits: int
    notes: str = ""
    recommended: bool = False


class PrimerResponse(BaseModel):
    mode: PrimerMode
    pairs: list[PrimerPair] = Field(default_factory=list)


# ─────────── CRISPR ───────────

CasEnzyme = Literal["SpCas9", "SaCas9", "Cas12a"]


class CrisprRequest(BaseModel):
    gene: str
    cdna: str
    cas: CasEnzyme = "SpCas9"
    strand_filter: Literal["both", "plus", "minus"] = "both"
    off_target_tolerance: int = 3


class CrisprGuide(BaseModel):
    index: int
    cut_position: int                # absolute cdna position
    strand: Literal["+", "-"]
    guide: str                       # 20 nt
    pam: str                         # e.g. "AGG"
    on_target_score: float           # 0..1
    off_target_score: float          # 0..1
    gc_percent: float
    notes: str = ""


class HdrSsodn(BaseModel):
    reference_arm: str
    variant_arm: str
    repair_template: str
    edits_encoded: list[str] = Field(default_factory=list)
    arm_lengths: dict[str, int] = Field(default_factory=dict)
    estimated_hdr_efficiency: float


class CrisprResponse(BaseModel):
    cas: CasEnzyme
    guides: list[CrisprGuide] = Field(default_factory=list)
    ssodn: HdrSsodn | None = None


# ─────────── Alignment ───────────

class AlignRequest(BaseModel):
    gene: str
    cdna: str
    user_sequence: str | None = None
    ab1_blob_base64: str | None = None


class TraceChannel(BaseModel):
    base: Literal["A", "T", "C", "G"]
    values: list[float]              # 0..1 normalised channel signal per sample


class AlignResponse(BaseModel):
    reference: str
    sanger_read: str
    match_line: str                  # "|" at matches, " " at mismatches
    mismatch_positions: list[int] = Field(default_factory=list)
    target_position: int
    trace_channels: list[TraceChannel] = Field(default_factory=list)
    base_calls: list[str] = Field(default_factory=list)
    q_scores: list[int] = Field(default_factory=list)
```

**Create fixture files** in `app/backend/app/fixtures/workbench/`:

- `primer_rpe65.json` — at least one ★ recommended pair + 2 alternates, RPE65 c.260 region. Borrow numerics from `e:\Web tool\Claude Design\Workbench\primer.js` (the sample data block at the top of that file).
- `crispr_rpe65.json` — 3 gRNAs + ssODN block. Borrow from `crispr.js`.
- `align_rpe65.json` — reference + Sanger read (1 mismatch at target), 4 trace channels (~80 samples each), base calls, Q-scores. Borrow from `alignment.js`. Keep arrays compact — ~80 samples is enough for the chromatogram to render correctly.

**Register the router** in `app/main.py`.

**Verify**:

```bash
cd app/backend
python -m pytest tests/ -q
curl -X POST http://localhost:8000/api/v1/primer  -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}' | jq .
curl -X POST http://localhost:8000/api/v1/crispr  -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}' | jq .
curl -X POST http://localhost:8000/api/v1/align   -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}' | jq .
# Each returns the corresponding fixture.
```

## BE-5 — Test sweep

**Add `app/backend/tests/test_franklin_removed.py`**:

```python
"""Smoke test that Franklin is fully archived."""
import importlib
import pkgutil
from pathlib import Path

import pytest

import app

APP_ROOT = Path(app.__file__).parent


def test_franklin_module_does_not_exist():
    franklin_path = APP_ROOT / "tools" / "franklin.py"
    assert not franklin_path.exists(), "Franklin tool should be archived, not active."


def test_franklin_fixture_does_not_exist():
    fixture_path = APP_ROOT / "fixtures" / "tools" / "franklin_fixtures.json"
    assert not fixture_path.exists(), "Franklin fixture should be archived, not active."


def test_no_franklin_imports():
    """No module under app/ should import franklin."""
    leaks = []
    for module_info in pkgutil.walk_packages([str(APP_ROOT)], prefix="app."):
        module = importlib.import_module(module_info.name)
        source_path = getattr(module, "__file__", None)
        if not source_path:
            continue
        text = Path(source_path).read_text(encoding="utf-8")
        if "franklin" in text.lower():
            leaks.append(module_info.name)
    assert not leaks, f"Franklin references leaked into: {leaks}"
```

**Extend `app/backend/tests/test_frontend_contract.py`** — the existing parametrized test asserts every Pydantic field has a TS counterpart. Add cases for the six new `ReportPayload` fields and the new schemas (`LocusContext`, `NearbyVariant`, `CodonCell`, `InSilicoPredictions`, `PredictorCard`, `AcmgCriterion`, `AcmgCriteriaScaffold`, `CuratedVariantsDistribution`, `AssociatedCondition`, `PublicationsCallout`, `ChatRequest`, `ChatResponse`, `ChatMessage`, `WorkbenchContext`, `WorkbenchEdit`, `PrimerRequest`, `PrimerResponse`, `PrimerPair`, `CrisprRequest`, `CrisprResponse`, `CrisprGuide`, `HdrSsodn`, `AlignRequest`, `AlignResponse`, `TraceChannel`).

(Claude Code will land the TS interfaces on the frontend side — this test will fail until both halves are in place. That's the desired sync point.)

**Final verify**:

```bash
cd app/backend
python -m pytest tests/ -q
# All tests pass except potentially test_frontend_contract.py, which waits on frontend.

grep -ri "franklin" app/ tests/        # should be empty
```

## BE-6 — Report v2 payload mock-fidelity

**Problem.** FE-3.5 wired the six report v2 components to `payload.*`, but Codex's `lookup_v2_modules.json` fixture carries less than the **Report Page v2** mock shows. The components still embed richer `SAMPLE` blocks (ported from the mock) as prop fallbacks, so payload-driven rendering visually regresses vs the mock. Close the gap so the live payload is mock-faithful and the frontend can delete the lossy fallbacks (FE-3.6).

**Fidelity source of truth.** The `SAMPLE` / default constants currently in these six frontend files ARE the mock-faithful values. Read them and mirror their content into the fixture:

| File | Constants to mirror |
| ---- | ------------------- |
| `app/frontend/src/components/report/LocusContext.tsx` | `SAMPLE_NEARBY` (11 variants), `SAMPLE_CODONS` (11 codons w/ DNA + `Asp → Gly`), the `coords` default string |
| `app/frontend/src/components/report/InSilicoGrid.tsx` | `SAMPLE_CARDS` (per-card descriptive verdict text), `SAMPLE_CONSENSUS` |
| `app/frontend/src/components/report/AcmgCriteriaFold.tsx` | `SAMPLE_INTRO`, `SAMPLE_NOTE` |
| `app/frontend/src/components/report/CuratedVariantsGrid.tsx` | `SAMPLE_ROWS` counts (210/187/6/3 …), `sub` default, `SAMPLE_READING` |
| `app/frontend/src/components/report/AssociatedConditions.tsx` | `SAMPLE` (5 conditions w/ split `metaTag`/`src`), `sub` default |
| `app/frontend/src/components/report/PublicationsCallout.tsx` | `DEFAULT_BLURB` |

**Schema changes** (`app/backend/app/schemas/run.py`) — additive only; do not rename or drop existing fields (the `test_frontend_contract.py` canary depends on every field having a TS twin):

```python
class CodonCell(BaseModel):
    codon_number: int
    aa_ref: str                      # 1-letter, UNCHANGED (existing contract)
    aa_alt: str | None = None        # 1-letter alt for the query codon, e.g. "G" (Gly)
    dna_ref: str = ""                # reference codon triplet, e.g. "GAC"
    dna_alt: str | None = None       # variant codon triplet for query, e.g. "GGC"
    is_query: bool = False

class NearbyVariant(BaseModel):
    cds_pos: int
    classification: ClassificationTier
    hgvs: str
    clinvar_id: str | None = None
    protein_change: str | None = None   # e.g. "p.Asp79Gly" — for the dot tooltip title

class LocusContext(BaseModel):
    gene: str
    centre_cdna: str
    coords: str = ""                 # "chr1 : 68,444,849 — 68,444,889  ·  RPE65 exon 4  ·  (+) strand"
    nearby_variants: list[NearbyVariant] = Field(default_factory=list)  # 11, matching SAMPLE_NEARBY
    codon_strip: list[CodonCell] = Field(default_factory=list)          # 11, matching SAMPLE_CODONS

class PredictorCard(BaseModel):
    name: Literal["REVEL", "AlphaMissense", "MetaLR", "SpliceAI"]
    score: float
    threshold: float
    verdict: PredictorVerdict
    verdict_label: str = ""          # descriptive, e.g. "Pathogenic supporting" / "No splice impact"
    source_url: str | None = None

class AcmgCriteriaScaffold(BaseModel):
    criteria: list[AcmgCriterion] = Field(default_factory=list)
    intro: str = ""                  # SAMPLE_INTRO prose
    note: str = ""                   # SAMPLE_NOTE prose
    disclaimer: str = "Supporting evidence, not classification."

class CuratedVariantsDistribution(BaseModel):
    cells: dict[str, int] = Field(default_factory=dict)   # mirror SAMPLE_ROWS counts
    row_totals: dict[str, int] = Field(default_factory=dict)  # {"pathogenic":406,"vus":426,"benign":454}
    total: int
    subtitle: str = ""               # "1,286 classified variants · ClinVar + UniProt"
    reading: str

class AssociatedCondition(BaseModel):
    name: str
    case_count: int
    evidence_level: Literal["definitive", "strong", "moderate", "limited"]
    inheritance: Literal["AR", "AD", "XL", "MT"]
    db_tag: str                      # "#204100" / "No OMIM entry" / "Orphanet ORPHA:71862"
    db_tag_bold: str | None = None   # "OMIM" (rendered bold) — None when no DB prefix
    source_list: str                 # "OMIM · Monarch · DECIPHER · GenCC · ClinGen"

class PublicationsCallout(BaseModel):
    total_count: int
    scholar_url: str
    blurb: str = ""                  # DEFAULT_BLURB descriptive sentence
    ai_summary_prompt: str
```

`ReportPayload` keeps `associated_conditions: list[AssociatedCondition]`. The list subtitle ("5 conditions · …") stays a frontend-static string — not a backend field.

**Fixture.** Rewrite `app/backend/app/fixtures/lookup_v2_modules.json` for `RPE65 / c.260A>G` so every value equals the mirrored SAMPLE constants:
- `codon_strip`: 11 codons 82–92 with correct `aa_ref` (Y,R,E,P,V,D,K,T,V,A,I → matching SAMPLE_CODONS), `dna_ref` triplets (TAT,CGG,GAA,CCT,GTG,GAC,AAG,ACA,GTC,GCC,ATT), query codon 87 `aa_alt="G"`, `dna_alt="GGC"`, `is_query=true`.
- `nearby_variants`: 11 entries; query at `cds_pos=0`; classifications + hgvs + protein_change mirroring SAMPLE_NEARBY's 11 titles. Spread `cds_pos` so the frontend mapping (`left = 50 + cds_pos/span*50`) lands dots at a visually equivalent density.
- predictor `verdict_label`, ACMG `intro`/`note`, distribution `row_totals`/`subtitle`, condition `db_tag`/`source_list` (5 conditions), publications `blurb` — all from the SAMPLE constants.

**Tests.** Extend `app/backend/tests/test_frontend_contract.py` with the new fields (`aa_alt`, `dna_ref`, `dna_alt`, `coords`, `protein_change`, `verdict_label`, `intro`, `note`, `row_totals`, `subtitle`, `db_tag`, `db_tag_bold`, `source_list`, `blurb`). It will fail until FE-3.6 lands the matching TS — that is the planned sync point.

**Verify**:

```bash
cd app/backend && python -m pytest tests/ -q
curl -X POST http://localhost:8000/api/v1/lookup -H "Content-Type: application/json" \
  -d '{"gene":"RPE65","cdna":"c.260A>G"}' | jq '.report_payload.locus_context.codon_strip[5]'
# codon 87: aa_ref "D", aa_alt "G", dna_ref "GAC", dna_alt "GGC", is_query true
```

## BE-7 — Workbench fixture fidelity

BE-4 created `app/backend/app/fixtures/workbench/{primer,crispr,align}_rpe65.json` by "borrowing numerics" from the Workbench mock JS. Tighten them to exact mock fidelity so FE-6/FE-7 render identically to **Eamos Workbench v1**.

- Read `e:\Web tool\Claude Design\Workbench\primer.js`, `crispr.js`, `alignment.js` sample-data blocks.
- Make each fixture an exact transcription: same primer pairs/Tm/GC/product sizes (★ pair flagged), same 3 gRNAs + ssODN arms/efficiency, same ~80-sample 4-channel trace + base calls + Q-scores + the single target mismatch.
- No schema changes expected (BE-4 models stand). If a mock field has no schema slot, surface it — don't silently drop.

**Verify**: `pytest tests/ -q`, then `curl` each endpoint and diff key fields against the mock JS.

---

# Variant-search-engine integration (BE-8 … BE-13)

Source plan: `C:\Users\seamegdool\.claude\plans\before-you-beging-the-groovy-swan.md`.
Adapts the external `variant-search-engine` design's **concepts** (input cleaning,
LitVar2 publications, VariantValidator strict coords, an expandable strict-genomic
plugin loop, a persistent cache) into Eamos's FastAPI tool-registry + React report
page. The external standalone `server.py`/`dashboard.html` are **not** added
verbatim. Incoherence pass (2026-05-16) ground-truthed every "Eamos reality"
claim below against live code — all confirmed.

**Ownership for this batch:** Codex owns BE-8…BE-13 (`app/backend/**` only).
Claude Code owns FE-14 + the BE-12 frontend half (`app/frontend/**` only). The
only soft-coupling point is the **frozen `warnings` codes** in BE-12 — both sides
build to those exact strings, no wait. Dependency order: **BE-8 → BE-9 → BE-10 →
BE-11 → BE-12 → BE-13**. BE-9 is the linchpin; BE-11 is independent of BE-9/10
(parallelizable); BE-13 depends on BE-8 (key) + BE-9/10/11 (what it caches).

**Watch-outs (do not relearn):** `use_real_apis` is global, default stays
`False`, opt-in via env only. Never `lower()` HGVS (`A>G` / `p.Asp87Gly` are
case-significant). VEP does **not** set `genomic_hg38` (stays `""` from
`lookup_service.py:86`). New tools must **never raise** — always self-fallback to
fixture, mirroring `pubmed.py`/`gnomad.py`. BE-11 is deliberately zero-schema so
the contract test cannot break and there is no irreversible
`backend.ts`/`sample-report.ts` migration — keep it that way.

## BE-8 — Input normalization

Pasted Franklin-style input like `RPE65:c.260A>G` currently becomes a malformed
`transcript_hgvs`. Add a single normalization function and wire it at both
species callsites.

**New** — `normalize_variant_query(gene, cdna, transcript) -> (gene, hgvs, transcript, kind)`
top-level in `app/backend/app/services/lookup_service.py`. Rules:
`gene.strip().upper()`; strip a leading `GENE:` or `NM_/ENST` accession+colon
from `cdna`; collapse internal whitespace; **preserve HGVS case** (the external
`lower()` rule is explicitly rejected — `A>G`/`p.Asp87Gly` are case-significant);
classify `kind ∈ {cdna, rsid, protein, genomic, unknown}`.

**Wire** — replace the inline logic at `lookup_service.py:62-63` (mouse) and
`:77-79` (human) with calls to `normalize_variant_query`. (Frontend mirror
`cleanQuery()` in `app/frontend/src/lib/variant-format.ts` is FE-14 — Claude
Code's, not Codex's.)

**Verify**:

```bash
cd app/backend && python -m pytest tests/test_lookup_normalize.py -q
curl -X POST http://localhost:8000/api/v1/lookup -H "Content-Type: application/json" \
  -d '{"gene":"RPE65","cdna":"RPE65:c.260A>G"}'
curl -X POST http://localhost:8000/api/v1/lookup -H "Content-Type: application/json" \
  -d '{"gene":"RPE65","cdna":"c.260A>G"}'
# Both produce an identical transcript_hgvs.
```

## BE-9 — VariantValidator coords-resolver tool (the linchpin)

`ensembl_vep.py._fetch_live` never sets `variant.genomic_hg38` (confirmed: stays
`""` from `lookup_service.py:86`), so gnomAD degrades to `live_stub`
(`gnomad.py:80-94`). This tool resolves strict VCF coords and mutates the shared
variant so the strict-genomic plugins can run.

**New** — `app/backend/app/tools/variant_validator.py`: `source="variant_validator"`,
`fixture_name="variant_validator_fixtures.json"`, subclass `FixtureBackedTool`,
**exact same** `use_real_apis`/try/except-fallback shape as `pubmed.py`
(`if not use_real_apis or variant is None → fixture`; `try _fetch_live except
Exception → status="fallback"` + `live_fetch_failed:<ExceptionName>` warning).
Live: `GET {variant_validator_base_url}/VariantValidator/variantvalidator/GRCh38/{gene}:{hgvs}/all`
→ parse `primary_assembly_loci.grch38.vcf` → `{chr,pos,ref,alt}`. **Mutates**
`variant.genomic_hg38 = f"{chr}-{pos}-{ref}-{alt}"` (+ `variation_type` /
`consequence` only if blank). Secondary fallback: derive coords from the existing
VEP `raw` payload before giving up. **Never raises.**

**Config** — add `variant_validator_base_url: str = "https://rest.variantvalidator.org"`
to `app/backend/app/core/config.py` next to `clinvar_base_url` (line 42).

**Fixture** — `app/backend/app/fixtures/tools/variant_validator_fixtures.json`:
real GRCh38 VCF for RPE65 c.260A>G captured from a live smoke run (do **not**
invent the coordinates).

**Docs** — when this tool lands, add a `variant_validator` row to the tool tables
in `README.md` (~line 130) and `app/backend/README.md` (~line 56) and the
`app/backend/app/tools/CLAUDE.md` index. (Per `plans/README.md` rule #3, the
milestone-shipper updates the shared docs after the code change.)

**Verify**:

```bash
$env:USE_REAL_APIS="true"; curl -X POST http://localhost:8000/api/v1/lookup \
  -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}'
# report_payload.variant_summary_rows[0].genomic_hg38 populated.
# Offline (USE_REAL_APIS unset): fixture coords returned, no raise.
```

## BE-10 — Explicit strict-genomic plugin loop

Make the resolve→plugin→annotate ordering explicit so adding a future
coords-keyed DB is one tuple entry, zero `lookup_service` change.

**New** — `STRICT_GENOMIC_PLUGINS = ("gnomad", "spliceai")` in
`app/backend/app/tools/registry.py` + a contract docstring: "a
`FixtureBackedTool` whose `get_evidence` reads `variant.genomic_hg38`, degrading
to `live_stub` if absent" — gnomAD already models exactly this
(`gnomad.py:80-94`).

**Refactor** — the `for name in ('vep','spliceai','clinvar','gnomad','pubmed')`
loop at `lookup_service.py:110` into 3 documented phases with the **same**
`evidence`/`evidence_map`/`evidence_statuses` accumulation (no behaviour change
for existing tools): (1) **resolve** = `vep` → `variant_validator`; (2) iterate
`STRICT_GENOMIC_PLUGINS`; (3) **annotate** = `clinvar`, `pubmed`, `litvar2`.
Document that phases 1-2 mutate the shared `SimpleNamespace` variant (the risk
the explicit phases mitigate).

**Verify**:

```bash
$env:USE_REAL_APIS="true"; curl -X POST http://localhost:8000/api/v1/lookup \
  -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}'
# gnomAD evidence status == "live" (was "live_stub" before BE-9/BE-10).
cd app/backend && python -m pytest tests/ -q   # 40/40 unchanged
```

## BE-11 — LitVar2 tool + Publications accuracy

The Publications section is currently 100% static fixture
(`lookup_v2_modules.json → publications_callout`). LitVar2 *complements*
PubMed (variant-precise count/IDs) — it does **not** replace `pubmed.py`, whose
URLs are already correct (`https://pubmed.ncbi.nlm.nih.gov/{pmid}/`,
`pubmed.py:113`).

**New** — `app/backend/app/tools/litvar2.py`: `source="litvar2"`,
`fixture_name="litvar2_fixtures.json"`, same FixtureBackedTool shape. Live:
`{litvar2_base_url}/variant/autocomplete/?query={gene} {hgvs}` → `litvar_id`,
then `{litvar2_base_url}/variant/get/{litvar_id}/publications` → PMIDs/count.
`summary = {litvar_id, total_publications, articles:[{pmid, title,
url=https://pubmed.ncbi.nlm.nih.gov/{pmid}/}], scholar_url}`. Register in
`build_tool_registry`; add `litvar2_base_url: str = "https://www.ncbi.nlm.nih.gov/research/litvar2-api"`
to `config.py`; add `litvar2_fixtures.json` with an RPE65 sample.

**Publications wiring** in `lookup_service.py` *after* `base_payload` is built
(reassign, mirroring the `draft_render` field reassignment at lines 233-237 —
the `**_lookup_v2_modules` spread at line 219 sets the fixture default, explicit
reassignment overrides it): `publications_callout.total_count` = LitVar2 live
count else `len(pubmed_articles)`; `scholar_url` = LitVar2 else URL-encoded
Scholar query; `blurb` = composed sentence (fixture blurb as fallback); merge
LitVar2 PMIDs into `pubmed_articles` (union by `pmid`, dedupe, normalize URL).

**Schema — ZERO changes.** `PublicationsCallout`/`PubMedArticle` already
suffice. `backend.ts`/`sample-report.ts`/`test_frontend_contract.py` untouched
(stays 40/40). Deliberate: no irreversible migration. Keep it this way.

**Docs** — when this tool lands, add a `litvar2` row to the tool tables in
`README.md` + `app/backend/README.md` + `app/backend/app/tools/CLAUDE.md`
(per `plans/README.md` rule #3).

**Verify**:

```bash
$env:USE_REAL_APIS="true"; curl -X POST http://localhost:8000/api/v1/lookup \
  -H "Content-Type: application/json" -d '{"gene":"RPE65","cdna":"c.260A>G"}'
# .report_payload.publications_callout.total_count is real;
# every merged article url == https://pubmed.ncbi.nlm.nih.gov/{pmid}/
cd app/backend && python -m pytest tests/test_frontend_contract.py -q   # 40/40
```

## BE-12 — Search robustness / error contract

Machine-readable warning codes; HTTP 200 is kept (no error-status change). The
codes are the **only** soft-coupling point with the frontend (FE-14) — they live
in the existing `LookupResponse.warnings: list[str]` field, **not** a schema
change.

### Frozen `warnings` codes — BE-12 ⇄ FE-14 contract

> **Do not change these strings without updating both `v2-backend.md` (Codex)
> and `v2-frontend.md`/FE-14 (Claude Code) in the same change.** Frozen
> 2026-05-16 in Step 0c so both sides build to the same constants with no wait.

| Code string | Backend emits when | FE-14 reaction |
| ----------- | ------------------ | -------------- |
| `input_unparseable:<kind>` | `normalize_variant_query` cannot classify the query. `<kind>` ∈ `{cdna,rsid,protein,genomic,unknown}`. Also set `report_payload.limitations` to a human sentence. | Inline malformed-input hint near the search box. No retry. (Client-side `classify()==unknown` short-circuits *before* the request — this code covers the server-confirmed case.) |
| `no_genomic_resolution` | Every coords resolver failed (VEP → VariantValidator → VEP-`raw` fallback all gave nothing). | "We couldn't resolve this variant" panel — visually **distinct** from a generic network failure. No auto-retry. |
| `live_fetch_failed:<ExceptionName>` | A tool's live call raised and it fell back to fixture. **This is the existing shape** already emitted by `pubmed.py:41` / `gnomad.py:64` — the suffix is `type(exc).__name__` (e.g. `live_fetch_failed:ConnectError`), the **exception class name, NOT the tool name**. (Incoherence finding #6, 2026-05-16: the source plan wrote `live_fetch_failed:<Tool>`; the real contract is `<ExceptionName>`.) | Treat as transient → show a retry affordance. FE-14 keys on the `live_fetch_failed:` **prefix only**; it must never parse or branch on the suffix. |

**Backend** — emit `input_unparseable:<kind>` + populate `report_payload.limitations`
on unparseable input; emit `no_genomic_resolution` when all resolvers fail; leave
the existing `live_fetch_failed:<ExceptionName>` path as-is (do not rename it to
match the source plan's `<Tool>` notation — the frozen contract above is the real
one). All transient failures keep HTTP 200 + `status="fallback"`.

**Verify**:

```bash
cd app/backend && python -m pytest tests/ -q   # 40/40 unchanged (no schema change)
curl -X POST http://localhost:8000/api/v1/lookup -H "Content-Type: application/json" \
  -d '{"gene":"RPE65","cdna":"???not-a-variant???"}'
# warnings contains input_unparseable:<kind>; report_payload.limitations populated.
```

## BE-13 — Persistent variant cache (build now, on Eamos's DB)

Build the 30-day cache on Eamos's **existing** SQLAlchemy `database_url` — **not**
a separate `variant_universal_cache.db`.

**New** — `app/backend/app/repos/variant_cache_repo.py` following the existing
`*_repo.py` pattern (`reports_repo.py`/`search_repo.py`), using the engine/session
from `app/core/db.py` + `settings.database_url`. Table `variant_cache(query_string
UNIQUE, litvar_id, total_publications, publication_data JSON-text,
strict_genomic_cache JSON-text, created_at)`; create on startup the same way
other repos' tables are created.

**Config** — `cache_ttl_days: int = 30` in `config.py`.

**Wrap** `lookup_service.lookup`: after BE-8 normalization, key = normalized
query string. **Cache active only when `use_real_apis` is true** (fixtures are
deterministic/fast; caching them would mask fixture edits). Fresh hit
(`age < cache_ttl_days`) → hydrate resolved coords + LitVar2 publications +
strict-genomic plugin evidence from cache, skip the live resolve+plugin calls.
Miss/expired → run the phases, then write cache. Provide a cache-bypass
(`?refresh=1` on the route or a request flag) and clean expired rows on read.

**Verify**:

```bash
cd app/backend && python -m pytest tests/test_variant_cache.py -q   # hit/miss/expiry
$env:USE_REAL_APIS="true"
# two consecutive identical live curls — the 2nd is served from cache
# (assert via a source marker / log line).
```

## BE-8…BE-13 end-to-end verification

```powershell
cd app/backend; python -m pytest tests/ -q                          # 40/40 stays green
$env:HSIL_RUN_LIVE_API_SMOKE="1"; python -m pytest tests/test_real_agent_smoke.py -q
# Manual, real APIs (opt-in):
$env:USE_REAL_APIS="true"; python -m uvicorn app.main:create_app --factory
curl -X POST http://localhost:8000/api/v1/lookup -H "Content-Type: application/json" -d '{\"gene\":\"RPE65\",\"cdna\":\"RPE65:c.260A>G\"}'
# expect: genomic_hg38 populated; gnomad status "live"; publications_callout.total_count real;
#         article urls = pubmed.ncbi.nlm.nih.gov/{pmid}/; 2nd identical call served from cache
```

---

## Out of scope (M-002 follow-ups)

- Real Primer3 invocation (replace BE-4 stub)
- Real CRISPOR invocation
- Real Needleman–Wunsch + biopython AB1 parsing
- Live `/api/v1/chat` calls to Anthropic / OpenAI (mock-mode only for v2)
- Live data feeds for the six new `ReportPayload` fields (fixtures for v2)
- Mouse mm39 paths for `/api/v1/primer`, `/crispr`, `/align`

---

## Working style for Codex

- Touch only the files listed per milestone. Don't refactor adjacent code.
- Match existing patterns: fixture-backed tools subclass `FixtureBackedTool` in `app/tools/base.py`; services live in `app/services/`; routes register via `app.include_router(...)` in `app/main.py`.
- Don't add error handling for impossible scenarios. Trust internal callers.
- Don't add backward-compatibility shims for Franklin (the user explicitly wants it removed).
- Stop after each milestone for a sync check. Report what you changed + the test command output.
- If you hit ambiguity, surface it — don't pick silently. The frontend plan and shared contract are the tie-breakers.

---

## Review Packet: Post-v2 Backend/API/Pipeline Planning

Section edited: 2026-05-17 18:19 +1000 · Codex

Status: M-002A implementation complete after user approval. Do not start
M-002B, FE-6/FE-7/FE-8, or any later M-002 execution until the user explicitly
approves the next backend task.

This packet applies the Blueprint flow in one reviewable place:

1. Design doc: choose the backend architecture and tradeoffs.
2. Spec: pin requirements, invariants, error behavior, and tests.
3. Plan: split the future implementation into independently reviewable tasks.

### Design Doc: M-002 Candidate Backend Real-Mode Layer

**Summary.** The v2 backend now exposes lookup, lookup-scoped chat, Workbench
stub endpoints, real API lookup enrichment, frozen warning codes, and a guarded
variant cache. The next backend phase should turn selected fixture-backed paths
into explicit real-mode providers without changing default demo behavior:
`USE_REAL_APIS=false` and `LLM_PROVIDER=mock` must stay deterministic, fast,
and safe.

**Context and Scope.** Current real-mode lookup already uses the existing tool
registry pattern for VEP, VariantValidator, gnomAD, SpliceAI, ClinVar, PubMed,
LitVar2, ClinicalTrials, and `variant_cache_repo.py`. The Workbench routes
`POST /api/v1/primer`, `/crispr`, and `/align` still return static fixture JSON
from `app/backend/app/api/routes/workbench.py`. Lookup-scoped chat exists at
`POST /api/v1/chat` but the live path is not production-shaped yet: the service
currently calls `self.llm.complete(...)`, while the existing LangChain wrappers
under `app/backend/app/agents/client.py` expose `invoke(...)` style adapters.
The six report v2 modules are loaded from
`app/backend/app/fixtures/lookup_v2_modules.json`; live hydration for those
modules remains future work.

This planning packet covers backend architecture for:

- real Workbench engine providers for primer, CRISPR, and alignment;
- a shared sequence-context provider needed by those engines;
- live lookup-module hydration where current public evidence can support it;
- live lookup/Workbench chat through a grounded LLM adapter;
- verification and safety gates.

**Goals.**

- Preserve the current public API contracts unless a later reviewed task
  explicitly makes an additive schema change and updates
  `test_frontend_contract.py`.
- Keep mock/fixture behavior as the default and as the offline test oracle.
- Introduce real providers behind service boundaries, not directly in route
  handlers.
- Never fabricate genomic, publication, ACMG, or design-tool results when a
  live source cannot support them; return fixture/mocked output only when the
  mode explicitly calls for fixture behavior.
- Keep clinical language guarded: supporting information only, no diagnosis or
  formal classification assignment.
- Make each future implementation task small enough to verify and roll back.

**Non-Goals.**

- No implementation in this session.
- No frontend FE-6/FE-7/FE-8 work.
- No broad schema migration, UI contract rewrite, or non-additive response
  changes.
- No production clinical validation claim.
- No attempt to fully solve off-target scoring, ACMG classification, OMIM/
  Monarch/DECIPHER licensing, or transcript/build coverage in one task.

**Constraints.**

- Default runtime remains `USE_REAL_APIS=false` / `LLM_PROVIDER=mock`.
- Current contract canary remains
  `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`.
- Shared warning strings from BE-12 are frozen unless both backend and frontend
  plans are updated in the same reviewed change.
- The existing `FixtureBackedTool` and `ToolResult` shape is the preferred
  pattern for live-data tools.
- Workbench real engines need sequence context that the current routes do not
  compute. A sequence-context layer is therefore a prerequisite, not optional
  plumbing.
- Any new third-party dependency or hosted service must be reviewed against
  license, offline-test strategy, failure mode, and Windows local-dev support
  before it is added.

**Proposed Design.**

Add a backend-only real-mode layer in four boundaries:

1. `SequenceContextService`: resolves `gene` + `cdna` + optional transcript/
   species into a validated sequence window, transcript HGVS, GRCh38 coordinate,
   reference/alternate base, codon context, strand, and source metadata. Fixture
   mode serves the known RPE65 context. Real mode reuses the existing
   normalization and resolver chain before fetching sequence context from an
   approved provider. If sequence context cannot be resolved, fixture mode may
   serve the known RPE65 fixture, but real mode returns the explicit Workbench
   HTTP error contract below; it does not silently fall back to fixtures or
   invent sequence.
2. `WorkbenchDesignService`: route handlers delegate primer, CRISPR, and
   alignment requests to provider interfaces. The current JSON fixtures become
   the fixture provider. Real providers are plugged in one at a time. The
   service owns an internal provider-status/result type; routes translate
   real-mode failures into structured HTTP errors until a reviewed additive
   response metadata field exists.
3. `LookupModuleHydrator`: replaces the all-or-nothing fixture merge for the
   six report v2 modules with per-module builders. Each builder may use existing
   evidence (`clinvar`, `spliceai`, `gnomad`, `pubmed`, `litvar2`) plus sequence
   context; unsupported fields stay omitted or fixture-backed by explicit mode.
4. `LookupChatService`: use a provider adapter that matches the existing
   LangChain `invoke(...)` pattern, passes bounded grounded context, cites
   evidence sources, and preserves the mock answer path.

Suggested runtime flow:

```text
Workbench request
  -> normalize gene/cdna
  -> SequenceContextService
  -> WorkbenchDesignService
  -> fixture provider OR real provider
  -> existing Primer/Crispr/Align response models

Lookup request
  -> existing resolver/tool phases
  -> LookupModuleHydrator
  -> ReportPayload with module fields from live evidence where supported

Chat request
  -> bounded ReportPayload/evidence/workbench context
  -> mock response OR grounded LLM adapter
  -> ChatResponse / streaming text
```

**Interfaces and Data.**

- Keep `PrimerRequest`, `CrisprRequest`, `AlignRequest`, `PrimerResponse`,
  `CrisprResponse`, and `AlignResponse` stable for the first real-provider
  pass. If real engines need species/build/transcript knobs, add fields only
  after a reviewed contract update.
- Internal sequence-context data should be a Pydantic or dataclass model, but
  it should not become public API until frontend needs it.
- Do not add top-level `warnings` or `status` fields to `PrimerResponse`,
  `CrisprResponse`, or `AlignResponse` in M-002C/D/E. Those models currently
  have no metadata channel, and keeping them stable is the first-pass decision.
  Real-mode Workbench failures therefore use HTTP errors with a structured JSON
  `detail` object until a later reviewed frontend/backend contract adds
  response metadata.
- Freeze these Workbench error/warning codes before any frontend consumption:
  `workbench_sequence_context_unavailable`,
  `workbench_unsupported_input:<kind>`, `workbench_provider_unavailable`,
  `workbench_provider_failed:<ExceptionName>`, and
  `workbench_provider_malformed`. These live in HTTP error `detail.warnings`
  for the first real-provider pass, not in the success response schema.
- Cache only data that is source-backed and keyed by normalized query/build/
  transcript/provider version. Do not cache fixture outputs as live evidence.

**Alternatives Considered.**

- Put engine logic directly in `api/routes/workbench.py`: rejected because the
  current route handlers are intentionally thin and direct engine calls would
  mix HTTP, provider failure modes, and design logic.
- Add broad schema fields now for all future engine outputs: rejected because
  it creates frontend contract churn before real providers prove their output
  shape.
- Replace all fixture modules with live builders in one milestone: rejected
  because module data quality varies by source and some fields need licensed or
  curated datasets.
- Make live chat use the draft-render chain directly: rejected because
  chat needs a bounded Q&A adapter, not report-section rewriting.

**Tradeoffs.**

- Keeping public schemas stable slows some provider work but protects the
  concurrent frontend lane.
- A sequence-context prerequisite adds one task up front, but it prevents three
  separate engines from resolving coordinates and transcripts differently.
- Per-module lookup hydration is slower than a single fixture merge, but it
  makes provenance and missing-data behavior reviewable.
- Optional real providers keep demo mode reliable, but they require explicit
  live smoke tests and clear degraded behavior before user-facing trust.

**Cross-Cutting Concerns.**

- Reliability: every live provider must have fixture-mode tests plus live-smoke
  tests gated by environment variables.
- Safety: never present generated prose or tool outputs as final diagnosis or
  formal clinical classification.
- Privacy: lookup/Workbench chat should send only the minimum bounded context
  needed for the answer; patient-upload run chat remains separate.
- Observability: lookup provider status should stay visible through warnings/
  evidence summaries. Workbench provider failure status should be visible
  through structured HTTP error details until Workbench success responses gain
  an approved metadata channel. Cache hits must be distinguishable from live
  responses.
- Performance: sequence context and lookup-module hydration should reuse
  existing resolver/cache outputs where possible.
- Operations: new dependencies or external services need documented install
  steps, env vars, and offline fallbacks before merge.

**Rollout and Migration.**

Roll out as backend-only vertical slices. Each slice keeps fixture mode green,
adds or preserves targeted tests, and stops for review before the next slice.
Frontend integration should happen only after backend contracts are stable and
the user chooses the corresponding FE milestone.

**Open Questions for User Review.**

- Should M-002 prioritize real primer design first, or sequence-context plus
  alignment first to reduce engine risk?
- For CRISPR, is an external CRISPOR-backed workflow required, or is a local
  deterministic guide-enumeration/scoring provider acceptable as the first
  real-mode step?
- For sequence retrieval, should Eamos prefer hosted API lookup in dev or a
  local reference FASTA/index for repeatability?
- Should live lookup-module hydration stay limited to publicly source-backed
  fields until licensed/curated datasets are chosen?
- Should lookup/Workbench chat support OpenAI only for now via existing config,
  or should provider-neutral Anthropic/OpenAI support be designed before code?

**Decision.** Recommended direction: approve a backend-only M-002 planning
sequence, beginning with the sequence-context/provider boundary, then landing
real providers one at a time. Do not approve broad contract changes until an
individual provider needs them and the frontend owner is ready to sync.

### Spec: Backend Real-Mode Provider Layer

**What.** Build an optional real-mode backend layer that can replace selected
fixtures with source-backed results while preserving current offline behavior
and public contracts. The first implementation sequence should establish
shared sequence context, then move primer, CRISPR, alignment, lookup modules,
and lookup/Workbench chat behind explicit provider adapters.

**Requirements.**

- `USE_REAL_APIS=false` must continue to return the current fixture/mock
  outputs for lookup, Workbench engines, and chat.
- Workbench route handlers must delegate to services; they should not contain
  engine or provider logic.
- Real engine providers must depend on a shared sequence-context result rather
  than each resolving `gene`/`cdna` independently.
- Workbench provider failures in M-002C/D/E must use the explicit HTTP error
  contract in this spec because the current success response models have no
  top-level warning/status channel. They must not silently fabricate live
  results or hide behind fixture fallback when real mode is requested.
- Any public schema change must be additive, reflected in TypeScript, and
  verified by `test_frontend_contract.py`.
- Live chat must use a bounded prompt/context adapter and must keep the same
  safety posture as report drafting: grounded, cautious, source-aware, and no
  diagnosis.
- New dependencies or services must be reviewed and documented before merge;
  this planning pass does not pin new versions.

**Design.**

- Add `app/backend/app/services/sequence_context.py` in the future to own
  sequence-window resolution.
- Add `app/backend/app/services/workbench_design.py` in the future to own
  primer/CRISPR/alignment orchestration.
- Add provider modules under `app/backend/app/tools/` or
  `app/backend/app/services/` based on whether they behave like external
  evidence tools (`ToolResult`) or local deterministic engines.
- Refactor `app/backend/app/api/routes/workbench.py` to obtain the service from
  `request.app.state`, mirroring lookup/chat route style.
- Add a small Workbench service exception/result boundary so route handlers can
  map real-mode provider failures to `HTTPException` with structured `detail`
  fields while returning the existing response models on success.
- Add `LookupModuleHydrator` as a small service called after existing lookup
  evidence is collected and before `ReportPayload` is returned.
- Replace the lookup chat live path with an adapter compatible with the
  existing LangChain `invoke(...)` wrappers; keep the mock path unchanged and
  wire the adapter through `app/backend/app/main.py:create_app`, not only
  isolated service tests.

**Decisions.**

- Decision: keep public Workbench response models stable for the first real
  provider pass. Alternative: add rich provider metadata now. Rationale:
  protects frontend parallel work and lets real providers prove their output.
  Reversible: yes, via additive fields later.
- Decision: use structured HTTP errors for real-mode Workbench provider
  failures until response metadata is approved. Alternative: add additive
  `warnings`/`status` fields now. Rationale: closes failure visibility without
  changing the success contract mid-frontend work. Reversible: yes; later
  metadata can move the same codes into success responses.
- Decision: make sequence context the first implementation slice. Alternative:
  wire Primer3 directly from route input. Rationale: primer, CRISPR, alignment,
  and module hydration all need consistent transcript/build/sequence context.
  Reversible: partially; skipping it would create duplicated resolver logic.
- Decision: default all live providers off unless `USE_REAL_APIS=true` or a
  provider-specific future flag enables them. Alternative: auto-enable if
  dependency exists. Rationale: deterministic local/dev behavior matters more.
  Reversible: yes.
- Decision: do not cache fixture results as live data. Alternative: cache all
  endpoint output. Rationale: fixture caching can hide fixture corrections and
  provenance errors. Reversible: yes.

**Invariants.**

- `python -m pytest tests/test_frontend_contract.py -q` stays green after every
  schema-touching change.
- `python -m pytest tests/ -q` stays green after each backend slice.
- `USE_REAL_APIS=false` snapshot behavior stays deterministic.
- `warnings` codes already frozen in BE-12 are not renamed in backend-only work.
- A real-mode Workbench provider call either returns source-backed data in the
  existing success response model or returns the structured HTTP error contract;
  it never returns fixture data while claiming live/provider output.
- Run-scoped chat remains separate from lookup-scoped chat.

**Error Behavior.**

- Missing sequence context in fixture mode: return the known RPE65 fixture when
  the fixture key matches; otherwise keep existing fixture/default behavior.
- Missing sequence context in real Workbench mode: return `422
  Unprocessable Entity` with `detail.code =
  "workbench_sequence_context_unavailable"` and `detail.warnings` containing
  the same code.
- Unsupported input/species/build in real Workbench mode: return `422
  Unprocessable Entity` with `workbench_unsupported_input:<kind>` and avoid
  provider calls that would imply unsupported coverage.
- Provider dependency/configuration unavailable in real Workbench mode: return
  `503 Service Unavailable` with `workbench_provider_unavailable`.
- Provider timeout/network error in real Workbench mode: return `503 Service
  Unavailable` with `workbench_provider_failed:<ExceptionName>`.
- Provider malformed/unmappable output in real Workbench mode: return `502 Bad
  Gateway` with `workbench_provider_malformed`.
- Provider completes successfully with zero designs: return HTTP 200 using the
  existing response model with an empty result collection only when the provider
  explicitly reports a valid no-design result, not when the provider failed.
- LLM unavailable: chat returns 503 only if the service is genuinely
  unavailable; otherwise mock mode and fixture tests remain unaffected.

**Testing Strategy.**

- Unit tests for sequence-context normalization and unsupported inputs.
- Route tests proving Workbench endpoints still return current fixtures in
  fixture mode.
- Provider tests using fake adapters for success, timeout, malformed output,
  and missing sequence.
- Workbench route tests for the structured `422`, `502`, and `503` error
  mapping, plus success tests proving the current response schemas are
  unchanged.
- Contract canary for any additive schema fields.
- Live smoke tests gated behind explicit environment variables for each real
  provider, never required for default CI.

**Out of Scope.**

- Frontend tool UX, pixel QA, and FE milestones.
- Clinical validation of any generated design or classification.
- Licensed/curated datasets that require business approval.
- Commit, push, stash, reset, or branch surgery.

### Plan: Reviewable Backend Task Split

**Task M-002A - Sequence context boundary.**

Status: DONE 2026-05-17 18:19 +1000 · Codex. Implemented backend-internal
sequence context boundary with no public schema change.

Goal: create the internal service contract that all real Workbench engines can
share.

Context: current lookup can resolve GRCh38 coordinates and transcript HGVS;
Workbench routes still load static fixtures.

Relevant files: `app/backend/app/services/sequence_context.py`,
`app/backend/app/services/lookup_service.py`, `app/backend/app/core/config.py`,
`app/backend/app/fixtures/workbench/sequence_contexts.json`,
`app/backend/tests/test_sequence_context.py`.

Proposed approach: define an internal sequence-context model, fixture provider,
and resolver hook that reuses normalized query data and existing coordinate
resolution. Keep it backend-internal.

Acceptance criteria: fixture mode returns the RPE65 context; unsupported inputs
return explicit warnings; no public schema changes.

Verification completed:
`cd app/backend && python -m pytest tests/test_lookup_normalize.py tests/test_tool_invariants.py tests/test_sequence_context.py -q`
→ 15 passed. Full backend suite also passed:
`cd app/backend && python -m pytest tests/ -q` → 92 passed / 4 skipped.

Out of scope: real Primer3/CRISPR/alignment invocation.

**Task M-002B - Workbench service extraction with fixture parity.**

Status: DONE 2026-05-17 18:30 +1000 · Codex. Implemented backend-only
Workbench service extraction with fixture parity and structured service error
translation. No public schema change.

Goal: move `/primer`, `/crispr`, and `/align` route behavior behind a service
without changing responses.

Context: route handlers currently read fixture files directly.

Relevant files: `app/backend/app/api/routes/workbench.py`,
`app/backend/app/main.py`, future `app/backend/app/services/workbench_design.py`,
`app/backend/tests/`.

Proposed approach: inject `WorkbenchDesignService` through `app.state`; keep
fixture provider output byte-for-byte equivalent at the model level. Define the
internal service error/result boundary and route-level HTTP error translation
now, so M-002C/D/E providers inherit one failure contract.

Acceptance criteria: existing endpoint JSON shapes are unchanged; route tests
cover all three endpoints; fake service failures map to the structured
Workbench HTTP error detail; no frontend contract drift.

Verification completed:
`cd app/backend && python -m pytest tests/test_workbench_api.py -q` → 7 passed.
`cd app/backend && python -m pytest tests/test_workbench_api.py tests/test_frontend_contract.py tests/test_sequence_context.py -q` → 53 passed.
`cd app/backend && python -m pytest tests/test_lookup_normalize.py tests/test_tool_invariants.py -q` → 9 passed.
`cd app/backend && python -m pytest tests/ --disable-warnings` → 99 passed / 4 skipped.

Out of scope: new engine dependencies.

**Task M-002C - Real primer provider + specificity screens.**

Status: DONE 2026-05-17 23:07 +1000 · Codex. Implemented backend-only real
primer design plus exact resolved-template amplicon specificity screening and
an opt-in local UCSC `isPcr` whole-genome specificity provider behind the
Workbench service boundary. Follow-up installed/configured the local UCSC
assets under ignored backend storage and captured the remaining native-Windows
runtime blocker. No public response schema change and no frontend files
touched.

Goal: add the first real Workbench provider behind the service boundary.

Context: primer design is the lowest-risk engine because the existing schema
already models primer pairs, Tm, GC, product size, specificity hit count, notes,
and recommendation.

Provider/dependency decision: use local Primer3 through
`primer3-py>=2.3,<3` for backend design. Do not make browser-only or
vendor/account-gated tools from the primer tool list direct runtime
dependencies. NCBI Primer-BLAST remains a later validation class. The online
UCSC `hgPcr` endpoint returned a bot-protection page when tested from this
environment, so the backend path is now an optional local UCSC/Kent `isPcr`
provider selected by `PRIMER_SPECIFICITY_PROVIDER=ucsc_ispcr` with explicit
local binary/genome paths. IDT OligoAnalyzer, NEB Tm Calculator, Thermo Fisher
OligoPerfect, VectorBuilder, Primer3 Input, and Primer3Plus are useful
manual/reference tools but are not stable backend provider APIs for this slice.

Relevant files:
`app/backend/app/services/workbench_design.py`,
`app/backend/app/services/sequence_context.py`, `app/backend/app/main.py`,
`app/backend/requirements.txt`, `app/backend/tests/test_workbench_api.py`,
`app/backend/tests/test_sequence_context.py`.

Implementation completed:
- Added `EnsemblVariantSequenceResolver`, which resolves transcript HGVS through
  VariantValidator and fetches a GRCh38 sequence window from Ensembl REST.
- Wired `app.state.sequence_context_service` and passed it into
  `WorkbenchDesignService`.
- Added lazy `Primer3PrimerProvider`, mapping Primer3 output into the existing
  `PrimerResponse` / `PrimerPair` schema.
- Added `TemplateAmpliconSpecificityProvider`, which exact-matches each
  Primer3 pair against the resolved design template by pairing the forward
  primer with the reverse primer's reverse complement, counts products inside
  the requested product-size range, and marks target-spanning products.
- Added `LocalIsPcrSpecificityProvider`, which invokes standalone UCSC `isPcr`
  with a stdin 3-column query, parses FASTA products, maps product coordinates
  to the resolved target locus, and sets `specificity_hits` to the local
  whole-genome product count when explicitly configured.
- Added opt-in settings/env keys for the local `isPcr` provider:
  `PRIMER_SPECIFICITY_PROVIDER`, `UCSC_ISPCR_BINARY_PATH`,
  `UCSC_ISPCR_HG38_PATH`, `UCSC_ISPCR_TIMEOUT_SECONDS`,
  `UCSC_ISPCR_MIN_PERFECT`, and `UCSC_ISPCR_MIN_GOOD`.
- Real-mode `specificity_hits` now reflects exact resolved-template amplicons,
  and recommendation prefers the first pair with one product spanning the
  queried base. Pair notes explicitly state this is not genome-wide
  Primer-BLAST/UCSC specificity unless the local `ucsc_ispcr` provider is
  explicitly configured.
- Preserved fixture mode exactly when `USE_REAL_APIS=false`.
- In real primer mode, mapped unsupported/missing sequence context to `422`,
  missing Primer3 dependency to `503`, provider failure to
  `workbench_provider_failed:<ExceptionName>`, and malformed provider output to
  `502`.

Known limitations for this slice:
- Default `PRIMER_SPECIFICITY_PROVIDER=template` keeps `specificity_hits`
  source-backed only for exact products found inside the resolved sequence
  template. It must not be read as whole-genome specificity.
- `PRIMER_SPECIFICITY_PROVIDER=ucsc_ispcr` requires local UCSC `isPcr` and
  `hg38.2bit` assets. These are now installed under ignored
  `app/backend/data/bio_assets/**`, and `app/backend/.env` points to them
  while keeping the default provider as `template`. A live local `isPcr` smoke
  is still blocked on this native Windows host because the official UCSC
  executable is a Linux ELF and no WSL distribution is installed
  (`WinError 193` / structured `503 workbench_provider_unavailable`).
- NCBI Primer-BLAST checks, SNP masking, dimer/hairpin analysis, and
  ARMS-specific mismatch placement are not implemented yet.
- UCSC/Kent BLAT-family command-line executable licensing must be confirmed
  before bundling or commercial deployment.

Acceptance criteria completed:
real mode returns source-backed primer pairs for RPE65; fixture mode matches
current samples; provider errors return the documented `422`/`502`/`503`
detail codes; valid no-design output remains HTTP 200 with an empty pair list.

Verification completed:
`cd app/backend && python -m pytest tests/test_workbench_api.py -q`
→ 13 passed.
`cd app/backend && python -m pytest tests/test_workbench_api.py tests/test_sequence_context.py -q`
→ 20 passed.
`cd app/backend && python -m pytest tests/test_workbench_api.py tests/test_frontend_contract.py tests/test_sequence_context.py -q`
→ 60 passed.
`cd app/backend && python -m pytest tests/test_lookup_normalize.py tests/test_tool_invariants.py -q`
→ 9 passed.
`cd app/backend && python -m pytest tests/ --disable-warnings`
→ 109 passed / 4 skipped.
Opt-in live/engine smoke after `python -m pip install "primer3-py>=2.3,<3"`:
real `/api/v1/primer` route with `USE_REAL_APIS=true`, VariantValidator,
Ensembl REST, local Primer3, and the exact template specificity screen returned
HTTP 200 with 3 RPE65 primer pairs for a 500-1000 bp Sanger range. All 3 pairs
had `specificity_hits = 1`; first pair
`CTAGCACTGTGTCCCACCTG` / `AGCACACCATGTCCGGAATT`, product size 792.
Follow-up verification for the local `isPcr` provider path:
`cd app/backend && python -m pytest tests/test_workbench_api.py -q`
→ 16 passed.
`cd app/backend && python -m pytest tests/test_workbench_api.py tests/test_sequence_context.py tests/test_frontend_contract.py -q`
→ 63 passed.
`cd app/backend && python -m pytest tests/test_lookup_normalize.py tests/test_tool_invariants.py -q`
→ 9 passed.
Asset-install follow-up verification:
downloaded official UCSC Linux `isPcr` and `hg38.2bit` into ignored
`app/backend/data/bio_assets/**`; verified `hg38.2bit` MD5
`dcc3ea27079aa6dc3f9deccd7275e0f8`; attempted provider-level opt-in smoke with
an RPE65 exon 4 primer pair. The provider found the configured assets but failed
before screening with native Windows `WinError 193` because the official UCSC
binary is a Linux ELF and this host has no installed WSL distribution.
Post-install tests:
`cd app/backend && python -m pytest tests/test_workbench_api.py -q`
→ 16 passed.
`cd app/backend && python -m pytest tests/ --disable-warnings`
→ 109 passed / 4 skipped.

Out of scope: frontend primer UX changes, broad schema expansion, automatic
NCBI Primer-BLAST verification, WSL/native runtime installation, and CRISPR/
alignment real engines.

**Task M-002D - Real CRISPR provider decision and slice.**

Status: DONE 2026-05-17 23:42 +1000 · Codex. First backend-only local
deterministic SpCas9 provider implemented and verified; M-002I/post-edit
analytics and broader CRISPR provider extensions remain follow-up approvals.

Goal: implement the first reviewed real-mode CRISPR guide-design provider
after user approval, while keeping fixture mode and the current frontend
contract stable.

Source references: the supplied `# Blueprint for an Automated CRISPR 1.txt`
for sequence ingestion, PAM discovery, Hsu scoring, and DeepHF context; the
supplied `Backend FASTAPI integration.txt` for AB1/Biopython style integration
patterns; the supplied Docker notes for dependency expectations; the
Claude-authored `plans/crispr-integration.md` as read-only frontend
coordination context; current backend files
`app/backend/app/schemas/workbench.py`,
`app/backend/app/services/sequence_context.py`, and
`app/backend/app/services/workbench_design.py`.

Context: `/api/v1/crispr` currently returns the fixture
`crispr_rpe65.json` through `WorkbenchDesignService.design_guides`. M-002A
already provides a reusable sequence-context boundary for `gene` + `cdna`.
The CRISPR blueprint asks for raw target-sequence and genomic-coordinate input,
PAM scanning on both strands, 21-nt DeepHF context extraction, Hsu et al.
off-target scoring, local reference FASTA access, and candidate-guide
persistence. The first backend slice should not silently expand all of those
surfaces at once while frontend work is active.

Provider decision: use a local deterministic SpCas9 provider first. Do not use
an external CRISPOR workflow as the first runtime dependency. Do not ship
DeepHF neural-network inference until trained weights and model provenance are
available; the supplied PyTorch class is architecture scaffolding only.
Genome-wide off-target enumeration through Bowtie/BWA is a later opt-in asset
slice, not part of the first deterministic provider.

Contract decision: preserve the existing `CrisprGuide.off_target_score`
semantics as lower-is-better risk in the first slice by mapping
`off_target_score = 100 - hsu_specificity_score`. Keep the true Hsu specificity
score internally named `hsu_specificity_score` for tests, logs, and future
persistence. If the frontend needs to display both values, add an optional
`specificity_score` field only after explicit contract approval and a paired
`backend.ts` update.

Implementation completed:
- Added backend-internal `app/backend/app/services/crispr_design.py` and a
  `CrisprDesignProvider` protocol in `workbench_design.py`.
- Added `CRISPR_PROVIDER=local_deterministic`; `USE_REAL_APIS=false` fixture
  behavior remains unchanged and byte-equivalent.
- Real-mode `/api/v1/crispr` resolves `gene` + `cdna` through
  `SequenceContextService`, then runs local deterministic SpCas9 `NGG` guide
  design. No raw-sequence or genomic-region request fields were added.
- PAM discovery scans both forward and reverse-complement strands, preserves
  spacer/PAM/strand/cut offsets, and retains the 21-nt `spacer + first PAM
  base` context internally for tests and future DeepHF integration.
- Hsu/MIT off-target scoring uses the position, mismatch-count, and distance
  penalties with distance constant `4.0`; local first-pass off-target
  candidates are enumerated only inside the resolved context/window.
- `CrisprGuide.off_target_score` remains lower-is-better by mapping
  `100 - hsu_specificity_score`; no `specificity_score` contract field was
  added.
- On-target score is a labelled heuristic (GC band, poly-T, PAM-proximal base,
  5' G preference), not DeepHF.
- ssODN generation uses only available context/ref/alt SNV data and otherwise
  returns `ssodn = null`; no repair template is fabricated without source
  context.
- Unsupported real-mode `cas` values return structured
  `422 workbench_unsupported_input:cas`; too-short context returns
  `422 workbench_unsupported_input:sequence_too_short`.
- Candidate persistence, PostgreSQL schema, raw sequence/genomic-coordinate
  inputs, genome-wide Bowtie/BWA off-target enumeration, CRISPOR integration,
  and DeepHF trained inference remain out of scope.

Acceptance criteria:
- Fixture mode remains byte-equivalent for `/api/v1/crispr`.
- Real mode supports SpCas9 `NGG` only; unsupported `cas` values return a
  structured `422` rather than fixture or fabricated real output.
- PAM discovery tests cover forward strand, reverse-complement strand,
  overlapping PAMs, strand filtering, cut-position mapping, and too-short
  DeepHF-context windows.
- Hsu scoring tests cover zero, one, and multiple mismatches, including
  mismatch-count and distance penalties.
- Real mode returns source-backed guides, a valid empty-guide result when no
  eligible PAM exists, or the documented `422`/`502`/`503` Workbench error
  detail.
- No frontend files are touched unless the user separately approves a paired
  contract update.

Verification completed:
- `cd app/backend && python -m pytest tests/test_workbench_api.py tests/test_sequence_context.py -q`
  → 27 passed.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`
  → 40 passed.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  → 120 passed / 4 skipped.
- `git diff --check -- app/backend/.env.example app/backend/app/core/config.py app/backend/app/services/workbench_design.py app/backend/app/services/crispr_design.py app/backend/tests/test_workbench_api.py app/backend/tests/test_crispr_design.py`
  → no whitespace errors; PowerShell reported existing LF-to-CRLF git warnings
  for tracked files only.

Out of scope: clinical-editability claims, genome-wide off-target completeness,
DeepHF trained inference, CRISPOR integration, Bowtie/BWA index installation,
PostgreSQL persistence, frontend CRISPR UX, and Post-CRISPR outcome analytics.

**Task M-002E - Real alignment and AB1 parsing.**

Goal: replace the alignment fixture path with an optional real alignment path
for provided sequence/AB1 input.

Context: `AlignRequest` already accepts `user_sequence` and `ab1_blob_base64`;
`AlignResponse` already models reference, read, match line, mismatches, trace
channels, base calls, Q scores, and target position.

Relevant files: future alignment provider module, `workbench_design.py`,
`schemas/workbench.py` only if additive fields are approved, tests.

Proposed approach: parse supported inputs, align against sequence context, and
map the result to the existing response model; keep fixture behavior for empty
input/demo mode. Malformed input and provider failures use the structured
Workbench HTTP error contract unless a later review approves additive response
metadata.

Acceptance criteria: plain sequence input has deterministic tests; malformed
base64/unsupported AB1 data has explicit `422` behavior; provider failures use
`502`/`503`; fixture mode unchanged.

Verify: default backend tests plus alignment-specific unit tests.

Out of scope: frontend file-upload UX.

**Task M-002F - Live lookup-module hydration.**

Goal: replace fixture-only report v2 module values where current live evidence
can support them.

Context: `lookup_service.py` currently spreads `_lookup_v2_modules(gene, cdna)`
into `ReportPayload` and then overrides publications from LitVar2/PubMed.

Relevant files: future `app/backend/app/services/lookup_modules.py`,
`lookup_service.py`, `schemas/run.py`, `fixtures/lookup_v2_modules.json`, tests.

Proposed approach: introduce per-module builders. Start with fields that can be
truthfully derived from existing evidence and sequence context; leave
unsupported fields omitted or fixture-backed by explicit mode.

Acceptance criteria: no fabricated module data; publications behavior remains
accurate; contract canary stays green; unsupported live fields are clearly
absent or limited.

Verify: `cd app/backend && python -m pytest tests/test_variant_search_integration.py tests/test_frontend_contract.py -q`.

Out of scope: licensed disease/condition datasets unless separately approved.

**Task M-002G - Live lookup/Workbench chat adapter.**

Goal: make `/api/v1/chat` live mode work through a bounded grounded adapter.

Context: `ChatService` mock mode works; live mode needs an adapter compatible
with existing LangChain `invoke(...)` style wrappers and source-grounding
rules. `app/backend/app/main.py:create_app` currently wires
`ChatService(settings=settings, llm_client=draft_chain)`, so this slice must
change app wiring as well as service internals.

Relevant files: `app/backend/app/services/chat_service.py`,
`app/backend/app/agents/client.py`, `app/backend/app/agents/prompts.py`,
`app/backend/app/main.py`, `app/backend/tests/`.

Proposed approach: add a dedicated lookup-chat chain or adapter, likely
`build_lookup_chat_chain(settings)`, and wire it in `create_app` instead of
passing `draft_chain` into `ChatService`. `ChatService` should call
`invoke(...)` or a narrow adapter method shared by fake and live chains; it
should not call `.complete(...)`. Pass bounded variant/evidence/workbench
context and preserve streaming behavior by chunking the final grounded answer.

Acceptance criteria: mock mode unchanged; live adapter is testable with a fake
chain through both service tests and app/route wiring tests; unsupported or
unsafe questions get cautious bounded answers; no diagnostic claims; no
regression to run-scoped chat wiring.

Verify: route/service tests with fake chain; opt-in live smoke only when the
user provides provider credentials and approves the model/provider choice.

Out of scope: run-scoped chat behavior.

**Task M-002H - End-to-end backend verification and docs sync.**

Goal: verify real-mode slices together and update only the agreed docs.

Context: backend docs currently describe tool registry and fixture defaults;
future provider changes need accurate setup and guardrails.

Relevant files: backend README/docs selected by the implementation owner,
`plans/v2-backend.md`, tests.

Proposed approach: run full backend tests, contract canary, targeted live smoke
with opt-in flags, and update docs after the code is verified.

Acceptance criteria: test output recorded in handoff; docs list new env vars
and provider limitations; no frontend files touched unless explicitly approved.

Verify: `cd app/backend && python -m pytest tests/ -q` plus approved live-smoke
commands.

Out of scope: commits or pushes unless the user asks.

**Task M-002I - Post-CRISPR TIDE/outcome analytics plan.**

Status: PLANNED 2026-05-17 23:18 +1000 · Codex. Source materials ingested;
implementation has not started and remains user-gated.

Goal: add a later backend endpoint for post-edit Sanger deconvolution without
mixing it into M-002D guide design.

Source references: the supplied `# Blueprint for a Post-CRISPR Genome Editing
Analytics Engine 2.txt`, `Prompts for building 2.txt`, and `Backend FASTAPI
integration.txt`.

Context: this is a different workflow from guide design. It consumes control
and edited sequencing traces, computes an indel spectrum with a TIDE-like
non-negative least squares model, and can later compare observed outcomes with
SPROUT/inDelphi-style predictors. It overlaps M-002E because both need AB1
parsing.

Proposed approach after approval:
- Add a new endpoint such as `POST /api/v1/crispr/tide` with request/response
  schemas owned by the backend contract.
- Share one AB1 parser with M-002E alignment work, based on Biopython
  `SeqIO.read(..., "abi")`, so trace-channel handling is not duplicated.
- Implement deterministic NNLS deconvolution with SciPy for numeric arrays and
  AB1-derived signal vectors. Validate length, finite numeric values, cut-site
  bounds, and max insertion/deletion settings before solving.
- Return observed indel frequencies, overall editing efficiency, residual
  error, and provenance. Leave predicted repair outcomes absent/null until
  trained SPROUT/inDelphi weights are sourced and reviewed.

Acceptance criteria:
- Synthetic numeric-array tests produce a known indel spectrum.
- Mismatched, empty, non-finite, malformed file, and out-of-range cut-site
  inputs return structured `422` errors.
- Fixture/demo behavior remains deterministic if the frontend needs mock-first
  development before the endpoint ships.
- Contract canary stays green for any additive frontend-facing schema.

Verify: backend unit/route tests for the new endpoint, contract canary, and
full backend test suite. Live AB1 smoke only when the user provides test trace
files and approves using them.

Out of scope: CRISPResso2 NGS processing, SPROUT/inDelphi trained prediction,
frontend chart/pixel work, and clinical interpretation of editing outcomes.

**Task GV-001/GV-002 - Gene viewer backend contract and coordinate core.**

Status: DONE 2026-05-18 14:38 +1000 · Codex. Implemented the first
backend-only gene viewer slices from `plans/gene-viewer/plan.md`: typed
Pydantic viewer request/response schemas, RPE65 offline fixture, validating
fixture provider/service shell, pure transcript window builder, reference vs
variant SNV overlay, plus-strand tests, reverse-strand transcript-order tests,
and reference-mismatch fail-closed tests.

Files added:
- `app/backend/app/schemas/gene_viewer.py`
- `app/backend/app/services/gene_viewer.py`
- `app/backend/app/fixtures/workbench/viewer_rpe65.json`
- `app/backend/tests/test_gene_viewer.py`

Verification completed:
- `cd app/backend && python -m pytest tests/test_gene_viewer.py tests/test_sequence_context.py -q`
  -> 12 passed.
- `cd app/backend && python -m ruff check app tests` -> pass.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> pass.
- `cd app/backend && python -m pytest tests/test_workbench_api.py -q`
  -> 20 passed.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`
  -> 40 passed.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  -> 125 passed / 4 skipped.

Out of scope: viewer API route/wiring, live Ensembl/ClinVar/UniProt provider,
frontend TypeScript mirror/adapter, and tool sequence-basis changes. Next
approved backend step is GV-003 source-backed viewer provider or GV-004 route
wiring, depending on whether the user wants live provider depth before the API
surface.

**Task GV-003/GV-004 - Gene viewer source provider seam and API route.**

Status: DONE 2026-05-18 14:56 +1000 - Codex. Implemented the backend-only
source-backed provider boundary and exposed `POST /api/v1/viewer`.

Files added:
- `app/backend/app/api/routes/gene_viewer.py`

Files updated:
- `app/backend/app/api/routes/__init__.py`
- `app/backend/app/main.py`
- `app/backend/app/services/gene_viewer.py`
- `app/backend/tests/test_gene_viewer.py`

Implementation completed:
- Added `SourceBackedGeneViewerProvider`, source transcript/exon/intron records,
  and a `GeneViewerSourceClient` protocol for VariantValidator, Ensembl
  transcript/sequence, protein features, and provenance.
- Added a default HTTP source-client skeleton that resolves VariantValidator
  and Ensembl sequence windows while leaving full transcript-structure
  hydration behind the source-client seam until GV-008 live-smoke hardening.
- Added source-backed provider tests using mocked official-source responses for
  reverse-strand RPE65 `c.260A>G`, including intron flank sequence calls,
  source provenance, protein features, and variant-applied display sequence.
- Added fixture-mode validation for the canonical RPE65 sample and made
  fixture variant mode apply the c.260A>G SNV at display offset 103.
- Added `GeneViewerService` real-mode dispatch, app-state wiring, and
  `POST /api/v1/viewer` with structured `422`/`502`/`503` error mapping.
- Existing `/primer`, `/crispr`, and `/align` route behavior is unchanged.

Verification completed:
- `cd app/backend && python -m pytest tests/test_gene_viewer.py tests/test_workbench_api.py -q`
  -> 35 passed.
- `cd app/backend && python -m pytest tests/test_gene_viewer.py tests/test_sequence_context.py -q`
  -> 22 passed.
- `cd app/backend && python -m pytest tests/test_gene_viewer.py tests/test_sequence_context.py tests/test_workbench_api.py tests/test_frontend_contract.py -q`
  -> 83 passed.
- `cd app/backend && python -m ruff check app tests` -> pass.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> pass.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  -> 136 passed / 4 skipped.

Out of scope: frontend TypeScript mirror/adapter, visible Workbench data switch,
tool sequence-basis changes, and live RPE65 HTTP smoke. Next backend step is
GV-005 only with frontend coordination, or GV-008 live smoke/doc hardening if
the user wants to validate external provider behavior before frontend wiring.

**Task GV-008 - Gene viewer live RPE65 smoke and documentation hardening.**

Status: DONE 2026-05-18 15:18 +1000 - Codex. Implemented the live HTTP source
client hardening that GV-003 intentionally left behind the seam, then verified
RPE65 `c.260A>G` in both reference and variant modes.

Files updated:
- `app/backend/app/services/gene_viewer.py`
- `app/backend/tests/test_gene_viewer.py`
- `plans/gene-viewer/design.md`
- `plans/gene-viewer/spec.md`
- `plans/gene-viewer/plan.md`

Implementation completed:
- Ensembl symbol lookup now hydrates the selected MANE/RefSeq transcript,
  coding exon/CDS coordinates, intron intervals, UTR lengths, transcript
  aliases, total coding length, protein length, and translation id.
- Ensembl sequence/region fetches are window-limited to the requested viewer
  window instead of hydrating the whole coding transcript.
- VariantValidator live responses now enrich the queried variant with
  `p.Asp87Gly`, codon 87, one-letter amino-acid ref/alt, and GRCh38 VCF
  projection.
- Ensembl translation overlap now populates protein-domain features such as
  RPE65 carotenoid oxygenase Pfam/PANTHER ranges.
- GV docs now record the user decision that the frontend's third viewer mode
  should be a protein view, not the removed exon-only view, with a
  domain-aware ClinVar lollipop track.

Live route smoke:
- `POST /api/v1/viewer` with `USE_REAL_APIS=true` semantics returned HTTP 200
  for RPE65 `NM_000329.3:c.260A>G` in reference and variant modes.
- Confirmed reverse strand, 14 total exons, rendered window `c.140-c.380`,
  segment `exon-4:246-353`, reference base `A`, variant-applied base `G`, and
  protein domains `Carotenoid oxygenase` from Ensembl translation overlap.
- Current live warnings are intentional:
  `live_source_transcript_from_ensembl`,
  `clinvar_track_not_live_hydrated`,
  `protein_features_from_ensembl_overlap`, and
  `ensembl_transcript:ENST00000262340`.

Verification completed:
- `cd app/backend && python -m pytest tests/test_gene_viewer.py -q`
  -> 18 passed.
- Live `POST /api/v1/viewer` route smoke with `USE_REAL_APIS=true` semantics
  -> HTTP 200 in reference and variant modes.
- `cd app/backend && python -m pytest tests/test_gene_viewer.py tests/test_workbench_api.py tests/test_frontend_contract.py -q`
  -> 78 passed.
- `cd app/backend && python -m ruff check app tests` -> pass.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> pass.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  -> 138 passed / 4 skipped.

Out of scope: frontend TypeScript mirror/adapter, visible protein/lollipop UI,
live ClinVar gene-wide hydration, and downstream tool sequence-basis changes.

**Task RP-001 - Report backend hardening audit slice.**

Status: DONE 2026-05-18 17:35 +1000 - Codex. Backend-only hardening completed
after auditing the landing/report surface.

Files updated:
- `app/backend/app/services/intake.py`
- `app/backend/app/schemas/lookup.py`
- `app/backend/tests/test_report_api.py`
- `app/backend/tests/test_variant_search_integration.py`

Implementation completed:
- Report upload now rejects non-PDF media types, empty bodies, and spoofed
  `.pdf` payloads before storing or extracting the file.
- Live extraction-chain failures now produce a structured blocked report with
  an extraction issue/warning instead of a 500.
- Lookup request fields are trimmed and bounded; blank `gene`/`cdna` inputs
  now fail at the Pydantic boundary with `422`.
- Route-level auth coverage now locks `POST /api/v1/reports/upload` as
  authenticated.

Audit notes:
- `/report` is live for structured variant queries through
  `POST /api/v1/lookup`; no-query and `demo=1` states intentionally render the
  bundled RPE65 sample.
- The legacy `/runs` report-upload frontend path is not end-to-end wired after
  auth hardening because `app/frontend/src/lib/api.ts` does not send bearer
  tokens. Coordinate before touching this frontend file because Claude is
  active in nearby frontend work.

Verification completed:
- `cd app/backend && python -m pytest tests/test_report_api.py tests/test_variant_search_integration.py tests/test_lookup_normalize.py tests/test_frontend_contract.py -q`
  -> 55 passed.
- `cd app/backend && python -m ruff check app tests` -> pass.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> pass.
- `cd app/backend && python -m pytest tests/ --disable-warnings -q`
  -> 143 passed / 4 skipped.

Out of scope: frontend auth/session UX, landing-page redesign, report-page
visual iteration, and edits to Claude-owned primer/GV frontend files.

**Task RP-002 - Variant Evidence Report AlphaMissense hold fixture alignment.**

Status: DONE 2026-05-19 14:22 +1000 - Codex. Backend side of the
AlphaMissense hold decision completed for the live Variant Evidence Report
payload.

Files updated:
- `app/backend/app/fixtures/lookup_v2_modules.json`

Implementation completed:
- Removed the `AlphaMissense` predictor card from the live
  `in_silico_predictions.cards` fixture returned through
  `POST /api/v1/lookup`.
- Updated the fixture `consensus_note` to remove the
  `(REVEL, AlphaMissense, MetaLR)` enumeration and any live report prose naming
  AlphaMissense.
- Preserved the `'AlphaMissense'` contract literal in backend/frontend schema
  mirrors and did not touch `sample-report.ts`, frontend render filters, or
  patient report pipeline (`/runs`) code.

Verification completed:
- `cd app/backend && python -m pytest tests/test_variant_search_integration.py tests/test_lookup_normalize.py tests/test_frontend_contract.py -q`
  -> passed.
- `python -m json.tool app/backend/app/fixtures/lookup_v2_modules.json`
  -> passed.
- `rg -n "AlphaMissense|REVEL, AlphaMissense|three protein-effect" app/backend/app/fixtures/lookup_v2_modules.json app/backend/app/schemas/run.py app/frontend/src/lib/backend.ts app/frontend/src/lib/sample-report.ts app/frontend/src/components/report`
  -> no backend fixture hits; remaining hits are intentional contract/sample/frontend hold references.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  -> 143 passed / 4 skipped.

Out of scope: re-enabling AlphaMissense, deleting AlphaMissense contract/tool
assets, frontend UI work, and any patient report pipeline (`/runs`) work.

**Task RP-003 - Variant literature extraction design/spec/plan.**

Status: PLANNED 2026-05-19 19:30 +1000 - Codex. Planning-only artifacts were
created for a future Variant Evidence Report Publication/Literature section
upgrade. Implementation has not started.

Artifacts:
- `plans/variant-literature-extraction/design.md`
- `plans/variant-literature-extraction/spec.md`
- `plans/variant-literature-extraction/plan.md`

Recommended algorithm name:
- **Eamos Proprietary Variant Literature Extractor (EP-VLEx)**

Planned behavior:
- Build a deduplicated variant-specific PMID set from LitVar2, PubMed, ClinVar,
  and future local ClinGen evidence.
- Keep `publications_callout.total_count` as the authoritative visible count.
- Show the five most recent publication rows in the initial Variant Evidence
  Report payload.
- Expose a paginated expansion endpoint for the full publication set.
- Add LitVar2-style variant-mention snippets from PubMed EFetch, PubTator BioC,
  and PMC BioC where available.
- Keep every article title/PMID link pointed to
  `https://pubmed.ncbi.nlm.nih.gov/{pmid}/`.

Planning validation:
- Local functional-literature reference docs and the supplied LitVar2 screenshot
  were reviewed.
- Official NCBI E-utilities, PubTator, LitVar2, and PMC developer API sources
  were checked.
- Live planning probe confirmed LitVar2 currently resolves `RPE65 p.R118K` /
  `rs1381010953` to 3 PMIDs and PubTator returns variant annotations for PMID
  `36142423`.
- `git diff --check -- plans\variant-literature-extraction` passed.

Out of scope: implementation, frontend rendering, Patient Report Pipeline
(`/runs`), AlphaMissense, commits, pushes, stashes, resets, and cleans.

**Task RP-004 - EP-VLEx backend implementation.**

Status: DONE 2026-05-19 19:56 +1000 - Codex. Implemented the backend
Variant Evidence Report publication/literature slice from
`plans/variant-literature-extraction/plan.md`.

Files added:
- `app/backend/app/services/publication_literature.py`
- `app/backend/tests/test_publication_literature.py`

Files updated:
- `app/backend/app/schemas/run.py`
- `app/backend/app/schemas/lookup.py`
- `app/backend/app/api/routes/lookup.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/tools/litvar2.py`
- `app/backend/app/fixtures/tools/litvar2_fixtures.json`
- `app/backend/app/fixtures/lookup_v2_modules.json`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_variant_cache.py`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_frontend_contract.py`
- `plans/variant-literature-extraction/plan.md`

Implementation completed:
- Added additive EP-VLEx schemas:
  `PublicationSnippet`, `PublicationSourceBreakdown`,
  `PublicationLiterature`, enriched optional `PubMedArticle` fields, and
  optional `ReportPayload.publications_literature`.
- Added `EamosProprietaryVariantLiteratureExtractor` with HGVS/protein
  one-letter/three-letter/rsID/genomic term building, PMID dedupe across
  PubMed/LitVar2/ClinVar citation-like PMIDs, recent-first sorting, PubMed URL
  invariants, and PubMed title/abstract snippet extraction.
- Added fallback-source guard so failed live sources do not count unrelated
  fixture rows as variant-specific publication evidence.
- Wired `POST /api/v1/lookup` to return at most five EP-VLEx rows and mirror
  them into `pubmed_articles`; `publications_callout.total_count` now equals
  `publications_literature.total_count`.
- Added `POST /api/v1/lookup/publications` with bounded pagination
  (`limit <= 50`).
- Extended fresh resolved-variant cache records with PubMed summary and EP-VLEx
  first-page data so PubMed/LitVar2 publication discovery is replayed from
  cache on cache hits.
- Fixed LitVar2 live publication URL construction by percent-encoding variant
  IDs containing reserved characters such as `@` and `#`.
- Adjusted deterministic fixture publication count for RPE65 `c.260A>G` to the
  deduped variant-specific PMID set (3 rows).

Coordination:
- Codex did not edit `app/frontend/src/lib/backend.ts` or any frontend render
  files. The backend contract canary explicitly allows the new EP-VLEx fields
  as pending frontend mirror fields until Claude mirrors/renders them.
- Cross-agent request filed for Claude to add the TypeScript mirror and render
  the Publication/Literature section.
- User clarification 2026-05-19: EP-VLEx is the general variant-publication
  inventory/count with an initial five-row display and expansion for more.
  The functional card is a separate future extractor/count for studies that did
  functional work on the variant, using ClinGen/ClinVar/PubMed functional
  screening tags/signals. Do not use `PublicationLiterature.total_count` as the
  functional-study count.

Verification completed:
- `cd app/backend && python -m ruff check app tests` -> pass.
- `cd app/backend && python -m pytest tests/test_tool_invariants.py tests/test_publication_literature.py tests/test_variant_search_integration.py tests/test_variant_cache.py tests/test_frontend_contract.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/ --disable-warnings -q`
  -> passed (160 collected; 4 skipped by collection inventory).
- Live publications-only smoke for user-supplied
  `USH2A c.2276G>T, p.Cys759Phe`:
  `POST /api/v1/lookup/publications` -> HTTP 200, `total_count=13`,
  `shown_count=5`, `variant_terms` include `rs752238803`, source breakdown
  `pubmed=10`, `litvar2=3`, `clinvar=0`, no warnings.

Out of scope: frontend TypeScript mirror/rendering, PubTator/PMC full-text
snippet expansion, the separate functional-card functional-study count,
automatic ACMG PS3/BS3 assignment, Patient Report Pipeline (`/runs`),
AlphaMissense, commits, pushes, stashes, resets, and cleans.

**Task RP-005 - Functional evidence study count backend.**

Status: DONE 2026-05-19 20:59 +1000 - Codex. Implemented the backend-only
functional-card study counting slice for the Variant Evidence Report.

Files added:
- `app/backend/app/services/functional_evidence.py`
- `app/backend/tests/test_functional_evidence.py`

Files updated:
- `app/backend/app/schemas/run.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/sequence_context.py`
- `app/backend/app/core/config.py`
- `app/backend/.env.example`
- `app/backend/tests/test_frontend_contract.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_variant_cache.py`
- `app/backend/tests/test_lookup_normalize.py`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added additive `ReportPayload.functional_evidence` with
  `FunctionalEvidenceSummary`, `FunctionalStudy`, and source-breakdown models.
- Added a `FunctionalEvidenceExtractor` that counts functional-study rows from
  ClinGen Evidence Repository classification summaries, ClinVar VCV XML
  comments, and PubMed title/abstract hits.
- Kept this count separate from EP-VLEx publication inventory. It counts
  source-supported functional studies only and does not use
  `PublicationLiterature.total_count`.
- Preserved ClinGen source-native citation-only evidence when no PMID exists,
  e.g. RPE65 `NM_000329.3:c.11+5G>A` `PS3_Supporting` from
  `Guan et al., 2024`.
- Counted and deduped PMID-backed functional evidence across ClinGen and
  ClinVar, e.g. RPE65 `c.1301C>T (p.Ala434Val)` `BS3_Supporting` PMIDs
  `16150724` and `19431183`.
- Added a conservative two-tier functional term policy:
  source-native/high-confidence terms include functional study/evidence/assay,
  assay, minigene, splicing assay, transcript/RNA analysis, RT-PCR,
  cDNA analysis, enzyme/enzymatic/protein activity, retinoid isomerase,
  rescue/complementation, cell/animal model, in vitro/in vivo, reporter/
  luciferase assay, electrophysiology/patch clamp/channel/transport activity;
  softer terms such as expression, mRNA, protein function, localization,
  trafficking, stability, folding, Western/immunoblot, immunofluorescence, and
  binding require variant/citation context.
- Tightened PMID parsing so ClinVar variation IDs are not counted as PMIDs.
- Added `CLINGEN_EREPO_BASE_URL` and URL construction that preserves `>` in
  ClinGen ERepo queries.
- Extended query normalization for transcript-with-gene annotation plus
  trailing protein text, e.g.
  `NM_000329.3(RPE65):c.1301C>T (p.Ala434Val)`.
- Cached `functional_evidence` on fresh resolved live lookup records.

Verification completed:
- `cd app/backend && python -m ruff check app tests` -> pass.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> pass.
- `cd app/backend && python -m pytest tests/test_functional_evidence.py tests/test_variant_search_integration.py tests/test_variant_cache.py tests/test_lookup_normalize.py tests/test_frontend_contract.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/ --disable-warnings -q`
  -> passed (172 collected; 4 skipped).
- Live route smoke with `USE_REAL_APIS=true`:
  - `POST /api/v1/lookup?refresh=true` for
    `RPE65 NM_000329.3(RPE65):c.11+5G>A` -> HTTP 200,
    `functional_evidence.total_count=1`, `evidence_codes=["PS3"]`, study
    `Guan et al., 2024` with no PMID.
  - `POST /api/v1/lookup?refresh=true` for
    `RPE65 NM_000329.3(RPE65):c.1301C>T (p.Ala434Val)` -> HTTP 200,
    `functional_evidence.total_count=2`, `evidence_codes=["BS3"]`, PMIDs
    `16150724` and `19431183` with ClinGen+ClinVar source tags.

Out of scope: frontend TypeScript mirror/rendering, final ACMG PS3/BS3
assignment, PubTator/PMC full-text functional classification, AlphaMissense,
Patient Report Pipeline (`/runs`), commits, pushes, stashes, resets, and
cleans.

**Task GV-005/RP hardening follow-up - Contract canary and false-positive guards.**

Status: DONE 2026-05-20 18:10 +1000 - Codex. Completed after the user approved
a checkpoint commit/push and asked Codex to proceed with GV-005 first, then
RP-004/RP-005 backend hardening.

Files updated:
- `app/backend/tests/test_frontend_contract.py`
- `app/backend/app/services/publication_literature.py`
- `app/backend/tests/test_publication_literature.py`
- `app/backend/tests/test_functional_evidence.py`
- `app/backend/tests/test_variant_cache.py`
- `PROGRESS.md`
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Extended the frontend contract canary to cover `GeneViewerRequest`,
  `GeneViewerResponse`, and all nested Gene Viewer Pydantic models against the
  existing TypeScript mirror in `app/frontend/src/lib/backend.ts`.
- Tightened EP-VLEx ClinVar PMID extraction so keys such as
  `reference_allele` do not create PMID context for genomic coordinate numbers.
  True citation/reference keys still count PMID-like values.
- Added EP-VLEx regression tests for failed ClinVar source skips and
  reference-allele false-positive PMIDs.
- Added functional-evidence regression tests for ClinGen live failure warnings
  that preserve PubMed hits and ClinVar failed-source statuses that skip VCV
  fetching.
- Extended variant-cache coverage so cached functional-evidence summaries,
  including studies and evidence codes, replay without recomputing.

Verification completed:
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py tests/test_publication_literature.py tests/test_functional_evidence.py tests/test_variant_cache.py -q`
  -> passed.
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed after formatting `app/services/publication_literature.py`.
- `cd app/backend && python -m pytest tests/ --disable-warnings -q`
  -> passed.

Checkpoint:
- Pre-task backend checkpoint `c40bf52` was committed and pushed to
  `origin/checkpoint/v2-batches-2026-05-17` before this follow-up work.

Out of scope: frontend rendering, `backend.ts` EP-VLEx/functional mirror work,
final ACMG PS3/BS3 assignment, Patient Report Pipeline (`/runs`),
AlphaMissense, FE-7/FE-8, M-002 follow-ups, and destructive git operations.

**Task RP layout planning - Functional display metrics and MVP source strategy.**

Status: DONE 2026-05-20 18:52 +1000 - Codex. Completed after the user clarified
that the Lab & Functional call card should display source-reported functional
categorization and unique functional-study count as separate facts.

Files updated:
- `app/backend/app/schemas/run.py`
- `app/backend/app/services/functional_evidence.py`
- `app/backend/tests/test_functional_evidence.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_variant_cache.py`
- `app/backend/tests/test_frontend_contract.py`
- `plans/variant-report-layout/design.md`
- `plans/variant-report-layout/spec.md`
- `plans/variant-report-layout/plan.md`
- `PROGRESS.md`
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added backend functional display metrics:
  `primary_label`, `acmg_badge_text`, `study_count_badge_text`, and
  `ui_color_theme`.
- Added `source_asserted_codes` and per-study `asserted_codes` so PS3/BS3-style
  source assertions can be displayed independently from study count.
- Added display mapping for source-reported PS3, source-reported BS3,
  conflicting source reports, PubMed-only functional evidence, and no evidence.
- Added/updated backend tests and the frontend contract canary for the new
  additive fields.
- Authored the Variant Evidence Report layout data design/spec/plan, including
  the four-card grid and the requested Precision Therapies & Active Clinical
  Trials section.
- Captured MVP source strategy: MyVariant.info is an annotation
  aggregator/fallback only; direct/source-native APIs remain required for
  evidence and provenance; SpliceAI target architecture is local/precomputed
  scoring in our own service/database, with public lookup only as cached demo
  fallback.

Verification completed:
- `cd app/backend && python -m ruff check .` -> passed.
- `cd app/backend && python -m black --check .` -> passed after formatting
  `app/services/functional_evidence.py`.
- `cd app/backend && python -m pytest tests/test_functional_evidence.py tests/test_variant_search_integration.py tests/test_variant_cache.py tests/test_frontend_contract.py -q`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed.

Out of scope: frontend rendering, generic four-call-card backend builder,
MyVariant adapter implementation, ClinicalTrials.gov implementation,
local SpliceAI service implementation, Patient Report Pipeline (`/runs`),
AlphaMissense, commits, pushes, stashes, resets, and cleans.

**Task RP call cards / gnomAD population source - Backend contract and first source slice.**

Status: DONE 2026-05-20 19:25 +1000 - Codex. Completed after the user
confirmed gnomAD Browser as the source for population data and reiterated that
each Variant Evidence Report call card/section must be live and gene agnostic.

Files added:
- `app/backend/app/services/report_call_cards.py`
- `app/backend/tests/test_gnomad_tool.py`

Files updated:
- `app/backend/app/schemas/run.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/tools/gnomad.py`
- `app/backend/app/fixtures/tools/gnomad_fixtures.json`
- `app/backend/tests/test_frontend_contract.py`
- `app/backend/tests/test_variant_search_integration.py`
- `plans/variant-report-layout/design.md`
- `plans/variant-report-layout/spec.md`
- `plans/variant-report-layout/plan.md`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added the additive generic call-card contract:
  `ReportCallBadge`, `ReportCallCard`, `VariantReportCallCards`, and optional
  `ReportPayload.call_cards`.
- Added additive source gnomAD population detail:
  `PopulationFrequencyDetail`, `PopulationFrequencyAncestryGroup`,
  `PopulationAgeDistribution`, `PopulationAgeHistogram`, and optional
  `ReportPayload.population_frequency_detail`.
- Added a call-card builder that produces Population Frequency, Computational,
  Lab & Functional, and Clinical Consensus cards from the current lookup
  payload/evidence maps.
- Extended the gnomAD real-mode GraphQL query to hydrate joint/exome/genome
  AC/AN/homozygotes, `faf95` popmax, genetic ancestry group rows, and available
  age histograms.
- Population Frequency now uses source gnomAD detail and preserves source URL,
  dataset, sequencing type, warnings, ancestry rows, and age histograms for
  section rendering.
- Lab & Functional maps `functional_evidence.display_metrics` into the generic
  card, preserving the invariant that source-reported PS3/BS3 category and
  `X Unique` study count are independent.
- Updated layout docs to state that gnomAD GraphQL is appropriate for cached
  interactive single-variant population data, while production-scale batch work
  should use local indexed gnomAD release data or the official toolbox path.

Verification completed:
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed after formatting the new/edited backend files.
- `cd app/backend && python -m pytest tests/test_gnomad_tool.py tests/test_variant_search_integration.py tests/test_frontend_contract.py -q`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed.

Out of scope: frontend TypeScript mirror/rendering, MyVariant adapter
implementation, local/precomputed SpliceAI service implementation, ClinGen
expert-panel clinical-consensus precedence, ClinicalTrials.gov implementation,
Patient Report Pipeline (`/runs`), AlphaMissense, commits, pushes, stashes,
resets, and cleans.

**Task RP call cards / gnomAD population source - Live route smoke and fallback guard.**

Status: DONE 2026-05-20 23:15 +1000 - Codex. Completed after resuming from the
call-card/population-detail handoff and live-smoking the current lookup path
for the prior PS3/BS3 variants.

Files updated:
- `app/backend/app/tools/gnomad.py`
- `app/backend/tests/test_gnomad_tool.py`
- `PROGRESS.md`
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Live-smoked `POST /api/v1/lookup?refresh=true` for:
  - RPE65 `NM_000329.3(RPE65):c.11+5G>A`
  - RPE65 `NM_000329.3(RPE65):c.1301C>T (p.Ala434Val)`
  - USH2A `c.2276G>T (p.Cys759Phe)` as the prior publication variant
- Confirmed the RPE65 responses return `call_cards`,
  `population_frequency_detail`, and `functional_evidence` together.
- Fixed gnomAD live fallback so a timeout for one normalized variant cannot
  attach the generic c.260A>G fixture population metrics to a different
  variant. Mismatched fallback now keeps requested variant ID/dataset/source URL
  and warnings but omits frequency/ancestry/age metrics.
- Added regression coverage for the mismatched gnomAD fallback case.

Verification completed:
- Live route smoke:
  - `c.11+5G>A` -> HTTP 200, gnomAD live, population variant ID
    `1-68449890-C-T`, 10 genetic ancestry groups, age distribution present,
    Lab & Functional `PS3_Supporting` / `1 Unique`.
  - `c.1301C>T (p.Ala434Val)` -> HTTP 200, gnomAD live, population variant ID
    `1-68431319-G-A`, 10 genetic ancestry groups, age distribution present,
    Lab & Functional `BS3_Supporting` / `2 Unique`.
  - USH2A `c.2276G>T (p.Cys759Phe)` -> HTTP 200, 13 EP-VLEx publications,
    one PubMed-backed functional-evidence study, and no gnomAD detail because
    the cDNA-only VEP path did not resolve genomic coordinates.
- `cd app/backend && python -m ruff check app/tools/gnomad.py tests/test_gnomad_tool.py`
  -> passed.
- `cd app/backend && python -m black --check --target-version py310 app/tools/gnomad.py tests/test_gnomad_tool.py`
  -> passed.
- `cd app/backend && python -m pytest tests/test_gnomad_tool.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_gnomad_tool.py tests/test_variant_search_integration.py tests/test_frontend_contract.py -q`
  -> passed.

Out of scope: frontend TypeScript mirror/rendering, Patient Report Pipeline
(`/runs`), AlphaMissense, MyVariant/dbNSFP, local/precomputed SpliceAI,
ClinicalTrials.gov implementation, commits, pushes, stashes, resets, and
cleans.

**Task Variant Evidence Report Task 11A + Task 12 backend implementation.**

Status: DONE 2026-05-23 19:51 +1000 - Codex. Completed after user approved the
combined backend-only session for gene-agnostic report-profile hardening and
Section 3 gnomAD expansion.

Files added:
- `app/backend/app/services/population_frequency_section.py`
- `app/backend/tests/test_report_call_cards.py`

Files updated:
- `app/backend/app/schemas/run.py`
- `app/backend/app/services/report_call_cards.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/services/clinical_consensus.py`
- `app/backend/app/tools/variant_validator.py`
- `app/backend/app/tools/ensembl_vep.py`
- `app/backend/app/tools/spliceai.py`
- `app/backend/app/tools/gnomad.py`
- `app/backend/app/tools/clinvar.py`
- `app/backend/app/tools/pubmed.py`
- `app/backend/app/tools/litvar2.py`
- `app/backend/app/fixtures/tools/clingen_fixtures.json`
- `app/backend/tests/test_frontend_contract.py`
- `app/backend/tests/test_gnomad_tool.py`
- `app/backend/tests/test_clinical_consensus.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_search_input_resolver.py`
- `plans/variant-report-data-orchestration/plan.md`
- `plans/variant-report-data-orchestration/spec.md`
- `docs/proprietary/README.md`
- `docs/proprietary/index.json`
- `docs/proprietary/variant-report-orchestration.md`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added fixture/fallback identity guards for VariantValidator, VEP, SpliceAI,
  gnomAD, ClinVar, PubMed, and LitVar2 so mismatched non-RPE65 lookups return
  empty/unavailable data instead of the RPE65 fixture snapshot.
- Added the six-variant Task 11A regression matrix: RPE65 `c.260A>G`, RPE65
  `c.11+5G>A`, USH2A `c.2276G>T`, BRCA1 `c.5266dup`, RPGRIP1 `c.1997C>T`,
  and CFTR Leu441 ambiguity.
- Added source-scoped ClinGen fixture coverage for RPE65 `c.11+5G>A` so the
  functional-prior/PS3 path is proven without borrowing `c.260A>G` facts.
- Added additive `ReportCallInteraction`, `ReportCallCard.interaction`, and
  `VariantReportProfile.population_frequency` schemas.
- Added the Section 3 population-frequency builder, projecting the existing
  canonical `population_frequency_detail` into a render-ready section with
  genetic ancestry groups, overall release-sample age bins, source/QC rows,
  warnings, source URL, and provenance.
- Population Frequency call cards now carry `scroll_and_expand` metadata to
  `section-3-population-frequency` and `gnomad-expansion`.
- Sanitized ACMG rationale text for raw population metric leakage and stopped
  PM2/BA1/BS1 call-card badges from being derived directly from raw AF/AC/popmax
  thresholds.

Verification:
- `cd app/backend && python -m pytest tests/test_variant_report_orchestration.py tests/test_report_call_cards.py tests/test_gnomad_tool.py tests/test_clinical_consensus.py tests/test_variant_search_integration.py tests/test_search_input_resolver.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py tests/test_tool_invariants.py tests/test_publication_literature.py tests/test_functional_evidence.py tests/test_clinical_trials_tool.py -q`
  -> passed.
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed, 4 skipped, existing JWT
  short-key warnings only.

Out of scope: frontend edits/rendering, browser verification, Patient Report
Pipeline (`/runs`), AlphaMissense, production gnomAD ETL/warehouse, commit,
push, stash, reset, or clean.

**Task Variant Evidence Report Section 3 gnomAD expansion planning.**

Status: PLANNED 2026-05-23 19:14 +1000 - Codex. Completed after the user
supplied gnomAD expansion briefs and redirected the population-frequency
detail into Section 3.

Files updated:
- `plans/variant-report-data-orchestration/design.md`
- `plans/variant-report-data-orchestration/spec.md`
- `plans/variant-report-data-orchestration/plan.md`
- `plans/v2-backend.md`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Plan captured:
- Population Frequency card remains compact and should emit navigation
  metadata for `scroll_and_expand` to Section 3 (`section-3-population-frequency`
  / `gnomad-expansion`).
- Section 3 owns the expanded gnomAD panel: source header, metric strip,
  genetic ancestry heatmap/bar rows, overall age histogram views, source/QC
  table rows, warnings, and provenance.
- `population_frequency_detail` stays the canonical raw/source detail group;
  any `report_profile.population_frequency` section is a render-ready
  projection with a clear reference back to that detail group.
- Section 2 remains disease mechanism/inheritance only.
- ACMG ledger stays clean: PM2/BA1/BS1 may appear as source-asserted criteria
  or Eamos hints, but no raw gnomAD AF/AC/AN/popmax, homozygote, genetic
  ancestry, or age-bin metrics should be repeated in ledger rationale.
- Current gnomAD GraphQL/fixture data has overall het/hom age distribution, not
  per-genetic-ancestry histograms. Do not fabricate per-group age arrays.

Planned implementation/test follow-up:
- Add `ReportCallInteraction`, `ReportCallCard.interaction`, and
  `VariantReportProfile.population_frequency`.
- Add a Section 3 population-frequency builder, likely
  `app/backend/app/services/population_frequency_section.py`.
- Add `app/backend/tests/test_population_frequency_expansion.py` and extend
  gnomAD/orchestration/contract/clinical-consensus tests for navigation,
  Section 2 cleanliness, no fixture bleed, no per-group age fabrication, and no
  raw gnomAD metrics in ACMG.

Verification for this planning slice:
- Not run; documentation/planning-only update. Use `git diff --check` before
  final handoff.

Out of scope: frontend edits/rendering, browser verification, Patient Report
Pipeline (`/runs`), AlphaMissense, production gnomAD ETL/warehouse, commit,
push, stash, reset, or clean.

**Task Variant Evidence Report Task 11A + Task 12 parallel next-session plan.**

Status: PLANNED 2026-05-23 19:24 +1000 - Codex. Added after the user asked
whether the sections before Task 12 need more hardening and testing with other
genes to prove gene-agnostic search/output behavior.

Plan update:
- Add `plans/variant-report-data-orchestration/plan.md` Task 11A:
  Gene-Agnostic Report Profile Regression Gate.
- Run Task 11A and Task 12 in the same next session, but keep shared
  schema/contract integration local to Codex.
- Use subagents in parallel for disjoint work:
  - Fixture Bleed Audit Agent.
  - Multi-Gene Test Matrix Agent.
  - Clinical/ACMG Semantics Agent.
  - Section 3 gnomAD Worker after Codex controls the shared schema shape.

Task 11A target matrix:
- RPE65 `c.260A>G` rich fixture happy path.
- RPE65 `c.11+5G>A` splice/functional-prior path.
- USH2A `c.2276G>T` different-gene path.
- BRCA1 `c.5266dup` indel normalization path.
- RPGRIP1 `c.1997C>T` sparse/no-hit path.
- CFTR Leu441 ambiguity path, which should require confirmation rather than
  building a report-runnable payload.

Task 11A acceptance:
- Non-RPE65 lookups must not inherit RPE65 disease, molecular,
  computational, ACMG, gnomAD, publication, functional, or trial facts.
- Gene-only/disease-only/ambiguous inputs keep variant-level sections
  unavailable or confirmation-gated.
- Interpretation summaries cite only current-lookup facts.
- Publication inventory and functional-study counts stay separate.
- gnomAD no-hit and fallback mismatch never attach fixture metrics.

Verification for this planning update:
- Planning/docs only; run `git diff --check` before handoff.

Out of scope: frontend edits/rendering, browser verification, Patient Report
Pipeline (`/runs`), AlphaMissense, commit, push, stash, reset, or clean.

**Task Variant Report Data Orchestration Task 7 - Computational annotation stack.**

Status: DONE 2026-05-23 18:44 +1000 - Codex. Completed after user approved
continuing backend-only with Task 7 and requested parallel subagents for ACMG
ledger, publications, clinical trials, and support work.

Files added:
- `app/backend/app/tools/computational_annotations.py`
- `app/backend/app/fixtures/tools/computational_annotations_fixtures.json`
- `app/backend/tests/test_clinical_trials_tool.py`
- `app/backend/tests/test_variant_report_publication_functional_integration.py`

Files updated:
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/tools/registry.py`
- `app/backend/app/tools/clinical_trials.py`
- `app/backend/app/tools/CLAUDE.md`
- `app/backend/app/fixtures/tools/CLAUDE.md`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_clinical_consensus.py`
- `plans/variant-report-data-orchestration/plan.md`
- `docs/proprietary/variant-report-orchestration.md`
- `docs/proprietary/index.json`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added a source-backed fixture-first `ComputationalAnnotationsTool` that
  matches by gene plus variant identifiers and returns empty/missing state for
  non-matching variants instead of bleeding RPE65 fixture rows.
- Added the RPE65 first-slice computational annotation fixture with SpliceAI
  DS/DP component scores, max delta/consequence, REVEL, CADD PHRED,
  PrimateAI-3D, MetaLR, phyloP100way, GERP++ RS, source URLs, and version
  labels.
- Wired `LookupService` to run `computational_annotations` during Variant
  Evidence Report lookup and updated `VariantReportDataOrchestrator` so
  `report_profile.computational_deep_dive` prefers these source-labeled rows
  over the legacy in-silico cards.
- Kept AlphaMissense filtered/on hold; no AlphaMissense value is surfaced.
- Integrated parallel sidecar hardening:
  - ACMG ledger regression proving source-asserted criteria stay separate from
    Eamos hints and hints do not overwrite final classification.
  - Publication/functional integration regression proving EP-VLEx publication
    inventory and functional-study count remain distinct.
  - ClinicalTrials.gov v2 structured parser/helper first slice with NCT
    discovery links, match-level labels, fallback query ordering, and
    no-eligibility warnings. `report_profile.therapies_trials.trial_rows`
    integration remains a later Task 9 step.

Verification completed:
- `cd app/backend && python -m pytest tests/test_tool_invariants.py tests/test_variant_report_orchestration.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_tool_invariants.py tests/test_variant_report_orchestration.py tests/test_variant_search_integration.py tests/test_frontend_contract.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_clinical_consensus.py tests/test_clinical_trials_tool.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_variant_report_publication_functional_integration.py tests/test_publication_literature.py tests/test_functional_evidence.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_tool_invariants.py tests/test_variant_report_orchestration.py tests/test_variant_search_integration.py tests/test_frontend_contract.py tests/test_clinical_consensus.py tests/test_clinical_trials_tool.py tests/test_variant_report_publication_functional_integration.py tests/test_publication_literature.py tests/test_functional_evidence.py -q`
  -> passed.
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed (existing short test-JWT
  warnings only).

Out of scope: frontend TypeScript mirror/rendering, live MyVariant/dbNSFP/CADD
API integration, local/precomputed SpliceAI service implementation,
PrimateAI-3D licensed data ingestion, `report_profile.therapies_trials`
integration, Patient Report Pipeline (`/runs`), AlphaMissense, commits,
pushes, stashes, resets, and cleans.

**Task Variant Report Data Orchestration Task 6 - Molecular context + structural overlap.**

Status: DONE 2026-05-23 18:22 +1000 - Codex. Completed after user approved
continuing backend-only with the next report-profile section.

Files added:
- `app/backend/app/tools/molecular_context.py`
- `app/backend/app/fixtures/tools/molecular_context_fixtures.json`

Files updated:
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/services/report_provenance.py`
- `app/backend/app/services/search_input_resolver.py`
- `app/backend/app/tools/ensembl_vep.py`
- `app/backend/app/tools/variant_validator.py`
- `app/backend/app/tools/registry.py`
- `app/backend/app/tools/CLAUDE.md`
- `app/backend/app/fixtures/tools/CLAUDE.md`
- `app/backend/app/fixtures/tools/vep_fixtures.json`
- `app/backend/app/fixtures/tools/variant_validator_fixtures.json`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_variant_search_integration.py`
- `plans/variant-report-data-orchestration/plan.md`
- `docs/proprietary/variant-report-orchestration.md`
- `docs/proprietary/index.json`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added a source-backed fixture-first `MolecularContextTool` for gnomAD gene
  constraint, ClinGen dosage sensitivity, and molecular-context provenance.
- Added the RPE65 first-slice fixture with LOEUF `1.0`, pLI `0.0`, ClinGen
  haploinsufficiency `Gene Associated with Autosomal Recessive Phenotype (30)`,
  triplosensitivity `No Evidence for Triplosensitivity (0)`, source URLs, and
  source release/version labels.
- Extended VEP and VariantValidator summaries/fixtures with molecular-context
  fields (`exon`, `codons`, `strand`) so the section can prefer source-backed
  coordinates over legacy display prose.
- Wired `LookupService` to run `molecular_context` during Variant Evidence
  Report lookup and internally resolve the existing sequence-context fixture
  for reverse-strand codon detail.
- Updated `VariantReportDataOrchestrator` so
  `report_profile.molecular_context` now returns chromosome 1, reverse strand,
  exon 4, codon change `GAC>GGC`, protein position 87, LOEUF 1.0, and ClinGen
  haploinsufficiency with provenance versions.
- Left domain, hotspot, and structural CNV overlap empty with explicit
  not-hydrated warnings; no unsupported structural claim is surfaced.
- Preserved the existing additive `report_profile` contract shape; no frontend
  TypeScript fields were added in this slice.

Verification completed:
- `cd app/backend && python -m pytest tests/test_variant_report_orchestration.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_tool_invariants.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_variant_search_integration.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_search_input_resolver.py tests/test_variant_search_integration.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`
  -> passed.
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed after formatting `lookup_service.py` and
  `variant_report_orchestrator.py`.
- `cd app/backend && python -m pytest -q` -> passed (existing short test-JWT
  warnings only).

Out of scope: frontend TypeScript mirror/rendering, UniProt/AlphaFold/PDB
domain mapping, full structural CNV overlap adapter, Patient Report Pipeline
(`/runs`), AlphaMissense, commits, pushes, stashes, resets, and cleans.

**Task Variant Report Data Orchestration Task 5 - Disease mechanism + inheritance.**

Status: DONE 2026-05-23 17:52 +1000 - Codex. Completed after user approved
continuing backend-only with the next report-profile section.

Files added:
- `app/backend/app/tools/gene_disease.py`
- `app/backend/app/fixtures/tools/gene_disease_fixtures.json`

Files updated:
- `app/backend/app/core/config.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/tools/registry.py`
- `app/backend/app/tools/CLAUDE.md`
- `app/backend/app/fixtures/tools/CLAUDE.md`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_variant_search_integration.py`
- `plans/variant-report-data-orchestration/plan.md`
- `docs/proprietary/variant-report-orchestration.md`
- `docs/proprietary/index.json`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added a source-backed `GeneDiseaseTool` for disease mechanism,
  inheritance, disease identifiers, gene-disease validity, and per-source
  provenance.
- Added the RPE65 first-slice fixture with HGNC, ClinGen Gene-Disease
  Validity, NCBI MedGen, and Orphadata provenance. Disease IDs include OMIM,
  MedGen, MONDO, and ORPHA-style identifiers when available.
- Wired `LookupService` to run `gene_disease` evidence during Variant Evidence
  Report lookup.
- Updated `VariantReportDataOrchestrator` so
  `report_profile.disease_mechanism` prefers `gene_disease` evidence and only
  falls back to legacy `associated_conditions` when the new source is absent.
- Preserved the existing additive `report_profile` contract shape; no frontend
  TypeScript fields were added in this slice.
- Kept missing penetrance as `null` with `penetrance_not_source_backed` rather
  than fabricating a value.

Verification completed:
- `cd app/backend && python -m pytest tests/test_tool_invariants.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_variant_report_orchestration.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_variant_search_integration.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`
  -> passed.
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed (existing short test-JWT
  warnings only).

Out of scope: frontend TypeScript mirror/rendering, OMIM licensed API work,
bulk disease ontology ingestion, Patient Report Pipeline (`/runs`),
AlphaMissense, commits, pushes, stashes, resets, and cleans.

**Task Variant Report Data Orchestration Task 4 - ClinGen/ClinVar clinical consensus + ACMG ledger.**

Status: DONE 2026-05-23 13:16 +1000 - Codex. Completed after user approved
continuing backend-first before the frontend mirror/render.

Files added:
- `app/backend/app/services/clinical_consensus.py`
- `app/backend/app/tools/clingen.py`
- `app/backend/app/fixtures/tools/clingen_fixtures.json`
- `app/backend/tests/test_clinical_consensus.py`

Files updated:
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/report_call_cards.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/app/tools/registry.py`
- `app/backend/app/tools/CLAUDE.md`
- `app/backend/app/fixtures/tools/CLAUDE.md`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `app/backend/tests/test_variant_search_integration.py`
- `plans/variant-report-data-orchestration/plan.md`
- `docs/proprietary/variant-report-orchestration.md`
- `docs/proprietary/index.json`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added a ClinGen ERepo adapter with fixture-backed and live summary
  classification lookup.
- Added clinical consensus assembly that prefers ClinGen/VCEP classifications
  over ClinVar, falls back to ClinVar when ClinGen has no variant record, and
  keeps source-asserted ACMG criteria separate from Eamos worksheet hints.
- Added ClinVar VCV XML comment/attribute parsing for source-asserted ACMG
  criteria and PMID refs when VCV XML is available.
- Wired Card 4, `report_profile.header`, deterministic interpretation summary,
  and `report_profile.acmg_worksheet` to the source-priority consensus result.
- Preserved the existing additive `report_profile` contract shape; no frontend
  TypeScript fields were added in this slice.

Verification completed:
- `cd app/backend && python -m pytest tests/test_clinical_consensus.py tests/test_tool_invariants.py tests/test_variant_report_orchestration.py tests/test_variant_search_integration.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_variant_search_integration.py tests/test_functional_evidence.py tests/test_tool_invariants.py tests/test_frontend_contract.py tests/test_variant_report_orchestration.py tests/test_clinical_consensus.py -q`
  -> passed.
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed (existing short test-JWT
  warnings only).

Out of scope: full ACMG classification engine, frontend mirror/rendering,
Patient Report Pipeline (`/runs`), AlphaMissense, live ClinGen/ClinVar VCV
smoke, commits, pushes, stashes, resets, and cleans.

**Task Variant Report Data Orchestration Tasks 1-3 - Report profile spine.**

Status: DONE 2026-05-23 12:10 +1000 - Codex. Completed after the user
approved `plans/variant-report-data-orchestration/plan.md` Tasks 1-3.

Files added:
- `app/backend/app/services/report_extraction_plan.py`
- `app/backend/app/services/report_provenance.py`
- `app/backend/app/services/variant_report_orchestrator.py`
- `app/backend/tests/test_variant_report_orchestration.py`
- `docs/proprietary/variant-report-orchestration.md`

Files updated:
- `app/backend/app/schemas/run.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/tests/test_frontend_contract.py`
- `docs/proprietary/README.md`
- `docs/proprietary/index.json`
- `plans/variant-report-data-orchestration/plan.md`
- `plans/v2-backend.md`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added additive `ReportPayload.report_profile` with typed header,
  deterministic interpretation summary, disease mechanism, molecular context,
  computational deep dive, ACMG worksheet, therapies/trials, and provenance.
- Added a section-aware `ReportExtractionPlan` that keeps canonical identity,
  source query bundles, section match levels, and warnings auditable.
- Added match-level gates so gene/disease-only or confirmation-required inputs
  cannot silently populate variant-level computational, ACMG, publication,
  population, or splicing claims.
- Kept publication variant aliases separate from gene fallback terms.
- Added `VariantReportDataOrchestrator` and `report_provenance` helpers so
  `LookupService` delegates profile assembly after existing call-card,
  population, EP-VLEx, and functional-evidence groups are built.
- Omitted `therapy_rows` in the first slice; `TherapiesTrialsSection` exposes
  empty structured `trial_rows` with explicit first-slice/gene-level fallback
  warnings until Task 9 lands a structured trials source.
- Kept AlphaMissense hidden in the computational deep dive while the hold is
  active.

Verification completed:
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed.
- `cd app/backend && python -m pytest tests/test_variant_report_orchestration.py tests/test_variant_search_integration.py tests/test_search_input_resolver.py tests/test_frontend_contract.py tests/test_publication_literature.py tests/test_functional_evidence.py -q`
  -> passed.
- `cd app/backend && python -m pytest tests/test_variant_cache.py tests/test_tool_invariants.py tests/test_gnomad_tool.py -q`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed (existing short test-JWT
  warnings only).

Out of scope: frontend TypeScript mirror/rendering, new live source adapters,
structured ClinicalTrials.gov rows, ClinGen/VCEP adapter work, Patient Report
Pipeline (`/runs`), AlphaMissense, commits, pushes, stashes, resets, and
cleans.

**Task Variant Report Data Orchestration - design/spec/plan.**

Status: PLANNED 2026-05-22 00:09 +1000 - Codex. Completed a backend
architecture planning pass after the user supplied the final Variant Evidence
Report layout documents and clarified that the supercharged search bar should
accurately extract relevant data for the right report sections.

Files added:
- `plans/variant-report-data-orchestration/design.md`
- `plans/variant-report-data-orchestration/spec.md`
- `plans/variant-report-data-orchestration/plan.md`

Planning outcome:
- Treat the search bar as a section-aware evidence planner, not just an input
  parser.
- Add a planned `ReportExtractionPlan` concept that maps interpreted user input
  to canonical identity, source-specific query bundles, report section targets,
  and match levels (`variant_level`, `gene_level`, `disease_level`,
  `unavailable`).
- Keep existing `call_cards`, `population_frequency_detail`,
  `functional_evidence`, and `publications_literature` as canonical detailed
  groups where they already work.
- Add a planned optional `ReportPayload.report_profile` for the remaining
  typed layout sections: header, interpretation summary, disease mechanism,
  molecular context, computational deep dive, ACMG worksheet, therapies/trials,
  and provenance.
- Source strategy recorded: ClinGen/VCEP first for curated clinical consensus
  and source-asserted ACMG criteria, ClinVar next, Eamos criteria only as
  worksheet hints; PubMed/EP-VLEx for all variant-related publications; gene-
  level ClinicalTrials.gov results allowed when variant-level trials are absent
  and clearly labeled.
- Additional source needs identified: HGNC, MedGen/Orphadata, optional OMIM
  with license/API approval, gnomAD constraint/ClinGen dosage, dbNSFP/CADD/
  PrimateAI-3D, optional CIViC for oncology, optional ClinPGx/PharmGKB/openFDA
  for therapy/drug-label context.

Verification:
- `git diff --check -- plans\variant-report-data-orchestration\design.md plans\variant-report-data-orchestration\spec.md plans\variant-report-data-orchestration\plan.md`
  -> passed.

Out of scope: implementation, frontend TypeScript mirror/rendering, Patient
Report Pipeline (`/runs`), AlphaMissense, live-provider AI smoke, commits,
pushes, stashes, resets, and cleans.

**Task Search Bar AI Input Tasks 1-3 - Web contract and candidate resolution.**

Status: DONE 2026-05-21 19:07 +1000 - Codex. Completed after the user approved
implementing `plans/search-bar-ai-input/plan.md` Tasks 1-3.

Files added:
- `app/backend/app/services/search_input_interpreter.py`
- `app/backend/app/services/search_candidate_resolver.py`
- `app/backend/app/fixtures/search_candidate_records.json`

Files updated:
- `app/backend/app/schemas/lookup.py`
- `app/backend/app/api/routes/lookup.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/search_input_resolver.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_frontend_contract.py`
- `plans/search-bar-ai-input/plan.md`
- `plans/v2-backend.md`
- `PROGRESS.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added additive search-input schemas and `POST /api/v1/lookup/parse` for
  deterministic parse preview without running the full evidence stack.
- Added canonical raw `LookupRequest.search_text`, alias `query`, mixed-mode
  validation, and optional `LookupResponse.search_interpretation`.
- Wired raw exact inputs through the backend interpreter and then the existing
  Variant Evidence Report lookup path.
- Added first-slice source-labeled candidate resolution for exact
  source-backed matches, protein/codon-level ambiguity, and near-miss cDNA or
  protein input.
- Captured the corrected CFTR proof-of-concept as a recommendation:
  `CFTR:p.Leu441fs` returns a ranked suggestion toward
  `CFTR c.1321_1323del (p.Leu441del)` and does not auto-select the
  non-existent frameshift.

Verification completed:
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed.
- `cd app/backend && python -m pytest tests/test_variant_search_integration.py tests/test_search_input_resolver.py tests/test_lookup_normalize.py tests/test_frontend_contract.py tests/test_tool_invariants.py tests/test_gnomad_tool.py tests/test_variant_cache.py -q`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed (rerun 2026-05-21
  19:07 +1000; existing JWT test-key
  warnings only).

Out of scope: frontend TypeScript mirror/rendering, AI extraction (Task 4),
Patient Report Pipeline (`/runs`), AlphaMissense, live AI smoke, commits,
pushes, stashes, resets, and cleans.

**Task Search Bar AI Input Task 4 - Mock-first AI plain-language extractor.**

Status: DONE 2026-05-21 23:09 +1000 - Codex. Completed after the user approved
the next backend task and supplied AI chatbot/dictionary notes to consider.

Files added:
- `app/backend/app/services/search_input_ai.py`
- `app/backend/app/fixtures/search_input_lexicon.json`

Files updated:
- `app/backend/app/schemas/lookup.py`
- `app/backend/app/core/config.py`
- `app/backend/app/agents/client.py`
- `app/backend/app/agents/prompts.py`
- `app/backend/app/agents/__init__.py`
- `app/backend/app/services/search_input_interpreter.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_frontend_contract.py`
- `plans/search-bar-ai-input/plan.md`
- `docs/proprietary/`
- `PROGRESS.md`
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added opt-in `SEARCH_INPUT_AI_ENABLED=false` default gating plus an
  8-second live-provider timeout setting.
- Added `SearchInputAiExtraction` and a guarded live structured-output chain
  that uses server-side API keys only when explicitly enabled.
- Added a mock-first `SearchInputAiExtractor` with a small curated
  search-input lexicon for gene aliases, amino-acid terms, and consequence
  terms. This is the first backend dictionary slice; broader reference coverage
  remains Task 5.
- Wired AI extraction only after deterministic parsing is unknown or
  gene-missing. Exact deterministic HGVS/genomic inputs do not call AI.
- Preserved the invariant that AI proposes intent only: protein-only plain
  language goes through deterministic validation and source-backed candidate
  resolution before any report can run.
- Covered CFTR Leu441 examples: frameshift text returns a source-backed
  recommendation toward the corrected deletion candidate; deletion text
  auto-selects the one source-backed CFTR Leu441 deletion candidate.
- Added prompt-injection phrase handling in mock mode and hardened the live
  prompt to treat submitted text/reference context as data, not instructions.

Verification completed:
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed.
- `cd app/backend && python -m pytest tests/test_variant_search_integration.py tests/test_search_input_resolver.py tests/test_lookup_normalize.py tests/test_frontend_contract.py -q`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed (existing JWT test-key
  warnings only).

Out of scope: frontend TypeScript mirror/rendering, live AI smoke, vector RAG,
bulk disease ontology ingestion, Patient Report Pipeline (`/runs`),
AlphaMissense, commits, pushes, stashes, resets, and cleans.

**Task Search Bar AI Input Task 5 first slice - Curated dictionary helper.**

Status: DONE 2026-05-21 23:26 +1000 - Codex. Completed after the user clarified
that the dictionary should assist agents/backend code and add to the existing
resolver/scripts, not replace them.

Files added:
- `app/backend/app/services/search_input_reference.py`
- `app/backend/tests/test_search_input_reference.py`

Files updated:
- `app/backend/app/services/search_input_ai.py`
- `app/backend/tests/test_variant_search_integration.py`
- `plans/search-bar-ai-input/plan.md`
- `PROGRESS.md`
- `plans/v2-backend.md`
- `docs/proprietary/search-input-ai.md`
- `docs/proprietary/index.json`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added `SearchInputReference`, a reusable helper over the curated
  search-input lexicon for gene aliases, amino-acid names/codes, consequence
  terms, and live-prompt reference context.
- Rewired the mock AI extractor through the helper while keeping the existing
  deterministic resolver and source-backed candidate resolver as the authority.
- Added the exact hamburger prompt guardrail regression from the user's AI
  notes. The prompt stays low-confidence, records
  `prompt_injection_phrase_ignored`, and produces no variant extraction or
  recipe-like response.
- Added helper tests for CFTR alias mapping, amino-acid nomenclature, and
  frameshift term normalization.

Verification completed:
- `cd app/backend && python -m pytest tests/test_search_input_reference.py tests/test_variant_search_integration.py tests/test_search_input_resolver.py -q`
  -> passed.
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed (existing JWT test-key
  warnings only).

Out of scope: frontend edits, live AI smoke, vector RAG, bulk disease ontology
ingestion, HGNC API integration, Patient Report Pipeline (`/runs`),
AlphaMissense, commits, pushes, stashes, resets, and cleans.

**Task Search Bar AI Input Task 5 broader dictionary + Task 7 smoke hardening.**

Status: DONE 2026-05-21 23:44 +1000 - Codex. Completed after the user approved
starting the broader curated dictionary work and live AI smoke/hardening. Task
6 frontend UX remains Claude-owned and is not a backend dependency.

Files added:
- `app/backend/app/cli/search_input_ai_smoke.py`
- `app/backend/tests/test_search_input_ai_smoke_cli.py`

Files updated:
- `app/backend/app/fixtures/search_input_lexicon.json`
- `app/backend/app/services/search_input_reference.py`
- `app/backend/app/services/search_input_ai.py`
- `app/backend/tests/test_search_input_reference.py`
- `app/backend/tests/test_variant_search_integration.py`
- `plans/search-bar-ai-input/plan.md`
- `docs/proprietary/search-input-ai.md`
- `docs/proprietary/index.json`
- `PROGRESS.md`
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Broadened the curated search-input lexicon with gene aliases, ambiguous
  disease/gene hints, MANE transcript hints, chromosome UI aliases, amino-acid
  terms, consequence terms, ClinVar-style display vocabulary, and ACMG display
  vocabulary.
- Extended `SearchInputReference` with helper methods for ambiguous disease
  hints, chromosome normalization, transcript hints, and display-only
  ClinVar/ACMG labels. These remain helper facts only; they do not assign
  final cDNA/genomic alleles.
- Hardened the AI extractor so prompt-injection text with no variant signal is
  blocked before a live provider call. Variant-bearing prompt-injection text
  preserves `prompt_injection_phrase_ignored`.
- Added `python -m app.cli.search_input_ai_smoke`, an opt-in mock/live smoke
  harness that reports interpretation, candidates, expectation failures, and
  whether a report would be allowed. Low-confidence or confirmation-required
  outputs are not report-runnable.
- Added regression coverage for ambiguous disease hints such as
  `retinal dystrophy gene variant`, which now returns low-confidence
  suggestions and `ambiguous_gene_hint:retinal dystrophy gene` instead of a
  guessed gene.

Verification completed:
- `cd app/backend && python -m pytest tests/test_search_input_reference.py tests/test_search_input_ai_smoke_cli.py tests/test_variant_search_integration.py -q`
  -> passed (33 tests).
- `cd app/backend && python -m app.cli.search_input_ai_smoke --mock --expect-gene CFTR --expect-protein p.Leu441fs --expect-mode suggestions --expect-candidate-id source:CFTR_c.1321_1323del --compact`
  -> passed.
- `cd app/backend && python -m app.cli.search_input_ai_smoke --skip-if-unconfigured --compact`
  -> skipped cleanly because this environment is not configured/enabled for
  live AI (`SEARCH_INPUT_AI_ENABLED=false`, `LLM_PROVIDER=mock`, no
  `OPENAI_API_KEY`).
- `cd app/backend && python -m ruff check app tests` -> passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> passed.
- `cd app/backend && python -m pytest -q` -> passed (existing JWT test-key
  warnings only).

Out of scope: frontend edits, actual live-provider call without configured
provider settings, vector RAG, bulk ontology/HGNC ingestion, Patient Report
Pipeline (`/runs`), AlphaMissense, commits, pushes, stashes, resets, and
cleans.

**Task RP source-input CLI - Developer Eamos Search Input stack.**

Status: DONE 2026-05-21 17:54 +1000 - Codex. Completed after the user supplied
additional search examples and identified the search input path as the lynchpin
for the web tool.

Files added:
- `app/backend/app/cli/__init__.py`
- `app/backend/app/cli/eamos_search_input.py`
- `app/backend/tests/test_eamos_search_input_cli.py`

Files updated:
- `app/backend/app/services/search_input_resolver.py`
- `app/backend/app/services/sequence_context.py`
- `app/backend/tests/test_search_input_resolver.py`
- `app/backend/tests/test_lookup_normalize.py`
- `PROGRESS.md`
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added `python -m app.cli.eamos_search_input` as a developer CLI that prints
  parsed, normalized, and per-source inputs from `EamosSearchInputResolver`.
- Added CLI support for a single query or an input file. File mode consumes the
  first tab-separated column, so annotated test stacks can be run directly.
- Added `parse_search_text()` / `resolve_text()` to the resolver layer so the
  future web search bar can reuse the same backend parser.
- Accepted the supplied loose formats:
  `GENE:c.`, transcript-with-gene HGVS plus protein alias,
  `chr-pos-ref-alt`, `chrom pos ref alt`, `chrom:pos ref>alt`, and
  `chrom:pos:ref:alt`.
- Normalized chromosome aliases for source calls (`chr8` -> `8`, `MT` -> `M`).
- Extended gnomAD-style non-SNV conversion to NC genomic HGVS for simple VCF
  anchored insertions, deletions, and delins forms, so ClinVar,
  VariantValidator, and VEP can receive RefSeq genomic HGVS where possible.

Verification completed:
- `cd app/backend && python -m pytest tests/test_search_input_resolver.py tests/test_lookup_normalize.py tests/test_eamos_search_input_cli.py -q`
  -> passed (22 tests).
- `cd app/backend && python -m ruff check app/services/search_input_resolver.py app/services/sequence_context.py app/cli/eamos_search_input.py tests/test_search_input_resolver.py tests/test_lookup_normalize.py tests/test_eamos_search_input_cli.py`
  -> passed.
- `cd app/backend && python -m black --check --target-version py310 app/services/search_input_resolver.py app/services/sequence_context.py app/cli/eamos_search_input.py tests/test_search_input_resolver.py tests/test_lookup_normalize.py tests/test_eamos_search_input_cli.py`
  -> passed.
- `cd app/backend && python -m pytest tests/test_search_input_resolver.py tests/test_tool_invariants.py tests/test_gnomad_tool.py tests/test_lookup_normalize.py tests/test_eamos_search_input_cli.py -q`
  -> passed (35 tests).
- Direct fixture-mode CLI run against the user-supplied
  `Variant test stack.txt` parsed all 10 nonblank examples and emitted
  source-specific query bundles.

Out of scope: frontend search bar contract changes, Patient Report Pipeline
(`/runs`), AlphaMissense, MyVariant/dbNSFP, local/precomputed SpliceAI,
ClinicalTrials.gov implementation, commits, pushes, stashes, resets, and
cleans.

**Task RP source-input resolver - Eamos Search Input stack.**

Status: DONE 2026-05-21 00:14 +1000 - Codex. Completed after the user
clarified that Variant Evidence Report source calls must resolve all relevant
identifiers and choose source-appropriate inputs rather than assuming gene and
codon strings are sufficient.

Files added:
- `app/backend/app/services/search_input_resolver.py`
- `app/backend/tests/test_search_input_resolver.py`

Files updated:
- `app/backend/app/services/sequence_context.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/tools/variant_validator.py`
- `app/backend/app/tools/ensembl_vep.py`
- `app/backend/app/tools/clinvar.py`
- `app/backend/app/tools/gnomad.py`
- `app/backend/app/tools/spliceai.py`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_gnomad_tool.py`
- `app/backend/tests/test_lookup_normalize.py`
- `PROGRESS.md`
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`

Implementation completed:
- Added `EamosSearchInputResolver`, which normalizes user-submitted variant
  text, resolves missing MANE/RefSeq transcript accessions in live mode, and
  produces source-specific inputs for VariantValidator, Ensembl VEP, gnomAD,
  SpliceAI, ClinVar, and literature term building.
- Added parsing for gnomAD-style genomic IDs (`chr-pos-ref-alt`) and RefSeq
  genomic HGVS SNVs, using the correct GRCh38 NC accession versions.
- Wired lookup and publication lookup variant objects with
  `search_input_resolution`, `genomic_hg38`, and `genomic_hgvs` so downstream
  tools can use the right identifier for each source.
- Updated VariantValidator and VEP to use source-specific identifiers and to
  return stubs instead of firing invalid source calls when no usable identifier
  exists.
- Updated ClinVar to prefer resolved NC genomic HGVS after coordinate
  resolution, including indels/duplications, because transcript-only ClinVar
  search can return unrelated top hits.
- Changed ClinVar live no-hit behavior to return `Unavailable` / `not found`
  instead of unrelated fixture evidence.
- Removed unsafe VariantValidator fallback mutation from VEP raw data after
  live timeouts; this avoided wrong allele-orientation coordinates on
  transcript queries.
- Increased gnomAD and VariantValidator live timeouts from 15s to 30s.
- Added current source-input test-stack coverage for USH2A genomic input,
  RPGRIP1 `c.1997C>T`, and BRCA1 `c.5266dupC`.

Live source mappings verified:
- RPE65 `NM_000329.3(RPE65):c.11+5G>A` -> `NC_000001.11:g.68449890C>T` ->
  gnomAD `1-68449890-C-T`.
- RPE65 `NM_000329.3(RPE65):c.1301C>T (p.Ala434Val)` ->
  `NC_000001.11:g.68431319G>A` -> gnomAD `1-68431319-G-A`.
- USH2A `c.2276G>T (p.Cys759Phe)` -> MANE `NM_206933.4` ->
  `NC_000001.11:g.216247118C>A` -> gnomAD `1-216247118-C-A` -> ClinVar
  `VCV000002356`.
- RPGRIP1 `c.1997C>T` -> MANE `NM_020366.4` ->
  `NC_000014.9:g.21324852C>T` -> gnomAD `14-21324852-C-T`; gnomAD and
  ClinVar both return live no-hit.
- BRCA1 `c.5266dupC` -> MANE `NM_007294.4`, normalized transcript
  `NM_007294.4:c.5266dup` -> `NC_000017.11:g.43057065dup` -> gnomAD
  `17-43057062-T-TG` -> ClinVar `VCV000017677`.

Verification completed:
- `cd app/backend && python -m ruff check app/tools/clinvar.py app/tools/variant_validator.py app/tools/gnomad.py app/services/lookup_service.py app/services/search_input_resolver.py app/services/sequence_context.py tests/test_search_input_resolver.py tests/test_tool_invariants.py tests/test_gnomad_tool.py tests/test_lookup_normalize.py`
  -> passed.
- `cd app/backend && python -m pytest tests/test_search_input_resolver.py tests/test_tool_invariants.py tests/test_gnomad_tool.py tests/test_lookup_normalize.py -q`
  -> passed (25 tests).
- Live route smoke with `USE_REAL_APIS=true` and `?refresh=true` passed for
  RPE65 `c.11+5G>A`, RPE65 `c.1301C>T`, USH2A `c.2276G>T`, RPGRIP1
  `c.1997C>T`, and BRCA1 `c.5266dupC`. Each response returned the report
  `call_cards`, `population_frequency_detail`, and `functional_evidence`
  groups together; RPGRIP1 correctly returned no-hit source warnings instead
  of fallback fixture metrics.

Out of scope: frontend TypeScript mirror/rendering, Patient Report Pipeline
(`/runs`), AlphaMissense, MyVariant/dbNSFP, local/precomputed SpliceAI,
ClinicalTrials.gov implementation, commits, pushes, stashes, resets, and
cleans.
