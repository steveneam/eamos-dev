# Current Agent State

> ## ▶ BOOT: Steven types **`gogogo`** — that IS the whole resume prompt.
>
> **Agent, on `gogogo` (or any greeting with no task): do this, unprompted.**
> He cannot copy text out of the terminal, and he may be sending it from a
> Telegram topic on his phone (the swordfish hermes relay cold-starts this
> session in tmux — no one types `claude` first). So there is no prompt for him
> to paste: **the prompt is this file.** Read, in order, then act:
> 1. this whole file (Resume Prompt → Pointer → Delta → Next Action)
> 2. `CLAUDE.md` + `agent_handoff/README.md` (protocol) and your memory
> 3. `git log --oneline -8` and `git status` — trust the repo, not the stamp
>
> Then **state the Next Action in one sentence, say what you are starting, and
> start it.** Do not ask "shall I?" — the Next Action IS the standing approval.
> Stop only at a founder gate (spend · irreversible · anything the protocol
> names a founder decision).
>
> _Boot block added 2026-07-13 at the founder's direction (by the swordfish ops
> agent) so a relay-cold-started session resumes with no chat history. Keep it
> at the top when you overwrite this file each wrap._

> **Live state only — overwrite the whole file each wrap; zero append surfaces.**
> This is the lean 5-heading form (assimilation M-012): Active Status + Log
> Edit-Lock are the every-session safety lines; Resume Prompt / Pointer / Delta /
> Next Action are the state. History lives in **git + PROGRESS.md + each agent's
> rolling log**, never here. Protocol (hard rules, locks, idle, stop/break,
> resume format) → `agent_handoff/README.md`. Risks → `agent_handoff/RISKS.md`.
> Worktree truth → `git status --short --branch` (not a frozen inventory file).
> The append-only ledgers that used to live here (Log-Edit-Lock history,
> Shared-File-Locks, Cross-Agent-Requests, per-agent Last-Task narratives) were
> relocated to PROGRESS.md on 2026-07-09; the full pre-reshape file is archived
> verbatim at `agent_handoff/archive/2026-07-09-current-pre-m012-lean-reshape.md`.

## Active Status

- **Claude:** STOPPED @ 2026-07-15 10:55 UTC (20:55 AEST) — **first boot on
  syd4** (Linux VPS; every `D:\`/`E:\` path is dead). Landed **PR #7** (merged
  to `main`): de-Windowsed `.mcp.json` (removed dead `obsidian-vault`, un-`cmd`'d
  `chrome-devtools`) + `.claude/settings.json` Stop hook, and fixed the **M-010
  pre-commit guard** — it was tracked `100644`, so git silently skipped it via
  `core.hooksPath` on Linux (now `100755`, armed + dogfooded green). Founder-
  approved direct-to-main housekeeping: pushed BOOT `67e7fb4`, deleted stale
  `codex/m9` remote branch, pruned `~/.codex/config.toml` Windows trust sections.
  **Ask-back sent to swordfish** (status + migration parked + consolidation Qs).
  `main == origin/main`, tree clean after this wrap. No env/provider/flag/
  Supabase change (Vercel autoDeploy rebuilt prod on the merges — docs/config
  only). Detail → `~/.claude/plans/next-session-eamos.md` (session 13).
- **Codex:** TAKING OVER 2026-07-15 — next: execute the founder-approved
  `agent_handoff/` consolidation per **`plans/handoff-consolidation/plan.md`**
  as one PR. Migration Phase 1 **PARKED** on the founder's command.

## Log Edit-Lock

UNLOCKED · 2026-07-15 10:55 UTC · Claude (wrap; own edits only)

## Resume Prompt

```text
# Resume · 2026-07-15 10:55 UTC (20:55 AEST) · Codex takeover (Eamos, agent_handoff consolidation)
Eamos, ~/work/eamos on syd4 (Linux/bash; every D:\ / E:\ path is dead). Read:
agent_handoff/README.md (Hard Rules) → this CURRENT.md → RISKS.md →
plans/handoff-consolidation/plan.md → CODEX.md/AGENTS.md. First:
git -C ~/work/eamos fetch origin && git status -sb && gh pr list --state open.
Delta: PR #7 merged (Linux config de-Windowsing + M-010 guard armed — was inert
at 100644). Ask-back sent to swordfish. Founder APPROVED the agent_handoff
consolidation "as one PR"; NEEDS-STEVEN.md add/skip deferred to swordfish's reply.
Next: execute plans/handoff-consolidation/plan.md via branch→PR→CI-green→Steven's
approval→admin-merge. FROZEN: never move/rename FROM-SWORDFISH.md /
ASK-BACKS-FOR-SWORDFISH.md (swordfish watcher pins them). Hard Rule 1: rotate to
archive/ verbatim (append+archive), never delete tracked history.
Guardrails: NO attribution trailer (verify %(trailers) empty); never git add -A
(explicit pathspecs); never cd; py312; backend -n auto; Vercel autoDeploy ON
(merge→prod rebuild); Render autoDeploy OFF (don't touch hook); don't revert
LLM_PROVIDER=gateway. Migration Phase 1 PARKED on founder's command. End clear-safe.
```

## Pointer

- Read next session: `agent_handoff/README.md` (Hard Rules) → this file →
  `agent_handoff/RISKS.md` → `plans/handoff-consolidation/plan.md` →
  `CODEX.md`/`AGENTS.md` → `git status --short --branch` + `gh pr list`.
- **Open ask-back thread:** `agent_handoff/ASK-BACKS-FOR-SWORDFISH.md`
  (2026-07-15) — awaiting swordfish's reply on `NEEDS-STEVEN.md` + fleet shape.

## Delta

- First boot on syd4 complete. **PR #7 merged** (Linux config de-Windowsing +
  M-010 guard armed — the guard was inert at `100644`; now `100755`).
- Ask-back sent to swordfish. Founder **APPROVED** the `agent_handoff/`
  consolidation "as one PR"; `NEEDS-STEVEN.md` add/skip **deferred to
  swordfish's reply**. Migration Phase 1 parked on the founder's command.
- Prod unchanged in substance: Ask-Eamos chat LIVE (per-user 10/day); M9
  LOCAL_EVIDENCE live on `eamos-dev-sg`; Render autoDeploy off, Vercel
  autoDeploy on (merges rebuilt prod with docs/config only).

## Next Action

- **Codex:** execute **`plans/handoff-consolidation/plan.md`** via branch → PR →
  CI-green → Steven's approval → admin-merge. **Frozen:** never move/rename
  `FROM-SWORDFISH.md` / `ASK-BACKS-FOR-SWORDFISH.md` (swordfish watcher pins
  them). **Hard Rule 1:** rotate to `archive/` verbatim, never delete history.
- **Deferred:** `NEEDS-STEVEN.md` (swordfish's fleet-pattern call); **M-013** CI
  hardening (needs Steven's branch-protection decision); **M-006** gateway choke.
- **Parked (founder gate):** Render→VPS asset migration Phase 1 (swordfish's
  brief in `agent_handoff/FROM-SWORDFISH.md`; plan in swordfish's
  `research/project1-asset-migration-plan-2026-07-15.md`).
