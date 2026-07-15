# Eamos — Test Deployment Guide

## Current Render Runtime Ops

For current SG Render provider flips, persistent-disk materialization, and
Workbench/CRISPR off-target runtime handling, start here:

- [Render Provider Flip Workflows](render-provider-flip-workflows.md)
- [Render Coordinate Assets](render-coordinate-assets.md)

> Written 2026-05-24 by Claude (overnight, while you slept) from your two Desktop
> docs: *Comprehensive Technical Architecture* and *Supabase Database
> Architecture — Variant Submission Context Ledger*.
> Stack: **Next.js → Vercel · Supabase (Sydney) · PostHog (US) · Stripe (AU)**.
>
> **This is a plan + prep, not a finished deployment.** The actual deploy needs
> your accounts/secrets and a few decisions (below). I did everything that does
> NOT need your login. No dev servers were left running.

---

## 0. TL;DR — your questions answered first

| Your question | Short answer |
| --- | --- |
| **Do you need my login details?** | **No — and please don't share passwords.** You log in to each dashboard yourself; I only need the *public* values they generate (project URL, publishable keys). See §6. |
| **Do you need my API keys?** | Only the **publishable/anon** ones, and only to paste into config — never secret keys. I never need secret keys, your bank, or your password. See §6. |
| **Do you need my bank account?** | **Only for Stripe**, and **only when you want real payouts**. Not needed for a test deploy. Stripe **test mode** needs no bank. See §5. |
| **Does `.env` need to be ready?** | The **templates are ready** (I updated `app/web/.env.local.example`). The real `.env.local` (with your keys) you fill in at execution time — it stays local + gitignored, never committed. See §6. |
| **Does the GitHub repo need to be ready?** | It already is: `github.com/steveneam/eamos-dev`, remote wired, credential manager authenticated. One decision: keep it **private** (recommended) and connect Vercel to it. See §4. |
| **Any IT / work-computer issues?** | **None blocking.** All services reachable, npm works, git push authenticated, Node 24 builds Next 16. Full results in §7. |

