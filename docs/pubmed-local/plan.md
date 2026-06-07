# PubMed Local Adapter And Materialization Plan

Source brief: build a backend-owned, local-first PubMed literature adapter and
materialization lane for the Variant Evidence Report. Preserve provenance,
avoid startup downloads, keep live PubMed E-utilities as fallback or refresh,
use de-identified/cache-safe storage, expose explicit CLI/preflight, and keep
the Patient Report Pipeline out of scope.

## Source Context

- Existing live path: `app/backend/app/tools/pubmed.py` queries PubMed through
  NCBI E-utilities (`esearch`, `esummary`, `efetch`) and falls back to
  `app/backend/app/fixtures/tools/pubmed_fixtures.json`.
- Existing publication aggregation:
  `app/backend/app/services/publication_literature.py` builds EP-VLEx
  `PublicationLiterature` rows from PubMed, LitVar2, and ClinVar PMIDs.
- Existing Variant Evidence Report wiring:
  `app/backend/app/services/lookup_service.py` calls PubMed during lookup,
  writes PubMed and EP-VLEx data into the resolved-variant cache, and exposes
  `POST /api/v1/lookup/publications`.
- Existing materialization pattern:
  `app/backend/app/services/compact_coordinate_index_materialization.py`,
  `app/backend/app/cli/eamos_compact_index_materialize.py`,
  `app/backend/app/services/coordinate_asset_materialization.py`, and
  `app/backend/app/cli/eamos_source_asset_preflight.py` show the expected
  explicit CLI, checksum/schema validation, sanitized output, and
  no-startup-download guardrails.
- Official source references:
  NCBI documents E-utilities as the public API for Entrez databases including
  PubMed (`https://www.ncbi.nlm.nih.gov/home/develop/api/`), PubMed data as
  available through FTP baseline/update files and E-utilities
  (`https://pubmed.ncbi.nlm.nih.gov/download/`), E-utilities rate guidance at
  3 requests/second without an API key and 10 requests/second with one
  (`https://eutilities.github.io/site/API_Key/usageandkey/`), NLM data
  copyright cautions including publisher-supplied abstracts
  (`https://www.nlm.nih.gov/databases/download.html`), and PubMed XML element
  documentation (`https://www.nlm.nih.gov/bsd/licensee/data_elements_doc.html`).

## Shared Decisions

- Treat this as a source materialization lane, not a request cache. The local
  corpus should store public literature records and source provenance, not
  patient data, user identifiers, raw user queries, uploaded report content, or
  Patient Report Pipeline state.
- Default behavior stays safe: no startup downloads, no background production
  downloads, no publisher scraping, no Google Scholar scraping, no frontend raw
  source access, and no Supabase/Render mutation unless a later operator task
  explicitly requests it.
- Local PubMed materialization starts with PubMed metadata and only stores
  abstract text when the source-policy gate says it is allowed. NLM warns that
  abstracts may be protected by copyright, so unknown or non-permissive
  abstract rights must be represented as metadata-only rows.
- Live E-utilities remains the fallback and refresh path. Local no-hit must not
  silently turn into fixture evidence for unrelated variants.
- Keep the public response contract additive or unchanged. The Variant Evidence
  Report should continue using `PublicationLiterature`, `PubMedArticle`, and
  `/api/v1/lookup/publications`.

## Task PML-001 - Source Policy And Corpus Contract

### Goal

Define the source-policy gate and local PubMed record contract so later tasks
can materialize metadata and permitted abstracts without storing non-permissive
or patient-derived data.

### Context

The brief asks for local materialized PubMed metadata/abstract search and also
requires permissive/open-source-only handling. NLM makes PubMed data available
through official channels, but its copyright page explicitly warns that
abstracts can originate from publishers and may be protected. This task owns
the policy boundary before storage or adapter wiring.

### Relevant Files Or References

- `app/backend/app/tools/pubmed.py`
- `app/backend/app/services/publication_literature.py`
- `app/backend/app/schemas/run.py`
- `app/backend/app/data_sources/registry.py`
- `app/backend/app/services/build_ledger.py`
- NCBI E-utilities API docs: `https://www.ncbi.nlm.nih.gov/home/develop/api/`
- PubMed data download docs: `https://pubmed.ncbi.nlm.nih.gov/download/`
- NLM copyright/data terms: `https://www.nlm.nih.gov/databases/download.html`
- PubMed XML elements: `https://www.nlm.nih.gov/bsd/licensee/data_elements_doc.html`

### Proposed Approach

