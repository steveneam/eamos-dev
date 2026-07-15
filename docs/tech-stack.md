# Eamos — Production Services / Vendor Stack

Single source of truth for the **external services** Eamos runs on, plus the
tools we have **deliberately decided not to adopt** (so they don't get
re-litigated). For local dev technologies (Next/FastAPI/SQLite/Python versions)
see the `## Tech Stack` table in `README.md`. For infra sizing rationale see
`docs/stability-audit/a11-render-budget.md`.

Last reviewed: 2026-06-16.

---

## What we use

### Frontend & hosting
| Service | Role | Notes |
| ------- | ---- | ----- |
| **Vercel** | Hosts the active FE (`app/web`, Next.js 16) | Auto-deploy ON → prod (`eamos-dev.vercel.app`). **Deploy from repo root only.** Provides edge DDoS mitigation + WAF/Firewall + BotID — this covers the **frontend** surface. |
| **Next.js 16** (App Router) | Active frontend (`app/web`) | The sole frontend application and contract consumer. |
| Tailwind v4 / framer-motion / gsap | UI / animation | In-house, legibility-first design system (`DESIGN.md`). |

### Backend & compute
| Service | Role | Notes |
| ------- | ---- | ----- |
| **Render** | FastAPI/Python backend | Service `eamos-dev-sg`, **Standard 2 GB / 1 CPU + 60 GB persistent disk**, **single instance by design** (~$40/mo). Auto-deploy OFF (deploy-hook gitignored). **Codex owns redeploy + live verify.** |
| Render persistent disk (60 GB) | Local-file runtime cache | tabix / HMMER / sqlite / 2bit. Materialize **offline → Supabase Storage → disk**; never startup-download. |

### AI
| Service | Role | Notes |
| ------- | ---- | ----- |
| **Vercel AI Gateway** | Model routing / provider mgmt | Wired but **inert** in prod (`LLM_PROVIDER=mock`, `RAG_ENABLED=false`). |
| **Groq** | Fast inference hardware | Via the gateway. |
| **Llama (Meta)** | Open chat model | Via the gateway. |
| Backend `ai_gateway` broker | Guard + broker + streaming `/report` chat | `app/backend/app/services/ai_gateway/`. Built, currently inert until the provider flip + RAG corpus materialization. |

### Data & memory
| Service | Role | Notes |
| ------- | ---- | ----- |
| **Supabase** | Core Postgres DB + Auth + Storage | Structured accounts/logs/evidence; durable asset Storage (dbSNP ~29.6 GB, phyloP ~9.9 GB). **pgvector available.** |
| SQLite | Local backend variant/provider cache | On the Render disk. |
| **sqlite-vec** | Literature RAG vector store (local) | Local-first; materialized with the Tier-1 corpus. (See "not using → Pinecone".) |

### Identity & security
| Service | Role | Notes |
| ------- | ---- | ----- |
| **Supabase Auth** | Identity / login | Google / Microsoft / LinkedIn, wired with RLS + service_role grants. (See "not using → Clerk".) |
| Vercel Firewall / BotID | Edge DDoS/WAF | Covers the FE. (Backend WAF — see "not using → Cloudflare".) |
| App-level rate limiting | `app/backend/app/core/rate_limit.py` | In-process, per-IP. Durable/multi-instance Redis is **deferred, not rejected** (see "on the radar → Upstash Redis"). |

### Business & ops
| Service | Role | Notes |
| ------- | ---- | ----- |
| **Stripe** | Payments / subscription tiers | Checkout → receipt; Stripe sends its own receipts. |
| **Resend** | Transactional email | Established vendor (CLI-first list in `docs/governance/decisions.md`). |
| **PostHog** | Product analytics + session replay | `posthog-js` wired in `app/web`. Replay lives here — **not** in Sentry. |
| **Sentry** | Error/crash + performance monitoring | Account created 2026-06-16. **Integration pending** — FE (`app/web`) first; backend FastAPI is Codex's lane. Errors + tracing only (replay stays in PostHog). |
| **Porkbun** | Domain registrar | `eamos.com.au`. |

---

## On the radar (deferred, not rejected)

- **Upstash Redis** — serverless Redis for durable rate-limiting + relieving the
  SQLite write-lock contention found in the Epic A audit (`variant_cache_repo`
  DELETE-on-read) + a shared cache for the `gene_context_snapshot` / run-chat
  vector index. **Gated on** scaling past the single Render instance or
  deciding to move the cache/rate-limit hot path off SQLite. The audit
  explicitly recommended Redis for multi-instance rate limiting.

---

## Deliberately not using (and why)

| Tool | Why not |
| ---- | ------- |
| **Pinecone** | Already covered by **sqlite-vec** (local RAG) + Supabase **pgvector**. An external managed vector DB adds cost + a network hop + data egress, and conflicts with the local-first / single-box / offline-materialization model and the Tier-1 plan. Reconsider only if the corpus outgrows one box and needs a distributed ANN index. |
| **Clerk** | Auth is already built on **Supabase Auth** (Google/MS/LinkedIn) wired into RLS + service_role grants. Swapping would be churn for zero gain. |
| **Cloudflare** | FE is already shielded by Vercel (Firewall/BotID/auto-DDoS). A backend WAF in front of Render is optional defense-in-depth; the primary control for the audit's unauthenticated-route findings is app-level (auth + size caps + rate limits), which Epic A largely shipped. |
| **Aceternity UI** | Flashy marketing-page animation fights the legibility-first clinical design system (`DESIGN.md`). At most cherry-pick a single effect for the landing page; never near report/workbench data surfaces. |

---

## Decision log
- **2026-06-16** — Evaluated an 11-tool "production SaaS chatbot" blueprint
  against Eamos. Adopted/confirmed: Resend (already in stack), Sentry (account
  created, integration pending). Deferred: Upstash Redis. Rejected: Pinecone,
  Clerk, Cloudflare (for now), Aceternity UI. Rationale above.
