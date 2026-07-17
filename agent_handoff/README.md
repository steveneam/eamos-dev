# Agent Handoff Protocol — Canonical Source

Shared source of truth for Claude Code and direct Codex sessions. **This README
is the single home for the coordination protocol** — `CLAUDE.md`, `CODEX.md`, and
`CURRENT.md` point here; change a rule *once*, here.

- **README.md** = stable rules (rarely changes).
- **CURRENT.md** = live state only: the lean 5-heading overwrite-whole-file form
  (Active Status / Log Edit-Lock / Resume Prompt / Pointer / Delta / Next Action);
  zero append surfaces, gated by `eamos-handoff-lint --strict`.
- **PROGRESS.md / CHANGELOG.md / each agent's next-session doc** = history.

## Read Order (every session)

`CLAUDE.md`/`CODEX.md` → this file → `CURRENT.md` (live state) →
`docs/operations/risks-and-guardrails.md` (hazards/gated) → the active
`plans/<feature>/` → `git status --short --branch` + `git diff --stat` (live
worktree truth). Read `docs/governance/decisions.md` when relevant.

## Hard Rules (user-mandated — breaking any needs explicit per-instance user OK)

1. **Never delete/overwrite the other agent's plan, handoff section, task brief,
   or `next-session-*` doc.** Supersede only by *append + archive*: copy the old
   verbatim to `agent_handoff/archive/<date>-<slug>.md`, then write new.
2. **Narrate your own work in your own `CURRENT.md` section.** You may reconcile
   the other's section (it's away / a factual error) but must preserve it via
   append+archive (Rule 1) — never silently clobber.
3. **Agent-agnostic ownership (Steven 2026-07-08).** Any agent owns any file/lane
   full-stack (FE + BE + data + docs + tests + tooling) and may audit/fix the
   other's historical work, deps, and branches. No fixed Claude=FE / Codex=BE
   wall; Steven picks the active agent by availability + usage limits.
4. **Shared files need a lock.** Before editing a shared/high-conflict file
   (`CLAUDE.md`, `CODEX.md`, `agent_handoff/*`, `CHANGELOG.md`, `PROGRESS.md`,
   `ROADMAP.md`, `plans/README.md`, `app/*/lib/backend.ts`, backend schemas), claim
   it in `CURRENT.md → ## Shared File Locks` (a lock line lives there only while
   held; released locks → PROGRESS.md); if held, defer or file a Cross-Agent
   Request. Never both editing one file.
5. **Contract changes are schema-first.** Land the backend Pydantic schema first,
   then the `app/web/lib/backend.ts` mirror; `test_frontend_contract.py` is the
   canary. Ordering, not role.
6. **No idle waiting.** Blocked or the next milestone is user-gated → follow the
   Idle Protocol; never idle, never start a gated milestone to fill time.
7. **Ownership is by availability, not role.** Two agents at once → take **disjoint
   scopes**, record who owns which in `## Active Status` (see Rule 3).
8. **Timestamp + edit-lock every log/handoff write** (`CURRENT.md`,
   `docs/operations/risks-and-guardrails.md`, `docs/governance/decisions.md`,
   `CHANGELOG.md`, `PROGRESS.md`, `ROADMAP.md`, active `plans/*`). Stamp the
   section `YYYY-MM-DD HH:MM ±zzzz · <agent>` from the real clock. Claim the
   single `## Log Edit-Lock` line first (`LOCKED: …`), release last
   (`UNLOCKED · …`) after re-reading. Other agent's lock fresh (≤20 min) → STOP
   + ask; stale (>20 min) → record takeover, proceed.
9. **`CURRENT.md` updates at MAJOR boundaries only — REPLACE, never stack.**
   Minor progress → your own rolling log (Claude →
   `~/.claude/plans/next-session-eamos.md`; Codex → `PROGRESS.md`), never here.
   When you update, overwrite the whole file to the lean form; append+archive
   verbatim first (Rule 1) if it held unrecorded detail. **Every session
   regardless** (safety, not gated): refresh `## Active Status`, release
   `## Log Edit-Lock`, end clear-safe. "Major" = a verified milestone or a
   user-visible state change.
10. **Raise the bar each session — ship net-new, not just maintenance.** The plan
    and Steven's decisions OUTRANK this; "net-new" is deepening the moat *within*
    the plan, never inventing scope. Durable structural/visual/architectural
    change needs Steven's explicit OK *before* it ships. Land ≥1 of: a new
    user-visible capability, a proprietary tool/script, a measurable perf win
    (name the metric), or a stronger verification layer. Lint/doc/refactor sweeps
    don't satisfy it alone. *Exception:* explicit user-constrained sessions ("just
    commit / clean up / verify") — record the constraint in `## Active Status`.
11. **Finish verified slices committed and pushed.** Once scoped user-directed
    work passes its gates, the acting agent commits and pushes without asking
    Steven to repeat approval; open/update the PR and watch CI when the branch
    workflow applies. Before staging, inspect status and use only explicit owned
    paths (DL-019). Merge approval, destructive Git, cleanup deletion, secrets,
    deploy/cloud actions, Supabase mutations, and other named founder gates stay
    separate. Unverified, speculative, or mixed-ownership work is not swept in.