Add a small backend policy module, for example
`app/backend/app/services/pubmed_local_policy.py`, with dataclasses or Pydantic
models for `PubmedLocalRecord`, `PubmedLocalProvenance`, and
`PubmedAbstractPolicy`. The policy should classify fields as always allowed
public metadata, conditionally allowed abstract text, or blocked text. It
should preserve PMID, title, journal, authors, publication date, DOI, PMCID,
MeSH/chemical terms if parsed, source XML provenance, source release/update
identity, and abstract policy status. It should explicitly reject local
storage of publisher full text and PMC full text unless a later source policy
task parses and approves a permissive open license.

### Acceptance Criteria

- Local PubMed record objects can represent metadata-only rows and permitted
  abstract rows without ambiguity.
- Abstract text with unknown or non-permissive rights is not stored locally;
  the row still carries `abstract_policy_status` and can be searched by
  metadata.
- Provenance captures source channel (`eutilities`, `pubmed_xml_baseline`,
  `pubmed_xml_update`), source version/update identity, fetched/imported time,
  and policy decision.
- No model includes patient identifiers, uploaded report IDs, raw user query
  strings, signed URLs, local filesystem paths for public responses, or
  service-role secrets.
- Build ledger source metadata can describe the PubMed local corpus as
  permissive-gated and materialization-required without unlocking unrelated
  sources.

### Source Reference

User brief plus NLM copyright/data terms and PubMed XML element documentation.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_pubmed_local_policy.py -q
python -m ruff check app/services/pubmed_local_policy.py tests/test_pubmed_local_policy.py
python -m black --check --target-version py310 app/services/pubmed_local_policy.py tests/test_pubmed_local_policy.py
```

### Out Of Scope

Database tables, materialization CLI, lookup wiring, full-text PMC ingestion,
Google Scholar, LitVar2 bulk ingestion, and Patient Report Pipeline work.

## Task PML-002 - Local Store And Search Index

### Goal

Add a de-identified local PubMed metadata store with enough search support for
gene and variant literature lookups.

### Context

`VariantCacheRepo` and `SourceCacheRepo` are request caches. They are useful
fallbacks, but they are not a materialized PubMed corpus. This lane needs
source records keyed by PMID plus searchable public terms, independent of any
user request.

### Relevant Files Or References

- `app/backend/app/core/db.py`
- `app/backend/app/repos/source_cache_repo.py`
- `app/backend/app/repos/variant_cache_repo.py`
- `app/backend/app/services/source_cache.py`
- `app/backend/tests/test_source_cache.py`
- `app/backend/tests/test_variant_cache.py`
- Task PML-001 policy models

### Proposed Approach

Add SQLAlchemy records for a local PubMed corpus, for example
`PubmedLocalArticleRecord`, `PubmedLocalTermRecord`, and
`PubmedLocalMaterializationRunRecord`. Keep the first implementation portable
across SQLite and Postgres. Index exact identifiers and normalized terms used
by `VariantLiteratureTerms`: gene, cDNA, transcript HGVS, protein aliases,
rsID, genomic alias, PMID, title words, and permitted abstract terms. Add a
repo such as `PubmedLocalRepo` with upsert, PMID lookup, variant-term search,
gene-scope count, materialization status, and health-summary methods.

### Acceptance Criteria

- Records are keyed by public source identity, not by user query.
- Search can return recent-first PMIDs for a term bundle equivalent to
  `VariantLiteratureTerms.build(...)`.
- Gene-scope count is computed from local records when materialized enough to
  be honest; otherwise it returns unavailable with a warning instead of a fake
  count.
- Re-importing the same PMID updates source metadata idempotently and does not
  duplicate terms.
- Deleted or withdrawn PubMed citations can be marked unavailable/tombstoned
  when present in update XML or refresh responses.
- Health summaries expose counts, latest materialization time, and policy
  counts, but do not expose local paths, source object URIs, secrets, or user
  input.

### Source Reference

Existing `core/db.py` SQLAlchemy models and cache repos, plus Task PML-001
corpus contract.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_pubmed_local_repo.py -q
python -m ruff check app/repos app/core/db.py tests/test_pubmed_local_repo.py
python -m black --check --target-version py310 app/repos app/core/db.py tests/test_pubmed_local_repo.py
```

### Out Of Scope

Network fetching, XML parsing beyond fixture rows, lookup-service wiring,
Supabase migrations, pgvector embeddings, and frontend contract changes.

## Task PML-003 - Explicit PubMed Materialization CLI

### Goal

Create an operator-run CLI that materializes PubMed rows into the local store
without any app-startup download path.

### Context

