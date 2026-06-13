from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.crispr_offtarget_index import verify_crispr_offtarget_index
from app.services.crispr_offtarget_screening import (
    CRISPR_OFFTARGET_PROVIDER_AUTO,
    CRISPR_OFFTARGET_PROVIDER_INDEXED_SQLITE,
    CRISPR_OFFTARGET_PROVIDER_MOCK,
)


def build_crispr_offtarget_preflight(
    *,
    settings: Settings,
    index_path: Path | None = None,
    provider: str | None = None,
    genome_build: str = "GRCh38",
    min_target_count: int = 1,
    generated_at: str | None = None,
) -> dict[str, Any]:
    configured_provider = _normalize_provider(provider or settings.crispr_offtarget_provider)
    resolved_index_path = _settings_path(
        settings,
        index_path if index_path is not None else settings.crispr_offtarget_index_path,
    )
    indexed_sqlite = verify_crispr_offtarget_index(
        resolved_index_path,
        genome_build=genome_build,
        min_target_count=min_target_count,
    )
    ready_to_flip = bool(indexed_sqlite["verification_ready"])
    auto_fallback = configured_provider == CRISPR_OFFTARGET_PROVIDER_AUTO and not ready_to_flip
    forced_fail_closed = (
        configured_provider == CRISPR_OFFTARGET_PROVIDER_INDEXED_SQLITE and not ready_to_flip
    )
    public_runtime_available = bool(
        configured_provider == CRISPR_OFFTARGET_PROVIDER_MOCK
        or ready_to_flip
        or configured_provider == CRISPR_OFFTARGET_PROVIDER_AUTO
    )

    return {
        "mode": "crispr_offtarget_preflight",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "network_used": False,
            "mutations_performed": False,
            "render_env_changed": False,
            "provider_flip_performed": False,
            "startup_downloads_allowed": False,
            "request_time_source_search_allowed": False,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
        },
        "configured_provider": configured_provider,
        "ready_to_flip": ready_to_flip,
        "public_runtime_available": public_runtime_available,
        "runtime_status": _runtime_status(
            configured_provider=configured_provider,
            ready_to_flip=ready_to_flip,
            forced_fail_closed=forced_fail_closed,
        ),
        "provider_policy": {
            "auto_mode_warns_and_uses_mock_fallback": auto_fallback,
            "forced_indexed_sqlite_fails_closed": forced_fail_closed,
            "mock_provider_allowed": configured_provider == CRISPR_OFFTARGET_PROVIDER_MOCK,
        },
        "indexed_sqlite": indexed_sqlite,
        "next_action": _next_action(
            configured_provider=configured_provider,
            ready_to_flip=ready_to_flip,
            forced_fail_closed=forced_fail_closed,
        ),
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight the local Eamos SpCas9 off-target SQLite runtime without "
            "network calls, env changes, or local path emission."
        )
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        help="SQLite index path to inspect; defaults to configured CRISPR_OFFTARGET_INDEX_PATH.",
    )
    parser.add_argument(
        "--provider",
        choices=(
            CRISPR_OFFTARGET_PROVIDER_AUTO,
            CRISPR_OFFTARGET_PROVIDER_INDEXED_SQLITE,
            CRISPR_OFFTARGET_PROVIDER_MOCK,
        ),
        help="Provider mode to evaluate; defaults to configured CRISPR_OFFTARGET_PROVIDER.",
    )
    parser.add_argument("--genome-build", default="GRCh38")
    parser.add_argument("--min-target-count", type=int, default=1)
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    return parser


def cli_main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    settings = Settings(jwt_secret="crispr-offtarget-preflight-local")
    report = build_crispr_offtarget_preflight(
        settings=settings,
        index_path=args.index_path,
        provider=args.provider,
        genome_build=args.genome_build,
        min_target_count=args.min_target_count,
    )
    payload = _compact_report(report) if args.compact else report
    print(json.dumps(payload, sort_keys=True))
    return 0 if report["ready_to_flip"] or not args.require_ready else 2


def _compact_report(report: dict[str, Any]) -> dict[str, Any]:
    indexed = report["indexed_sqlite"]
    return {
        "mode": report["mode"],
        "configured_provider": report["configured_provider"],
        "ready_to_flip": report["ready_to_flip"],
        "public_runtime_available": report["public_runtime_available"],
        "runtime_status": report["runtime_status"],
        "provider_policy": report["provider_policy"],
        "indexed_sqlite": {
            "ready": indexed["ready"],
            "status": indexed["status"],
            "verification_ready": indexed["verification_ready"],
            "genome_build_matches": indexed["genome_build_matches"],
            "target_count": indexed["target_count"],
            "target_count_meets_min": indexed["target_count_meets_min"],
            "local_path_values_emitted": indexed["local_path_values_emitted"],
        },
        "guardrails": report["guardrails"],
        "next_action": report["next_action"],
    }


def _settings_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _normalize_provider(provider: str) -> str:
    return provider.strip().lower() or CRISPR_OFFTARGET_PROVIDER_AUTO


def _runtime_status(
    *,
    configured_provider: str,
    ready_to_flip: bool,
    forced_fail_closed: bool,
) -> str:
    if configured_provider == CRISPR_OFFTARGET_PROVIDER_MOCK:
        return "mock_fixture"
    if ready_to_flip:
        return "indexed_ready"
    if forced_fail_closed:
        return "forced_indexed_sqlite_not_ready_fail_closed"
    if configured_provider == CRISPR_OFFTARGET_PROVIDER_AUTO:
        return "auto_mock_fallback_not_ready_to_flip"
    return "unknown_provider"


def _next_action(
    *,
    configured_provider: str,
    ready_to_flip: bool,
    forced_fail_closed: bool,
) -> str | None:
    if ready_to_flip:
        return None
    if forced_fail_closed:
        return "Mount and verify the SpCas9 SQLite index before using indexed_sqlite mode."
    if configured_provider == CRISPR_OFFTARGET_PROVIDER_AUTO:
        return "Keep auto mode until the SpCas9 SQLite index is mounted and verified."
    if configured_provider == CRISPR_OFFTARGET_PROVIDER_MOCK:
        return "Mock provider is available for non-source-backed fallback only."
    return "Use auto, mock, or indexed_sqlite."


def main(argv: list[str] | None = None) -> int:
    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(cli_main())
