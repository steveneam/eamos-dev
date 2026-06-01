from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence

from app.core.config import Settings, get_settings
from app.rules.clinic_rules import ClinicRules
from app.schemas.lookup import LookupRequest, LookupResponse
from app.services.claim_provenance import (
    build_assertion,
    build_demo_audit,
    evaluate_claims,
    resolved_from_payload,
)
from app.services.lookup_service import LookupService
from app.services.search_input_resolver import parse_search_text
from app.tools.registry import build_tool_registry


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.eamos_press",
        description="Print report claim provenance and assert source-backed pills.",
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Variant text. Quote queries that contain spaces.",
    )
    parser.add_argument(
        "--sections",
        default="pills,popfreq,publications,trials",
        help="Comma-separated sections: pills,popfreq,publications,trials,clinical,acmg,disease,gene,protein,all.",
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Read one query per line. For tab-separated notes, only the first column is used.",
    )
    parser.add_argument(
        "--explain-pill",
        action="store_true",
        help="Accepted for contract parity; claim records always include source_facts in JSON.",
    )
    parser.add_argument(
        "--assert-source-backed-pills",
        action="store_true",
        help="Exit 2 if selected claims are unsupported or contradicted.",
    )
    parser.add_argument(
        "--assert-no-overclaim",
        action="store_true",
        help="Exit 2 only if selected claims are contradicted.",
    )
    parser.add_argument(
        "--audit-demo-sample",
        action="store_true",
        help="Emit demo_audit and exit 2 when the variant is not safe as a primary demo sample.",
    )
    parser.add_argument("--gene", help="Gene symbol when query text omits it.")
    parser.add_argument("--transcript", help="Transcript accession to prefer for cDNA input.")
    parser.add_argument("--protein", help="Protein change alias to include in lookup.")
    parser.add_argument(
        "--base-url",
        help="Read a deployed lookup response over HTTP instead of running in-process.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Bypass source cache where the underlying lookup service supports it.",
    )
    parser.add_argument(
        "--real-apis",
        action="store_true",
        help="Force USE_REAL_APIS=true for in-process lookup.",
    )
    parser.add_argument(
        "--fixture-mode",
        action="store_true",
        help="Force fixture/offline lookup settings for in-process runs.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    queries = _queries_from_args(args)
    if not queries:
        parser.error("provide a query")
    if args.real_apis and args.fixture_mode:
        parser.error("--real-apis and --fixture-mode are mutually exclusive")
    if args.assert_source_backed_pills and args.assert_no_overclaim:
        parser.error(
            "--assert-source-backed-pills and --assert-no-overclaim are mutually exclusive"
        )

    mode = "http" if args.base_url else "in_process"
    results = [_run_one_query(query, args, mode=mode) for query in queries]
    exit_code = 2 if any(not result["_passed"] for result in results) else 0
    for result in results:
        result.pop("_passed", None)
    if len(results) == 1 and args.input_file is None:
        output = results[0]
    else:
        output = {"count": len(results), "mode": mode, "results": results}

    print(json.dumps(output, indent=None if args.compact else 2, sort_keys=True))
    return exit_code


def _queries_from_args(args: argparse.Namespace) -> list[str]:
    queries: list[str] = []
    if args.input_file is not None:
        for line in args.input_file.read_text(encoding="utf-8-sig").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            query = stripped.split("\t", 1)[0].strip()
            if query:
                queries.append(query)
    if args.query:
        queries.append(" ".join(args.query).strip())
    return queries


def _run_one_query(query: str, args: argparse.Namespace, *, mode: str) -> dict[str, Any]:
    lookup_request = _lookup_request_from_args(query, args)
    if args.base_url:
        lookup = _lookup_http(args.base_url, lookup_request, refresh=args.refresh)
    else:
        lookup = _lookup_in_process(lookup_request, args)

    evaluation = evaluate_claims(
        lookup["payload"],
        lookup["evidence_map"],
        lookup["source_statuses"],
        sections=args.sections,
    )
    assertion = _assertion_for_args(evaluation["sections"], args)
    output: dict[str, Any] = {
        "query": query,
        "resolved": resolved_from_payload(lookup["payload"]),
        "mode": mode,
        "source_statuses": lookup["source_statuses"],
        "sections": evaluation["sections"],
        "summary": evaluation["summary"],
        "assert": assertion,
        "_passed": assertion["passed"],
    }
    if args.audit_demo_sample:
        demo_audit = build_demo_audit(evaluation["sections"], lookup["source_statuses"])
        output["demo_audit"] = demo_audit
        output["_passed"] = output["_passed"] and demo_audit["allowed_as_primary_demo_sample"]
    return output


def _assertion_for_args(
    sections: Sequence[dict[str, Any]], args: argparse.Namespace
) -> dict[str, Any]:
    if args.assert_source_backed_pills:
        return build_assertion(sections, mode="source_backed_pills")
    if args.assert_no_overclaim:
        return build_assertion(sections, mode="no_overclaim")
    return {"mode": "none", "passed": True, "failed_claim_ids": []}


def _lookup_request_from_args(query: str, args: argparse.Namespace) -> LookupRequest:
    parsed = parse_search_text(
        query,
        gene=args.gene,
        transcript=args.transcript,
        protein_change=args.protein,
    )
    if parsed.gene and parsed.cdna:
        return LookupRequest(
            gene=parsed.gene,
            cdna=parsed.cdna,
            transcript=parsed.transcript,
            protein_change=parsed.protein_change,
        )
    return LookupRequest(search_text=query)


def _lookup_in_process(request: LookupRequest, args: argparse.Namespace) -> dict[str, Any]:
    settings = _settings_for_args(args)
    service = LookupService(
        tool_registry=build_tool_registry(settings),
        rule_engine=ClinicRules(),
        settings=settings,
    )
    result = service.lookup_with_evidence_context(request, refresh=args.refresh)
    source_statuses = dict(result.evidence_statuses)
    if not source_statuses:
        source_statuses = {item.source: item.status for item in result.response.evidence}
    return {
        "payload": result.response.report_payload,
        "evidence_map": result.evidence_map,
        "source_statuses": source_statuses,
    }


def _lookup_http(base_url: str, request: LookupRequest, *, refresh: bool) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/api/v1/lookup?include_lazy_sections=true"
    if refresh:
        url += "&refresh=true"
    body = json.dumps(request.model_dump(mode="json", exclude_none=True)).encode("utf-8")
    http_request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(f"lookup HTTP request failed: {exc}") from exc
    response_model = LookupResponse.model_validate(payload)
    return {
        "payload": response_model.report_payload,
        "evidence_map": {},
        "source_statuses": {item.source: item.status for item in response_model.evidence},
    }


def _settings_for_args(args: argparse.Namespace) -> Settings:
    if args.fixture_mode:
        return Settings(jwt_secret="eamos-press-fixture-secret", use_real_apis=False)
    settings = get_settings()
    if args.real_apis and not settings.use_real_apis:
        settings = settings.model_copy(update={"use_real_apis": True})
    return settings


if __name__ == "__main__":
    raise SystemExit(main())