The source-asset materialization lane already uses explicit CLIs with
sanitized JSON, checksum/schema validation, and `--require-ready` exits. PubMed
needs the same operational shape. PubMed data can come from operator-supplied
baseline/update XML files or from bounded E-utilities refreshes.

### Relevant Files Or References

- `app/backend/app/cli/eamos_compact_index_materialize.py`
- `app/backend/app/services/compact_coordinate_index_materialization.py`
- `app/backend/app/services/coordinate_asset_materialization.py`
- `app/backend/app/tools/pubmed.py`
- `app/backend/app/core/config.py`
- `app/backend/.env.example`
- `app/backend/tests/test_compact_coordinate_index_materialization.py`
- NCBI E-utilities usage guidelines:
  `https://eutilities.github.io/site/API_Key/usageandkey/`
- PubMed baseline/update docs: `https://pubmed.ncbi.nlm.nih.gov/download/`

### Proposed Approach

Add `python -m app.cli.eamos_pubmed_materialize` with explicit modes:
`--from-xml-dir`, `--from-xml-file`, `--pmid-file`, and bounded
`--query gene:variant` or `--gene` refresh. XML modes read files already
provided by an operator and never download them. E-utilities mode honors NCBI
rate guidance, supports `tool`, `email`, and optional `api_key`, uses batched
history/fetch where appropriate, and records source request identity without
storing user-origin raw query text. Output should be sanitized JSON with mode,
record counts, policy counts, deleted/tombstoned counts, source identity,
warnings, and `ready`.

### Acceptance Criteria

- The CLI is the only materialization entry point; no startup, import-time, or
  request-time bulk download is introduced.
- XML fixture import can create/update local PubMed rows with provenance and
  abstract policy decisions.
- Bounded E-utilities refresh can fetch by PMIDs or curated gene/variant seed
  terms and upsert rows.
- CLI output omits secrets, API keys, local paths, raw object URIs, and signed
  URLs.
- `--require-ready` exits non-zero when no usable rows were materialized or
  policy blocks every requested abstract.
- Re-running the CLI is idempotent and safe against partial failures.

### Source Reference

Existing compact coordinate materialization CLI/service and official PubMed
FTP/E-utilities docs.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_pubmed_materialization_cli.py tests/test_pubmed_local_repo.py -q
python -m app.cli.eamos_pubmed_materialize --from-xml-file app/fixtures/tools/pubmed_sample.xml --compact --require-ready
python -m ruff check app/cli/eamos_pubmed_materialize.py app/services app/repos tests/test_pubmed_materialization_cli.py
python -m black --check --target-version py310 app/cli/eamos_pubmed_materialize.py app/services app/repos tests/test_pubmed_materialization_cli.py
```

### Out Of Scope

Automatic FTP baseline downloads, production Render disk seeding, Supabase
Storage mutation, background schedulers, and Patient Report Pipeline work.

## Task PML-004 - Local-First PubMed Adapter With Live Fallback

### Goal

Introduce a PubMed adapter that searches the local materialized corpus first
and uses live E-utilities only as a fallback or explicit refresh path.

### Context

`PubmedTool` currently owns live E-utilities plus fixture fallback. The local
lane should preserve existing output shape (`ToolResult.summary.articles`,
`gene_scope`, `request_identity`, `source_url`) so EP-VLEx and existing tests
continue to work.

### Relevant Files Or References

- `app/backend/app/tools/pubmed.py`
- `app/backend/app/tools/base.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/search_input_resolver.py`
- `app/backend/app/services/publication_literature.py`
- `app/backend/app/core/config.py`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_publication_literature.py`

### Proposed Approach

Either extend `PubmedTool` with an injected `PubmedLocalRepo` or add a
`PubmedLocalFirstTool` wrapper registered under source `pubmed`. Add disabled
by default settings such as `pubmed_local_enabled`,
`pubmed_local_refresh_on_miss`, `pubmed_local_require_real_apis`, and a
materialization status requirement. When local records satisfy the term bundle,
return status `local` with local provenance and PubMed URLs. On local no-hit,
return local no-hit plus live fallback only when `USE_REAL_APIS=true` and the
refresh/fallback setting allows it. `refresh=true` should bypass local fresh
results only for a bounded E-utilities refresh, then update the local store if
policy permits.

### Acceptance Criteria

- Fixture mode remains deterministic and does not require a local PubMed DB.
- In real mode with local enabled and ready, PubMed lookup can return local
  articles without calling E-utilities.
- Local no-hit does not fall back to unrelated fixture rows.
- Live fallback preserves existing PubMed behavior and writes refresh results
  through the policy gate before local storage.
