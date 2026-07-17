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
- **Codex:** PHASE-3C SOAK ACTIVE @ 2026-07-17 11:38 +0000 — Steven directly
  authorized and Eamos completed the public-domain attach plus Vercel target
  flip. DNS/TLS, proxy-origin proof, auth boundary, effective-container
  hardening, and the full local repository gate are green. One mixed viewer
  200/503 observation keeps the soak open. Render stays live as rollback;
  Phase 4 remains held for a separate direct Steven instruction.
- **Runtime:** Codex is inside the persistent `eamos` tmux session under
  `agent-tmux.service`; the code-server terminal profile now defaults to that
  seam, so a code-server restart no longer owns this process cgroup.

## Log Edit-Lock

UNLOCKED · 2026-07-17 11:38 +0000 · Codex

## Shared File Locks

- None. Codex released the bounded Phase-3c cutover evidence locks at
  2026-07-17 11:38 +0000.

## Resume Prompt

```text
# Resume prompt · 2026-07-17 11:38 +0000 · Codex Phase-3c active soak
Read CURRENT.md, README.md, the latest Swordfish mail, and the Phase-3 runbook's Phase-3c section.
Do not repeat the domain attach or Vercel flip: preview-api and eamos-dev production are already live on syd2.
Compose 5rBnRf20ht4wGRQ856ZLO and Vercel deployment dpl_2Yy6712rwE4zHqaKPHjJoCxmC9SZ are the active seam.
Frontend/backend workstation ports remain 3532/8532; Dokploy 8000 is only the isolated container listener.
Next, gather spaced soak evidence and characterize the immediate viewer probes that mixed 200 and 503.
The 48-hour floor ends approximately 2026-07-19 11:31 UTC, but every evidence gate must also pass.
Keep Singapore Render and the old Application live; do not widen grants or enable auto-deploy.
Phase 4, Supabase, tags, credentials, cleanup, and Render cancellation remain held for direct gates.
Codex runs inside persistent tmux via agent-tmux.service; continue from that seam.
```

## Pointer

- Full mutation ledger, proof, and soak exit contract:
  `docs/deployment/render-to-syd2-phase3.md` → Phase 3c.
- Hardened Compose: `5rBnRf20ht4wGRQ856ZLO`; public-label redeploy:
  `SSvNBmx91esTGz1tohYoU`; immutable contract: `deploy/syd2/compose.yaml`.
- Vercel production deployment: `dpl_2Yy6712rwE4zHqaKPHjJoCxmC9SZ`, alias
  `eamos-dev.vercel.app`; prior rollback target:
  `https://eamos-dev-sg.onrender.com`.
- Immediate provider-health proof: direct syd2 and Vercel share SHA-256
  `b087c5a6…`; Render differs and remains HTTP 200.
- Cutover receipt sent to Swordfish at 11:34 UTC in
  `agent_handoff/ASK-BACKS-FOR-SWORDFISH.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- `preview-api.swordfish.cfd` now serves the hardened Compose through valid LE
  TLS, and Vercel production now proxies to it. The complete provider-health
  payload proves the active origin is syd2 rather than Render.
- Public 443, local frontend/backend 3532/8532, and isolated container 8000 are
  explicitly separated. No host port was published.
- Auth/CORS/security-header checks passed. Effective-container inspection after
  redeploy retained the exact digest, all hardening, restart 0, and 747.7 MiB / 2
  GiB immediate memory use.
- `npm run verify` passed in 144.9 seconds: structural/port/contract guards,
  lint/format/typecheck, 9 coordination tests, 163 web tests, full backend
  pytest, and the 17-route production build.
- Immediate repeated viewer probes mixed 200 and 503 without a crash or
  restart. A later probe returned 200; this remains an explicit soak item.

## Next Action

- Run the Phase-3c spaced soak matrix from the runbook, beginning with the
  viewer 503 characterization and representative Vercel-proxied viewer,
  summary, full-report, provider, resource, TLS, auth, and rollback samples.
  Do not close Phase 3c on elapsed time alone and do not enter Phase 4 without
  Steven's separate direct authorization.
