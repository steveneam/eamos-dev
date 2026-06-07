# PubMed Local Adapter And Materialization Spec

**What**

Build a backend-owned, local-first PubMed literature adapter for the Variant
Evidence Report. The adapter should serve PubMed article metadata and
license-gated abstract search from an explicitly materialized local store when
available, then fall back to the existing live NCBI E-utilities path for refresh
or incomplete local coverage. It must preserve existing `PublicationLiterature`
and `PubMedArticle` response contracts, record source provenance, avoid startup
downloads, and keep all materialized storage de-identified and cache-safe.

**Context**

Eamos already has a source-backed publication lane:

- `app/backend/app/tools/pubmed.py` performs live PubMed ESearch, ESummary, and
  EFetch calls through `settings.clinvar_base_url`, currently the NCBI
  E-utilities base URL.
- `app/backend/app/services/publication_literature.py` implements EP-VLEx,
  which deduplicates PubMed, LitVar2, and ClinVar PMIDs, derives snippets, sorts
  articles by date, builds per-source counts, and returns
  `PublicationLiterature`.
- `app/backend/app/services/lookup_service.py` wires PubMed into the Variant
  Evidence Report, caches publication replay data in `variant_cache`, and
  exposes `/api/v1/lookup/publications`.
- `app/backend/app/services/lookup_sections.py` treats `publications` as a lazy
  section backed by `pubmed`, `litvar2`, and `clinvar`.
- `app/backend/app/repos/source_cache_repo.py` already supports source cache
  rows, freshness, stale-on-failure behavior, and sanitized provider-cache
  health summaries.
- Existing explicit materialization patterns live in
  `app/backend/app/services/coordinate_asset_materialization.py`,
  `app/backend/app/services/pfam_materialization.py`,
  `app/backend/app/cli/eamos_source_asset_preflight.py`, and
  `app/backend/app/cli/eamos_pfam_runtime_materialize.py`.

The new PubMed local lane should be analogous to those source-asset lanes:
manual CLI materialization, preflight reporting, fail-safe runtime behavior, and
no production/startup downloads. It is not Patient Report Pipeline (`/runs`)
work.

Important source/legal context:

- NCBI E-utilities are the official PubMed search/retrieval interface:
  https://www.ncbi.nlm.nih.gov/books/NBK25501/
- NCBI documents E-utilities rate limits and recommends batching large work:
  https://www.ncbi.nlm.nih.gov/books/NBK25497/
- NLM states PubMed abstracts may be protected by copyright and NLM does not
  grant reuse rights: https://www.nlm.nih.gov/databases/download.html
- PMC Open Access provides machine-readable license information and separates
  commercial-use, non-commercial-use, and other/no-machine-readable-license
  groups: https://pmc.ncbi.nlm.nih.gov/tools/ftp/
- PMC developer APIs expose OA metadata, BioC full text, and ID conversion:
  https://pmc.ncbi.nlm.nih.gov/tools/developers/

**Requirements**

1. The local PubMed adapter must preserve the existing `ToolResult` summary
   shape from `PubmedTool`: `articles`, `total`, optional `gene_scope`, PubMed
   URLs, `request_identity`, warnings, source URL, fetched timestamp, and source
   version.
2. The public API response shape must stay `PublicationLiterature` for
   `/api/v1/lookup`, `/api/v1/lookup/sections`, and
   `/api/v1/lookup/publications`.
3. Local runtime status must use `status="local"` for materialized PubMed hits,
   not `cache`, `fixture`, or `live`.
4. The adapter must search local materialized metadata first when
   `PUBMED_LOCAL_ENABLED=true` and the local preflight is ready.
5. Live E-utilities must remain the fallback for missing, stale, incomplete, or
   explicitly refreshed local coverage.
6. `refresh=true` on lookup/publication paths must bypass local materialized
   results for that request and use live E-utilities, while still avoiding
   request-time writes to the materialized PubMed store.
7. Request-time lookup must never download, build, rebuild, vacuum, or mutate
   the PubMed materialization database. Only the explicit CLI may mutate it.