- Source statuses make provenance clear: local, local_no_hit, live,
  fallback, cache, or unavailable.
- Request identities and warnings are cache-safe and do not contain patient
  data or raw long-form user prompts.

### Source Reference

Existing `PubmedTool` behavior, `LookupService` source-cached result wrapper,
and Task PML-002 repo API.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_pubmed_local_adapter.py tests/test_tool_invariants.py tests/test_publication_literature.py -q
python -m ruff check app/tools/pubmed.py app/services tests/test_pubmed_local_adapter.py
python -m black --check --target-version py310 app/tools/pubmed.py app/services tests/test_pubmed_local_adapter.py
```

### Out Of Scope

Changing `PublicationLiterature` schema, frontend rendering, PubTator/PMC full
text, and Patient Report Pipeline work.

## Task PML-005 - Variant Evidence Report And Publication Pagination Wiring

### Goal

Wire local-first PubMed results into the existing Variant Evidence Report
literature path without changing frontend ownership or adding Patient Report
Pipeline behavior.

### Context

`LookupService.lookup()` already calls PubMed, ClinVar, and LitVar2, then
builds `PublicationLiterature`. `LookupService.page_publications()` already
returns bounded pages. This task makes those paths prefer local PubMed when
configured and keeps live E-utilities available for refresh.

### Relevant Files Or References

- `app/backend/app/services/lookup_service.py`
- `app/backend/app/services/publication_literature.py`
- `app/backend/app/api/routes/lookup.py`
- `app/backend/app/schemas/run.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_variant_cache.py`
- `app/backend/tests/test_lookup_section_fetch_contract.py`
- `plans/variant-literature-extraction/plan.md`

### Proposed Approach

Inject the PubMed local repo/tool through the app setup and lookup service.
Keep `PublicationLiterature` as the public shape. Ensure local PubMed rows
participate in EP-VLEx deduping with LitVar2 and ClinVar PMIDs, snippets are
created only from permitted title/abstract text, and gene-scope counts come
from local materialization only when the corpus status supports them. Keep the
existing variant-cache replay path, but do not use variant cache as the source
of truth for local corpus readiness.

### Acceptance Criteria

- `/api/v1/lookup` returns the same `publications_literature` shape with local
  PubMed articles when local materialization is enabled and ready.
- `/api/v1/lookup/publications` returns deterministic local-backed pages with
  `limit <= 50` and recent-first sorting.
- Local PubMed rows dedupe correctly with LitVar2 and ClinVar citation PMIDs.
- Snippet statuses honestly distinguish exact variant snippets, gene-only
  rows, metadata-only rows, abstract-policy-blocked rows, and no-text rows.
- `publications_callout.total_count` and `scope_counts` remain consistent with
  `PublicationLiterature`.
- Cache hits do not mask stale or missing local materialization status.

### Source Reference

Existing EP-VLEx implementation and lookup publication pagination route.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_variant_search_integration.py tests/test_variant_cache.py tests/test_publication_literature.py tests/test_lookup_section_fetch_contract.py -q
python -m ruff check app/services/lookup_service.py app/services/publication_literature.py tests
python -m black --check --target-version py310 app/services/lookup_service.py app/services/publication_literature.py tests
```

### Out Of Scope

Frontend components, TypeScript mirrors unless a backend schema change is
explicitly approved, Patient Report Pipeline `/runs`, and functional-evidence
classification changes.

## Task PML-006 - Preflight, Health, And Build Ledger

### Goal

Expose PubMed local materialization readiness through backend preflight and
health surfaces without leaking sensitive configuration.

### Context

`/api/v1/health/provider-cache` already reports source cache and source asset
readiness. `eamos_source_asset_preflight` reports local-first asset guardrails.
The PubMed local lane needs equivalent readiness output so operators can verify
materialization before enabling local-first lookup.

### Relevant Files Or References

- `app/backend/app/api/routes/health.py`
- `app/backend/app/cli/eamos_source_asset_preflight.py`
- `app/backend/app/services/build_ledger.py`
- `app/backend/app/core/config.py`
- `app/backend/tests/test_health_api.py`
- `app/backend/tests/test_source_asset_preflight_cli.py`
- Task PML-002 repo health summary

### Proposed Approach

