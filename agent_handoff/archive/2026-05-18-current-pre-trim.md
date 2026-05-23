# Current Agent State

## Current Objective

Keep Claude Code and direct Codex synchronized while the project moves from the
old plugin-limited Codex workflow to direct Codex sessions with verified full
workspace and network access.

Immediate practical objective: resume from the paused Eamos checkpoint without
conflicting edits or stale assumptions.

Next backend objective, when the user chooses backend work: use the global
Blueprint `design-doc`, `spec`, and `plan` skills to produce reviewable
planning artifacts for the remaining backend/API/pipeline work before any
implementation. Store those artifacts under `plans/` when that planning task
starts.

## Coordination Rules (hard — both agents, read every session)

User-mandated standing rules (2026-05-17). Breaking any of these needs the
user's explicit, per-instance OK.

1. **Never delete or overwrite the other agent's plan, handoff section, task
   brief, or `next-session-*` doc. Default-deny.** Supersede only by
   *append + archive*: move the old content to
   `agent_handoff/archive/<date>-<slug>.md`, then write the new. Editing or
   removing anything the other agent authored requires explicit user approval,
   every time.
2. **Each agent writes only its own section.** Per-agent state lives in
   `## Claude — Last Task & Resume` and `## Codex — Last Task & Resume`. You
   read the other's; you never rewrite it.
3. **Parallel mode is ON.** Claude (frontend) and Codex (backend) may run in
   separate terminals simultaneously on disjoint file scopes. Role swaps
   happen only on explicit user command.
4. **Shared files need a lock.** Before editing a shared/high-conflict file
   (see `## Shared File Locks`), claim it there; if the other agent holds it,
   defer or file a `## Cross-Agent Requests` entry. Never both editing one
   file.
5. **Contract changes are backend-led.** Frontend never edits the
   `app/frontend/src/lib/backend.ts` contract *shape* or backend schema; it
   requests the change via `## Cross-Agent Requests`.
   `test_frontend_contract.py` is the canary.
6. **No idle waiting.** If blocked on the other agent — or they ran out of
   usage/context — follow `## Idle / Usage-Exhaustion Protocol`. Never sit
   idle; never start a user-gated milestone to fill time.
7. **Everyone has a main role; swaps are explicit and written.** Default
   roles: Claude = frontend + **integration-checkpoint driver**; Codex =
   backend + **fallback driver** if Claude is out of usage/context. A role
   swap is *only* valid when (a) the user commands it and (b) it is recorded
   in `## Active Status` + the affected agent sections. No silent or
   opportunistic swaps — clean handoff = accurate notes **plus** explicit
   written ownership.
8. **Timestamp + edit-lock on every log/handoff write** (user-mandated
   2026-05-17). Shared log/handoff files — `agent_handoff/CURRENT.md`,
   `RISKS.md`, `TASKS.md`, `DECISIONS.md`, `CHANGELOG.md`, `PROGRESS.md`,
   `ROADMAP.md`, active `plans/*`:
   - **Stamp the section you edit** with real local time in the format
     `YYYY-MM-DD HH:MM ±zzzz · <agent>` (same stamp format as the resume
     prompt). Read the real clock — `Get-Date` / `date` — **never guess the
     time**. This fixes edit ordering and gives blame/forensics.
   - **Claim the log edit-lock first, release it last.** Before editing any
     of these files, set the single line under `## Log Edit-Lock` to
     `LOCKED: <agent> · <stamp> · <file/section>`; set it back to
     `UNLOCKED · <stamp>` only after you finish *and* re-read to confirm no
     concurrent change. The lock-line write itself is the first/last edit.
   - **If the lock is already held by the other agent:** fresh (≤ 20 min) →
     **STOP**, do not read-then-edit the logs, surface it to the user, and
     ask whether it is OK to proceed. Stale (> 20 min) → assume the other
     agent stopped mid-edit (see `## Idle / Usage-Exhaustion Protocol`),
     record the stale-lock takeover in your own section with a stamp, then
     proceed. This is distinct from `## Shared File Locks` (that covers
     source/contract files; this covers the log/handoff docs themselves).

## Active Status (heartbeat — set when you start and stop)

- Claude: idle @ 2026-05-17 23:47 +1000 Session 26 — done + verified: **CRISPR
  FE slice** (plans/crispr-integration.md §5 Phase A + §8 Phase C-fe), all
  `app/frontend/**` (Claude lane), mock-first on the existing `CrisprResponse`
  contract (no `backend.ts`/schema change; TIDE shape kept FE-local per Rule 5
  — complies with the open Codex→Claude mock-first request). New:
  `crispr-guide-map.ts`(+test), `crispr-sample.ts`, `crispr-tide-sample.ts`,
  `crispr/{CrisprPanel,DesignTab,GuideTrack,OutcomesTab,IndelSpectrum}.tsx`;
  edited `api.ts` (`designGuides`/`analyzeTide` mock-first), `WorkbenchShell`,
  `SidePanel` (CrisprSide), `workbench.css`. Verified: vitest **42/42** (35
  prior + 7 new guide-map), build clean, contract **40/40** (untouched),
  browser pixel-check at /workbench (Design+Outcomes, GuideTrack cut@18 ==
  unit test, ssODN 3-arm diff verified in-DOM, grouped-SVG IndelSpectrum,
  CrisprSide; fixed a panel-title that duplicated the canvas h1). Uncommitted.
  Next: user-gated (FE-6 full / FE-7/8 / commit). §6 backend = Codex M-002D
  (done); §7 TIDE backend brief filed in Cross-Agent Requests.
- Codex: idle @ 2026-05-18 12:06 +1000 · Codex - done + verified:
  gene viewer design/spec/plan drafted in `plans/gene-viewer/` from the
  supplied RPE65 brief and current Workbench/backend code. Docs only; no
  implementation, frontend edits, commit, push, stash, reset, or clean.

## Log Edit-Lock

Single mutex line for the shared log/handoff docs (see Coordination Rule 8).
Set `LOCKED: <agent> · <YYYY-MM-DD HH:MM ±zzzz> · <file/section>` before you
edit any of them; set `UNLOCKED · <stamp>` after you finish and re-read.
Fresh lock held by the other agent (≤ 20 min) → stop + ask the user. Stale
(> 20 min) → assume mid-edit abandonment, record the takeover, proceed.

UNLOCKED · 2026-05-18 12:07 +1000 · Codex (gene viewer spec/plan handoff; re-read confirmed no concurrent change)

## Shared File Locks

Claim before editing a shared/high-conflict file; release when done. Set:
`CLAUDE.md`, `CODEX.md`, `agent_handoff/README.md`, `agent_handoff/CURRENT.md`
shared sections, `CHANGELOG.md`, `PROGRESS.md`, `ROADMAP.md`,
`plans/README.md`, `app/frontend/src/lib/backend.ts`, backend schema files.

- (none held)

## Cross-Agent Requests

Append-only. Format: `[OPEN|DONE] <from>→<to> (date): <ask> · <where to deliver>`.

- [OPEN] Codex→Claude (2026-05-17): CRISPR backend plan is now in
  `plans/v2-backend.md`; while FE CRISPR work starts, keep frontend mock-first
  against the existing `CrisprResponse` shape and do not depend on additive
  fields such as `specificity_score`, `target_sequence`, or `genomic_region`
  until the user approves the backend contract change. · Deliver via
  `plans/v2-frontend.md`/FE implementation notes.
- [DONE] Claude→Codex (2026-05-17 23:47 +1000, ack of the above): CRISPR FE
  slice shipped **mock-first on the existing `CrisprResponse`/`CrisprGuide`/
  `HdrSsodn` contract only** — no additive fields used, no `backend.ts`/schema
  change, TIDE shape kept FE-local (`lib/workbench/crispr-tide-sample.ts`) per
  Rule 5. `test_frontend_contract.py` 40/40 untouched. Compliance noted in
  `plans/v2-frontend.md` FE-6 notes. No FE action needed from Codex.
- [OPEN] Claude→Codex (2026-05-17 23:47 +1000): **§7 TIDE backend brief** —
  `POST /api/v1/crispr/tide` (multipart control/edited + `cut_site_index`) +
  `CrisprTide*` schema + `backend.ts` mirror (backend-led), Brinkman-2014 NNLS
  deconvolution, shared AB1 reader with M-002E, SPROUT/inDelphi deferred
  (`predicted_available:false` → FE renders observed-only, already wired).
  Full spec: `plans/crispr-integration.md §7`. FE is mock-first against
  `crispr-tide-sample.ts` until this lands (no FE block). §6 (gRNA design
  engine) = **Codex M-002D, already done** — no brief needed. · Deliver via
  `plans/v2-backend.md` + `app/backend/**`.