8. Application startup must fail closed if any startup materialization flag is
   enabled, matching the coordinate-resolver startup-download policy.
9. The materialized store must be de-identified: no patient identifiers, user
   IDs, IP addresses, sessions, free-text clinical notes, request headers, or
   prompt/input text beyond normalized gene and variant terms.
10. The materialized store must preserve provenance: source query, PMID, PubMed
    URL, NCBI/PubMed source version or fetch date, E-utilities endpoint family,
    source release label, materialization CLI version, materialized-at time,
    checksum, and license/text policy for every stored text field.
11. Persisted raw abstract text must be license-gated. Store and index abstract
    text only when the record is proven permissive for Eamos use, such as
    `CC0`, `CC BY`, `CC BY-SA`, or U.S. Government/public-domain source.
12. Do not persist or index raw abstract text for unknown, publisher-copyright,
    `NO-CC CODE`, custom, non-commercial-only, or no-derivatives records. Those
    records may keep metadata and PMID links only.
13. The adapter must expose coverage status so a local no-hit is not mistaken
    for source truth when the local materialization only covers a subset of a
    gene or variant term bundle.
14. Existing EP-VLEx invariants must hold: dedupe by PMID, PubMed URL per
    article, recent-first sorting, `publications_callout.total_count ==
    publications_literature.total_count`, and at most five initial rows.
15. Materialization and preflight commands must emit sanitized JSON only: no
    secrets, API keys, raw local paths in public health output, signed URLs,
    private object paths, or raw abstract text.
16. The first implementation must use only permissive/open-source dependencies.
    Prefer Python standard library `sqlite3`, SQLite FTS5 when available, and
    existing `httpx`. Do not add GPL, AGPL, non-commercial, publisher-scraper,
    or reverse-engineered dependencies.
17. The implementation must not touch the Patient Report Pipeline, `/runs`,
    PDF generation, patient upload/intake tables, or frontend UI.

**Design**

Add a local materialized PubMed store and a runtime adapter around the existing
`PubmedTool` behavior.

**Components**

- `app/backend/app/services/pubmed_local.py`
  - `PubMedLocalStore`: read-only SQLite access, preflight inspection, metadata
    search, FTS search, and sanitized health summaries.
  - `PubMedLocalAdapter`: local-first orchestration that returns `ToolResult`.
    It delegates to the existing live `PubmedTool` for fallback and refresh.
  - `PubMedLocalCoverage`: describes whether the materialized store is complete
    enough for a gene, variant term bundle, or PMID set.
- `app/backend/app/cli/eamos_pubmed_local_materialize.py`
  - Explicit CLI that builds or updates the materialized SQLite store.
- `app/backend/app/cli/eamos_pubmed_local_preflight.py`
  - Read-only CLI that inspects the local store and emits sanitized readiness
    JSON. This can also be folded into `eamos_source_asset_preflight`, but a
    dedicated CLI is clearer for today.
- `app/backend/app/tools/pubmed.py`
  - Keep the existing live E-utilities implementation. Add a thin wrapper or
    factory so the tool registry can use `PubMedLocalAdapter` when enabled.
- `app/backend/app/services/lookup_sections.py`
  - Extend `STATUS_PRIORITY` to include `"local"` immediately after `"live"` so
    section freshness does not degrade local materialized results to fallback.
- `app/backend/app/api/routes/health.py`
  - Add sanitized `source_assets.pubmed_local` or `providers.pubmed_local`
    readiness data to provider-cache health.
- `app/backend/app/services/build_ledger.py`
  - Update `literature_engine` status from "live fetch plus bulk pending" to
    include `pubmed_local_adapter` and materialization status.
- `app/backend/app/core/config.py` and `.env.example`
  - Add disabled-by-default settings listed below.

**Configuration**

Add disabled-by-default settings:

