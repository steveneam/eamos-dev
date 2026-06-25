# Eamos Architecture Inventory

Last updated: 2026-06-25 23:59 +1000 - Codex.
Status: Static inventory for the architecture consistency gate. This is not a
production sign-off, remote audit, deploy approval, or Supabase migration.

## Scope

This inventory maps the current local Eamos skeleton across:

- backend routes and route-level bounds;
- SQLAlchemy tables and cache ownership;
- lookup/report/analysis flow;
- frontend report surfaces;
- health/preflight/performance surfaces;
- storage and analytical-artifact boundaries.

It is deliberately conservative: if a property needs a live database, Supabase
advisor run, browser pass, or load test, this file marks it as unproven instead
of inferring safety from code shape.

## Canonical Flow

```text
input or uploaded file
  -> parser / resolver / normalizer
  -> normalized query identity
  -> source adapter, source cache, or prepared local index
  -> source_result_cache, source_cache, or domain cache row
  -> report shell / report section envelope
  -> frontend section slot
  -> health, preflight, timing, payload-size, cache-hit, and freshness proof
```

The same skeleton should apply to lookup, analysis, workbench, and report
sections. A route or section that cannot be mapped to this chain is a drift
candidate.

## Actionable Checklist

Use this table as the Task A closeout checklist. A gate is not passed until its
pass evidence is recorded in this repo or in a linked operator runbook. A fail
is any missing proof, unbounded path, silent blank UI state, or remote-only claim
without sanitized evidence.

| Item | Owner | Gate | Pass evidence | Fail evidence |
| --- | --- | --- | --- | --- |
| Route bounds matrix | Codex/backend | Every expensive route has auth or an explicit public model, rate/input bounds, and named failure states. | Static route inventory plus focused tests for lookup, batch, workbench, chat, report/run ownership, and payment webhook behavior. | Unauthenticated or unbounded mutation/read path; unclear ownership checks; generic 500 or blank failure state. |
| SQL and cache ownership | Codex/backend | New report/source state writes to `report_shell_cache`, `report_section_cache`, `source_result_cache`, or source-specific caches, not only `variant_cache.publication_data`. | Cache tests prove table-backed shell/section/source rows are read first and legacy JSON remains compatibility-only. | New section payload is stored only in legacy JSON, or cache key/freshness/schema version is missing. |
| Frontend report section registry | Codex scoped implementation, Claude design review when available | Required report sections have stable desktop slots before hydration. Mobile overflow/stability is inactive until Steven explicitly reactivates it. | `REPORT_SECTION_REGISTRY` defines ids, anchors, required flags, skeleton/empty/error contracts, nav/export participation, and preflight-required slots. | Section identity exists as scattered constants, or a required desktop section disappears when data is empty, delayed, stale, or failed. |
| Report preflight slot gate | Codex/frontend tooling | Desktop preflight fails before hydration if required report slots are missing. Sub-desktop widths are ignored. | `scripts/eamos-report-preflight.mjs` asserts registry-required slots for desktop fixtures or target URL. | Browser report renders without one of the required desktop anchors/slots and the preflight still exits 0. |
| Performance and memory proof | Codex backend, Claude browser verification as needed | Cold/warm report paths have p50/p95, payload size, provider-call, cache-hit, duplicate-viewer-fetch, and peak-RSS evidence. | `scripts/eamos-report-performance-audit.mjs --runs=<n>` records cold/warm p50/p95 and payload-ceiling checks; report preflight, focused tests, and memory-watch output are recorded with exact variants and dates. | Static code inspection is used as proof; no cold/warm distinction; no peak RSS or payload ceiling. |
| DuckDB/Parquet artifact contract | Codex/backend | Analytical lane has tiny-fixture layout, manifest, checksum, row-count, and sanitized health proof only. | Tiny fixture preflight validates `bronze/silver/gold/<release>/chrom=<chrom>/` without real corpus materialization. | DuckDB is placed on the request path, a multi-GB build runs, or health leaks local paths/object secrets. |
| PubMed/PMC corpus boundary | Codex/backend data lane | Literature stays layered: source objects, Parquet releases, runtime SQLite/FTS/vector stores, report/source caches. | Plan or tests show PubMed/PMC metadata, license, checksum, and runtime store boundaries; no full article blobs in Supabase Postgres. | Full text or large XML/PDF blobs are stored in Postgres, or license state is ignored. |
| Supabase production readiness | Steven approval plus Codex/operator | Remote schema/storage changes have RLS, grants, advisors, indexes, rollback, and sanitized health proof. | Supabase advisor output, verification SQL, private storage policy review, and rollback object/version are attached to the runbook. | Remote mutation without explicit approval; service-role key in client/bundle/log; public source bucket. |
| Operations and deployment gate | Steven/operator | No deploy, Render env mutation, Supabase mutation, startup download, or request-time materialization happens without explicit approval. | Command runbook names exact effects, dry-run/checksum proof, rollback, and expected health output. | Unapproved `vercel`/`vc`, Render env change, Supabase mutation, or startup/request-time source download. |