## Idle / Usage-Exhaustion Protocol

If your next step is blocked on the other agent, the other agent is out of
usage/context, or you've finished your lane and the next milestone is
user-gated: do **not** idle and do **not** start a gated milestone. In your
own ownership only, take the highest-value safe work:

1. **Plan ahead.** Produce reviewable `design-doc`/`spec`/`plan` artifacts for
   upcoming milestones in your lane so later execution is mechanical. Planning
   is allowed even when implementation is gated.
2. **Harden your own tree.** Behavior-preserving refactor / lint / dead-code /
   type-safety / test-coverage, scoped strictly to your folders, fully
   revertible, no contract-shape change (the `f2de719` model).
3. **Mock-first to stay unblocked.** If blocked on the other's deliverable,
   build/verify against the mock/stub (`provider=mock`, shared contract JSON)
   so your work integrates when they return.
4. **Write the precise ask.** Put exactly what you need from the other agent
   into `## Cross-Agent Requests` so they execute on return — no round-trips.
5. **Lane-specific free time.** Claude: browser/pixel/a11y QA passes,
   visual-polish backlog, component-doc tightening. Codex: backend
   error-path/perf hardening, security review of its own surface, test
   hardening.

Never in free time: gated milestones (FE-6/7/8, M-002), the other agent's
tree, shared-contract shape, broad reformatting, commits/pushes without ask,
speculative features. Free time = de-risking + planning, not scope creep.

When **you** are about to run out: reach a verified boundary, write your own
section + archive anything superseded, leave a prioritized pickup queue, and
state in `## Cross-Agent Requests` whether the other agent is now blocked on
you and the minimal unblock.

## Integration Checkpoint

A periodic joint verification that frontend + backend still agree (run at
milestone boundaries, not mid-task).

- **Driver: Claude (default).** Fallback driver: **Codex**, only if Claude is
  out of usage/context and the user commands the swap (record it in
  `## Active Status`).
- The driver runs: `cd app/backend && python -m pytest
  tests/test_frontend_contract.py -q` (the contract canary) + a frontend
  build + a frontend↔backend smoke against the live/mock backend, then logs
  the result in its own section and flags any drift in `## Cross-Agent
  Requests` for the owning agent to fix.
- Cadence: at each completed milestone (e.g., end of an FE-5.6 unit / a
  backend milestone), or on user request. Not every task.

## Current Product Checkpoint

- Backend hardening Sessions 1 and 2 are complete and verified.
- Workbench FE-5.5 is complete and verified.
- Workbench FE-5.6 in progress: Units A (items 2,3,5), B (item 1), C
  (items 4,7) complete + verified (headless + browser), uncommitted. Units D
  (item 6 dynamic reflow, highest risk) + E (item 8 variant-render) remain.
- FE-6/FE-7/FE-8 and M-002 real-engine work should not start until the user
  explicitly chooses the next direction.

## Current Worktree State

- Branch: `checkpoint/v2-batches-2026-05-17` (created from `master`, pushed,
  tracking `origin/checkpoint/v2-batches-2026-05-17`).
- **Committed & pushed 2026-05-17:** `9a27ef0` — one comprehensive checkpoint
  of all ~3 verified batches (variant-search engine, backend hardening S1–S2,
  Workbench FE-4/5/5.5 + Codex hardening, FE-5.6 plan, agent_handoff/ +
  workflow-doc sync). 110 files, +12039 / −2862.
- **`origin/main` untouched at `e0f1763`** — checkpoint is off the default
  branch by design; open a PR when ready.
- Working tree is now **clean**. There is a real git restore point — Codex
  refactoring is low-risk (revert = `git checkout 9a27ef0 -- <path>`).
- Git identity: repo-local `user.*` = `Steveneam <steveneam@hotmail.com>`
  (was unset → git Windows auto-detect leaked
  `Steven Eamegdool <seamegdool@cmri.org.au>`). Future commits correct.
  Past-commit decision **CLOSED** (user chose "f2de719 only"): the local-only
  refactor commit was re-authored via amend → **`f2de719` is now `88a3739`,
  authored Steveneam** (same tree/content; reversible via reflog; no
  force-push). `9a27ef0` (pushed) + `e0f1763` (`origin/main` tip) intentionally
  left as old author — fix `9a27ef0`'s author at PR time via squash-merge;
  never rewrite `e0f1763`.

## Current Agent Coordination State

- Direct Codex has verified filesystem write/delete access in `E:\eamos`.
- Direct Codex has verified outbound network connectivity.
- The old "Codex only for grunt work" assumption came from earlier plugin-mode
  limitations and should not constrain future direct-Codex task assignment.
- **Parallel mode is now ON** (user-enabled 2026-05-17): Claude (frontend) and
  Codex (backend) may run simultaneously in separate terminals on disjoint
  scopes — see `## Coordination Rules` + `## Idle / Usage-Exhaustion Protocol`.

## Active Owner

Parallel mode. **Claude (frontend lane):** completed + verified FE-5.6
Units A, B, and C (Session 24, 2026-05-17 18:10 +1000) — the unified edit-hub
redesign is in; canvas selects, all editing off-canvas. FE-5.6 Units D
(dynamic reflow, highest risk) + E (variant-render) remain; resume from
`## Claude — Last Task & Resume`. **Codex (backend lane):** see
`## Codex — Last Task & Resume` + the Codex `## Active Status` line for live
state (running the approved M-002A backend slice as of this writing) — Claude
did not inspect or touch Codex's lane (disjoint scope).

Next intended Direct Codex backend flow, when assigned by the user:

1. Read `CODEX.md`, this file, `agent_handoff/RISKS.md`, `plans/v2-backend.md`,
   and `git status --short --branch`.
2. Use global Blueprint `design-doc`, then `spec`, then `plan` skills.
3. Draft reviewable backend planning artifacts under `plans/`.
4. Stop for user review before implementation.
5. Do not start FE-6/FE-7/FE-8/M-002 or change frontend UX as part of this
   backend planning flow.

### Codex task brief — "Review + refactor Claude's folders"

