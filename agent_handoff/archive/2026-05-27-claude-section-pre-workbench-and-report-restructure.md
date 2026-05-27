# Archive: prior Claude section (verbatim) before 2026-05-27 12:45 +1000 rewrite

Archived per README Hard Rule 1 (append + archive) before the Claude
section in `agent_handoff/CURRENT.md` was replaced with the Workbench
pass-2 slice 1 + viewer UX + chrome diet + scratchpad + chevron-left
restructure + report restructure + copy-to-Excel TSV summary
(7 commits `248552a..9910431`, swept up to origin by Codex's
`f00d1c0` bundle push).

Source: `agent_handoff/CURRENT.md` lines 1157–1208 immediately prior
to the rewrite.

---

## Claude — Last Task & Resume

Owner-written by **Claude only**. Codex: read, never rewrite (README Rule 1/2).
Section last edited: 2026-05-25 03:05 +1000 · Claude. Prior section (eamos.com.au
go-live night) is preserved in git history + `~/.claude/plans/next-session-eamos.md`.
Full incremental detail in the next-session doc (sections "2026-05-25 later 1..5").

**Session 2026-05-25 — large /report + landing FE pass + stealth (all pushed + verified).**

Branch `checkpoint/v2-batches-2026-05-17`, local==origin at `b7fc9ca`. All Claude-lane,
`app/web` only, Vercel auto-deploys, each verified on `eamos-dev.vercel.app`:
- `d1c3a2a` trials/pubs display rules (5 + View-more, coloured ClinicalTrials status
  pills RECRUITING/NOT_YET/ACTIVE_NOT, live publications pagination via
  `/api/v1/lookup/publications`, honest `snippet_status`, PubMed search link).
- `5448ba3` pricing collapsed to ONE landing surface; **`/pricing` page removed**
  (Individual/Team toggle + enterprise card moved to landing, cumulative
  "Everything in … plus:" leads, CTAs to `/checkout`). `app/web` `SearchShell.tsx` now unused.
- `9c11b91`/`7146d4f`/`1989b44` mobile swipe carousels for the 4 report call cards +
  pagination dots (new `components/ui/CarouselDots.tsx`) + desktop-leak fix.
- `b847e10` mobile nav hamburger centred (left of auth).
- `3aee4c1`/`9f0e469`/`73c3257`/`b7fc9ca` report search unified with the hero freeform
  `EamosSearch` (added `tone` prop, suggestive placeholder, dropped Lookup/AI toggle,
  shared `lib/variant-search.ts`), sticky + smooth focus-expand growing from a narrower
  resting state on mobile + desktop (percentage width, no overshoot).

**Stealth (verified):** `eamos.com.au` + `www` unhooked from Vercel; Supabase Site
URL to `https://eamos-dev.vercel.app`. Confirmed `eamos.com.au` shows "Deployment not
found" on Steven's mobile; vercel URL serves + auth works. Un-stealth steps (re-add
domain in Vercel + revert Supabase Site URL) are in the next-session doc; Steven saved them.

**Render:** Steven manually redeployed `084221e` to branch tip `b7fc9ca`; live with
Codex's `f625107` (RPE65 ClinVar contradiction fixed: `nearby_variants` c.260A>G now
`vus`; honest publication `gene_only_no_variant`). Verified via live probe.

**Coordination:** `b7fc9ca` inadvertently swept Codex's staged docs (`PROGRESS.md`, this
`CURRENT.md`, `plans/source-cache-architecture.md`, `plans/v2-backend.md`) — Codex
verified the content + agreed leave-as-is (no rewrite). Claude now commits with
`git commit -- <pathspec>` to avoid re-sweeping the shared index.

**Open:** (Codex lane) re-capture `app/web/lib/rpe65-sample.json` — the `?demo=1` fixture
drifted from corrected live (`vus` + `gene_only_no_variant`). (Claude parked, Steven's
"add to consideration") host-conditional `noindex` (noindex all hosts EXCEPT
`eamos.com.au`) for when going public. No servers running.

**Resume prompt:**
`# Resume prompt · 2026-05-25 03:05 +1000 · Claude (FE polish done; stealth on; Render live)`
`Eamos. Read ~/.claude/plans/next-session-eamos.md (START HERE — "2026-05-25 later 5" is newest), agent_handoff/README.md (protocol), agent_handoff/CURRENT.md (## Claude + Active Status + Locks + Cross-Agent Requests), agent_handoff/RISKS.md, then git status --short --branch. Branch checkpoint/v2-batches-2026-05-17 (HEAD b7fc9ca, local==origin).`
`Verify on eamos-dev.vercel.app ONLY — eamos.com.au is in STEALTH (domain unhooked from Vercel; Supabase Site URL set to eamos-dev.vercel.app). Vercel auto-deploys app/web on push; Render backend is MANUAL (live at b7fc9ca with Codex f625107 fixes).`
`Delta: large /report+landing FE session shipped+verified (trials/pubs display, single-surface pricing [/pricing removed], mobile carousels+dots, centred mobile nav, report search unified with hero freeform bar + smooth focus-expand mobile+desktop). b7fc9ca inadvertently swept Codex staged docs — Codex agreed leave-as-is.`
`Open: (Codex) re-capture app/web/lib/rpe65-sample.json (demo fixture drifted from corrected live = vus + gene_only_no_variant); (Claude parked) host-conditional noindex when going public; un-stealth = re-add domain in Vercel + Supabase Site URL to eamos.com.au.`
`Guardrails: no /runs, AlphaMissense, Workbench (Vite app/frontend = Codex lane); commit with git commit -- <pathspec> (concurrent Codex index); no destructive git. End clear-safe.`
