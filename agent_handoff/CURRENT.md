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
# Resume prompt · 2026-07-25 05:52 +0000 · Claude primer engine + Wave 4
Read CURRENT.md, plans/primer-specificity-engine/plan.md, plans/live-product-completion/{research,spec,plan}.md, and docs/live-product-verification/wave3-approval-cards.md.
Steven named the primer specificity engine as the next product need; its plan is the first file above and Phase 1 there is ungated, so start it without asking.
Key finding to trust: the primer engine is already built (Primer3, template specificity, SNP masking, the whole-genome provider seam, scope disclosure, preflight) and dbSNP plus hg38.2bit are already mounted on syd2. Only the isPcr binary is missing, and that is a commercial-licence question, not engineering.
Phase 0 is a founder gate: get a real UCSC quote, then put Route A (licence isPcr) against Route B (add a public-domain blastn provider, recommended) and let Steven pick.
Owed from the prior session: browser evidence for the panel loading/unavailable states in PR #31; the Wave 4 lane cannot close without it.
Wave 4 continues on agent/live/surface-truth after that: useReportClient fixture labelling, CompareClient sample-vcf, workbench sample modules.
Do not download, build, materialize, upload, mount, configure, or deploy any Wave 3 card until Steven names the approved card IDs exactly.
Never stage watcher-owned agent_handoff/FROM-SWORDFISH.md.
```

## Pointer

- Primer engine plan: `plans/primer-specificity-engine/plan.md`.
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

- Start `plans/primer-specificity-engine/plan.md` Phase 1 (ungated), and get
  the UCSC quote so Phase 0's route choice can go to Steven with a real number.
  Capture the browser evidence still owed by PR #31.
