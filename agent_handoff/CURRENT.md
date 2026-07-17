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
- **Codex:** STOPPED AT FOUNDER GATE @ 2026-07-17 10:57 +0000 — Phase 3a and
  internal Phase 3b are two-party green. Swordfish moved and independently
  consume-tested the deploy-only tenant grant. The public-hostname/Certificate-
  Transparency and Phase-3c cutover/soak decision is now held for Steven; no
  edge, DNS, Vercel, Render, or traffic mutation is in flight.
- **Runtime:** Codex is inside the persistent `eamos` tmux session under
  `agent-tmux.service`; the code-server terminal profile now defaults to that
  seam, so a code-server restart no longer owns this process cgroup.

## Log Edit-Lock

UNLOCKED · 2026-07-17 11:16 +0000 · Codex

## Shared File Locks

- None. Codex released the bounded Swordfish-acknowledgement locks at
  2026-07-17 11:16 +0000.

## Resume Prompt

```text
# Resume prompt · 2026-07-17 10:57 +0000 · Codex Phase-3c founder gate
Read CURRENT.md, README.md, the latest Swordfish ASK/FROM entries, and the Phase-3 runbook.
Phase 3a and internal Phase 3b are two-party green on Compose 5rBnRf20ht4wGRQ856ZLO.
Swordfish moved the tenant grant and proved Compose positive plus old-app/cross-tenant/Docker/SSH denial.
The old Application rollback is deliberately human-only from CI; do not widen the grant.
The mixed-heading mail ratchet now surfaces Swordfish's physically latest 10:45 reply.
Stop for Steven's public preview-api hostname/CT-log and Phase-3c cutover/soak decision.
If approved, freeze the external-routing and evidence-based soak contract before mutation.
Keep Render and the old Application live; auto-deploy, tags, Phase 4, and Supabase stay held.
Codex runs inside persistent tmux via agent-tmux.service; continue from that seam.
```

## Pointer

- Durable service contract: `deploy/syd2/compose.yaml`; ratchet:
  `app/backend/tests/test_syd2_compose_contract.py`; commit `2374dbc`.
- Actual green workflow: `29571532636` on `ac6d3e8`; internal Compose ID:
  `5rBnRf20ht4wGRQ856ZLO`; deployment: `6FfxABW5Aplk_G7HWb1Z7`.
- Proof-wrap workflow `29574642738` is fully green for `3048633`, including
  image publication and immutable pull-back.
- Full retained proof and credential boundary:
  `docs/deployment/render-to-syd2-phase3.md` → Phase 3b internal Compose proof.
- Cross-agent closure: Swordfish's 10:45 inbound reply and Eamos's 10:56
  acceptance in `agent_handoff/ASK-BACKS-FOR-SWORDFISH.md`.
- Mailbox regression ratchet: `.agent-mailboxes.json` and
  `scripts/eamos-peer-mail.test.mjs` mixed-level/physical-latest coverage.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Through the tenant key, Compose returned 200; the old Application, a Thalon
  service, Docker inventory, and SSH-key inventory returned 401; project scope
  exposed only `project1`. The grant was moved, not copied.
- Swordfish's direct container inspection independently corroborated healthy
  state, read-only root, cap-drop ALL, 2-GiB limit, read-only corpus mounts,
  writable private state, and zero host bindings.
- The receiver registry now accepts legacy level-1 and current level-2 inbound
  headings. Physical append order determines the latest inbound title, so a
  delayed peer timestamp cannot mask new bytes; nine peer-mail tests pass.
- The old hardened Application and Singapore Render service are both healthy.
  Phase 3c has not started and no external hostname or production traffic moved.

## Next Action

- Steven decides whether to create the public `preview-api.swordfish.cfd`
  hostname, accepting its durable Certificate-Transparency footprint, and
  authorizes the external proxy/Vercel Phase-3c path. If approved, freeze the
  routing and evidence-based soak exit contract with Swordfish before any
  mutation. Otherwise hold the internal Compose exactly as proved.