Add a PubMed local readiness summary to provider-cache health and source asset
preflight, or add a focused `python -m app.cli.eamos_pubmed_preflight` if the
existing preflight would become noisy. Report enabled/configured state,
materialized row count, permitted abstract count, metadata-only count, latest
baseline/update identity, latest refresh time, deleted/tombstoned count, and
whether local-first lookup can use the corpus. Update the build ledger item for
the literature engine from "bulk edges pending" toward this materialized
PubMed metadata lane while preserving launch/provenance metadata.

### Acceptance Criteria

- Health/preflight output is sanitized: no local paths, DB URLs, API keys,
  service-role keys, source object URIs, signed URLs, or raw user inputs.
- Preflight distinguishes not configured, configured but empty,
  materialized metadata-only, materialized with permitted abstracts, stale, and
  ready.
- Output states that startup downloads are not used.
- Build ledger identifies PubMed local metadata as backend-owned,
  materialization-required, and public-serialization-safe only for approved
  fields.
- Failing PubMed local inspection does not crash `/health/provider-cache`.

### Source Reference

Existing source asset preflight and provider-cache health implementations.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_health_api.py tests/test_source_asset_preflight_cli.py tests/test_pubmed_preflight_cli.py -q
python -m app.cli.eamos_pubmed_preflight --compact
python -m ruff check app/api/routes/health.py app/cli app/services/build_ledger.py tests
python -m black --check --target-version py310 app/api/routes/health.py app/cli app/services/build_ledger.py tests
```

### Out Of Scope

Render env changes, Supabase mutations, public dashboard UI, and automatic
schedulers.

## Task PML-007 - Verification, Fixtures, And Optional Live Smoke

### Goal

Lock the local-first PubMed lane with focused fixtures, regression tests, and
an optional bounded live smoke.

### Context

The current publication stack has strong tests for EP-VLEx, variant cache
replay, and source-cache behavior. The new lane adds policy decisions,
materialized corpus storage, and fallback ordering, so tests need to cover both
happy paths and failure paths before any live enablement.

### Relevant Files Or References

- `app/backend/tests/test_publication_literature.py`
- `app/backend/tests/test_variant_cache.py`
- `app/backend/tests/test_source_cache.py`
- `app/backend/tests/test_variant_search_integration.py`
- `app/backend/tests/test_health_api.py`
- `app/backend/app/fixtures/tools/pubmed_fixtures.json`
- New tiny PubMed XML fixtures under `app/backend/app/fixtures/tools/` or
  `app/backend/app/fixtures/data_sources/`

### Proposed Approach

Add tiny PubMed XML fixtures covering RPE65 and USH2A rows, one deleted
citation, one metadata-only row, one permitted-abstract row, one unknown-rights
abstract row, and duplicate PMID imports. Add tests for local-first lookup,
live fallback with mocked E-utilities, refresh bypass, stale readiness, health
sanitization, and pagination. Provide an optional live smoke command that uses
`--skip-if-unconfigured` semantics and NCBI rate limits so CI and local
Windows runs do not require network.

### Acceptance Criteria

- Focused tests pass without network and without production PubMed data.
- Mocked E-utilities fallback proves that local no-hit can refresh without
  using fixtures for unrelated variants.
- Local materialization tests prove no startup download path exists.
- Health/preflight tests prove no secrets, local paths, patient identifiers,
  or raw user prompts are serialized.
- Existing tests for `PublicationLiterature`, variant cache replay,
  source-cache stale fallback, and frontend contract still pass.
- Optional live smoke is bounded, rate-limited, skip-safe when unconfigured,
  and records current PubMed counts only as smoke observations, not fixtures.

### Source Reference

Existing backend verification expectations in `agent_handoff/RISKS.md` and
the BE-11/RP-003 publication verification history in `plans/v2-backend.md`.

### Verify

```powershell
cd app/backend
python -m pytest tests/test_pubmed_local_policy.py tests/test_pubmed_local_repo.py tests/test_pubmed_materialization_cli.py tests/test_pubmed_local_adapter.py tests/test_pubmed_preflight_cli.py -q
python -m pytest tests/test_publication_literature.py tests/test_variant_search_integration.py tests/test_variant_cache.py tests/test_source_cache.py tests/test_health_api.py tests/test_frontend_contract.py -q
python -m ruff check app tests
python -m black --check --target-version py310 app tests
```

Optional live smoke after operator approval/configuration:

```powershell
cd app/backend
python -m app.cli.eamos_pubmed_materialize --pmid-file .tmp/pubmed-smoke-pmids.txt --compact --require-ready
```

### Out Of Scope

Full backend test-suite runtime guarantees for every downstream source,
production FTP baseline download, deploy, commit, push, Render/Vercel/Supabase
mutation, frontend UI, and Patient Report Pipeline work.
