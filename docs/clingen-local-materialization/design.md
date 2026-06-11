# ClinGen Local Materialization Design

## Status

Draft, approved to proceed by Steven in-session on 2026-06-12.

## Summary

Eamos should treat ClinGen Evidence Repository (eRepo) VCEP classifications and
the Criteria Specification Registry (CSpec) as operator-materialized source
assets, not request-time APIs. The backend should support a full public snapshot
of eRepo VCEP classifications and the CSpec specification graph, materialized by
an explicit CLI into a local SQLite source asset with manifests, provenance,
license/source metadata, and refresh behavior. Runtime lookup then reads local
first, with live eRepo fallback only when local is disabled, incomplete, or
explicit refresh is requested.

## Context And Scope

Today, `app/backend/app/tools/clingen.py` searches live eRepo in
`USE_REAL_APIS=true` mode and otherwise reads `clingen_fixtures.json`.
`LookupService` wraps that with `SourceCacheRepo`, and the report uses the same
`ToolResult` data to populate `report_profile.expert_panel`,
`clinical_consensus`, `functional_evidence`, and the lazy `clingen_vcep`
section. This is workable, but eRepo remains a live dependency unless cache rows
already exist.

ClinGen gene validity is already a local clinical source table, but that is
gene-disease evidence, not variant-level VCEP classification. CSpec is absent.
The new lane covers variant-level VCEP assertions, CSpec criteria/ruleset
content, source-cache wiring, health/preflight, and the section contract needed
by the frontend.

External source facts checked during this design:

- eRepo identifies itself as a public ClinGen Evidence Repository containing
  expert-curated variant pathogenicity assertions and supporting summaries.
- eRepo exposes UI downloads and paged `summary/classifications` API modifiers
  (`columns`, `values`, `matchTypes`, `matchMode`, `pgSize`, `pg`).
- CSpec documents REST JSON and JSON-LD APIs, paged entity listing, batch `ids`,
  and `pgSize` capped at 250.
- CSpec service inventory is beta and reports a registry-sized graph of about
  78k entities, including `SequenceVariantInterpretation`, `CriteriaCode`,
  `RuleSet`, `Organization`, `File`, `Gene`, and `Disease`.
- Both ClinGen pages warn that source information is not intended for direct
  diagnostic use without professional review. Eamos must preserve that boundary.

## Goals

- Materialize local eRepo VCEP classification rows and CSpec criteria/ruleset
  rows through explicit operator CLIs.
- Preserve the current public report contract for `ExpertPanelSection`,
  `AcmgWorksheetLedger`, `FunctionalEvidenceSummary`, and
  `LookupSectionEnvelope`.
- Prefer local materialized ClinGen rows at runtime when enabled and ready.
- Preserve live eRepo fallback and source-cache stale fallback.
- Keep source, provenance, license, launch-gate, freshness, and refresh metadata
  visible in health/preflight and section freshness.
- Prove report sections render from local fixtures/cache without live calls.

## Non-Goals

- No Supabase corpus/vector work.
- No runtime startup downloads or request-time bulk materialization.
- No browser/client access to raw ClinGen source assets.
- No clinical classification engine that reinterprets ACMG criteria beyond
  source assertions and Eamos worksheet hints.
- No broad rewrite of clinical consensus or frontend report components.

## Constraints

- Runtime must remain safe when the local asset is missing, stale, malformed, or
  disabled.
- The materializer may fetch public ClinGen APIs only as an explicit operator
  action with throttling/backoff.
- Tests must use tiny fixtures and must not depend on live ClinGen availability.
- CSpec is beta and its service/content IRIs are not permanent, so local rows
  must carry source version, fetched time, source URL, upstream IDs, and logical
  checksums.
- `CRISPR_OFFTARGET_PROVIDER` and Supabase corpus/vector guardrails remain
  unrelated and untouched.

## Proposed Design

Add a local ClinGen source asset service, `clingen_local.py`, with three layers:

1. **Store and inspection**: read-only SQLite access with schema validation,
   logical checksum verification, row counts, source version, and sanitized
   inspection output.
2. **Materialization**: explicit CLI import from operator JSONL files and
   optional paged API fetch. Writes a SQLite asset and manifest with source
   counts and checksum. No import-time path is called by the app.
3. **Runtime adapter**: `ClingenTool` reads local first when
   `clingen_local_enabled=true` and `refresh=false`. It returns the same
   `ToolResult` shape as live eRepo/fixtures. On local no-hit or local
   unavailable, it falls back to live eRepo only when `USE_REAL_APIS=true` and
   fallback is enabled.

