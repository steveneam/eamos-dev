from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.crispr_tide import CrisprTideInputError, analyze_crispr_tide_observed
from app.services.trace_parser import TraceParseError, parse_ab1_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the local observed-only CRISPR TIDE-style analyzer on two AB1 traces."
    )
    parser.add_argument("--control", type=Path, required=True, help="control AB1 trace path")
    parser.add_argument("--edited", type=Path, required=True, help="edited AB1 trace path")
    parser.add_argument(
        "--cut-site-index",
        type=int,
        required=True,
        help="1-based Cas cut site index within both parsed trace consensus sequences",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    try:
        control_bytes = _read_trace(args.control)
        edited_bytes = _read_trace(args.edited)
        control_trace = parse_ab1_bytes(control_bytes)
        edited_trace = parse_ab1_bytes(edited_bytes)
        result = analyze_crispr_tide_observed(
            control_trace=control_trace,
            edited_trace=edited_trace,
            cut_site_index=args.cut_site_index,
        )
    except (OSError, TraceParseError, CrisprTideInputError) as exc:
        print(
            json.dumps(
                _error_report(exc),
                indent=None if args.compact else 2,
                sort_keys=True,
            )
        )
        return 2

    report = {
        "mode": "local_observed_tide",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guardrails": {
            "network": "not_used",
            "server": "not_used",
            "prediction": "not_used",
            "lindel": "not_used",
        },
        "inputs": {
            "control": _file_summary(args.control, control_bytes),
            "edited": _file_summary(args.edited, edited_bytes),
            "cut_site_index": args.cut_site_index,
            "control_base_calls": len(control_trace.sequence),
            "edited_base_calls": len(edited_trace.sequence),
        },
        "result": result.model_dump(mode="json"),
    }
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return 0


def _read_trace(path: Path) -> bytes:
    return path.read_bytes()


def _file_summary(path: Path, data: bytes) -> dict[str, Any]:
    return {
        "name": path.name,
        "size_bytes": len(data),
    }


def _error_report(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, TraceParseError):
        code = exc.code
        message = exc.message
        warnings = [exc.code]
    elif isinstance(exc, CrisprTideInputError):
        code = exc.code
        message = exc.message
        warnings = exc.warnings
    else:
        code = "crispr_tide_file_read_failed"
        message = "Unable to read one of the supplied trace files."
        warnings = [code]

    return {
        "mode": "local_observed_tide",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "warnings": warnings,
        },
    }


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
