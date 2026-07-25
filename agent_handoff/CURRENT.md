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
- **Wave 4:** PR #31 merged (`7605ffff`) — `/compare` panel paths now fail
  closed. Remaining slices listed in the wiring plan Phase 6.
- **Licence determination (2026-07-25):** Eamos is research/free/non-profit.
  Cleared ten registry records + two Wave 3 NO-GOs, incl. UCSC isPcr, REVEL,
  ESM-1b, PrimateAI-3D, SpliceAI, CADD. OMIM and PanelApp still need their own
  registration/agreement. **New binding constraint is syd2 disk** (34 G free vs
  ~65 GB newly permitted), so bounded MANE slices are the default.
  Production, provider, cloud, deploy, Supabase, and source-materialization
  state are unchanged; no `license_status` has been flipped yet.
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
# Resume prompt · 2026-07-25 06:05 +0000 · Claude research-unblock wiring
Read CURRENT.md, plans/research-unblock-and-wiring/plan.md, plans/primer-specificity-engine/plan.md, and docs/live-product-verification/free-access-licence-review.md.
Eamos is for research, free, and non-profit (Steven, 2026-07-25). That answered the entity AND diagnostic-use questions and cleared ten registry records plus two Wave 3 NO-GOs. Start Phase 1 of the wiring plan without asking; it is bookkeeping and needs no gate.
The constraint has MOVED: licences no longer bind, syd2 disk does. 34 G free against ~65 GB of newly-permitted predictors, so bounded MANE-scoped slices are the default and CADD/SpliceAI must be sliced. Reuse eamos_compact_index_build / eamos_esm1b_mane_context_build; whole-genome would need a founder-gated disk resize.
Primer engine is already built and Route A is now expected: accept UCSC research terms, drop the isPcr binary at bio_assets/bin/isPcr, flip primer_specificity_provider. hg38.2bit is already mounted at exactly the configured path. Zero application code.
Apply for OMIM academic access early; it has lead time and gates InterVar.
Owed from the prior session: browser evidence for PR #31's panel loading/unavailable states; the Wave 4 lane cannot close without it.
The determination clears licences, NOT the action gates. Do not download, build, materialize, upload, mount, configure, or deploy until Steven names exact card IDs.
Never stage watcher-owned agent_handoff/FROM-SWORDFISH.md.
```

## Pointer

- Next-session master plan: `plans/research-unblock-and-wiring/plan.md`.
- Primer engine plan: `plans/primer-specificity-engine/plan.md`.
- Licence determination: `docs/live-product-verification/free-access-licence-review.md`.
- Campaign plan: `plans/live-product-completion/{research,spec,plan}.md`.
- Exact cards + reconciliation:
  `docs/live-product-verification/wave3-approval-cards.md`.
- Mounted-asset authority: `app/backend/app/runtime-tree-manifest-syd2.json`.
- Wave 4 lane: branch `agent/live/surface-truth`, `plan.md` Wave 4 web paths.
- Watcher-owned `agent_handoff/FROM-SWORDFISH.md` remains dirty only in the
  main checkout and was not staged or edited.

## Delta

- Cleared a repo-wide CI block: three vulnerable dependencies across both audit
  halves (pypdf's failure had been masking the npm half), plus the false
  bcftools GPL claim that gated W3-BCF-01.
- Opened Wave 4 and removed four fixture fallbacks from the `/compare` panel
  paths, including one unhandled rejection that pinned a chip permanently.
- Checked the Wave 3 cards against the live syd2 tree for the first time: two
  are already materialized in whole or part, and one NO-GO contradicts an
  approved mounted asset. Corrected my own earlier wrong claim that no runtime
  asset destination existed.
- Planned the primer specificity engine: already built, blocked only on an
  isPcr licence, with a public-domain route that avoids the spend.

## Next Action

- Start `plans/research-unblock-and-wiring/plan.md` Phase 1: record the research
  determination per registry record, split the isPcr NO-GO row, and apply for
  OMIM academic access. Then Phase 2 (primer engine, zero code). Capture the
  browser evidence still owed by PR #31.
