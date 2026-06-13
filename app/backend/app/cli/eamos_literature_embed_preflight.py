from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.ai_gateway.retrieval import inspect_literature_store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only literature-embedding store preflight. Output is sanitized "
            "and never includes local paths, API keys, abstracts, or vectors."
        )
    )
    parser.add_argument("--db-path", type=Path)
    parser.add_argument("--manifest-path", type=Path)
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    settings_kwargs: dict[str, Any] = {"jwt_secret": "literature-embed-preflight-local"}
    if args.db_path is not None:
        settings_kwargs["rag_sqlite_path"] = args.db_path
    if args.manifest_path is not None:
        settings_kwargs["rag_manifest_path"] = args.manifest_path
    settings = Settings(**settings_kwargs)

    inspection = inspect_literature_store(settings)
    report = {
        "mode": "literature_embed_preflight",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready": inspection.ready,
        "status": inspection.status,
        "startup_download_allowed": False,
        "network_used": False,
        "article_count": inspection.article_count,
        "gene_pair_count": inspection.gene_pair_count,
        "embedding_model": inspection.embedding_model,
        "embedding_dim": inspection.embedding_dim,
        "source_version": inspection.source_version,
        "secret_values_emitted": False,
        "local_path_values_emitted": False,
        "abstract_values_emitted": False,
        "message": inspection.message,
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0 if inspection.ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