The full source snapshot should be supported, but runtime should query by
stable identities:

- CAID when present.
- ClinVar VCV when available from ClinVar.
- Gene plus transcript/cDNA/genomic/protein HGVS terms as fallback.
- VCEP affiliation ID and CSpec document/ruleset IDs for provenance.

CSpec rows should not be forced into the public report shape immediately.
Instead, they enrich local VCEP rows and health/preflight metadata:

- criteria code labels and strength descriptors,
- ruleset/specification version,
- VCEP/organization identity,
- source file/document references,
- CSpec beta/version caveat.

## Architecture Views

Operator flow:

```text
ClinGen eRepo API or export
ClinGen CSpec API
        |
        v
eamos_clingen_local_fetch -> JSONL source snapshot
        |
        v
eamos_clingen_local_materialize
        |
        v
clingen-local.sqlite + manifest
        |
        v
eamos_clingen_local_preflight
```

Runtime flow:

```text
LookupService -> ClinVar -> ClingenTool
                         -> local ClinGen store
                         -> SourceCacheRepo fresh/stale rows
                         -> live eRepo fallback when allowed
                         -> ExpertPanelSection / ACMG / functional sections
```

## Interfaces And Data

Settings:

- `clingen_local_enabled=false`
- `clingen_local_sqlite_path=./data/bio_assets/clingen/clingen-local.sqlite`
- `clingen_local_manifest_path=./data/bio_assets/clingen/clingen-local.manifest.json`
- `clingen_local_fallback_on_no_hit=true`
- `clingen_local_max_results=25`
- `clingen_local_materialize_timeout_seconds=1200`
- `clingen_cspec_base_url=https://cspec.genome.network/cspec`

SQLite tables:

- `clingen_local_manifest`
- `clingen_erepo_classification`
- `clingen_erepo_classification_term`
- `clingen_cspec_entity`
- `clingen_cspec_link`

Public API contracts remain additive or unchanged. Provider-cache gains a
sanitized `source_assets.clingen_local` block.

## Alternatives Considered

- **Live eRepo plus source cache only**: lowest implementation cost, but still
  brittle for report sections and cannot explain CSpec source versions.
- **Download only user-requested VCEP rows**: cheaper but request-time source
  state remains incomplete, and no-hit/freshness cannot be interpreted well.
- **Full source snapshot through app startup**: easier operationally but unsafe
  for Render and violates existing source-asset guardrails.
- **Supabase corpus tables**: not allowed in this lane and unnecessary for the
  first local adapter proof.

## Tradeoffs

The chosen design adds one local source asset and two CLIs, which increases
backend code surface. In exchange, report lookups become deterministic for
covered variants, health can report ClinGen readiness, and CSpec provenance can
be preserved without live calls. Full eRepo/CSpec materialization is larger than
a seed-pack proof, but still small enough compared with PubMed/PMC and
appropriate for the adapter pattern.

## Cross-Cutting Concerns

- **Security/privacy**: source assets are public ClinGen data only. No user
  query history, patient identifiers, signed URLs, service-role secrets, local
  paths, or raw private object URIs are serialized.
- **Reliability**: local-ready status is checked by schema and logical checksum.
  Bad local assets fail closed to live/cache/fixture paths.
- **Observability**: preflight and provider-cache expose row counts, source
  versions, checksum state, enabled state, and fallback policy.
- **Cost**: no Supabase mutation. Full snapshot fetching is operator-run and
  bounded by paging/backoff.
- **Clinical safety**: ClinGen and CSpec remain source evidence. Eamos does not
  recalculate a clinical classification from criteria.

## Rollout And Migration

1. Land local store, JSONL materializer, preflight, and local-first tool path
   with tiny fixtures.
2. Use paged fetch mode for eRepo and CSpec to produce the operator snapshot.
3. Materialize a full source snapshot locally, record counts/checksum/version,
   and preflight.
4. Enable `CLINGEN_LOCAL_ENABLED=true` only after preflight passes.
5. Keep live fallback and source-cache stale fallback during rollout.

Rollback is setting `CLINGEN_LOCAL_ENABLED=false`. No schema migration or public
contract rollback is required.

## Open Questions

- Whether the first production full snapshot should use eRepo tab/comma export
  or paged JSON API as the canonical input. The runtime store supports both by
  normalizing to JSONL-like records.
- Whether CSpec `File` documents should be copied into the local asset or stored
  as metadata only for the first production snapshot.

## Decision

Implement local-first ClinGen eRepo/CSpec source materialization. Support a full
operator snapshot, but make tests and first merge use tiny fixtures. Preserve
current report schemas and live/cache fallbacks.
