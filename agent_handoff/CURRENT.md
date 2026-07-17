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
- **Codex:** STOPPED AT FOUNDER GATE @ 2026-07-17 09:52 +0000 — Phase 3a is
  checksum-green and the internal Phase-3b Application is functionally green.
  Hardened Compose commit `2374dbc` is pushed and fully green locally, but CI
  `29571230013` started no steps because GitHub reports failed account payments
  or an insufficient Actions spending limit. No Compose, edge, DNS, Vercel, or
  Render mutation followed the red gate.

## Log Edit-Lock

UNLOCKED · 2026-07-17 09:52 +0000 · Codex

## Shared File Locks

- None. Codex released the handoff lock at 2026-07-17 09:52 +0000.

## Resume Prompt

```text
# Resume prompt · 2026-07-17 09:52 +0000 · Codex Phase-3b Compose gate
Read CURRENT.md, README.md, the latest Swordfish ASK/FROM entries, and the Phase-3 runbook.
Phase 3a is exact-manifest green; the internal Application and real lookup matrix are green.
Commit 2374dbc freezes the hardened no-port Compose contract and is pushed.
Local full verify and the syd2 Compose parser are green.
CI 29571230013 ran no steps: GitHub account payment/Actions spending gate.
After Steven clears Billing & plans, rerun CI and require every job green.
Only then create the no-domain Compose replacement and repeat the full proof matrix.
Keep Render live and the current Application as rollback; Phase 4 stays held.
Do not edit or stage FROM-SWORDFISH.md or move credentials, tags, DNS, or traffic.
```

## Pointer

- Durable service contract: `deploy/syd2/compose.yaml`; ratchet:
  `app/backend/tests/test_syd2_compose_contract.py`; commit `2374dbc`.
- Blocked workflow: GitHub Actions run `29571230013` on `2374dbc`.
- Phase-3 procedure and retained proof paths:
  `docs/deployment/render-to-syd2-phase3.md`.
- Latest Swordfish coordination: the 09:55 inbound and 09:51 outbound entries
  in the watcher-owned FROM and Eamos-owned ASK mailboxes.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Phase 3a landed 23 files / 47,943,536,945 bytes with canonical SHA-256
  `c907fa2aab78eb31a5ae30dcbc3e914ed89d90584d5aea845f360cdc25c20cbb`;
  exact sizes/hashes, ownership/modes, canary, residue, and reserve all passed.
- The internal Application is healthy at 2 GiB with no domain or published port.
  Real AlphaMissense, coordinate, viewer, Pfam/HMMER, summary, and full lookup
  probes passed; the bounded compact-index ceiling is 131,000 transcripts.
- A Dokploy Application redeploy erased manual read-only-root, cap-drop, tmpfs,
  and read-only-bind hardening. The overlay was restored, and the tracked raw
  Compose contract now makes those properties declarative.
- Swordfish independently confirmed the durability gap and Compose-first order.
  Push-to-box automation remains held; future fixed-tag/deploy-only-key posture
  is a separate post-Compose decision, with no credential movement authorized.

## Next Action

- Steven clears the GitHub Actions account payment/spending-limit gate. Then
  rerun the latest main workflow and require all jobs green. If green, create
  the no-domain raw Compose replacement, transfer the existing 55-name
  environment securely without logging values, and repeat the hardening,
  corpus, real-functional, memory, restart, and rollback checks. Do not expose
  an edge or alter Render/Vercel until that internal Compose proof is green.