## Backend Route Inventory

| Route family | Current endpoints | Bounds seen in static scan | Gate status |
| --- | --- | --- | --- |
| Auth | `/api/v1/auth/register`, `/login`, `/logout`, `/me` | Auth rate limit on register/login. `/me` depends on current auth state. | Verify lockout/error payloads and token storage strategy before launch. |
| Lookup | `/api/v1/lookup`, `/summary`, `/sections`, `/parse`, `/publications` | Lookup rate limit by query subject; eager lookup trims lazy sections unless requested; parse disables forced coordinate resolution; optional timing header is gated by setting. | Good direction. Needs p50/p95, payload ceiling, provider-call, cache-hit, and stale-on-failure proof. |
| Gene viewer | `/api/v1/viewer` | Workbench rate limit. | Must retain seeded payload path so report viewer does not duplicate fetches when context already has a viewer snapshot. |
| Workbench | `/api/v1/primer`, `/crispr`, `/crispr/offtargets`, `/crispr/screening-primers`, `/crispr/ssodn`, `/align`, `/align/reference`, `/align/trace`, `/crispr/tide` | Workbench rate limit; trace uploads read at `TRACE_MAX_DECODED_BYTES + 1`; service-level sequence/matrix/sample limits exist. | Needs one matrix of max input sizes, timeout behavior, and memory ceiling per tool. |
| Batch | `/api/v1/batch/uploads`, `/api/v1/batch`, `/api/v1/batch/{job_id}` | Upload is authenticated, rate-limited, content-length checked, chunk-read bounded, decompressed-size and variant-count bounded. Create/read job are not auth-gated in the route file and rely on opaque upload/job references and service behavior. | Gate finding: decide whether batch create/read must require the same principal as upload, or document the opaque-reference security model and expiry. |
| Chat | `/api/v1/chat`, `/api/v1/chat/stream`, run chat endpoints | Authenticated principal plus chat rate limit and configured caps. | Verify streaming cancellation, request timeout, prompt-size limit, and no provider key leakage. |
| Search | `/api/v1/search`, `/api/v1/search/answer` | Authenticated; query result limit is bounded. | Verify FTS index coverage and top-k behavior for large corpus. |
| Variant library | `/api/v1/library` user mutations and folders; public popular/view count endpoints | User library routes authenticated and rate-limited; public popularity/view endpoints rate-limited and bounded. | Verify Supabase RLS for user-owned rows and FK/index coverage remotely. |
| Payments | `/api/v1/payments/checkout-session`, `/plan`, `/stripe/webhook` | Checkout/plan authenticated; webhook rate-limited and delegated to Stripe service for signature handling. | Verify webhook raw-body/signature path and idempotency in production config. |
| Reports/runs/reviews | `/api/v1/reports/upload`, `/runs`, `/runs/{id}`, review/approve/drop/pdf/report-payload/chat | Authenticated route dependencies visible. | Verify ownership checks for every run/report ID, not just presence of auth. |
| Evidence submission | `/api/v1/evidence` | Authenticated principal and evidence rate limit. | Verify service-role usage remains server-only and row ownership/RLS is enforced remotely. |
| Admin materialization | `/api/v1/admin/materialization/run`, `/clinical-release/import` | Requires authenticated principal, admin enable flag, hashed `X-Eamos-Admin-Token`, admin rate limit, sanitized failure details. | Strong operator boundary. Still requires explicit approval before any Render/Supabase mutation. |
| Health | `/healthz`, `/api/v1/health/provider-cache` | Public health surfaces include provider/cache readiness; DuckDB health reports sanitized disabled/missing/ready states. | Keep local paths, object URIs, and secrets out of all health payloads. |

