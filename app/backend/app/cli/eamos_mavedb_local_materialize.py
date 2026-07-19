from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from app.services.mavedb_local import (
    MAVEDB_ARCHIVE_RELEASE_DOI_V4,
    MAVEDB_ARCHIVE_SOURCE_URL_V4,
    MAVEDB_FIXTURE_RELEASE_PREFIX,
    MAVEDB_FIXTURE_SOURCE_URL,
    materialize_mavedb_local_store,
    verify_mavedb_archive_file,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a schema-v2 local MaveDB CC0 asset by streaming an already-acquired "
            "documented bulk ZIP only after verifying its pinned upstream digest. This performs no "
            "network, Supabase, Render, or provider mutation."
        )
    )
    parser.add_argument("--output", type=Path, help="destination SQLite path")
    parser.add_argument("--manifest-path", type=Path, help="destination manifest sidecar path")
    parser.add_argument("--source-version", help="source version label for the manifest")
    parser.add_argument(
        "--archive-path",
        type=Path,
        required=True,
        help="already-acquired archive whose published digest must be verified",
    )
    parser.add_argument(
        "--archive-digest-algorithm",
        choices=("md5", "sha256"),
        help="algorithm used by the published archive digest",
    )
    parser.add_argument(
        "--archive-digest",
        help="published digest for --archive-path",
    )
    parser.add_argument(
        "--fixture-only",
        action="store_true",
        help="mark synthetic test bytes as non-public fixture data",
    )
    parser.add_argument("--force", action="store_true", help="replace an existing destination")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero if not ready")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    proof_args = (args.archive_path, args.archive_digest_algorithm, args.archive_digest)
    if not all(proof_args):
        parser.error(
            "--archive-path, --archive-digest-algorithm, and --archive-digest are required together"
        )
    archive_proof = verify_mavedb_archive_file(
        args.archive_path,
        expected_digest_algorithm=args.archive_digest_algorithm,
        expected_digest_value=args.archive_digest,
        release_doi=(
            f"{MAVEDB_FIXTURE_RELEASE_PREFIX}cli"
            if args.fixture_only
            else MAVEDB_ARCHIVE_RELEASE_DOI_V4
        ),
        source_url=(
            MAVEDB_FIXTURE_SOURCE_URL if args.fixture_only else MAVEDB_ARCHIVE_SOURCE_URL_V4
        ),
        allow_synthetic_fixture=args.fixture_only,
    )

    settings = Settings(jwt_secret="mavedb-local-materialize")
    result = materialize_mavedb_local_store(
        settings,
        archive_path=args.archive_path,
        archive_proof=archive_proof,
        output_path=args.output,
        manifest_path=args.manifest_path,
        source_version=args.source_version,
        force=args.force,
    )
    payload = {
        "mode": "eamos_mavedb_local_materialize",
        "guardrails": {
            "network": "not_used",
            "supabase": "not_used",
            "render": "not_used",
            "provider_flips": "not_used",
            "startup_downloads": "not_used",
        },
        "materialization": result.to_sanitized_dict(),
    }
    print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
    return 1 if args.require_ready and not result.ready else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
