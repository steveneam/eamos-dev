from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.parse import quote, urlencode
from urllib.request import urlopen

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.eamos_coordinate_resolver import (  # noqa: E402
    EamosCoordinateResolution,
    EamosLocalCoordinateResolver,
)
from app.services.search_input_resolver import _variant_validator_summary  # noqa: E402
from app.services.sequence_context import (  # noqa: E402
    NC_CHROMOSOME_ACCESSIONS,
    genomic_variant_id_to_refseq_hgvs,
)

FIXTURE_ROOT = BACKEND_ROOT / "app" / "fixtures"
MANIFEST_PATH = FIXTURE_ROOT / "hardening" / "project_100_sample_manifest.json"
STACK_PATH = FIXTURE_ROOT / "tools" / "clinvar_gene_agnostic_report_stack.json"
DEFAULT_OUTPUT_PATH = FIXTURE_ROOT / "hardening" / "project_100_coordinate_validation.json"

NCBI_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_VARIATION_API = "https://api.ncbi.nlm.nih.gov/variation/v0"
VARIANT_VALIDATOR_API = "https://rest.variantvalidator.org"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the Eamos local coordinate resolver on the project-100 hardening stack. "
            "ClinVar/SPDI and VariantValidator are oracle checks only, never runtime "
            "coordinate providers."
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--validate-variant-validator",
        action="store_true",
        help="Validate generated VCF fields against VariantValidator transcript HGVS responses.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.12)
    parser.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source_rows = _project_100_source_rows()
    variation_ids = [
        row["clinvar_variation_id"]
        for row in source_rows
        if row.get("clinvar_variation_id")
    ]
    clinvar_summaries = _fetch_clinvar_summaries(
        variation_ids,
        timeout_seconds=args.timeout_seconds,
    )
    local_resolver = EamosLocalCoordinateResolver(coordinate_catalog_path=None)

    output_rows: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    stats = {
        "total": len(source_rows),
        "local_resolved": 0,
        "clinvar_oracle_resolved": 0,
        "clinvar_oracle_matched": 0,
        "variant_validator_oracle_resolved": 0,
        "variant_validator_oracle_matched": 0,
    }
    validation_failures: list[dict[str, str]] = []

    for source_row in source_rows:
        local = local_resolver.resolve(
            gene=source_row["gene"],
            transcript=source_row["transcript"],
            cdna=source_row["cdna"],
            accession=source_row.get("accession"),
            clinvar_variation_id=source_row.get("clinvar_variation_id"),
        )
        clinvar = None
        if source_row.get("clinvar_variation_id"):
            clinvar = _clinvar_coordinate(
                clinvar_summaries[source_row["clinvar_variation_id"]],
                timeout_seconds=args.timeout_seconds,
            )
            if clinvar is not None:
                stats["clinvar_oracle_resolved"] += 1
            time.sleep(args.sleep_seconds)

        if local is None:
            unresolved.append(
                {
                    "sample_id": source_row["sample_id"],
                    "gene": source_row["gene"],
                    "cdna": source_row["cdna"],
                    "reason": "eamos_local_coordinate_unresolved",
                }
            )
            continue

        resolution = local
        validation = _validation(local=local, clinvar=clinvar)
        stats["local_resolved"] += 1
        if validation.get("clinvar_match") is True:
            stats["clinvar_oracle_matched"] += 1
        elif clinvar is not None:
            validation_failures.append(
                {
                    "sample_id": source_row["sample_id"],
                    "oracle": "clinvar_spdi",
                    "eamos": resolution.genomic_hg38,
                    "oracle_variant_id": clinvar.genomic_hg38,
                }
            )

        if args.validate_variant_validator:
            vv = _variant_validator_coordinate(
                transcript=source_row["transcript"],
                cdna=source_row["cdna"],
                timeout_seconds=args.timeout_seconds,
            )
            validation["variant_validator_match"] = _coordinate_match(resolution, vv)
            validation["variant_validator_variant_id"] = vv.genomic_hg38 if vv else None
            validation["variant_validator_unavailable"] = vv is None
            if vv is not None:
                stats["variant_validator_oracle_resolved"] += 1
            if validation["variant_validator_match"] is True:
                stats["variant_validator_oracle_matched"] += 1
            else:
                validation_failures.append(
                    {
                        "sample_id": source_row["sample_id"],
                        "oracle": "variant_validator",
                        "eamos": resolution.genomic_hg38,
                        "oracle_variant_id": vv.genomic_hg38 if vv else "",
                    }
                )
            time.sleep(args.sleep_seconds)

        output_rows.append(
            {
                **source_row,
                "chrom": resolution.chrom,
                "pos": resolution.pos,
                "ref": resolution.ref,
                "alt": resolution.alt,
                "genomic_hg38": resolution.genomic_hg38,
                "genomic_hgvs": resolution.genomic_hgvs,
                "canonical_spdi": resolution.canonical_spdi,
                "source": resolution.source,
                "confidence": resolution.confidence,
                "provenance": list(
                    dict.fromkeys(
                        [
                            *resolution.provenance,
                            "project_100_coordinate_validation",
                        ]
                    )
                ),
                "warnings": list(resolution.warnings),
                "validation": validation,
            }
        )

    payload = {
        "version": "2026-06-04-project-100-coordinate-validation-v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "purpose": (
            "Oracle validation snapshot for Eamos local coordinate resolution on the project-100 stack."
        ),
        "runtime_policy": (
            "Runtime uses the Eamos local coordinate resolver over local MANE/RefSeq transcript "
            "geometry and the local hg38 reference. This file is not a runtime coordinate provider. "
            "ClinVar/SPDI and VariantValidator are validation oracles only."
        ),
        "sources": {
            "project_100_manifest": _repo_path(MANIFEST_PATH),
            "challenge_stack": _repo_path(STACK_PATH),
            "clinvar_esummary": f"{NCBI_EUTILS}/esummary.fcgi",
            "ncbi_variation_spdi_vcf_fields": f"{NCBI_VARIATION_API}/spdi/{{spdi}}/vcf_fields",
            "variant_validator": (
                f"{VARIANT_VALIDATOR_API}/VariantValidator/variantvalidator/GRCh38/"
                "{transcript_hgvs}/all"
            ),
        },
        "coverage": {
            "rows": len(output_rows),
            "unresolved": len(unresolved),
            "validation_failures": len(validation_failures),
            **stats,
        },
        "unresolved": unresolved,
        "validation_failures": validation_failures,
        "rows": output_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=None if args.compact else 2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["coverage"], indent=2, sort_keys=True))
    if unresolved or validation_failures:
        return 1
    return 0


