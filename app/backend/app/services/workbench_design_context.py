from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from fastapi import status

from app.schemas.workflow import WorkbenchDesignContextV2, WorkbenchSparseEditV2
from app.services.sequence_context import SequenceContext, SequenceContextResult
from app.services.workbench_design_common import HTTP_UNPROCESSABLE_ENTITY, WorkbenchDesignError

WORKBENCH_CONTEXT_SOURCE_UNAVAILABLE = "workbench_context_source_unavailable"
WORKBENCH_CONTEXT_IDENTITY_MISMATCH = "workbench_context_identity_mismatch"
WORKBENCH_CONTEXT_REFERENCE_DIGEST_MISMATCH = "workbench_context_reference_digest_mismatch"
WORKBENCH_CONTEXT_EDIT_REFERENCE_MISMATCH = "workbench_context_edit_reference_mismatch"
WORKBENCH_CONTEXT_SELECTION_DIGEST_MISMATCH = "workbench_context_selection_digest_mismatch"
WORKBENCH_CONTEXT_SELECTION_UNAVAILABLE = "workbench_context_selection_unavailable"

_COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


@dataclass(frozen=True)
class VerifiedWorkbenchContext:
    context: WorkbenchDesignContextV2
    source_context: SequenceContext
    reference_sequence: str
    reference_coordinates: tuple[int, ...]
    effective_sequence: str
    selected_sequence: str
    selected_coordinates: tuple[int | None, ...]
    engine_context: SequenceContext
    source_identity_verified: bool

    def reference_sequence_at_genomic_interval(self, start: int, end: int) -> str | None:
        if start > end:
            return None
        by_coordinate = dict(zip(self.reference_coordinates, self.reference_sequence, strict=True))
        try:
            return "".join(by_coordinate[position] for position in range(start, end + 1))
        except KeyError:
            return None

    def genomic_coordinate(self, template_offset: int) -> int | None:
        if template_offset < 0 or template_offset >= len(self.selected_coordinates):
            return None
        return self.selected_coordinates[template_offset]

    def genomic_interval(self, start: int, end: int) -> tuple[int, int] | None:
        """Map a half-open selected-template interval to one contiguous genomic interval."""

        if start < 0 or end <= start or end > len(self.selected_coordinates):
            return None
        coordinates = self.selected_coordinates[start:end]
        if any(coordinate is None for coordinate in coordinates):
            return None
        concrete = tuple(int(coordinate) for coordinate in coordinates if coordinate is not None)
        if len(concrete) != end - start:
            return None
        step = 1 if concrete[-1] >= concrete[0] else -1
        if any(later - earlier != step for earlier, later in zip(concrete, concrete[1:])):
            return None
        return min(concrete), max(concrete)

    def genomic_strand(self, template_strand: str) -> str:
        if template_strand not in {"+", "-"}:
            raise ValueError("template_strand must be '+' or '-'")
        coordinates = tuple(
            coordinate for coordinate in self.selected_coordinates if coordinate is not None
        )
        orientation_reversed = len(coordinates) > 1 and coordinates[0] > coordinates[-1]
        if not orientation_reversed:
            return template_strand
        return "+" if template_strand == "-" else "-"

    def sequence_at_genomic_interval(
        self,
        start: int,
        end: int,
        *,
        strand: str,
    ) -> str | None:
        if start > end or strand not in {"+", "-"}:
            return None
        by_coordinate: dict[int, str] = {}
        for base, coordinate in zip(
            self.selected_sequence,
            self.selected_coordinates,
            strict=True,
        ):
            if coordinate is not None:
                by_coordinate[coordinate] = base
        try:
            sequence = "".join(by_coordinate[position] for position in range(start, end + 1))
        except KeyError:
            return None
        return sequence if strand == "+" else _reverse_complement(sequence)


