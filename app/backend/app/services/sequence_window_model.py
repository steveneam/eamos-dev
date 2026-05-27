from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.services.reference_genome import (
    ReferenceBaseCheck,
    ReferenceGenomeMetadata,
    ReferenceGenomeStore,
    ReferenceGenomeStoreError,
    ReferenceWindow,
)

Strand = Literal["+", "-", "unknown"]
VariantChangeType = Literal["substitution", "insertion", "deletion", "delins", "identity"]

DEFAULT_FLANK_BP = 25
REFERENCE_ALLELE_MISMATCH = "reference_allele_mismatch"
REFERENCE_WINDOW_UNAVAILABLE = "reference_window_unavailable"
UNSUPPORTED_VARIANT_ALLELE = "unsupported_variant_allele"


class ReferenceWindowReader(Protocol):
    def metadata(self) -> ReferenceGenomeMetadata:
        """Return source/provenance metadata for the backing reference."""

    def get_sequence(
        self,
        chrom: str,
        start: int,
        end: int,
        build: str | None = None,
    ) -> ReferenceWindow:
        """Return a 1-based inclusive reference window."""

    def validate_reference_base(
        self,
        chrom: str,
        position: int,
        expected: str,
        build: str | None = None,
    ) -> ReferenceBaseCheck:
        """Validate the first reference base at a 1-based genomic position."""


@dataclass(frozen=True)
class SequenceWindowProvenance:
    source_id: str
    source_url: str | None
    source_version: str
    reader: str
    checksum_algorithm: str
    checksum: str
    relative_path: str


@dataclass(frozen=True)
class LocalReferenceWindow:
    chrom: str
    start: int
    end: int
    strand: Strand
    sequence: str
    genome_build: str
    zero_based_start: int
    zero_based_end_exclusive: int

    @property
    def length(self) -> int:
        return len(self.sequence)


@dataclass(frozen=True)
class LocalReferenceBaseCheck:
    position: int
    expected_base: str
    observed_base: str | None
    matches: bool
    reason: str
    expected_allele: str
    observed_allele: str | None


@dataclass(frozen=True)
class LocalVariantWindow:
    reference_allele: str
    alternate_allele: str
    applied_sequence: str
    change_type: VariantChangeType
    reference_start_offset: int
    reference_end_offset_exclusive: int
    variant_start_offset: int
    variant_end_offset_exclusive: int
    flank_convention: str


@dataclass(frozen=True)
class LocalSequenceWindowContext:
    gene: str | None
    transcript: str | None
    cdna_hgvs: str | None
    genomic_hg38: str
    genome_build: str
    reference_window: LocalReferenceWindow | None
    reference_base_check: LocalReferenceBaseCheck | None
    variant_window: LocalVariantWindow | None
    provenance: SequenceWindowProvenance | None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    unavailable_reason: str | None = None


class LocalSequenceWindowBuilder:
    """Build deterministic local reference and variant-applied windows."""

    def __init__(
        self,
        reference_store: ReferenceWindowReader | None = None,
        *,
        flank_bp: int = DEFAULT_FLANK_BP,
    ) -> None:
        if flank_bp < 0:
            raise ValueError("flank_bp must be non-negative")
        self.reference_store = reference_store or ReferenceGenomeStore()
        self.flank_bp = flank_bp

    def build(
        self,
        *,
        chrom: str,
        position: int,
        reference_allele: str,
        alternate_allele: str,
        genome_build: str = "GRCh38",
        strand: Strand = "unknown",
        gene: str | None = None,
        transcript: str | None = None,
        cdna_hgvs: str | None = None,
        genomic_hg38: str | None = None,
        flank_bp: int | None = None,
    ) -> LocalSequenceWindowContext:
        ref = _normalize_dna_allele(reference_allele)
        alt = _normalize_dna_allele(alternate_allele)
        normalized_strand = _normalize_strand(strand)
        normalized_genomic_hg38 = genomic_hg38 or f"{chrom}-{position}-{ref}-{alt}"
        warnings: list[str] = []

        if ref is None or alt is None:
            return LocalSequenceWindowContext(
                gene=gene,
                transcript=transcript,
                cdna_hgvs=cdna_hgvs,
                genomic_hg38=normalized_genomic_hg38,
                genome_build=genome_build,
                reference_window=None,
                reference_base_check=None,
                variant_window=None,
                provenance=_provenance_or_none(self.reference_store),
                warnings=(UNSUPPORTED_VARIANT_ALLELE,),
                unavailable_reason=UNSUPPORTED_VARIANT_ALLELE,
            )

        active_flank = self.flank_bp if flank_bp is None else flank_bp
        if active_flank < 0:
            raise ValueError("flank_bp must be non-negative")

        start = max(1, position - active_flank)
        end = position + len(ref) - 1 + active_flank
        try:
            source_window = self.reference_store.get_sequence(
                chrom,
                start,
                end,
                build=genome_build,
            )
            source_base_check = self.reference_store.validate_reference_base(
                chrom,
                position,
                ref[0],
                build=genome_build,
            )
        except ReferenceGenomeStoreError as exc:
            return LocalSequenceWindowContext(
                gene=gene,
                transcript=transcript,
                cdna_hgvs=cdna_hgvs,
                genomic_hg38=normalized_genomic_hg38,
                genome_build=genome_build,
                reference_window=None,
                reference_base_check=None,
                variant_window=None,
                provenance=_provenance_or_none(self.reference_store),
                warnings=(f"{REFERENCE_WINDOW_UNAVAILABLE}:{exc.code}",),
                unavailable_reason=exc.code,
            )

        reference_window = _reference_window(source_window, strand=normalized_strand)
        provenance = _provenance(self.reference_store.metadata())
        offset = position - source_window.start
        observed_allele = source_window.sequence[offset : offset + len(ref)]
        allele_matches = observed_allele == ref
        reference_base_check = _reference_base_check(
            source_base_check,
            expected_allele=ref,
            observed_allele=observed_allele,
            allele_matches=allele_matches,
        )

        if not allele_matches:
            warnings.append(REFERENCE_ALLELE_MISMATCH)
            return LocalSequenceWindowContext(
                gene=gene,
                transcript=transcript,
                cdna_hgvs=cdna_hgvs,
                genomic_hg38=normalized_genomic_hg38,
                genome_build=genome_build,
                reference_window=reference_window,
                reference_base_check=reference_base_check,
                variant_window=None,
                provenance=provenance,
                warnings=tuple(warnings),
                unavailable_reason=REFERENCE_ALLELE_MISMATCH,
            )

        variant_window = _variant_window(
            reference_sequence=source_window.sequence,
            reference_allele=ref,
            alternate_allele=alt,
            offset=offset,
        )
        return LocalSequenceWindowContext(
            gene=gene,
            transcript=transcript,
            cdna_hgvs=cdna_hgvs,
            genomic_hg38=normalized_genomic_hg38,
            genome_build=genome_build,
            reference_window=reference_window,
            reference_base_check=reference_base_check,
            variant_window=variant_window,
            provenance=provenance,
            warnings=tuple(warnings),
        )


