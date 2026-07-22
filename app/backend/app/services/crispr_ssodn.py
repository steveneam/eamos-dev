from __future__ import annotations

import gzip
import re
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.schemas.workbench import (
    CrisprSsodnRequest,
    CrisprSsodnResponse,
    SourceDisclosure,
)
from app.services.crispr_design import reverse_complement
from app.services.reference_genome import ReferenceGenomeStoreError, TwoBitReferenceGenomeStore
from app.services.sequence_context import SequenceContext, unsupported_input_warning

SSODN_LOCAL_TRANSCRIPT_UNAVAILABLE_WARNING = "crispr_ssodn_local_transcript_unavailable"
SSODN_PAM_BLOCK_REVIEW_WARNING = "crispr_ssodn_pam_block_review_required"
SSODN_PAM_BLOCK_NOT_APPLIED_PREFIX = "crispr_ssodn_pam_block_not_applied"

_BASES = {"A", "C", "G", "T"}
_CDNA_SNV_RE = re.compile(
    r"^c\.(?P<pos>\d+)(?P<ref>[ACGT])>(?P<alt>[ACGT])$",
    re.IGNORECASE,
)
_REFSEQ_CHROMOSOME_RE = re.compile(r"^NC_0*(?P<number>\d+)\.\d+$", re.IGNORECASE)
_MANE_GFF_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "bio_assets"
    / "transcripts"
    / "MANE.GRCh38.v1.5.refseq_genomic.gff.gz"
)
_PAM_BLOCK_SWAP = {
    "A": "G",
    "C": "T",
    "G": "A",
    "T": "C",
}
_TRANSCRIPT_COMPLEMENT = str.maketrans("ACGT", "TGCA")
_LOCAL_HG38_REFERENCE_LOCK = threading.RLock()


class CrisprSsodnInputError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        warnings: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.warnings = warnings if warnings is not None else [code]


@dataclass(frozen=True)
class _TranscriptSsodnModel:
    gene: str
    transcript: str
    chrom: str
    strand: str
    cds_intervals: tuple[tuple[int, int], ...]
    exon_intervals: tuple[tuple[int, int], ...]
    cds_coordinates: tuple[int, ...]


@dataclass(frozen=True)
class _ResolvedSsodnWindow:
    reference_sequence: str
    variant_sequence: str
    intron_mask: list[bool]
    variant_offset: int
    strand: str
    template_source: str
    genome_build: str
    reference_base: str
    alternate_base: str
    variant_genomic: str | None = None
    codon_ref: str | None = None
    codon_alt: str | None = None


def design_ssodn(
    payload: CrisprSsodnRequest,
    context: SequenceContext | None,
    *,
    context_warnings: list[str] | None = None,
) -> CrisprSsodnResponse:
    del payload, context
    warnings = list(context_warnings or [])
    code = "crispr_ssodn_hdr_efficiency_contract_unavailable"
    raise CrisprSsodnInputError(
        code=code,
        message=(
            "ssODN output is unavailable until HDR efficiency can be represented "
            "as a typed not-assessed state."
        ),
        warnings=[
            *warnings,
            code,
            "required_contract_amendment:ssodn_hdr_efficiency_optional",
        ],
    )


def _ssodn_source_disclosure(
    template_source: str,
    *,
    warnings: list[str],
) -> SourceDisclosure:
    if template_source == "local_mane_hg38_transcript":
        return SourceDisclosure(
            source_status="source_backed",
            provider_id="local_mane_hg38_ssodn",
            provider_label="Local MANE/hg38 ssODN context",
            cache_status="local",
            warnings=warnings,
        )

    return SourceDisclosure(
        source_status="source_backed",
        provider_id="sequence_context_ssodn",
        provider_label="Sequence-context ssODN provider",
        cache_status="resolved",
        warnings=warnings,
    )