def verify_workbench_design_context_v2(
    context: WorkbenchDesignContextV2,
    resolved: SequenceContextResult,
) -> VerifiedWorkbenchContext:
    """Verify and execute a declared Workbench V2 sequence context.

    The request contract binds metadata and digests. This function closes the
    runtime boundary by independently resolving the source bases, comparing the
    immutable reference digest, replaying sparse edits, and deriving the exact
    selected sequence supplied to an engine. No raw bases are included in an
    exception or disclosure.
    """

    source = resolved.context
    if source is None or source.source != "resolver":
        raise WorkbenchDesignError(
            code=WORKBENCH_CONTEXT_SOURCE_UNAVAILABLE,
            message="A source-backed sequence basis is required to execute this Workbench context.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            warnings=[WORKBENCH_CONTEXT_SOURCE_UNAVAILABLE],
        )

    _verify_context_identity(context, source)
    source_sequence = _normalize_source_sequence(source.window_sequence)
    source_chrom, source_position = _resolved_locus(source)
    source_start = source_position - source.target_offset
    source_end = source_start + len(source_sequence) - 1
    reference = context.reference
    if (
        _normalize_chromosome(reference.chrom) != source_chrom
        or reference.genomic_start != source_start
        or reference.genomic_end != source_end
        or reference.sequence_length != len(source_sequence)
    ):
        raise _identity_mismatch(
            "The resolved sequence interval does not match the declared reference basis."
        )

    reference_sequence, reference_coordinates = _orient_reference(
        source_sequence,
        start=source_start,
        end=source_end,
        orientation=reference.orientation,
        strand=reference.strand,
    )
    if _sha256(reference_sequence) != reference.sequence_sha256:
        raise WorkbenchDesignError(
            code=WORKBENCH_CONTEXT_REFERENCE_DIGEST_MISMATCH,
            message="The resolved source bases do not match the declared reference digest.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=[WORKBENCH_CONTEXT_REFERENCE_DIGEST_MISMATCH],
        )
    source_identity_verified = _verify_source_identity_metadata(context, source)

    effective_sequence, _effective_coordinates = _apply_edits(
        reference_sequence,
        reference_coordinates,
        context.edits,
        segment_start=0,
        segment_end=len(reference_sequence),
    )
    if _sha256(effective_sequence) != context.selection.sequence_sha256:
        raise WorkbenchDesignError(
            code=WORKBENCH_CONTEXT_SELECTION_DIGEST_MISMATCH,
            message="The replayed sequence does not match the declared selection-basis digest.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=[WORKBENCH_CONTEXT_SELECTION_DIGEST_MISMATCH],
        )

    selection_start, selection_end = _selection_reference_offsets(
        context,
        reference_coordinates,
    )
    selected_sequence, selected_coordinates = _apply_edits(
        reference_sequence,
        reference_coordinates,
        context.edits,
        segment_start=selection_start,
        segment_end=selection_end,
    )
    if not selected_sequence:
        raise WorkbenchDesignError(
            code=WORKBENCH_CONTEXT_SELECTION_UNAVAILABLE,
            message="The verified Workbench selection is empty after replaying edits.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=[WORKBENCH_CONTEXT_SELECTION_UNAVAILABLE],
        )

    target_offset, target_warnings = _target_offset(
        source_position,
        selected_coordinates,
    )
    engine_context = source.model_copy(
        update={
            "gene": context.variant.gene,
            "cdna": context.variant.cdna,
            "transcript": context.variant.transcript,
            "transcript_hgvs": f"{context.variant.transcript}:{context.variant.cdna}",
            "genome_build": context.reference.genome_build,
            "genomic_hg38": context.variant.genomic_hg38,
            "strand": context.reference.strand,
            "window_sequence": selected_sequence,
            "target_offset": target_offset,
            "genomic_coordinates": selected_coordinates,
            "source_metadata": {
                **source.source_metadata,
                "context_digest": context.context_digest,
                "reference_sequence_sha256": context.reference.sequence_sha256,
                "selection_sequence_sha256": context.selection.sequence_sha256,
                "selection_genomic_start": str(context.selection.genomic_start),
                "selection_genomic_end": str(context.selection.genomic_end),
                "selection_orientation": context.selection.orientation,
            },
            "warnings": [
                *source.warnings,
                *target_warnings,
                *(
                    []
                    if source_identity_verified
                    else ["workbench_reference_source_identity_metadata_unavailable"]
                ),
            ],
        }
    )
    return VerifiedWorkbenchContext(
        context=context,
        source_context=source,
        reference_sequence=reference_sequence,
        reference_coordinates=reference_coordinates,
        effective_sequence=effective_sequence,
        selected_sequence=selected_sequence,
        selected_coordinates=selected_coordinates,
        engine_context=engine_context,
        source_identity_verified=source_identity_verified,
    )


