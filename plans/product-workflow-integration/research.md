# Product Workflow Integration Audit

Status: complete planning evidence; no product implementation or cloud mutation.

Audit stamped: 2026-07-19 09:15 +0000 · Codex.

## Scope And Method

This audit traces the live Next.js product and its FastAPI contracts across:

- Variant Report, including related, nearby, same-class, condition, and curated
  variant surfaces;
- Paper → Variants;
- Batch import, annotation, filtering, comparison, and row handoffs;
- Workbench sequence viewing, full-locus viewing, editing, Primer, CRISPR, and
  Align;
- the shared ModePill, WorkRail, Library, Ask Eamos, and account seams;
- auth, uploads, retention, privacy, accessibility, responsive behavior,
  performance, persistence, exports, source disclosure, and tests.

Evidence came from direct code reads, focused tests, local API probes, and a
headless-Chrome run against the local app (`:3532`) and backend (`:8532`). Local
runtime data is fixture-oriented, so timings prove code-path behavior rather
than production-source latency or production correctness. No deploy, provider,
environment, Supabase, source-materialization, or Phase-7 action occurred.

## Outcome

The product is not four empty mockups. Each surface contains substantial real
logic, and the Report is already a strong reading experience. The main weakness
is continuity: the surfaces do not yet form one durable, typed workflow.

Three findings block calling the current end-to-end path release-ready:

| Severity | Finding | Direct evidence | Consequence |
| --- | --- | --- | --- |
| P0 | Paper never sends the bearer token required by its backend route. | `app/web/lib/paperVariants.ts:32-67` versus `app/backend/app/api/routes/paper_variants.py:37-52`; runtime POST had no `Authorization` header and returned 401. | A normal extraction ends in raw `{"detail":"Not authenticated"}` instead of candidates. |
| P0 | Batch writes every uploaded parsed variant to an orphaned plaintext snapshot. | `app/backend/app/services/batch.py:142-175,389-422`; registry expiry removes memory entries but never unlinks the snapshot, which is not read elsewhere. | Auth-bound VCF content can remain on disk indefinitely without a deletion or retention contract. |
| P0 | Workbench is horizontally clipped on mobile. | Headless Chrome at a requested 390px viewport reproduced 107px document overflow and visibly clipped the nav/tool strip/canvas. | Core tools and controls are not reliably reachable on a phone or narrow window. |

Important P1 findings are the missing full-locus selection/navigation workflow,
the hard-coded CRISPR off-target locus default, non-durable Batch jobs, lost or
resurrected client state, incomplete handoffs, blank Suspense fallbacks, and the
absence of a committed cross-surface browser/a11y ratchet.

## Status Vocabulary

The audit uses narrower labels than “real” versus “mock”:

- **Source-backed**: output is tied to an identified external or approved local
  source with provenance.
- **Computed/local**: real deterministic computation runs, but the result is not
  itself an external evidence assertion.
- **Fixture/fallback**: deterministic sample data or a degraded substitute;
  acceptable only when visibly disclosed.
- **Partial**: the implementation exists, but a broken seam, missing provider,
  missing state, or incomplete workflow prevents the promised outcome.
- **Missing**: no usable product path exists.

## Capability Inventory