def _context_window(
    payload: CrisprSsodnRequest,
    context: SequenceContext,
    *,
    warnings: list[str],
) -> _ResolvedSsodnWindow:
    del warnings
    reference = (context.reference_base or "").upper()
    alternate = (context.alternate_base or "").upper()
    if (
        len(reference) != 1
        or len(alternate) != 1
        or reference not in _BASES
        or alternate not in _BASES
    ):
        code = unsupported_input_warning("ssodn_variant")
        raise CrisprSsodnInputError(
            code=code,
            message="ssODN donor design currently requires a resolved SNV sequence context.",
            warnings=[code],
        )

    desired_offset = (
        payload.variant_offset
        if payload.variant_offset is not None
        else (payload.oligo_length - 1) // 2
    )
    source_window = _source_context_window(
        context,
        oligo_length=payload.oligo_length,
        desired_offset=desired_offset,
        reference=reference,
    )
    if source_window is None:
        code = "crispr_ssodn_reference_window_unavailable"
        raise CrisprSsodnInputError(
            code=code,
            message="ssODN design requires a source-backed reference window.",
            warnings=[code],
        )
    raw_reference, intron_mask, variant_offset = source_window
    template_source = "sequence_context"
    variant_genomic = _variant_genomic_from_hg38(context.genomic_hg38)

    reference_bases = list(raw_reference.upper())
    variant_bases = reference_bases.copy()
    variant_bases[variant_offset] = alternate
    return _ResolvedSsodnWindow(
        reference_sequence="".join(reference_bases),
        variant_sequence="".join(variant_bases),
        intron_mask=intron_mask,
        variant_offset=variant_offset,
        strand=context.strand if context.strand in {"+", "-"} else "+",
        template_source=template_source,
        genome_build=context.genome_build or payload.genome_build,
        reference_base=reference,
        alternate_base=alternate,
        variant_genomic=variant_genomic,
        codon_ref=context.codon_ref,
        codon_alt=context.codon_alt,
    )


def _local_transcript_window(payload: CrisprSsodnRequest) -> _ResolvedSsodnWindow | None:
    if payload.species != "human" or payload.genome_build not in {"GRCh38", "hg38"}:
        return None
    match = _CDNA_SNV_RE.match(payload.cdna.upper())
    if match is None:
        return None
    cpos = int(match.group("pos"))
    reference = match.group("ref").upper()
    alternate = match.group("alt").upper()
    if payload.transcript:
        transcript = payload.transcript
    else:
        transcript = None
    model = _load_transcript_model(payload.gene, transcript)
    if model is None:
        return None
    if cpos < 1 or cpos > len(model.cds_coordinates):
        return None

    target_coordinate = model.cds_coordinates[cpos - 1]
    variant_offset = (
        payload.variant_offset
        if payload.variant_offset is not None
        else _default_transcript_variant_offset(
            cpos=cpos,
            oligo_length=payload.oligo_length,
            model=model,
        )
    )
    if variant_offset < 0 or variant_offset >= payload.oligo_length:
        return None

    try:
        with _LOCAL_HG38_REFERENCE_LOCK:
            reference_store = _local_hg38_reference_store()
            codon_ref, codon_alt = _codons_for_variant(
                reference_store=reference_store,
                model=model,
                cpos=cpos,
                reference=reference,
                alternate=alternate,
            )
            reference_sequence, variant_sequence, intron_mask = _build_transcript_window(
                reference_store=reference_store,
                model=model,
                target_coordinate=target_coordinate,
                variant_offset=variant_offset,
                oligo_length=payload.oligo_length,
                reference=reference,
                alternate=alternate,
            )
    except (OSError, ReferenceGenomeStoreError, ValueError):
        return None

    return _ResolvedSsodnWindow(
        reference_sequence=reference_sequence,
        variant_sequence=variant_sequence,
        intron_mask=intron_mask,
        variant_offset=variant_offset,
        strand=model.strand,
        template_source="local_mane_hg38_transcript",
        genome_build=payload.genome_build,
        reference_base=reference,
        alternate_base=alternate,
        variant_genomic=_format_variant_genomic(model.chrom, target_coordinate),
        codon_ref=codon_ref,
        codon_alt=codon_alt,
    )