```text
PUBMED_LOCAL_ENABLED=false
PUBMED_LOCAL_SQLITE_PATH=./data/bio_assets/pubmed/pubmed-local.sqlite
PUBMED_LOCAL_MANIFEST_PATH=./data/bio_assets/pubmed/pubmed-local.manifest.json
PUBMED_LOCAL_STARTUP_MATERIALIZATION_ENABLED=false
PUBMED_LOCAL_FALLBACK_ON_NO_HIT=true
PUBMED_LOCAL_MAX_RESULTS=50
PUBMED_LOCAL_REQUIRE_LICENSED_ABSTRACTS=true
PUBMED_LOCAL_MATERIALIZE_TIMEOUT_SECONDS=1200
NCBI_EUTILS_API_KEY=
NCBI_EUTILS_TOOL=eamos
NCBI_EUTILS_EMAIL=
```

`PUBMED_LOCAL_STARTUP_MATERIALIZATION_ENABLED=true` must raise at startup with a
message equivalent to "PubMed local startup materialization is disabled; seed
and verify with explicit CLI".

**Runtime Data Flow**

1. Lookup resolves gene, cDNA, transcript, protein, rsID, genomic HGVS, and
   `genomic_hg38` through the existing resolver.
2. `LookupService` calls `tool_registry["pubmed"].get_evidence(variant=variant)`
   as it already does.
3. If local PubMed is disabled or preflight is not ready, the adapter returns
   the existing live/fixture behavior.
4. If local PubMed is enabled and ready, the adapter builds the same PubMed term
   bundle used today:
   - gene scope: `{gene}[Gene Name]`
   - variant scope: gene plus OR over cDNA, protein aliases, rsID, and genomic
     terms
5. The adapter queries local tables first. It searches metadata for all records
   and abstract FTS only for records whose abstract text is licensed for local
   reuse.
6. If local results are found, return `ToolResult(source="pubmed",
   status="local", summary={...})`.
7. If local results are not found and coverage is incomplete, call live
   E-utilities and add warning `pubmed_local_no_hit_live_fallback`.
8. If local results are not found and coverage is complete, return a local
   no-hit with `summary={"articles": [], "total": 0, "gene_scope": ...}`.
9. EP-VLEx consumes the result exactly as it consumes today's PubMed result.

**CLI Contracts**

Materialize command:

```bash
cd app/backend
python -m app.cli.eamos_pubmed_local_materialize `
  --query-file data/pubmed/pubmed-seed.tsv `
  --output data/bio_assets/pubmed/pubmed-local.sqlite `
  --manifest data/bio_assets/pubmed/pubmed-local.manifest.json `
  --mode targeted-eutils `
  --max-records-per-query 200 `
  --compact
```

Supported materialization modes:

- `targeted-eutils`: controlled E-utilities fetch for an explicit gene/variant
  seed list. This is the first build-today path.
- `import-jsonl`: import a previously fetched, reviewed JSONL file with PubMed
  metadata rows.
- `verify-only`: open the existing SQLite store, verify schema/checksum, and
  write no data.

Seed file TSV columns:

```text
gene    cdna    transcript    protein_change    rsid    genomic_hg38    scope
```

`scope` is `variant` or `gene`. Empty optional columns are allowed. The CLI must
reject rows with non-gene/variant free text.

Materialize output JSON:

```json
{
  "mode": "pubmed_local_materialize",
  "generated_at": "2026-06-07T00:00:00+00:00",
  "guardrails": {
    "startup_download": "not_used",
    "patient_data": "not_used",
    "abstract_license_gate": "enforced",
    "secrets_in_output": "blocked"
  },
  "network": {
    "used": true,
    "provider": "ncbi_eutilities",
    "rate_limit_profile": "3_per_second_without_api_key_or_10_with_key"
  },
  "materialization": {
    "ready": true,
    "status": "ready",
    "schema_version": 1,
    "article_count": 123,
    "licensed_abstract_count": 17,
    "metadata_only_count": 106,
    "coverage_count": 12,
    "source_version": "pubmed-targeted-eutils-2026-06-07",
    "checksum_algorithm": "sha256",
    "checksum_value": "<sha256>",
    "warnings": []
  }
}
```

Preflight command:

```bash
cd app/backend
python -m app.cli.eamos_pubmed_local_preflight --compact
```

Preflight output JSON:

