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
- **Codex:** STOPPED CLEAR-SAFE @ 2026-07-22 15:10 +0000 — Task F,
  Product Workflow Lane C, and the landing variant-search slice are complete.
- **Product Workflow V1:** serial contract, B, and C are integrated. Steven
  approved Task F's filled exact card; `user_library_document` and
  `product_workflow_runs` applied to `eamos-dev` as remote ledger entries
  `20260722144613` and `20260722144619`. Exact metadata, grants, RLS, advisors,
  rollback-scoped two-owner isolation, and zero residual rows all verified.
- **Product integration:** Lane C PR #17 merged as `0d52e11`; its post-merge CI
  is green. Lanes D/E remain pending and unlaunched; D needs a fresh named-lane
  approval and E remains downstream of D.
- **Landing:** PR #19 merged as `c6f500f` (head `db8d2fd`) under Steven's explicit
  approval. Eamos now presents as next-generation variant search across clinical
  sources, the 11-engine in-silico catalog, traceable score releases/status, and
  version-pinned ACMG/AMP criteria. The founder photo is no longer rendered; its
  asset remains on disk. The FAQ tracks forthcoming SVC v4 without labelling the
  active ruleset v4.
- **Landing verification:** 223 web tests, TypeScript, lint, build, web boundary,
  and the responsive browser audit passed. Browser coverage spanned 360–1920 px;
  LCP was 220 ms and CLS 0.0003. PR checks/Vercel and post-merge `main` CI run
  `29931752433` passed, including immutable-image pull-back. Production deployment
  `5557845525` succeeded and `https://eamos-dev.vercel.app/` serves the new title
  and hero copy without the founder-image reference.
- **Phase 3 / Render:** Phase 3 is closed. The 13:33 UTC public end sample and
  Swordfish's independent 14:21 UTC syd2 host/container sample are green: exact
  digest and 23-file/47,943,536,945-byte tree, no restart/5xx/429/OOM/cgroup
  pressure since recovery, unchanged hardening, and healthy headroom. Phase 4
  may retire the Render rollback; no Render disk or service was deleted here.
- **Evidence expansion:** Phases 0-6 are complete. Source acquisition or
  materialization, live providers, new-ruleset activation, and Phase 7 remain
  held behind their existing gates.

## Log Edit-Lock

UNLOCKED · 2026-07-22 15:10 +0000 · Codex

## Shared File Locks

- None.

## Resume Prompt

```text
# Resume prompt · 2026-07-22 15:10 +0000 · Codex post-landing checkpoint
Read CURRENT.md, COORDINATION.md, and plans/product-workflow-integration/{plan,spec}.md first.
Task F is applied and fully verified; its sanitized receipt is in docs/db/supabase-inventory.md.
Product Workflow A/B/C are integrated; PR #17 and post-merge CI are green.
Landing PR #19 merged as c6f500f; main CI 29931752433 and Production deployment 5557845525 are green.
The live Vercel alias serves the new variant-search title/hero and no founder-image reference.
Lanes D/E remain pending; D is the next serial lane and E depends on D.
Before launching D, present its exact named-lane ownership/contract/verification card and get fresh Steven approval.
Do not call the active ACMG ruleset v4 before final review/activation.
No deploy/cloud/provider/source/Render-retirement/Phase-7 action is authorized.
Preserve watcher-owned FROM-SWORDFISH.md.
```

## Pointer

- Product workflow board: `COORDINATION.md`; plan:
  `plans/product-workflow-integration/`; Lane C merge: PR #17 / `0d52e11`.
- Task F durable receipt: `docs/db/supabase-inventory.md`; exact runbook:
  `docs/architecture-consistency-gate/task-f-supabase-production-readiness-runbook.md`.
- Landing merge: PR #19 / `c6f500f`; copy surfaces:
  `app/web/components/landing/`; metadata: `app/web/app/layout.tsx`; browser
  contract: `scripts/eamos-capture-landing-features.mjs`.
- ACMG/SVC v4 activation boundary: `plans/evidence-source-expansion/`.
- Phase-3c evidence contract: `docs/deployment/render-to-syd2-phase3.md`.
- Never edit or stage watcher-owned `agent_handoff/FROM-SWORDFISH.md`.

## Delta

- Task F created the three reviewed account-owned workflow/library tables only;
  it did not mutate Storage/source assets, provider/env state, or Phase 7.
- The two-principal verification ran inside a rolled-back transaction and left
  every new table empty. Security advisors remain clear.
- Product Workflow V1 A/B/C are integrated; D/E are the next planned lanes but
  require Steven's fresh named-lane launch approval.
- The Impeccable-guided landing pass preserved the warm-paper reading-instrument
  identity while shifting the information hierarchy from generic evidence
  workspace to variant search, versioned predictors, and standards readiness.
- The landing update changed copy, metadata, and its executable browser contract
  only. It did not change predictor wiring, score data, ACMG rules, or the founder
  image asset.
- Phase 3 remains closed on independent evidence. No Render deletion, deploy,
  provider/source mutation, or Phase 7 action occurred beyond Vercel's normal
  merge-triggered Production deployment.

## Next Action

- If Steven resumes Product Workflow V1, present Lane D's exact single-lane
  launch card from the frozen plan and stop for fresh approval before launching
  it. Keep E downstream and do not widen into cloud/provider/Phase-7 work.