def _verify_context_identity(
    context: WorkbenchDesignContextV2,
    source: SequenceContext,
) -> None:
    if (
        source.gene.upper() != context.variant.gene.upper()
        or source.cdna != context.variant.cdna
        or source.transcript != context.variant.transcript
        or source.genome_build.upper() not in {"GRCH38", "HG38"}
        or context.reference.genome_build != "GRCh38"
    ):
        raise _identity_mismatch(
            "The resolved variant identity does not match the declared Workbench context."
        )
    if source.strand in {"+", "-"} and source.strand != context.reference.strand:
        raise _identity_mismatch(
            "The resolved transcript strand does not match the declared reference basis."
        )
    if context.variant.genomic_hg38 is not None:
        declared = _normalized_variant_locus(context.variant.genomic_hg38)
        observed = _normalized_variant_locus(source.genomic_hg38)
        if declared is None or observed is None or declared != observed:
            raise _identity_mismatch(
                "The resolved genomic allele does not match the declared variant identity."
            )

    source_sequence = _normalize_source_sequence(source.window_sequence)
    reference = (source.reference_base or "").upper()
    alternate = (source.alternate_base or "").upper()
    if (
        not reference
        or not alternate
        or re.fullmatch(r"[ACGTN]+", reference) is None
        or re.fullmatch(r"[ACGTN]+", alternate) is None
        or source.target_offset < 0
        or source.target_offset + len(reference) > len(source_sequence)
        or source_sequence[source.target_offset : source.target_offset + len(reference)]
        != reference
    ):
        raise _identity_mismatch(
            "The resolved reference allele does not match the source sequence basis."
        )