**Biggest thing to know:** your deployment docs describe a *pure Next.js + Supabase*
app where the browser talks straight to the database. **Eamos is bigger than that** —
it has a **FastAPI Python backend** that does all the genomic orchestration
(gnomAD, ClinVar, VariantValidator, SpliceAI, PubMed…). That backend needs its own
host (it can't run on Vercel). Good news: there's already a `Dockerfile` for it, so
hosting is turnkey. Details + recommendation in §2.

---

## 1. Current readiness snapshot (verified tonight)

| Piece | State |
| --- | --- |
| **Frontend** `app/web` (Next 16, landing + `/report`) | ✅ builds clean, deploy-ready |
| **Backend** `app/backend` (FastAPI) | ✅ Dockerfile + requirements ready; needs a host |
| **GitHub repo** | ✅ `steveneam/eamos-dev`, in sync, credential mgr authenticated |
| **Secrets hygiene** | ✅ no `.env` is tracked; `.gitignore` hardened (`.vercel`, `.env.*.local`) |
| **Supabase schema** | ✅ SQL migration written (`supabase/migrations/0001_submission_ledger.sql`) |
| **Supabase / PostHog / Stripe code** | ⛔ not built yet — greenfield (no auth/DB/payment UI exists in `app/web`) |
| **Env templates** | ✅ `app/web/.env.local.example` updated with all vars |

**Reality check on scope:** the only surfaces currently built in `app/web` are the
**landing page** and the **Variant Evidence Report**. There is **no login,
no "save variant," no evidence-submission UI, and no pricing/checkout wired** yet —
"Sign in / Register / Pricing" are marketing placeholders. So:

- **Supabase + Auth + the "Messenger" submission feature = a feature to BUILD**,
  not just configure. The DB schema is ready; the React UI for it is not.
- **Stripe checkout = also a feature to build** (the pricing tiers are display-only).
- **What you CAN deploy as a test today = landing + report.** That alone is a
  legitimate, impressive test deployment.

---

## 2. The architecture decision: where does the FastAPI backend live?

Your browser (on Vercel) calls same-origin `/api/*`. `next.config.mjs` rewrites
that to `API_PROXY_TARGET` (defaults to `http://localhost:8000`). In production you
point `API_PROXY_TARGET` at a hosted backend — **no CORS, no code change.**

Vercel can host the Next.js app but **not** this Python backend (it's a long-lived
container with native deps, not serverless functions). So pick a backend host:

| Option | Cost | Region | Effort | Notes |
| --- | --- | --- | --- | --- |
| **Render.com** (Docker) | Free tier | Oregon (US) | ⭐ lowest | Builds from existing Dockerfile. Free tier **sleeps after 15 min idle** (~30–50s cold start) — fine for a demo. Recommended to start. |
| **Fly.io** (Docker) | Free allowance | **Sydney (syd)** | medium | Best latency (matches Supabase Sydney). Needs `flyctl` + a `fly.toml`. |
| **Railway** (Docker) | Trial credit then paid | US | low | Easiest UX but not free long-term. |
| Vercel Python functions | — | — | ✗ | Not viable for this backend (heavy deps, stateful). Don't. |

**Recommendation for the test demo:** **Render free tier** to start (turnkey from
the Dockerfile), switch to **Fly.io Sydney** if cold-starts/latency annoy you.

### Two deploy depths — choose how far to go for the test

- **Depth A — Frontend-only demo (fastest, ~15 min, no backend host).**
  Deploy `app/web` to Vercel and show `/report?demo=1` (renders the static sample
  report — no backend needed) + the landing page. Great for a first live URL.
- **Depth B — Full live demo.** Deploy the backend (Render/Fly), set
  `API_PROXY_TARGET` on Vercel to that URL, set `USE_REAL_APIS=true` on the
  backend → live variant lookups end-to-end.

---

## 3. Phased deployment plan

### Phase 1 — Vercel frontend (Depth A) — *no secrets except a Vercel login*
1. Vercel → **Add New Project** → import `steveneam/eamos-dev`.
2. **Root Directory = `app/web`** (critical — it's a monorepo). Vercel auto-detects Next.js.
3. Build command `next build --webpack` is already in `package.json`; leave defaults.
4. Env vars: leave `NEXT_PUBLIC_API_BASE_URL` empty for now (demo route needs no backend).
5. Deploy → you get `https://<project>.vercel.app`. Visit `/` and `/report?demo=1`.

### Phase 2 — FastAPI backend (Depth B)
1. Render → **New → Web Service** → connect repo → **Root Directory `app/backend`**,
   Runtime **Docker** (uses the existing Dockerfile).
2. Set backend env (from `app/backend/.env.example`): `JWT_SECRET` (32+ chars),
   `USE_REAL_APIS=true`, `LLM_PROVIDER=mock` (or `openai` + `OPENAI_API_KEY` if you
   want live AI summaries), `ALLOWED_ORIGINS=https://<project>.vercel.app`.
3. Deploy → get `https://eamos-api.onrender.com`.
4. Back in Vercel → add env `API_PROXY_TARGET=https://eamos-api.onrender.com` → redeploy.
5. Now `/report?gene=RPE65&cdna=c.260A>G` runs live through the proxy.

### Phase 3 — Supabase (for the future auth + Messenger feature)
1. Supabase → **New project**, region **Sydney (ap-southeast-2)**.
2. Settings per your doc: Data API **ON**, auto-expose new tables **OFF**, automatic RLS **ON**.
3. SQL Editor → paste `supabase/migrations/0001_submission_ledger.sql` → Run.
   (Creates `profiles`, `saved_variants`, `user_evidence_submissions` + RLS.)
4. Copy **Project URL** + **publishable (anon)** key → Vercel env
   `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
5. *(Build step, later)* add `@supabase/ssr`, the `utils/supabase/client.ts` helper
   (code in §8), and the actual login / save-variant / submit-evidence UI.

### Phase 4 — PostHog analytics
1. PostHog → project → copy **Project API key** (`phc_…`) + host (`https://us.i.posthog.com`).
2. Vercel env `NEXT_PUBLIC_POSTHOG_KEY`, `NEXT_PUBLIC_POSTHOG_HOST`.
3. *(Build step, later)* add `posthog-js`, `app/providers.tsx`, wrap `app/layout.tsx` (code in §8).

### Phase 5 — Stripe payments (last; needs the most product decisions)
1. Stripe → create the 3 products/prices (Free / Starter $9.95 / Pro $24.95 AUD).
   Per your doc + RBA Oct-2026 rule: **bake fees into flat prices, no surcharging.**
2. Use **Payment Links / hosted Checkout** (no card UI to build).
3. Test mode first (no bank). Add a bank account only to take real money.

---

## 4. GitHub — is it ready?

Yes. `origin = https://github.com/steveneam/eamos-dev.git`, local branch in sync,
**Git Credential Manager** is configured and authenticated (verified — `git ls-remote`
worked with no prompt). So `git push` will work when you authorize it.

**Decisions for you:**
- **Keep the repo private** (recommended — it has proprietary algorithms in `docs/proprietary/`).
  Vercel deploys fine from a private repo.
- **Pushing is held for your go-ahead.** I committed my deployment-prep files locally
  but did **not** push (push is gated to you, and it's what triggers Vercel auto-deploy).
  When ready: `git push origin checkpoint/v2-batches-2026-05-17` — or merge to `main`
  first if you want Vercel's production branch to be `main`.

---

## 5. Money: what Stripe actually needs

- **Test mode:** nothing financial. Test card `4242 4242 4242 4242` works with no bank.
- **Live mode (real payouts):** Stripe needs your identity + an Australian bank account
  for settlement. Only do this when you actually want to charge people.
- For a *test deployment*, **skip Stripe live entirely** or stub it with a test-mode
  Payment Link. No bank account required for the demo.

---

## 6. Secrets — what I need from you vs. what stays yours

**I never need:** your passwords, your bank details, or any **secret** key
(`sb_secret_…`, `sk_live_…`, `sk_test_…`). Those either live only in server env
(backend host) or aren't needed at all.

**To finish wiring, you paste these PUBLIC values (safe in the browser bundle):**
- `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` (publishable, `sb_publishable_…`)
- `NEXT_PUBLIC_POSTHOG_KEY` (`phc_…`) + `NEXT_PUBLIC_POSTHOG_HOST`
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (`pk_…`) — only when Stripe is wired

**Where they go:**
- **Local dev:** `app/web/.env.local` (copy from `.env.local.example`; gitignored).
- **Production:** Vercel dashboard → Project → Settings → Environment Variables
  (not in any file). Backend secrets (`JWT_SECRET`, `OPENAI_API_KEY`) → the backend
  host's env, never the frontend.

**Golden rule (from your architecture doc):** publishable keys client-side, secret
keys server-only. The DB is still safe because **Row Level Security** is on — the
anon key can only touch rows the logged-in user owns.

---

## 7. IT / work-computer findings (tested tonight)

| Check | Result |
| --- | --- |
| Outbound HTTPS to supabase / vercel / posthog / stripe / npm / github | ✅ all reachable (no corporate firewall block) |
| Genomic API (rest.ensembl.org) reachable | ✅ 200 (and the deployed backend runs on its host, not this PC, so this isn't even a prod dependency) |
| npm registry | ✅ reachable — `npm install` of new deps will work |
| Git push auth | ✅ Credential Manager configured + authenticated |
| Node / npm | ✅ Node 24.15, npm 11.12 — Next 16 builds clean |
| Python | ✅ 3.10.11 local; Docker image pins 3.12 for the host |

**No IT blockers found.** The one historical caveat (the *local* UCSC isPcr binary
needs WSL — `docs/operations/risks-and-guardrails.md` M-002C) only affects the
parked **Workbench**, which is
**not** part of this deployment.

**One thing to watch:** the 15-min inactivity timeout on this machine. It doesn't
affect cloud builds (they run on Vercel/Render). It only matters if you run a long
*local* dev server and walk away — so close local servers before stepping away.

---

## 8. Ready-to-paste code (apply at execution, after `npm i` the deps)

> Deferred to a coordinated step because adding `@supabase/ssr`/`posthog-js` to
> `app/web/package.json` and editing `app/web/app/layout.tsx` overlaps with Codex's
> active report-render lane — and you need the keys anyway. Kept here (not as live
> files) so the build stays green until we wire it together.

**`app/web/utils/supabase/client.ts`**
```ts
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  )
}
```

**`app/web/app/providers.tsx`** (PostHog)
```tsx
'use client'
import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'
import { useEffect } from 'react'

export function PHProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
      person_profiles: 'identified_only',
      capture_pageview: false,
    })
  }, [])
  return <PostHogProvider client={posthog}>{children}</PostHogProvider>
}
```
Then wrap `{children}` in `app/web/app/layout.tsx` with `<PHProvider>`.

> Note: your doc used `@posthog/react`; the maintained import for `posthog-js` v1+
> is `posthog-js/react` (one package). Use `npm i posthog-js` only.

---

## 9. What's done vs. what needs you (the morning checklist)

**Done tonight (committed locally, not pushed):**
- ✅ `supabase/migrations/0001_submission_ledger.sql` — runnable schema + RLS
- ✅ `app/web/.env.local.example` — all deploy vars documented
- ✅ `.gitignore` — `.vercel` + `.env.*.local` added
- ✅ This guide
- ✅ IT environment verified; backend Dockerfile confirmed deploy-ready

**Needs you (decisions + accounts):**
1. Pick deploy depth (A frontend-only, or B full-stack) and backend host (Render vs Fly).
2. Create the Supabase/Vercel/PostHog projects; paste the public keys.
3. Authorize the push to GitHub (and decide: deploy from `checkpoint/...` or merge to `main`).
4. (Later) approve building the auth + Messenger + Stripe **features** (they don't exist yet).

When you're up, we can run the interactive **`planner`** skill together to turn §3
into a tracked, step-by-step execution — that's the right moment for it, since each
account step needs your hands on the keyboard.