def _project_100_source_rows() -> list[dict[str, Any]]:
    manifest = _json(MANIFEST_PATH)
    stack = _json(STACK_PATH)

    stack_by_gene = {entry["gene"]: entry["variants"] for entry in stack["stack_genes"]}
    rows: list[dict[str, Any]] = []

    for gene_entry in manifest["genes"]:
        gene = gene_entry["gene"]
        control = gene_entry["control_sample"]
        rows.append(
            {
                "sample_id": f"HC-{gene}-CTRL",
                "sample_kind": "reference_control",
                "source_fixture": "control_queries",
                "gene": gene,
                "transcript": control["transcript"],
                "cdna": control["cdna"],
                "protein": control.get("protein"),
                "category": "control",
                "clinical_significance": control.get("clinical_significance"),
                "accession": control.get("accession"),
                "clinvar_variation_id": control.get("clinvar_variation_id"),
                "truth": {
                    "expected_panel_membership": True,
                    "expected_filter_behavior": "included_by_gene_panel",
                    "workbench_viewer_mode": "reference",
                },
            }
        )

        for index, variant in enumerate(stack_by_gene[gene], start=1):
            rows.append(
                {
                    "sample_id": f"HC-{gene}-CH-{index:02d}",
                    "sample_kind": "clinvar_challenge",
                    "source_fixture": "challenge_stack",
                    "gene": gene,
                    "transcript": variant["transcript"],
                    "cdna": variant["cdna"],
                    "protein": variant.get("protein"),
                    "category": variant["category"],
                    "clinical_significance": variant["clinical_significance"],
                    "accession": variant["accession"],
                    "clinvar_variation_id": variant["clinvar_variation_id"],
                    "truth": {
                        "expected_panel_membership": True,
                        "expected_filter_behavior": "included_by_gene_panel",
                        "variant_type": variant["variant_type"],
                    },
                }
            )
    return rows


def _fetch_clinvar_summaries(
    variation_ids: list[str],
    *,
    timeout_seconds: float,
) -> dict[str, dict[str, Any]]:
    params = urlencode(
        {
            "db": "clinvar",
            "retmode": "json",
            "id": ",".join(variation_ids),
        }
    )
    payload = _get_json(f"{NCBI_EUTILS}/esummary.fcgi?{params}", timeout_seconds=timeout_seconds)
    result = payload["result"]
    summaries: dict[str, dict[str, Any]] = {}
    for uid in result["uids"]:
        summaries[uid] = result[uid]
    return summaries


