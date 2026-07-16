# Eamos Roadmap

Updated 2026-07-16 15:44 +0000 · Codex.

This file records the current product sequence. Git, executable guards, the
active plan, and `agent_handoff/CURRENT.md` remain the operational ground truth.
Historical implementation ledgers stay in `PROGRESS.md` and the scoped plans.

## Product reality

| Surface | Route | Current state |
| --- | --- | --- |
| Landing | `/` | Shipped. Free-public positioning, real product examples, responsive feature gallery, safe share links, and anonymous content-free discovery telemetry are complete. |
| Search results | `/search` | Shipped. Structured results and answer paths use the active backend contract and authenticated result surface where required. |
| Variant Report | `/report` | Shipped and source-backed. Four evidence-axis cards hand directly to Clinical, followed by one coherent seven-chapter evidence record. |
| Paper | `/paper` | Shipped. Paper evidence review is a first-class product surface. |
| Batch | `/compare` | Shipped. VCF/list ingestion, panel filtering, sample flow, results, and exports are active. |
| Workbench | `/workbench` | Shipped for Sequence Viewer, Primer, CRISPR, and Alignment. Ask Eamos is mounted in the shared rail. An embedded Workbench comparator remains a product decision because Batch already owns multi-variant comparison. |
| Account and auth | `/account`, `/auth` | Shipped as supporting surfaces. There is no active pricing, checkout, upgrade, or paid-tier product surface. |
| Patient report | `/runs` | Frozen on the legacy v1 interface. Security fixes remain allowed; feature and visual work wait for a separately approved Layer 2 cycle. |

## Foundations already complete

- `app/web` is the only active frontend. The historical Vite application and
  duplicate TypeScript contract were retired.
- Eamos is universal-free at the product layer. All eleven predictor rows remain
  visible; operational availability is separate from access. Backend rows keep
  license, provenance, launch-gate, and preflight metadata for later policy.
- The Variant Report has a backend-generated four-axis summary, seven registered
  evidence sections, lazy section contracts, exports, report library, source
  currency, provenance, negative controls, and section-state handling.
- Search, Paper, Batch, and Workbench share the same variant-oriented product
  shell and backend contract.
- Ask Eamos is mounted on report and Workbench rails. Metered chat routes require
  authenticated principals and retain per-user and global caps.
- Private source/cache schemas, source readers, provenance, provider health,
  contract canaries, ownership checks, boundary guards, dependency security,
  and CI branch protection are established.
- The parallel-worktree protocol, verified-slice commit/push rule, clear-safe
  handoff, and peer-mail boundary are executable repository policy.

## Current execution order

### 1. Variant Report reading experience

Status: complete, selected and verified on 2026-07-16.

Outcome:

- Preserve the four evidence-axis cards as the only top summary display.
- Hand directly from those cards to Clinical evidence.
- Remove the backend-ranked mini-card dashboard and standalone evidence-
  fingerprint strip from the top flow. The full Eamos computation remains in
  the auditable In-silico section.
- Present Clinical, In-silico, Population, Gene and locus, Disease,
  Publications, and Trials as a coherent numbered evidence record with strong
  source hierarchy, calm disclosure controls, and complete loading, empty,
  partial, stale, and failed states.
- Verify the hierarchy on the offline negative-control fixture without changing
  backend contracts. Representative live-variant evidence auditing belongs to
  the next source-closure cycle.

Verified result:

- Structural boundary guard locks Call cards → Clinical as the top read order.
- Full repository verification, the independent frontend-contract canary, local
  Next -> FastAPI report smoke, 1024/1280/1440 desktop preflight, 1440 browser
  review, keyboard/console review, and the accessibility audit are green for
  this slice. Remaining dense-widget contrast debt is recorded in the plan and
  `PROGRESS.md`.

Active plan: `plans/variant-report-experience/plan.md`.

### 2. Report evidence and runtime closure

Status: next report cycle after the presentation slice.

Prioritize source-backed gaps visible to a curator, not another page redesign:

1. Audit representative pathogenic, benign, unresolved, and source-empty
   variants across all seven sections.
2. Close any remaining ClinGen VCEP attribution, ClinVar interpretation,
   structured ClinicalTrials.gov, gene-constraint, protein-track, or source-
   freshness gaps only where the current payload proves them missing.
3. Keep missing sources explicit. Never turn a fixture, cache fallback, or
   unavailable predictor into a clinical claim.
4. Keep the seven-section registry, lazy-fetch contract, export contract, and
   backend/frontend schema canary aligned.

Founder-gated runtime work stays separate: persistent-disk materialization,
provider or environment changes, Supabase mutations, migrations, deployment,
and large source downloads require their existing approval and preflight gates.

### 3. Workbench completeness

Status: active product, no rebuild planned.

- Keep Sequence Viewer, Primer, CRISPR, Alignment, protein context, edits, and
  tool-aware Ask Eamos on the shared product shell.
- Decide whether an embedded comparator creates value beyond `/compare`. If it
  does, define one frozen cross-surface contract and build it. If it does not,
  remove the remaining ghost `compare` metadata and CSS rather than advertising
  an unreachable tool.
- Continue source-backed runtime and browser verification for real engines;
  preserve explicit unavailable states when a local engine or asset is absent.

### 4. Release feedback loop

Status: follows a normal approved deployment of the current product state.

- Review only aggregate, anonymous discovery events. Never inspect person
  profiles, genomic query content, raw URLs, account identifiers, or session
  replay.
- Re-run route-level performance, accessibility, responsive, and browser
  verification after material UI changes.
- Use measured product behavior to select the next slice. Do not revive pricing
  or entitlement UI as a proxy for validation.

## Held and future cycles

- Layer 2 v2: redesign `/runs` only as its own approved patient-report cycle.
- Mouse mm39: reuse the human lookup architecture with a separately sourced and
  verified database stack; keep it hidden until complete.
- Large local evidence bundles and protein annotation: continue only through the
  persistent-volume, checksum, provenance, and provider-health gates.
- Multi-instance durable rate limiting and counters: required before horizontal
  backend scaling or stronger spend guarantees.
- Layer 3 remains internal and is not part of the public roadmap.

## Retired assumptions

The following statements in historical plans must not drive new work:

- The old React/Vite frontend is active or needs a second maintained contract.
- Work is divided by Claude frontend and Codex backend roles.
- The product has Free, Pro, Max, checkout, upgrade, or predictor entitlement
  surfaces.
- AlphaMissense or any other predictor is hidden from the product because of a
  commercial tier. Runtime availability and backend metadata remain honest,
  but access is universal-free.
- Ask Eamos is an unfunded orphan or the chat route is public and uncapped.
- Workbench Primer, CRISPR, and Alignment are pending mock panels.
- The repository has dozens of uncommitted May changes or uses a no-commit rule.
- The May 2026 session plan is the current execution queue.

## Release gates

Every product slice finishes at a committed and pushed verified boundary:

1. Preserve `app/backend/tests/test_boundary.py`,
   `scripts/eamos-web-boundary.mjs`, and the frontend-contract canary.
2. Run focused tests first, then the relevant frontend build and backend
   contract/integration checks.
3. Browser-check representative ready, loading, empty, partial, and failure
   states in proportion to the change.
4. Stage only owned paths. Never stage watcher-owned inboxes or unrelated work.
5. Push and watch CI. Production merge/deploy, destructive Git, cloud, provider,
   migration, source-materialization, and secret-bearing actions keep their
   separate approval gates.
