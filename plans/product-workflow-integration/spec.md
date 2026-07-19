# Integrated Product Workflow Specification

Status: proposed contract freeze; implementation and lane launch require Steven's approval.

Spec stamped: 2026-07-19 09:15 +0000 · Codex.

## Product Outcome

A user can start with one variant, a cohort, or one or more publications; move
between Report, Batch, Paper, and Workbench without losing scientific context;
select any resolvable region of the full gene; use that exact region and
sequence basis in Primer, CRISPR, or Align; compare variants; save or export the
result; refresh or return later; and always know whether each fact/result is
source-backed, locally computed, fixture-backed, gated, or unavailable.

The four surfaces remain distinct:

- **Report** explains one variant and its evidence.
- **Paper** discovers and resolves variant mentions from publications.
- **Batch** annotates a cohort and compares selected variants.
- **Workbench** inspects and edits sequence context and runs molecular-design
  tools.

## Invariants

1. Operational clinical labels come from typed backend facts. A frontend may
   format a typed label but must not infer a final classification from prose,
   score thresholds, or missing data. Explicitly labelled educational what-if
   components may compute locally and must remain visually separate.
2. Canonical genomic coordinates are GRCh38, 1-based, closed intervals unless a
   field explicitly declares another build/basis. Every interval declares its
   coordinate system and orientation.
3. Raw paper text, PDFs, VCF rows, AB1 traces, free-form notes, and edited
   sequences never appear in URLs, analytics, error telemetry, or logs.
4. A fixture or fallback never masquerades as source-backed output. Missing
   measurements render `not assessed`/`unavailable`, not illustrative numbers.
5. Full gene means one continuous genomic locus—including introns and UTRs—
   navigable as one surface. Virtualization is an implementation detail, not
   user-visible pagination.
6. A tool result is bound to the exact variant, transcript, reference build,
   selection, sequence basis, and edit revision used to compute it. Context
   changes make previous results visibly stale; they are never silently reused.
7. Raw uploads are ephemeral by default. Durable results are owner-scoped and
   deletable. Any different retention policy requires explicit user disclosure
   and a separately approved storage design.
8. Auth identity is derived only from a verified token. No client-supplied user
   id, folder owner, job owner, or workspace owner is trusted.
9. Batch is the variant-comparison surface; Align is the sequence-comparison
   tool. A legacy `tool=compare` value redirects to Batch with a notice and is
   not shown as a fifth Workbench tool.
10. Existing evidence/provider/cloud/Phase-7 holds remain unchanged.

## Proposed Contract Freeze: Product Workflow V1

The following is the only shared seam for the sprint. Lane A lands it
schema-first in Pydantic, mirrors it in `app/web/lib/backend.ts`, and makes the
frontend-contract canary green. Once that commit is approved and merged, all
other lanes treat these shapes and semantics as frozen. A needed change pauses
the sprint for re-plan.

### CanonicalVariantRefV1

```text
schema_version: "canonical_variant_ref.v1"
gene: uppercase string
cdna: string
transcript: string | null
protein_hgvs: string | null
genomic_hg38: string | null
variant_key: string
species: "human"
genome_build: "GRCh38"
resolution_status: "resolved" | "ambiguous" | "unresolved"
source_support: string[]
warnings: string[]
```

`variant_key` is the stable server-issued identity used by links, library rows,
Batch rows, related variants, and workspaces. Gene+cDNA remains the human-
readable round-trip pair. An ambiguous or unresolved reference cannot execute a
molecular-design tool.

### WorkflowContextV1

```text
schema_version: "workflow_context.v1"
context_id: opaque string | null
variant: CanonicalVariantRefV1 | null
origin_surface: "report" | "paper" | "batch" | "workbench" | "library" | "search"
return_to: bounded same-origin path | null
batch_run_id: opaque string | null
paper_run_id: opaque string | null
workspace_id: opaque string | null
active_tool: "viewer" | "primer" | "crispr" | "align" | null
selection: SelectionRangeV1 | null
created_at: UTC timestamp
expires_at: UTC timestamp | null
```

