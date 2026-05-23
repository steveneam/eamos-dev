# Vite → Next.js Migration — Design Doc

> Owner: Claude (frontend). Status: **IMPLEMENTED + browser-verified** (Slices
> 0–5 done in one session per user "proceed"; fully reversible). Created &
> implemented 2026-05-23.
>
> Supersedes the "**Do not migrate to Next.js**" line in `plans/v2-frontend.md`
> (locked decision, 2026-05-23). Backend stays the FastAPI **contract
> authority**; Next.js owns rendering/routing only. This doc is **design-agnostic**
> — it migrates the *current* aesthetic verbatim. The emerald/animated
> "Lifestream" redesign + the landing mock are a **separate, later** effort that
> builds on this skeleton.

## 0. Implementation status (2026-05-23)

**Built `app/web/` (Next.js, App Router) and ported landing + Variant Evidence
Report. Production build green; both pages browser-verified pixel-faithful.**

- **Next version: 16.2.6, NOT 15 — RATIFIED by user 2026-05-23** ("might as well
  use the newer next 16 then"). The locked decision said "Next.js 15 App Router";
  the **App Router** is the load-bearing requirement, not the major number. Next
  15.5.18 **fails to build on the IT-managed Node 24.15** — a trivial one-line
  app threw `SyntaxError: Unexpected token '}'` (15.5 predates Node 24; can't
  downgrade the system Node). Next 16.2.6 builds cleanly on Node 24 and uses the
  same App Router APIs — the ported code is byte-identical across the bump.
- **Verification:** `cd app/web && npm run build` → compiled + TypeScript +
  prerendered `/`, `/report`, `/_not-found` (clean, no warnings). Browser
  (`next start`): `/` and `/report?demo=1` render identical to the Vite app;
  console clean except a now-fixed favicon 404 (added `app/web/app/icon.svg`).
- **Vite app, contract canary, `/runs`, AlphaMissense, Codex backend lane:
  untouched.** No edit to `app/frontend/src/lib/backend.ts`.
- Open follow-ups: live-backend lookup browser smoke (needs FastAPI running);
  strict-TS hardening pass (see §10); the redesign + cutover (later, gated).

## 1. Goal & scope

Move the two **active** surfaces — the landing page (`/`) and the Variant
Evidence Report (`/report`) — from the React/Vite SPA to **Next.js 15 (App
Router)**, pixel-faithful to today, with no contract change.

**In scope:** landing, Variant Evidence Report, the shared design tokens, the
shared lib (`backend.ts` types, the `variantLookup` client, `variant-format`,
`sample-report`, `sources`, `utils`), and the UI/report/aistack/landing
component trees those two pages use.

**Explicitly out of scope (deferred, do not port now):**
- **Workbench** (`/workbench`) — ON HOLD (register.md). Stays in the Vite app.
- **Patient Report Pipeline** (`/runs`, `LegacyRunsApp`) — frozen. Stays in Vite.
- **AlphaMissense** — display stays off; assets/contract literals untouched.
- The **new emerald/animated aesthetic** + GSAP/R3F/ScrollTrigger — later, with
  the landing mock.
- **Net-new scope** flagged but undecided: auth/accounts, pricing, ClinVar
  "messenger", Supabase, brand rename ("GeneVision AI"?). None built here.

## 2. Directory strategy — parallel app, not in-place

**Decision: build the Next.js app in a new directory `app/web/`, leaving the
Vite app `app/frontend/` fully intact.**

Why parallel (forced by the holds, not a preference):
- The Workbench and `/runs` are Vite-resident and **must keep working** while on
  hold/frozen. An in-place conversion of `app/frontend/` to Next.js would break
  both — violating their no-touch holds.
- Reversibility: the skeleton is a self-contained new tree; reverting = delete
  `app/web/`. The Vite checkpoint base (`205eaae`) is undisturbed.
- **No shared-file collision.** `app/web/` gets its **own copy** of the contract
  types (`app/web/lib/backend.ts`), so we never edit the canary-guarded
  `app/frontend/src/lib/backend.ts` (Hard Rule 4 / 5 — backend-led contract).
  The existing `test_frontend_contract.py` keeps guarding the Vite copy; the
  new copy is a verbatim mirror kept in sync by hand until cutover.

**Coexistence during transition:**
- `app/frontend/` (Vite, port 5173): Workbench + `/runs` + (still-live) landing
  & report until cutover.
- `app/web/` (Next.js, port 3000): the new landing + report.
- Both call the same FastAPI backend (`localhost:8000`).

**Cutover (LATER, user-gated — not this effort):** once the Next.js landing +
report are accepted and the Workbench/`/runs` question is decided, rename/retire:
either move Workbench+runs into Next.js too, or keep a thin Vite app only for
them, then make `app/web/` canonical (and point the contract canary at its
`backend.ts`). Recorded as a hold; **do not execute without the user.**

## 3. Target structure (`app/web/`)

```
app/web/
  package.json            # next 16, react 19, tailwind v4 (+ @tailwindcss/postcss)
  next.config.mjs         # rewrites: /api/* → http://localhost:8000/api/* (dev proxy parity)
  tsconfig.json           # paths: { "@/*": ["./*"] }  (root-relative, Next convention)
  postcss.config.mjs      # { plugins: { "@tailwindcss/postcss": {} } }
  next-env.d.ts
  .env.local.example      # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
  app/
    layout.tsx            # <html><body>, metadata, imports globals.css
    globals.css           # ported verbatim from frontend/src/index.css (tokens + utils)
    page.tsx              # server → renders <LandingClient/> ('/')
    report/
      page.tsx            # server → <Suspense><ReportClient/></Suspense> ('/report')
  components/             # ported from frontend/src/components (landing/report/aistack/ui/layout/search/brand)
  lib/                    # backend.ts (mirror), api.ts (lookup subset), variant-format, sample-report, sources, utils, chat
```

Path alias: Next convention is `@/*` → project root. I keep imports as `@/components/...`
and `@/lib/...`; since the new tree puts `components/` and `lib/` at the app root
(not under `src/`), `@/*` → `./*` resolves them unchanged. **Net effect: existing
`@/` imports port verbatim.**

## 4. Client / server component boundary

Both pages are interactive (search, async lookup, loading/error/retry, URL
state). First migration keeps them **client components** — faithful behaviour,
lowest risk. RSC/server-data optimisation is a deliberate later pass.

- `app/page.tsx` (server) → renders `<LandingClient/>` (`'use client'`).
  Metadata via `export const metadata`.
- `app/report/page.tsx` (server) → `<Suspense fallback={…}><ReportClient/></Suspense>`.
  `ReportClient` is `'use client'` and uses `useSearchParams` — which **requires**
  a Suspense boundary at build time, hence the wrapper.
- All ported leaf components that use hooks/handlers get `'use client'` at the
  top. Pure-presentational ones can stay server, but to minimise churn and
  match the SPA mental model, the ported page subtrees are client.

## 5. API mapping (mechanical, contained)

Only 5 files reference router/env (verified by grep). The component/report/
aistack/ui trees are router-free and port byte-for-byte.

| Vite (react-router / vite) | Next.js |
| --- | --- |
| `App.tsx` `<BrowserRouter><Routes>` | file-based routes — deleted, replaced by `app/**/page.tsx` |
| `useNavigate()` → `navigate('/report?…')` | `useRouter()` from `next/navigation` → `router.push('/report?…')` |
| `useSearchParams()` (RR) | `useSearchParams()` from `next/navigation` (read-only; same `.get()` API) |
| `<Link to="…">` (RR) | `<Link href="…">` from `next/link` |
| `import.meta.env.VITE_API_BASE_URL` | `process.env.NEXT_PUBLIC_API_BASE_URL` |
| Vite dev proxy `/api → :8000` | `next.config.ts` `rewrites()` (or absolute `NEXT_PUBLIC_API_BASE_URL`) |

`lib/api.ts`: port the **lookup subset only** (`variantLookup`, `parseResponse`,
`API_BASE_URL`). The `/runs` auth helpers + Workbench tool calls (primer/crispr/
tide/viewer) are out of scope — omitted from the new `api.ts`.

## 6. Styling — Tailwind v4 unchanged in substance

The Vite app already uses Tailwind v4 (`@import "tailwindcss"` + `@theme inline`
+ `:root` tokens). The only delta is the build integration:

- Vite: `@tailwindcss/vite` plugin.
- Next.js: `@tailwindcss/postcss` via `postcss.config.mjs`.

`globals.css` = `frontend/src/index.css` ported verbatim (Google-fonts `@import`
first, then `@import "tailwindcss"`, `@theme inline`, `:root`, base, utilities),
with one edit: drop the `#root` selector (Next has no `#root`) — keep `html, body`.

## 7. Dependencies (`app/web/package.json`)

Final (minimal) set, confirmed by import-graph audit: `next@16`, `react@19`,
`react-dom@19`, `tailwindcss@4` + `@tailwindcss/postcss`, `clsx`,
`tailwind-merge`. **Dropped vs the Vite app** (the in-scope tree imports none of
them — they're Workbench/`/runs`-only): `lucide-react`, `framer-motion`,
`@radix-ui/*`, `class-variance-authority`, `react-router-dom` (replaced), and
the `vite`/`vitest` toolchain.

## 8. Migration slices (verify after each)

0. **Design-doc** (this file).
1. **Skeleton:** `app/web/` config + `globals.css` + `layout.tsx` + placeholder
   `page.tsx` / `report/page.tsx`. → `npm install` + `npm run build` clean.
2. **Shared lib + ui primitives:** `lib/{backend,api,variant-format,sample-report,sources,utils,chat}.ts`
   + `components/ui/*`. → build clean.
3. **Landing:** `TopNav`, `SearchShell`, `SourceStrip`, `FeaturesGrid`,
   `HowItWorks`, `SiteFooter`, `brand/EamosLogo`, `LandingClient`. → build +
   browser render at `/`.
4. **Report:** `VariantHeader`, `VariantDecoder`, `AIStack` (+aistack/*),
   `EvidenceTable`, `DiseaseSection`, `TrialsSection`, `PubMedSection`,
   `LimitationsSection`, `LocusContext`, `InSilicoGrid`, `AcmgCriteriaFold`,
   `CuratedVariantsGrid`, `AssociatedConditions`, `PublicationsCallout`,
   `ModePill`, `ReportClient`. → build + browser render at `/report?demo=1` and
   against live backend.
5. **Parity check:** both pages pixel-compared to the Vite app; `?demo=1` sample
   + live `/api/v1/lookup` both render.

## 9. Verification

- `cd app/web && npm run build` (Next production build = type-check + compile).
- Browser: `/` and `/report?demo=1` render identical to the Vite app; live
  lookup works against `localhost:8000`; loading/offline/malformed states intact.
- The Vite app + its contract canary are **untouched** → `app/frontend` build +
  `test_frontend_contract.py` remain green by construction (no edits there).

## 10. Risks / watch-outs

- **Contract drift:** `app/web/lib/backend.ts` is a hand-kept mirror of the
  canary-guarded Vite copy until cutover. Note in a Cross-Agent Request so Codex
  knows additive contract changes now need mirroring in **two** places (or defer
  the second until cutover). Keep the new copy a verbatim paste of the Vite one.
- **`useSearchParams` Suspense:** missing the boundary fails the production build
  — the `report/page.tsx` wrapper is mandatory, not optional.
- **Two `node_modules`:** one-time `npm install`; verify with `npm run build`,
  not a long-running dev server (no orphaned servers — memory note).
- **Brand/aesthetic churn:** everything here uses the current "Eamos" brand +
  current visuals. When the mock + brand decision land, the redesign edits this
  skeleton; nothing here presupposes the final look.
- **`strict: false`:** `app/web/tsconfig.json` matches the Vite app's actual
  (non-strict) TS config so the verbatim-copied code compiles identically. A
  later hardening pass should flip `strict: true` and fix the null-checks it
  surfaces — do it as its own slice, not mixed with the redesign.
- **Toolchain pin:** Next 16 + Node 24 is the verified combo here. Next 15.5
  does **not** build on this host's Node 24. If anyone pins Next back to 15,
  they must also provide Node 20/22. Next 16 `next build` uses **Turbopack** by
  default (worked cleanly); `next.config` no longer accepts the `eslint` key.
- **ModePill `/workbench` link:** points at `/workbench`, which lives only in
  the Vite app (parked) — it 404s in `app/web`. Known coexistence gap; the nav
  redesign resolves it. Not a regression of in-scope surfaces.
```

