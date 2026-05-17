# Worktree Inventory

Snapshot taken 2026-05-17 for cross-agent orientation.

Purpose: help Claude Code and direct Codex understand the intentionally dirty
worktree without treating it as accidental churn.

## Summary

- Branch: `master`
- Committed state: none of the current work is committed.
- Tracked modified files: 55.
- Untracked files/directories: agent handoff files, backend variant-search/auth
  additions, frontend Workbench v2 additions.
- This inventory is descriptive only. Do not use it as permission to reset,
  stash, delete, or clean anything.

## New Agent Coordination Files

Created by direct Codex in this session:

- `AGENT_HANDOFF.md`
- `agent_handoff/README.md`
- `agent_handoff/CURRENT.md`
- `agent_handoff/TASKS.md`
- `agent_handoff/DECISIONS.md`
- `agent_handoff/RISKS.md`
- `agent_handoff/WORKTREE_INVENTORY.md`

These files are safe for either agent to read. Updates should be limited to
actual handoff state changes.

## Backend Modified Files

Tracked backend files with modifications:

- `app/backend/README.md`
- `app/backend/app/api/routes/lookup.py`
- `app/backend/app/api/routes/reports.py`
- `app/backend/app/api/routes/reviews.py`
- `app/backend/app/api/routes/runs.py`
- `app/backend/app/api/routes/search.py`
- `app/backend/app/core/config.py`
- `app/backend/app/core/db.py`
- `app/backend/app/core/deps.py`
- `app/backend/app/fixtures/lookup_v2_modules.json`
- `app/backend/app/fixtures/tools/CLAUDE.md`
- `app/backend/app/fixtures/workbench/align_rpe65.json`
- `app/backend/app/fixtures/workbench/crispr_rpe65.json`
- `app/backend/app/fixtures/workbench/primer_rpe65.json`
- `app/backend/app/main.py`
- `app/backend/app/schemas/run.py`
- `app/backend/app/services/lookup_service.py`
- `app/backend/app/tools/CLAUDE.md`
- `app/backend/app/tools/base.py`
- `app/backend/app/tools/pubmed.py`
- `app/backend/app/tools/registry.py`
- `app/backend/app/tools/spliceai.py`
- `app/backend/tests/conftest.py`
- `app/backend/tests/test_docker_integration.py`
- `app/backend/tests/test_frontend_contract.py`
- `app/backend/tests/test_real_agent_smoke.py`
- `app/backend/tests/test_report_api.py`
- `app/backend/tests/test_review_api.py`
- `app/backend/tests/test_run_chat_api.py`
- `app/backend/tests/test_run_flow.py`
- `app/backend/tests/test_search_api.py`

Untracked backend additions:

- `app/backend/app/fixtures/tools/litvar2_fixtures.json`
- `app/backend/app/fixtures/tools/variant_validator_fixtures.json`
- `app/backend/app/repos/variant_cache_repo.py`
- `app/backend/app/tools/litvar2.py`
- `app/backend/app/tools/variant_validator.py`
- `app/backend/tests/test_auth_guard.py`
- `app/backend/tests/test_lookup_normalize.py`
- `app/backend/tests/test_tool_invariants.py`
- `app/backend/tests/test_variant_cache.py`
- `app/backend/tests/test_variant_search_integration.py`

Interpretation from existing docs: these files belong to the variant-search
engine, auth hardening, backend invariant fixes, cache work, and contract tests.
Direct Codex can own future scoped backend work here, but should not alter this
batch without a specific task.

## Frontend Modified Files

Tracked frontend files with modifications:

- `app/frontend/package-lock.json`
- `app/frontend/package.json`
- `app/frontend/src/App.tsx`
- `app/frontend/src/components/report/AcmgCriteriaFold.tsx`
- `app/frontend/src/components/report/AssociatedConditions.tsx`
- `app/frontend/src/components/report/CuratedVariantsGrid.tsx`
- `app/frontend/src/components/report/InSilicoGrid.tsx`
- `app/frontend/src/components/report/LocusContext.tsx`
- `app/frontend/src/components/report/PublicationsCallout.tsx`
- `app/frontend/src/lib/api.ts`
- `app/frontend/src/lib/backend.ts`
- `app/frontend/src/lib/sample-report.ts`
- `app/frontend/src/lib/variant-format.ts`
- `app/frontend/src/pages/ReportPage.tsx`

Untracked frontend additions:

- `app/frontend/src/components/workbench/`
- `app/frontend/src/lib/variant-format.test.ts`
- `app/frontend/src/lib/workbench/`
- `app/frontend/src/pages/WorkbenchPage.tsx`
- `app/frontend/src/styles/`

Interpretation from existing docs: these files belong to Report v2 contract
sync/search robustness and Workbench FE-4/FE-5/FE-5.5. Claude Code is the likely
owner for FE-5.6 and future Workbench UI work.

## Shared Docs And Plans Modified

Tracked shared files with modifications:

- `.claude/settings.json`
- `.claude/settings.local.json`
- `CHANGELOG.md`
- `CLAUDE.md`
- `PROGRESS.md`
- `README.md`
- `ROADMAP.md`
- `plans/frontend-rebuild.md`
- `plans/v2-backend.md`
- `plans/v2-frontend.md`

Guardrail: avoid editing these while another agent is mid-task. Update them at
task boundaries only when project state actually changes.

## Verification Recorded In Existing Docs

Existing docs record:

- Frontend FE-5.5: `npx vitest run` 24/24, `npm run build` clean.
- Backend hardening Session 2: offline pytest 86 passed / 4 skipped.
- Frontend contract: 40/40.
- `test_tool_invariants.py`: 5 passed.
- FE-5.5 browser pixel-check found planned FE-5.6 refinements; implementation
  is still pending.

## Low-Shock Work Still Safe Tonight

Safe:

- read-only audits
- handoff-folder updates
- task scoping
- reviewing docs for stale assumptions
- preparing prompts for tomorrow

Not safe without user approval:

- touching app backend/frontend code
- running broad formatters
- changing shared project docs beyond handoff protocol
- committing, stashing, resetting, cleaning
- starting FE-6/FE-7/FE-8 or M-002 work