def _normalized_variant_locus(value: str | None) -> tuple[str, int, str, str] | None:
    if value is None:
        return None
    match = re.fullmatch(
        r"(?:chr)?(?P<chrom>\d+|X|Y|M|MT)-(?P<position>\d+)-"
        r"(?P<reference>[ACGTN]+)-(?P<alternate>[ACGTN]+)",
        value,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return (
        _normalize_chromosome(match.group("chrom")),
        int(match.group("position")),
        match.group("reference").upper(),
        match.group("alternate").upper(),
    )


def _verify_source_identity_metadata(
    context: WorkbenchDesignContextV2,
    source: SequenceContext,
) -> bool:
    declared = {
        "source_id": context.reference.source_id,
        "source_release": context.reference.source_release,
        "source_record_id": context.reference.source_record_id,
    }
    complete = True
    for key, expected in declared.items():
        observed = source.source_metadata.get(key)
        if observed is None:
            complete = False
        elif observed != expected:
            raise _identity_mismatch(
                "Resolved source identity metadata does not match the declared reference basis."
            )
    return complete


def _normalize_source_sequence(sequence: str) -> str:
    normalized = re.sub(r"\s+", "", sequence).upper()
    if not normalized or re.fullmatch(r"[ACGTN]+", normalized) is None:
        raise _identity_mismatch("The resolved reference sequence is malformed.")
    return normalized


def _resolved_locus(source: SequenceContext) -> tuple[str, int]:
    if not source.genomic_hg38:
        raise _identity_mismatch("The resolved source context has no GRCh38 locus.")
    match = re.fullmatch(
        r"(?:chr)?(?P<chrom>\d+|X|Y|M|MT)-(?P<position>\d+)-[ACGTN]+-[ACGTN]+",
        source.genomic_hg38,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise _identity_mismatch("The resolved source context has an unsupported GRCh38 locus.")
    return _normalize_chromosome(match.group("chrom")), int(match.group("position"))


def _orient_reference(
    sequence: str,
    *,
    start: int,
    end: int,
    orientation: str,
    strand: str,
) -> tuple[str, tuple[int, ...]]:
    reverse = orientation == "genomic_reverse" or (orientation == "transcript" and strand == "-")
    if reverse:
        return _reverse_complement(sequence), tuple(range(end, start - 1, -1))
    return sequence, tuple(range(start, end + 1))


def _selection_reference_offsets(
    context: WorkbenchDesignContextV2,
    coordinates: tuple[int, ...],
) -> tuple[int, int]:
    selected = [
        index
        for index, coordinate in enumerate(coordinates)
        if context.selection.genomic_start <= coordinate <= context.selection.genomic_end
    ]
    if not selected or selected != list(range(selected[0], selected[-1] + 1)):
        raise WorkbenchDesignError(
            code=WORKBENCH_CONTEXT_SELECTION_UNAVAILABLE,
            message="The declared selection cannot be mapped onto the verified reference basis.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=[WORKBENCH_CONTEXT_SELECTION_UNAVAILABLE],
        )
    return selected[0], selected[-1] + 1


def _apply_edits(
    reference: str,
    coordinates: tuple[int, ...],
    edits: list[WorkbenchSparseEditV2],
    *,
    segment_start: int,
    segment_end: int,
) -> tuple[str, tuple[int | None, ...]]:
    pieces: list[str] = []
    mapped: list[int | None] = []
    cursor = segment_start
    for edit in edits:
        if edit.end_offset <= segment_start and not (
            edit.operation == "insertion" and edit.start_offset == segment_start
        ):
            continue
        if edit.start_offset >= segment_end:
            continue
        if edit.start_offset < segment_start or edit.end_offset > segment_end:
            raise WorkbenchDesignError(
                code=WORKBENCH_CONTEXT_SELECTION_UNAVAILABLE,
                message="A sparse edit crosses the declared selection boundary.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=[WORKBENCH_CONTEXT_SELECTION_UNAVAILABLE],
            )
        observed = reference[edit.start_offset : edit.end_offset]
        if observed != edit.reference_bases:
            raise WorkbenchDesignError(
                code=WORKBENCH_CONTEXT_EDIT_REFERENCE_MISMATCH,
                message="A sparse edit does not match the verified reference bases.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=[WORKBENCH_CONTEXT_EDIT_REFERENCE_MISMATCH],
            )
        pieces.append(reference[cursor : edit.start_offset])
        mapped.extend(coordinates[cursor : edit.start_offset])
        pieces.append(edit.alternate_bases)
        replaced_coordinates = coordinates[edit.start_offset : edit.end_offset]
        shared = min(len(replaced_coordinates), len(edit.alternate_bases))
        mapped.extend(replaced_coordinates[:shared])
        mapped.extend([None] * (len(edit.alternate_bases) - shared))
        cursor = edit.end_offset
    pieces.append(reference[cursor:segment_end])
    mapped.extend(coordinates[cursor:segment_end])
    return "".join(pieces), tuple(mapped)


def _target_offset(
    genomic_position: int,
    coordinates: tuple[int | None, ...],
) -> tuple[int, list[str]]:
    exact = next(
        (index for index, coordinate in enumerate(coordinates) if coordinate == genomic_position),
        None,
    )
    if exact is not None:
        return exact, []
    return len(coordinates) // 2, ["workbench_selection_excludes_variant_locus"]


def _identity_mismatch(message: str) -> WorkbenchDesignError:
    return WorkbenchDesignError(
        code=WORKBENCH_CONTEXT_IDENTITY_MISMATCH,
        message=message,
        status_code=HTTP_UNPROCESSABLE_ENTITY,
        warnings=[WORKBENCH_CONTEXT_IDENTITY_MISMATCH],
    )


def _normalize_chromosome(chromosome: str) -> str:
    normalized = chromosome.strip().removeprefix("chr").removeprefix("CHR").upper()
    if normalized == "MT":
        normalized = "M"
    return f"chr{normalized}"


def _reverse_complement(sequence: str) -> str:
    return sequence.translate(_COMPLEMENT)[::-1]


def _sha256(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()
