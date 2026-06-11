# AI Gateway — scoped build plan (variant chat MVP)

> **Status:** planned · authored 2026-06-12 (Claude) · **start next session.**
> Steven granted a one-off FE+BE exception for this work (Claude owns both lanes here).
> Full vision = the Wiki dossiers (`Wiki/product/ai-gateway-build-{kickoff,dossier}.md`, 10 phases /
> 6 features). **This plan does the foundation first:** light up the one feature the UI is already
> built for — the **Ask-Eamos variant chat on `/report`** — against the live gateway, with the
> guardrail spine in place. The rest of the dossier is **sequenced after this foundation, not
> dropped** — we build it once the chatbot works end-to-end and the integration pattern is proven
> consistent (see Scope → Follow-on roadmap).

## 0. Where we are
- **Phase 0 DONE this session:** gateway live, `order:['groq','bedrock']` verified (Groq primary),
  2 keys minted (`eamos-render-broker` $50/mo, `eamos-vercel-support` $10/mo), `AI_GATEWAY_API_KEY`
  set on Render `eamos-dev-sg` + Vercel `eamos-dev`, $5 credit, smoke green (streamed token + forced
  failover + `generationId`/`usage.cost` captured).
- **The FE rail already exists** (`components/aistack/{AIStack,AskEamos,EvidenceSummary}.tsx`): chat
  shell, composer, the deterministic evidence summary as the opening message, `streamChat` scaffold,
  gated on `runId`. Designed to "light up with no rebuild."
- **The backend already has the right service:** `ChatService` (`services/chat_service.py`) takes
  `ChatRequest{question, variant_context: ReportPayload, history, workbench}`, builds an
  **evidence-only** bounded context, blocks diagnosis/prescribing, exposes `respond` + `respond_stream`
  at `POST /api/v1/chat/stream` (`routes/chat.py`). Today its LLM is the mock/OpenAI LangChain
  `lookup_chat_chain`.

So the build = **point that service's LLM at the gateway + make streaming real + flip the FE gate.**

## 1. Scope

**Foundation (build first):**
1. Gateway broker module (OpenAI-compat → `https://ai-gateway.vercel.sh/v1`, `meta/llama-3.3-70b`,
   `order:['groq','bedrock']`, ZDR, temp, 429 backoff, true token streaming, capture
   `generationId`/`finalProvider`/`cost`).
2. `ChatService` uses it when `llm_provider == "gateway"`; **true token SSE** on `/api/v1/chat/stream`.
3. FE: `AskEamos` posts the report payload to `/api/v1/chat/stream` and streams tokens; gate flips
   from coming-soon to live.
4. Guardrail spine: evidence-only context (already allowlisted) + no-diagnosis filter (already there)
   + temp control + **verdict-deferral** (model explains; deterministic ACMG stays authoritative)
   + log `{model, finalProvider, generationId, cost}` + fail-closed.
5. One CI test: outbound gateway payload contains **only** variant-evidence fields (no PHI / no secret).

**Follow-on roadmap (build AFTER the foundation works — sequenced, NOT dropped):**
The foundation establishes the reusable substrate — gateway broker, de-ID/allowlist guard, true
streaming, the structured-output validate+repair pattern, observability-lite, and the guardrail spine.
Once the chatbot works end-to-end on `/report` and that pattern is proven consistent, layer the rest on
top of it, roughly by reuse/value as capacity allows:
1. **Full pgvector literature RAG** — upgrade the same variant chat's grounding from report-payload-only
   to the literature corpus (biggest UX lift; reuses the broker directly).
2. **The other 5 dossier features**, each reusing the broker + validate+repair pattern: messy-text→JSON,
   auto report-narrative, cross-tool audit, NL→SQL (closed-enum QuerySpec), paper→variants
   (VariantValidator-gated).
3. **`/runs` patient-report chat → gateway** — migrate `RunChatService`; needs the heavier PHI
   de-ID boundary, so it follows once de-ID is matured.
4. **Vercel-direct support bot** (zero-PHI surface) + tool-calling / bounded tool loop + fuller
   observability (dashboards, cost alerting, team-wide ZDR).

This sequencing is the point: prove the chatbot + integration first so every later feature inherits a
consistent, working foundation rather than re-deriving it.

> **De-ID note:** `/report` is variant-centric (no patient), so the chat context is inherently
> non-PHI. The guardrail here is an **allowlist assertion** on the outbound payload, not name/DOB/MRN
> stripping. The full `deidentify()` boundary belongs to the patient-report flow, which is out of scope.

## 2. Collision map (the load-bearing constraint)

Codex is live in the workbench + PubMed lanes. This build is **almost entirely additive** and stays
out of his files.

