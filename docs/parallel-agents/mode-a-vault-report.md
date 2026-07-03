# Field report — "Mode A" parallel-agent run (for the Forj vault)

**Audience:** maintainers of the Forj parallel-agent protocol
(`bones/parallel-agents.md` + `Wiki/reference/parallel-agent-workflow.md`).
**From:** the Eamos project, first real multi-lane run, 2026-07-03.
**Status:** proof-of-concept — succeeded end-to-end. This is field feedback to fold
back into the protocol; nothing here needs to be taken on faith, the run is reproduced
in the appendix.

This report is self-contained; it does not assume Eamos context.

---

## TL;DR

We ran the protocol for real with a **launch model the playbook doesn't yet document**:
a single **lead agent spawned each lane as an isolated-worktree subagent** and drove the
whole sprint itself — the human only **approved the partition** and **approved each merge**.
No human ran a per-lane terminal. We call this **"Mode A"** (solo lead, worktree-subagent
lanes) as distinct from the playbook's **"Mode B"** (one human-run terminal/agent per lane).

Three disjoint lanes → three `agent/*` PRs → the CI merge gate → a lead-run serialized
merge → production. **First-try green on all three, zero conflicts.** The machinery works.
Five generalizable lessons below; the two highest-value are the **strict-mode rebase tax**
and the **gate ⊆ deploy-checks trap**.

---

## The headline: Mode A is a viable launch model — document it

The playbook's launch step hands the human copy-paste `git worktree add …` commands and
assumes **one terminal (and often one human-driven agent) per lane**. That's the right model
at scale. But for a **solo operator with a capable lead agent**, we validated a lighter path:

- The lead **spawns each lane as a subagent in its own git worktree** (isolation is the
  harness's job, not the human's).
- Each lane subagent: creates its owned file(s), commits on its `agent/*` branch, **pushes,
  opens its PR**, and **returns a small structured handoff** (branch, PR #, files touched,
  isolation confirmation) to the lead.
- The lead runs the **serialized merge gate** exactly as the protocol specifies (sole merger,
  human-approved per merge).
- The human's entire involvement: **approve the partition once, approve each merge.**

**Why document it:** it removes the per-lane-terminal setup cost for solo operators and makes
the "propose → approve → fan-out → gate" loop runnable by one person + one lead. **Trade-off
to state in the doc:** the lead's context spawns and tracks every lane, so Mode A suits the
protocol's existing **3–5 disjoint lanes** ceiling; past that, Mode B (independent agents/
humans per lane) scales better because no single context has to hold all lanes.

**Suggested vault edit:** add "Mode A vs Mode B" as an explicit launch-model choice in the
playbook, with the 3–5-lane heuristic as the switch-over point.

---

## What held (keep these — confirmed under real load)

1. **Observable-state coordination needs no live channel.** The lead sequenced everything from
   the git-tracked lane board + `gh pr checks` + branch state alone. No live link between
   agents was needed. (Confirms the protocol's existing claim.)
2. **Lead = sole merger, lane-ownership ≠ merge-authority.** Lanes pushed + handed off; only the
   lead pressed merge; the human approved each. No "both agents think they're clear" race.
3. **Structured lane handoffs make the gate trivial.** Because each lane returned
   `{branch, PR#, files-touched, isolation-confirmed}`, the lead's gate was mechanical. Worth
   making the handoff shape a protocol convention.
4. **Front-loaded specs → first-try green.** Each lane got explicit "match these conventions"
   pointers **and an explicit lint-gotcha list** (e.g. the framework's "no unescaped entities in
   JSX" rule). All three passed CI on the first run. Cheap upfront specificity beat CI-catch-and-fix.

---

## What we learned (fold these in)

### 1. `strict` branch protection charges a serial rebase tax on every lane after the first
With GitHub's *"require branches to be up to date before merging"* (strict mode) ON, the moment
lane 1 merges, lanes 2..N go stale and **each needs a rebase + a full fresh CI run** before it
can merge — **even for zero-conflict, glob-disjoint lanes**. Real merge-path cost ≈ **(N−1)
sequential CI cycles**, not N instant merges.

- **Generalizes:** any strict-protected trunk + serialized merges.
- **Do NOT** admin-bypass it — that skips the very gate you're validating.
- **Suggested guidance:** name this cost in the playbook so sprints size it in; offer the choice:
  keep strict (honest, serial), *or* for provably-disjoint lanes use a lead-run "rebase-all-onto-
  head, then fast-merge" pass, *or* run non-strict + rely on the lead's pre-merge rebase-and-verify.

### 2. A merge gate that runs a *subset* of the deploy's checks is a trap
Our CI gate **linted** the frontend but did **not typecheck** it; the production deploy
(`next build`) typechecks **even unimported files**. So a type error could **pass the gate and
break the deploy**. We bridged it with a lead-run local typecheck preflight and filed a "add the
typecheck to CI" follow-up.

- **Generalizes past any specific stack:** *the merge gate's checks must be a superset of (or
  equal to) the deploy's checks.* If the deploy validates something the gate doesn't, green ≠ safe.
- **Suggested vault edit:** add a retrofit checklist item — "enumerate what the deploy validates;
  ensure the gate runs at least that set."

### 3. Worktree lifecycle leaves litter the lead must sweep
Subagents/agents that **commit** leave their worktree **and** local branch behind (not auto-cleaned
once "changed"), and `gh pr merge --delete-branch` **can't delete a local branch still held by a
worktree** (noisy but harmless error).

- **Lead cleanup step:** after collecting PRs, `git worktree remove --force <lane>` + delete
  leftover local `agent/*` branches. Remote-branch deletion is unaffected.
- **Guardrail:** **never sweep another agent's worktree** (we left a second agent's worktree
  untouched). Add both to the protocol's lead-cleanup checklist.