@lru_cache(maxsize=32)
def _load_transcript_model(
    gene: str,
    transcript: str | None,
) -> _TranscriptSsodnModel | None:
    if not _MANE_GFF_PATH.is_file():
        return None
    requested_gene = gene.strip().upper()
    requested_transcript = _versionless(transcript) if transcript else None
    mrnas: dict[str, tuple[str, str, str, str, bool]] = {}
    cds_by_parent: dict[str, list[tuple[int, int]]] = {}
    exons_by_parent: dict[str, list[tuple[int, int]]] = {}

    try:
        handle = gzip.open(_MANE_GFF_PATH, "rt", encoding="utf-8", errors="replace")
    except OSError:
        return None
    with handle:
        for raw_line in handle:
            if raw_line.startswith("#"):
                continue
            parts = raw_line.rstrip("\n").split("\t")
            if len(parts) < 9:
                continue
            chrom, _source, feature, start, end, _score, strand, _phase, raw_attrs = parts
            attrs = _parse_gff_attributes(raw_attrs)
            if attrs.get("gene", "").upper() != requested_gene:
                continue
            if feature == "mRNA":
                parent_id = attrs.get("ID")
                name = attrs.get("Name", "")
                if parent_id:
                    mrnas[parent_id] = (
                        name,
                        chrom,
                        strand,
                        attrs.get("tag", ""),
                        "MANE" in attrs.get("tag", ""),
                    )
                continue
            parent = attrs.get("Parent")
            if parent is None:
                continue
            if feature == "CDS":
                cds_by_parent.setdefault(parent, []).append((int(start), int(end)))
            elif feature == "exon":
                exons_by_parent.setdefault(parent, []).append((int(start), int(end)))

    selected_parent: str | None = None
    for parent, (name, _chrom, _strand, _tag, _is_mane) in mrnas.items():
        if requested_transcript and _versionless(name) == requested_transcript:
            selected_parent = parent
            break
    if selected_parent is None:
        for parent, (_name, _chrom, _strand, _tag, is_mane) in mrnas.items():
            if is_mane:
                selected_parent = parent
                break
    if selected_parent is None and mrnas:
        selected_parent = next(iter(mrnas))
    if selected_parent is None:
        return None

    name, chrom, strand, _tag, _is_mane = mrnas[selected_parent]
    cds_intervals = tuple(sorted(cds_by_parent.get(selected_parent, [])))
    exon_intervals = tuple(sorted(exons_by_parent.get(selected_parent, [])))
    if not cds_intervals or not exon_intervals or strand not in {"+", "-"}:
        return None
    cds_coordinates = _transcript_coordinates(cds_intervals, strand=strand)
    if not cds_coordinates:
        return None
    return _TranscriptSsodnModel(
        gene=requested_gene,
        transcript=name,
        chrom=chrom,
        strand=strand,
        cds_intervals=cds_intervals,
        exon_intervals=exon_intervals,
        cds_coordinates=cds_coordinates,
    )


@lru_cache(maxsize=1)
def _local_hg38_reference_store() -> TwoBitReferenceGenomeStore:
    return TwoBitReferenceGenomeStore.local_hg38()


def _build_transcript_window(
    *,
    reference_store: TwoBitReferenceGenomeStore,
    model: _TranscriptSsodnModel,
    target_coordinate: int,
    variant_offset: int,
    oligo_length: int,
    reference: str,
    alternate: str,
) -> tuple[str, str, list[bool]]:
    positions = _output_genomic_positions(
        target_coordinate=target_coordinate,
        variant_offset=variant_offset,
        oligo_length=oligo_length,
        strand=model.strand,
    )
    start = min(positions)
    end = max(positions)
    source_window = reference_store.get_sequence(model.chrom, start, end, build="GRCh38")
    reference_bases: list[str] = []
    variant_bases: list[str] = []
    intron_mask: list[bool] = []

    for index, position in enumerate(positions):
        genomic_base = source_window.sequence[position - source_window.start]
        transcript_base = _to_transcript_base(genomic_base, strand=model.strand)
        reference_bases.append(transcript_base)
        variant_bases.append(alternate if index == variant_offset else transcript_base)
        intron_mask.append(not _is_position_in_intervals(position, model.exon_intervals))

    if reference_bases[variant_offset] != reference:
        raise ValueError("local transcript reference base does not match requested cDNA edit")
    return "".join(reference_bases), "".join(variant_bases), intron_mask


