# Integrated Product Workflow Delivery Plan

Status: active; Lane A integrated and verified on `main` as `6d2f6c9` through
Steven's one-time manual CI substitute. B/C have not launched.

Plan stamped: 2026-07-19 09:48 +0000 · Codex lead.

## Outcome And Authority

This plan turns the evidence in [`research.md`](research.md) and the approved
contract in [`spec.md`](spec.md) into one verified product slice. It connects
Variant Report, Paper, Batch/Compare, and Workbench without weakening source
truth, privacy, accessibility, or the existing structural ratchets.

The delivery authority is:

1. `spec.md` for product behavior and the approved V1 contract;
2. this file for dependencies, lane ownership, gates, and merge order;
3. `COORDINATION.md` for live worktree state after launch;
4. the repository's executable boundary and frontend-contract guards for
   cross-code wiring.

Steven approved the V1 contract, five-lane partition, and Lane B's local
migration-file authoring on 2026-07-19. That approval authorizes Lane A to launch
on the next `gogogo`; it does not pre-approve a lane merge or an unspecified
remote mutation. A lane never applies migrations. The Codex lead owns the
serialized post-merge Supabase checkpoint under the repository's Task F
runbook, including an exact mutation approval card immediately before the
named remote action.

## Delivery Graph

The sprint uses Mode B because it spans persistent backend state, upload/privacy
boundaries, two complex frontend surfaces, and a committed browser ratchet.

```text
Lane A: freeze code contract
  ├──> Lane B: backend + persistence ──> B merge ──> Task F apply ──┐
  └──> Lane C: surface flow (parallel work) ────────────────────────┤
                                                                   v
                                              C merge ──> Lane D ──> Lane E
```

Only B and C run concurrently. There is one web writer in each wave: C in the
first implementation wave, D in the second. Merge order is strictly
**A → B → Task F apply → C → D → E**; Task F is a serialized lead checkpoint,
not a sixth lane or merge. Codex is the sprint lead and sole merger. Every
merge waits for Steven's explicit approval and green required CI; the current
GitHub Actions minute lock may delay merges but does not lower the gate.

## Contract Freeze

Steven's 2026-07-19 approval freezes these `spec.md` elements before Lane A starts:

- `CanonicalVariantRefV1`;
- `WorkflowContextV1`;
- `SelectionRangeV1` and its GRCh38, 1-based, closed coordinate rule;
- `ProcessingDisclosureV1`;
- `WorkflowRunV1` and `WorkflowArtifactV1`;
- `RelatedVariantGroupV1` and `CuratedVariantPageV1`;
- the URL/handoff grammar;
- the shared async state machine;
- Batch as the variant comparator and Align as the sequence comparator.

Lane A expresses that contract in Pydantic and TypeScript, adds serialization
canaries, and lands before any implementation lane forks. Later lanes consume
it without editing its owned files. If implementation proves the contract
wrong or incomplete, the affected lane stops and proposes a versioned contract
amendment; it does not drift a schema, duplicate a type, or add an unreviewed
field. The lead then replans ownership and ordering before work resumes.

## Release-Blocking Order

These fixes are P0 and must be demonstrated before feature-completeness work is
called release-ready:

1. Paper attaches the authenticated bearer token and presents a safe,
   recoverable auth/error state.
2. Batch no longer leaves orphaned plaintext upload snapshots; expiry, cancel,
   and deletion have executable cleanup tests.
3. Workbench has no document-level overflow or clipped primary controls at
   320px and 390px.

Lanes may complete adjacent work while a P0 is under review, but Lane E cannot
pass and no final release claim can be made until all three regressions are
committed.

## Lane Partition

`COORDINATION.md` row edits are the sole shared-file exception. A lane edits
only its own row. `agent_handoff/CURRENT.md`, this plan package, and all other
shared governance files remain lead-owned.

