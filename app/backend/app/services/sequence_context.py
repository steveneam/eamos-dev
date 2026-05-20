from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from app.core.config import Settings

CANONICAL_TRANSCRIPTS: dict[str, str] = {
    "RPE65": "NM_000329.3",
}

WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE = "workbench_sequence_context_unavailable"
WORKBENCH_UNSUPPORTED_INPUT_PREFIX = "workbench_unsupported_input"

QueryKind = Literal["cdna", "rsid", "protein", "genomic", "unknown"]
SequenceContextSource = Literal["fixture", "resolver"]
Strand = Literal["+", "-", "unknown"]


def normalize_variant_query(
    gene: str,
    cdna: str,
    transcript: str | None,
) -> tuple[str, str, str | None, QueryKind]:
    normalized_gene = gene.strip().upper()
    hgvs = re.sub(r"\s+", "", cdna.strip())
    normalized_transcript = transcript.strip() if transcript else None

    if ":" in hgvs:
        prefix, remainder = hgvs.split(":", 1)
        prefix_upper = prefix.upper()
        if prefix_upper == normalized_gene:
            hgvs = remainder
        elif prefix_upper.startswith(("NM_", "ENST")):
            normalized_transcript = re.sub(r"\([^)]*\)$", "", prefix)
            hgvs = remainder

    hgvs = re.sub(r"\(p\.[^)]+\)$", "", hgvs)

    if re.match(r"^c\.", hgvs):
        kind: QueryKind = "cdna"
    elif re.match(r"^rs\d+$", hgvs, flags=re.IGNORECASE):
        kind = "rsid"
    elif re.match(r"^p\.", hgvs):
        kind = "protein"
    elif re.match(r"^(chr)?[\dXYM]+[:\-]", hgvs, flags=re.IGNORECASE) or re.match(
        r"^NC_\d+\.\d+:", hgvs
    ):
        kind = "genomic"
    else:
        kind = "unknown"

    return normalized_gene, hgvs, normalized_transcript, kind


def unsupported_input_warning(kind: str) -> str:
    return f"{WORKBENCH_UNSUPPORTED_INPUT_PREFIX}:{kind}"


class NormalizedVariantQuery(BaseModel):
    gene: str
    hgvs: str
    transcript: str | None = None
    kind: QueryKind
    transcript_hgvs: str
    resolver_transcript: str | None = None
    resolver_transcript_hgvs: str


def normalize_sequence_query(
    gene: str,
    cdna: str,
    transcript: str | None = None,
) -> NormalizedVariantQuery:
    normalized_gene, hgvs, normalized_transcript, kind = normalize_variant_query(
        gene,
        cdna,
        transcript,
    )
    transcript_hgvs = f"{normalized_transcript}:{hgvs}" if normalized_transcript else hgvs
    resolver_transcript = normalized_transcript
    if resolver_transcript is None and kind == "cdna":
        resolver_transcript = CANONICAL_TRANSCRIPTS.get(normalized_gene)
    resolver_transcript_hgvs = (
        f"{resolver_transcript}:{hgvs}" if resolver_transcript else transcript_hgvs
    )
    return NormalizedVariantQuery(
        gene=normalized_gene,
        hgvs=hgvs,
        transcript=normalized_transcript,
        kind=kind,
        transcript_hgvs=transcript_hgvs,
        resolver_transcript=resolver_transcript,
        resolver_transcript_hgvs=resolver_transcript_hgvs,
    )


class SequenceContext(BaseModel):
    gene: str
    cdna: str
    transcript: str | None = None
    transcript_hgvs: str
    query_kind: QueryKind
    species: str = "human"
    genome_build: str = "GRCh38"
    genomic_hg38: str | None = None
    strand: Strand = "unknown"
    window_sequence: str
    target_offset: int
    reference_base: str | None = None
    alternate_base: str | None = None
    codon_number: int | None = None
    codon_ref: str | None = None
    codon_alt: str | None = None
    source: SequenceContextSource
    source_metadata: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class SequenceContextResult(BaseModel):
    query: NormalizedVariantQuery
    context: SequenceContext | None = None
    warnings: list[str] = Field(default_factory=list)


class SequenceContextResolver(Protocol):
    def resolve(self, query: NormalizedVariantQuery, species: str) -> SequenceContext | None:
        """Return a source-backed sequence context for a normalized query."""


