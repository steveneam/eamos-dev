# Parallel-agent retrofit — prep, validation, and field lessons (Eamos)

> Eamos adopted the Forj parallel-agent protocol on **2026-07-03**. The *operational*
> protocol is canonical elsewhere — this doc is the **retrofit record + field-validated
> lessons** for future Eamos sessions and for other repos (Selom, the Forj vault) adopting
> it. It does not restate the protocol.
>
> - Live lane board + Eamos adaptation: `COORDINATION.md` (repo root)
> - Standing rules: `AGENTS.md` → "Parallel-agent workflow"
> - Protocol source (read-only vault): `Forj/bones/parallel-agents.md` +
>   `Forj/Wiki/reference/parallel-agent-workflow.md`

## What shipped (PR #1 → `main` a9dd456)

- `.gitignore` → `.claude/worktrees/`; `.worktreeinclude` (boot config only); `COORDINATION.md`;
  `AGENTS.md` two standing rules.
- CI merge gate `.github/workflows/ci.yml`: **web** (lint + vercel guard) / **frontend** (lint +
  vitest) / **backend** (pytest).
- Branch protection on `main`: admin-bypass (`enforce_admins:false`), `strict:true`, 3 required
  checks, no required review, force-push/delete blocked.

## Prep & validation (the process, before writing anything)

1. Read both vault pages end-to-end; mapped every checklist item to actual repo state.
2. Audited parallel-readiness — found **none** of the plumbing present: no `.claude/worktrees/`
   ignore, no `.worktreeinclude`, no `COORDINATION.md`, `AGENTS.md` missing the rules, **no
   `.github/` at all**, and `main` unprotected.
3. Verified the Vercel prebuild guard (`scripts/eamos-vercel-project-guard.mjs`) **no-ops in a
   fresh worktree** — a missing root `.vercel/project.json` degrades to a *note* (not an error)
   without `--require-root-link`, so `npm run dev` in a worktree isn't blocked.
4. Confirmed dev isolation is free: local dev runs on a local seam (SQLite / `LLM_PROVIDER=mock`),
   so each worktree gets its own DB; only dev ports need offsetting (Next :3000 / Vite :5173).
5. Confirmed lockfiles exist (so CI uses `npm ci`), backend `requires-python>=3.10`, `render.yaml`
   tracked; `gh` had `repo`+`workflow` scopes (branch-protection API + workflow push).
6. Dogfooded the gate via PR #1 (the repo's first-ever PR): iterated CI to green, merged, *then*
   enabled protection — **green-before-protect**.

## Field-validated lessons (candidates to feed back to the vault)

1. **"Confirm the merge gate exists" understates it for a no-CI repo.** For Eamos the gate had to
   be *built from scratch*; that is the *bulk* of the retrofit, not a checkbox. Inert plumbing is
   ~15 min; CI + branch protection is the real work.
2. **The first CI run is a latent-debt audit.** A brand-new gate on a repo that never had CI
   immediately surfaced 3 pre-existing bugs on `main` (an eslint error; a Playwright spec vitest
   was wrongly globbing; a stale Vite↔Next `gnomad` v3/v4 mirror). Budget a "green the gate" pass;
   don't assume `main` is green just because it ships.
3. **Green-before-protect, always.** Enabling a required check before the gate is green blocks the
   very PR that greens it. Sequence: build CI → PR → iterate green → merge → protect.
4. **Separate deterministic tests from asset/integration tests in CI.** Two backend tests need
   gitignored data assets a clean runner can't provide. Handled with `--deselect` in the workflow
   (self-contained, in-lane) plus a follow-up to make them `skipif`-asset-absent. Don't let
   asset-bound tests redden a logic gate.
5. **`.worktreeinclude` carries *boot* config, not *deploy authority*.** We deliberately EXCLUDED
   `.render-deploy-hook` so a lane worktree can't deploy shared prod. The vault example ("copy
   `.env`, secrets config") should add: include what a worktree needs to *run*; exclude anything
   that *deploys or mutates shared infra*.
6. **Verify prebuild/predev guards no-op in a fresh checkout.** A guard that hard-fails on absent
   gitignored state (e.g. `.vercel`) would block worktree dev. Make guard-tolerance a retrofit check.
7. **Merge model: one lead = sole merger.** Sharpened the vault's "lead sequences merges" into:
   exactly one lead per sprint *presses merge* for ALL lanes; lane agents push + mark their
   `COORDINATION.md` row `review` + hand off, never self-merging. **Lane ownership (who edits a
   glob) ≠ merge authority (the lead).** Removes the "two agents both think they're clear" race.
8. **Observable-state coordination needs no live channel.** The lead sequences merges from the
   git-tracked ledger + `gh pr checks` + branches alone — Claude and Codex (separate runtimes)
   never need a live link. Confirmed sufficient.
9. **Admin-bypass fits a solo / 2-agent repo.** `enforce_admins:false` keeps the existing
   direct-push cadence for routine commits; only `agent/*` lane branches go through PR+CI. A full
   PR-for-everyone gate would end a working direct-push rhythm for no benefit at this scale.
10. **No dedicated orchestrator at 2-agent / 3–5-lane scale.** The lead can also own a lane; a
    standalone orchestrator only earns its cost past ~5 lanes.

## Cost model — one-time vs recurring

- **One-time (paid this session):** reading the protocol, building CI, greening latent debt,
  protocol decisions.
- **Recurring per sprint:** propose partition → human approves → parallel lane work (CI
  self-checks each lane in the background) → human approves merges → done. Wall-clock ≈ the
  slowest lane, not the sum. CI ≈ 5 min cold, ≈ 1–2 min warm-cached, and never blocks the human.

## Dogfood status (be precise)

- **Merge gate + PR flow:** dogfooded via PR #1 (built → CI-iterated → merged → protected). ✅
- **Multi-lane worktree flow:** designed (3 disjoint FE pillars, driven solo via worktree
  subagents — "Mode A"), **pending partition approval** — not yet run at time of writing.

## Follow-ups

- **Codex (backend lane):** make the two `--deselect`ed tests `skipif`-asset-absent, then drop the
  deselect lines from `.github/workflows/ci.yml`.
- Re-check warm-cache CI timing after a few runs; consider making `backend` a soft (non-required)
  check if `pip install` proves flaky.
