## Repository ratchets and attribution

Executable structural guards are the cross-code wiring source of truth. Keep
`app/backend/tests/test_boundary.py`, `scripts/eamos-web-boundary.mjs`, and the
frontend-contract canary green when changing boundaries or package structure.

Commits and PRs carry no AI attribution: no `Co-Authored-By` trailers and no
"Generated with" footer. The tracked `.claude/settings.json` attribution block
is the harness-side enforcement; strip any attribution that still appears
before merge.

## Parallel-agent workflow

Eamos is parallel-ready (Forj protocol). Live board + Eamos adaptation: `COORDINATION.md`.
Protocol (read-only vault): `Forj/bones/parallel-agents.md` + `Forj/Wiki/reference/parallel-agent-workflow.md`.
Ratchet policy: `docs/parallel-agents/ratchet-philosophy.md`.

**Ownership is agent-agnostic (Steven, 2026-07-08).** Any agent (Claude or Codex) can own any
file, any lane, full-stack — frontend, backend, data/pipeline, docs, tests, tooling — and may
audit/fix the other agent's historical work, dependencies, and branches. There is no fixed
Claude=frontend / Codex=backend wall; Steven picks the active agent by availability + usage
limits. Lanes below assign a *glob to a worktree*, never a discipline to an agent. Full rule +
handoff hygiene: `agent_handoff/README.md` Hard Rule 3.

Two standing rules:

1. **Propose & launch lanes.** When upcoming work has ≥2 dependency-independent buckets that
   meet at one freezable contract, proactively propose a parallel-worktree sprint — name the
   lanes, owned globs (one file → one owner), the frozen contract, and merge order — and hand
   Steven exact copy-paste launch commands. He approves the partition and runs them; he never
   designs the setup. 3–5 lanes max; run coupled work sequentially.
2. **Lead-run merges, human-approved.** Each sprint has one **lead** (the proposing agent) — the
   sole merger. Lane agents push their branch + mark their `COORDINATION.md` row `review` + hand
   off; they never merge their own branch. The lead runs the serialized gate one lane at a time in
   merge-order (rebase onto latest `main` → CI green → review → merge), pausing for Steven's
   explicit approval before each merge. Never merge on red. Lane ownership (who edits a glob) is
   separate from merge authority (the lead).

Guidance:
- Use Mode A for small, quick, disjoint work where one lead can comfortably run
  worktree-subagent lanes. Use Mode B for larger work where lanes need independent
  runtime context, longer verification, backend/cloud caution, or more than about
  three lanes. This is guidance, not a hard threshold.
- Treat contract-window/schema work as the serial first lane, then fork
  dependency-ordered waves. Allow only one web writer per wave; any additive
  out-of-glob edit must be enumerated in the approved lane contract.
- Each lane/subagent launch needs fresh per-session Steven approval covering the
  named runs. Mode B is preferred for larger work; inspect and salvage a dead
  lane's worktree before replacing it.
- The lead owns review, rebase, PR creation, CI watch, merge, and post-merge
  verification end-to-end. Take cheap provably non-breaking speedups in-run,
  without trading correctness or widening the approved scope.
- Freeze the shared contract before lanes fork. A lane needing to edit the frozen
  contract means re-plan, not ad-hoc drift.
- Review lane scope before merge (`git log --name-only main..lane`); conflicts
  outside `COORDINATION.md` are partition leaks.

End every session clear-safe — update `agent_handoff/CURRENT.md` + hand Steven a stamped
resume prompt (protocol: `agent_handoff/README.md`).

## Verified-slice git completion

Normal user-directed work ends at a verified, committed, pushed boundary without asking Steven
to repeat a commit/push approval. This standing approval is agent-agnostic and matches Thalon and
Swordfish: inspect `git status`, stage only the acting agent's explicit owned paths, commit without
AI attribution, push the branch, open/update the PR when the branch workflow applies, and watch CI.
Pause for the existing explicit approval before merge. This does not authorize destructive Git,
cleanup deletion, secret output, env/provider changes, deploy hooks, Supabase mutations, source
materialization, or other cloud actions; those retain their own gates.

## backend predictor wiring

When Steven says "admin" for predictor work, interpret it as: Steven/backend gets all predictors wired now. Do not add account-role/auth plumbing for this. Do not postpone backend predictor integration because of commercial, launch, or licensing labels. Preserve license/provenance/launch-gate metadata on rows and health/preflight output so commercialization filtering can be decided later.