Public/anonymous navigation may reconstruct a context from canonical bounded URL
fields. Private or large context uses `context_id`/run ids. The server always
revalidates identity and ownership before resolving an opaque id.

### SelectionRangeV1

```text
schema_version: "selection_range.v1"
variant_key: string
transcript: string
genome_build: "GRCh38"
chrom: string
genomic_start: positive integer, 1-based inclusive
genomic_end: positive integer, 1-based inclusive
strand: "+" | "-"
orientation: "genomic_forward" | "genomic_reverse" | "transcript"
sequence_basis: "reference" | "variant" | "edited"
edit_revision: non-negative integer
sequence_sha256: string
cdna_start: integer | null
cdna_end: integer | null
cds_start: integer | null
cds_end: integer | null
protein_start: integer | null
protein_end: integer | null
overlaps: Array<"utr5" | "utr3" | "cds" | "exon" | "intron">
```

The backend supplies biological projection. The browser may calculate row-local
geometry but may not invent cDNA/CDS/protein mappings. Mixed or intronic ranges
legitimately have null transcript/protein bounds.

### ProcessingDisclosureV1

This complements the existing Workbench `SourceDisclosure`; one explains where
the result came from, the other where user input was processed.

```text
execution: "browser" | "eamos_backend" | "external_provider"
provider_id: string
provider_label: string
input_classes: Array<"variant_id" | "sequence" | "vcf" | "paper_text" | "pdf" | "trace" | "notes">
raw_input_persisted: boolean
retention: "none" | "request_lifetime" | "ttl" | "account_saved"
expires_at: UTC timestamp | null
user_deletable: boolean
consent_required: boolean
warnings: string[]
```

Paper gateway submission requires an explicit pre-submit disclosure/consent
state. Browser-local Align declares `execution=browser` and no raw persistence.

### WorkflowRunV1

```text
schema_version: "workflow_run.v1"
run_id: opaque string
kind: "batch" | "paper" | "workbench"
status: "draft" | "queued" | "running" | "completed" | "partial" | "failed" | "cancelled" | "expired"
owner_scope: "account" | "anonymous_session"
context: WorkflowContextV1
done: integer
total: integer
created_at: UTC timestamp
updated_at: UTC timestamp
expires_at: UTC timestamp | null
warnings: string[]
source_disclosures: SourceDisclosure[]
processing_disclosure: ProcessingDisclosureV1 | null
artifacts: WorkflowArtifactV1[]
```

Owner identity is never serialized from a client request. Anonymous-session
runs may be ephemeral and non-resumable after the browser session; the UI must
say so. Account runs expose list/read/cancel/delete routes with owner checks.

### WorkflowArtifactV1

```text
artifact_id: opaque string
kind: "report_tsv" | "report_html" | "batch_tsv" | "paper_tsv" | "fasta" | "primer_tsv" | "primer_fasta" | "guide_tsv" | "ssodn_txt" | "alignment_tsv" | "workspace_json"
filename: safe string
media_type: string
generated_at: UTC timestamp
source_run_id: opaque string | null
context_digest: string
sha256: string
download_state: "client_generated" | "ready" | "expired"
```

Exports include a small provenance header/manifest naming context, build,
sequence basis, source statuses, warnings, and generation time.

### RelatedVariantGroupV1 And CuratedVariantPageV1

```text
RelatedVariantItemV1:
  variant: CanonicalVariantRefV1
  relationship: "nearby" | "same_gene" | "same_class" | "same_condition"
  distance_bp: integer | null
  classification: typed classification | null
  evidence_axis_summary: typed per-item summary | null
  source_disclosure: SourceDisclosure
  report_href: canonical /report href

RelatedVariantGroupV1:
  items: deduplicated RelatedVariantItemV1[]
  warnings: string[]

CuratedVariantPageV1:
  gene: string
  classification_filter: typed classification | null
  consequence_filter: typed consequence bucket | null
  items: CanonicalVariantRefV1[]
  next_cursor: opaque string | null
  total: integer
  source_disclosure: SourceDisclosure
  warnings: string[]
```

