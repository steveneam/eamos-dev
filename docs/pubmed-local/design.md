# PubMed Local Adapter Design

## Status

Draft.

## Summary

Eamos already has a live PubMed/E-utilities path and EP-VLEx, the backend
publication aggregation layer used by the Variant Evidence Report. The next
step should be a backend-owned local-first PubMed lane: explicitly materialize
PubMed citation metadata and abstracts into a searchable local store, query it
first for gene/variant literature, and keep live E-utilities as fallback and
targeted refresh.

The recommended first build is SQLite FTS5 plus explicit materialization and
preflight CLIs. This fits the current backend footprint, avoids startup
downloads, keeps provenance attached, and does not require a new database,
frontend contract, or non-permissive dependency.

## Context And Scope

Current publication path:

- `PubmedTool` builds a gene plus variant-identifier query and calls PubMed
  ESearch, ESummary, and EFetch through the NCBI E-utilities base URL.
- `LitVar2Tool` resolves a variant to PMIDs and returns PMID stubs.
- `EamosProprietaryVariantLiteratureExtractor` in
  `publication_literature.py` builds variant terms, dedupes PMIDs across
  PubMed/LitVar2/ClinVar, extracts snippets, and emits
  `PublicationLiterature`.
- `LookupService.lookup()` wires PubMed, LitVar2, and EP-VLEx into
  `ReportPayload.publications_literature` and keeps `pubmed_articles`
  backward-compatible.
- `POST /api/v1/lookup/publications` re-runs ClinVar/PubMed/LitVar2 for
  paginated publication expansion.

Source-asset context:

- Local source assets are explicit materializations, not app startup work.
- Health and preflight output should be sanitized, non-throwing, and specific
  about readiness.
- Runtime source usage needs source version, checksum/update identity,
  materialization status, provenance, and clear fallback behavior.
- PubMed baseline/update XML is the right bulk input. NLM documents annual
  baseline files, daily update files, MD5 sidecars, and load order.
- NCBI E-utilities remains rate-limited and should be used for fallback or
  bounded refresh, not high-volume request-time recovery.
- NLM freely provides PubMed data, but some abstracts may be protected by
  copyright. The local lane should enable backend search, not bulk abstract
  redistribution.

This document covers backend architecture only. It does not authorize code
edits, frontend work, Supabase migrations, production imports, or Patient
Report Pipeline changes.

## Goals

- Serve Variant Evidence Report publication lookup from verified local PubMed
  metadata and abstract search when available.
- Preserve the current `PublicationLiterature` and `PubMedArticle` contract for
  the first slice.
- Keep live E-utilities as fallback and explicit refresh.
- Require an explicit materialization CLI and preflight before runtime use.
- Store only de-identified, cache-safe public citation data and provenance; no
  patient context or user query history.
- Preserve source version, update sequence, checksum status, copyright
  metadata, and PubMed source links.
- Use permissive/open-source implementation dependencies only.
- Build the first slice with tiny fixtures or small local shards today.

## Non-Goals

- No `/runs`, Patient Report Pipeline, PDF intake, or clinician-review work.
- No frontend or TypeScript mirror work.
- No startup, build-time, predeploy, or one-off-job PubMed downloader.
- No publisher scraping, paywalled full text, PMC full-text import, PubTator
  bulk edge import, MedCPT/vector search, LLM summarization, or AI gateway work
  in the first slice.
- No Supabase migration/import unless separately approved after local proof.

## Constraints

- Default tests stay offline and deterministic.
- Local PubMed reads fail closed when the DB, manifest, FTS index, checksum, or
  update sequence is invalid.
- Lookup fails open to the existing live/fallback PubMed behavior when local
  PubMed is disabled or not ready.
- Preflight and health must not emit secrets, absolute local paths, private
  object URIs, or raw filesystem layout.
- The local store is backend-only: no browser role, public bucket, signed raw
  object URL, or frontend direct database access.
- Abstract text may be indexed for search, but public APIs should stay bounded
  to citation metadata, PubMed links, selected top rows, and short snippets. Do
  not add a bulk abstract export.
