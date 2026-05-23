# Archived verbatim — Claude CURRENT.md section, pre git-policy update

> Archived 2026-05-18 17:14 +1000 · Claude (README Hard Rule 1/9: append+archive
> before replacing the section). Superseded by the git-policy-lift + memory-
> hygiene + FE-6-Phase-A-start state written into CURRENT.md at the same stamp.
> The restructure narrative below is also recorded in
> `~/.claude/plans/next-session-eamos.md` and `PROGRESS.md`.

## Claude — Last Task & Resume  (as of section stamp 2026-05-18 14:02 +1000)

**Current task (2026-05-18 14:02 +1000):** user-mandated dual-agent workflow
audit + restructure. Done: hard rules/protocol deduped into a single home
(`agent_handoff/README.md`); `CLAUDE.md`/`CODEX.md`/`CURRENT.md` now point
there instead of re-stating; `CURRENT.md` trimmed 1200→~130 lines, state-only;
new Hard Rule 9 (CURRENT.md = major-boundary + replace-never-stack);
`WORKTREE_INVENTORY.md` archived + stubbed (use `git status`); 2 superseded
`DECISIONS.md` entries marked resolved. The pristine 1200-line `CURRENT.md`
and old `WORKTREE_INVENTORY.md` are archived verbatim under
`agent_handoff/archive/2026-05-18-*` (nothing lost — README Rule 1).

**Prior still-valid build state (carry-forward, full detail in
`~/.claude/plans/next-session-eamos.md`):** CRISPR frontend slice
(`plans/crispr-integration.md` §5 Phase A + §8 Phase C-fe) DONE + verified
Session 26 — mock-first on the existing `CrisprResponse` contract, no
`backend.ts`/schema change (TIDE shape FE-local per README Rule 5). FE-5.6
(all 8 items) DONE + verified Session 25. Both uncommitted. Verified: vitest
42/42, build clean, contract 40/40, browser pixel-check.

**Next (all user-gated — do not auto-start):** FE-6 Primer panel + remaining
CRISPR polish · FE-7/FE-8 · commit/push the checkpoint · §7 TIDE FE wiring
once Codex ships `POST /api/v1/crispr/tide` · optional Integration Checkpoint.

**Resume prompt (superseded):**
`# Resume prompt · 2026-05-18 14:02 +1000 · Claude (workflow restructure)
Eamos. Read agent_handoff/README.md (the protocol — now single-home), then
agent_handoff/CURRENT.md (## Claude section + Locks + Requests),
agent_handoff/RISKS.md, ~/.claude/plans/next-session-eamos.md, then git status
--short --branch. Delta: dual-agent workflow restructured — protocol deduped
into README.md, CURRENT.md trimmed to state-only, new Hard Rule 9 (major-
boundary + replace-never-stack). Build state unchanged: CRISPR FE + FE-5.6
DONE+verified, uncommitted. No active task — FE-6/7/8, commit, §7 TIDE wiring
are user-gated; ask before starting. End clear-safe.`
