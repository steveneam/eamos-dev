# Archived verbatim — Claude `## Claude — Last Task & Resume` section

Archived 2026-05-24 01:15 +1000 · Claude (Rule 1/9), before replacing with the
BE↔FE cross-check + integration state. Prior content (the Vite→Next.js migration
narrative, last edited 2026-05-23 18:51 +1000) follows verbatim.

---

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 2).
Section last edited: 2026-05-23 18:51 +1000 · Claude. Prior 2026-05-19 section
(/runs auth + AlphaMissense removal + /report audit fixes) archived verbatim →
`agent_handoff/archive/2026-05-23-claude-section-pre-nextjs.md` (Rule 1/9).
Full incremental detail + gotchas in `~/.claude/plans/next-session-eamos.md`;
migration design-doc in `plans/v2-nextjs-migration/design.md`.

**Session 2026-05-23 — Vite→Next.js migration STARTED + COMPLETED + verified
(landing + Variant Evidence Report only).**

Per user "proceed". Built a NEW Next.js (App Router) app at **`app/web/`** — a
**parallel** dir so the Vite `app/frontend/` stays intact for the parked
Workbench + frozen `/runs`. Ported landing (`/`) and the Variant Evidence
Report (`/report`) **pixel-faithful and design-agnostic** (the emerald
"Lifestream" redesign + landing mock are a separate later effort).

- **What:** scaffold (next.config.mjs `/api/*`→:8000 rewrite, tsconfig,
  postcss/Tailwind v4, layout, globals.css ported verbatim, icon.svg) + 28
  in-scope files copied verbatim + 6 App-Router edits (`lib/api.ts` lookup
  subset, `ModePill`/`LandingClient`/`ReportClient` on `next/link`+
  `next/navigation`, two route files with `<Suspense>` around `useSearchParams`).
- **Next 16, NOT 15 — user-ratified 2026-05-23.** Next 15.5 won't build on the
  IT Node 24 (`SyntaxError` on a trivial app); Next 16.2.6 builds clean, App
  Router identical, ported code byte-identical.
- **Verified:** `cd app/web && npm run build` clean (compile + TS + prerender
  `/`,`/report`,`/_not-found`); browser (`next start`) — `/` and
  `/report?demo=1` render identical to Vite. Server stopped, no orphan.
- **`strict: false`** in app/web/tsconfig.json to match the Vite app's actual
  non-strict TS (verbatim code compiles identically); flip to strict later.
- **Untouched:** `app/frontend/**`, the contract canary's `backend.ts`, `/runs`,
  AlphaMissense, Codex's backend lane. `app/web/lib/backend.ts` is a hand-kept
  mirror (see the Cross-Agent Request above).

**Carry-forward (uncommitted, Claude lane):** all prior verified work (GV-005/6,
FE-6 Primer/CRISPR, FE-5.6, /runs-auth, AlphaMissense removal, /report audit
fixes — see archive) PLUS this session's `app/web/**` Next.js app +
`plans/v2-nextjs-migration/design.md` (both untracked). Nothing committed.

**Next (all gated — user direction):** await landing mock + brand/scope/
content-realism decisions → emerald redesign on the app/web skeleton · mirror
Codex's additive report contracts into app/web/lib/backend.ts + render new
sections (mind the dual backend.ts) · strict-TS hardening pass · cutover
(make app/web canonical) — later. `/runs`, AlphaMissense, Workbench: do not
touch (on hold).

**Resume prompt:**
`# Resume prompt · 2026-05-23 18:52 +1000 · Claude (Vite→Next.js migration DONE+verified — break)
Eamos. Read ~/.claude/plans/next-session-eamos.md (full state), then
agent_handoff/README.md, agent_handoff/CURRENT.md (## Claude + Active Status +
Locks + Cross-Agent Requests), agent_handoff/DECISIONS.md, agent_handoff/RISKS.md,
agent_handoff/on_hold/register.md, plans/v2-nextjs-migration/design.md, then
git status --short --branch.
Delta: STARTED+COMPLETED the Vite→Next.js migration. NEW parallel app app/web/
(App Router) — landing + Variant Evidence Report ported pixel-faithful,
design-agnostic; Vite app/frontend untouched (Workbench+/runs still there).
Build clean + browser-verified. On Next 16 (user-ratified; 15.5 won't build on
IT Node 24). app/web has its OWN backend.ts mirror (canary guards only the Vite
copy). CURRENT.md synced this session. Next: await landing mock + brand/scope
decisions → emerald "Lifestream" redesign on the app/web skeleton; mirror
Codex's new report contracts into app/web. Do NOT touch /runs, AlphaMissense,
parked Workbench. FE Vite checkpoint = 205eaae. End clear-safe.`
