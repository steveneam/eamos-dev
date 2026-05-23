# Archived verbatim — Claude `CURRENT.md` section prior to GV-005/006 replace

Archived 2026-05-19 09:38 +1000 · Claude (README Hard Rule 1/9: append+archive
before replacing the `## Claude — Last Task & Resume` narrative at a major
boundary). Superseded by the GV-005/GV-006 done+verified section. The FE-6
Primer detail also lives in `~/.claude/plans/next-session-eamos.md`.

---

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 2).
Section last edited: 2026-05-18 20:19 +1000 · Claude. Prior workflow-
restructure section archived →
`agent_handoff/archive/2026-05-18-claude-section-pre-gitpolicy.md`; the
intervening git-policy/memory/FE-6-in-progress detail is fully in
`~/.claude/plans/next-session-eamos.md` (Rule 1: nothing lost).

**FE-6 Primer Phase A — DONE + verified (2026-05-18, user-approved,
`plans/primer-integration.md §5`).** Mock-first on the frozen
`POST /api/v1/primer` contract — zero contract/schema edits. New:
`index.css` (added `--elev-*`/`--dur-*`/`--ease-*` tokens + global
reduced-motion guard — were absent), `lib/workbench/primer-sample.ts`,
`primer-metrics.ts` (+`primer-metrics.test.ts`),
`components/workbench/primer/PrimerPanel.tsx` + `PrimerResultCard.tsx`
(canonical 3-layer progressive-disclosure card). Edited: `lib/api.ts`
(`designPrimers`), `WorkbenchShell.tsx` (wired + surgical `CRISPR_CDNA`→
`QUERY_CDNA`), `SidePanel.tsx` (`PrimerSide`), `styles/workbench.css`
(Primer block; elevation/motion via tokens only). Verified: **vitest
53/53** (+11 primer-metrics), **contract 40/40** (untouched, no FE drift),
**build clean** (51 s; chunk advisory only), DESIGN.md-conformance grep
(no ad-hoc shadow/transition; reduced-motion guard present; no emoji —
`★` is text glyph), **browser pixel-check** at `/workbench` Primer tab
(badges §5.1 correct: #1 Specific+recommended+teal-tint+first, #2 Thermo
warning ΔTm 2.6, #3 Off-target risk; honest loading → feed; 3-layer
disclosure collapsed by default; viewer visible above; clinical aesthetic).
Also done earlier this session: git commit-gate lifted (RISKS.md + Current
State) and memory hygiene (own `~/.claude` surface).

**Build-env incident (resolved):** 3 orphaned vite dev servers (prior
sessions) had corrupted `node_modules`; killed them, `npm ci` (recovered via
folder-rename — node_modules_broken moved to
`E:\eamos_nm_broken_DELETE_AFTER_REBOOT`, delete after a reboot). Root-cause
rule saved to memory: stop dev servers before `/clear`. The dev server I
started for the pixel-check was stopped; temp debug files cleaned.

**Carry-forward (uncommitted):** FE-6 Primer + CRISPR FE slice + FE-5.6 (all
verified). Gotchas in `~/.claude/plans/next-session-eamos.md` (incl. new:
CSS comments must not contain `*/`; Tailwind v4 Lightning CSS is strict).

**Next (gated):** commit the checkpoint (Claude gate lifted — ask still wise
for the mixed worktree) · FE-7/8 · §7 TIDE FE wiring once Codex ships
`POST /api/v1/crispr/tide` · §6 Phase-B is now filed in Cross-Agent Requests.

**Resume prompt:**
`# Resume prompt · 2026-05-18 20:19 +1000 · Claude (FE-6 Primer Phase A DONE+verified)
Eamos. Read agent_handoff/README.md (protocol), agent_handoff/CURRENT.md
(## Claude + Locks + Requests), agent_handoff/RISKS.md (Dirty Worktree = git
policy), ~/.claude/plans/next-session-eamos.md, then git status --short
--branch. Delta: FE-6 Primer Phase A DONE+verified (vitest 53/53, contract
40/40, build clean, pixel-check); §6 Phase-B Codex brief filed; node_modules
recovered (delete E:\eamos_nm_broken_DELETE_AFTER_REBOOT after a reboot).
Next (all gated): commit checkpoint / FE-7/8 / §7 TIDE wiring when Codex
ships /api/v1/crispr/tide. Stop any dev server before /clear. End clear-safe.`
