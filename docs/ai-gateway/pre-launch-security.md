# AI gateway chat — pre-launch security gate

> **Do not enable the variant chat against the live gateway in production until the
> items below are addressed.** From the 2026-06-12 vibe-security audit of the
> gateway foundation. The audit found no Critical issues and clean secret handling;
> these are the launch-gating hardening items.

## The launch gate (one server-side fact to hold)

The chat only spends real money when the **backend** is set to `LLM_PROVIDER=gateway`.
Until the items below are done, keep production on `LLM_PROVIDER=mock` (or simply do
not set it to `gateway`). That single server-side setting — **not** the frontend
`NEXT_PUBLIC_AI_CHAT_ENABLED` flag — is the real on/off switch.

## High — the paid chat endpoint is unauthenticated, rate-limit-only

`POST /api/v1/chat/stream` (`app/backend/app/api/routes/chat.py`) enforces
`RATE_LIMIT_CHAT` (10 requests / window / IP) but has **no auth and no per-user/tier
token budget**. Wired to the paid gateway, this is a cost-abuse vector: a client
rotating IPs (or simply many users) can drive gateway spend. The `$50/month` key cap
bounds the damage but can be exhausted, which also denies service to legitimate users.

**Before prod-enabling, add a server-side guard on the paid path** — one or both of:
- an **auth requirement** on the chat endpoint (decide first whether `/report` chat
  should require login — `/report` is currently a public surface, so this is a
  product call), and/or
- a **per-user / per-tier daily token (or request) budget**, tracked server-side,
  returning a clear error when exceeded.

```python
# Before — chat_stream(): rate-limit only
enforce_rate_limit(request, RATE_LIMIT_CHAT)

# After — also gate the paid path
user = require_user(request)                      # if chat should be authed
enforce_user_ai_budget(user, daily_token_cap)     # per-user/tier cap, server-side
```

Do **not** rely on the gateway's `$50/mo` cap alone (provider caps lag and are a blunt
instrument).

## Medium — `NEXT_PUBLIC_AI_CHAT_ENABLED` is a UX gate, not a security boundary

`app/web/components/aistack/AIStack.tsx` gates the chat UI on this flag, but it only
disables the composer in the browser. Anyone can still `POST /api/v1/chat/stream`
directly regardless of the flag. Treat it as a rollout/UX toggle only; the security
boundary is server-side (the `LLM_PROVIDER` setting + the High-finding guard above).

## Also before / around launch (already flagged elsewhere)

- **Re-mint the gateway key.** The `eamos-render-broker` key passed through a session
  transcript and must be rotated before production. (Tracked in `[[project_ai_gateway]]`.)
- **Paid credits.** The free tier rate-limits `meta/llama-3.3-70b`; sustained/real
  usage needs paid credits topped up on the gateway.
- **Low / dev-only:** `scripts/fake_gateway.py` is a localhost dev double — never run
  with `--host 0.0.0.0` or in any deployed environment.

## Good controls already in place (no action needed)

Evidence-only outbound allowlist guard (fail-closed PHI/secret), prompt-injection
hardening (separate system/user messages, history role-validation, no tool access),
key isolation (backend-only, gitignored/untracked `.env`, not in the FE bundle, never
logged), LLM output rendered as escaped text (no XSS), and no client-controllable
gateway URL (no SSRF).
