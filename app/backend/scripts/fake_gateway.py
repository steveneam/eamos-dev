"""Local fake of the Vercel AI Gateway — OpenAI-compatible, zero-cost, offline.

Speaks the same `POST /v1/chat/completions` protocol the real gateway does
(streaming SSE + non-streaming), so it exercises the *real* broker code path
(`app/services/ai_gateway/engine.py`) without spending tokens or needing a real
key. Point the backend at it for offline development:

    # terminal 1 — the fake gateway
    python scripts/fake_gateway.py --port 8799

    # terminal 2 — the backend, wired to the fake (any dummy key works)
    LLM_PROVIDER=gateway \
    AI_GATEWAY_API_KEY=local-fake \
    AI_GATEWAY_BASE_URL=http://127.0.0.1:8799/v1 \
    python -m uvicorn app.main:create_app --factory

Then use /report's Ask Eamos chat (with NEXT_PUBLIC_AI_CHAT_ENABLED=true) or
scripts/chat_cli.py — all offline, all free.

Fault injection for testing the broker's error handling:
    --fail-first N   return HTTP 429 for the first N requests, then succeed
                     (exercises the 429 retry/backoff path)
    --status CODE    always return this HTTP status (e.g. 503)
"""

from __future__ import annotations

import argparse
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_CANNED = (
    "Based on the supplied evidence, {variant} is currently reported as {clinvar}. "
    "The in-silico predictors lean damaging while population and functional support "
    "remain limited, so the variant stays of uncertain significance pending further "
    "evidence. This is a local fake-gateway reply (no tokens were spent)."
)


def _generation_id(counter: int) -> str:
    return f"gen_localfake_{counter:020d}"


def _extract(messages: list[dict]) -> tuple[str, str]:
    """Pull a believable variant + clinvar label out of the last user message."""
    user = next((m for m in reversed(messages) if m.get("role") == "user"), {})
    content = str(user.get("content", ""))
    variant = "this variant"
    explicit = re.search(r'"variant"\s*:\s*"([^"]+)"', content)
    gene = re.search(r'"gene"\s*:\s*"([^"]+)"', content)
    cdot = re.search(r"(c\.[A-Za-z0-9>_.+-]+)", content)
    if explicit:
        variant = explicit.group(1)
    elif gene:
        variant = f"{gene.group(1)} {cdot.group(1)}".strip() if cdot else gene.group(1)
    clinvar = "uncertain significance"
    cm = re.search(r'"clinvar"\s*:\s*"([^"]+)"', content)
    if cm:
        clinvar = cm.group(1)
    return variant, clinvar


class Handler(BaseHTTPRequestHandler):
    server_version = "fake-gateway/1.0"
    protocol_version = "HTTP/1.0"  # read-until-close streaming, no chunked encoding

    def log_message(self, *_args) -> None:  # quiet by default
        pass

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        if self.path.rstrip("/").endswith("/v1/models"):
            self._json(200, {"object": "list", "data": [{"id": self.server.model}]})
        else:
            self._json(404, {"error": {"message": "not found"}})

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        if not self.path.rstrip("/").endswith("/chat/completions"):
            self._json(404, {"error": {"message": "not found"}})
            return

        srv = self.server
        srv.request_count += 1
        count = srv.request_count

        if srv.force_status:
            self._json(srv.force_status, {"error": {"message": f"forced {srv.force_status}"}})
            return
        if count <= srv.fail_first:
            self._json(
                429,
                {"error": {"message": "Rate limited (fake). Retry.", "type": "rate_limit_exceeded"}},
                extra_headers={"retry-after": "0"},
            )
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        messages = body.get("messages", [])
        stream = bool(body.get("stream"))
        order = (body.get("providerOptions", {}).get("gateway", {}) or {}).get("order") or ["groq"]
        variant, clinvar = _extract(messages)
        text = _CANNED.format(variant=variant, clinvar=clinvar)
        gen_id = _generation_id(count)
        usage = {
            "prompt_tokens": 110,
            "completion_tokens": len(text.split()),
            "total_tokens": 110 + len(text.split()),
            "cost": 0.0,
            "gateway_cost": 0.0,
            "market_cost": 0.0,
        }
        meta = {"gateway": {"generationId": gen_id, "routing": {"finalProvider": order[0]}}}

        if stream:
            self._stream(text, usage, meta)
        else:
            self._json(
                200,
                {
                    "id": gen_id,
                    "object": "chat.completion",
                    "model": srv.model,
                    "choices": [
                        {"index": 0, "message": {"role": "assistant", "content": text},
                         "finish_reason": "stop"}
                    ],
                    "usage": usage,
                    "providerMetadata": meta,
                },
            )

    def _stream(self, text: str, usage: dict, meta: dict) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        words = text.split(" ")
        for i, word in enumerate(words):
            token = word if i == len(words) - 1 else word + " "
            self._sse({"choices": [{"index": 0, "delta": {"content": token}}]})
            time.sleep(self.server.token_delay)
        self._sse(
            {
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": usage,
                "providerMetadata": meta,
            }
        )
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _sse(self, obj: dict) -> None:
        self.wfile.write(f"data: {json.dumps(obj)}\n\n".encode())
        self.wfile.flush()

    def _json(self, status: int, obj: dict, extra_headers: dict | None = None) -> None:
        payload = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    ap = argparse.ArgumentParser(description="Local OpenAI-compatible fake of the AI Gateway.")
    ap.add_argument("--port", type=int, default=8799)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--model", default="meta/llama-3.3-70b")
    ap.add_argument("--token-delay", type=float, default=0.02, help="seconds between streamed tokens")
    ap.add_argument("--fail-first", type=int, default=0, help="429 the first N requests, then succeed")
    ap.add_argument("--status", type=int, default=0, help="always return this HTTP status")
    args = ap.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.model = args.model
    httpd.token_delay = args.token_delay
    httpd.fail_first = args.fail_first
    httpd.force_status = args.status
    httpd.request_count = 0
    print(f"fake gateway on http://{args.host}:{args.port}/v1  (model={args.model})")
    if args.fail_first:
        print(f"  will 429 the first {args.fail_first} request(s)")
    if args.status:
        print(f"  will always return HTTP {args.status}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
