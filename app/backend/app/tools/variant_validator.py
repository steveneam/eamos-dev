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


def _mutate_variant(variant, summary: dict[str, Any]) -> None:
    variant_id = summary.get("variant_id")
    if variant_id:
        variant.genomic_hg38 = variant_id

    explicit_variation_type = summary.get("variation_type") or summary.get("variant_type")
    explicit_consequence = summary.get("consequence") or summary.get("most_severe_consequence")

    if not getattr(variant, "variation_type", "") and (variant_id or explicit_variation_type):
        variant.variation_type = explicit_variation_type or "single nucleotide variant"
    if not getattr(variant, "consequence", "") and (variant_id or explicit_consequence):
        variant.consequence = explicit_consequence or "missense variant"


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
            if variant is not None and _fixture_matches_variant(
                variant, fixture.get("summary", {})
            ):
                _mutate_variant(variant, fixture.get("summary", {}))
            return ToolResult(source=self.source, status="fixture", **fixture)
        try:
            return self._fetch_live(variant)
        except Exception as exc:
            vep_summary = _summary_from_vep_raw(getattr(variant, "vep_raw", None))
            if vep_summary is not None:
                _mutate_variant(variant, vep_summary)
                return ToolResult(
                    source=self.source,
                    status="fallback",
                    request_identity={"hgvs": variant.transcript_hgvs},
                    summary=vep_summary,
                    warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                    raw=getattr(variant, "vep_raw", None),
                    source_url=None,
                )
            fixture = self.load_fixture()
            if _fixture_matches_variant(variant, fixture.get("summary", {})):
                _mutate_variant(variant, fixture.get("summary", {}))
            return ToolResult(
                source=self.source,
                status="fallback",
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                **fixture,
            )

    def _fetch_live(self, variant) -> ToolResult:
        hgvs = _extract_hgvs(variant.transcript_hgvs)
        query = (
            variant.transcript_hgvs
            if ":" in variant.transcript_hgvs
            else f"{variant.gene}:{hgvs}" if hgvs else variant.gene
        )
        url = f"{self.settings.variant_validator_base_url}/VariantValidator/variantvalidator/GRCh38/{query}/all"
        response = httpx.get(url, timeout=15.0)
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
