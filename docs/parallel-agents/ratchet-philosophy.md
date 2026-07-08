# Eamos ratchet philosophy

Status: active guidance.
Created: 2026-07-04 by Codex.
Sources: Thalon Sprint 0 production field report, Eamos Mode-A dogfood, and
Steven's 2026-07-03 ratchet guidance.

## Principle

Every expensive lesson becomes a durable artifact in the same change. A lesson
that lives only in chat will be rediscovered, and agent sessions have no durable
memory of why the lesson mattered.

Use one home per lesson and link to it. Do not copy the same protocol paragraph
into every handoff, plan, and README.

## Strength ladder

Promote each ratchet as high as it reasonably goes:

1. Executable: tests, CI checks, database constraints, transactions, preflight
   commands, structure guards.
2. Structural: seams, schemas, typed contracts, package boundaries.
3. Configuration: tracked settings, guarded workflow config.
4. Documentary: protocol rules, runbooks, handoff notes.
5. Memory/chat: acceptable only as raw incident context before it is ratcheted.

Default to executable ratchets where the failure mode can be detected cheaply.
If the ratchet is only read, schedule a fire drill that executes the documented
command exactly as written.

## Invariant vs opinion

Tag ratchets mentally as invariant or opinion.

Invariant ratchets protect safety, tenancy, provenance, deploy authority, source
materialization posture, and no-ungated-output behavior. They are one-way unless
Steven explicitly changes the product risk posture.

Opinion ratchets encode current preferences such as file-size budgets, workflow
thresholds, and tool choices. They should be revisited during re-charter and
pruned when stale. Do not let opinion ratchets accumulate permanent tax because
they once helped a single sprint.

## Eamos invariant ratchets

- Search request paths do not download, seed, sync, materialize, or scan raw
  source assets.
- Source/provider/runtime mutations, Supabase changes, deploy hook use, env
  flips, and large cleanup deletions are explicit Steven-approved actions.
- Private search rows stay owner-filtered; raw private report text is not
  exposed outside owner-scoped hits.
- Backend/frontend contracts are frozen before parallel lanes fork.
- Exactly one lane owns `supabase/migrations/**` in any sprint.
- Render production deploy stays main-only and lead/Codex-owned; lane worktrees
  do not carry deploy authority.
- Lane merges go through the lead-run gate and Steven approves each merge.

## Eamos executable ratchet backlog

- Make the two asset-bound backend CI tests self-skip when required assets are
  absent, then remove the CI `--deselect` pins.
- Add `tsc --noEmit -p tsconfig.json` to the `web` CI job so the merge gate is
  at least as strict as Vercel's deploy typecheck.
- Add or preserve focused search tests for owner filtering, public result
  metadata, disabled answer behavior, and grounded citations.
- Keep structure/contract guards in `app/backend/tests/test_structure_guard.py`
  and `app/backend/tests/test_frontend_contract.py` as executable protocol, not
  memory.

## Fire drills

At release or handoff checkpoints, run documented commands verbatim for the
active ratchets rather than only their underlying scripts. A broken documented
command is a doc with false confidence.

Suggested first drills:

- CI command set from `.github/workflows/ci.yml`.
- Search backfill dry-run command from `docs/search-index/plan.md`.
- Handoff lint command if the current session touches handoff docs.
- Graphify AST update command from `AGENTS.md`.
- **Vault MCP reachability** — `node scripts/eamos-vault-mcp-preflight.mjs`
  (Claude, 2026-07-08). Run it after wiring the `obsidian-vault` MCP, and on the
  first launch on a new machine (migration), instead of launching an agent host
  and guessing why the `mcp__obsidian-vault__*` tools are missing. It reproduces
  the MCP host's Node-TLS connection path (honoring `NODE_EXTRA_CA_CERTS`,
  without the `curl -k` shortcut that hides cert-trust failures) and prints the
  exact 3-condition fix on red. Promotes the vault-MCP setup lesson from a
  runbook note (documentary rung) to an executable check.
