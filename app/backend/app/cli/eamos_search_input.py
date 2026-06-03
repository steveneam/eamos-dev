from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from app.core.config import get_settings
from app.services.search_input_resolver import EamosSearchInputResolver, parse_search_text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.eamos_search_input",
        description="Resolve Eamos search-box variant text into per-source query inputs.",
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Variant search text. Quote queries that contain spaces.",
    )
    parser.add_argument("--gene", help="Gene symbol when the query text does not include one.")
    parser.add_argument("--transcript", help="Transcript accession to prefer for cDNA input.")
    parser.add_argument("--protein", help="Protein change alias to include in literature terms.")
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Read one query per line. For tab-separated notes, only the first column is used.",
    )
    parser.add_argument(
        "--real-apis",
        action="store_true",
        help="Force live source settings for MANE and coordinate resolution.",
    )
    parser.add_argument(
        "--fixture-mode",
        action="store_true",
        help="Force offline parsing without constructing backend Settings.",
    )
    parser.add_argument(
        "--resolve-coordinates",
        action="store_true",
        help=(
            "Resolve GRCh38 coordinates with the local Eamos resolver first. "
            "Live mode may fall back to VariantValidator only when local resolution misses."
        ),
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON.",
    )
    return parser


def _queries_from_args(args: argparse.Namespace) -> list[str]:
    queries: list[str] = []
    if args.input_file is not None:
        for line in args.input_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            query = stripped.split("\t", 1)[0].strip()
            if query:
                queries.append(query)
    if args.query:
        queries.append(" ".join(args.query).strip())
    return queries


def _settings_for_args(args: argparse.Namespace):
    if args.fixture_mode:
        return None
    settings = get_settings()
    if args.real_apis and not settings.use_real_apis:
        settings = settings.model_copy(update={"use_real_apis": True})
    return settings


def _resolution_to_dict(query: str, resolver: EamosSearchInputResolver, args: argparse.Namespace):
    parsed = parse_search_text(
        query,
        gene=args.gene,
        transcript=args.transcript,
        protein_change=args.protein,
    )
    resolution = resolver.resolve(
        gene=parsed.gene,
        cdna=parsed.cdna,
        transcript=parsed.transcript,
        protein_change=parsed.protein_change,
    )
    if parsed.warnings:
        warnings = [*parsed.warnings, *resolution.warnings]
    else:
        warnings = list(resolution.warnings)

    return {
        "submitted": query,
        "parsed": {
            "gene": parsed.gene,
            "cdna": parsed.cdna,
            "transcript": parsed.transcript,
            "protein_change": parsed.protein_change,
        },
        "normalized": {
            "gene": resolution.gene,
            "hgvs": resolution.hgvs,
            "kind": resolution.kind,
            "transcript": resolution.transcript,
            "transcript_hgvs": resolution.transcript_hgvs,
            "resolver_transcript": resolution.resolver_transcript,
            "resolver_transcript_hgvs": resolution.resolver_transcript_hgvs,
            "genomic_hg38": resolution.genomic_hg38,
            "genomic_hgvs": resolution.genomic_hgvs,
        },
        "local_coordinate_summary": resolution.local_coordinate_summary,
        "coordinate_resolution_audit": asdict(resolution.coordinate_resolution_audit),
        "source_inputs": asdict(resolution.source_inputs),
        "rsid_candidates": [asdict(candidate) for candidate in resolution.rsid_candidates],
        "warnings": warnings,
        "provenance": list(resolution.provenance),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    queries = _queries_from_args(args)
    if not queries:
        parser.error("provide a query or --input-file")

    if args.real_apis and args.fixture_mode:
        parser.error("--real-apis and --fixture-mode are mutually exclusive")

    settings = _settings_for_args(args)
    resolver = EamosSearchInputResolver(
        settings=settings,
        resolve_coordinates=args.resolve_coordinates,
    )
    payload = {
        "count": len(queries),
        "mode": "live" if settings is not None and settings.use_real_apis else "fixture",
        "coordinate_resolution": args.resolve_coordinates,
        "results": [_resolution_to_dict(query, resolver, args) for query in queries],
    }
    print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
