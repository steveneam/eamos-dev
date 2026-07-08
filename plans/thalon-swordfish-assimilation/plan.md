# Thalon/Swordfish → Eamos assimilation plan

Ported engineering-efficiency frameworks from **Thalon** (`E:\thalon`) and **Swordfish**
(`E:\swordfish`) into Eamos. Machine-readable plan: `plan.json` (18 milestones). Context +
measured facts: `context.json`, `exploration-notes.md`. Built via the `planner` skill
(2026-07-09), plan-design QR gate PASS.

## Scope (Steven-confirmed)

- Parallel-workflow tooling + native worktree symlinks + an adapted **contract-window** skill
- Agent-handoff leanness (Thalon's ~45-line CURRENT.md shape vs Eamos's 483)
- CI/repo safety hardening + ops safety nets
- A single metered LLM gateway choke point
- **Full graphify removal**, replaced by executable structural ratchet tests as the cross-code
  wiring tracker
- **No AI attribution** in GitHub (follow Thalon: `attribution:{commit:"",pr:""}`)

Out of scope: turbo/nx monorepo conversion; VPS self-host (Swordfish Bucket-6, separate); the
full eval-as-CI-gate harness (deferred).

## Load-bearing principle — every gate ships in 3 moves, never 1

1. **Measure** — run the gate report-only, count existing violations.
2. **Conform** — debug/refactor/lint the existing repo to zero, sized from the measured count.
3. **Enforce** — flip to blocking in CI + pre-commit only once green.

Never flip a blocking gate onto a non-conforming repo. Encoded as `depends_on` fields.

## Fixed ordering (the hard constraint)

All graphify decommission (M-014/15/16/18) **depends on M-013** — i.e. the structural boundary
ratchets must be green **and CI-enforced** before any graphify artifact/rule/doc is removed.
Enforcement (M-013) depends on the conform pass (M-017) + the handoff reshape (M-012).

## Milestones by wave

**Wave 1 — Foundation (parallel, additive/report-only, reversible):**
- M-001 Backend dev-dependency surface for lint tooling (`requirements-dev.txt`, `pyproject.toml`)
- M-002 Backend structural boundary ratchet (`app/backend/tests/test_boundary.py`)
- M-003 Web structural boundary guard (`scripts/eamos-web-boundary.mjs`)
- M-004 Repo grep-guard: secrets/PHI + conflict markers (`scripts/eamos-grep-guard.mjs`)
- M-005 Handoff-lint hardening (`scripts/eamos-handoff-lint.mjs`)
- M-006 Single metered LLM gateway choke point (`ai_gateway/choke.py` + call-site routing)
- M-007 Worktree tooling (`scripts/eamos-worktree-setup.ps1`, `scripts/guard-worktree-install.mjs`)
- M-008 Contract-window skill (`.claude/skills/contract-window/SKILL.md`)
- M-009 Renovate action-pinning config (`renovate.json`)
- M-011 Package-manifest wiring (`preinstall` guard in the 3 package.json)

**Wave 2 — Conform + handoff reshape:**
- M-017 Backend+web CONFORM pass — ruff/black to zero + `next build` clean (no enforce yet)
      [dep: M-001, M-002, M-006]
- M-012 Agent-handoff leanness — reshape `CURRENT.md` to the lean form; ledgers→`PROGRESS.md`;
      drop stale `WORKTREE_INVENTORY.md`

**Wave 3 — Local enforce:**
- M-010 Pre-commit hook wiring (installer + hook body) [dep: M-012]

**Wave 4/5 — CI enforce:**
- M-013 CI hardening + 3-move gate enforcement — SHA-pin actions, least-priv perms, zizmor,
      flip ruff/black + prod-build + grep-guard + handoff-lint to blocking [dep: M-017, M-012]

**Wave 6/7 — Graphify decommission (all gated on M-013):**
- M-014 config + worktree `symlinkDirectories` + no-attribution settings (`.claude/settings.json`,
      `.codex/hooks.json`) [dep: M-013]
- M-015 governance docs + parallel/contract conventions (`CLAUDE.md`, `AGENTS.md`, `CODEX.md`,
      `.claude/CLAUDE.md`, memory) [dep: M-013]
- M-016 artifact deletion (`graphify-out/` ~510 MB, `.graphifyignore`, `.claude/skills/graphify/`,
      `.agents/skills/graphify/`) [dep: M-013]
- M-018 live-doc reference scrub + repo-wide `git grep -i graphify` completeness sweep across the
      28 living docs; acceptance = grep returns only dated tombstones [dep: M-013,14,15,16]

## Memory/ratchet lessons folded in (from `~/.claude/projects/E--thalon|E--swordfish/memory/`)

Windows/PowerShell: pure-ASCII `.ps1` (PS 5.1), `pwsh`-absent fallback (`& script.ps1`), delete
worktrees via `cmd rmdir /s /q` (not PS `Remove-Item -Recurse`), never `npm install` in a worktree,
`git commit -F`/`--body-file` for multi-line, CRLF-safe scanners. Parallel: lead-drives-lanes,
per-launch approval, Mode-B "vscode method", dead-lane salvage, net-positive-speedups. Swordfish:
`claude-md-hardlink` (recreate+hash-verify if CLAUDE≡AGENTS hardlinked), `ps51-secret-transport`.

## Irreversible / high-consequence milestones (review before running)

- **M-016** deletes `graphify-out/` (~510 MB) — permanent (recoverable only from git history if
  ever committed; it's large + likely gitignored).
- **M-013** flips CI gates to blocking — every subsequent PR must pass ruff/black/prod-build.
- **M-014** no-attribution config — going-forward only; existing history keeps its trailers
  (retroactive scrub = destructive force-push, explicitly out of scope, see R-010).