12. **Bound phases and obey wrap immediately.** Before implementation, freeze a
    short exit checklist and explicit exclusions from the active plan. A late
    review finding is either (a) a concrete violation of that checklist or a
    security/data-integrity invariant, or (b) deferred follow-up; it does not
    silently widen the phase. After the first full green boundary, do not open
    another general audit. After Steven says `wrap`, `stop`, or equivalent,
    start no new implementation: resolve only red caused by the owned slice,
    run the minimum remaining gate, commit/push, watch required CI, and hand
    off. If a newly discovered critical issue truly prevents that boundary,
    state the issue and its bounded fix before touching it. Verification is
    focused during development, one full local gate at the boundary, and one CI
    run; repeat a full layer only when a later mutation can affect that layer.

## Idle / Usage-Exhaustion Protocol

Blocked or waiting → never idle, never start a gated milestone. Take the
highest-value safe work anywhere (agent-agnostic): plan-ahead reviewable
artifacts; behavior-preserving hardening (no contract-shape change); mock-first
against a not-yet-built dep; write the precise ask into `## Cross-Agent Requests`;
browser/a11y/perf/security/test QA. Never in free time: gated milestones, the
other agent's in-flight work, shared-contract shape mid-flight, broad reformatting,
committing/pushing unrequested work, speculative features.

## Integration Checkpoint

At milestone boundaries (not mid-task) the active agent runs `cd app/backend &&
python -m pytest tests/test_frontend_contract.py -q` + a frontend build + a FE↔BE
smoke, logs it in its section, flags drift in `## Cross-Agent Requests`.

## Stop / Break Semantics

On "break / wrap / stop / pause": start no new scope, ask no new non-blocking
questions, reach the nearest **verified** boundary, finalize the handoff (own
`CURRENT.md` section if major + heartbeat + lock release; archive, never delete,
anything superseded). A review observation found after the stop instruction is
recorded for the next slice unless it proves the current commit unsafe; it is
not an invitation to resume auditing. **The final chat message must end with** (1) a labeled
`Safe to clear: yes|no` line + reason and (2) a fenced, paste-ready resume
`Prompt:` block — in the message, not only the files.

## Resume Prompt Format

A pointer, not a state dump (~8 lines, ≤15 for the lint). First line is a stamp
(real local time): `# Resume prompt · YYYY-MM-DD HH:MM ±zzzz · <agent> <task>`.
Say what to read first, the one-line delta, and the gate. The same stamped prompt
goes in `CURRENT.md → ## Resume Prompt`.

## Wrap Ritual — mechanical rolling-log rotate-to-archive

Keep the live docs lean by rotating history OUT, never stacking it IN.
`CURRENT.md`: overwrite to the lean 5-heading form; released locks, DONE/stale
Cross-Agent Requests, and superseded narratives move to `PROGRESS.md`; the
pre-reshape file is archived verbatim (Rule 1) when it held unrecorded detail;
`eamos-handoff-lint --strict` must pass. Rolling logs: when one grows past
readability, rotate its oldest sessions verbatim to `archive/<date>-<slug>.md` and
leave a one-line pointer.

## Peer-mail executable contract

Added: 2026-07-16 11:36 +0000 · Codex.

The tracked registry [`.agent-mailboxes.json`](../.agent-mailboxes.json) names
the writer of each channel and is the source of truth for protected inbound
paths. `scripts/eamos-peer-mail.mjs` provides the local commands:

```text
npm run mail -- status
npm run mail -- check --peer=swordfish
npm run mail -- check --peer=swordfish --ack
npm run mail -- wait --peer=swordfish --timeout=60
npm run mail -- send --peer=swordfish --subject="..." --body-file=note.md
npm run mail -- clear-safe
```

`status`, `check`, and `wait` are read-only. `--ack` writes only a receipt under
the repository's private `.git/eamos-peer-mail/` state. `send` is append-only,
uses a per-peer exclusive lock, stamps UTC itself, and refuses secret-shaped
content, out-of-order mail, stale locks, or a staged peer-owned inbox. Running
the command does not create authority to contact a peer; the active task still
controls whether a live send is allowed.

The pre-commit hook always blocks staged peer-owned inboxes. `clear-safe`
refuses unless the live handoff is unlocked with a concrete Next Action,
strict handoff lint passes, locally owned changes are committed, and `HEAD` is
exactly synced with its upstream. A registry-declared watcher-owned inbox may
remain dirty, but never staged. Full neutral contract and adoption procedure:
`docs/operations/peer-mailbox-contract.md`.

## Roles & Capabilities (agent-agnostic — neither is a lane)

Inventory reconciled: 2026-07-15 11:39 UTC by Codex against the live Swordfish
checkout.

Live (this folder): `CURRENT.md` (state only), `NEEDS-STEVEN.md` (open founder
actions), `README.md` (this protocol), and the watcher-pinned
`FROM-SWORDFISH.md` / `ASK-BACKS-FOR-SWORDFISH.md` peer-mail exceptions.
`archive/` holds stamped snapshots and retired evidence. Durable reference
ledgers live at `docs/governance/decisions.md` and
`docs/operations/risks-and-guardrails.md`; other history lives in
`CHANGELOG.md`, `PROGRESS.md`, `ROADMAP.md`, and `plans/*`.
Either agent owns any of FE (UI, design, Workbench, copy, browser iteration) or BE
(APIs, evidence tools, pipelines, schema contracts, tests, live verification,
security, review). Direct Codex sessions have full `~/work/eamos` read/write,
network, and local FE+BE verification, exactly as Claude does.
