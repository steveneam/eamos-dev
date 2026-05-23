from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import quote

import httpx

from app.services.sequence_context import (
    CANONICAL_TRANSCRIPTS,
    QueryKind,
    genomic_variant_id_to_refseq_hgvs,
    normalize_variant_query,
    parse_genomic_variant_id,
)


@dataclass(frozen=True)
class SourceSpecificInputs:
    variant_validator: str | None = None
    ensembl_vep: str | None = None
    gnomad: str | None = None
    spliceai: str | None = None
    clinvar: str | None = None
    literature_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParsedSearchInput:
    submitted_text: str
    gene: str
    cdna: str
    transcript: str | None = None
    protein_change: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SearchInputResolution:
    gene: str
    hgvs: str
    transcript: str | None
    protein_change: str | None
    kind: QueryKind
    transcript_hgvs: str
    resolver_transcript: str | None
    resolver_transcript_hgvs: str
    genomic_hg38: str | None = None
    genomic_hgvs: str | None = None
    source_inputs: SourceSpecificInputs = field(default_factory=SourceSpecificInputs)
    warnings: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    variant_validator_summary: dict[str, Any] | None = None
    variant_validator_raw: dict[str, Any] | None = None
    variant_validator_url: str | None = None


class EamosSearchInputResolver:
    """Resolve user variant input into source-specific identifiers."""

    def __init__(
        self,
        settings=None,
        *,
        timeout_seconds: float = 15.0,
        resolve_coordinates: bool = False,
    ) -> None:
        self.settings = settings
        self.timeout_seconds = timeout_seconds
        self.resolve_coordinates = resolve_coordinates

    def resolve_text(
        self,
        text: str,
        *,
        gene: str | None = None,
        transcript: str | None = None,
        protein_change: str | None = None,
    ) -> SearchInputResolution:
        parsed = parse_search_text(
            text,
            gene=gene,
            transcript=transcript,
            protein_change=protein_change,
        )
        resolution = self.resolve(
            gene=parsed.gene,
            cdna=parsed.cdna,
            transcript=parsed.transcript,
            protein_change=parsed.protein_change,
        )
        if not parsed.warnings:
            return resolution
        return replace(resolution, warnings=(*parsed.warnings, *resolution.warnings))

    def resolve(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str | None = None,
        protein_change: str | None = None,
    ) -> SearchInputResolution:
        normalized_gene, hgvs, normalized_transcript, kind = normalize_variant_query(
            gene,
            cdna,
            transcript,
        )
        warnings: list[str] = []
        provenance: list[str] = []

        transcript_hgvs = f"{normalized_transcript}:{hgvs}" if normalized_transcript else hgvs
        resolver_transcript = normalized_transcript
        if resolver_transcript is None and kind == "cdna":
            resolver_transcript = CANONICAL_TRANSCRIPTS.get(normalized_gene)
            if resolver_transcript is not None:
                provenance.append("local_canonical_transcript_map")
            else:
                resolver_transcript, resolver_warnings = self._resolve_mane_transcript(
                    normalized_gene
                )
                warnings.extend(resolver_warnings)
                if resolver_transcript is not None:
                    provenance.append("ensembl_mane_transcript_lookup")

        resolver_transcript_hgvs = (
            f"{resolver_transcript}:{hgvs}" if resolver_transcript else transcript_hgvs
        )
        genomic_hg38 = parse_genomic_variant_id(hgvs) if kind == "genomic" else None
        genomic_hgvs = hgvs if kind == "genomic" and hgvs.upper().startswith("NC_") else None
        variant_validator_summary = None
        variant_validator_raw = None
        variant_validator_url = None

        if genomic_hg38 is not None:
            if genomic_hgvs is None:
                genomic_hgvs = genomic_variant_id_to_refseq_hgvs(genomic_hg38)
            provenance.append("submitted_genomic_variant_id")
        elif self.resolve_coordinates and kind == "cdna" and resolver_transcript is not None:
            (
                genomic_hg38,
                genomic_hgvs,
                variant_validator_summary,
                variant_validator_raw,
                variant_validator_url,
                coordinate_warnings,
            ) = self._resolve_variant_validator_coordinates(resolver_transcript_hgvs)
            warnings.extend(coordinate_warnings)
            if genomic_hg38 is not None:
                provenance.append("variant_validator_grch38_vcf")

        source_inputs = SourceSpecificInputs(
            variant_validator=(
                resolver_transcript_hgvs
                if kind == "cdna" and resolver_transcript is not None
                else genomic_hgvs
            ),
            ensembl_vep=(
                resolver_transcript_hgvs
                if kind == "cdna" and resolver_transcript is not None
                else genomic_hgvs
            ),
            gnomad=genomic_hg38,
            spliceai=genomic_hg38,
            clinvar=self._clinvar_input(
                normalized_gene,
                hgvs,
                kind,
                genomic_hgvs,
                resolver_transcript_hgvs if resolver_transcript is not None else None,
            ),
            literature_terms=self._literature_terms(
                normalized_gene,
                hgvs,
                resolver_transcript_hgvs,
                genomic_hg38,
                protein_change,
            ),
        )

        return SearchInputResolution(
            gene=normalized_gene,
            hgvs=hgvs,
            transcript=normalized_transcript,
            protein_change=protein_change,
            kind=kind,
            transcript_hgvs=transcript_hgvs,
            resolver_transcript=resolver_transcript,
            resolver_transcript_hgvs=resolver_transcript_hgvs,
            genomic_hg38=genomic_hg38,
            genomic_hgvs=genomic_hgvs,
            source_inputs=source_inputs,
            warnings=tuple(warnings),
            provenance=tuple(provenance),
            variant_validator_summary=variant_validator_summary,
            variant_validator_raw=variant_validator_raw,
            variant_validator_url=variant_validator_url,
        )

    def _resolve_mane_transcript(self, gene: str) -> tuple[str | None, list[str]]:
        if self.settings is None or not getattr(self.settings, "use_real_apis", False):
            return None, []

        url = (
            f"{self.settings.vep_base_url}/lookup/symbol/homo_sapiens/"
            f"{quote(gene, safe='')}?expand=1;mane=1;utr=1"
        )
        try:
            response = httpx.get(
                url,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return None, [f"transcript_resolution_failed:{type(exc).__name__}"]

        transcripts = [
            transcript
            for transcript in _as_list(
                payload.get("Transcript") if isinstance(payload, dict) else None
            )
            if isinstance(transcript, dict)
        ]
        for transcript in transcripts:
            if transcript.get("biotype") != "protein_coding":
                continue
            for mane in _as_list(transcript.get("MANE")):
                if not isinstance(mane, dict) or mane.get("type") != "MANE_Select":
                    continue
                refseq_match = str(mane.get("refseq_match") or "").strip()
                if refseq_match:
                    return refseq_match, []

        canonical = (
            str(payload.get("canonical_transcript") or "") if isinstance(payload, dict) else ""
        )
        for transcript in transcripts:
            if transcript.get("biotype") != "protein_coding":
                continue
            if canonical and str(transcript.get("id") or "") == canonical:
                resolved = _versioned_ensembl_id(transcript)
                if resolved:
                    return resolved, []

        for transcript in transcripts:
            if transcript.get("biotype") != "protein_coding" or transcript.get("is_canonical") != 1:
                continue
            resolved = _versioned_ensembl_id(transcript)
            if resolved:
                return resolved, []

        return None, [f"transcript_resolution_unavailable:{gene}"]

    def _resolve_variant_validator_coordinates(
        self,
        transcript_hgvs: str,
    ) -> tuple[
        str | None, str | None, dict[str, Any] | None, dict[str, Any] | None, str | None, list[str]
    ]:
        if self.settings is None or not getattr(self.settings, "use_real_apis", False):
            return None, None, None, None, None, []

        url = (
            f"{self.settings.variant_validator_base_url}"
            f"/VariantValidator/variantvalidator/GRCh38/{quote(transcript_hgvs, safe='')}/all"
        )
        try:
            response = httpx.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return (
                None,
                None,
                None,
                None,
                url,
                [f"coordinate_resolution_failed:{type(exc).__name__}"],
            )

        summary = _variant_validator_summary(payload)
        return (
            summary.get("variant_id"),
            summary.get("hgvs_genomic_description"),
            summary,
            payload,
            url,
            [],
        )

    def _clinvar_input(
        self,
        gene: str,
        hgvs: str,
        kind: QueryKind,
        genomic_hgvs: str | None,
        resolver_transcript_hgvs: str | None,
    ) -> str | None:
        if genomic_hgvs:
            return genomic_hgvs
        if kind == "cdna":
            return resolver_transcript_hgvs or f"{gene}:{hgvs}"
        if kind == "rsid":
            return hgvs
        if kind == "genomic":
            return genomic_hgvs or parse_genomic_variant_id(hgvs) or hgvs
        return None

    def _literature_terms(
        self,
        gene: str,
        hgvs: str,
        transcript_hgvs: str,
        genomic_hg38: str | None,
        protein_change: str | None,
    ) -> tuple[str, ...]:
        terms = [gene, hgvs, transcript_hgvs, genomic_hg38, protein_change]
        unique: list[str] = []
        for term in terms:
            if term and term not in unique:
                unique.append(term)
        return tuple(unique)


_TRANSCRIPT_SEARCH_RE = re.compile(
    r"^(?P<transcript>(?:N[MR]_|ENST)[A-Z0-9_.]+)"
    r"(?:\((?P<gene>[A-Z][A-Z0-9-]*)\))?:"
    r"(?P<hgvs>.+)$",
    flags=re.IGNORECASE,
)
_GENE_PREFIX_SEARCH_RE = re.compile(
    r"^(?P<gene>[A-Z][A-Z0-9-]*)\s*:\s*" r"(?P<hgvs>(?:[CGMNP]\..+|rs\d+))$",
    flags=re.IGNORECASE,
)
_GENE_SPACE_SEARCH_RE = re.compile(
    r"^(?P<gene>[A-Z][A-Z0-9-]*)\s+" r"(?P<hgvs>(?:[CGMNP]\..+|rs\d+))$",
    flags=re.IGNORECASE,
)
_TRAILING_PROTEIN_RE = re.compile(r"\s*\((?P<protein>p\.[^)]+)\)\s*$", flags=re.IGNORECASE)


def parse_search_text(
    text: str,
    *,
    gene: str | None = None,
    transcript: str | None = None,
    protein_change: str | None = None,
) -> ParsedSearchInput:
    """Parse a search-box style string into resolver inputs."""
    submitted_text = text
    working = text.strip()
    warnings: list[str] = []

    protein_match = _TRAILING_PROTEIN_RE.search(working)
    if protein_match is not None:
        protein_change = protein_change or protein_match.group("protein")
        working = working[: protein_match.start()].strip()

    parsed_gene = (gene or "").strip()
    parsed_transcript = transcript.strip() if transcript else None
    parsed_cdna = working

    transcript_match = _TRANSCRIPT_SEARCH_RE.fullmatch(working)
    if transcript_match is not None:
        parsed_transcript = parsed_transcript or transcript_match.group("transcript")
        parsed_gene = parsed_gene or transcript_match.group("gene") or ""
        parsed_cdna = transcript_match.group("hgvs")
    else:
        gene_prefix_match = _GENE_PREFIX_SEARCH_RE.fullmatch(working)
        if gene_prefix_match is not None:
            parsed_gene = parsed_gene or gene_prefix_match.group("gene")
            parsed_cdna = gene_prefix_match.group("hgvs")
        else:
            gene_space_match = _GENE_SPACE_SEARCH_RE.fullmatch(working)
            if gene_space_match is not None:
                parsed_gene = parsed_gene or gene_space_match.group("gene")
                parsed_cdna = gene_space_match.group("hgvs")

    normalized_gene, _, _, kind = normalize_variant_query(
        parsed_gene,
        parsed_cdna,
        parsed_transcript,
    )
    if not normalized_gene and kind in {"cdna", "protein"}:
        warnings.append("gene_missing_for_gene_specific_variant_input")

    return ParsedSearchInput(
        submitted_text=submitted_text,
        gene=parsed_gene,
        cdna=parsed_cdna,
        transcript=parsed_transcript,
        protein_change=protein_change,
        warnings=tuple(warnings),
    )


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _versioned_ensembl_id(transcript: dict[str, Any]) -> str:
    transcript_id = str(transcript.get("id") or "")
    version = transcript.get("version")
    if transcript_id and version:
        return f"{transcript_id}.{version}"
    return transcript_id


def _vcf_to_variant_id(vcf: dict[str, Any] | None) -> str | None:
    if not vcf:
        return None
    chrom = str(vcf.get("chr") or "").removeprefix("chr")
    pos = str(vcf.get("pos") or "")
    ref = str(vcf.get("ref") or "").upper()
    alt = str(vcf.get("alt") or "").upper()
    if not all((chrom, pos, ref, alt)):
        return None
    return f"{chrom}-{pos}-{ref}-{alt}"


def _variant_validator_summary(payload: dict[str, Any]) -> dict[str, Any]:
    variant_payload = next(
        (
            value
            for key, value in payload.items()
            if key not in {"flag", "metadata"} and isinstance(value, dict)
        ),
        {},
    )
    loci = variant_payload.get("primary_assembly_loci", {})
    grch38 = loci.get("grch38", {}) if isinstance(loci, dict) else {}
    vcf = grch38.get("vcf") or {} if isinstance(grch38, dict) else {}
    return {
        "gene": variant_payload.get("gene_symbol"),
        "submitted_variant": variant_payload.get("submitted_variant"),
        "hgvs_transcript_variant": variant_payload.get("hgvs_transcript_variant"),
        "hgvs_genomic_description": grch38.get("hgvs_genomic_description"),
        "vcf": {
            "chr": str(vcf.get("chr") or "").removeprefix("chr"),
            "pos": str(vcf.get("pos") or ""),
            "ref": str(vcf.get("ref") or "").upper(),
            "alt": str(vcf.get("alt") or "").upper(),
        },
        "variant_id": _vcf_to_variant_id(vcf),
        "exon": _exon_from_variant_validator_payload(variant_payload),
        "selected_assembly": variant_payload.get("selected_assembly"),
    }


def _exon_from_variant_validator_payload(variant_payload: dict[str, Any]) -> str | None:
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
