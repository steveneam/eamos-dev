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
- **Codex:** PAUSED @ 2026-07-16 06:48 UTC — PR #14 is reviewed and fully
  green; waiting at Steven's explicit merge-approval gate.

## Log Edit-Lock

RELEASED: 2026-07-16 06:48 +0000 · Codex (PR #14 review boundary clear-safe)

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-16 06:48 +0000 · Codex PR #14 merge gate
Read CURRENT.md, agent_handoff/README.md, then inspect PR #14 and git status.
PR #14 splits ReportGeneViewer by adapter/controller/presentation/protein responsibility
behind its unchanged exported component contract; commit 19f04f2 is pushed.
Lead review found no blockers. Focused local checks, CI run 29477496972, and the
Vercel preview are green; the prior full root verify and report browser smoke passed.
Do not merge until Steven explicitly approves PR #14.
After approval, merge as lead, fast-forward local main, verify the merged boundary,
and write the post-merge handoff. Keep cloud/provider/schema/deploy actions gated.
Safe to clear: yes — the implementation and handoff are pushed; only merge approval remains.
```

## Pointer

- PR: #14, `refactor(web): split report gene viewer responsibilities`.
- Branch: `codex/report-gene-viewer-fold`; implementation commit `19f04f2`.
- CI: run `29477496972`; all six repository jobs passed.
- Preview: Vercel deployment `ArtZYAag3ahogHWDaE3SqX4N3neK`, Ready.
- Local resumed checks: adapter/controller Vitest 3/3, protein-architecture
  regression, and structure guard 10/10 passed.

## Delta

- `ReportGeneViewer.tsx` fell from 2,487 to 845 lines while remaining the stable
  public component and gene-locus renderer.
- Snapshot adaptation, request/state control, shared presentation, protein view
  modeling, and protein SVG rendering now have focused modules and line budgets.
- Focused tests preserve snapshot semantics and fixture/live-fetch decisions;
  the existing report fixture visuals, copy, controls, and provenance remain.
- Lead review found no blocker, attribution footer, boundary drift, or unowned
  product/cloud/schema/deploy change.

## Next Action

- Wait for Steven's explicit approval to merge PR #14. Once approved, perform
  the lead-run merge, update local `main`, run the post-merge checks, and record
  the final clear-safe boundary.