| Lane | Branch | Starts after | Owned surface | Exit |
| --- | --- | --- | --- | --- |
| A — Contract V1 | `agent/product/contract-v1` | Next `gogogo`; recovery sample first if due | Shared schemas, TypeScript contract, contract canaries | V1 types serialize identically and existing contract tests pass |
| B — Workflow backend | `agent/product/workflow-backend` | A merged | Auth, lifecycle, persistence, cleanup, related/curated APIs, Workbench service safety | Backend P0s and owner/retention/API tests pass |
| C — Surface flow | `agent/product/surface-flow` | A merged; parallel with B | Report, Paper, Batch/Compare, Library, shared navigation | Paper P0 and cross-surface handoffs pass in the active Next.js app |
| D — Workbench canvas | `agent/product/workbench-canvas` | B and C merged | Sequence/locus viewer and Primer/CRISPR/Align UI | Mobile P0, selection/tool binding, and exports pass |
| E — Workflow ratchets | `agent/product/workflow-ratchets` | D merged | Browser/a11y/performance scripts, CI wiring, verification receipt | Integrated browser and structural gate is committed and green |

Lane C may work while Lane B is in flight, but it is not merged until Lane B is
merged and the Task F `eamos-dev` checkpoint has completed successfully.

### Lane A — Contract V1

Owned paths:

```text
app/backend/app/schemas/__init__.py
app/backend/app/schemas/workflow.py                         # new
app/backend/app/schemas/batch.py
app/backend/app/schemas/paper_variants.py
app/backend/app/schemas/gene_viewer.py
app/backend/app/schemas/workbench.py
app/backend/app/schemas/report.py
app/backend/app/schemas/variant_library.py
app/web/lib/backend.ts
app/backend/tests/test_frontend_contract.py
app/backend/tests/test_product_workflow_contract.py         # new
```

Tasks:

- Encode every frozen V1 shape with strict enums, UTC timestamps, bounded
  strings/collections, opaque ids, and explicit nullable fields.
- Reuse existing source-disclosure types rather than create a competing model.
- Add canonical URL builders/serialized href fields to the contract without
  changing route behavior in this lane.
- Make coordinate/build/orientation semantics explicit and reject ambiguous
  interval input.
- Add cross-language canaries for required fields, enum parity, casing, null
  behavior, and JSON examples covering Batch, Paper, locus selection, and
  artifacts.
- Preserve backward-readable fields where needed; any compatibility shim must
  be marked for removal and tested.

Required verification:

```bash
app/backend/.venv/bin/pytest -q \
  app/backend/tests/test_product_workflow_contract.py \
  app/backend/tests/test_frontend_contract.py \
  app/backend/tests/test_batch_panel_schemas.py
npm --prefix app/web test
npm --prefix app/web run typecheck
node scripts/eamos-web-boundary.mjs
app/backend/.venv/bin/pytest -q app/backend/tests/test_boundary.py
```

### Lane B — Workflow Backend

Owned paths:

```text
app/backend/app/core/deps.py
app/backend/app/core/config.py
app/backend/app/main.py
app/backend/app/api/routes/batch.py
app/backend/app/api/routes/paper_variants.py
app/backend/app/api/routes/gene_viewer.py
app/backend/app/api/routes/workbench.py
app/backend/app/api/routes/variant_library.py
app/backend/app/api/routes/lookup.py
app/backend/app/repos/__init__.py
app/backend/app/repos/product_workflow_repo.py                  # new
app/backend/app/repos/variant_library_repo.py
app/backend/app/services/batch.py
app/backend/app/services/paper_variants.py
app/backend/app/services/workflow.py
app/backend/app/services/variant_library.py
app/backend/app/services/gene_viewer.py
app/backend/app/services/gene_viewer_*.py
app/backend/app/services/lookup_service.py
app/backend/app/services/lookup_service_report_payload.py
app/backend/app/services/lookup_service_clinvar_distribution.py
app/backend/app/services/lookup_service_utils.py
app/backend/app/services/variant_report_orchestrator.py
app/backend/app/services/workbench_design*.py
app/backend/app/services/crispr_*.py
app/backend/app/services/trace_*.py
app/backend/tests/test_auth_guard.py
app/backend/tests/test_batch_api.py
app/backend/tests/test_gene_viewer.py
app/backend/tests/test_paper_variants.py
app/backend/tests/test_product_workflow_api.py                 # new
app/backend/tests/test_sequence_context.py
app/backend/tests/test_sequence_window_model.py
app/backend/tests/test_lookup_service_report_payload.py
app/backend/tests/test_variant_report_orchestration.py
app/backend/tests/test_variant_library_api.py
app/backend/tests/test_variant_library_supabase.py
app/backend/tests/test_workbench_api.py
app/backend/tests/test_supabase_migrations.py
supabase/migrations/20260719*_product_workflow_runs.sql      # local authoring approved
```