| Action | File | Codex? |
|---|---|---|
| NEW | `app/backend/app/services/ai_gateway/engine.py` (broker) | clean |
| NEW | `app/backend/app/services/ai_gateway/__init__.py` | clean |
| NEW | `app/backend/tests/test_ai_gateway.py` (+ no-PHI/no-secret assertion) | clean |
| EDIT | `app/backend/app/agents/client.py` — add `build_gateway_chat_client()` | **not** in Codex's list |
| EDIT | `app/backend/app/services/chat_service.py` — true streaming via `.stream()` | **not** in Codex's list |
| EDIT | `app/backend/app/api/routes/chat.py` — SSE headers (`X-Accel-Buffering: no`) | **not** in Codex's list |
| EDIT | `app/backend/app/main.py` — build gateway client when `llm_provider=="gateway"` | **not** in Codex's list |
| EDIT ⚠️ | `app/backend/app/core/config.py` — **append** a gateway settings block | **CONTENDED** (Codex edits config.py) |
| EDIT | `app/web/lib/chat.ts` (mine) — add `streamReportChat()` | clean |
| EDIT | `app/web/components/aistack/AskEamos.tsx` (mine) — wire + gate flip | clean |
| EDIT | `app/web/components/aistack/AIStack.tsx` (mine) — pass payload | clean |
| READ-ONLY | `app/web/lib/backend.ts` (`ReportPayload` type) | Codex's — **do not edit**, only import |

**Only one genuinely shared file: `config.py`.** Append my settings in a clearly-marked block,
coordinate with Codex before/after. Avoid `lib/backend.ts`, `lib/api.ts`, `components/workbench/**`,
`routes/health.py`, and the PubMed lane entirely. **Never `git add -A`** — stage explicit pathspecs.
`requirements.txt`: prefer `httpx` (already a dep) over adding the `openai` SDK, to avoid a contended
dependency edit — confirm at build time.

## 3. Request flow (MVP)
```
/report (FE) ── ReportPayload + question + history ──▶ POST /api/v1/chat/stream (FastAPI, Render)
                                                         │ ChatService:
                                                         │  • block diagnosis/prescribing (exists)
                                                         │  • build evidence-only bounded context (exists)
                                                         │  • assert allowlist (new guard)
                                                         ▼
                              ai_gateway/engine.py ── de-id'd messages ──▶ Vercel AI Gateway (ZDR)
                                                                            order:[groq → bedrock]
   FE rail ◀───────────── SSE token stream ◀──────────── true .stream() ◀──┘
                                              log {model, finalProvider, generationId, cost}
```

## 4. Phased steps (each ends with a verify)

- **P1 — Broker** (`ai_gateway/engine.py`): httpx client → gateway; `stream_chat(messages, *, temp, max_tokens)`
  generator yielding tokens + a non-streaming `complete()`; `order:['groq','bedrock']`, ZDR,
  `temperature` from settings, 429 exponential backoff, capture `generationId`/`finalProvider`/`cost`.
  **Verify:** unit smoke against the live gateway (we hold the key) streams a token; forced order-reversal
  logs the other provider.
- **P2 — Guard** (allowlist assertion + CI test): assert the serialized context exposes only the
  evidence keys `ChatService._build_bounded_context` already emits; **CI test fails** if a non-allowlisted
  or secret-looking field reaches the payload. **Verify:** test red on an injected stray field, green otherwise.
- **P3 — Wire + stream**: `agents/client.py` `build_gateway_chat_client()`; `ChatService.respond_stream`
  uses `.stream()` when available (keep word-chunk fallback); `routes/chat.py` SSE headers; `main.py`
  selects the gateway client when `llm_provider=="gateway"`; `config.py` settings block. **Verify:**
  `curl -N /api/v1/chat/stream` streams real Llama tokens; `mock` still returns the mock answer.
- **P4 — FE**: `lib/chat.ts` `streamReportChat(payload, question, history, signal)` → `/api/v1/chat/stream`;
  `AskEamos` calls it, sends `variant_context = payload` (+ history for multi-turn), gate flips from
  `runId===null` to a capability flag. **Verify:** browser-test the rail on `/report` end-to-end, tokens
  render, abort works, disclaimer shown, zero console errors.
- **P5 — Guardrails + obs-lite**: system prompt forbids asserting an ACMG tier ≠ the engine's; log
  `{model, finalProvider, generationId, cost}` per call; live failover check. **Verify:** a forced
  Groq-down run completes via Bedrock; a verdict-contradiction prompt is refused/deferred.

## 5. Open decisions (confirm at session start)
1. **Endpoint** — reuse existing `/api/v1/chat/stream` (ChatService already takes `variant_context`) —
   **recommended** — vs a new `/api/v1/ai/chat/stream`. Rec: reuse.
2. **Chat temperature** — dossier feature-6 suggests `0.3` (conversational, still cite-grounded) vs `0`
   (deterministic). Rec: `0.3`.
3. **FE gate** — `NEXT_PUBLIC_AI_CHAT_ENABLED` flag vs a `/healthz` capability bit, so prod stays
   coming-soon until verified. Rec: env flag for v1.
4. **History** — `ChatRequest.history` exists; send prior turns for multi-turn? Rec: yes (cheap, better UX).
5. **HTTP client** — `httpx` (existing dep) vs `openai` SDK. Rec: `httpx`, to avoid a contended
   `requirements.txt` edit.

## 6. Reproduce / reference
- Full vision + ledger: `Wiki/product/ai-gateway-build-{kickoff,dossier}.md`.
- Phase-0 evidence + key/env state: this session's handoff + the gateway smoke.
- Live gateway smoke (needs the broker key): `GET …/v1/credits`, `GET …/v1/models/meta/llama-3.3-70b/endpoints`,
  `POST …/v1/chat/completions` with `providerOptions.gateway.order`.
