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
- **Codex:** STOPPED @ 2026-07-16 11:18 UTC — Phase 1 is complete. The next
  `gogogo` has standing approval to build the Eamos-local cross-agent mailbox
  ratchet; all migration and Swordfish-side actions remain held.

## Log Edit-Lock

UNLOCKED · 2026-07-16 11:20 +0000 · Codex (clear-safe ratchet queued; lock released)

## Resume Prompt

```text
# Resume prompt · 2026-07-16 11:18 +0000 · coordination ratchet queued
Read CURRENT.md, README.md, CLAUDE.md, git log/status, and the live mailbox conventions.
Phase 1 is complete; head f6474a2 and CI 29492555791 are green. Migration stays held.
Steven explicitly approved the next-session Eamos-local coordination-ratchet lane.
Build a peer-mailbox registry and tested CLI for send, check, wait, and status.
Enforce mailbox ownership/order, UTC stamps, lock hygiene, secret/stale-lock checks, and staging guards.
Add a clear-safe verifier: refuse unless CURRENT has the concrete next plan, is unlocked,
strict-lint clean, committed, and pushed; never tell Steven to clear/start before it passes.
Document a neutral cross-project contract and prepare a Swordfish adoption packet.
Use mock mailboxes for tests; never edit/stage FROM-SWORDFISH.md or Swordfish's repository.
Do not contact Swordfish or start Phase 2/3, resize, bulk seed, cutover, cancellation, or cleanup.
Keep structural guards green, commit, push, and watch CI to the verified boundary.
Safe to clear: yes — the next action and its exclusions are durable in CURRENT.md.
```

## Pointer

- Code/image: `d9a3270060a7b50886964546c0b7dd995139e647` and
  `ghcr.io/steveneam/eamos-backend@sha256:177fb44fae30d2fec76d97f39636a05ea08067f2a472e6138c291109d87716b8`.
- Phase-1 handoff: `f6474a2b008141ee86b01183d10d2f91f33450f1`;
  CI run `29492555791` and Vercel are green.
- Runbook: `docs/deployment/render-to-syd2-phase1.md` §4 blocks migration on
  any `RENDER_ONLY`; §7 is now checksum-green for the isolated ClinGen proof.
- Evidence: `/home/deploy/transfer-project1/` is `0700`; Eamos manifest and
  identity artifacts are `0600` with hashes recorded in the outbound note.
- Source proof: private prefix `render_precutover_20260716/` contains exactly
  the approved 10 new objects / 5,061,937,840 bytes; post-preservation inventory
  is 45 objects / 48,562,226,185 bytes with manifest SHA-256 `dbc6ad9a...fe2`.
- syd2 proof: `/srv/project1/assets/phase1-dry-run/` contains only the verified
  payload and metadata; `/srv/project1/assets/runtime/` is empty.
- Coordination: latest requests/verdicts are in `ASK-BACKS-FOR-SWORDFISH.md`
  and watcher-owned `FROM-SWORDFISH.md`; never stage or edit the latter.

## Delta

- Steven approved exact-byte preservation and accepted worst-case Render
  overage of at most $0.02; all 10 Render-only identities were preserved without
  overwrite/delete, and strict comparison now exits 0 at `render_only=0`.
- Swordfish `project1-apply` run `29491702667` is green at `104d8f0`; the exact
  image digest, numeric user, two mounts, free space, and empty roots were probed.
- The §7 one-off used only four S3 keys via a mode-0600 ephemeral env file,
  exited 0, self-removed, and left the long-lived service stopped at `0/0`.
- Codex independently re-hashed the payload, reran `asset-manifest diff`, checked
  permissions/tree/runtime/canary, and corroborated the stopped service state.
- Phase 1 exit is met. Phase 2 resize is held; current 79 GiB free means the
  resize trigger remains the later Phase-3 bulk seed, not this completed proof.
- Steven chose to leave Swordfish closed tonight and approved turning the
  successful asymmetric mailbox/watcher workflow into an executable Eamos
  ratchet next session, without cross-project or infrastructure mutations.

## Next Action

- On bare `gogogo`, immediately implement the approved Eamos-local coordination
  ratchet: registry; `send`/`check`/`wait`/`status` CLI; ownership, append-order,
  timestamp, lock, secret, staging, and durable clear-safe guards; tests; neutral
  protocol docs; and a ready-but-unsent Swordfish adoption packet.
- Do not ask Steven to restate approval. Do not edit/stage the watcher-owned
  inbound file, touch Swordfish's repository, contact its agent, or mutate any
  cloud/host/provider state. Keep every migration phase held.
- Verify the applicable structural guards, commit only owned paths, push, and
  watch CI. Leave the four exited uvicorn containers untouched.
