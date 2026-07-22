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
- **Codex:** STOPPED @ 2026-07-22 22:22 +0000 — user-requested wrap at the
  exact Wave 3 material-approval gate.
- **Waves 1–2:** Wave 1 PRs #24/#25/#23/#26, contract-amendment PR #27, and
  runtime-composition PR #28 are merged. Post-merge CI run `29961634345` is
  fully green on `main@2dd181c`.
- **Wave 3:** exact material approval cards are frozen in PR #29 from commit
  `55df2ce`; CI run `29962477435` was still completing at wrap. No card was
  executed and PR #29 remains unmerged pending green CI plus merge approval.
- **Wave 4:** not started. Production, provider, cloud, deploy, Supabase, and
  source-materialization state are unchanged.

## Log Edit-Lock

UNLOCKED · 2026-07-22 22:22 +0000 · Codex

## Shared File Locks

- None. Campaign lane locks are released; watcher-owned
  `agent_handoff/FROM-SWORDFISH.md` remains untouched.

## Resume Prompt

```text
# Resume prompt · 2026-07-22 22:22 +0000 · Codex Live Product Wave 3 gate
Read CURRENT.md, plans/live-product-completion/{research,spec,plan}.md, and docs/live-product-verification/wave3-approval-cards.md.
Wave 1, the contract amendment, and Wave 2 are merged green through main@2dd181c; PR #29 freezes the eight exact Wave 3 approval cards.
First verify PR #29 CI and obtain Steven's separate approval before merging it.
Do not download, build, materialize, upload, mount, configure, or deploy any card until Steven names the approved card IDs exactly.
After exact approval, execute only those bounded cards and retain every deferred/NO-GO item.
Wave 4 remains pending behind Wave 3 verification and its own applicable gates.
Never stage watcher-owned agent_handoff/FROM-SWORDFISH.md.
```

## Pointer

- Plan: `plans/live-product-completion/{research,spec,plan}.md`.
- Exact cards: `docs/live-product-verification/wave3-approval-cards.md`.
- Review boundary: PR #29, branch `agent/live/material-approval-cards`, card
  commit `55df2ce`, CI run `29962477435`.
- Merged Wave 2 boundary: PR #28, `main@2dd181c`, post-merge run
  `29961634345`.
- Watcher-owned `agent_handoff/FROM-SWORDFISH.md` remains dirty only in the
  main checkout and was not staged or edited.

## Delta

- Merged and post-merge-verified the four Wave 1 lanes, contract amendment,
  and Wave 2 runtime composition.
- Researched and froze eight individually approvable Wave 3 cards totaling
  about 1.673 GiB, with checksums/licences/bounds and explicit rollback paths.
- Kept unavailable, incompatible, oversized, or licence-unclear candidates in
  the deferred/NO-GO section. Performed no gated material or cloud action.

## Next Action

- Wait for PR #29 checks and Steven's explicit merge approval; then wait for an
  exact named-card approval before performing any Wave 3 material action.
