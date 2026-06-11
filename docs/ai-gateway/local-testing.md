# AI gateway — local testing (no live tokens)

Three ways to develop and test the Ask-Eamos variant chat without spending gateway
credits. Run everything from `app/backend/`.

## 1. Mock provider — free, instant, deterministic

The cheapest check. Exercises the full `ChatService` streaming path with a canned
answer; no gateway, no key.

```bash
python -m app.cli.chat_smoke --mock --expect-contains RPE65
```

Prints a JSON status payload (`status: passed|failed|skipped`) and exits non-zero on
failure, so it doubles as a CI assertion (same pattern as `app/cli/search_input_ai_smoke.py`).

## 2. Fake gateway — free, realistic, exercises the *real* broker

`scripts/fake_gateway.py` is a local OpenAI-compatible stand-in for the Vercel AI
Gateway. It speaks the same streaming SSE protocol, so the actual broker
(`app/services/ai_gateway/engine.py`) runs unchanged — httpx, SSE parsing, retry,
metadata — but offline and free. Best for developing the chat UI/UX with believable
streamed prose.

```bash
# terminal 1 — the fake gateway
python scripts/fake_gateway.py --port 8799

# terminal 2 — drive the chat through the real broker, pointed at the fake
LLM_PROVIDER=gateway \
AI_GATEWAY_API_KEY=local-fake \
AI_GATEWAY_BASE_URL=http://127.0.0.1:8799/v1 \
python -m app.cli.chat_smoke --stream --expect-contains RPE65
```

Or run the whole backend against the fake and use the browser `/report` chat
(`NEXT_PUBLIC_AI_CHAT_ENABLED=true`):

```bash
LLM_PROVIDER=gateway AI_GATEWAY_API_KEY=local-fake \
AI_GATEWAY_BASE_URL=http://127.0.0.1:8799/v1 \
python -m uvicorn app.main:create_app --factory
```

Fault injection (test the broker's error handling, still free):

```bash
python scripts/fake_gateway.py --fail-first 1   # 429 the first request, then succeed → broker retries
python scripts/fake_gateway.py --status 503     # always fail → broker raises GatewayError after retries
```

## 3. Live gateway — spends credits

Only when you need to confirm against the real model. Needs a real `vck_…` key in
`app/backend/.env` and `LLM_PROVIDER=gateway`.

```bash
LLM_PROVIDER=gateway python -m app.cli.chat_smoke --stream
```

Cost is ~$0.00008/call; the key has a $50/month cap. The free tier rate-limits
`meta/llama-3.3-70b`, so sustained use needs paid credits topped up. Prefer modes 1–2
for day-to-day work and keep live runs deliberate.

## Notes

- `--skip-if-unconfigured` makes mode 1/3 exit 0 with `status: skipped` when no client
  is configured — handy in CI where the key may be absent.
- The broker is also covered by offline unit tests (`tests/test_ai_gateway.py`,
  `httpx.MockTransport`) — those need no server at all.