Condition summaries remain condition summaries. They do not appear in a
“related variants” lane unless the backend can return actual variant identities
for the condition relationship. Curated-grid cells open a bounded page rather
than fabricating rows from counts.

## URL And Handoff Grammar

Allowed public URL fields:

```text
/report?gene=&cdna=&transcript=&from=
/workbench?gene=&cdna=&transcript=&tool=&view=window|locus&context_id=
/compare?run_id=&context_id=&view=cohort|compare
/paper?run_id=&context_id=
```

Rules:

- `gene`, `cdna`, and `transcript` are accepted only after normal resolution.
- `tool` is deep-linkable and drives the Workbench tool rail.
- `context_id` and run ids are opaque, short-lived/owner-scoped lookups.
- `return_to` is stored in context and restricted to same-origin product paths.
- Selection sequence, paper text, VCF content, trace data, notes, classifications,
  and evidence payloads are never URL parameters.

Required handoffs:

| From | To | Action |
| --- | --- | --- |
| Report | Workbench | Open Sequence, Primer, CRISPR, or Align with canonical variant/transcript and optional selection |
| Report | Batch | Add current variant; Add related/curated selections |
| Report | Paper | Find this variant in papers; sets target context without pre-populating paper content |
| Paper candidate | Report / Workbench / Library / Batch | Enabled only for a resolved canonical candidate; ambiguous candidates require selection first |
| Batch row | Report / Workbench / Library | One canonical row context |
| Batch selected rows | Compare subview | 2–3 variants, typed evidence columns, no Workbench `compare` tool |
| Library item | Report / Workbench / Batch | Same canonical action set on every surface |
| Workbench result | Report / Library / export | Return to originating variant; save only explicit user artifacts |

Navigation through ModePill is non-mutating. Explicit handoff actions move data
or create a run. If meaningful context exists, the destination shows a compact
“From Report/Paper/Batch” chip and a clear way to discard it.

## Shared State Machine

Every async surface maps its implementation-specific state onto:

```text
idle → validating → auth_required? → consent_required? → queued/running
     → completed | partial | empty | failed | cancelled | expired
```

Cross-cutting rules:

- `auth_required` and `consent_required` happen before uploading/processing.
- `partial` preserves successful source results and names failed sources.
- `empty` is a successful computation with no qualifying rows, not an error.
- `failed` gives a safe summary, retry, and preserved inputs when permitted.
- `expired` keeps enough metadata to explain what ended and how to rerun.
- Context changes during/after a run mark the result `stale`; they do not erase
  it or present it as current.
- Cancellation aborts browser work, requests backend cancellation when a run id
  exists, and applies the retention policy.

## Surface Requirements

### Report

- Keep the current chapter/report hierarchy and call-card-first reading flow.
- Replace free-form operational classification inference with typed display
  facts from the response.
- Return deduplicated related-variant groups from the backend. Each card exposes
  Report, Workbench, Library, and Add-to-Batch actions.
- Turn the curated distribution into a keyboard-operable grid. Enter/Space on a
  non-empty cell opens `CuratedVariantPageV1`; rows can open Report or be added
  to Batch.
- Keep condition evidence in the disease section. If actual related variants
  are unavailable, do not label condition summaries as a variant lane.
- Add explicit Report→Primer/CRISPR/Align shortcuts and an Add-to-Batch action.
- Preserve current policy-aware TSV/HTML exports and add a provenance manifest.
- Replace null Suspense fallback with the report loading shell.

### Batch And Variant Compare

- Preflight authentication before upload/create. Preserve the staged cohort
  while sign-in completes.
- Never persist raw upload snapshots by default. If a temporary spool is needed,
  create it owner-bound with restrictive permissions, expiry, crash cleanup,
  cancel/delete cleanup, and tests.
- A truncated browser preview must retain an explicit “reattach full file” state
  after refresh; it may never submit the preview as if it were the full file.