**Goal.** Independent review, analysis, and *behavior-preserving* refactor of
the code/docs Claude has produced so far. Improve clarity, structure, dead
code, duplication, naming, types, and consistency **without changing runtime
behavior or UX**, and surface (don't silently fix) anything that needs a
product/design decision.

**In scope (Claude-owned surface):**
- `app/frontend/src/components/workbench/**` (FE-4/5/5.5 chrome + viewer)
- `app/frontend/src/lib/workbench/**` (gene-window, codon-table, edit-state,
  sample data, tests)
- `app/frontend/src/styles/workbench.css`
- `app/frontend/src/components/report/**` (Report v2 modules)
- `app/frontend/src/lib/{api,backend,sample-report,variant-format}.ts` (+
  `variant-format.test.ts`)
- `app/frontend/src/pages/{WorkbenchPage,ReportPage}.tsx`, `App.tsx`
- `plans/v2-frontend.md`, `plans/README.md`, `agent_handoff/**`,
  `next-session` handoff docs

**Out of scope / DO NOT TOUCH:**
- `app/backend/**` (Codex's own domain — separate task, not this one)
- `/runs` legacy patient flow (`LegacyRunsApp.tsx`, run intake/sign-off) —
  **frozen**, no design changes
- `app/frontend/src/lib/backend.ts` *contract shape* — keep every field; it is
  the canary for `test_frontend_contract.py` (refactor internals only, no
  field renames/removals)
- **Do NOT implement FE-5.6.** It is planned, decisions locked, and is Claude's
  to build. Reviewing/refactoring the *current* FE-5.5 code is in scope;
  pre-empting or changing the FE-5.5 UX is not. If a refactor finding overlaps
  an FE-5.6 item, note it for Claude — don't act on it.
- No behavior/UX changes, no dependency bumps, no broad reformatting churn.

**Verify (direct Codex now has the access to run these):**
- `cd app/frontend && npx vitest run` → must stay green (24/24 + variant-format)
- `cd app/frontend && npm run build` → `tsc -b` + vite clean
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q` →
  40/40 (unchanged — proves no contract drift)
- If any gate cannot run in your environment, say so explicitly and leave it
  for Claude to run — do not report "done" on an unrun gate.

**Git discipline.** Work on `checkpoint/v2-batches-2026-05-17` (or a branch off
it). Commit the refactor as its own revertible commit(s) separate from
`9a27ef0`, `Co-Authored-By` trailer. Do not touch `origin/main`. Do not
force-push. No commits unless the work is verified.

**Handoff discipline (now a hard standing rule).** Read this file +
`agent_handoff/RISKS.md` before editing; update the "Required Post-Task Update"
block below before stopping (files changed, verification run, tests not run,
risks, recommended next step). The next session resumes from this file, not
chat memory.

**Deliverable.** A findings report (severity-ranked: structural / dead code /
duplication / type-safety / naming / doc drift), the behavior-preserving
refactor applied + verified, and anything product-shaping surfaced for Claude
+ the user — not silently changed.

## Codex refactor `f2de719` — record + Claude review

**Hash note (2026-05-17 S21):** `f2de719` was re-authored via `git commit
--amend --reset-author` (user-approved, "f2de719 only") and is now commit
**`88a3739`** — identical tree/content, author/committer
`Steveneam <steveneam@hotmail.com>`. All "f2de719" references below describe
this same commit.

**Coherence note.** Codex's refactor findings/verification originally lived in
this file's "Required Post-Task Update" block but were overwritten by Codex's
later Blueprint-skill-cleanup task update. The full original record survives at
`git show f2de719:agent_handoff/CURRENT.md`. Summary restored here so a cold
read of this file does not require git archaeology.

**`f2de719 "Refactor Workbench frontend surface"`** (on
`checkpoint/v2-batches-2026-05-17`, on top of `9a27ef0`; **committed, not
pushed** — branch ahead of origin by 1):

- Codex findings (all applied as the behavior-preserving refactor itself):
  structural split of `ToolIcon.tsx` + `viewer/zoom-config.ts` out of mixed
  modules (Fast-Refresh hygiene); removed `as never` in `EditPopoverV2`
  (typed `Base` + `isBase` guard) and `SequenceViewerV2`; dead-code removal in
  `CodonDetail` (`ROW_BP`/`posDisplay` exports, stale eslint-disable); regex
  hyphen-class cleanup in `variant-format.ts`; `ReportPage` file-level
  eslint-disable for the intentional URL-sync effect. No UX/behavior change; no
  product decision surfaced; no FE-5.6 work pre-empted.
- Codex verification: vitest 24/24, build clean, contract 40/40, lint clean.
  Not run: browser/pixel (no UX change → correctly skipped).
- **Claude independent review (Session 21):** read the full `f2de719` diff +
  grepped consumers — `ROW_BP` is CodonDetail-local, `posDisplay` consumers all
  import from `gene-window`, `presetForBaseW` is ZoomSlider-local (all removed
  exports confirmed dead). The only non-trivial logic change (EditPopoverV2
  preview → derived state) preserves observable behavior in all steady states
  and sits on code FE-5.6 Unit C rewrites anyway. **Verdict: genuinely
  behavior-preserving, safe to build FE-5.6 on.** Re-verified locally before
  starting FE-5.6: vitest 24/24, build clean.

## Files In Play

Current live coordination files:

- `agent_handoff/README.md`
- `agent_handoff/CURRENT.md`
- `agent_handoff/TASKS.md`
- `agent_handoff/DECISIONS.md`
- `agent_handoff/RISKS.md`
- `agent_handoff/WORKTREE_INVENTORY.md`
- `AGENT_HANDOFF.md` as a legacy pointer to this folder

Current project areas with major uncommitted work:

- `app/backend/**`
- `app/frontend/**`
- `plans/**`
- `README.md`
- `CHANGELOG.md`
- `PROGRESS.md`
- `ROADMAP.md`
- `.claude/**`

## Do Not Touch Without Explicit User Approval

- Checkpoint commit/push to a feature branch is **done & user-authorized**
  (`9a27ef0`). Still: no force-push, no rewriting `9a27ef0`, no pushing to
  `origin/main`.
- Do not stash. Do not reset/clean/discard.
- Do not auto-start FE-6/FE-7/FE-8 or M-002 real engines.
- **Do not implement FE-5.6** (Claude's, decisions locked) — review/refactor
  of existing FE-5.5 only.
- Do not modify shared project docs just to tidy them (doc drift → report it).

## Canonical Resume Context

Agents should read, in this order:

1. `CODEX.md` for direct Codex sessions
2. `agent_handoff/README.md`
3. `agent_handoff/CURRENT.md`
4. `agent_handoff/RISKS.md`
5. `CLAUDE.md`
6. `PROGRESS.md`
7. `CHANGELOG.md`
8. `ROADMAP.md`
9. Relevant active plan, usually `plans/v2-frontend.md` or `plans/v2-backend.md`
10. `C:\Users\seamegdool\.claude\plans\next-session-eamos-hardening.md`
11. `git status --short --branch`
12. `git diff --stat`

## Latest Verification Snapshot

Last recorded verification in project docs:

- **FE-5.6 Unit C (latest, 2026-05-17 Session 24):** `npx vitest run` 24/24,
  `npm run build` clean (`tsc -b` + vite), `pytest
  tests/test_frontend_contract.py` 40/40 (no drift). **Browser pixel-check
  DONE** (Chrome DevTools MCP, `localhost:5175/workbench`): left-click selects
  with no popover; right-click opens the cursor-anchored edit menu (clamped +
  flip-up, correct base, selection untouched); Scratchpad single/range
  summaries correct; Delete/Replace/Clear drive edits through the `viewerRef`
  seam; old `.sv-selbar` gone; undo/redo + FE-5.5 hardening intact.
- **FE-5.6 Units A/B (2026-05-17 S21/S23):** vitest 24/24, build clean,
  contract 40/40; Unit B also browser pixel-checked.
- `f2de719` (Codex refactor): vitest 24/24, build clean, contract 40/40, lint
  clean (Codex); Claude re-verified vitest 24/24 + build clean before Unit A.
- Frontend FE-5.5: `npx vitest run` 24/24, `npm run build` clean.
- Backend hardening Session 2: offline pytest 86 passed / 4 skipped.
- Frontend contract: 40/40. `test_tool_invariants.py`: 5 passed.
- Browser pixel-check for FE-5.5 surfaced the 8 FE-5.6 items (Unit A resolves
  items 2, 3, 5).
- `9a27ef0` (checkpoint) + `88a3739` (Codex refactor, ex-`f2de719`,
  re-authored) committed on `checkpoint/v2-batches-2026-05-17`; `9a27ef0`
  pushed, `88a3739` + FE-5.6 Unit A working-tree changes NOT pushed.

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (Rule 1/2).
Section last edited: 2026-05-17 23:47 +1000 · Claude Session 26.

**Task (2026-05-17 23:47 +1000 Session 26):** implemented + verified the
**CRISPR frontend slice** — `plans/crispr-integration.md` **§5 Phase A**
(Blueprint-1 gRNA design) **+ §8 Phase C-fe** (Blueprint-2 Outcomes scaffold).
All work is `app/frontend/**` (Claude lane), **mock-first** on the existing
`CrisprResponse` contract — no `backend.ts`/Pydantic shape change.

**§5 Phase A — Design.** `CrisprPanel` (Design|Outcomes sub-tabs via `.seg`,
locked decision §2.4 — rail stays 5 tools); `DesignTab` (form → contract
fields `cas`/`strand_filter`/`off_target_tolerance`; target-window ±bp is a
labelled UI affordance, honestly noted as engine-gated; gRNA `.tool-table`
with teal-spacer/amber-PAM accent split, ★ + tinted recommended row =
lowest off-target, score-good/mid/bad, Default/On↓/Off↑ sort `.seg`,
min-on-target range filter; ssODN `.ssodn-vis` block); `GuideTrack` (the
blueprint's row-hover ribbon — `mapGuide` locates spacer+PAM+predicted blunt
cut on the **ssODN reference arm**, not the gene-window).

**Design interpretation surfaced (not silently chosen):** the plan said map
the ribbon "from the gene-window context around `cut_position`", but the
`/api/v1/crispr` fixture's `cut_position` (24–31) is a **design-template-local
offset, not an RPE65 CDS coord** (window is c.217–339) — mapping onto the
gene-window would place guides wrong. I instead locate the spacer in the
ssODN `reference_arm` the guides were scored against (exactly how the
blueprint dashboard works off its submitted sequence). Documented in
`crispr-guide-map.ts` header; reconciling `cut_position` semantics is already
in the §6 Codex brief.

**§8 Phase C-fe — Outcomes.** `OutcomesTab` (2 trace inputs + cut-index +
Run, mock-first `analyzeTide`); `IndelSpectrum` (hand-rolled grouped SVG
Observed-vs-AI bar chart, PhyloP-track precedent, observed-only fallback when
`predicted_available:false`). TIDE response shape is **FE-local**
(`crispr-tide-sample.ts`) per Rule 5 — the canonical contract is backend-led
and moves into `backend.ts` when Codex ships §7.

**Verification (all green):**
- `npx vitest run` → **42/42** (35 prior + 7 new pure `crispr-guide-map`
  cases: revComp involution, the 3 fixture guides' spacer/PAM/cut on the
  reference arm, not-located + edge-clamp).
- `npm run build` → clean (`tsc -b` + vite; only the pre-existing >500 kB
  chunk advisory; PowerShell wraps that stderr as a RemoteException — build
  emitted `dist/`).
- `python -m pytest tests/test_frontend_contract.py -q` → **40/40**
  (contract untouched — proves no FE-side drift; satisfies the open
  Codex→Claude mock-first request).
- **Browser pixel-check** (Chrome DevTools MCP, `localhost:5176/workbench`
  CRISPR): table renders 3 guides, ★ on guide 1 (off 16.2); GuideTrack
  "cut at base 18" == the unit test; ssODN diff verified **in-DOM**
  (Variant: 1 `seq-hl-pam` G at the pathogenic site; Repair: `seq-hl-silent`
  T + `seq-hl-correct` A — derived generically, no hard-coded positions);
  Outcomes IndelSpectrum 16 obs + 16 pred bars, callouts 69% / R² 0.93 /
  cut 100 / "AI + observed"; sub-tabs switch; viewer still above; no
  h-scroll. Fixed a panel `<h2>` that duplicated the canvas `<h1>` — panel
  head now reads "Guide design & repair" / "Editing outcomes" per sub-tab.

**Files (uncommitted working tree, all `app/frontend/**`):**
- New: `lib/workbench/crispr-guide-map.ts` (+`.test.ts`),
  `lib/workbench/crispr-sample.ts`, `lib/workbench/crispr-tide-sample.ts`,
  `components/workbench/crispr/{CrisprPanel,DesignTab,GuideTrack,OutcomesTab,
  IndelSpectrum}.tsx`.
- Edited: `lib/api.ts` (`designGuides`/`analyzeTide`, mock-first),
  `components/workbench/WorkbenchShell.tsx` (CrisprPanel in the crispr slot
  + `CRISPR_CDNA`), `components/workbench/SidePanel.tsx` (`CrisprSide` branch),
  `styles/workbench.css` (CRISPR block — reuses tool-panel/tool-table/
  ssodn-vis/.seg; adds guide-table accents, `.guide-track`, `.indel-chart`,
  `.sw` swatch, `.side-chip`).
- Handoff/plan: `plans/v2-frontend.md` (FE-6 CRISPR note + Codex-req
  compliance), `plans/crispr-integration.md §9` (status), this section +
  Claude heartbeat + `## Cross-Agent Requests`,
  `~/.claude/plans/next-session-eamos.md`.

**Prior, still-valid context:** FE-5.6 (all 8 items, Units A–E) DONE +
verified in Session 25 — still uncommitted. This CRISPR slice builds on that
working tree + Codex's `88a3739`. Codex completed backend **M-002D**
(local deterministic SpCas9 provider, the §6 work) in parallel @ 23:44 —
disjoint scope, Claude did not touch `app/backend/**`.

**Coordination:** Codex held a fresh Log Edit-Lock @ 23:31 (M-002D); per
Rule 8 Claude **STOPPED and asked the user**; user chose "wait, then
finalize". Codex released @ 23:45 / idle @ 23:44; Claude then claimed the
lock @ 23:47 and finalized. Per the user's choice the redundant §6 brief was
**not** filed (Codex already shipped M-002D); only the **§7 TIDE** brief was
filed in `## Cross-Agent Requests` (pointer to `plans/crispr-integration.md
§7`). The open Codex→Claude mock-first request is satisfied + acknowledged.

**Next (all user-gated — do not auto-start):** full FE-6 (Primer panel /
remaining CRISPR polish) · FE-7/FE-8 · commit/push · §7 TIDE FE wiring once
Codex lands the endpoint. An Integration Checkpoint (Claude default driver)
can run now that a milestone is complete.

**Commit/push:** none this session — CRISPR FE + FE-5.6 + rule/handoff edits
all **uncommitted**; no commit/push/stash/reset/clean without explicit user
ask. Git unchanged: `checkpoint/v2-batches-2026-05-17` ahead of origin by 1
(`88a3739` unpushed, ex-`f2de719`, re-authored Steveneam); `9a27ef0`/
`e0f1763` left old-author by design. Worktree also carries Codex's
uncommitted backend M-002A/B/C/D (disjoint).

**Dev server:** Vite is on **5176** (this session; 5173–5175 are stale from
prior sessions, Vite file-watches so all serve current source). Background
ids `bfaffvcqy` (5176 dev) + `b9y316kdx` (wait timer) are this session;
harmless, kill for clean ports if desired.

**Clear-safe: yes.** Nothing mid-edit; Log Edit-Lock claimed @ 23:47 and
released below after re-read; state fully captured here + in
`~/.claude/plans/next-session-eamos.md`.

**Resume prompt** (deliberately a thin pointer — the detail lives in the
files it names; do not re-encode protocol/lineage here, that is the bloat
this format fixes):
`# Resume prompt · 2026-05-18 11:18 +1000 · Claude Session 26 (CRISPR FE done)
Eamos. Read agent_handoff/CURRENT.md (Coordination Rules + ## Log Edit-Lock +
## Claude — Last Task & Resume + ## Cross-Agent Requests), agent_handoff/
RISKS.md, ~/.claude/plans/next-session-eamos.md, then git status --short
--branch. Those carry the full state + the lock/lane/parallel-mode protocol —
do not re-derive it here. Delta: CRISPR FE slice (crispr-integration.md §5
Phase A + §8 Phase C-fe) DONE + verified (vitest 42/42 · build · contract
40/40 · pixel-check), uncommitted; Codex M-002D (§6) done. No active task —
FE-6 Primer / FE-7/8 / commit / §7 TIDE FE-wiring are user-gated; ask before
starting. End clear-safe (Safe-to-clear line + fresh stamped resume prompt).`

## Codex — Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (Rule 1/2).
Section last edited: 2026-05-18 12:06 +1000 · Codex.

**Latest Codex update (2026-05-18 12:06 +1000 · Codex):** stepped back on the
Workbench gene viewer and drafted reviewable planning artifacts for a
gene-agnostic, backend-owned viewer payload. The draft treats RPE65 c.260A>G
as the first live acceptance example while keeping the service design generic.
It explicitly includes a reference/control versus variant-applied allele mode,
defaulting to reference/control.

**Planning artifacts created:**
- `plans/gene-viewer/design.md`
- `plans/gene-viewer/spec.md`
- `plans/gene-viewer/plan.md`

**Key planning decisions captured:**
- Add a new `POST /api/v1/viewer` contract instead of embedding viewer data in
  primer/CRISPR/alignment responses.
- Build a backend `GeneViewerService` that resolves transcript structure,
  source-backed reference/control sequence, variant projection, allele overlay,
  tracks, and provenance.
- Preserve RPE65 fixture/offline behavior, but do not hard-code RPE65 in live
  service logic beyond a temporary canonical-transcript fallback consistent
  with the existing `CANONICAL_TRANSCRIPTS` pattern.
- Defer PostgreSQL/Redis/Celery/full ingestion until the viewer contract and
  coordinate layer are proven.
- Keep primer/CRISPR/alignment contracts unchanged until the viewer endpoint is
  implemented and the user approves a follow-up sequence-basis contract change.

**Files changed by this update:**
- `plans/gene-viewer/design.md`
- `plans/gene-viewer/spec.md`
- `plans/gene-viewer/plan.md`
- `agent_handoff/CURRENT.md`
- `agent_handoff/TASKS.md`
- `agent_handoff/RISKS.md`

**Verification run for this update:**
- `git diff --check -- plans/gene-viewer agent_handoff\CURRENT.md agent_handoff\TASKS.md agent_handoff\RISKS.md`
  -> no whitespace errors; git reported existing LF-to-CRLF warnings only.

**Tests not run for this update:** backend tests, frontend tests/build, and
browser checks were not run because this was documentation/planning only and no
app code or contract files were changed.

**Risks/blockers for this update:**
- Implementation remains user-gated. The current viewer still uses frontend
  RPE65 sample data until the plan is approved and executed.
- The new viewer contract will eventually require backend-led TypeScript mirror
  changes and contract canary updates.
- Reverse-strand coordinate handling and RefSeq/Ensembl transcript aliasing are
  the highest-risk implementation details.

**Commit/push state for this update:** no commit, push, stash, reset, clean, or
force-push. Branch remains `checkpoint/v2-batches-2026-05-17`, ahead of origin
by 1 (`88a3739`, ex-`f2de719`, re-authored Steveneam), with the intentionally
dirty worktree.

**Recommended next step:** user review of `plans/gene-viewer/spec.md` and
`plans/gene-viewer/plan.md`. If approved, start Task GV-001 backend-only
schemas + fixture, then GV-002 coordinate/window builder before any frontend
switch.

**Clear-safe:** yes after the Log Edit-Lock is released; no implementation,
tests, or provider command is mid-flight.

**Latest resume prompt:**
`# Resume prompt · 2026-05-18 12:06 +1000 · Codex gene viewer spec/plan
Resume Eamos from CODEX.md + agent_handoff/CURRENT.md. Read CURRENT Codex/Locks/Requests, agent_handoff/RISKS.md, plans/gene-viewer/{design.md,spec.md,plan.md}, and git status --short --branch.
State: checkpoint/v2-batches-2026-05-17 is ahead 1; worktree dirty by design; Codex M-002A-D and backend Ruff/Black pass are done; Claude FE CRISPR mock-first is done; new gene viewer design/spec/plan are drafted only.
Next: wait for user review/approval. If approved, start GV-001 backend-only viewer schemas + RPE65 fixture, then GV-002 coordinate/window builder.
Constraints: no implementation until approved; no frontend/Claude edits unless explicitly assigned; no commit/push/stash/reset/clean; claim Log Edit-Lock before shared docs; keep prompts short and put details in CURRENT.`

**Previous Codex update (2026-05-18 11:23 +1000 · Codex):** completed the
requested backend-only refactor/lint pass after M-002D. This was deliberately
kept behavior-preserving: public API/schema shapes are unchanged, fixture mode
is unchanged, and no frontend files were touched.

**Refactor/lint work completed:**
- Installed `ruff` and `black` into the user Python environment so the existing
  backend `pyproject.toml` lint/format config can run.
- Fixed Ruff findings: explicit `__all__` for package re-export modules,
  removed an unused `SearchVariantWrite` import, removed no-op f-string
  prefixes in `variant_decoder.py`, and marked `tests/conftest.py`'s
  intentional post-`sys.path` imports with `# noqa: E402`.
- Ran Black across backend `app/` and `tests/` with `--target-version py310`;
  this reformatted existing backend code only.

**Files changed by this update:**
- Logical lint fixes: `app/backend/app/agents/__init__.py`,
  `app/backend/app/schemas/__init__.py`,
  `app/backend/app/services/__init__.py`,
  `app/backend/app/repos/search_repo.py`,
  `app/backend/app/services/variant_decoder.py`,
  `app/backend/tests/conftest.py`.
- Formatting pass: backend Python files under `app/backend/app/**` and
  `app/backend/tests/**` touched by Black.
- No frontend files, schema contract changes, commits, pushes, stashes,
  resets, or cleans.

**Verification run for this update:**
- `cd app/backend && python -m ruff check app tests` -> all checks passed.
- `cd app/backend && python -m black --check --target-version py310 app tests`
  -> 91 files left unchanged.
- `cd app/backend && python -m compileall -q app tests` -> passed.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`
  -> 40 passed.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  -> 120 passed / 4 skipped.
- `git diff --check -- app/backend` -> no whitespace errors; git reported
  existing LF-to-CRLF warnings only.

**Tests not run for this update:** frontend tests/build and browser checks were
not run because the task was backend-only and made no frontend changes.

**Risks/blockers for this update:**
- The backend diff is broad because Black was run over the backend folder; the
  semantic edits are the Ruff fixes listed above.
- Existing M-002C/M-002D provider limitations and the corrupt filesystem shell
  risk still apply; see `agent_handoff/RISKS.md`.

**Commit/push state for this update:** no commit, push, stash, reset, clean, or
force-push. Branch remains `checkpoint/v2-batches-2026-05-17`, ahead of origin
by 1 (`88a3739`, ex-`f2de719`, re-authored Steveneam), with the intentionally
dirty worktree.

**Recommended next step:** take the break. On return, wait for explicit user
direction; likely choices are review/commit, backend M-002E/M-002I planning,
or Claude-owned frontend follow-up.

**Clear-safe:** yes after the Log Edit-Lock is released; no implementation,
tests, or provider command is mid-flight.

**Previous resume prompt:**
`# Resume prompt · 2026-05-18 11:23 +1000 · Codex backend lint/refactor
Resume Eamos from CODEX.md + agent_handoff/CURRENT.md. Read CURRENT Codex/Locks/Requests, RISKS.md, and git status --short --branch.
State: checkpoint/v2-batches-2026-05-17 is ahead 1; worktree dirty by design; Codex M-002A-D and backend Ruff/Black pass are done; Claude FE CRISPR mock-first is done.
Next: wait for explicit user direction (review/commit, FE follow-up, M-002E/M-002I planning, or another scoped task).
Constraints: no frontend/Claude edits; no commit/push/stash/reset/clean; claim Log Edit-Lock before shared docs; keep prompts short and put details in CURRENT.`

**Previous Codex update (2026-05-17 23:44 +1000 · Codex):** implemented the
approved backend-only **M-002D local deterministic SpCas9 CRISPR provider**.
Fixture mode remains unchanged; no frontend files or schema/contract fields
were touched.

**Implementation made in this update:**
- Added `app/backend/app/services/crispr_design.py` with deterministic SpCas9
  `NGG` PAM discovery on plus/minus strands, 21-nt `spacer + first PAM base`
  context capture, Hsu/MIT-style local off-target scoring, a labelled
  on-target heuristic, and source-backed ssODN generation from existing
  context/ref/alt SNV data.
- Wired `WorkbenchDesignService.design_guides()` to use the CRISPR provider
  only when `USE_REAL_APIS=true`; `USE_REAL_APIS=false` still returns
  `crispr_rpe65.json` byte-equivalent.
- Added `CRISPR_PROVIDER=local_deterministic` config/env documentation.
- Preserved the current `CrisprGuide.off_target_score` lower-is-better
  contract by mapping `100 - hsu_specificity_score`; no `specificity_score`,
  `target_sequence`, or `genomic_region` fields were added.
- Real-mode unsupported `cas` values return structured
  `422 workbench_unsupported_input:cas`; too-short sequence context returns
  `422 workbench_unsupported_input:sequence_too_short`; no eligible PAM returns
  HTTP 200 with an empty guide list.

**Files changed by this update:**
- `app/backend/app/services/crispr_design.py`
- `app/backend/app/services/workbench_design.py`
- `app/backend/app/core/config.py`
- `app/backend/.env.example`
- `app/backend/tests/test_crispr_design.py`
- `app/backend/tests/test_workbench_api.py`
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`, `agent_handoff/RISKS.md`,
  `agent_handoff/TASKS.md` - Codex/task/risk status only.

**Verification run for this update:**
- `cd app/backend && python -m pytest tests/test_crispr_design.py tests/test_workbench_api.py -q`
  -> 27 passed.
- `cd app/backend && python -m pytest tests/test_frontend_contract.py -q`
  -> 40 passed.
- `cd app/backend && python -m pytest tests/test_sequence_context.py -q`
  -> 7 passed.
- `cd app/backend && python -m pytest tests/test_workbench_api.py tests/test_sequence_context.py -q`
  -> 27 passed.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  -> 120 passed / 4 skipped.
- `git diff --check -- app/backend/.env.example app/backend/app/core/config.py app/backend/app/services/workbench_design.py app/backend/app/services/crispr_design.py app/backend/tests/test_workbench_api.py app/backend/tests/test_crispr_design.py`
  -> no whitespace errors; PowerShell reported only existing LF-to-CRLF git
  warnings for tracked files.
- `rg -n "[ \t]+$" app/backend/app/services/crispr_design.py app/backend/tests/test_crispr_design.py app/backend/tests/test_workbench_api.py app/backend/app/services/workbench_design.py app/backend/app/core/config.py app/backend/.env.example`
  -> no matches.

**Tests not run for this update:** frontend tests/build and browser checks were
not run because this was backend-only and no frontend or contract schema files
changed. No live genome-wide CRISPR/Bowtie/BWA smoke was run because M-002D
intentionally implements only deterministic in-context scoring.

**Risks/blockers for this update:**
- On-target scoring is a transparent heuristic, not DeepHF; no trained DeepHF
  weights/model provenance are present.
- Off-target scoring is deterministic in-context Hsu/MIT-style scoring only,
  not genome-wide Bowtie/BWA specificity.
- Raw sequence/genomic-region request fields, PostgreSQL persistence, and
  M-002I post-CRISPR TIDE analytics remain separate approvals.
- The existing corrupt filesystem shell risk remains: run `chkdsk E: /f` at a
  restart with E: dismounted.

**Commit/push state for this update:** no commit, push, stash, reset, clean, or
force-push. Branch remains `checkpoint/v2-batches-2026-05-17`, ahead of origin
by 1 (`88a3739`, ex-`f2de719`, re-authored Steveneam), with the intentionally
dirty worktree.

**Recommended next step:** user review. Claude can build FE-6 against the
existing CRISPR contract if assigned; backend follow-ups should be separately
approved (M-002E alignment/AB1, M-002I TIDE analytics, DeepHF, Bowtie/BWA,
raw sequence/genomic-region fields, or persistence).

**Clear-safe:** yes after the Log Edit-Lock is released; no implementation,
tests, or provider command is mid-flight.

**Latest resume prompt:**
`# Resume prompt · 2026-05-17 23:44 +1000 · Codex M-002D CRISPR provider
Resume Eamos from CODEX.md and agent_handoff/CURRENT.md. Read CODEX.md,
agent_handoff/CURRENT.md (Coordination Rules incl. Rule 8 + Log Edit-Lock,
Codex section, Locks, Requests), agent_handoff/RISKS.md, plans/v2-backend.md,
and git status --short --branch first. Current state: branch
checkpoint/v2-batches-2026-05-17 is ahead of origin by 1 (88a3739,
ex-f2de719, re-authored Steveneam); worktree intentionally dirty with Claude
frontend/log-rule/FE-5.6/FE-6-start work and Codex backend M-002A/M-002B/
M-002C/M-002D plus planning changes. Latest Codex result: backend-only
M-002D local deterministic SpCas9 provider implemented behind /api/v1/crispr
real mode. Fixture mode is unchanged; no frontend or schema/contract expansion.
It scans SpCas9 NGG PAMs on both strands, scores local in-context off-targets
with Hsu/MIT-style math, maps off_target_score as lower-is-better risk, labels
on-target as heuristic/not DeepHF, and generates ssODN only from existing
context/ref/alt data. Verification passed: CRISPR+Workbench tests 27/27,
frontend contract 40/40, sequence context 7/7, full backend 120 passed / 4
skipped; no frontend tests/build/browser checks run. Next task: wait for user
review or explicit approval for a follow-up such as M-002E alignment/AB1,
M-002I TIDE analytics, DeepHF, Bowtie/BWA genome-wide off-targets, raw
sequence/genomic-region fields, persistence, or Claude FE-6 work against the
current contract. Constraints: Codex lane remains app/backend/** +
plans/v2-backend.md plus Codex handoff/risk/task sections; do not touch
frontend or Claude sections; do not start FE-6/FE-7/FE-8 or M-002I/follow-up
implementation without explicit user approval; do not commit/push/stash/reset/
clean; carry forward corrupt filesystem shell risk requiring chkdsk E: /f at
restart; before any shared log/plan edit claim Log Edit-Lock with a real date
stamp and release it after re-reading.`

**Previous Codex update (2026-05-17 23:18 +1000 · Codex):** ingested the
supplied CRISPR design and post-CRISPR analytics materials and integrated them
into a reviewable backend plan only. No M-002D/M-002I implementation was
started.

**Planning decisions captured:**
- M-002D recommended first provider is local deterministic SpCas9 guide design
  behind the existing Workbench service boundary, not external CRISPOR and not
  random-weight DeepHF inference.
- First slice keeps fixture mode byte-equivalent and preserves the current
  `CrisprGuide.off_target_score` lower-is-better contract by mapping it from
  internal `hsu_specificity_score`.
- DeepHF trained inference, genome-wide Bowtie/BWA off-target enumeration,
  raw sequence/genomic-coordinate request fields, PostgreSQL persistence, and
  post-CRISPR TIDE analytics are explicit follow-up approvals, not hidden
  requirements in the first slice.
- Blueprint 2 was split out as future M-002I TIDE/outcome analytics and should
  share AB1 parsing with M-002E alignment work.

**Files changed by this update:**
- `plans/v2-backend.md` - expanded M-002D plan and added future M-002I.
- `agent_handoff/RISKS.md` - added CRISPR provider planning risks.
- `agent_handoff/TASKS.md` - marked M-002D/M-002I as planned but gated.
- `agent_handoff/CURRENT.md` - Codex handoff, active status, and
  cross-agent request only.

**Verification run for this update:**
- `git diff --check -- plans/v2-backend.md agent_handoff/CURRENT.md agent_handoff/RISKS.md agent_handoff/TASKS.md`
  -> no whitespace errors; PowerShell reported only existing LF-to-CRLF git
  warnings.

**Tests not run for this update:** backend tests, frontend tests/build, and
browser checks were not run because this was documentation/planning only and
no app code or contract code changed.

**Risks/blockers for this update:**
- M-002D/M-002I implementation remains gated until the user approves the
  backend plan.
- DeepHF weights/model provenance are missing; do not claim DeepHF output
  until sourced and reviewed.
- Genome-wide CRISPR off-target enumeration still requires approved local
  FASTA/Bowtie/BWA assets and runtime decisions.
- The existing corrupt filesystem shell risk remains: run `chkdsk E: /f` at a
  restart with E: dismounted.

**Commit/push state for this update:** no commit, push, stash, reset, clean, or
force-push. Branch remains `checkpoint/v2-batches-2026-05-17`, ahead of origin
by 1 (`88a3739`, ex-`f2de719`, re-authored Steveneam), with the intentionally
dirty worktree.

**Recommended next step:** user reviews `plans/v2-backend.md` M-002D/M-002I.
If approved, implement M-002D as the backend-only deterministic SpCas9 provider
slice. If not approved, revise the plan before code.

**Clear-safe:** yes after the Log Edit-Lock is released; no implementation,
tests, or provider command is mid-flight.

**Latest resume prompt:**
`# Resume prompt · 2026-05-17 23:18 +1000 · Codex M-002D/M-002I CRISPR planning
Resume Eamos from CODEX.md and agent_handoff/CURRENT.md. Read CODEX.md,
agent_handoff/CURRENT.md (Coordination Rules incl. Rule 8 + Log Edit-Lock,
Codex section, Locks, Requests), agent_handoff/RISKS.md, plans/v2-backend.md,
and git status --short --branch first. Current state: branch
checkpoint/v2-batches-2026-05-17 is ahead of origin by 1 (88a3739,
ex-f2de719, re-authored Steveneam); worktree intentionally dirty with Claude
frontend/log-rule/FE-5.6/FE-6-start work and Codex backend M-002A/M-002B/
M-002C plus planning changes. Latest Codex result: supplied CRISPR design and
post-CRISPR analytics materials were ingested into plans/v2-backend.md only:
M-002D now recommends a local deterministic SpCas9 provider first; DeepHF,
Bowtie/BWA genome-wide off-targets, raw sequence/genomic-region contract
fields, PostgreSQL persistence, and M-002I TIDE analytics remain follow-up
approvals. Verification: git diff --check on edited planning/handoff docs only;
no backend/frontend tests were run because no app code changed. Next task:
wait for user review/approval of M-002D/M-002I; if approved, implement M-002D
backend-only. Constraints: Codex lane remains app/backend/** +
plans/v2-backend.md plus Codex handoff/risk/task sections; do not touch
frontend or Claude sections; do not start FE-6/FE-7/FE-8 or M-002D/M-002I
implementation without explicit user approval; do not commit/push/stash/reset/
clean; carry forward corrupt filesystem shell risk requiring chkdsk E: /f at
restart; before any shared log/plan edit claim Log Edit-Lock with a real date
stamp and release it after re-reading.`

**Latest Codex update (2026-05-17 23:07 +1000 · Codex):** installed and
configured the approved local UCSC `isPcr` assets for the optional M-002C
whole-genome primer specificity path, without changing the default provider.
Clear-safe, done. Defaults remain unchanged: `PRIMER_SPECIFICITY_PROVIDER` is
still `template` unless explicitly overridden.

**Asset installation/configuration in this update:**
- Downloaded official UCSC Linux `isPcr` from
  `https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/blat/isPcr` to
  `app/backend/data/bio_assets/bin/isPcr`.
- Downloaded official UCSC `hg38.2bit` from
  `https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.2bit` to
  `app/backend/data/bio_assets/genomes/hg38.2bit`.
- Downloaded UCSC `md5sum.txt`; verified `hg38.2bit` MD5
  `dcc3ea27079aa6dc3f9deccd7275e0f8`.
- Configured local ignored `app/backend/.env` paths:
  `UCSC_ISPCR_BINARY_PATH=./data/bio_assets/bin/isPcr` and
  `UCSC_ISPCR_HG38_PATH=./data/bio_assets/genomes/hg38.2bit`, while keeping
  `PRIMER_SPECIFICITY_PROVIDER=template`.
- Confirmed `app/backend/data/` is git-ignored, so the large assets do not
  appear in `git status`.

**Live local isPcr smoke result:** attempted a provider-level smoke with the
user-validated RPE65 exon 4 primer pair 3 and `PRIMER_SPECIFICITY_PROVIDER`
path configuration. The provider found the configured local assets, then failed
before executing the screen with structured `503 workbench_provider_unavailable`
caused by native Windows `OSError [WinError 193] %1 is not a valid Win32
application`. `file` identifies the downloaded UCSC executable as `ELF 64-bit
LSB ... GNU/Linux`; this host has `wsl.exe` only as a stub and no WSL
distribution installed. Therefore the live whole-genome `isPcr` smoke remains
blocked by runtime platform, not by missing assets.

**Files changed by this update:**
- `app/backend/.env` — local ignored configuration only.
- Local ignored assets under `app/backend/data/bio_assets/**`.
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`, `agent_handoff/RISKS.md` — Codex/risk status
  only.

**Verification run for this update:**
- `cd app/backend && python -m pytest tests/test_workbench_api.py -q`
  → 16 passed.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  → 109 passed / 4 skipped.
- `git status --short --branch` confirmed the downloaded assets remain ignored
  and do not add new tracked/untracked status noise.

**Tests not run for this update:** frontend tests/build and browser checks were
not run because this was backend-only and no frontend/contract files changed.
A successful live local `isPcr` whole-genome smoke was not possible on this
native Windows host without WSL/Linux or a native Windows build/wrapper for
UCSC `isPcr`.

**Risks/blockers for this update:**
- To complete the live local whole-genome smoke on this machine, install a WSL
  distribution or provide another Linux/native execution wrapper for UCSC
  `isPcr`. I did not install WSL because that is a system-level change beyond
  the approved asset download and may require admin/restart.
- Local UCSC `isPcr` remains not NCBI Primer-BLAST and still lacks SNP masking,
  dimer/hairpin analysis, and ARMS mismatch placement.
- UCSC/Kent BLAT-family command-line executables have licensing constraints
  for commercial use; confirm distribution/deployment comfort before bundling
  binaries.

**Commit/push state for this update:** no commit, push, stash, reset, clean, or
force-push. Branch remains `checkpoint/v2-batches-2026-05-17`, ahead of origin
by 1 (`88a3739`, ex-`f2de719`, re-authored Steveneam), with the intentionally
dirty worktree.

**Recommended next step:** clear this session and start a new session for the
CRISPR provider planning discussion. Do not start M-002D implementation until
the user provides the CRISPR materials and explicitly approves the provider
plan.

**Clear-safe:** yes. Local assets are installed/configured; no implementation
or verification command is mid-flight. Log Edit-Lock released below after
re-read.

**Latest resume prompt:**
`# Resume prompt · 2026-05-17 23:07 +1000 · Codex M-002C local isPcr assets
Resume Eamos from CODEX.md and agent_handoff/CURRENT.md. Read CODEX.md,
agent_handoff/CURRENT.md (Coordination Rules incl. Rule 8 + Log Edit-Lock,
Codex section, Locks, Requests), agent_handoff/RISKS.md, plans/v2-backend.md,
and git status --short --branch first. Current state: branch
checkpoint/v2-batches-2026-05-17 is ahead of origin by 1 (88a3739,
ex-f2de719, re-authored Steveneam); worktree intentionally dirty with Claude
frontend/log-rule/FE-5.6 work and Codex backend M-002A/M-002B/M-002C changes.
Last Codex result: local UCSC isPcr assets are installed/configured under
ignored app/backend/data/bio_assets, hg38.2bit MD5 verified, app/backend/.env
points to those local assets, and defaults remain PRIMER_SPECIFICITY_PROVIDER=template.
Opt-in live isPcr smoke was attempted but platform-blocked on native Windows:
official UCSC isPcr is a Linux ELF and this host has no installed WSL
distribution, producing WinError 193 / structured 503 provider_unavailable.
Verification passed: Workbench tests 16/16 and full backend suite 109 passed /
4 skipped. Next task: start a new session for M-002D CRISPR provider planning
after the user provides materials; do not implement M-002D+ until the user
approves the plan. Constraints: Codex lane is app/backend/** +
plans/v2-backend.md only; do not touch frontend or Claude sections; do not
start FE-6/FE-7/FE-8 or M-002D+ without explicit user approval; do not
commit/push/stash/reset/clean; carry forward the corrupt filesystem shell risk
requiring chkdsk E: /f at restart; before any shared log/plan edit claim Log
Edit-Lock with a real date stamp and release it after re-reading.`

**Latest Codex update (2026-05-17 22:43 +1000 · Codex):** reviewed the
supplied primer references and implemented a backend-only **M-002C follow-up:
optional local UCSC `isPcr` whole-genome primer specificity provider**.
Clear-safe, done. Defaults remain unchanged: real Primer3 still uses the
in-template screen unless `PRIMER_SPECIFICITY_PROVIDER=ucsc_ispcr` is
explicitly configured.

**Integration decision:** use the standalone UCSC/Kent `isPcr` command shape
as the backend-owned local provider, not the online UCSC `hgPcr` CGI. The
dropped infrastructure note was directionally useful, but its download URLs
were placeholders and the runtime code needed to fit the existing sync
Workbench service boundary.

**Implementation made in this update:**
- Added opt-in backend settings:
  `primer_specificity_provider`, `ucsc_ispcr_binary_path`,
  `ucsc_ispcr_hg38_path`, `ucsc_ispcr_timeout_seconds`,
  `ucsc_ispcr_min_perfect`, and `ucsc_ispcr_min_good`.
- Added `LocalIsPcrSpecificityProvider` behind the existing
  `PrimerSpecificityProvider` protocol in
  `app/backend/app/services/workbench_design.py`.
- The provider builds a no-shell `isPcr` command using a stdin 3-column query,
  parses FASTA-style products, counts whole-genome products into
  `specificity_hits`, and marks `intended_hits` when a product overlaps the
  resolved target coordinate.
- Recommendation still requires exactly one product and exactly one
  target-spanning product.
- Missing local `isPcr` binary or `hg38.2bit` assets return structured
  `503 workbench_provider_unavailable`; provider failures/timeouts return
  structured `503 workbench_provider_failed:*`.
- Added `.env.example` keys documenting the opt-in provider and local asset
  paths. No binary or genome was downloaded into the repo.

**Files changed by this update:**
- `app/backend/app/core/config.py`
- `app/backend/app/services/workbench_design.py`
- `app/backend/tests/test_workbench_api.py`
- `app/backend/.env.example`
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`, `agent_handoff/TASKS.md`,
  `agent_handoff/RISKS.md` — Codex/task/risk status only.

**Verification run for this update:**
- `cd app/backend && python -m pytest tests/test_workbench_api.py -q`
  → 16 passed.
- `cd app/backend && python -m pytest tests/test_workbench_api.py tests/test_sequence_context.py tests/test_frontend_contract.py -q`
  → 63 passed.
- `cd app/backend && python -m pytest tests/test_lookup_normalize.py tests/test_tool_invariants.py -q`
  → 9 passed.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  → 109 passed / 4 skipped.

**Tests not run for this update:** frontend tests/build and browser checks were
not run because this was backend-only and no frontend/contract files changed.
A live local `isPcr` smoke was not run because no UCSC `isPcr` binary or
`hg38.2bit` asset was downloaded/configured in this workspace.

**Risks/blockers for this update:**
- `PRIMER_SPECIFICITY_PROVIDER=ucsc_ispcr` is a real whole-genome path only
  after local assets are installed at the configured paths; default `template`
  mode remains the previous exact-template screen.
- Local `isPcr` is not NCBI Primer-BLAST, does not add SNP masking,
  dimer/hairpin analysis, or ARMS mismatch placement, and should be presented
  as a UCSC whole-genome in-silico PCR screen only.
- UCSC/Kent BLAT-family command-line executables have licensing constraints
  for commercial use; confirm distribution/deployment comfort before bundling
  binaries.

**Commit/push state for this update:** no commit, push, stash, reset, or clean.
Branch remains `checkpoint/v2-batches-2026-05-17`, ahead of origin by 1
(`88a3739`, ex-`f2de719`, re-authored Steveneam), with uncommitted worktree
changes.

**Recommended next step:** install/configure local UCSC `isPcr` + `hg38.2bit`
outside the repo if the user wants a live opt-in smoke, or pause backend work
while Claude continues FE-5.6. M-002D CRISPR provider choice remains gated.

**Clear-safe:** yes. Log Edit-Lock released; no implementation is mid-flight.

**Latest resume prompt:**
`# Resume prompt · 2026-05-17 22:43 +1000 · Codex M-002C local isPcr specificity
Resume Eamos from CODEX.md and agent_handoff/CURRENT.md. Read CODEX.md,
agent_handoff/CURRENT.md (Coordination Rules incl. Rule 8 + Log Edit-Lock,
Codex section, Locks, Requests), agent_handoff/RISKS.md, plans/v2-backend.md,
and git status --short --branch first. Current state: branch
checkpoint/v2-batches-2026-05-17 is ahead of origin by 1 (88a3739,
ex-f2de719, re-authored Steveneam); worktree intentionally dirty with Claude
frontend/log-rule/FE-5.6 work and Codex backend M-002A/M-002B/M-002C changes.
Last Codex result: M-002A sequence context boundary, M-002B Workbench service
extraction, M-002C real Primer3 primer provider + exact-template specificity
screen, and an opt-in local UCSC isPcr whole-genome specificity provider are
implemented backend-only. Defaults remain PRIMER_SPECIFICITY_PROVIDER=template;
set PRIMER_SPECIFICITY_PROVIDER=ucsc_ispcr plus UCSC_ISPCR_BINARY_PATH and
UCSC_ISPCR_HG38_PATH to use the local whole-genome screen. Verification passed:
Workbench tests 16/16, Workbench+sequence+contract 63/63, lookup/tool canaries
9/9, full backend suite 109 passed / 4 skipped. No live local isPcr smoke was
run because the binary/genome assets are not installed. Next task: if approved,
install/configure local UCSC isPcr assets and run an opt-in smoke, choose
M-002D CRISPR provider design, or pause backend work while Claude continues
FE-5.6. Constraints: Codex lane is app/backend/** + plans/v2-backend.md only;
do not touch frontend or Claude sections; do not start FE-6/FE-7/FE-8 or
M-002D+ without explicit user approval; do not commit/push/stash/reset/clean;
carry forward the corrupt filesystem shell risk requiring chkdsk E: /f at
restart; before any shared log/plan edit claim Log Edit-Lock with a real date
stamp and release it after re-reading.`

**Prior Codex task (2026-05-17 19:11 +1000):** implemented backend-only **M-002C primer specificity
screening** after user approval — **clear-safe, done.** This extends the real
Primer3 provider; no frontend files, Claude-owned sections, commits, pushes,
stashes, resets, or cleans.

**Primer context used:** user supplied RPE65 gDNA primer notes showing NCBI
Primer-BLAST whole-genome specificity workflow and lab-validated Sanger pairs:
exon 4 pair 3 (`GCTGTACGGATTGCTCCTGT` /
`ACACCAATTGCAGGAAAGCAT`) and pair 1 (`CCTTCAGGTTCATCCGCACT` /
`AGAGGCAATCAGTGCAGTCC`). A direct online UCSC `hgPcr` call was tested from
this environment and returned bot-protection, so this slice does **not** claim
whole-genome specificity.

**Implementation made:**
- Added `TemplateAmpliconSpecificityProvider` in
  `app/backend/app/services/workbench_design.py`.
- Each real Primer3 pair is now exact-matched against the resolved design
  template by pairing the forward primer with the reverse primer's reverse
  complement, counting products inside the requested product-size range, and
  checking whether products span the queried base.
- Real-mode `specificity_hits` now reflects exact resolved-template amplicons
  instead of the previous unchecked `0`; pair notes explicitly state this is
  not genome-wide Primer-BLAST/UCSC specificity.
- Recommendation now prefers the first pair with exactly one target-spanning
  template product.
- Added tests for Primer3 mapping with a specificity provider, recommendation
  ranking, and the two user-validated RPE65 Sanger primer pairs.
- Updated `plans/v2-backend.md`, `agent_handoff/TASKS.md`, and
  `agent_handoff/RISKS.md` with the new status and limitations.

**Files changed by this continuation:**
- `app/backend/app/services/workbench_design.py`
- `app/backend/tests/test_workbench_api.py`
- `plans/v2-backend.md`
- `agent_handoff/CURRENT.md`, `agent_handoff/TASKS.md`,
  `agent_handoff/RISKS.md` — Codex/task/risk status only.

Existing uncommitted Codex M-002A/M-002B/M-002C files remain in the worktree:
`app/backend/app/services/sequence_context.py`, `app/backend/app/main.py`,
`app/backend/app/api/routes/workbench.py`, `app/backend/requirements.txt`, and
`app/backend/tests/test_sequence_context.py`.

**Verification run:**
- `cd app/backend && python -m pytest tests/test_workbench_api.py -q`
  → 13 passed.
- `cd app/backend && python -m pytest tests/test_workbench_api.py tests/test_sequence_context.py -q`
  → 20 passed.
- `cd app/backend && python -m pytest tests/test_workbench_api.py tests/test_frontend_contract.py tests/test_sequence_context.py -q`
  → 60 passed.
- `cd app/backend && python -m pytest tests/ --disable-warnings`
  → 106 passed / 4 skipped.
- Opt-in live/engine smoke with `USE_REAL_APIS=true` through the real
  `/api/v1/primer` route and a 500-1000 bp Sanger range → HTTP 200, 3 RPE65
  pairs; all had exact template `specificity_hits = 1`. First pair:
  `CTAGCACTGTGTCCCACCTG` / `AGCACACCATGTCCGGAATT`, product size 792.

**Tests not run:** frontend tests/build and browser checks were not run because
this was backend-only and no frontend/contract files changed.

**Risks/blockers:**
- M-002D and later real-engine slices remain user-gated; do not start M-002D,
  FE-6, FE-7, or FE-8 without explicit user direction.
- Current real primer output still does not run genome-wide specificity,
  Primer-BLAST, UCSC/BLAT whole-genome in-silico PCR, SNP masking,
  dimer/hairpin analysis, or ARMS-specific mismatch placement.
- Direct online UCSC `hgPcr` automation is blocked from this environment by a
  bot-protection page; future whole-genome specificity should use local
  BLAT/isPcr or BLAST+ infrastructure, or another approved provider/API.
- `primer3-py` / Primer3 has GPL-family licensing; confirm distribution comfort
  before treating it as a production dependency.
- Open Codex-owned risk remains: corrupt filesystem shell
  `.claude/skills/scripts/skills/planner/quality_reviewer_bad/` needs
  `chkdsk E: /f` at a restart with E: dismounted. Not acted on.
- Worktree remains intentionally dirty with Claude frontend/log-rule/FE-5.6
  work plus Codex backend/planning changes. Do not commit/push/stash/reset/
  clean unless the user asks.

**Commit/push state:** no commit, push, stash, reset, or clean. Branch remains
`checkpoint/v2-batches-2026-05-17`, ahead of origin by 1 (`88a3739`,
ex-`f2de719`, re-authored Steveneam), with uncommitted worktree changes.

**Recommended next step:** user reviews M-002C specificity. If approved, choose
whether to pursue a true whole-genome specificity provider design
(local BLAT/isPcr or BLAST+), M-002D CRISPR provider choice, or pause backend
work while Claude continues FE-5.6.

**Clear-safe:** yes. Log Edit-Lock released; no implementation is mid-flight.

**Resume prompt:**
`# Resume prompt · 2026-05-17 19:11 +1000 · Codex M-002C primer specificity
Resume Eamos from CODEX.md and agent_handoff/CURRENT.md. Read CODEX.md,
agent_handoff/CURRENT.md (Coordination Rules incl. Rule 8 + Log Edit-Lock,
Codex section, Locks, Requests), agent_handoff/RISKS.md, plans/v2-backend.md,
and git status --short --branch first. Current state: branch
checkpoint/v2-batches-2026-05-17 is ahead of origin by 1 (88a3739,
ex-f2de719, re-authored Steveneam); worktree intentionally dirty with Claude
frontend/log-rule/FE-5.6 work and Codex backend M-002A/M-002B/M-002C changes.
Last Codex result: M-002A sequence context boundary, M-002B Workbench service
extraction, M-002C real Primer3 primer provider, and M-002C primer specificity
screen are implemented backend-only. Specificity screen exact-matches Primer3
pairs against the resolved design template, sets template-level
specificity_hits, and prefers the first single target-spanning product; it is
not genome-wide Primer-BLAST/UCSC specificity. Verification passed: Workbench
tests 13/13, Workbench+sequence 20/20, Workbench+contract+sequence 60/60, full
backend suite 106 passed / 4 skipped, and opt-in real /api/v1/primer smoke
returned HTTP 200 with 3 RPE65 500-1000 bp pairs all at exact-template
specificity_hits=1. Next task: wait for user review/approval; if approved,
choose true whole-genome primer specificity provider design, M-002D CRISPR
provider choice, or pause backend work while Claude continues FE-5.6.
Constraints: Codex lane is app/backend/** + plans/v2-backend.md only; do not
touch frontend or Claude sections; do not start FE-6/FE-7/FE-8 or M-002D+
without explicit user approval; do not commit/push/stash/reset/clean; carry
forward the corrupt filesystem shell risk requiring chkdsk E: /f at restart;
before any shared log/plan edit claim Log Edit-Lock with a real date stamp and
release it after re-reading.`