No schema file is owned here. If a route cannot be implemented with Lane A's
contract, stop and request a contract re-plan. The migration prefix above has
one owner and Steven approved its local authoring on 2026-07-19. The lane never
links a project, applies a migration, invokes a Supabase MCP mutation, or
changes remote data; the lead owns the post-merge checkpoint below.

Tasks, in order:

1. Remove the Batch snapshot leak. Prefer parsing within request lifetime and
   retaining normalized result metadata only. If a spool is unavoidable, use
   restrictive permissions, an owner-bound opaque path, TTL cleanup, startup
   scavenging, and cancel/delete cleanup.
2. Add owner-scoped run lifecycle operations: create/read/list/page/cancel/delete
   for Batch and Paper, plus Workbench workspace metadata/artifacts. Raw VCF,
   PDF/text, trace, notes, and edited sequence remain absent by default.
3. Correct Batch `report_href` to the canonical `/report?...` grammar and add
   bounded export/page behavior.
4. Return backend-derived related-variant groups and paginated curated-variant
   buckets. Do not infer clinical relationships from frontend text.
5. Populate honest Paper source metadata/disclosures, support bounded
   concurrency/cancel/retry/partial completion, and keep temporary PDF cleanup
   fail-safe.
6. Validate Supabase JWT `iss` against configured project issuer in addition to
   the existing signature, algorithm, expiry, audience, role, and subject
   checks. Keep service-role credentials server-only.
7. Add Library v2 tombstones and deterministic merge semantics so deletion
   cannot resurrect an older local item.
8. Return the complete source-backed genomic locus for every supported resolved
   gene/transcript, including all exons, intervening introns, and UTRs. The
   queried variant supplies initial focus only. A cropped window or fixture-only
   locus fails release acceptance; unavailable source data fails closed with a
   typed state.
9. Bind locus selection and design services to build, reference basis, edit
   revision, and context digest. Reject an unresolved or unrelated CRISPR
   off-target locus and require auth for server-side trace processing.

Security and persistence acceptance:

- Cross-account and forged-owner reads, pages, cancels, deletes, and artifact
  downloads fail closed.
- RLS is enabled on every exposed durable table, policies use verified
  `(select auth.uid())`, owner columns are indexed, and service-role-only paths
  are never exposed through a client token.
- Delete/expiry removes rows, artifacts, and any ephemeral spool; restart tests
  prove stale spools cannot become immortal.
- Redirect/return paths are same-origin allowlisted; raw input and tokens do not
  appear in logs, URLs, filenames, errors, or exported provenance.
- Migration lint/security tests are local in the lane. Remote application is a
  required lead-run checkpoint after merge, with the exact mutation separately
  confirmed under Task F.

Required verification:

```bash
app/backend/.venv/bin/pytest -q \
  app/backend/tests/test_auth_guard.py \
  app/backend/tests/test_batch_api.py \
  app/backend/tests/test_gene_viewer.py \
  app/backend/tests/test_paper_variants.py \
  app/backend/tests/test_product_workflow_api.py \
  app/backend/tests/test_sequence_context.py \
  app/backend/tests/test_sequence_window_model.py \
  app/backend/tests/test_lookup_service_report_payload.py \
  app/backend/tests/test_variant_report_orchestration.py \
  app/backend/tests/test_variant_library_api.py \
  app/backend/tests/test_variant_library_supabase.py \
  app/backend/tests/test_workbench_api.py \
  app/backend/tests/test_supabase_migrations.py
app/backend/.venv/bin/pytest -q app/backend/tests/test_frontend_contract.py
app/backend/.venv/bin/pytest -q app/backend/tests/test_boundary.py
```