## SQLAlchemy Table Inventory

| Table | Role | Architecture owner | Gate status |
| --- | --- | --- | --- |
| `users` | Local user identity projection | Auth/app data | Remote Supabase auth/RLS state must be checked outside local code. |
| `user_evidence_submissions` | User-submitted evidence | Evidence framework | Needs RLS/ownership proof and service-role containment. |
| `subscription_states` | Billing entitlement state | Payments | Needs webhook idempotency and FK/index review. |
| `collection`, `saved_variant`, `variant_view_count`, `user_library` | Variant library and popularity state | User library | User-owned tables need RLS, FK indexes, and ownership checks. |
| `reports`, `report_runs` | Uploaded/generated report records | Report workflow | Ownership checks and payload size policy must be audited per route. |
| `search_documents`, `search_variants` | Search corpus and variant index | Search/AI retrieval | Needs FTS/index freshness and rebuild contract. |
| `variant_cache` | Legacy variant cache plus compatibility JSON | Compatibility layer | Do not add new report-section state here; migrate reads to report/source cache where possible. |
| `normalized_variant` | Canonical gene/cDNA/protein/query identity | Lookup normalizer | Correct backbone for consistent lookup/report cache keys. |
| `report_shell_cache` | Prepared report shell without lazy-heavy sections | Report cache | Good canonical owner for shell cache; verify stale policy and schema version bump discipline. |
| `report_section_cache` | Renderable section envelope cache | Report cache | Good canonical owner for lazy section results; verify status/stale/error payload contract. |
| `source_result_cache` | Provider/source result rows | Source cache | Correct owner for table-backed source rows; verify source IDs, freshness, and provenance coverage. |
| `section_hydration_status` | Lazy section status tracking | Report hydration | Useful for UI skeleton/status consistency; ensure frontend consumes the same states. |
| `source_cache` | Generic source cache keyed by source/cache key | Source adapters | Keep bounded and versioned; avoid undifferentiated JSON dumps for long-lived report state. |
| `protein_annotation_cache` | Protein/domain annotation cache | Protein/report sections | Verify input-size cap, freshness/version, and fallback disclosure. |

Local indexes and unique constraints exist for the newer cache tables. Production
readiness still requires a Supabase-side migration/advisor pass for:

- RLS on user-owned and service-role-written tables;
- FK indexes;
- composite indexes matching hot filters;
- unique constraints that match cache-key invariants;
- storage policies for private source assets.

## Cache Boundary Inventory

| Cache or artifact | Canonical content | Should not contain |
| --- | --- | --- |
| `report_shell_cache` | Identity, summary shell, eager lightweight payload, schema version, stale policy. | Lazy section payloads that should be independently refreshable. |
| `report_section_cache` | One section envelope per query/schema/section. | Raw provider artifacts or user-owned mutable state. |
| `source_result_cache` | Source-specific result rows, freshness, status, provenance, warnings. | Render-only UI state. |
| `source_cache` | Adapter-local source payloads that need key/value semantics. | Whole report blobs that bypass section envelopes. |
| `variant_cache` | Compatibility and older variant cache state. | New report-source or report-section canonical writes. |
| DuckDB/Parquet analytical lane | Immutable or release-versioned analytical/source artifacts. | Single-coordinate hot request state, auth/user/payment data, or mutable report edits. |

## Frontend Report Inventory