```json
{
  "mode": "pubmed_local_preflight",
  "generated_at": "2026-06-07T00:00:00+00:00",
  "ready": true,
  "status": "ready",
  "enabled": true,
  "startup_download_allowed": false,
  "network_used": false,
  "schema_version": 1,
  "article_count": 123,
  "licensed_abstract_count": 17,
  "metadata_only_count": 106,
  "coverage": {
    "genes": 10,
    "variant_queries": 40,
    "complete_gene_scopes": 2,
    "partial_gene_scopes": 8
  },
  "license_profile_counts": {
    "metadata_only": 106,
    "cc_by": 12,
    "cc_by_sa": 3,
    "public_domain": 2
  },
  "source_version": "pubmed-targeted-eutils-2026-06-07",
  "secret_values_emitted": false,
  "local_path_values_emitted": false,
  "raw_abstract_values_emitted": false,
  "warnings": []
}
```

**API Contracts**

No new frontend-facing publication payload is required for the first slice.
Keep these existing response contracts:

- `POST /api/v1/lookup`
- `POST /api/v1/lookup/sections`
- `POST /api/v1/lookup/publications`

Additive route behavior:

- `POST /api/v1/lookup?refresh=true` bypasses local materialized PubMed for
  that request and uses live E-utilities when `USE_REAL_APIS=true`.
- Add `refresh: bool = false` to `PublicationPageRequest` or support
  `/api/v1/lookup/publications?refresh=true`. The response remains
  `PublicationLiterature`.
- Provider health includes sanitized PubMed-local readiness, but never local
  paths, object paths, raw abstract text, seed queries, or secrets.

`EvidenceSourceSummary` for local PubMed should include:

```json
{
  "source": "pubmed",
  "status": "local",
  "cache_status": "pubmed_local_materialized",
  "source_version": "pubmed-targeted-eutils-2026-06-07",
  "source_url": "https://pubmed.ncbi.nlm.nih.gov/?term=RPE65%5Bgene%5D",
  "warnings": []
}
```

**Materialized Data Shape**

Use a standalone SQLite database under `data/bio_assets/pubmed/`, not the app
transactional database. This makes it an explicit source asset that can be
seeded, checksummed, moved to Render disk, and opened read-only at runtime.

Schema version 1:

```sql
create table pubmed_article (
  pmid text primary key,
  title text not null,
  authors_display text not null default '',
  journal text not null default '',
  year text not null default '',
  publication_date text,
  doi text,
  pmcid text,
  pubmed_url text not null,
  source_status text not null,
  source_version text not null,
  fetched_at text not null,
  license_profile text not null,
  license_source text,
  abstract_policy text not null,
  abstract_text text,
  abstract_sha256 text,
  is_retracted integer not null default 0,
  provenance_json text not null default '{}'
);

create table pubmed_article_term (
  pmid text not null references pubmed_article(pmid) on delete cascade,
  term_type text not null,
  term_norm text not null,
  matched_field text not null,
  primary key (pmid, term_type, term_norm, matched_field)
);

create table pubmed_coverage (
  coverage_key text primary key,
  scope text not null,
  gene_norm text not null,
  query_terms_json text not null,
  completeness text not null,
  materialized_at text not null,
  source_query text not null,
  result_count integer not null,
  warning_json text not null default '[]'
);

create table pubmed_materialization_manifest (
  id integer primary key check (id = 1),
  schema_version integer not null,
  source_version text not null,
  materialized_at text not null,
  cli_version text not null,
  article_count integer not null,
  licensed_abstract_count integer not null,
  metadata_only_count integer not null,
  checksum_algorithm text not null,
  checksum_value text not null,
  warnings_json text not null default '[]'
);
```

If SQLite FTS5 is available, create:

```sql
create virtual table pubmed_article_fts using fts5(
  pmid unindexed,
  title,
  abstract_text,
  content=''
);
```

Only insert `abstract_text` into FTS rows when `abstract_policy =
'licensed_text_persisted'`. Metadata-only rows may still insert title text.
Preflight must report `fts_status="available"` or `fts_status="unavailable"`.
If FTS5 is unavailable, local search may fall back to bounded `LIKE` over title
and terms but must report `pubmed_local_fts_unavailable`.

