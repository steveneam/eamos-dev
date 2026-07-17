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
- **Codex:** PHASE-3C SOAK ACTIVE @ 2026-07-17 12:43 +0000 — the beginning
  sample and a verification-only pre-middle pulse are green. The two genuine
  viewer 503s remain bounded to the application path; later direct/proxied
  traffic is clean, and Swordfish withdrew its timestamp-filter false positive.
  The roughly 24-hour middle sample is due around 2026-07-18 11:31 UTC; the
  48-hour floor plus middle/end evidence remain open. This early resume was
  deliberately verification-only because the timed gate was not yet valid.
  Render stays live as rollback; Phase 4 remains held for a separate direct
  Steven instruction.
- **Runtime:** Codex is inside the persistent `eamos` tmux session under
  `agent-tmux.service`; the code-server terminal profile now defaults to that
  seam, so a code-server restart no longer owns this process cgroup.

## Log Edit-Lock

UNLOCKED · 2026-07-17 12:43 +0000 · Codex

## Shared File Locks

- None. Codex released the verification-only pre-middle checkpoint locks at
  2026-07-17 12:43 +0000.

## Resume Prompt

```text
# Resume prompt · 2026-07-17 12:43 +0000 · Codex Phase-3c active soak
Read CURRENT.md, README.md, latest Swordfish mail, and the Phase-3 runbook's active-soak section.
Do not repeat the domain attach or Vercel flip; preview-api and eamos-dev production already use syd2.
Compose 5rBnRf20ht4wGRQ856ZLO and stable alias eamos-dev.vercel.app are the active seam.
The 12:12 beginning sample is green; exactly two app viewer 503s remain in the historical tally.
The 12:40 pre-middle pulse was also green but does not satisfy the roughly 24-hour time gate.
Use the performance audit's --require-ok mode for the roughly 24-hour middle and 48-hour end samples.
Run the middle sample around/after 2026-07-18 11:31 UTC and include exact Compose/resource proof.
The 48-hour floor ends approximately 2026-07-19 11:31 UTC, but every evidence gate must also pass.
Keep Singapore Render and the old Application live; do not widen grants or enable auto-deploy.
Do not flip forwarded-header trust ad hoc; the trusted-proxy boundary is a separate reviewed follow-up.
Phase 4, Supabase, tags, credentials, cleanup, and Render cancellation remain held for direct gates.
Codex runs inside persistent tmux via agent-tmux.service; continue from that seam.
```

## Pointer

- Full mutation ledger, proof, and soak exit contract:
  `docs/deployment/render-to-syd2-phase3.md` → Phase 3c.
- Executable full-report failure ratchet:
  `scripts/eamos-report-performance-audit.mjs --require-ok`; regression test:
  `scripts/eamos-report-performance-audit.test.mjs`.
- Hardened Compose: `5rBnRf20ht4wGRQ856ZLO`; public-label redeploy:
  `SSvNBmx91esTGz1tohYoU`; immutable contract: `deploy/syd2/compose.yaml`.
- Stable Vercel production seam: `eamos-dev.vercel.app`; initial cutover
  deployment: `dpl_2Yy6712rwE4zHqaKPHjJoCxmC9SZ`. Every `main` push creates a
  successor deployment, so follow the alias rather than treating that ID as
  current. Prior rollback target: `https://eamos-dev-sg.onrender.com`.
- Beginning-sample proof and 503 characterization are in the runbook; the
  verification-only 12:40 pulse is at the top of `PROGRESS.md`; the 12:20
  false-positive correction is in
  `agent_handoff/ASK-BACKS-FOR-SWORDFISH.md`.
- Trusted-proxy residual and remediation gate:
  `docs/operations/risks-and-guardrails.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Beginning DNS/TLS/redirect, direct/proxy/rollback health, provider state,
  auth/CORS/security headers, exact Compose, and container-resource samples are
  green. A 12:40 pre-middle pulse re-proved the public/rollback/security paths;
  direct and proxied provider-health bytes still match and differ from Render.
- The historical log has exactly two app-level viewer 503s, 18 viewer 200s, two
  expected 422s, and zero 429s. A later 18-request window had 16x 200, 2x 422,
  and no 503; the old structured error is unavailable, so transient external
  coordinate resolution remains the bounded explanation rather than proof.
- The 12:40 `--require-ok` pass returned 200 for lookup, summary, four lazy
  sections, and viewer; lookup/viewer were 16.15/1.43 seconds. A handled
  upstream `ReadTimeout` remained a warning rather than an HTTP failure.
- `npm run verify` passed in 147.1 seconds: executable structural/contract
  guards, lint/format/typecheck, 11 Node ratchet tests, 163 web tests, full
  backend pytest, and the 17-route production build. CI run `29580021557` for
  `faeae0a` also passed.
- Forwarded-header trust remains disabled, collapsing app IP buckets behind
  Traefik. It did not cause the 503s and was not changed during the frozen soak.
- No deployment, provider, environment, DNS, Render, Supabase, credential,
  source, cleanup, or Phase-4 mutation followed the cutover.

## Next Action

- At/after roughly 2026-07-18 11:31 UTC, run the Phase-3c middle sample:
  `--require-ok` report/viewer coverage plus DNS/TLS, direct/proxy/rollback
  health, provider, resource/restart/OOM, auth/CORS, and exact-contract checks.
  Repeat at/after the 48-hour floor; do not close Phase 3c on elapsed time alone
  or enter Phase 4 without Steven's separate direct authorization.