def _normalize_dna_allele(value: str) -> str | None:
    normalized = value.strip().upper()
    if not normalized or any(base not in {"A", "C", "G", "T", "N"} for base in normalized):
        return None
    return normalized


def _normalize_strand(value: str) -> Strand:
    if value in {"+", "-", "unknown"}:
        return value  # type: ignore[return-value]
    return "unknown"


def _reference_window(source_window: ReferenceWindow, *, strand: Strand) -> LocalReferenceWindow:
    return LocalReferenceWindow(
        chrom=source_window.chrom,
        start=source_window.start,
        end=source_window.end,
        strand=strand,
        sequence=source_window.sequence,
        genome_build=source_window.genome_build,
        zero_based_start=source_window.zero_based_start,
        zero_based_end_exclusive=source_window.zero_based_end_exclusive,
    )


def _reference_base_check(
    source_base_check: ReferenceBaseCheck,
    *,
    expected_allele: str,
    observed_allele: str | None,
    allele_matches: bool,
) -> LocalReferenceBaseCheck:
    return LocalReferenceBaseCheck(
        position=source_base_check.position,
        expected_base=source_base_check.expected_base,
        observed_base=source_base_check.observed_base,
        matches=source_base_check.matches and allele_matches,
        reason=(
            source_base_check.reason
            if source_base_check.matches and allele_matches
            else REFERENCE_ALLELE_MISMATCH
        ),
        expected_allele=expected_allele,
        observed_allele=observed_allele,
    )


def _variant_window(
    *,
    reference_sequence: str,
    reference_allele: str,
    alternate_allele: str,
    offset: int,
) -> LocalVariantWindow:
    reference_end = offset + len(reference_allele)
    applied_sequence = (
        reference_sequence[:offset] + alternate_allele + reference_sequence[reference_end:]
    )
    return LocalVariantWindow(
        reference_allele=reference_allele,
        alternate_allele=alternate_allele,
        applied_sequence=applied_sequence,
        change_type=_change_type(reference_allele, alternate_allele),
        reference_start_offset=offset,
        reference_end_offset_exclusive=reference_end,
        variant_start_offset=offset,
        variant_end_offset_exclusive=offset + len(alternate_allele),
        flank_convention="genomic_forward_1_based_inclusive_ref_allele_centered",
    )


def _change_type(reference_allele: str, alternate_allele: str) -> VariantChangeType:
    if reference_allele == alternate_allele:
        return "identity"
    if len(reference_allele) == len(alternate_allele):
        return "substitution"
    if len(alternate_allele) > len(reference_allele) and alternate_allele.startswith(
        reference_allele
    ):
        return "insertion"
    if len(reference_allele) > len(alternate_allele) and reference_allele.startswith(
        alternate_allele
    ):
        return "deletion"
    return "delins"


def _provenance(metadata: ReferenceGenomeMetadata) -> SequenceWindowProvenance:
    return SequenceWindowProvenance(
        source_id=metadata.source_id,
        source_url=metadata.source_url,
        source_version=metadata.source_version,
        reader=metadata.reader,
        checksum_algorithm=metadata.checksum_algorithm,
        checksum=metadata.checksum,
        relative_path=metadata.relative_path,
    )


def _provenance_or_none(
    reference_store: ReferenceWindowReader,
) -> SequenceWindowProvenance | None:
    try:
        return _provenance(reference_store.metadata())
    except ReferenceGenomeStoreError:
        return None
