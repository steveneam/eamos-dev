# Current Agent State

> ## ▶ BOOT: Steven types **`gogogo`** — that IS the whole resume prompt.
>
> **Agent, on `gogogo` (or any greeting with no task): do this, unprompted.**
> He cannot copy text out of the terminal, and he may be sending it from a
> Telegram topic on his phone. Read, in order, then act:
> 1. this whole file (Resume Prompt → Pointer → Delta → Next Action)
> 2. `CLAUDE.md` + `agent_handoff/README.md` (protocol) and your memory
> 3. `git log --oneline -8` and `git status` — trust the repo, not the stamp
>
> Then state the Next Action in one sentence, say what you are starting, and
> start it. Do not ask “shall I?” — the Next Action is the standing approval.
> Stop only at a founder gate (spend, irreversible action, or anything the
> protocol names a founder decision).
>
> _Boot block added 2026-07-13 at the founder's direction. Keep it at the top
> when overwriting this file._

> **Live state only — overwrite the whole file each wrap.** History belongs in
> Git, `PROGRESS.md`, and the agents' rolling logs. Protocol →
> `agent_handoff/README.md`; risks → `docs/operations/risks-and-guardrails.md`;
> worktree truth → `git status --short --branch`.

## Active Status

- **Claude:** STOPPED @ 2026-07-15 10:55 UTC — no active lane.
- **Codex:** COMPLETE @ 2026-07-16 07:28 UTC — PR #14 is merged, local `main`
  matches `origin/main`, and the post-merge boundary is verified.

## Log Edit-Lock

RELEASED: 2026-07-16 07:29 +0000 · Codex (PR #14 post-merge boundary clear-safe)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-16 07:28 +0000 · Codex report folds merged
Read CURRENT.md, agent_handoff/README.md, then inspect git log/status and the structure plan.
PR #14 rebase-merged at fe85bc5; local main and origin/main match.
ReportGeneViewer, PopulationFrequencySection, and ReportClient retain stable public contracts
while adapter/controller/model/rendering responsibilities now live in focused modules.
Full verify, audit, protein regression, browser QA, CI, and Vercel passed; post-merge guards
and 13 focused tests also pass. FROM-SWORDFISH.md is watcher-owned and remains dirty.
Next, perform a read-only audit of the next approved non-gated structure-plan hotspot and
freeze a bounded contract before edits; keep schema/provider/cloud/materialization/deploy gated.
Safe to clear: yes — PR #14 is merged, main is synced, and the verified boundary is durable.
```

## Pointer

- PR: #14, `refactor(web): split report rendering responsibilities`, merged
  2026-07-16 07:26 UTC by rebase.
- Main commits: `e932d3d` gene-viewer fold, `2a20031` review handoff, and
  `fe85bc5` population/report-shell fold.
- CI: run `29479731408`; all repository jobs passed. Vercel preview is Ready.
- Post-merge: `HEAD == origin/main == fe85bc5`; root guard passed and focused
  gene-viewer/population/report-client Vitest passed 13/13.
- Worktree: only `agent_handoff/FROM-SWORDFISH.md` is modified; it is
  watcher-owned and was not staged, committed, or altered by this lane.

## Delta

- `ReportGeneViewer.tsx` fell from 2,487 to 845 lines,
  `PopulationFrequencySection.tsx` from 1,580 to 326, and `ReportClient.tsx`
  from 1,770 to 148 while their exported component contracts stayed stable.
- Snapshot adaptation, request/state control, population modeling/readouts/map,
  load states, section primitives, and body/protein rendering now have focused
  owners, structural budgets, and model/controller regression tests.
- Existing report fixture visuals, copy, controls, exports, provenance, and
  backend contract shapes remain unchanged; no provider/cloud/schema/deploy
  action was taken.

## Next Action

- Start with a read-only audit of the next already-approved, non-gated hotspot
  in `docs/repo-structure/plan.md`. Freeze its public contract and propose the
  smallest serial slice before editing; do not sweep the watcher-owned handoff
  change or cross any schema/provider/cloud/materialization/deploy gate.