### 4. Dogfood-task selection: "disjoint + low-risk" validates the machinery, but pick "disjoint + *needed*" if you want the output to ship
We deliberately chose 3 disjoint, low-risk components to exercise isolation cleanly — and it
worked perfectly for **validating the machinery**. But at integration, **2 of the 3 turned out
redundant** with UI the app already had (existing empty-state / loading handling), so they shipped
as **inert reusable components**, not wired in. Only the one that filled a **real gap** (an error
boundary the app genuinely lacked) integrated and shipped.

- **Meta-lesson for the playbook:** separate two goals. If the sprint's goal is *validate the
  machinery*, disjoint+low-risk is ideal. If the goal is *ship useful output*, pick lanes that are
  disjoint **and** each fill a real, non-redundant gap — verify the integration point exists
  **before** partitioning, not after.

### 5. Inert-until-integrated is a feature for de-risking fan-out
All three lanes merged to trunk **unimported** (dead code, tree-shaken) — so the fan-out and the
merges carried **zero production risk**, and integration became a separate, single-owner step with
its own review. Worth recommending as a pattern: **land new units inert, integrate in a second
single-owner pass.** It cleanly separates "did the parallel machinery work" from "is the product
change correct."

---

## Suggested vault edits (checklist form)

- [ ] Document **Mode A vs Mode B** launch models + the 3–5-lane switch-over heuristic.
- [ ] Standardize the **lane→lead handoff shape**: `{branch, PR#, files-touched, isolation-confirmed}`.
- [ ] Add the **strict-mode rebase-tax** note + the three mitigation options.
- [ ] Add a retrofit check: **gate checks ⊇ deploy checks**.
- [ ] Add lead-cleanup steps: **sweep own worktrees + local branches; never touch others'.**
- [ ] Add task-selection guidance: **disjoint + needed** (verify integration point pre-partition).
- [ ] Recommend the **land-inert, integrate-second-pass** pattern for de-risked fan-out.

---

## Appendix — the actual run (for reproducibility)

- **Partition:** 3 disjoint NEW frontend components, one owned file each, no shared globs. Contract
  was trivially FE-only (no shared types), so the "freeze the contract first" step was a no-op — a
  clean case for parallelization.
- **Lanes:** `agent/popfreq-empty-state`, `agent/geneviewer-errorboundary`,
  `agent/insilico-placeholder-rows` — each built by an `isolation:worktree` subagent.
- **Gate:** 3 PRs, 3 required checks each (2 frontend jobs + 1 backend), all **first-try green**;
  Vercel preview per PR.
- **Merge:** lead-run serialized rebase→verify→**human-approved**→merge, in order; linear history.
- **Result:** merged to trunk + production deploy **green**; one of three integrated (the error
  boundary), two left inert as reusable components (see lesson 4).
- **Wall-clock shape:** lane work ran concurrently (≈ slowest lane, not the sum); the dominant
  *serial* cost was the strict-mode CI re-runs on the merge path (lesson 1).