- Use existing backend primitives where possible: stdlib XML parsing,
  `sqlite3`/SQLite FTS5, `ToolResult`, existing cache conventions, and existing
  Pydantic schemas.

## Proposed Architecture

Add a backend PubMed local package with four pieces.

1. `PubMedLocalStore`: repository over a materialized SQLite database with FTS5
   indexes for title, abstract, author, journal, DOI, PMID, PMCID, MeSH terms,
   and normalized identifier text.
2. `PubMedLocalAdapter`: `ToolResult`-compatible adapter that accepts the same
   resolved variant object as `PubmedTool`, searches local FTS first, and
   returns the current PubMed summary shape.
3. `eamos_pubmed_materialize`: explicit CLI that imports local PubMed
   baseline/update XML shards, verifies MD5 sidecars when available, applies
   revised/deleted citation semantics, and atomically publishes a ready DB plus
   manifest.
4. `eamos_pubmed_preflight`: read-only CLI/health helper that reports sanitized
   readiness, row counts, FTS status, source/update identity, and failure
   reasons.

Runtime flow:

```text
resolved variant
  -> PubMedLocalAdapter if enabled and preflight-ready
  -> else live PubmedTool when USE_REAL_APIS allows it
  -> else fixture/missing behavior as today
  -> EP-VLEx aggregation unchanged
  -> PublicationLiterature unchanged
```

EP-VLEx remains the publication reasoning layer. The new adapter only changes
how PubMed evidence is acquired.

SQLite FTS5 is the first-store decision because it has no new package/service
dependency, works on Windows and Render Linux, supports atomic replacement, and
is enough for fixture/small-shard proof. DuckDB, Postgres full-text, and
pgvector can be revisited after local search quality and corpus size are
measured.

## Materialization Flow

1. Operator stages PubMed XML shards outside app startup.
2. `python -m app.cli.eamos_pubmed_materialize --input-dir <dir> --db-path
   <path> --compact` performs a dry-run plan by default.
3. With `--apply`, the CLI verifies available `.md5` sidecars, streams XML,
   upserts new/revised PMIDs, marks deleted citations, builds FTS, writes the
   manifest, runs integrity checks, and atomically publishes the DB.
4. `python -m app.cli.eamos_pubmed_preflight --db-path <path> --require-ready
   --compact` reports readiness without leaking local paths.
5. Runtime local use is enabled only after preflight is green, through settings
   such as `PUBMED_LOCAL_ENABLED=true` and `PUBMED_LOCAL_DB_PATH=<mounted
   path>`.
6. Lookup uses local first. If local is not ready, it records a warning and
   uses live E-utilities or fixture behavior according to existing settings.

For Render, the DB belongs on persistent disk under the Eamos runtime asset
tree. Seed it through Render Shell/SCP or a committed backend CLI run from the
live service shell. Do not seed it through build, predeploy, one-off jobs that
cannot reach the service disk, or app startup.

## Interfaces And Data

Minimum local DB tables:

- `pubmed_article`: PMID, title, abstract, journal, date/year, authors JSON,
  DOI, PMCID, MeSH terms, publication types, language, copyright information,
  citation status, deleted flag, source/update identity, and updated timestamp.
- `pubmed_article_fts`: FTS5 virtual table over title, abstract, authors,
  journal, identifiers, MeSH, and normalized aliases.
- `pubmed_materialization_manifest`: baseline year, loaded shard/update range,
  MD5/checksum status, row counts, deleted count, PubMed DTD/source version,
  importer version, ready marker, and created timestamp.
- Optional `pubmed_local_term_cache` only after profiling shows repeated
  gene/variant searches need cached PMID lists.

Adapter output should match `PubmedTool`:

- `articles`: `PubMedArticle`-compatible dicts;
- `total`: variant-scope loaded row count;
- `gene_scope`: optional gene-wide count with `gene_wide_source_count`;
- `request_identity`: local query terms plus materialization version;
- `status`: `local`;
- `source_url`: PubMed URL, never a local DB path.

Settings can be added later:

