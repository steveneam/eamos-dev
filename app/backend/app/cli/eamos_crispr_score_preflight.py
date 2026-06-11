from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.services.crispr_design import (
    CRISPR_PROVIDER_LOCAL_DETERMINISTIC,
    inspect_crisprscore_r_runtime,
)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preflight the EAMOS crisprScore R runtime without emitting local paths."
    )
    parser.add_argument(
        "--provider",
        default=os.getenv("CRISPR_PROVIDER", CRISPR_PROVIDER_LOCAL_DETERMINISTIC),
        help="Configured CRISPR provider. Defaults to CRISPR_PROVIDER or local_deterministic.",
    )
    parser.add_argument(
        "--rscript",
        type=Path,
        default=os.getenv("CRISPR_RSCRIPT_PATH", "Rscript"),
        help="Rscript executable name or configured file path.",
    )
    parser.add_argument(
        "--ruleset3-conda-env",
        default=os.getenv("CRISPR_RULESET3_CONDA_ENV"),
        help="Optional RuleSet3 conda environment path/name.",
    )
    parser.add_argument(
        "--lindel-conda-env",
        default=os.getenv("CRISPR_LINDEL_CONDA_ENV"),
        help="Optional Lindel conda environment path/name.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print only availability, status, checks, and score-family readiness.",
    )
    return parser


def cli_main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    inspection = inspect_crisprscore_r_runtime(
        configured_provider=args.provider,
        rscript_path=args.rscript,
        rule_set3_conda_env=args.ruleset3_conda_env,
        lindel_conda_env=args.lindel_conda_env,
    )
    payload = inspection.to_sanitized_dict()
    if args.compact:
        payload = {
            "available": payload["available"],
            "status": payload["status"],
            "configured_provider": payload["configured_provider"],
            "checks": payload["checks"],
            "score_families": payload["score_families"],
            "local_path_values_emitted": payload["local_path_values_emitted"],
        }
    print(json.dumps(payload, sort_keys=True))
    return 0 if inspection.available or inspection.status == "disabled" else 1


if __name__ == "__main__":
    raise SystemExit(cli_main())