class EnsemblVariantSequenceResolver:
    """Resolve a cDNA variant to a GRCh38 sequence window for local design engines."""

    def __init__(
        self,
        settings: Settings,
        *,
        flank_bp: int = 1000,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.settings = settings
        self.flank_bp = flank_bp
        self.timeout_seconds = timeout_seconds

    def resolve(self, query: NormalizedVariantQuery, species: str) -> SequenceContext | None:
        if species != "human" or query.kind != "cdna" or not query.resolver_transcript_hgvs:
            return None

        summary = self._variant_validator_summary(query)
        vcf = summary.get("vcf") if isinstance(summary, dict) else None
        if not isinstance(vcf, dict):
            return None

        chrom = str(vcf.get("chr") or "").removeprefix("chr")
        pos_text = str(vcf.get("pos") or "")
        ref = str(vcf.get("ref") or "").upper()
        alt = str(vcf.get("alt") or "").upper()
        if not chrom or not pos_text.isdigit() or not ref or not alt:
            return None

        pos = int(pos_text)
        start = max(1, pos - self.flank_bp)
        end = pos + self.flank_bp
        sequence, sequence_url = self._ensembl_sequence(chrom=chrom, start=start, end=end)
        target_offset = pos - start

        return SequenceContext(
            gene=query.gene,
            cdna=query.hgvs,
            transcript=query.resolver_transcript,
            transcript_hgvs=query.resolver_transcript_hgvs,
            query_kind=query.kind,
            species=species,
            genome_build="GRCh38",
            genomic_hg38=f"{chrom}-{pos}-{ref}-{alt}",
            strand="unknown",
            window_sequence=sequence,
            target_offset=target_offset,
            reference_base=ref,
            alternate_base=alt,
            source="resolver",
            source_metadata={
                "coordinate_source": "variant_validator",
                "sequence_source": "ensembl_rest",
                "variant_validator_url": self._variant_validator_url(query),
                "ensembl_sequence_url": sequence_url,
            },
        )

    def _variant_validator_url(self, query: NormalizedVariantQuery) -> str:
        encoded_query = quote(query.resolver_transcript_hgvs, safe="")
        return (
            f"{self.settings.variant_validator_base_url}"
            f"/VariantValidator/variantvalidator/GRCh38/{encoded_query}/all"
        )

    def _variant_validator_summary(self, query: NormalizedVariantQuery) -> dict[str, object]:
        response = httpx.get(self._variant_validator_url(query), timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
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
            "vcf": {
                "chr": str(vcf.get("chr") or "").removeprefix("chr"),
                "pos": str(vcf.get("pos") or ""),
                "ref": str(vcf.get("ref") or ""),
                "alt": str(vcf.get("alt") or ""),
            },
        }

    def _ensembl_sequence(self, *, chrom: str, start: int, end: int) -> tuple[str, str]:
        region = f"{chrom}:{start}..{end}:1"
        url = f"{self.settings.vep_base_url}/sequence/region/human/{region}"
        response = httpx.get(
            url,
            headers={"Content-Type": "text/plain", "Accept": "text/plain"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        sequence = re.sub(r"[^ACGTNacgtn]", "", response.text).upper()
        if not sequence:
            return "", url
        return sequence, url


@lru_cache(maxsize=1)
def _sequence_context_fixtures() -> dict:
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "workbench" / "sequence_contexts.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


class SequenceContextFixtureProvider:
    def resolve(self, query: NormalizedVariantQuery, species: str) -> SequenceContext | None:
        fixture = (
            _sequence_context_fixtures()
            .get(species.lower(), {})
            .get(query.gene, {})
            .get(query.hgvs)
        )
        if not fixture:
            return None
        return SequenceContext(
            **fixture,
            gene=query.gene,
            cdna=query.hgvs,
            transcript=query.resolver_transcript,
            transcript_hgvs=query.resolver_transcript_hgvs,
            query_kind=query.kind,
            species=species.lower(),
            source="fixture",
        )


class SequenceContextService:
    def __init__(
        self,
        settings: Settings | None = None,
        fixture_provider: SequenceContextFixtureProvider | None = None,
        resolver: SequenceContextResolver | None = None,
    ) -> None:
        self.settings = settings
        self.fixture_provider = fixture_provider or SequenceContextFixtureProvider()
        self.resolver = resolver

    def resolve(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str | None = None,
        species: str = "human",
    ) -> SequenceContextResult:
        normalized_species = species.strip().lower() or "human"
        query = normalize_sequence_query(gene, cdna, transcript)

        if normalized_species != "human":
            return SequenceContextResult(
                query=query,
                warnings=[unsupported_input_warning("species")],
            )

        if query.kind != "cdna":
            return SequenceContextResult(
                query=query,
                warnings=[unsupported_input_warning(query.kind)],
            )

        if self.settings is None or not self.settings.use_real_apis:
            context = self.fixture_provider.resolve(query, normalized_species)
            if context is not None:
                return SequenceContextResult(query=query, context=context)
            return SequenceContextResult(
                query=query,
                warnings=[WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE],
            )

        if self.resolver is None:
            return SequenceContextResult(
                query=query,
                warnings=[WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE],
            )

        context = self.resolver.resolve(query, normalized_species)
        if context is None:
            return SequenceContextResult(
                query=query,
                warnings=[WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE],
            )
        return SequenceContextResult(query=query, context=context)
