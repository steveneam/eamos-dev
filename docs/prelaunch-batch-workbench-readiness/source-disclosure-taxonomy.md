# Batch And Workbench Source Disclosure Taxonomy

Status: Sprint A Task 0.2 baseline.
Created: 2026-06-28 by Codex.

## Purpose

Batch and Workbench can launch with a mix of source-backed, local-provider,
fallback, fixture, gated, and unavailable states only if those states are
visible and consistent. This taxonomy is the shared vocabulary for launch
labels and future additive API metadata.

## Statuses

| Status | Display label | Valid when | Must not be used when |
| --- | --- | --- | --- |
| `source_backed` | Source-backed | The result was derived from an identified external or generated source artifact with source identity, version, or release metadata available. | The result came from a bundled sample, mock, heuristic-only fallback, or provider that failed open. |
| `local_provider` | Local provider | A deterministic local engine produced the result and the provider/runtime identity is known, but it is not claiming a materialized source corpus. | The result depends on a missing local asset, frontend-only sample, or external live request hidden behind a fallback. |
| `fallback` | Preview fallback | The app intentionally returned a degraded fallback because a source/provider is absent, disabled, or unavailable, and the fallback is useful for preview or continuity. | The output is being presented as an authoritative source-backed annotation. |
| `fixture` | Fixture | The output is bundled test/demo data, a curated static sample, or an offline UI fixture. | A live backend/provider computed the result for the submitted user input. |
| `gated` | Gated | The feature/provider exists but is disabled pending approval, asset readiness, license review, env flip, or launch decision. | The provider is enabled and returning real results. |
| `unavailable` | Unavailable | No result can be produced for the input/provider state, and no fallback is being used. | A fallback or fixture was rendered instead. |

## Batch Mapping

- Backend-annotated cohort rows from `/api/v1/batch` should be treated as
  `source_backed` only for fields that came from the lookup/report source
  stack. Row warnings remain part of the disclosure.
- Browser-parsed rows before Generate are `fixture` only if they are bundled
  examples; user-imported VCF rows before backend annotation are not annotated
  and must not be labeled source-backed.
- Failed create, poll, auth, validation, rate-limit, or backend errors are
  `unavailable`, not fallback.
- A future deliberate demo mode may use `fallback`, but it must be explicit in
  UI state and must not reuse ordinary backend failure handling.
- Current panel filters are local launch panels with warning labels. They are
  not source-backed PanelApp/ClinGen/GenCC panels unless a generated panel
  catalog artifact exists and provider-cache/preflight reports it ready.

## Workbench Mapping

- Primer3 placement and thermodynamic calculations are `local_provider` when
  the backend Primer3 route computed them.
- Primer specificity is `local_provider` for template-only specificity and
  `source_backed` only when an approved source-backed specificity provider is
  enabled and identified.
- SNP masking is `source_backed` only when local dbSNP is configured and the
  response identifies that source path through sanitized metadata.
- CRISPR deterministic guide design is `local_provider`.
- CRISPR off-targets are `fallback` when `CRISPR_OFFTARGET_PROVIDER=auto` falls
  back to mock output. They are `source_backed` only when the indexed SQLite
  provider is built, mounted, preflighted, enabled, and reported in metadata.
- ssODN local MANE/hg38 context is `source_backed` when resolved from the local
  context source. Mock genomic windows are `fallback`.
- Align with user-provided pasted sequence or trace data is `local_provider`
  unless the response explicitly identifies a source-backed reference context.
- TIDE-style observed-only analysis is `source_backed` for the observed trace
  evidence supplied by the user and `local_provider` for deterministic
  computation over that evidence.
- Bundled offline samples are `fixture`.

## Future Additive Metadata Shape

When schema changes are implemented, Batch and Workbench responses should be
able to expose this optional shape without breaking current clients:

```text
source_status: source_backed | local_provider | fallback | fixture | gated | unavailable
provider_id
provider_label
source_version
cache_status
warnings
requirements
```

Backend routes remain authoritative. Frontend code may render labels from this
metadata, but it must not upgrade a result to `source_backed` based only on
client-side assumptions.

## Launch Rule

When in doubt, choose the less authoritative label. A fallback that keeps the
experience usable is acceptable for launch only when it is visibly marked and
does not replace a failed backend operation silently.
