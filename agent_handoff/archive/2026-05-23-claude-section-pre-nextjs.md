# Archived verbatim — `## Claude — Last Task & Resume` (pre-Next.js-migration)

Archived 2026-05-23 18:51 +1000 · Claude, per README Hard Rule 1/9, before
replacing the CURRENT.md Claude section with the Vite→Next.js migration state.
Verbatim copy of the 2026-05-19 section follows.

---

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 2).
Section last edited: 2026-05-19 13:59 +1000 · Claude. Prior GV-005/006
section archived verbatim →
`agent_handoff/archive/2026-05-19-claude-section-pre-runs-auth-am.md`
(Rule 1/9); incremental detail + gotchas in
`~/.claude/plans/next-session-eamos.md`.

**Session 2026-05-19 (post-GV) — two user-directed deliverables, both
DONE + verified. GV-005/006 remain done (prior section archived).**

**(1) Legacy `/runs` auto demo-session auth wiring — DONE + verified.**
Codex RP-001 made `/reports/upload` + all `/runs/*` (run/review/approve/
drop/chat/pdf) require a bearer token; FE `api.ts` sent none → entire
patient-report pipeline was 401 in-browser (`/report` + Workbench were
**never** affected — `/api/v1/lookup` is unauthed). User picked the
**auto demo session** approach. `api.ts`: added `ensureToken()`/
`provisionToken()`/`authedFetch()` — transparently logs into a fixed demo
account (bootstraps via `/auth/register` on a fresh DB, 401-self-heals),
attaches `Authorization: Bearer` to the gated calls only; non-gated calls
untouched. PDF preview converted from `<object data=buildRunPdfUrl>` to an
authed `fetchRunPdfBlob` → object URL in `LegacyRunsApp` (a header can't
ride an `<object src>`). Also removed genuinely-stale legacy copy: Franklin
(competitor, excluded) outbound link + "No login required" + Franklin from
the `/runs` source line. Verified: vitest 73/73, build clean, contract
40/40 (untouched — no `backend.ts` edit). **Browser smoke** `/runs`:
login 401→register 201→**upload 201, runs 200, pdf 200** (were 401);
authed blob PDF preview renders inline (PluginObject).

**(2) AlphaMissense removed from landing + variant-report UI — DONE +
verified. User decision: ON HOLD until explicit user approval (assets
kept, not cancelled).** Render-filtered (reversible): `InSilicoGrid` +
`EvidenceTable` drop AlphaMissense; `VariantHeader` sample stat removed;
`sources.ts` 6→5 (drops landing POWERED BY + report loading skeleton);
landing copy (`LandingPage` hero, `FeaturesGrid` ×3, `HowItWorks`) "six
databases/6 live/six tabs" → "five"; `sample-report.ts` consensus prose
de-enumerated (kept AM cards/rows as assets). **Contract/schemas/fixtures
NOT touched** (`backend.ts`/`schemas/run.py` `'AlphaMissense'` literal
intact — on hold, reversible). Verified: vitest 73/73, build clean.
Browser: `/report` (live) + `/` landing AM-free + internally consistent.
**Residual → Codex (filed):** live `/report` `consensus_note` prose still
names AlphaMissense (`lookup_v2_modules.json`, backend lane).

**(3) Two `/report` audit fixes — DONE + verified (user-approved).**
`EvidenceTable` got a recursive `formatValue` — nested arrays of objects
(PubMed/litvar2 `articles`) now render `N items` and scalar arrays join
cleanly (no more `[object Object]`; ClinVar `conditions` reads as a list).
ReportPage Card-3 `meta` "live · last refreshed 2 min ago" (false — every
row is "fixture") → honest `in-silico · per-source detail · ACMG`. Verified
vitest 73/73, build clean, browser-confirmed on live `/report`.

**(4) Cleanup:** `E:\eamos_nm_broken_DELETE_AFTER_REBOOT` deleted (user
confirmed post-reboot) — no longer a carry-forward.

**Naming convention (user-mandated 2026-05-19 — see DECISIONS):** never use
bare "report". **Variant Evidence Report** = `/report` = `ReportPage` =
`POST /api/v1/lookup` (unauthed) = the **active focus**. **Patient Report
Pipeline** = `/runs` = `LegacyRunsApp` = PDF→review (auth-gated) = **ON
HOLD**; no further `/runs` work by Claude *or* Codex until the user says so
(the auth wiring already shipped is complete — leave it, don't extend).

**Carry-forward (uncommitted, Claude lane):** GV-005/006 + FE-6 Primer +
CRISPR FE + FE-5.6 + this session's /runs-auth + AlphaMissense removal +
2 `/report` audit fixes — all verified. Detail in
`~/.claude/plans/next-session-eamos.md`.

**Next (all gated — explicit user direction):** variant-evidence-report
(`/report`) work as directed · re-enable AlphaMissense (blocked on user
approval) · commit the Claude-lane checkpoint (gate lifted; mixed worktree
→ ask) · FE-7/8 · §7 TIDE FE wiring when Codex ships `/api/v1/crispr/tide`.
Patient report pipeline (`/runs`): **do not touch** (on hold).

**Resume prompt:**
`# Resume prompt · 2026-05-19 14:11 +1000 · Claude (session DONE+verified — break)
Eamos. Read agent_handoff/README.md (protocol), agent_handoff/CURRENT.md
(## Claude + Locks + Requests + DECISIONS: AlphaMissense-on-hold + 2026-05-19
naming/patient-pipeline-hold), agent_handoff/RISKS.md,
~/.claude/plans/next-session-eamos.md, then git status --short --branch.
Delta: /runs auto demo-session auth wiring + AlphaMissense removed from
landing/variant-report UI (on hold, assets kept) + 2 /report audit fixes
(EvidenceTable [object Object]→readable, Card-3 false-freshness meta→honest)
+ broken-nm dir deleted — all DONE+verified (vitest 73/73, build clean,
browser-confirmed live /report). Naming locked: active = variant evidence
report (/report); patient report pipeline (/runs) ON HOLD, do not touch.
Next (all gated): /report work as directed / commit checkpoint / FE-7/8.
Stop any dev server before /clear. End clear-safe.`