def _clinvar_coordinate(
    summary: dict[str, Any],
    *,
    timeout_seconds: float,
) -> EamosCoordinateResolution | None:
    variation = _primary_variation(summary)
    if variation is None:
        return None
    spdi = str(variation.get("canonical_spdi") or "").strip()
    if not spdi:
        return None
    vcf_fields = _spdi_vcf_fields(spdi, timeout_seconds=timeout_seconds)
    if vcf_fields is None:
        return None

    chrom = str(vcf_fields["chrom"]).removeprefix("chr")
    chrom = NC_CHROMOSOME_ACCESSIONS.get(chrom, chrom)
    pos = int(vcf_fields["pos"])
    ref = str(vcf_fields["ref"]).upper()
    alt = str(vcf_fields["alt"]).upper()
    variant_id = f"{chrom}-{pos}-{ref}-{alt}"
    transcript, cdna = _split_transcript_cdna(str(variation.get("variation_name") or ""))
    return EamosCoordinateResolution(
        gene=_gene_from_summary(summary),
        transcript=transcript or "",
        cdna=cdna or str(variation.get("cdna_change") or ""),
        chrom=chrom,
        pos=pos,
        ref=ref,
        alt=alt,
        genomic_hg38=variant_id,
        genomic_hgvs=genomic_variant_id_to_refseq_hgvs(variant_id),
        source="ncbi_clinvar_canonical_spdi",
        accession=str(summary.get("accession") or ""),
        clinvar_variation_id=str(summary.get("uid") or ""),
        canonical_spdi=spdi,
        provenance=("ncbi_clinvar_esummary", "ncbi_variation_spdi_vcf_fields"),
    )


def _variant_validator_coordinate(
    *,
    transcript: str,
    cdna: str,
    timeout_seconds: float,
) -> EamosCoordinateResolution | None:
    transcript_hgvs = f"{transcript}:{cdna}"
    url = (
        f"{VARIANT_VALIDATOR_API}/VariantValidator/variantvalidator/GRCh38/"
        f"{quote(transcript_hgvs, safe='')}/all"
    )
    try:
        payload = _get_json(url, timeout_seconds=timeout_seconds)
    except (URLError, TimeoutError, ValueError):
        return None
    summary = _variant_validator_summary(payload)
    variant_id = summary.get("variant_id")
    if not isinstance(variant_id, str) or not variant_id:
        return None
    chrom, pos, ref, alt = variant_id.split("-", 3)
    return EamosCoordinateResolution(
        gene=str(summary.get("gene") or ""),
        transcript=transcript,
        cdna=cdna,
        chrom=chrom,
        pos=int(pos),
        ref=ref,
        alt=alt,
        genomic_hg38=variant_id,
        genomic_hgvs=str(summary.get("hgvs_genomic_description") or "")
        or genomic_variant_id_to_refseq_hgvs(variant_id),
        source="variant_validator_grch38_vcf",
        provenance=("variant_validator_grch38",),
    )


def _primary_variation(summary: dict[str, Any]) -> dict[str, Any] | None:
    variation_set = summary.get("variation_set")
    if not isinstance(variation_set, list):
        return None
    for variation in variation_set:
        if isinstance(variation, dict) and variation.get("canonical_spdi"):
            return variation
    for variation in variation_set:
        if isinstance(variation, dict):
            return variation
    return None


def _spdi_vcf_fields(spdi: str, *, timeout_seconds: float) -> dict[str, Any] | None:
    url = f"{NCBI_VARIATION_API}/spdi/{quote(spdi, safe='')}/vcf_fields"
    try:
        payload = _get_json(url, timeout_seconds=timeout_seconds)
    except (URLError, TimeoutError, ValueError):
        return None
    data = payload.get("data")
    return data if isinstance(data, dict) else None


def _validation(
    *,
    local: EamosCoordinateResolution | None,
    clinvar: EamosCoordinateResolution | None,
) -> dict[str, Any]:
    return {
        "local_variant_id": local.genomic_hg38 if local else None,
        "clinvar_variant_id": clinvar.genomic_hg38 if clinvar else None,
        "clinvar_match": _coordinate_match(local, clinvar),
    }


def _coordinate_match(
    left: EamosCoordinateResolution | None,
    right: EamosCoordinateResolution | None,
) -> bool | None:
    if left is None or right is None:
        return None
    return left.genomic_hg38 == right.genomic_hg38


def _get_json(url: str, *, timeout_seconds: float) -> dict[str, Any]:
    with urlopen(url, timeout=timeout_seconds) as response:
        return json.load(response)


def _split_transcript_cdna(value: str) -> tuple[str | None, str | None]:
    if ":" not in value:
        return None, None
    transcript_part, rest = value.split(":", 1)
    transcript = transcript_part.split("(", 1)[0].strip()
    cdna = rest.split(" ", 1)[0].strip()
    return transcript or None, cdna or None


def _gene_from_summary(summary: dict[str, Any]) -> str:
    title = str(summary.get("title") or "")
    if "(" in title and ")" in title:
        inside = title.split("(", 1)[1].split(")", 1)[0]
        if inside.isidentifier():
            return inside.upper()
    return ""


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_path(path: Path) -> str:
    return str(path.relative_to(BACKEND_ROOT.parent).as_posix())


if __name__ == "__main__":
    raise SystemExit(main())
