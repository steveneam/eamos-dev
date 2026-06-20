# AI gateway chat — pre-launch security gate

> **Do not enable the variant chat against the live gateway in production until the
> items below are addressed.** From the 2026-06-12 vibe-security audit of the
> gateway foundation. The audit found no Critical issues and clean secret handling;
> these are the launch-gating hardening items.

## The launch gate (one server-side fact to hold)

The chat only spends real money when the **backend** is set to `LLM_PROVIDER=gateway`.
Until the per-user budget below is **enabled** in production, keep prod on
`LLM_PROVIDER=mock` (or simply do not set it to `gateway`). That single server-side
setting — **not** the frontend `NEXT_PUBLIC_AI_CHAT_ENABLED` flag — is the real on/off
switch. (The gated dev demo runs on the shared Render service, bounded by the global
dev cap — see `[[project_ai_gateway]]`.)

## High — the paid chat endpoint guard (IMPLEMENTED — must be ENABLED before launch)

> **Status (2026-06-20):** both halves of the High guard are now built. What remains
> is a one-line deploy action: turn the per-user budget ON before any prod exposure.

`POST /api/v1/chat` and `/api/v1/chat/stream` (`app/backend/app/api/routes/chat.py`)
now enforce, in order:
1. **Auth** — `require_authenticated_principal`. Login is the gate that makes every
   request attributable and closes the anonymous rotating-IP cost-abuse vector. (The
   product call was made: `/report` chat requires sign-in.)
2. **Per-user burst limit** — `RATE_LIMIT_CHAT` (10 / window), keyed on the
   authenticated `user_id` (not just IP).
3. **Per-user daily budget** — `enforce_chat_user_daily_cap` (`core/rate_limit.py`):
   a per-user daily *request* cap (**free-tier = 10/user/day**). Because every response
   is already token-bounded by `ai_gateway_max_tokens` (700), a request cap
   deterministically bounds per-user token spend. Flat across users for first launch (no
   paid tier wired into the chat path yet); config-shaped to grow into per-tier limits
   later. **Env-gated, OFF by default** (`ai_chat_user_daily_cap_*`).
4. **Global dev backstop** — `enforce_chat_dev_daily_cap` (cross-user spend guard for
   the dev/demo period; separate from the per-user budget above).

```python
# routes/chat.py — the paid path now layers all four guards:
principal = require_authenticated_principal(request)             # 1. auth
enforce_rate_limit(request, RATE_LIMIT_CHAT, subject=principal.user_id)  # 2. burst
enforce_chat_user_daily_cap(request, subject=principal.user_id) # 3. per-user budget
enforce_chat_dev_daily_cap(request)                             # 4. global backstop
```

**Launch action (required before prod FE exposure of chat):** set
`AI_CHAT_USER_DAILY_CAP_ENABLED=true` (and tune `AI_CHAT_USER_DAILY_CAP`, free-tier
default 10) on the Render service. The per-user budget is OFF by default so it does not
change the current gated demo; it is the explicit gate to flip at launch. Do **not** rely on the
gateway's spend cap alone (provider caps lag and are a blunt instrument).

**Future (not launch-blocking):** per-tier budgets (free vs paid) once the user's
pricing tier is resolvable server-side (the `AuthenticatedPrincipal` carries no tier
today), and/or true token-accounting if request-count proves too coarse.

## Medium — `NEXT_PUBLIC_AI_CHAT_ENABLED` is a UX gate, not a security boundary

`app/web/components/aistack/AIStack.tsx` gates the chat UI on this flag, but it only
disables the composer in the browser. Anyone can still `POST /api/v1/chat/stream`
directly regardless of the flag. Treat it as a rollout/UX toggle only; the security
boundary is server-side (the `LLM_PROVIDER` setting + the High-finding guard above).

## Also before / around launch (already flagged elsewhere)

- **Gateway key rotation — DONE (2026-06-20).** A transcript-exposed gateway key was
  revoked and verified dead; Render + local now run a fresh key. (Details in
  `[[project_ai_gateway]]`.) Rotate again before broad public launch as a matter of
  hygiene.
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
