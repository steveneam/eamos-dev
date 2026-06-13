from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.ai_gateway.retrieval import (
    Embedder,
    GatewayEmbedder,
    materialize_literature_embeddings,
)


def _build_embedder(settings: Settings) -> Embedder:
    if not settings.ai_gateway_api_key:
        raise SystemExit(
            "AI_GATEWAY_API_KEY is required to embed the corpus "
            "(set it in app/backend/.env or the environment)."
        )
    from app.services.ai_gateway.engine import AIGatewayEngine

    engine = AIGatewayEngine(
        api_key=settings.ai_gateway_api_key,
        model=settings.ai_gateway_model,
        provider_order=settings.ai_gateway_provider_order,
        base_url=settings.ai_gateway_base_url,
        timeout_seconds=settings.ai_gateway_timeout_seconds,
        max_retries=settings.ai_gateway_max_retries,
    )
    return GatewayEmbedder(engine, settings.rag_embedding_model)


def main(argv: list[str] | None = None, *, embedder: Embedder | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize the local literature-embedding vector store from the "
            "PubMed-local SQLite, embedding license-permitted gene-scoped articles "
            "through the AI Gateway. Offline action (never startup/deploy). Output "
            "is sanitized: counts only, never abstracts, local paths, or secrets."
        )
    )
    parser.add_argument("--source-db", type=Path, help="pubmed_local SQLite path")
    parser.add_argument("--output", type=Path, help="literature-embeddings SQLite path")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source-version")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "literature-embed-materialize-local"}
    if args.source_db is not None:
        settings_kwargs["pubmed_local_sqlite_path"] = args.source_db
    if args.output is not None:
        settings_kwargs["rag_sqlite_path"] = args.output
    if args.manifest is not None:
        settings_kwargs["rag_manifest_path"] = args.manifest
    settings = Settings(**settings_kwargs)

    if embedder is None:
        embedder = _build_embedder(settings)

    result = materialize_literature_embeddings(
        settings,
        embedder=embedder,
        source_db_path=args.source_db,
        output_path=args.output,
        manifest_path=args.manifest,
        source_version=args.source_version,
        batch_size=args.batch_size,
    )
    report = {
        "mode": "literature_embed_materialize",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "startup_download": "not_used",
            "request_time_materialization": "not_used",
            "patient_data": "not_used",
            # Embeddings are computed via the AI Gateway, so network IS used — but
            # only at this offline action, never at startup/deploy.
            "network": {"used": True, "provider": "vercel_ai_gateway"},
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "raw_source_rows_in_output": "blocked",
        },
        "materialization": result.to_sanitized_dict(),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if result.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
