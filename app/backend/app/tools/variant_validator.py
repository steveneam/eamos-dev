from __future__ import annotations

from typing import Any

import httpx

from app.tools.base import FixtureBackedTool, ToolResult


def _extract_hgvs(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


def _vcf_to_variant_id(vcf: dict[str, Any] | None) -> str | None:
    if not vcf:
        return None
    chrom = str(vcf.get("chr") or "").removeprefix("chr")
    pos = str(vcf.get("pos") or "")
    ref = str(vcf.get("ref") or "")
    alt = str(vcf.get("alt") or "")
    if not all((chrom, pos, ref, alt)):
        return None
    return f"{chrom}-{pos}-{ref}-{alt}"


def _summary_from_response(payload: dict[str, Any]) -> dict[str, Any]:
    variant_payload = next(
        (
            value
            for key, value in payload.items()
            if key not in {"flag", "metadata"} and isinstance(value, dict)
        ),
        {},
    )
    loci = variant_payload.get("primary_assembly_loci", {})
    grch38 = loci.get("grch38", {})
    vcf = grch38.get("vcf") or {}
    return {
        "gene": variant_payload.get("gene_symbol"),
        "submitted_variant": variant_payload.get("submitted_variant"),
        "hgvs_transcript_variant": variant_payload.get("hgvs_transcript_variant"),
        "hgvs_genomic_description": grch38.get("hgvs_genomic_description"),
        "vcf": {
            "chr": str(vcf.get("chr") or "").removeprefix("chr"),
            "pos": str(vcf.get("pos") or ""),
            "ref": str(vcf.get("ref") or ""),
            "alt": str(vcf.get("alt") or ""),
        },
        "variant_id": _vcf_to_variant_id(vcf),
        "exon": _exon_from_response(variant_payload),
        "selected_assembly": variant_payload.get("selected_assembly"),
    }


def _summary_from_vep_raw(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    chrom = str(raw.get("seq_region_name") or "").removeprefix("chr")
    pos = raw.get("start")
    allele_string = raw.get("allele_string") or ""
    alleles = [part for part in str(allele_string).split("/") if part and part != "-"]
    if not chrom or not pos or len(alleles) < 2:
        return None
    vcf = {"chr": chrom, "pos": str(pos), "ref": alleles[0], "alt": alleles[1]}
    variant_id = _vcf_to_variant_id(vcf)
    if variant_id is None:
        return None
    return {
        "gene": raw.get("gene_symbol"),
        "submitted_variant": raw.get("input"),
        "hgvs_transcript_variant": raw.get("input"),
        "hgvs_genomic_description": None,
        "vcf": vcf,
        "variant_id": variant_id,
        "selected_assembly": "GRCh38",
    }


def _source_query(variant) -> str:
    source_inputs = getattr(
        getattr(variant, "search_input_resolution", None), "source_inputs", None
    )
    source_query = (
        getattr(source_inputs, "variant_validator", None) if source_inputs is not None else None
    )
    transcript_hgvs = getattr(variant, "transcript_hgvs", "") or ""
    hgvs = _extract_hgvs(transcript_hgvs)
    return source_query or (
        transcript_hgvs
        if ":" in transcript_hgvs
        else f"{variant.gene}:{hgvs}" if hgvs else variant.gene
    )


def _exon_from_response(variant_payload: dict[str, Any]) -> str | None:
    positions = variant_payload.get("variant_exonic_positions")
    if not isinstance(positions, dict):
        return None
    for accession in ("NC_000001.11", "GRCh38", "grch38", "hg38", "NG_008472.2"):
        exon = _format_exon(positions.get(accession))
        if exon:
            return exon
    for value in positions.values():
        exon = _format_exon(value)
        if exon:
            return exon
    return None


def _format_exon(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    start = str(value.get("start_exon") or "").strip()
    end = str(value.get("end_exon") or "").strip()
    if not start and not end:
        return None
    if start and end and start != end:
        return f"{start}-{end}"
    return start or end


def _variant_type_from_variant_id(variant_id: str | None) -> str:
    if not variant_id:
        return ""
    parts = variant_id.split("-")
    if len(parts) != 4:
        return ""
    ref = parts[2]
    alt = parts[3]
    if len(ref) == 1 and len(alt) == 1:
        return "single nucleotide variant"
    if len(ref) < len(alt):
        return "insertion"
    if len(ref) > len(alt):
        return "deletion"
    return "indel"


def _mutate_variant(variant, summary: dict[str, Any]) -> None:
    variant_id = summary.get("variant_id")
    if variant_id:
        variant.genomic_hg38 = variant_id
    genomic_hgvs = summary.get("hgvs_genomic_description")
    if genomic_hgvs:
        variant.genomic_hgvs = genomic_hgvs

    explicit_variation_type = summary.get("variation_type") or summary.get("variant_type")
    explicit_consequence = summary.get("consequence") or summary.get("most_severe_consequence")

    if not getattr(variant, "variation_type", "") and (variant_id or explicit_variation_type):
        variant.variation_type = explicit_variation_type or _variant_type_from_variant_id(
            variant_id
        )
    if not getattr(variant, "consequence", "") and explicit_consequence:
        variant.consequence = explicit_consequence


def _fixture_matches_variant(variant, summary: dict[str, Any]) -> bool:
    hgvs = _extract_hgvs(getattr(variant, "transcript_hgvs", None))
    submitted = str(
        summary.get("submitted_variant") or summary.get("hgvs_transcript_variant") or ""
    )
    return summary.get("gene") == getattr(variant, "gene", None) and bool(
        hgvs and submitted.endswith(hgvs)
    )


class VariantValidatorTool(FixtureBackedTool):
    source = "variant_validator"
    fixture_name = "variant_validator_fixtures.json"

    def get_evidence(self, variant=None) -> ToolResult:
        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            summary = fixture.get("summary", {})
            if variant is None or _fixture_matches_variant(variant, summary):
                if variant is not None:
                    _mutate_variant(variant, summary)
                return ToolResult(source=self.source, status="fixture", **fixture)
            return ToolResult(
                source=self.source,
                status="missing",
                request_identity={"query": _source_query(variant)},
                summary={},
                warnings=["variant_validator_fixture_variant_mismatch"],
                raw=None,
                source_url=None,
            )
        seeded_resolution = getattr(variant, "search_input_resolution", None)
        seeded_summary = getattr(seeded_resolution, "variant_validator_summary", None)
        if isinstance(seeded_summary, dict) and seeded_summary.get("variant_id"):
            _mutate_variant(variant, seeded_summary)
            return ToolResult(
                source=self.source,
                status="live",
                request_identity={
                    "query": getattr(seeded_resolution, "resolver_transcript_hgvs", "")
                },
                summary=seeded_summary,
                raw=getattr(seeded_resolution, "variant_validator_raw", None),
                source_url=getattr(seeded_resolution, "variant_validator_url", None),
            )
        source_inputs = getattr(seeded_resolution, "source_inputs", None)
        if source_inputs is not None and not getattr(source_inputs, "variant_validator", None):
            return ToolResult(
                source=self.source,
                status="live_stub",
                request_identity={"submitted": getattr(variant, "transcript_hgvs", None)},
                summary={},
                warnings=[
                    "VariantValidator live query requires transcript HGVS or RefSeq genomic HGVS; "
                    "no source-specific VariantValidator identifier was resolved."
                ],
                source_url=None,
            )
        try:
            return self._fetch_live(variant)
        except Exception as exc:
            fixture = self.load_fixture()
            if _fixture_matches_variant(variant, fixture.get("summary", {})):
                _mutate_variant(variant, fixture.get("summary", {}))
                return ToolResult(
                    source=self.source,
                    status="fallback",
                    warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                    **fixture,
                )
            return ToolResult(
                source=self.source,
                status="fallback",
                request_identity={"query": _source_query(variant)},
                summary={},
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                raw=None,
                source_url=None,
            )

    def _fetch_live(self, variant) -> ToolResult:
        query = _source_query(variant)
        url = f"{self.settings.variant_validator_base_url}/VariantValidator/variantvalidator/GRCh38/{query}/all"
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
        payload = response.json()
        summary = _summary_from_response(payload)
        _mutate_variant(variant, summary)
        return ToolResult(
            source=self.source,
            status="live",
            request_identity={"query": query},
            summary=summary,
            raw=payload,
            source_url=url,
        )