| Surface | Current role | Gate status |
| --- | --- | --- |
| `ReportClient.tsx` | Main report composition, lazy override IDs, section anchors, section renders. | Needs a central section registry before more sections are added. |
| `LazySection.tsx` | IntersectionObserver-driven section fetch to `/api/v1/lookup/sections`, placeholder/error/success state. | Good generic primitive; required section slots should be registry-driven and preflight-enforced. |
| `ReportGeneViewer.tsx` | Uses seeded viewer payload when available, otherwise fallback fetch. | Keep no-duplicate-fetch invariant under browser verification. |
| `ReportSectionNav.tsx` | Scroll-spy navigation for report anchors. | Should consume registry metadata rather than its own hard-coded list. |
| Export serializers | TSV/HTML/full report export. | Should consume section registry metadata where possible, so export coverage does not drift from UI coverage. |
| `DataCurrencyLine.tsx` and `ProvenanceNote.tsx` | Source freshness and non-live disclosure. | Must remain visible for stale/fallback/partial states. |
| `scripts/eamos-report-preflight.mjs` | Browser/preflight check for lazy sections and report rendering. | Extend to assert required section slots before hydration and fail on missing registry slots. |

Current lazy-eligible section IDs are:

- `publications`;
- `therapies_trials`;
- `computational_deep_dive`;
- `clingen_vcep`.

Task 5 should make these IDs data, not scattered constants. The registry should
include:

- section ID;
- anchor ID;
- title/number;
- eager payload selector;
- lazy fetch contract;
- skeleton component;
- empty/partial/stale/failed display contract;
- export participation;
- navigation participation;
- required/preflight flag.

## Analysis and Artifact Inventory

DuckDB/Parquet is the analytical lane, not the point-lookup lane.

| Use case | Preferred runtime | Reason |
| --- | --- | --- |
| Single variant lookup | Prepared report cache, tabix/local indexes, SQLite/source-specific adapters | Lowest request latency and simplest memory behavior. |
| Lazy report section fetch | `report_section_cache` plus source-specific cold miss builders | Lets one section refresh without rebuilding full lookup. |
| Batch VCF, region, cohort, freshness scan | DuckDB over bounded Parquet releases or derived Gold tables | Columnar scan/pushdown helps analytical workloads. |
| Durable large source storage | Private Supabase Storage objects with manifest/checksum | Keeps multi-GB corpora out of Postgres and Git. |
| Runtime serving subset | Render persistent disk approved release and compact serving indexes | Avoids startup/request downloads and controls disk footprint. |
| Mutable app/user state | Supabase Postgres with RLS | Needs SQL semantics, ownership, constraints, and transactionality. |

DuckDB Phase 1 must stay tiny-fixture-only:

- define artifact layout;
- define manifest schema;
- validate row counts/checksums;
- prove sanitized disabled/missing/ready health;
- do not materialize multi-GB releases;
- do not add request-route dependency.

## Literature Corpus Inventory

The local code already points toward a layered PubMed/PMC architecture:

- `pubmed_local` is a generated runtime SQLite store with article rows, term
  rows, literature edges, source-file coverage, a manifest row, logical
  checksum, and optional FTS;
- `literature_embeddings` is a separate generated SQLite store for RAG snippets;
- `generated_source_artifacts` treats both as generated runtime artifacts with
  manifests and private-storage identities;
- report publications currently flow through lookup/source cache/report section
  paths rather than a raw corpus query in the UI.

Recommended source-specific layers:

| Layer | PubMed citations | PMC article datasets | Runtime rule |
| --- | --- | --- | --- |
| Bronze | NCBI annual baseline XML plus daily update files and checksums. | PMC OA/cloud/FTP inventory, article-object JSON metadata, XML/text/PDF/media object identity, license grouping. | Immutable, manifest-driven, never request-time downloaded. |
| Silver Parquet | Normalized citation metadata, PMID, PMCID, DOI, journal, dates, terms, source status, deleted/revised handling, abstract policy. | Normalized PMCID/PMID joins, license status, retraction status, article-object checksums, extracted metadata/features. | Good for rebuilds, audits, freshness, and analytics. |
| Gold Parquet | Gene/variant/publication joins, source counts, publication timeline, license-permitted abstract/text features. | License-approved full-text feature tables, section/entity edges, PMID/PMCID crosswalks. | Query with DuckDB during offline builds or bounded analysis. |
| Runtime SQL/FTS/vector | `pubmed_local` SQLite, term indexes, FTS, RAG embedding SQLite. | Only bounded license-approved subsets, not the whole raw object corpus. | Serve report sections and RAG without scanning full Parquet. |
| Supabase Postgres | Release metadata, job status, source versions, cache references, user-visible report cache. | Same, plus storage object manifests and license policy rows. | Govern and audit; do not store full article blobs. |

