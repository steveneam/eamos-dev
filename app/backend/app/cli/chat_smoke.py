from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from app.agents.client import build_gateway_chat_client, build_lookup_chat_chain
from app.core.config import Settings, get_settings
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService

DEFAULT_QUESTION = "What does the current evidence show about this variant?"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.chat_smoke",
        description=(
            "Opt-in smoke check for the Ask-Eamos variant chat. Uses the same "
            "ChatService + broker selection as the app, so it honours LLM_PROVIDER. "
            "Run with --mock for a free deterministic answer, or point "
            "AI_GATEWAY_BASE_URL at scripts/fake_gateway.py for a free, realistic "
            "offline gateway. Live mode (LLM_PROVIDER=gateway, real key) spends credits."
        ),
    )
    parser.add_argument("--question", default=DEFAULT_QUESTION, help="The question to ask.")
    parser.add_argument("--gene", default="RPE65")
    parser.add_argument("--hgvs", default="NM_000329.3:c.260A>G")
    parser.add_argument("--protein", default="p.Asp87Gly")
    parser.add_argument("--consequence", default="missense_variant")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run against the deterministic mock provider instead of a live/gateway client.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Echo tokens to stderr as they arrive (stdout stays clean JSON).",
    )
    parser.add_argument(
        "--skip-if-unconfigured",
        action="store_true",
        help="Exit 0 with status=skipped when no live/gateway chat client is configured.",
    )
    parser.add_argument(
        "--expect-contains",
        help="Fail if the answer does not contain this substring (case-insensitive).",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON.",
    )
    return parser


def _mock_settings() -> Settings:
    return Settings(
        upload_dir=Path("./data/uploads"),
        final_report_dir=Path("./data/final_reports"),
        database_url="sqlite+pysqlite:///./data/app.db",
        llm_provider="mock",
        use_real_apis=False,
        jwt_secret="chat-smoke",
    )


def _chat_request(args: argparse.Namespace) -> ChatRequest:
    return ChatRequest.model_validate(
        {
            "question": args.question,
            "variant_context": {
                "patient_id": "chat-smoke",
                "variant_summary_rows": [
                    {
                        "gene": args.gene,
                        "transcript_hgvs": args.hgvs,
                        "protein_change": args.protein,
                        "consequence": args.consequence,
                    }
                ]
            },
            "history": [],
        }
    )


def _stream_answer(service: ChatService, request: ChatRequest, echo: bool) -> str:
    tokens: list[str] = []
    for token in service.respond_stream(request):
        tokens.append(token)
        if echo:
            sys.stderr.write(token)
            sys.stderr.flush()
    if echo:
        sys.stderr.write("\n")
    return "".join(tokens).strip()


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.mock:
        settings: Settings | None = _mock_settings()
        client = None  # mock path uses no client
        mode = "mock"
    else:
        try:
            settings = get_settings()
        except Exception as exc:
            settings = None
            client = None
            mode = "live"
            payload = {"status": "skipped", "mode": mode, "reasons": [f"settings:{type(exc).__name__}"]}
            print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
            return 0 if args.skip_if_unconfigured else 2
        client = build_gateway_chat_client(settings) or build_lookup_chat_chain(settings)
        mode = "live"

    if mode == "live" and client is None:
        payload = {
            "status": "skipped",
            "mode": mode,
            "reasons": [f"no chat client for LLM_PROVIDER={settings.llm_provider!r} (gateway key / OpenAI key missing)"],
        }
        print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
        return 0 if args.skip_if_unconfigured else 2

    service = ChatService(settings=settings, llm_client=client)
    answer = _stream_answer(service, _chat_request(args), echo=args.stream)

    failures: list[str] = []
    if not answer:
        failures.append("empty answer")
    if args.expect_contains and args.expect_contains.lower() not in answer.lower():
        failures.append(f"answer does not contain {args.expect_contains!r}")

    payload = {
        "status": "failed" if failures else "passed",
        "mode": mode,
        "provider": settings.llm_provider,
        "gateway_base_url": settings.ai_gateway_base_url if mode == "live" else None,
        "question": args.question,
        "answer": answer,
        "failures": failures,
    }
    print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