- Make jobs resumable by opaque account run id. Support read, page, cancel,
  delete, and bounded history. Do not store original raw VCF unless a separately
  disclosed option is approved.
- Use server paging or row virtualization; do not collect/render the entire
  maximum cohort merely to display the first viewport.
- Canonicalize `report_href` to `/report?...` on the backend and consume it
  directly on the frontend.
- Add row selection and a 2–3-variant Compare subview. Comparison columns use
  typed backend facts and show missing/source status per cell.
- Add TSV/CSV and workflow-manifest export. Large exports stream/page without
  materializing the whole cohort in the DOM.
- Make pane separators keyboard adjustable and persist filter/view state in the
  run snapshot.

### Paper → Variants

- Attach the current bearer token exactly as Batch/Library do. If absent or
  expired, render an auth-required card before processing and resume the staged
  input after sign-in.
- Replace “Mock extraction” with a typed source/processing badge:
  deterministic local extractor, external gateway, frontend fixture, or
  unavailable.
- Before a gateway request, show `ProcessingDisclosureV1` and require explicit
  consent for sending publication text to the named provider.
- Rename the patient-data guardrail to describe actual input posture; arbitrary
  publications may contain person/case language even when Eamos does not ask
  for patient records.
- Populate source metadata when it can be extracted; show “metadata unavailable”
  rather than illustrative values on live runs.
- Run sources with bounded concurrency, independent status, cancel, retry, and
  partial completion.
- Persist an owner-scoped extraction workspace containing source metadata,
  candidate results, and warnings. Raw files/text remain ephemeral by default.
- Keep fail-closed candidate actions and add resolved candidate→Workbench.
- Normalize errors; never place backend JSON bodies directly in the UI.
- Replace null Suspense fallback with the Paper intake shell.

### Workbench Sequence Viewer

- Treat the existing full-locus schema and virtualized renderer as the base.
  Do not fork a second viewer.
- Make full locus the complete gene/transcript navigation surface with:
  whole-gene minimap and viewport indicator; exon/variant/coordinate/sequence
  search; window↔locus continuity; genomic/transcript orientation; active
  transcript switching; and return-to-variant.
- Implement one range interaction model in window and locus modes:
  click, drag, Shift+click, Shift+Arrow, keyboard start/end extension, touch
  handles, edge autoscroll, Escape clear, and a coordinate-entry alternative.
- Emit `SelectionRangeV1` on every selection. Screen readers receive a concise
  range summary and commands, not 128k individually focusable bases.
- Apply edits as sparse revisions over immutable source sequence. Substitution,
  insertion, deletion, replace, undo, and redo work in both views. Consequence
  fields remain null/unavailable when projection is not biologically valid.
- Context/tool/view/selection are deep-linkable where safe. Notes, edits, and
  results live in an explicit workspace with dirty/saved status.
- Explain the default RPE65 example; never silently imply it is user data.
- Remove narrow-screen overflow and prove 320, 390, 768, 1024, and desktop
  layouts.

### Primer

- Accept `SelectionRangeV1` or a resolved default target; record the exact
  sequence basis and revision in the result.
- Return true Primer3/provider measurements only. Missing secondary-structure,
  SNP-avoidance, or specificity data is `not_assessed` with requirements.
- If no pair qualifies, explain which constraints eliminated candidates and
  offer bounded adjustments; an empty result remains honest.
- Show only implemented modes. ARMS or whole-genome specificity stays gated
  until the provider is ready.
- Overlay returned primer coordinates precisely in the viewer.
- Export TSV, FASTA, and provenance manifest.

### CRISPR

- Resolve and display the on-target locus from canonical context. Off-target
  submission is disabled until the user confirms that locus; no unrelated
  hard-coded coordinate is accepted.
- Show only supported enzymes/providers for the active deployment.
- Preserve clear source/fallback disclosure for guide scores, off-target index,
  screening primers, ssODN, and outcomes.