| Capability | UI/runtime | Backend/data | Audit classification |
| --- | --- | --- | --- |
| Report lookup and seven-section reading flow | Loading, error, offline, unresolved, interpretation, ready, copy, TSV, rich HTML, print, lazy sections | Lookup orchestration and typed payload are implemented; the local proof mixed fixture and unavailable local assets | **Partial/source-mixed**, visually mature |
| Nearby and same-class variants | Clickable report cards in a closed-by-default rail | Derived from `locus_context.nearby_variants`; same-class is filtered again in the UI | **Partial**: useful, but duplicated lanes and frontend relationship derivation |
| Same-condition lane | Informational rows only | Uses associated-condition summaries, not related variant identities | **Partial**: the label suggests a variant handoff that does not exist |
| Curated variant distribution | 3×4 count/heat grid with query bucket | Count payload exists | **Partial**: no cell action, variant page, provenance drill-down, Batch handoff, or keyboard interaction |
| Report exports | Whole-report TSV/HTML clipboard/download and print are implemented | Export policy filters are present | **Computed/local**, usable |
| Batch import | VCF/list/paste parser, source chips, scope filters, large-file server upload | Bounded upload parsing, async lookup, paging, owner checks | **Partial/source-mixed**: engine works; persistence and retention do not |
| Batch comparison | Cohort summary and annotated table | Results include evidence/classification fields | **Partial**: cohort analysis exists, but no explicit 2–3-row side-by-side compare |
| Paper extraction | Multi-source UI, candidate merging, Report/Library/Batch actions, TSV | Authenticated extraction route, deterministic local extractor or gateway chain, bounded PDF handling | **Broken partial**: the frontend/backend auth seam makes the live UI unusable |
| Sequence window | Search/jump, tracks, range selection, sparse edits, undo/redo, history, scratchpad, primer overlay | `POST /viewer` returns typed window data; default local path is a disclosed RPE65 fixture | **Computed/partial** |
| Full genomic locus | Virtualized wrapped rows, coordinates, queried-variant focus | Full sequence + projection + feature intervals for curated stress genes; currently fixture hydration | **Fixture/partial**: read-only proof, no navigation/selection/edit bridge |
| Primer | Form and result cards; local runtime called the API successfully | Primer3 computation is implemented; optional genome specificity is provider-gated | **Computed/partial**: default RPE65 run returned no pairs; some UI metrics are illustrative fallbacks |
| CRISPR design | Guide design, off-targets, screening primers, ssODN, TIDE-style outcomes, TSV exports | Deterministic design and provider seams exist; off-target index/provider may fall back; TIDE is observed-consensus analysis | **Computed/source-mixed** with one safety blocker |
| Align | Browser-local FASTA/paste/AB1 parsing and pairwise comparison | Reference resolution is used; the general `/align` endpoint exists but the UI does not call it | **Computed/partial**, privacy-positive browser default |
| Variant library | Shared across surfaces; account sync when signed in | Owner-scoped API/repo and Supabase RLS migrations exist | **Partial**: localStorage is long-lived and union merge has no tombstones |
| Durable workflow state | Batch source preview and library survive some navigation | Jobs and most tool work are memory/session state | **Missing** as a coherent workflow contract |

## Surface Findings

### Variant Report

What works:

- The report has explicit loading, offline, generic error, malformed,
  unresolved, interpretation, and ready states.
- A 1280/1440 runtime preflight found no root overflow, console errors, missing
  report slots, or unexpected viewer fetches for the tested fixture.
- Report↔Workbench preserves the active URL query through ModePill.
- Related variant cards are keyboard-focusable and open real Report routes.
- The shared WorkRail combines Library, Related variants, section navigation,
  Ask Eamos, and account access without obscuring the reading column.
- Report export builders exclude facts denied by the product-export policy.

What does not yet work as one workflow:

- ModePill intentionally drops all variant context when switching to Paper or
  Batch. There is no explicit “find this variant in papers” or “add this variant
  to Batch” contract to replace the dropped context.
- Paper candidates can reach Report, Library, and Batch, but not a selected
  Workbench tool. Batch rows reach Report only. Library items do not expose one
  consistent action set across surfaces.
- `RelatedVariants` computes “same class” from the nearby list in the browser.
  Condition rows are not variants, and the four evidence-axis squares repeat
  the current report themes rather than evidence for each related variant.
- `CuratedVariantsGrid` is a static distribution. The underlying response has
  no paginated identity rows for a selected bucket.
- Several presentation helpers normalize free-form classification strings, and
  the educational ACMG components can recompute a verdict. Operational labels
  should consume typed backend facts; explicitly labelled what-if teaching
  tools may keep local math.
- All four top-level product pages use `Suspense fallback={null}`. A cold Batch
  navigation reproduced a blank page until compilation completed.

### Batch

What works:

- Browser parsing supports VCF, CSV/TSV-like lists, and pasted variants.
- A single client-truncated file retains its original `File` in memory and uses
  the server upload path, preserving the full cohort while the tab remains open.
- Backend upload/create/read routes require an authenticated principal and bind
  uploads/jobs to that principal.
- Lookups run asynchronously with bounded workers; the UI reports queued,
  running, completed, failed, expired, rate-limited, sign-in, and stale-scope
  states.
- Backend tests cover upload bounds, ownership, filters, paging, and lookup
  enrichment.

