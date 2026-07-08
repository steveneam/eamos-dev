# CI Guard — commit-time guard gate

Eamos ships a small set of **tracked** guard scripts that run at commit time (via
the pre-commit hook) and in CI. Unlike the upstream portfolio's brand-cleanliness
guard, Eamos is the private product repo, so the invariant here is **not** about
hiding a name — it is about keeping two hazards out of the tracked tree:

1. **secret-shaped tokens** — `Bearer <token>`, `sk-…`, `vck_…` (24+ high-entropy chars);
2. **merge-conflict markers** — `<<<<<<<`, `=======`, `>>>>>>>` at line start.

## The check

`scripts/eamos-grep-guard.mjs` runs a `git grep` for those two hazard shapes over
**git-tracked files only** and:

- prints every offending `path:line`, if any;
- exits **0** when there are zero hits (clean);
- exits **1** when there is at least one hit (fails the commit / build);
- exits **2** on a git error.

Run it locally any time:

```bash
node scripts/eamos-grep-guard.mjs          # scan tracked files
node scripts/eamos-grep-guard.mjs --json   # machine output
```

## The gate

The tracked pre-commit hook `scripts/hooks/pre-commit` chains three guards, each
**gating the commit on its non-zero exit**:

1. `eamos-vercel-project-guard --require-root-link` — keep the repo-root `.vercel`
   linked to `eamos-dev`, and no stray `app/web/.vercel` (always).
2. `eamos-grep-guard` — the secret + conflict-marker scan above (always).
3. `eamos-handoff-lint --strict` — the handoff anti-bloat lint, but only when
   `agent_handoff/CURRENT.md` is staged.

Install the hook (idempotent; run automatically by the root `npm install` once the
`prepare` script is wired):

```bash
node scripts/install-hooks.mjs
```

It sets `core.hooksPath=scripts/hooks` so every clone and worktree runs this one
committed hook, and retires any superseded copy in `.git/hooks`. The same guards
are wired into `ci.yml` as blocking checks by the CI-enforcement milestone
(M-013), so a hazard that slips a local hook is still caught on the PR.

## Why the exit code is the contract

Each guard is checked with an explicit `if ! guard; then exit 1; fi`. The hook
never chains a guard and the commit in a form that could swallow a non-zero exit
(the semicolon-chain trap that once let a guarded token through upstream because
the guard ran but its exit code never gated the commit). A failing guard **always**
aborts the commit.

## Why tracked-files-only is correct

CI only ever sees **committed** files, so grepping the tracked set is the true
guarantee that the *shipped* repo is clean. Working-tree scratch, gitignored
`.context/`, and local `.env` files are correctly out of scope.

The secret prefixes and the 7-character conflict markers are **assembled from
fragments at runtime** inside `scripts/eamos-grep-guard.mjs` (and referred to only
obliquely in this document), so the guard, this file, and the rest of the tracked
tree never contain the literal patterns and therefore never trip their own check —
the guard can scan itself and pass, with no path excluded from the grep.

## What this does NOT do

This is the commit-time hazard gate only. It is intentionally **not** the full CI
pipeline (typecheck, lint, tests, build, boundary ratchets) — those live in
`ci.yml` and `app/backend/tests/test_boundary.py`. And it is deliberately **not** a
brand-name check: Eamos is the private product repo and names itself freely.