def _default_transcript_variant_offset(
    *,
    cpos: int,
    oligo_length: int,
    model: _TranscriptSsodnModel,
) -> int:
    codon_index = (cpos - 1) % 3
    codon_start_cpos = cpos - codon_index
    codon_start_coordinate = model.cds_coordinates[codon_start_cpos - 1]
    codon_start_offset = oligo_length // 2
    exonic_bases_before = _same_exon_transcript_bases_before(
        codon_start_coordinate,
        model=model,
    )
    if exonic_bases_before < 4 and codon_start_offset >= 4:
        codon_start_offset = (codon_start_offset - 4) + exonic_bases_before
    return codon_start_offset + codon_index


def _same_exon_transcript_bases_before(
    coordinate: int,
    *,
    model: _TranscriptSsodnModel,
) -> int:
    exon = next(
        ((start, end) for start, end in model.exon_intervals if start <= coordinate <= end),
        None,
    )
    if exon is None:
        return 0
    start, end = exon
    if model.strand == "-":
        return end - coordinate
    return coordinate - start


def _codons_for_variant(
    *,
    reference_store: TwoBitReferenceGenomeStore,
    model: _TranscriptSsodnModel,
    cpos: int,
    reference: str,
    alternate: str,
) -> tuple[str | None, str | None]:
    codon_index = (cpos - 1) % 3
    codon_start = cpos - codon_index
    if codon_start < 1 or codon_start + 2 > len(model.cds_coordinates):
        return None, None
    try:
        bases = [
            _transcript_base_at(
                reference_store,
                model=model,
                coordinate=model.cds_coordinates[codon_start + offset - 1],
            )
            for offset in range(3)
        ]
    except (OSError, ReferenceGenomeStoreError):
        return None, None
    if bases[codon_index] != reference:
        return None, None
    codon_ref = "".join(bases)
    bases[codon_index] = alternate
    return codon_ref, "".join(bases)


def _transcript_base_at(
    reference_store: TwoBitReferenceGenomeStore,
    *,
    model: _TranscriptSsodnModel,
    coordinate: int,
) -> str:
    window = reference_store.get_sequence(model.chrom, coordinate, coordinate, build="GRCh38")
    return _to_transcript_base(window.sequence, strand=model.strand)


def _to_transcript_base(base: str, *, strand: str) -> str:
    normalized = base.upper()
    if strand == "-":
        return normalized.translate(_TRANSCRIPT_COMPLEMENT)
    return normalized


def _variant_genomic_from_hg38(genomic_hg38: str | None) -> str | None:
    if not genomic_hg38:
        return None
    chrom, sep, rest = genomic_hg38.partition("-")
    if not sep:
        return None
    position_text = rest.split("-", 1)[0]
    try:
        position = int(position_text)
    except ValueError:
        return None
    return _format_variant_genomic(chrom, position)


def _format_variant_genomic(chromosome: str, position: int) -> str:
    return f"{_display_chromosome(chromosome)}:{position}"


def _display_chromosome(chromosome: str) -> str:
    normalized = chromosome.strip()
    if not normalized:
        return "chr?"
    if normalized.lower().startswith("chr"):
        return f"chr{normalized[3:]}"
    if normalized.upper() in {"X", "Y", "M", "MT"} or normalized.isdigit():
        return f"chr{'M' if normalized.upper() == 'MT' else normalized.upper()}"
    match = _REFSEQ_CHROMOSOME_RE.match(normalized)
    if match is None:
        return normalized
    number = int(match.group("number"))
    if 1 <= number <= 22:
        return f"chr{number}"
    if number == 23:
        return "chrX"
    if number == 24:
        return "chrY"
    if number == 12920:
        return "chrM"
    return normalized


