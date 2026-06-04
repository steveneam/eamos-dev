from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Protocol

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.eamos_coordinate_resolver import (  # noqa: E402
    EamosCoordinateResolution,
    EamosLocalCoordinateResolver,
)
from scripts.validate_project_100_coordinates import _project_100_source_rows  # noqa: E402

FIXTURE_ROOT = BACKEND_ROOT / "app" / "fixtures"
DEFAULT_VCF_PATH = FIXTURE_ROOT / "hardening" / "project_100_mock_stack.vcf"
DEFAULT_TRUTH_PATH = FIXTURE_ROOT / "hardening" / "project_100_mock_stack.truth.json"
MANIFEST_PATH = FIXTURE_ROOT / "hardening" / "project_100_sample_manifest.json"


class CoordinateResolver(Protocol):
    def resolve(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str | None = None,
        accession: str | None = None,
        clinvar_variation_id: str | None = None,
    ) -> EamosCoordinateResolution | None:
        ...


class Project100MockVcfError(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a Project-100 mock VCF and truth manifest from the Eamos local "
            "coordinate resolver. ClinVar/SPDI and VariantValidator are not used."
        )
    )
    parser.add_argument("--output-vcf", type=Path, default=DEFAULT_VCF_PATH)
    parser.add_argument("--truth-manifest", type=Path, default=DEFAULT_TRUTH_PATH)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source_rows = _project_100_source_rows()
    if args.limit is not None:
        source_rows = source_rows[: args.limit]
    try:
        payload = generate_project_100_mock_vcf(
            output_vcf=args.output_vcf,
            truth_manifest=args.truth_manifest,
            source_rows=source_rows,
            compact=args.compact,
        )
    except Project100MockVcfError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(payload["coverage"], indent=2, sort_keys=True))
    return 0


