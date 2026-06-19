from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from app.services.indexed_sources import IndexedSourceError
from app.services.repeatmasker_local import (
    REPEATMASKER_SOURCE_ID,
    RepeatMaskerLocalError,
    RepeatMaskerLocalStore,
    build_repeatmasker_compact_index,
)

DEFAULT_REPEATMASKER_SOURCE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "source_assets"
    / "repeatmasker_rmsk_bb"
    / "rmsk.txt.gz"
)
DEFAULT_REPEATMASKER_INDEX_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "bio_assets"
    / "repeatmasker"
    / "repeatmasker.interval-index.jsonl"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Eamos compact RepeatMasker interval index from UCSC rmsk.txt.gz."
    )
    parser.add_argument(
        "--source-rmsk-path",
        type=Path,
        default=DEFAULT_REPEATMASKER_SOURCE_PATH,
        help="approved local UCSC rmsk.txt or rmsk.txt.gz source path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPEATMASKER_INDEX_PATH,
        help="compact RepeatMasker interval index output path",
    )
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="reload the written compact index and fail if it cannot be queried",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    try:
        result = build_repeatmasker_compact_index(
            source_rmsk_path=args.source_rmsk_path,
            output_path=args.output,
        )
        if args.require_ready:
            RepeatMaskerLocalStore(compact_index_path=args.output).provenance()
    except (OSError, IndexedSourceError, RepeatMaskerLocalError) as exc:
        print(
            json.dumps(
                {
                    "mode": "eamos_repeatmasker_compact_index_build",
                    "status": "failed",
                    "source_id": REPEATMASKER_SOURCE_ID,
                    "code": getattr(exc, "code", type(exc).__name__),
                    "message": str(exc),
                    "guardrails": _guardrails(),
                },
                indent=None if args.compact else 2,
                sort_keys=True,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "mode": "eamos_repeatmasker_compact_index_build",
                "status": "ready",
                "source_id": REPEATMASKER_SOURCE_ID,
                "result": asdict(result),
                "guardrails": _guardrails(),
            },
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )
    return 0


def _guardrails() -> dict[str, str]:
    return {
        "production_downloads": "not_used",
        "storage_uploads": "not_used",
        "render_disk_seed": "not_used",
        "local_evidence_enabled_flip": "not_used",
        "runtime_provider_flip": "not_used",
        "startup_materialization": "not_used",
    }


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