### Lead Checkpoint — Apply The Supabase Migration

This is not a sixth lane. It is a serialized lead operation after Lane B is
approved, merged, and verified on `main`, and before persistence is called
complete or Lane C is merged. Follow
`docs/architecture-consistency-gate/task-f-supabase-production-readiness-runbook.md`.

The lead must:

1. Re-check the current Supabase changelog and discover the installed official
   CLI command shape with `--help`; use the repository's official CLI → REST →
   MCP → Steven-dashboard escalation order.
2. Verify project `eamos-dev` / `cpdjxsgasaesysvxkpmi`, environment `dev`, the
   current remote migration ledger, exposed schemas, and backup/rollback owner.
3. Reconcile known local/remote migration-name drift and the previously reported
   missing `20260614195800_user_library_document.sql` before ordering the new
   workflow migration. Do not blindly push every local file.
4. Review the exact pending SQL, affected tables/policies/indexes/grants, Data
   API exposure, rollback SQL, and secrets-redaction plan. Run the local reset,
   migration tests, RLS tests, and a dry-run/list operation supported by the
   current CLI.
5. Present Task F's filled mutation approval template to Steven. Only after that
   exact confirmation, apply the reviewed missing migration set once from the
   lead/operator environment, never from a lane worktree.
6. Verify migration history, table/policy/grant/index state, two-user isolation,
   create/read/list/page/cancel/delete/expiry behavior, raw-input absence, and
   backend service-role access without browser service-role exposure.
7. Run Supabase security and performance advisors plus bounded smoke queries,
   resolve or disposition every finding, then update
   `docs/db/supabase-inventory.md` with a sanitized application receipt.

Application to an unnamed production project, direct Dashboard schema editing,
environment/provider flips, deploys, and seed/source writes remain outside this
checkpoint. A failed preflight or ledger mismatch stops the apply and returns to
review; it is never repaired speculatively.

### Lane C — Report, Paper, Batch, And Shared Flow

Owned paths:

```text
app/web/app/report/**
app/web/app/paper/**
app/web/app/compare/**
app/web/components/layout/**
app/web/components/auth/**
app/web/components/report/**
app/web/components/paper/**
app/web/components/compare/**
app/web/components/library/**
app/web/lib/batch.ts
app/web/lib/batch-summary.ts
app/web/lib/compare-filters.ts
app/web/lib/library-sync.ts
app/web/lib/paperVariants.ts
app/web/lib/report-*.ts
app/web/lib/variant-file.ts
app/web/lib/variant-format.ts
app/web/lib/variant-library.ts
app/web/lib/variant-search.ts
app/web/lib/work-rail-collapse.ts
```

`app/web/lib/backend.ts`, `app/web/lib/api.ts`, Workbench paths, global CSS,
and unrelated report data fixtures are excluded. Consume Lane A's types; do not
fork or shadow them.

Tasks, in order:

1. Fix Paper auth before extraction: obtain the current session token, preflight
   missing/expired auth, preserve staged input through sign-in, normalize safe
   errors, and prove no raw backend JSON reaches the page.
2. Replace mock/live ambiguity with processing/source badges. Require explicit
   consent before an external gateway receives publication text; show provider,
   input class, persistence, retention, and cancellation posture.
3. Implement bounded per-source Paper states, cancellation, retry, partial
   completion, durable-run resume, source removal, and resolved-candidate
   handoffs to Report, Workbench, Library, and Batch.
4. Preflight Batch auth, preserve staged inputs safely, and make a refreshed
   truncated upload require full-file reattachment. Never submit the preview as
   a complete cohort.
5. Resume/page/cancel/delete Batch runs; virtualize or server-page large tables;
   add keyboard-operable split panes, filters, export/manifest, row actions, and
   a 2–3-row comparison view.
6. Make Report related and curated variants typed, deduplicated, actionable,
   keyboard-operable, and backend-derived. Add explicit Paper/Batch/Primer/
   CRISPR/Align handoffs while preserving the report reading hierarchy.
7. Give Library items the same canonical action set everywhere and implement
   local v1→v2/tombstone/clear behavior without cross-account cache mixing.