def generate_project_100_mock_vcf(
    *,
    output_vcf: Path = DEFAULT_VCF_PATH,
    truth_manifest: Path = DEFAULT_TRUTH_PATH,
    source_rows: Iterable[dict[str, Any]] | None = None,
    resolver: CoordinateResolver | None = None,
    compact: bool = False,
) -> dict[str, Any]:
    rows = list(source_rows if source_rows is not None else _project_100_source_rows())
    owned_resolver = resolver is None
    local_resolver: CoordinateResolver = resolver or EamosLocalCoordinateResolver(
        coordinate_catalog_path=None
    )
    try:
        generated_rows, unresolved = _generate_rows(rows, local_resolver)
    finally:
        if owned_resolver:
            close = getattr(local_resolver, "close", None)
            if callable(close):
                close()

    payload = _truth_payload(generated_rows, unresolved)
    truth_manifest.parent.mkdir(parents=True, exist_ok=True)
    truth_manifest.write_text(
        json.dumps(payload, indent=None if compact else 2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if unresolved:
        raise Project100MockVcfError(
            f"Project-100 mock VCF unresolved rows: {len(unresolved)}; see {truth_manifest}"
        )

    output_vcf.parent.mkdir(parents=True, exist_ok=True)
    output_vcf.write_text(_vcf_text(generated_rows), encoding="utf-8", newline="\n")
    return payload


def _generate_rows(
    source_rows: list[dict[str, Any]],
    resolver: CoordinateResolver,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    generated_rows: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    for source_row in source_rows:
        resolved = resolver.resolve(
            gene=source_row["gene"],
            transcript=source_row["transcript"],
            cdna=source_row["cdna"],
            accession=source_row.get("accession"),
            clinvar_variation_id=source_row.get("clinvar_variation_id"),
        )
        if resolved is None:
            unresolved.append(
                {
                    "sample_id": str(source_row["sample_id"]),
                    "gene": str(source_row["gene"]),
                    "cdna": str(source_row["cdna"]),
                    "reason": "eamos_local_coordinate_unresolved",
                }
            )
            continue
        generated_rows.append(_generated_row(source_row, resolved))
    generated_rows.sort(key=_vcf_sort_key)
    return generated_rows, unresolved


def _generated_row(
    source_row: dict[str, Any],
    resolved: EamosCoordinateResolution,
) -> dict[str, Any]:
    truth = dict(source_row.get("truth") or {})
    return {
        "sample_id": source_row["sample_id"],
        "sample_kind": source_row["sample_kind"],
        "source_fixture": source_row["source_fixture"],
        "gene": source_row["gene"],
        "transcript": source_row["transcript"],
        "cdna": source_row["cdna"],
        "protein": source_row.get("protein"),
        "category": source_row.get("category"),
        "clinical_significance": source_row.get("clinical_significance"),
        "accession": source_row.get("accession"),
        "clinvar_variation_id": source_row.get("clinvar_variation_id"),
        "chrom": resolved.chrom,
        "pos": resolved.pos,
        "ref": resolved.ref,
        "alt": resolved.alt,
        "genomic_hg38": resolved.genomic_hg38,
        "genomic_hgvs": resolved.genomic_hgvs,
        "source": resolved.source,
        "confidence": resolved.confidence,
        "provenance": list(
            dict.fromkeys(
                [
                    *resolved.provenance,
                    "project_100_mock_vcf_generator",
                ]
            )
        ),
        "warnings": list(resolved.warnings),
        "truth": truth,
    }


def _truth_payload(
    rows: list[dict[str, Any]],
    unresolved: list[dict[str, str]],
) -> dict[str, Any]:
    genes = sorted({str(row["gene"]) for row in rows})
    return {
        "version": "2026-06-04-project-100-mock-vcf-v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "purpose": (
            "Project-100 synthetic VCF stack for batch/panel integration tests and "
            "frontend mock-to-backend replacement."
        ),
        "runtime_policy": (
            "Coordinates are generated with the Eamos local coordinate resolver. "
            "ClinVar/SPDI and VariantValidator are validation oracles only, not runtime "
            "coordinate providers for this artifact."
        ),
        "sources": {
            "project_100_manifest": _repo_path(MANIFEST_PATH),
            "coordinate_resolver": "app/backend/app/services/eamos_coordinate_resolver.py",
            "source_rows": "scripts.validate_project_100_coordinates._project_100_source_rows",
        },
        "coverage": {
            "rows": len(rows),
            "unresolved": len(unresolved),
            "genes": len(genes),
            "control_rows": sum(1 for row in rows if row["sample_kind"] == "reference_control"),
            "challenge_rows": sum(1 for row in rows if row["sample_kind"] == "clinvar_challenge"),
        },
        "genes": genes,
        "unresolved": unresolved,
        "rows": rows,
    }


def _vcf_text(rows: list[dict[str, Any]]) -> str:
    contigs = sorted({str(row["chrom"]) for row in rows}, key=_chrom_sort_value)
    lines = [
        "##fileformat=VCFv4.2",
        "##source=EamosProject100MockVcfGenerator",
        "##reference=GRCh38",
        '##INFO=<ID=SAMPLE_ID,Number=1,Type=String,Description="Project-100 sample id">',
        '##INFO=<ID=GENE,Number=1,Type=String,Description="Gene symbol">',
        '##INFO=<ID=HGVS_C,Number=1,Type=String,Description="Transcript cDNA HGVS">',
        '##INFO=<ID=HGVS_P,Number=1,Type=String,Description="Protein HGVS when available">',
        '##INFO=<ID=CLNSIG,Number=1,Type=String,Description="Fixture clinical significance">',
        '##INFO=<ID=CATEGORY,Number=1,Type=String,Description="Project-100 category">',
        '##INFO=<ID=SOURCE_FIXTURE,Number=1,Type=String,Description="Project-100 source fixture">',
        '##INFO=<ID=EXPECTED_PANEL,Number=0,Type=Flag,Description="Expected panel membership">',
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Synthetic heterozygous genotype">',
    ]
    lines.extend(f"##contig=<ID={contig}>" for contig in contigs)
    lines.append("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tPROJECT100")
    for row in rows:
        lines.append(
            "\t".join(
                [
                    str(row["chrom"]),
                    str(row["pos"]),
                    str(row["sample_id"]),
                    str(row["ref"]),
                    str(row["alt"]),
                    ".",
                    "PASS",
                    _info_field(row),
                    "GT",
                    "0/1",
                ]
            )
        )
    return "\n".join(lines) + "\n"


def _info_field(row: dict[str, Any]) -> str:
    truth = dict(row.get("truth") or {})
    fields = {
        "SAMPLE_ID": row.get("sample_id"),
        "GENE": row.get("gene"),
        "HGVS_C": row.get("cdna"),
        "HGVS_P": row.get("protein"),
        "CLNSIG": row.get("clinical_significance"),
        "CATEGORY": row.get("category"),
        "SOURCE_FIXTURE": row.get("source_fixture"),
    }
    parts = [f"{key}={_info_value(value)}" for key, value in fields.items() if value]
    if truth.get("expected_panel_membership") is True:
        parts.append("EXPECTED_PANEL")
    return ";".join(parts) if parts else "."


def _info_value(value: object) -> str:
    return (
        str(value)
        .replace("%", "%25")
        .replace(" ", "%20")
        .replace(";", "%3B")
        .replace("=", "%3D")
        .replace(",", "%2C")
        .replace("\t", "%09")
    )


def _vcf_sort_key(row: dict[str, Any]) -> tuple[int, int, str, str, str]:
    return (
        _chrom_sort_value(str(row["chrom"])),
        int(row["pos"]),
        str(row["ref"]),
        str(row["alt"]),
        str(row["sample_id"]),
    )


def _chrom_sort_value(chrom: str) -> int:
    normalized = chrom.removeprefix("chr").upper()
    if normalized.isdigit():
        return int(normalized)
    if normalized == "X":
        return 23
    if normalized == "Y":
        return 24
    if normalized in {"M", "MT"}:
        return 25
    return 10_000


def _repo_path(path: Path) -> str:
    return path.resolve().relative_to(BACKEND_ROOT.parents[1]).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