Gaps:

- Refresh loses the original `File`. `readCompareVariants()` deliberately
  strips `clientTruncated` metadata, so Generate can submit only the capped
  browser preview after refresh while the UI no longer knows the file was
  truncated.
- Job id, progress, results, and filters are component memory. Backend upload
  and job registries expire after one hour and disappear on process restart.
  There is no resume, cancel route, job history, or explicit delete.
- The backend emits `/lookup?query=...` in `report_href`, a route that does not
  exist in the Next.js product. The frontend ignores it and reconstructs
  `/report`, while a backend test ratifies the wrong URL.
- `collectBatchResults()` gathers all pages into the browser, and the table is
  not virtualized. The current upper path can retain/render thousands of rows.
- There is no result TSV/CSV/manifest export, no provenance bundle, and no
  explicit selected-row compare view.
- The split-pane separator is pointer-oriented and lacks a keyboard-adjustable
  separator interaction.
- Anonymous demo import is honest but waits until Generate to say sign-in is
  required; the page can preflight auth and offer a direct sign-in path.

### Paper → Variants

What works below the broken seam:

- The backend accepts bounded JSON text or validated PDF multipart input, checks
  extension/content-type/magic/size, applies deadlines, and best-effort removes
  its temporary PDF.
- The deterministic local extractor is input-dependent; the gateway path uses a
  structured extraction chain. Candidate validation is fail-closed.
- The UI distinguishes resolved clinical alleles, ambiguous protein mentions,
  experimental constructs, and unresolved mentions, then supports candidate
  review, Library save, Batch handoff, Report open, and TSV export.
- Ask Eamos receives only bounded candidate/provenance context, not the full
  paper body.

Gaps:

- `extractPaperVariants()` never requests the current session or attaches a
  bearer token, although the route always requires one. Its mock fallback only
  handles 404, 501, or network `TypeError`, so a normal 401 becomes raw JSON.
- Stale comments and the initial “Mock extraction” treatment claim the HTTP
  route is not built. The backend route is built; “mock” now conflates a real
  deterministic local extractor with a fixed frontend sample.
- `source_metadata` is always `null` on the backend response, so live title,
  author, PMID, and DOI grouping cannot match the illustrative fallback.
- Multi-source extraction is sequential and has no visible per-source retry or
  cancellation model.
- With `llm_provider=gateway`, the chain sends the full extracted publication
  text to the configured AI gateway. The UI does not disclose processing
  location, provider, retention posture, or request consent. The response
  guardrail says `patient_data: not_used` even though arbitrary publications
  and the extractor's own context lexicon can include patient/proband text.
  This is a contract and disclosure defect, not evidence of unauthorized
  exfiltration.
- No extraction workspace survives refresh, and no source can be removed from a
  completed durable run.

### Workbench

What works:

- The visible tool rail is Sequence, Primer, CRISPR, and Align. The desktop
  shell is visually coherent, with one shared Library/Ask/account rail and a
  contextual tool panel.
- Sequence window selection uses pointer capture and animation-frame throttling;
  sparse edits support substitute, insert, delete, replace, undo, and redo.
- Full-locus mode returns a continuous full genomic sequence and uses row
  virtualization with overscan. An older stability finding that described the
  current full-locus surface as entirely unvirtualized is stale.
- RPE65 full locus locally returned 21,139 bases in a 196,456-byte response in
  260ms. ABCA4 returned 128,315 bases in 851,744 bytes in 380ms. Both clearly
  disclosed deterministic fixture hydration.
- Align parses AB1 and computes pairwise comparison in the browser, keeping read
  data local by default; only reference resolution uses the backend.
- Workbench engine responses have a useful `SourceDisclosure` contract.

Gaps:

- A no-query Workbench silently opens RPE65 `c.260A>G`; it does not explain that
  a default example was selected.
- Active tool, view mode, selection, edits, notes, and results are not encoded in
  the URL or a durable workspace. Tool change or refresh loses important state.
- Full locus is explicitly an FGV-003 proof: no selection, edit, scratchpad,
  minimap, sequence search, distant jump, keyboard range extension, or tool
  consumption. Selection in the window is not a shared coordinate contract.