8. Replace null Suspense fallbacks with stable, surface-specific shells and
   keep loading, empty, partial, stale, expired, auth, consent, offline, and
   safe-error states visually distinct.

Required verification:

```bash
npm --prefix app/web test
npm --prefix app/web run typecheck
npm --prefix app/web run lint
npm --prefix app/web run build
node scripts/eamos-web-boundary.mjs
```

The lane also records browser evidence at 320, 390, 768, 1024, 1280, and 1440
for its owned surfaces, keyboard-only paths, reduced motion, slow loading,
offline/failure states, and the two authenticated P0 workflows. Evidence stays
local until Lane E defines the committed artifact contract.

### Lane D — Workbench Canvas And Tools

Owned paths:

```text
app/web/app/workbench/**
app/web/components/workbench/**
app/web/lib/api.ts
app/web/lib/workbench/**
```

Tasks, in order:

1. Remove root overflow and clipped controls at 320px and 390px; preserve a
   coherent tool/navigation model across touch, tablet, and desktop.
2. Turn the existing virtualized full-locus surface into the single whole-gene
   navigator. It spans the resolved gene bounds with every exon, intervening
   intron, and UTR; the queried variant is only the initial scroll target. Add a
   minimap/viewport, genomic and transcript orientation, feature and coordinate
   search, distant jump, transcript choice, and window↔locus continuity. Do not
   build a second viewer or satisfy this with a wider variant-centred window.
3. Implement the same selection model in window and locus modes: pointer/touch
   drag, edge autoscroll, Shift+click, Shift+Arrow, keyboard endpoints,
   coordinate entry, Escape clear, accessible summary, and stable virtualized
   focus.
4. Apply sparse edit revisions with undo/redo in both views and propagate
   `SelectionRangeV1`, sequence basis, revision, and context digest to tools.
   Context changes retain but visibly stale old results.
5. Deep-link safe tool/view/context identity and persist explicit workspace
   state. Never place raw sequence, trace, edits, or notes in the URL.
6. Primer: accept an exact selection anywhere in the complete locus, including a
   distant exon, intron, or UTR. Show only measured facts; label unavailable
   specificity/SNP/structure checks `not assessed`; explain empty results; add
   precise overlay, TSV, FASTA, and manifest.
7. CRISPR: derive and require confirmation of the canonical on-target locus,
   disable unresolved off-target requests, preserve provider/fallback truth,
   bind guide/donor/outcome results to revision, and export the complete bundle.
8. Align: retain browser-local FASTA/AB1 as the disclosed default, support
   canonical/identifier reference input, persist results in the workspace, and
   export alignment plus manifest.
9. Remove the visible/dead fifth-tool ambiguity: legacy `tool=compare` redirects
   to Batch with notice; Batch compares variants and Align compares sequences.
10. Explain the RPE65 default example and finish keyboard, focus, touch target,
    screen-reader, reduced-motion, loading, empty, unavailable, stale, error,
    and cancellation states.

Required verification:

```bash
npm --prefix app/web test
npm --prefix app/web run typecheck
npm --prefix app/web run lint
npm --prefix app/web run build
node scripts/eamos-web-boundary.mjs
```

Browser acceptance additionally proves no document overflow or clipped primary
control at all required widths, no ordinary select/scroll input task over
100ms, at least 50fps on the verification host, and equivalent keyboard/pointer
selection coordinates in both viewer modes. The required end-to-end proof opens
a variant in one exon, jumps to a distant exon in the same gene, selects and
edits there, submits that exact selection to Primer, returns to the original
variant, and confirms that the continuous locus was never cropped or replaced.

### Lane E — Integrated Workflow Ratchets

Owned paths:

```text
scripts/eamos-product-workflow-*.mjs                       # new
docs/product-workflow-verification/**                     # new
.github/workflows/ci.yml
package.json
```

This lane edits no product implementation. It converts the agreed verification
into durable guards and fails when the product regresses.

Tasks:

- Add a committed CDP/browser runner for Report→Workbench, Report→Paper,
  Paper→Report/Batch/Workbench, Batch row/selection handoffs, Library actions,
  refresh/resume/delete, distant-exon navigation/editing, and Workbench
  selection→Primer/CRISPR/Align.