- Bind guides and donors to `SelectionRangeV1`, sequence basis, build, and
  revision. Context changes make prior results stale.
- Require auth and processing disclosure for server-processed trace uploads.
- Keep TIDE-style wording bounded to the implemented observed analysis.
- Export guides, off-targets, primers, donors, outcome table, and manifest.

### Align

- Browser-local paste/FASTA/AB1 remains the default and visibly says the trace
  stays in the browser.
- Reference lookup supports canonical variant/transcript and identifier input.
- The unused general backend `/align` route is either documented for API clients
  or deprecated; the UI must not silently choose a second processing path.
- Alignment result, differences, target state, quality, and source disclosure
  persist in the workspace until cleared.
- Export alignment TSV/plain text and manifest. Server processing, if later
  offered, is opt-in, authenticated, and disclosed.

## Persistence And Deletion

- **Anonymous:** bounded session state; optional browser-only workspace with an
  expiry label and one-click clear. No claim of cross-device persistence.
- **Account:** owner-scoped run/workspace metadata and results. Raw source bodies
  are absent unless a separately approved retention feature is selected.
- **Library v2:** per-item `updated_at`, deletion tombstones, schema version,
  deterministic conflict resolution, migration from v1, and explicit local-data
  purge. Sign-out does not silently merge another user's local cache.
- **Automatic edit log:** 48-hour default TTL. Deliberately saved notes/results
  do not expire with transient logs.
- **Delete:** removes durable run/artifact rows and any ephemeral server spool;
  UI immediately clears local mirrors. Deletion and expiry are testable.

Any production Supabase migration is a separate Steven-approved action. A lane
may author a local migration file only if the approved lane scope explicitly
includes it; no lane applies it to a shared project.

## Accessibility Acceptance

- Zero document-level horizontal overflow at 320px and above.
- All controls have visible focus, names, states, and keyboard paths.
- Range selection is fully operable without a pointer; touch targets are at
  least 44×44 CSS px where controls are discrete.
- Virtualized content keeps stable focus/selection semantics when rows unmount.
- Split panes implement the ARIA separator keyboard pattern.
- Async progress uses non-spammy live regions; errors focus a summary and retain
  input where safe.
- Color is never the only carrier of classification, selection, error, source,
  or stale state.
- Motion respects `prefers-reduced-motion`; focus is restored after surface,
  tool, drawer, and modal transitions.

## Performance Budgets

Initial budgets are no-regression bounds grounded in the audit and become
executable checks in Lane E:

- RPE65 fixture lookup response: ≤150KB uncompressed and ≤250ms warm local.
- RPE65 viewer window: ≤20KB and ≤100ms warm local.
- RPE65 full locus: ≤300KB; ABCA4 full locus: ≤1MB uncompressed.
- Full-locus interaction: no >100ms input task during ordinary scroll/select;
  target 50fps or better on the repo's Chrome verification host.
- Batch: at most 500 rows mounted/rendered at once; paging/virtualization for
  larger cohorts.
- Paper: at most two concurrent extraction requests by default; cancel aborts
  remaining work.
- Mobile: no root overflow or clipped primary control at tested widths.

Production latency/SLO values require a separate production read-only baseline;
local fixture numbers must not be presented as production guarantees.

## Definition Of Done

The integrated slice is complete only when:

1. all three P0 findings have executable regressions and are fixed;
2. every required handoff round-trips canonical context and preserves `return_to`;
3. Batch and Paper can resume owner-scoped runs without retaining raw input by
   default;
4. full-locus selection/edit/navigation feeds all three Workbench tools;
5. Primer, CRISPR, and Align exports identify source, context, basis, revision,
   and warnings;
6. fixture/fallback/unavailable states are visibly truthful;
7. Report curated/related variants are actionable without frontend clinical
   inference;
8. keyboard, screen-reader, mobile, and reduced-motion acceptance passes;
9. performance budgets and structural boundaries pass;
10. focused tests, full local verify, committed browser ratchet, and required CI
    are green before any merge.