- Long drag has no edge autoscroll. Range handles and edit affordances remain
  mouse-centric. Global key handling can intercept browser shortcuts outside
  the viewer.
- `WorkbenchTool` and `TOOL_META` still contain a dead `compare` member even
  though `TOOL_ORDER` does not show it. Product language should make Batch the
  variant comparator and Align the sequence comparator, rather than revive an
  ambiguous fifth tool.
- Workbench “export” is mostly print, with tool-specific CRISPR TSV paths.
  Primer, Align, sequence edits, and workspace state lack consistent exports.

Tool-specific gaps:

- **Primer:** Primer3 is real local computation, but whole-genome specificity is
  gated and `avoid_snps` has no complete SNP source. The default RPE65 runtime
  returned a valid 200 with no qualifying pair. Some missing secondary-
  structure numbers are replaced by deterministic illustrative values; a
  decision surface should show `not assessed`, not pseudo-measurements.
- **CRISPR:** design and source disclosure are substantial. Off-target screening
  starts with a hard-coded chr7 locus even for the RPE65 example and merely
  warns the user to change it. A real request must require a resolved/confirmed
  on-target locus. Provider-unavailable results may be disclosed fixture
  fallbacks. TIDE is an observed-consensus difference analysis, not a full NNLS
  decomposition; its existing disclosure is directionally correct.
- **Align:** the browser implementation is real and privacy-positive, but there
  is no identifier lookup, result persistence, or export. The general backend
  `/align` route is unused by the UI, creating two nominal paths without a clear
  product rule.

## Persistence And Handoff Findings

| State | Current store | Failure mode |
| --- | --- | --- |
| Report lookup cache | `sessionStorage`, 30-minute cache | No visible cache age/refresh control; not a workflow record |
| Batch sources | `sessionStorage`; original large `File` in memory | Raw paste persists for the tab; refresh can silently downgrade a full file to a preview |
| Batch job/results | React memory + backend process memory | Lost on refresh, restart, or one-hour expiry |
| Paper sources/results | React memory | Lost on refresh; no per-source durable status |
| Workbench tool/view/selection/edits/results | React memory; rail pane preferences in `localStorage` | Scientific context is lost while chrome preference survives |
| Library | Long-lived `localStorage` plus account document | Variant identifiers remain locally until cleared; union merge has no delete tombstones, so deleted items can reappear |

The product needs a canonical workflow context, not more ad-hoc query copying.
URLs should carry only bounded public identity and view intent. Raw paper text,
VCF rows, AB1 data, edit sequences, and private notes must never be put in URLs;
durable paths should use owner-scoped opaque run/workspace ids.

## Security And Privacy Review

Positive controls:

- Local and Supabase JWT paths verify signatures and expiry with an algorithm
  allowlist; Supabase tokens also validate `aud=authenticated`, `sub`, and role.
- Variant-library backend routes derive ownership from the authenticated
  principal. Inspected migrations enable RLS, use `auth.uid()` ownership, index
  ownership joins, and reserve aggregate mutation RPCs for `service_role`.
- No service-role key use was found in browser code, and no concrete committed
  secret was established by this audit.
- Paper PDF validation and the Workbench input-size bounds are meaningful.

Required hardening:

- Validate the Supabase JWT `iss` claim against the configured project issuer;
  the current decode validates audience but not issuer. Supabase's current JWT
  guidance lists issuer, audience, expiry, signature, and required claims as
  validation inputs.
- Remove or strictly private/expire/unlink the Batch upload snapshots before
  accepting real cohorts.
- Require authentication for server-processed trace uploads (TIDE and any
  future server-side AB1 path), while keeping browser-local Align available.
- Add explicit processing/retention disclosure for Paper gateway requests,
  Batch uploads, and trace uploads. Never log source bodies or raw variant rows.
- Introduce versioned/tombstoned library sync and a visible “clear local data”
  control.

Official Supabase references used for this review:

- [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [JWT verification](https://supabase.com/docs/guides/auth/jwts)
- [JWT claims and validation](https://supabase.com/docs/guides/auth/jwt-fields)
- [Securing the Data API](https://supabase.com/docs/guides/api/securing-your-api)

## Accessibility And Responsive Audit

Scored on a 0–4 launch-readiness scale, where 4 means the tested workflow is
complete and independently ratcheted:

| Dimension | Score | Evidence |
| --- | ---: | --- |
| Visual hierarchy and clinical restraint | 3 | Strong Report and desktop Workbench composition; clear semantic colors and source notes |
| Cross-surface information architecture | 2 | Shared chrome exists, but handoffs and state identity are inconsistent |
| Keyboard accessibility | 2 | Many buttons/rails are semantic; sequence range editing and split controls are pointer-led |
| Screen-reader state clarity | 2 | Several live states use roles, but virtual sequence interaction and async source states lack one coherent announcement model |
| Responsive behavior | 2 | Report, Paper, and Batch contained in tested mobile views; Workbench overflow is a release blocker |
| Error and recovery UX | 2 | Report/Batch are broad; Paper exposes raw auth JSON; no durable resume/cancel model |
| Motion and focus management | 2 | Reduced-motion scroll is respected in viewers; tool/route changes need explicit focus restoration |
| Performance architecture | 3 | Report payload is bounded and full locus is virtualized; Batch table/all-page collection and unbudgeted workflow scripts remain |

Required accessibility acceptance includes keyboard range selection and
extension, edge autoscroll, touch-safe targets, keyboard-operable separators,
focus restoration after tool and surface changes, async live-region summaries,
an accessible alternate to a 128k-base visual grid, reduced-motion behavior,
and zero root overflow from 320px upward.

## Performance Baseline

Local fixture-mode, two-run Report audit for RPE65 `c.260A>G`:

| Path | Cold/first | Warm | Response bytes |
| --- | ---: | ---: | ---: |
| `/api/v1/lookup` | 144ms | 50ms | 119,033 |
| `/api/v1/lookup/summary` | 35ms | 39ms | 3,911 |
| `/api/v1/viewer` window | 13ms | 17ms | 6,713 |

The lookup report payload itself was approximately 94KB. These are useful
no-regression baselines, not production SLOs. Full-locus response baselines are
listed in the Workbench section. The browser audit found no root overflow for
the tested Report, Paper, or Batch mobile pages; Workbench failed.

Performance risks to ratchet:

- Batch collects and renders all result pages rather than exposing bounded
  viewport/page state.
- Paper runs multiple sources sequentially.
- Full-locus layout eagerly builds all row models, although DOM mounting is
  virtualized; ABCA4 is acceptable locally but must be measured under browser
  interaction, not only API latency.
- The performance audit's JSON mode emits entire response bodies, producing a
  very large diagnostic stream; a summary-only mode would be safer for CI.

## Verification Baseline And Gaps

Passed during this audit:

- `app/web`: 26 Vitest files, 193 tests.
- focused backend collection: 398 tests across Paper, Batch, Workbench, viewer,
  sequence context, library, Supabase migrations, and frontend contract; run
  exited green with expected skips/warnings.
- `npm run test:coordination`: 9/9.
- `app/web` boundary guard: 275 tracked files, clean.
- local Report performance/API probes and manual headless-Chrome scenarios.

The existing test suite is strong at pure models and backend APIs. It has no
committed integration tests that render `ReportClient`, `CompareClient`,
`PaperClient`, `WorkbenchClient`, `SequenceViewerV2`, `FullLocusViewer`, or
`ModePill`. There is no committed product browser/a11y suite proving auth header
attachment, handoff round trips, refresh/resume, mobile containment, keyboard
selection, source disclosure, or cancellation. The new plan makes that an
executable ratchet rather than another manual checklist.

## Decisions Carried Into The Spec

1. Keep four top-level surfaces; make their responsibilities explicit rather
   than merging them into one giant page.
2. Batch owns cohort and 2–3-variant comparison. Align owns sequence comparison.
   The dead Workbench `compare` alias is compatibility-only, not a fifth tool.
3. Use one canonical variant/workflow context and one genomic selection contract
   across Report, Batch, Paper, and Workbench.
4. Make fixture/computed/source-backed/unavailable status visible and typed;
   never replace absent measurements with plausible-looking numbers.
5. Preserve browser-local Align as the privacy-default path.
6. Persist metadata/results only with owner scope; raw uploads are ephemeral by
   default and governed by explicit retention/deletion.
7. Finish the existing full-locus contract and renderer rather than designing a
   second sequence-viewer architecture.
8. Fix release blockers before polish or provider expansion.