- Cover 320/390/768/1024/desktop layouts, document overflow, clipped controls,
  keyboard-only paths, focus restoration, ARIA separator behavior, reduced
  motion, async live regions, and fixture/fallback disclosure.
- Add privacy assertions for URLs, browser storage, console/network error text,
  exports, and cancel/delete cleanup. Test identities are synthetic and no raw
  patient/publication/cohort material is committed.
- Encode `spec.md` performance budgets in a summary-only CI mode so fixture
  payload timing/output cannot flood logs.
- Invoke, never replace, `test_boundary.py`, `eamos-web-boundary.mjs`, the
  frontend-contract canary, and the existing full verify.
- Commit a concise verification protocol and expected evidence locations; do
  not commit screenshots containing tokens or user inputs.

Required verification:

```bash
npm run test:coordination
npm run verify
npm run verify:product-workflow
git diff --check
```

The exact new root script name is `verify:product-workflow`; the implementation
may split internal scripts, but that public gate is frozen for this sprint.

## Merge Protocol

### Lane A one-time manual gate exception

Added: 2026-07-19 10:51 +0000 · Codex.

Steven explicitly approved manual verification and direct commit/push for Lane
A after GitHub-hosted jobs failed without executing any steps. For Lane A only,
the lead may replace required hosted CI with the complete local-equivalent gate,
push the exact verified commit to a no-PR branch for a fresh Vercel preview, and
then promote that commit to current `main` with CI skipped. The receipt records
any unavailable local environment check rather than claiming it passed.

All downstream dependency order, Task F, cloud/deploy/provider/source holds, and
later-lane gates remain unchanged. The zero-step Actions run remains failed; it
is not converted into success evidence.

Receipt: `6d2f6c9` passed the runnable local substitute, fresh preview and
production Vercel builds, and current-main contract/web/structural smokes.
Actions did not run; PR #15 was closed as superseded. Docker was unavailable on
the verification host, and the pre-push local Next build was blocked by Google
Fonts network timeouts; neither limitation is represented as a passing check.

For every lane, the lane agent:

1. reads repository and nested instructions before editing;
2. stays inside the owned paths and the approved contract;
3. runs its focused gates and inspects `git diff --check`;
4. stages only owned paths, commits without AI attribution, and pushes;
5. opens or updates a PR, marks only its `COORDINATION.md` row `review`, and
   hands the lead `{branch, PR number, files changed, isolation notes, test
   evidence, remaining risks}`;
6. never merges its own PR.

The Codex lead then, one lane at a time:

1. confirms the handoff and audits scope with
   `git log --name-only origin/main..origin/<lane-branch>`;
2. checks for one-file/one-owner violations and contract drift;
3. rebases onto the latest `origin/main`, reruns lane and structural gates, and
   publishes a fresh review branch if publishing the rebase would otherwise
   require a force-push;
4. creates/updates the PR and watches required CI;
5. presents evidence and asks Steven for explicit merge approval;
6. merges only on green, verifies `main`, updates coordination, then releases
   the next dependency wave.

Neither lane nor lead force-pushes. Conflicts outside a lane's own
`COORDINATION.md` row are partition leaks and trigger review/re-plan. GitHub's
known zero-minute Actions lock means a lane may reach committed/pushed/review
state while merge remains held; it is never treated as green CI.

## Exact Launch Commands

Approval is recorded. On the next `gogogo`, launch A alone. Launch B and C only
after A is reviewed, explicitly approved, merged, and verified on `main`.
Launch D only after B and C merge. Launch E only after D merges.

### Wave 0 — Lane A

```bash
cd /home/deploy/work/eamos
git fetch origin
git worktree add .claude/worktrees/product-contract-v1 -b agent/product/contract-v1 origin/main
cd .claude/worktrees/product-contract-v1
python3 -m venv app/backend/.venv
app/backend/.venv/bin/pip install -r app/backend/requirements.txt
npm --prefix app/web ci
codex
```

### Wave 1 — Lanes B And C In Separate Terminals

