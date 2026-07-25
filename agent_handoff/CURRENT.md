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

- **Claude:** ACTIVE @ 2026-07-25 05:27 +0000 — took over the campaign after
  Codex exhausted usage; holds this Wave 3 docs branch.
- **Codex:** STOPPED @ 2026-07-22 22:22 +0000 — usage exhausted at the exact
  Wave 3 material-approval gate. All lane worktrees clean, nothing unpushed.
- **Waves 0–2:** merged and green. Wave 1 PRs #24/#25/#23/#26, contract
  amendment #27, runtime composition #28, then repo-correctness #30 merged as
  `main@5861056`.
- **Repo correctness (#30):** pypdf 6.13.3 carried four CVEs published after
  the Wave 2 merge, and its failure had masked the npm half of the same job —
  postcss 8.5.10 and brace-expansion 5.0.7 were also vulnerable. All three
  patched. `590ca85` additionally made the bcftools licence a recorded property
  of the built binary, which was W3-BCF-01's blocking precondition.
- **Wave 3:** cards frozen, none executed. Blocked only on Steven naming exact
  card IDs. 6 of 8 named builders are unwritten, so most of Wave 3 is ungated
  code work. **Correction:** an earlier version of this file claimed no runtime
  asset destination existed. That was wrong — it read the absence of
  `/var/data/eamos/bio_assets` on this workspace box as the absence of a mount
  anywhere. The live destination is syd2's `/srv/project1/assets/runtime`,
  mounted read-only into the container, holding the 23-item /
  47,943,536,945-byte frozen tree in
  `app/backend/app/runtime-tree-manifest-syd2.json`. Reconciliation of the cards
  against that tree is in the cards doc.
- **Wave 4:** open on `agent/live/surface-truth`; PR #31 (panel fixture
  fallback) is green and awaiting merge approval. Production, provider, cloud,
  deploy, Supabase, and source-materialization state are unchanged.
- **Render:** cancelled by the founder 2026-07-25 ~04:55 UTC (Phase 4 closed).
  syd2 has been the sole serving path since the 07-17 cutover; the rollback path
  is gone by design.

## Log Edit-Lock

UNLOCKED · 2026-07-25 05:27 +0000 · Claude

## Shared File Locks

- None. Campaign lane locks are released; watcher-owned
  `agent_handoff/FROM-SWORDFISH.md` remains untouched.

## Resume Prompt

```text
# Resume prompt · 2026-07-25 05:27 +0000 · Claude Live Product Wave 4 lane
Read CURRENT.md, plans/live-product-completion/{research,spec,plan}.md, and docs/live-product-verification/wave3-approval-cards.md.
Waves 0-2 plus repo correctness are merged green through main@5861056; the eight Wave 3 cards are frozen and none is executed.
Wave 4 (agent/live/surface-truth) is the active lane: remove ordinary scientific mock/sample fallbacks and render execution/source truth across workbench, report, paper, and compare.
Start with app/web/lib/panels.ts, which returns MOCK_PANELS on any fetch failure in ordinary mode; match the thrown typed-unavailable idiom in lib/batch.ts and lib/paperVariants.ts.
Wave 3 needs BOTH exact named card IDs from Steven AND a runtime asset mount that does not exist on this host; its 6 unwritten builders are ungated code work that can proceed first.
Do not download, build, materialize, upload, mount, configure, or deploy any card until Steven names the approved card IDs exactly.
Never stage watcher-owned agent_handoff/FROM-SWORDFISH.md.
```

## Pointer

- Plan: `plans/live-product-completion/{research,spec,plan}.md`.
- Exact cards: `docs/live-product-verification/wave3-approval-cards.md`.
- Review boundary: PR #29, branch `agent/live/material-approval-cards`, card
  commit `55df2ce`, brought up to `main@5861056`.
- Merged boundaries: Wave 2 PR #28 `main@2dd181c` (run `29961634345`); repo
  correctness PR #30 `main@5861056`.
- Wave 4 lane: branch `agent/live/surface-truth`, `plan.md` Wave 4 web paths.
- Watcher-owned `agent_handoff/FROM-SWORDFISH.md` remains dirty only in the
  main checkout and was not staged or edited.

## Delta

- Froze eight individually approvable Wave 3 cards totaling about 1.673 GiB,
  with checksums/licences/bounds and explicit rollback paths; kept unavailable,
  incompatible, oversized, or licence-unclear candidates as deferred/NO-GO.
- Cleared a repo-wide CI block: three vulnerable dependencies across both audit
  halves, plus the false bcftools GPL claim that gated W3-BCF-01.
- Corrected this board's stale rows; #27 and #28 were shown unmerged.

## Next Action

- Merge PR #29 on green, then open Wave 4 on `agent/live/surface-truth`
  starting with the `panels.ts` fixture fallback. Wave 3 material execution
  still needs exact card IDs and a runtime asset destination.