- `PUBMED_LOCAL_ENABLED=false`
- `PUBMED_LOCAL_DB_PATH=./data/bio_assets/pubmed/pubmed-local.sqlite`
- `PUBMED_LOCAL_REQUIRE_READY=true`
- `PUBMED_LOCAL_RETURN_ABSTRACTS=false` initially unless preserving current
  top-row abstract exposure is explicitly required.
- `PUBMED_EUTILS_TOOL`, `PUBMED_EUTILS_EMAIL`, and optional server-side
  `PUBMED_EUTILS_API_KEY`.

Query semantics should reuse current resolver/EP-VLEx terms: gene, transcript
HGVS, cDNA HGVS, protein aliases, rsID, and genomic GRCh38 alias. Variant-scope
search should require gene plus at least one non-gene variant term when variant
identity exists. Gene-only results remain gene-scope counts, not variant-scope
evidence.

## Alternatives Considered

- **Live E-utilities only:** simplest, but keeps latency, rate limits, and
  source availability tied to request-time NCBI calls.
- **Existing source/variant cache only:** useful for recent lookups, but not a
  searchable PubMed corpus and not a baseline/update materialization model.
- **Supabase Postgres first:** plausible later, but requires migrations,
  import approval, and deployment policy before proving the adapter.
- **DuckDB/Parquet first:** useful for analytics, but adds dependency review
  and does not fit current runtime health/preflight as directly.
- **Startup downloader:** rejected. It violates the source-asset rule and makes
  deploys non-deterministic.
- **Full PMC/PubTator/MedCPT now:** valuable later, but too broad for today's
  PubMed local proof.

## Risks

- **Copyright and redistribution:** abstracts may have third-party rights.
  Mitigation: keep abstract search backend-only, return bounded snippets/top
  rows, preserve copyright metadata, and link out to PubMed.
- **Corpus size:** full baseline plus FTS may be large. Mitigation: fixture and
  small-shard proof first, explicit disk reporting, and no assumption that this
  fits the existing 60 GB genomic/protein disk plan.
- **Freshness drift:** PubMed updates include revised and deleted citations.
  Mitigation: manifest update sequence, stale thresholds, gap detection, and
  live fallback.
- **False positives:** gene-only literature can swamp variant evidence.
  Mitigation: variant-scope requires non-gene terms and snippet evidence;
  gene-wide counts remain explicitly labelled.
- **Partial reads:** request handlers must not see half-built DBs. Mitigation:
  build in staging, verify, then atomic rename.

## Rollout

1. Approve this design.
2. Implement tiny-fixture SQLite schema, importer, preflight, and local adapter
   without runtime wiring.
3. Add tests for missing DB, corrupt DB, manifest gaps, FTS readiness,
   sanitized output, query ranking, and EP-VLEx integration.
4. Wire `LookupService` to prefer local PubMed only behind disabled-by-default
   settings and green preflight.
5. Materialize a small USH2A/RPE65/BRCA1 shard for local verification.
6. Run focused backend tests:
   `test_publication_literature.py`, `test_variant_search_integration.py`,
   `test_variant_cache.py`, `test_frontend_contract.py`, plus new PubMed local
   materialization tests.
7. Decide separately whether to stage a full PubMed baseline/update corpus and
   where its disk footprint belongs.

Backout is `PUBMED_LOCAL_ENABLED=false`; live PubMed behavior remains intact.

## Open Questions

- What disk budget should PubMed baseline plus FTS get, separate from the
  existing genomic/protein asset plan?
- Should local results populate `PubMedArticle.abstract`, or should local
  lookup prefer snippets and links while keeping abstracts private to search?
- Should `ready=true` ever mean a partial gene-focused shard, or only full
  baseline plus contiguous updates?
- Should PubMed source rows enter the runtime data-source registry in the
  first implementation, or after the importer proves exact source-version
  fields?

## Decision

Proceed with a backend-owned PubMed local lane using SQLite FTS5, explicit
materialization, sanitized preflight, local-first lookup, and live E-utilities
fallback. Keep EP-VLEx as the publication reasoning layer, preserve the public
publication contract for the first slice, avoid startup downloads, and keep the
Patient Report Pipeline out of scope.