**Decisions**

- Decision: Use a standalone materialized SQLite asset rather than the app
  transactional database.
  - Alternatives: add app DB tables, use `source_cache`, or use Supabase
    Postgres/pgvector first.
  - Why: PubMed-local is a seeded source asset, not user data. A standalone
    asset can be checksummed, opened read-only, mounted on Render disk, and
    preflighted without changing patient/user storage. `source_cache` remains a
    request replay cache, not the materialized source.
  - Reversible: yes. Rows can later be imported into Supabase Postgres if the
    literature engine moves to pgvector.

- Decision: Store abstract text only for permissive/public-domain records.
  - Alternatives: persist all EFetch abstracts or store no abstracts.
  - Why: NLM explicitly warns that PubMed abstracts may be copyrighted. The user
    asked for permissive/open source only. This keeps local abstract search
    real where rights are clear while allowing metadata-only coverage elsewhere.
  - Reversible: partly. If legal approval expands allowed rights, the CLI can
    materialize more abstract text without changing runtime contracts.

- Decision: Local no-hit falls back to live unless local coverage is marked
  complete for the relevant query scope.
  - Alternatives: always trust local no-hit or always call live after local.
  - Why: targeted materialization will be partial at first. Falling back avoids
    false "no literature" claims while complete scopes can avoid unnecessary
    network calls.
  - Reversible: yes via `PUBMED_LOCAL_FALLBACK_ON_NO_HIT`.

- Decision: Keep existing `PubmedTool` live code as the fallback path.
  - Alternatives: rewrite the PubMed tool around the local store immediately.
  - Why: the live path is already tested and wired through EP-VLEx, variant
    cache, source cache, and lazy publication sections.
  - Reversible: yes after local coverage matures.

- Decision: Do not add a frontend contract for license/provenance details in
  the first slice.
  - Alternatives: add fields to `PubMedArticle` for local source mode.
  - Why: existing evidence summaries and health/preflight can carry source
    status. The frontend already renders `PublicationLiterature`.
  - Reversible: yes as an additive contract change later.

- Assumption: The first build-today materialization is targeted by Eamos seed
  gene/variant terms, not a full PubMed baseline mirror.

**Versions**

- Python runtime: use the repo's existing backend Python runtime and standard
  library `sqlite3`.
- SQLite: use standard `sqlite3`; require schema preflight and detect FTS5 at
  runtime. No new SQLite package is required.
- HTTP: use existing `httpx`.
- NCBI E-utilities: use official ESearch, ESummary, and EFetch endpoints under
  `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`. As of the NCBI Bookshelf
  page opened for this spec, the E-utilities in-depth docs were last updated
  March 4, 2026.
- Rate limits: default CLI pacing must respect NCBI's documented 3 requests per
  second without an API key and 10 requests per second with an API key.

**Invariants**

- No startup or request-time materialization.
- No Patient Report Pipeline changes.
- No frontend changes required by the first backend slice.
- No raw abstract text is persisted unless `abstract_policy` is licensed and
  `license_profile` is permissive/public-domain.
- All article URLs are `https://pubmed.ncbi.nlm.nih.gov/{pmid}/`.
- Local materialized results use `status="local"`.
- `PublicationLiterature.total_count` remains the deduplicated PMID count.
- `PublicationLiterature.articles` in initial lookup remains bounded to five.
- `PublicationLiterature.publication_timeline` is computed across the full
  deduplicated local result set before pagination.
- Local health/preflight output never emits raw local paths, object paths,
  signed URLs, API keys, seed file contents, or abstract text.
- Query materialization stores only normalized gene/variant identifiers, never
  patient or user context.
- Live fallback warnings are explicit and prefix-stable:
  `pubmed_local_unavailable:*`, `pubmed_local_no_hit_live_fallback`,
  `live_fetch_failed:<ExceptionName>`.

**Error Behavior**

- Local DB missing: return live/fixture path and warning
  `pubmed_local_unavailable:db_missing`.