Lane B:

```bash
cd /home/deploy/work/eamos
git fetch origin
git worktree add .claude/worktrees/product-workflow-backend -b agent/product/workflow-backend origin/main
cd .claude/worktrees/product-workflow-backend
python3 -m venv app/backend/.venv
app/backend/.venv/bin/pip install -r app/backend/requirements.txt
codex
```

Lane C:

```bash
cd /home/deploy/work/eamos
git fetch origin
git worktree add .claude/worktrees/product-surface-flow -b agent/product/surface-flow origin/main
cd .claude/worktrees/product-surface-flow
npm --prefix app/web ci
codex
```

### Wave 2 — Lane D

```bash
cd /home/deploy/work/eamos
git fetch origin
git worktree add .claude/worktrees/product-workbench-canvas -b agent/product/workbench-canvas origin/main
cd .claude/worktrees/product-workbench-canvas
npm --prefix app/web ci
codex
```

### Wave 3 — Lane E

```bash
cd /home/deploy/work/eamos
git fetch origin
git worktree add .claude/worktrees/product-workflow-ratchets -b agent/product/workflow-ratchets origin/main
cd .claude/worktrees/product-workflow-ratchets
python3 -m venv app/backend/.venv
app/backend/.venv/bin/pip install -r app/backend/requirements.txt
npm --prefix app/web ci
codex
```

`claude` may replace the final `codex` command for any lane; ownership is
agent-agnostic. Steven chooses the available agent, but the branch, path,
contract, and handoff obligations do not change.

## Exact Lane Kickoff Prompts

Paste the matching prompt after the agent starts.

### Lane A Prompt

```text
You own Lane A (Contract V1) on agent/product/contract-v1. Read AGENTS.md, nested instructions, COORDINATION.md, agent_handoff/README.md, and plans/product-workflow-integration/{research,spec,plan}.md completely. Implement only the frozen V1 Pydantic/TypeScript shapes and contract canaries in Lane A's exact owned paths. Do not change runtime behavior, cloud state, Supabase, deploys, providers, source assets, Phase 7, or any out-of-glob file except your own COORDINATION row. If the frozen contract is insufficient, stop and hand the lead a proposed amendment; do not drift it. Run every Lane A gate plus diff-check, stage only owned paths, commit/push with no AI attribution, open/update the PR, mark your row review, and hand Codex lead {branch, PR number, files, isolation, tests, risks}. Never merge.
```

### Lane B Prompt

```text
You own Lane B (Workflow Backend) on agent/product/workflow-backend. Read AGENTS.md, nested instructions, COORDINATION.md, agent_handoff/README.md, and plans/product-workflow-integration/{research,spec,plan}.md completely. Confirm Lane A is present in your base, then implement Lane B in its exact owned paths, prioritizing Batch snapshot cleanup, owner-scoped run lifecycle, canonical report/related/curated APIs, honest Paper processing, JWT issuer validation, Library tombstones, and Workbench/CRISPR/trace safety. Consume Lane A schemas without editing them. Steven approved authoring and locally testing the allocated Supabase migration. Never link or mutate a remote project from the lane; after merge, the Codex lead performs the canonical Task F application checkpoint. No deploy/provider/source/Phase-7 action and no out-of-glob edit except your own COORDINATION row. Run all Lane B/security/boundary gates and diff-check, stage only owned paths, commit/push without AI attribution, open/update the PR, mark review, and hand Codex lead {branch, PR number, files, isolation, tests, risks}. Never merge.
```

### Lane C Prompt

```text
You own Lane C (Report, Paper, Batch, and shared flow) on agent/product/surface-flow. Read AGENTS.md, nested instructions, COORDINATION.md, agent_handoff/README.md, the Impeccable skill, and plans/product-workflow-integration/{research,spec,plan}.md completely. Confirm Lane A is in your base. Work only in Lane C's exact globs. Fix Paper bearer/auth/error/disclosure first, then complete Paper/Batch durable states and handoffs, actionable related/curated Report variants, Library v2 behavior, explicit cross-surface actions, honest states, and responsive/accessibility polish. Consume backend.ts; do not edit it, api.ts, Workbench, global CSS, cloud/provider/source/Phase-7 state, or out-of-glob files except your own COORDINATION row. Run all Lane C tests/build/boundary/browser checks and diff-check, stage only owned paths, commit/push without AI attribution, open/update the PR, mark review, and hand Codex lead {branch, PR number, files, isolation, tests, browser evidence, risks}. Never merge.
```

