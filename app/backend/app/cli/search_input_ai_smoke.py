from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.core.config import Settings, get_settings
from app.services.search_input_interpreter import SearchInputInterpreter

DEFAULT_PROMPT = "a frameshift beginning at Leucine 441, in the cystic fibrosis gene"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.search_input_ai_smoke",
        description=(
            "Run an opt-in smoke check for search-input AI extraction. Live mode "
            "respects provider settings and keeps the final report gated by "
            "deterministic validation plus source-backed candidate resolution."
        ),
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Plain-language search text to smoke.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run the smoke against the deterministic mock extractor instead of a live provider.",
    )
    parser.add_argument(
        "--force-enable",
        action="store_true",
        help="Set search_input_ai_enabled=true for this process. Does not override provider/API key.",
    )
    parser.add_argument(
        "--skip-if-unconfigured",
        action="store_true",
        help="Exit 0 with status=skipped when live provider settings are not configured.",
    )
    parser.add_argument(
        "--resolve-coordinates",
        action="store_true",
        help="Allow live coordinate resolution during interpretation.",
    )
    parser.add_argument("--expect-gene", help="Fail if the interpretation gene differs.")
    parser.add_argument("--expect-protein", help="Fail if protein_change differs.")
    parser.add_argument("--expect-mode", help="Fail if the interpretation mode differs.")
    parser.add_argument(
        "--expect-candidate-id",
        help="Fail if no returned candidate or auto-selected candidate has this ID.",
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
        search_input_ai_enabled=True,
        use_real_apis=False,
        max_upload_mb=5,
        debug=True,
        jwt_secret="search-input-ai-smoke",
    )


def _live_settings(args: argparse.Namespace) -> tuple[Settings | None, list[str]]:
    try:
        settings = get_settings()
    except Exception as exc:
        return None, [f"settings_unavailable:{type(exc).__name__}"]

    if args.force_enable and not settings.search_input_ai_enabled:
        settings = settings.model_copy(update={"search_input_ai_enabled": True})

    missing: list[str] = []
    if not settings.search_input_ai_enabled:
        missing.append("SEARCH_INPUT_AI_ENABLED is not true")
    if settings.llm_provider == "mock":
        missing.append("LLM_PROVIDER is mock")
    if not settings.openai_api_key:
        missing.append("OPENAI_API_KEY is not configured")
    return settings, missing


def _interpret(args: argparse.Namespace, settings: Settings) -> dict[str, object]:
    interpreter = SearchInputInterpreter(settings=settings)
    interpretation = interpreter.interpret(
        args.prompt,
        allow_ai=True,
        resolve_coordinates=args.resolve_coordinates,
    )
    return interpretation.model_dump(mode="json")


def _report_allowed(interpretation: dict[str, object]) -> bool:
    return bool(
        interpretation.get("mode") in {"deterministic", "ai_assisted", "auto_resolved"}
        and interpretation.get("confidence") != "low"
        and not interpretation.get("requires_confirmation")
    )


def _expectation_failures(args: argparse.Namespace, interpretation: dict[str, object]) -> list[str]:
    failures: list[str] = []
    if args.expect_gene and interpretation.get("gene") != args.expect_gene:
        failures.append(f"expected gene {args.expect_gene}, got {interpretation.get('gene')}")
    if args.expect_protein and interpretation.get("protein_change") != args.expect_protein:
        failures.append(
            f"expected protein_change {args.expect_protein}, "
            f"got {interpretation.get('protein_change')}"
        )
    if args.expect_mode and interpretation.get("mode") != args.expect_mode:
        failures.append(f"expected mode {args.expect_mode}, got {interpretation.get('mode')}")
    if args.expect_candidate_id:
        candidate_ids = {
            item.get("candidate_id")
            for item in interpretation.get("candidates", [])
            if isinstance(item, dict)
        }
        auto_selected = interpretation.get("auto_selected_candidate_id")
        if (
            args.expect_candidate_id not in candidate_ids
            and args.expect_candidate_id != auto_selected
        ):
            failures.append(f"expected candidate {args.expect_candidate_id}, got {candidate_ids}")
    if interpretation.get("confidence") == "low" and _report_allowed(interpretation):
        failures.append("low-confidence interpretation would be report-runnable")
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.mock:
        settings = _mock_settings()
        mode = "mock"
        missing: list[str] = []
    else:
        settings, missing = _live_settings(args)
        mode = "live"

    if settings is None or missing:
        payload = {
            "status": "skipped",
            "mode": mode,
            "prompt": args.prompt,
            "reasons": missing,
        }
        print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
        return 0 if args.skip_if_unconfigured else 2

    interpretation = _interpret(args, settings)
    failures = _expectation_failures(args, interpretation)
    payload = {
        "status": "failed" if failures else "passed",
        "mode": mode,
        "prompt": args.prompt,
        "report_allowed": _report_allowed(interpretation),
        "failures": failures,
        "interpretation": interpretation,
    }
    print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
