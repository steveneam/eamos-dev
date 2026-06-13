from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.compact_coordinate_index_builder import build_compact_coordinate_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the compact coordinate index from approved raw GFF inputs. "
            "This is an offline operator action; runtime must use the emitted "
            "JSONL/JSONL.GZ artifact, not raw GFF scans."
        )
    )
    parser.add_argument("--mane-gff", type=Path)
    parser.add_argument("--refseq-gff", type=Path)
    parser.add_argument("--gff", action="append", type=Path, default=[])
    parser.add_argument("--gene", action="append", default=[])
    parser.add_argument("--gene-list", type=Path)
    parser.add_argument("--all-genes", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--artifact-version")
    parser.add_argument("--genome-build", default="GRCh38")
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument("--require-ready", action="store_true", help="exit non-zero unless ready")
    args = parser.parse_args(argv)

    generated_at = datetime.now(timezone.utc).isoformat()
    gff_paths = [path for path in (args.mane_gff, args.refseq_gff, *args.gff) if path is not None]
    genes = _read_genes(args.gene, args.gene_list)
    if not args.all_genes and not genes:
        report = _report(
            generated_at=generated_at,
            build={
                "status": "gene_scope_required",
                "ready": False,
                "warnings": ["pass --gene, --gene-list, or --all-genes"],
            },
        )
        print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
        return 2

    if not gff_paths:
        report = _report(
            generated_at=generated_at,
            build={
                "status": "source_unconfigured",
                "ready": False,
                "warnings": ["pass --mane-gff, --refseq-gff, or --gff"],
            },
        )
        print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
        return 2

    result = build_compact_coordinate_index(
        output_path=args.output,
        gff_paths=gff_paths,
        genes=genes,
        discover_all_genes=args.all_genes,
        artifact_version=args.artifact_version,
        genome_build=args.genome_build,
        generated_at=generated_at,
    )
    report = _report(generated_at=generated_at, build=result.to_sanitized_dict())
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))

    return 0 if result.ready or not args.require_ready else 2


def _read_genes(raw_genes: list[str], gene_list_path: Path | None) -> tuple[str, ...]:
    genes = list(raw_genes)
    if gene_list_path is not None and gene_list_path.is_file():
        genes.extend(
            line.split("#", 1)[0].strip()
            for line in gene_list_path.read_text(encoding="utf-8").splitlines()
        )
    normalized: set[str] = set()
    for item in genes:
        for gene in item.replace(",", "\n").splitlines():
            value = gene.strip().upper()
            if value:
                normalized.add(value)
    return tuple(sorted(normalized))


def _report(*, generated_at: str, build: dict[str, object]) -> dict[str, object]:
    return {
        "mode": "eamos_compact_index_build",
        "generated_at": generated_at,
        "guardrails": {
            "network": "not_used",
            "startup_downloads": "not_used",
            "runtime_raw_gff_scan": "not_used",
            "offline_raw_gff_scan": "build_only",
            "variant_evidence_inference": "not_used",
            "clinvar_or_clingen_inference": "not_used",
            "secret_values_emitted": False,
            "local_paths_in_output": False,
        },
        "build": build,
    }


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