Concrete SQL/domain entities for a future robust literature schema:

- `literature_release`;
- `literature_source_file`;
- `literature_article`;
- `literature_article_identifier`;
- `literature_article_license`;
- `literature_article_term`;
- `literature_entity_edge`;
- `literature_section_feature`;
- `literature_retraction_status`;
- `literature_embedding_manifest`;
- `literature_materialization_job`.

Gate findings for literature:

1. PubMed citation metadata is a good Parquet candidate for durable rebuilds,
   but the report path should continue using generated SQLite/FTS/source-result
   caches unless benchmarks prove DuckDB is faster for that specific query.

2. PMC full text is a license-governed object corpus, not just a bigger PubMed
   table. Start with metadata, licenses, checksums, PMCID/PMID joins, and
   extracted features before attempting any full-text materialization.

3. Supabase storage savings should come from avoiding multi-GB Postgres rows and
   keeping immutable corpus releases in private object storage. Render savings
   should come from seeding only the current runtime subset and compact indexes.

## Findings Requiring Action

1. Frontend section registry is the next consistency fix.

   The report UI has the right primitives, but section identity is still spread
   across `ReportClient`, `LazySection`, navigation, export, and preflight code.
   That is maintainability drift waiting to happen.

2. Batch job create/read need a security model decision.

   Upload is authenticated and bounded. Static route inspection shows create/read
   are not route-authenticated. If jobs can expose uploaded variant lists or
   results, they should be principal-bound or protected by signed opaque
   references with expiry and tests.

3. Legacy cache compatibility must not become the new architecture.

   `variant_cache` remains useful as a compatibility path, but new report
   sections should flow through `source_result_cache` and `report_section_cache`.

4. Supabase production readiness cannot be inferred locally.

   Local SQLAlchemy models are not enough. Before production sign-off, run
   Supabase advisors, inspect RLS policies, inspect grants, and verify indexes
   against the real schema.

5. "No performance issues or memory leaks" needs measured gates.

   Static code shape can find obvious unbounded reads and duplicate fetches, but
   final confidence needs browser preflight, endpoint p50/p95, payload-size,
   cache-hit, provider-call, and peak-RSS measurements for cold and warm report
   paths. The report performance audit now supports repeated cold/warm runs and
   payload-size ceilings; peak-RSS evidence still needs a local or approved
   live memory watch.

6. Slow legacy integration tests no longer own the fast report-cache gate.

   `tests/test_report_cache_contract.py` is the fast named cache/report contract
   target. Broader integration-style cases in `tests/test_variant_cache.py` are
   marked `slow`, so ordinary feature commits can run the contract target or
   `tests/test_variant_cache.py -m "not slow"` instead of the full multi-minute
   legacy file.

7. Parquet conversion needs source-by-source benchmarking.

   It should save durable storage for large immutable analytical/source
   artifacts, but it can increase CPU/decompression/temp-disk cost and may be
   slower than loaded DuckDB tables for repeated join-heavy analytics.

## Read-Only Verification Checklist

Before claiming the architecture is production-ready:

- run focused backend tests for lookup sections, report cache, DuckDB health,
  health API, batch limits, workbench limits, and route ownership;
- run frontend typecheck and focused report component tests;
- run browser preflight for ABCA4/RPE65/USH2A cold and warm reports;
- record p50/p95 and peak RSS for lookup summary, lazy section fetch, full
  report, and viewer fallback;
- run a secret/environment scan for client bundle exposure;
- run Supabase advisors and migration/index/RLS review;
- verify Render disk footprint and no startup/request downloads;
- prove DuckDB disabled/missing/ready health payloads are sanitized;
- keep all remote mutations behind explicit Steven approval.