### Lane D Prompt

```text
You own Lane D (Workbench Canvas and Tools) on agent/product/workbench-canvas. Read AGENTS.md, nested instructions, COORDINATION.md, agent_handoff/README.md, the Impeccable skill, and plans/product-workflow-integration/{research,spec,plan}.md completely. Confirm Lanes B and C are in your base. Work only in Lane D's exact globs. Fix 320/390 overflow first; extend the existing virtualized viewer into one continuous whole-gene navigation/selection/edit model across every exon, intervening intron, and UTR, with the queried variant as initial focus rather than crop boundary; prove a distant-exon selection/edit can feed Primer; bind exact context/revision to Primer, CRISPR, and Align; remove illustrative decision facts and hard-coded locus behavior; add durable/deep-linked safe state and complete exports/accessibility. Do not fork another viewer or edit backend.ts, shared layout, global CSS, backend, cloud/provider/source/Phase-7 state, or out-of-glob files except your own COORDINATION row. Run all Lane D tests/build/boundary/browser/performance checks and diff-check, stage only owned paths, commit/push without AI attribution, open/update the PR, mark review, and hand Codex lead {branch, PR number, files, isolation, tests, browser evidence, risks}. Never merge.
```

### Lane E Prompt

```text
You own Lane E (Integrated Workflow Ratchets) on agent/product/workflow-ratchets. Read AGENTS.md, nested instructions, COORDINATION.md, agent_handoff/README.md, and plans/product-workflow-integration/{research,spec,plan}.md completely. Confirm Lanes A-D are in your base. Edit only Lane E's exact paths and your own COORDINATION row. Add the summary-only committed CDP/browser, accessibility, privacy, handoff, deletion, and performance ratchets plus root/CI wiring; invoke the existing boundary and frontend-contract guards rather than weakening or duplicating them. Do not edit product code, cloud/provider/source/Phase-7 state, or apply migrations. Run npm run verify, verify:product-workflow, coordination, and diff-check; stage only owned paths, commit/push without AI attribution, open/update the PR, mark review, and hand Codex lead {branch, PR number, files, isolation, tests, evidence, risks}. Never merge.
```

## Final Serialized Gate

After E is merged and before calling the slice complete, the lead runs from a
clean, current `main`:

```bash
git status --short --branch
npm run test:coordination
npm run verify
npm run verify:product-workflow
git diff --check
```

The lead also verifies every `spec.md` Definition of Done item, records the
required-CI URLs and browser/performance receipt, confirms no raw upload remains
after expiry/delete, confirms no attribution footer/trailer exists, and checks
that Render rollback, provider configuration, sources, and Phase 7 are
unchanged. Supabase must match the sanitized post-Task-F inventory exactly,
with no mutation beyond the approved `eamos-dev` migration set.

## Bounded Exclusions

This sprint does not include pricing or account-role gates, live provider
activation, production source acquisition/materialization, a production deploy,
database migrations outside the serialized Task F application of the reviewed
workflow migration to named dev project `eamos-dev`, Phase 7, final
regulated-ELN claims, clinical decision automation, or arbitrary
chromosome-scale/DMD-scale expansion. Any other target or migration requires
its own contract and approval. Predictor integration remains backend-wide when
Steven says “admin”; no commercial label may defer or hide predictor wiring,
and license/provenance/launch-gate metadata remains intact.

## Approval Receipt And Remaining Gates

Steven approved the V1 contract, five-lane ownership/merge order, and Lane B's
local migration authoring on 2026-07-19. The next `gogogo` starts Lane A only.
Every later wave still waits for its dependency merge, every merge waits for a
separate Steven approval, and the lead presents Task F's exact mutation card
before applying the reviewed migration to `eamos-dev`.
