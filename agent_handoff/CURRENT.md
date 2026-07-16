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
- **Codex:** STOPPED @ 2026-07-16 10:53 UTC — Render-to-syd2 Phase 1 is complete
  and independently verified. Phase 2/3, cutover, cancellation, and destructive
  cleanup remain held behind new explicit founder gates.

## Log Edit-Lock

UNLOCKED · 2026-07-16 10:54 +0000 · Codex (Phase-1 completion recorded; shared file locks released)

## Resume Prompt

```text
# Resume prompt · 2026-07-16 10:53 +0000 · Codex Phase 1 complete
Read CURRENT.md, README.md, the Phase-1 runbook, latest ASK/FROM notes, and git log/status.
Main d9a3270 and image sha256:177fb44f...16b8 are verified; CI 29487052200 was green.
Two independent Render manifests match: 23 rows / 47,943,536,945 bytes / c907fa2a...20cbb.
Exact-byte preservation added the approved 10 objects; comparator is matched=23 render_only=0.
The syd2 ClinGen one-off exited 0 and its one-file asset-manifest diff is green.
Payload: 527925248 bytes, sha256 50e12d4c...dd9b, owner 1000:1000, mode 0600.
Runtime remains empty, .drill is intact, service is stopped 0/0, temp credentials are absent.
Four exited uvicorn swarm remnants remain deliberately unpruned; they contain no payload.
Do not start Phase 2/3, cutover, Render cancellation, provider changes, or cleanup without a new gate.
Safe to clear: yes — Phase 1 is verified, the handoff is recorded, and all later actions are held.
```

## Pointer

- Code/image: `d9a3270060a7b50886964546c0b7dd995139e647` and
  `ghcr.io/steveneam/eamos-backend@sha256:177fb44fae30d2fec76d97f39636a05ea08067f2a472e6138c291109d87716b8`.
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

## Next Action

- No migration action is active. Await Steven's explicit gate for Phase 2/3.
- If resumed, re-read the latest Swordfish note, rerun the fail-closed syd2
  preflight before any write, and preserve the frozen digest/mount/manifest
  contracts. Render stays live until the final founder-approved Phase-4 cancel.
- Leave the four exited uvicorn evidence containers alone unless destructive
  cleanup is separately and explicitly authorized.