- Local DB schema mismatch: return live/fixture path and warning
  `pubmed_local_unavailable:schema_mismatch`.
- Local DB checksum mismatch: return live/fixture path and warning
  `pubmed_local_unavailable:checksum_mismatch`; provider health reports not
  ready.
- FTS unavailable: use bounded metadata/title/term search and warn
  `pubmed_local_fts_unavailable`.
- Local no-hit with incomplete coverage: call live E-utilities and warn
  `pubmed_local_no_hit_live_fallback`.
- Local no-hit with complete coverage: return local zero-result without live
  call unless `refresh=true`.
- Live fallback failure after local failure: return fixture/fallback behavior
  exactly as current `PubmedTool` does, including `live_fetch_failed:<ExceptionName>`.
- E-utilities rate-limit response during CLI materialization: back off and
  retry within CLI timeout; if exhausted, exit non-zero with status
  `eutils_rate_limited` and leave the previous materialized DB untouched.
- CLI partial build: write to a temp path, verify, then atomically replace the
  destination. Never leave a half-built DB at the configured runtime path.
- License ambiguity: store metadata only, do not persist abstract text, and add
  materialization warning `abstract_text_not_persisted:license_unverified`.
- Corrupt row or invalid PMID: skip row, count it in CLI warnings, and fail the
  CLI only if all rows fail or `--strict` is passed.

**Testing Strategy**

- Unit: `PubMedLocalStore` preflight returns missing, schema mismatch, checksum
  mismatch, FTS unavailable, and ready states.
- Unit: local search finds title, PMID, DOI/PMCID, gene, cDNA, protein alias,
  rsID, and licensed abstract matches.
- Unit: metadata-only records never match on raw abstract text and never expose
  abstract bodies.
- Unit: license gating accepts `CC0`, `CC BY`, `CC BY-SA`, and
  public-domain/U.S. Government records; rejects unknown, no-machine-readable,
  non-commercial, and no-derivatives profiles.
- Unit: materialization writes to a temporary file and atomically replaces only
  after checksum/schema verification.
- Unit: CLI output is sanitized and does not contain API keys, local paths in
  public health mode, seed query rows, or abstract text.
- Integration: `LookupService.lookup()` with local ready PubMed returns
  `EvidenceSourceSummary.status == "local"` and EP-VLEx builds the same
  `PublicationLiterature` shape.
- Integration: local no-hit with incomplete coverage falls back to live and
  emits `pubmed_local_no_hit_live_fallback`.
- Integration: `refresh=true` bypasses local and calls live PubMed.
- Route: `/api/v1/lookup/publications` preserves pagination, limit bounds, gene
  scope counts, and existing mouse unsupported behavior.
- Route: `/api/v1/lookup/sections` freshness treats `"local"` as a first-class
  source status.
- Health/preflight: provider-cache and CLI summaries include counts/status but
  no paths, object paths, raw abstracts, or secrets.
- Regression: current publication tests continue to pass:
  `test_publication_literature.py`,
  `test_variant_report_publication_functional_integration.py`,
  `test_variant_cache.py`,
  `test_lookup_section_fetch_contract.py`,
  `test_source_cache.py`, and `test_frontend_contract.py`.
- Startup: enabling `PUBMED_LOCAL_STARTUP_MATERIALIZATION_ENABLED=true` raises
  before app startup completes.

**Out Of Scope**

- Patient Report Pipeline (`/runs`), PDF/report upload, clinician review, or
  auth-gated patient workflows.
- Frontend UI or `backend.ts` mirror changes unless a later contract change is
  explicitly approved.
- Full PubMed baseline mirroring in the first implementation.
- Persisting publisher-copyright or ambiguous-license abstract text.
- Publisher page scraping.
- PubTator/PMC full-text materialization beyond permissive/open-license
  metadata needed to decide abstract/text eligibility.
- LLM summarization, MedCPT/pgvector embeddings, RAG, or clinical
  recommendation generation.
- Final ACMG PS3/BS3 assertion from raw literature.
- Any startup, deploy-time, or request-time download/materialization path.
