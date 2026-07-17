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
- **Codex:** STOPPED AT CROSS-AGENT GATE @ 2026-07-17 10:46 +0000 — recovered
  and completed the internal Phase-3b Compose proof. Swordfish's independent
  deploy-only tenant-grant move/consumption proof is pending after three
  bounded waits. No edge, DNS, Vercel, Render, or traffic mutation is in flight.
- **Runtime:** Codex is inside the persistent `eamos` tmux session under
  `agent-tmux.service`; the code-server terminal profile now defaults to that
  seam, so a code-server restart no longer owns this process cgroup.

## Log Edit-Lock

UNLOCKED · 2026-07-17 10:46 +0000 · Codex

## Shared File Locks

- None. Codex released the Phase-3b proof-wrap locks at
  2026-07-17 10:46 +0000.

## Resume Prompt

```text
# Resume prompt · 2026-07-17 10:46 +0000 · Codex Phase-3b grant/edge gate
Read CURRENT.md, README.md, the latest Swordfish ASK/FROM entries, and the Phase-3 runbook.
Phase 3a and the no-domain hardened Compose service are exact-proof green.
Actual CI 29571532636 is fully green; Compose 5rBnRf20ht4wGRQ856ZLO is healthy.
Hash/source preflight, real predictors/APIs, clean-restart memory, and both rollbacks passed.
First poll Swordfish mail for the requested tenant-grant move and positive/negative proof.
Do not duplicate that move through the org-admin credential or stage FROM-SWORDFISH.md.
After proof, stop at the public-hostname/CT-log decision before any external proxy or traffic.
Keep Render and the old Application live; tags, workflows, Vercel, DNS, and Phase 4 stay held.
```

## Pointer

- Durable service contract: `deploy/syd2/compose.yaml`; ratchet:
  `app/backend/tests/test_syd2_compose_contract.py`; commit `2374dbc`.
- Actual green workflow: `29571532636` on `ac6d3e8`; internal Compose ID:
  `5rBnRf20ht4wGRQ856ZLO`; deployment: `6FfxABW5Aplk_G7HWb1Z7`.
- Full retained proof and credential boundary:
  `docs/deployment/render-to-syd2-phase3.md` → Phase 3b internal Compose proof.
- Latest outbound evidence/reminder: the 10:40 entry in
  `agent_handoff/ASK-BACKS-FOR-SWORDFISH.md`; inbound reply remains pending.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Effective runtime is exact-digest, `1000:1000`, read-only-root, cap-drop ALL,
  no-new-privileges, no-port, bounded to 2 GiB / 2 CPUs / 256 PIDs, with both
  47.94-GB corpus views read-only and private state writable.
- Resume preflight exact-hashed all 23 files and HEAD-verified all 23 private
  sources with zero downloads. Four S3 keys used the encrypted-stdin/mode-0600
  tmpfs channel and were removed; the serving environment does not retain them.
- AlphaMissense, the bounded coordinate index, viewer, uncached Pfam/HMMER,
  summary, and full lookup passed. After controlled restart, clean warm peak was
  54.11% / 1.073 GiB with zero pressure, restart, or OOM events.
- The old hardened Application and Singapore Render service are both healthy.
  Phase 3c has not started and no external hostname or production traffic moved.

## Next Action

- Poll Swordfish mail and verify its promised positive Compose visibility plus
  negative cross-tenant/Docker-authority proof for the moved deploy-only grant.
  Do not duplicate the permission mutation. Once it is green, present the
  irreversible public-hostname/Certificate-Transparency seam to Steven before
  creating the external Phase-3b proxy or moving any production traffic.
