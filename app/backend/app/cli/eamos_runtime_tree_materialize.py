from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from app.services.runtime_tree_materialization import (
    DEFAULT_MINIMUM_FREE_AFTER_BYTES,
    RuntimeTreeMaterializationError,
    materialize_runtime_tree,
)

DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "runtime-tree-manifest-syd2.json"
DEFAULT_TARGET_ROOT = Path("/var/data/eamos/bio_assets")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize the frozen Eamos runtime tree from private Storage into an "
            "empty or verified-resume target. This command has no force/overwrite mode."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="verify and retain exact completed files, then fetch only missing items",
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--minimum-free-after-bytes",
        type=int,
        default=DEFAULT_MINIMUM_FREE_AFTER_BYTES,
    )
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = materialize_runtime_tree(
            Settings(jwt_secret="runtime-tree-materialization-operator"),
            manifest_path=args.manifest,
            target_root=args.target_root,
            resume=args.resume,
            preflight_only=args.preflight_only,
            minimum_free_after_bytes=args.minimum_free_after_bytes,
        )
    except RuntimeTreeMaterializationError as exc:
        result = {
            "mode": "eamos_runtime_tree_materialize",
            "ready": False,
            "status": exc.code,
            "details": exc.details,
            "local_path_values_emitted": False,
            "object_path_values_emitted": False,
            "secret_values_emitted": False,
        }
    except Exception:  # noqa: BLE001 - sanitize the operator boundary fail-closed
        result = {
            "mode": "eamos_runtime_tree_materialize",
            "ready": False,
            "status": "unexpected_error",
            "details": {},
            "local_path_values_emitted": False,
            "object_path_values_emitted": False,
            "secret_values_emitted": False,
        }

    output = {
        **result,
        "guardrails": {
            "empty_target_default": "required",
            "resume": "verify_exact_then_skip",
            "force_or_overwrite": "unavailable",
            "source": "private_storage_s3_only",
            "secrets_in_output": "blocked",
            "local_paths_in_output": "blocked",
            "object_paths_in_output": "blocked",
            "supabase_metadata_mutation": "not_used",
            "provider_or_deploy_mutation": "not_used",
            "startup_or_request_time_download": "not_used",
        },
    }
    print(json.dumps(output, indent=None if args.compact else 2, sort_keys=True))
    ready = output.get("ready") is True
    return 0 if ready or not args.require_ready else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