def _output_genomic_positions(
    *,
    target_coordinate: int,
    variant_offset: int,
    oligo_length: int,
    strand: str,
) -> list[int]:
    if strand == "-":
        return [target_coordinate + variant_offset - index for index in range(oligo_length)]
    return [target_coordinate - variant_offset + index for index in range(oligo_length)]


def _transcript_coordinates(
    intervals: tuple[tuple[int, int], ...],
    *,
    strand: str,
) -> tuple[int, ...]:
    coordinates: list[int] = []
    if strand == "-":
        ordered = sorted(intervals, reverse=True)
        for start, end in ordered:
            coordinates.extend(range(end, start - 1, -1))
    else:
        ordered = sorted(intervals)
        for start, end in ordered:
            coordinates.extend(range(start, end + 1))
    return tuple(coordinates)


def _is_position_in_intervals(position: int, intervals: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= position <= end for start, end in intervals)


def _parse_gff_attributes(raw_attrs: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for item in raw_attrs.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        attrs[key] = value
    return attrs


def _versionless(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().split(".", 1)[0].upper()


def _source_context_window(
    context: SequenceContext,
    *,
    oligo_length: int,
    desired_offset: int,
    reference: str,
) -> tuple[str, list[bool], int] | None:
    raw_sequence = re.sub(r"\s+", "", context.window_sequence or "")
    start = context.target_offset - desired_offset
    end = start + oligo_length
    if start < 0 or end > len(raw_sequence):
        return None
    variant_offset = context.target_offset - start
    window = raw_sequence[start:end]
    if window[variant_offset].upper() != reference:
        return None
    return window, [base.islower() for base in window], variant_offset


def _apply_pam_blocking_edit(
    bases: list[str],
    *,
    variant_offset: int,
    payload: CrisprSsodnRequest,
) -> str:
    candidates = [value for value in (payload.pam_sequence, payload.guide_sequence) if value]
    if not candidates:
        return f"{SSODN_PAM_BLOCK_NOT_APPLIED_PREFIX}:missing_guide_or_pam"

    donor = "".join(bases).upper()
    for candidate in candidates:
        if candidate is None:
            continue
        start = donor.find(candidate.upper())
        if start < 0:
            continue
        for index in range(start, start + len(candidate)):
            if index == variant_offset:
                continue
            base = bases[index]
            replacement = _PAM_BLOCK_SWAP.get(base)
            if replacement is not None:
                bases[index] = replacement
                return SSODN_PAM_BLOCK_REVIEW_WARNING
    return f"{SSODN_PAM_BLOCK_NOT_APPLIED_PREFIX}:target_not_found"


def _apply_intron_case(bases: list[str], intron_mask: list[bool]) -> str:
    return "".join(
        base.lower() if intron else base.upper() for base, intron in zip(bases, intron_mask)
    )


def _reverse_complement_with_mask(
    sequence: str,
    intron_mask: list[bool],
    *,
    apply_intron_case: bool = True,
) -> tuple[str, list[bool]]:
    rc_mask = list(reversed(intron_mask))
    rc_bases = list(reverse_complement(sequence.upper()))
    if apply_intron_case:
        return _apply_intron_case(rc_bases, rc_mask), rc_mask
    return "".join(rc_bases), rc_mask


def _output_strand(payload: CrisprSsodnRequest, source_strand: str) -> str:
    if payload.strand in {"+", "-"}:
        return payload.strand
    if source_strand in {"+", "-"}:
        return source_strand
    return "+"


def _oligo_name(
    payload: CrisprSsodnRequest,
    *,
    codon_ref: str | None,
    codon_alt: str | None,
) -> str:
    parts = [f"ss oligo for {payload.cdna}"]
    if payload.protein_change:
        parts.append(payload.protein_change)
    if codon_ref and codon_alt:
        parts.append(f"{codon_ref} > {codon_alt}")
    return "; ".join(parts)


def _dedupe_warnings(warnings: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for warning in warnings:
        if warning and warning not in seen:
            seen.add(warning)
            ordered.append(warning)
    return ordered
