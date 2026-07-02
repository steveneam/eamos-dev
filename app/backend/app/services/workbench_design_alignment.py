from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, NoReturn

from fastapi import status

from app.schemas.workbench import AlignRequest, AlignResponse, TraceChannel
from app.services.sequence_context import SequenceContext, unsupported_input_warning
from app.services.trace_parser import (
    TRACE_INVALID_BASE64,
    TRACE_PAYLOAD_TOO_LARGE,
    TRACE_PARSER_UNAVAILABLE,
    ParsedTrace,
    TraceParseError,
    parse_ab1_base64,
    parse_ab1_bytes,
)
from app.services.workbench_design_common import (
    ALIGN_GAP_SCORE,
    ALIGN_MATCH_SCORE,
    ALIGN_MAX_MATRIX_CELLS,
    ALIGN_MAX_SEQUENCE_BASES,
    ALIGN_MISMATCH_SCORE,
    HTTP_UNPROCESSABLE_ENTITY,
    WORKBENCH_PROVIDER_MALFORMED,
    WORKBENCH_PROVIDER_UNAVAILABLE,
    WorkbenchDesignError,
    _clean_template,
)


@dataclass(frozen=True)
class AlignmentCell:
    reference_base: str
    read_base: str
    reference_index: int | None
    read_index: int | None


class LocalSangerAlignmentProvider:
    def align(self, payload: AlignRequest, context: SequenceContext) -> AlignResponse:
        reference = _clean_template(context.window_sequence)
        if not reference:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_MALFORMED,
                message="Sequence context did not include a reference window for alignment.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        if context.target_offset < 0 or context.target_offset >= len(reference):
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_MALFORMED,
                message="Sequence context target offset is outside the alignment template.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        read, trace = _alignment_read(payload)
        _validate_alignment_size(reference=reference, read=read)
        cells = _align_sequences(reference=reference, read=read)
        return _alignment_response(
            cells,
            target_offset=context.target_offset,
            trace=trace,
            read=read,
        )


def _alignment_read(payload: AlignRequest) -> tuple[str, ParsedTrace | None]:
    if payload.user_sequence and payload.ab1_blob_base64:
        code = unsupported_input_warning("alignment_read")
        raise WorkbenchDesignError(
            code=code,
            message="Provide either user_sequence or ab1_blob_base64, not both.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=[code],
        )

    if payload.ab1_blob_base64:
        trace = _parse_ab1_trace(payload.ab1_blob_base64)
        return trace.sequence, trace

    if payload.user_sequence:
        return _parse_alignment_sequence(payload.user_sequence), None

    code = unsupported_input_warning("alignment_read")
    raise WorkbenchDesignError(
        code=code,
        message="Real-mode alignment requires user_sequence or ab1_blob_base64.",
        status_code=HTTP_UNPROCESSABLE_ENTITY,
        warnings=[code],
    )


def _parse_ab1_trace(blob: str) -> ParsedTrace:
    try:
        return parse_ab1_base64(blob)
    except TraceParseError as exc:
        _raise_trace_parse_error(exc, encoded=True)


def _parse_ab1_trace_bytes(data: bytes) -> ParsedTrace:
    try:
        return parse_ab1_bytes(data)
    except TraceParseError as exc:
        _raise_trace_parse_error(exc, encoded=False)


def _raise_trace_parse_error(exc: TraceParseError, *, encoded: bool) -> NoReturn:
    if exc.code == TRACE_PARSER_UNAVAILABLE:
        raise WorkbenchDesignError(
            code=WORKBENCH_PROVIDER_UNAVAILABLE,
            message=exc.message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            warnings=[WORKBENCH_PROVIDER_UNAVAILABLE, exc.code],
        ) from exc

    kind = (
        "ab1_blob_base64"
        if encoded and exc.code in {TRACE_INVALID_BASE64, TRACE_PAYLOAD_TOO_LARGE}
        else "ab1"
    )
    code = unsupported_input_warning(kind)
    raise WorkbenchDesignError(
        code=code,
        message=exc.message,
        status_code=HTTP_UNPROCESSABLE_ENTITY,
        warnings=[code, exc.code],
    ) from exc


def _parse_alignment_sequence(raw_sequence: str) -> str:
    bases: list[str] = []
    invalid: set[str] = set()
    for raw_line in raw_sequence.splitlines():
        line = raw_line.strip()
        if line.startswith(">"):
            continue
        for char in raw_line:
            if char.isspace() or char.isdigit():
                continue
            base = char.upper()
            if base == "U":
                bases.append("T")
            elif base in {"A", "C", "G", "T", "N"}:
                bases.append(base)
            else:
                invalid.add(char)

            if len(bases) > ALIGN_MAX_SEQUENCE_BASES:
                code = unsupported_input_warning("alignment_length")
                raise WorkbenchDesignError(
                    code=code,
                    message=(
                        "Alignment read is too long for the local Workbench aligner "
                        f"({ALIGN_MAX_SEQUENCE_BASES} bp limit)."
                    ),
                    status_code=HTTP_UNPROCESSABLE_ENTITY,
                    warnings=[code],
                )

    if invalid:
        code = unsupported_input_warning("alignment_sequence")
        invalid_text = " ".join(sorted(invalid))
        raise WorkbenchDesignError(
            code=code,
            message=f"Alignment read contains unsupported characters: {invalid_text}.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=[code],
        )

    sequence = "".join(bases)
    if not sequence:
        code = unsupported_input_warning("alignment_read")
        raise WorkbenchDesignError(
            code=code,
            message="Alignment read is empty.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=[code],
        )
    return sequence


def _validate_alignment_size(*, reference: str, read: str) -> None:
    if len(reference) <= ALIGN_MAX_SEQUENCE_BASES and len(read) <= ALIGN_MAX_SEQUENCE_BASES:
        return

    code = unsupported_input_warning("alignment_length")
    raise WorkbenchDesignError(
        code=code,
        message=(
            "Alignment input is too long for the local Workbench aligner "
            f"({ALIGN_MAX_SEQUENCE_BASES} bp limit per sequence)."
        ),
        status_code=HTTP_UNPROCESSABLE_ENTITY,
        warnings=[code],
    )


def _align_sequences(*, reference: str, read: str) -> tuple[AlignmentCell, ...]:
    if _alignment_matrix_cells(reference=reference, read=read) > ALIGN_MAX_MATRIX_CELLS:
        return _positional_alignment(reference=reference, read=read)

    bio_cells = _bio_pairwise_alignment(reference=reference, read=read)
    if bio_cells:
        return bio_cells
    return _fallback_alignment(reference=reference, read=read)


def _bio_pairwise_alignment(*, reference: str, read: str) -> tuple[AlignmentCell, ...] | None:
    try:
        pairwise_aligner = import_module("Bio.Align").PairwiseAligner
    except (AttributeError, ImportError, ModuleNotFoundError):
        return None

    try:
        aligner = pairwise_aligner()
        aligner.mode = "global" if len(reference) == len(read) else "local"
        aligner.match_score = ALIGN_MATCH_SCORE
        aligner.mismatch_score = ALIGN_MISMATCH_SCORE
        aligner.open_gap_score = ALIGN_GAP_SCORE
        aligner.extend_gap_score = ALIGN_GAP_SCORE
        alignments = aligner.align(reference, read)
        alignment = alignments[0]
    except Exception:
        return None

    if getattr(alignment, "score", 0) <= 0:
        return None
    try:
        return _cells_from_bio_alignment(
            reference=reference,
            read=read,
            aligned=getattr(alignment, "aligned", None),
            local=aligner.mode == "local",
        )
    except Exception:
        return None


def _cells_from_bio_alignment(
    *,
    reference: str,
    read: str,
    aligned: Any,
    local: bool,
) -> tuple[AlignmentCell, ...] | None:
    if aligned is None or len(aligned) < 2:
        return None

    reference_blocks = _alignment_blocks(aligned[0])
    read_blocks = _alignment_blocks(aligned[1])
    if not reference_blocks or not read_blocks:
        return None

    cells: list[AlignmentCell] = []
    reference_pos = reference_blocks[0][0] if local else 0
    read_pos = read_blocks[0][0] if local else 0

    for (reference_start, reference_end), (read_start, read_end) in zip(
        reference_blocks,
        read_blocks,
        strict=True,
    ):
        while reference_pos < reference_start and read_pos < read_start:
            cells.append(
                AlignmentCell(
                    reference_base=reference[reference_pos],
                    read_base=read[read_pos],
                    reference_index=reference_pos,
                    read_index=read_pos,
                )
            )
            reference_pos += 1
            read_pos += 1
        while reference_pos < reference_start:
            cells.append(
                AlignmentCell(
                    reference_base=reference[reference_pos],
                    read_base="-",
                    reference_index=reference_pos,
                    read_index=None,
                )
            )
            reference_pos += 1
        while read_pos < read_start:
            cells.append(
                AlignmentCell(
                    reference_base="-",
                    read_base=read[read_pos],
                    reference_index=None,
                    read_index=read_pos,
                )
            )
            read_pos += 1

        block_length = min(reference_end - reference_start, read_end - read_start)
        for offset in range(block_length):
            cells.append(
                AlignmentCell(
                    reference_base=reference[reference_start + offset],
                    read_base=read[read_start + offset],
                    reference_index=reference_start + offset,
                    read_index=read_start + offset,
                )
            )
        reference_pos = reference_start + block_length
        read_pos = read_start + block_length
        while reference_pos < reference_end:
            cells.append(
                AlignmentCell(
                    reference_base=reference[reference_pos],
                    read_base="-",
                    reference_index=reference_pos,
                    read_index=None,
                )
            )
            reference_pos += 1
        while read_pos < read_end:
            cells.append(
                AlignmentCell(
                    reference_base="-",
                    read_base=read[read_pos],
                    reference_index=None,
                    read_index=read_pos,
                )
            )
            read_pos += 1

    if not local:
        while reference_pos < len(reference):
            cells.append(
                AlignmentCell(
                    reference_base=reference[reference_pos],
                    read_base="-",
                    reference_index=reference_pos,
                    read_index=None,
                )
            )
            reference_pos += 1
        while read_pos < len(read):
            cells.append(
                AlignmentCell(
                    reference_base="-",
                    read_base=read[read_pos],
                    reference_index=None,
                    read_index=read_pos,
                )
            )
            read_pos += 1

    return tuple(cells) if cells else None


def _alignment_blocks(blocks: Any) -> list[tuple[int, int]]:
    parsed: list[tuple[int, int]] = []
    for block in blocks:
        if len(block) != 2:
            continue
        parsed.append((int(block[0]), int(block[1])))
    return parsed


def _fallback_alignment(*, reference: str, read: str) -> tuple[AlignmentCell, ...]:
    if len(reference) == len(read):
        return _positional_alignment(reference=reference, read=read)

    if _alignment_matrix_cells(reference=reference, read=read) > ALIGN_MAX_MATRIX_CELLS:
        return _positional_alignment(reference=reference, read=read)

    cells, score = _smith_waterman_alignment(reference=reference, read=read)
    if score > 0 and cells:
        return cells
    return _positional_alignment(reference=reference, read=read)


def _alignment_matrix_cells(*, reference: str, read: str) -> int:
    return (len(reference) + 1) * (len(read) + 1)


def _positional_alignment(*, reference: str, read: str) -> tuple[AlignmentCell, ...]:
    cells: list[AlignmentCell] = []
    for index in range(max(len(reference), len(read))):
        cells.append(
            AlignmentCell(
                reference_base=reference[index] if index < len(reference) else "-",
                read_base=read[index] if index < len(read) else "-",
                reference_index=index if index < len(reference) else None,
                read_index=index if index < len(read) else None,
            )
        )
    return tuple(cells)


def _smith_waterman_alignment(
    *,
    reference: str,
    read: str,
) -> tuple[tuple[AlignmentCell, ...], int]:
    cols = len(read) + 1
    scores = [0] * ((len(reference) + 1) * cols)
    pointers = bytearray((len(reference) + 1) * cols)
    best_score = 0
    best_i = 0
    best_j = 0

    for i in range(1, len(reference) + 1):
        for j in range(1, len(read) + 1):
            index = i * cols + j
            diagonal = scores[index - cols - 1] + _alignment_score(
                reference[i - 1],
                read[j - 1],
            )
            up = scores[index - cols] + ALIGN_GAP_SCORE
            left = scores[index - 1] + ALIGN_GAP_SCORE
            score = 0
            pointer = 0
            if diagonal > score:
                score = diagonal
                pointer = 1
            if up > score:
                score = up
                pointer = 2
            if left > score:
                score = left
                pointer = 3

            scores[index] = score
            pointers[index] = pointer
            if score > best_score:
                best_score = score
                best_i = i
                best_j = j

    cells: list[AlignmentCell] = []
    i = best_i
    j = best_j
    while i > 0 and j > 0:
        index = i * cols + j
        pointer = pointers[index]
        if pointer == 0 or scores[index] == 0:
            break

        if pointer == 1:
            i -= 1
            j -= 1
            cells.append(
                AlignmentCell(
                    reference_base=reference[i],
                    read_base=read[j],
                    reference_index=i,
                    read_index=j,
                )
            )
        elif pointer == 2:
            i -= 1
            cells.append(
                AlignmentCell(
                    reference_base=reference[i],
                    read_base="-",
                    reference_index=i,
                    read_index=None,
                )
            )
        else:
            j -= 1
            cells.append(
                AlignmentCell(
                    reference_base="-",
                    read_base=read[j],
                    reference_index=None,
                    read_index=j,
                )
            )

    cells.reverse()
    return tuple(cells), best_score


def _alignment_score(reference_base: str, read_base: str) -> int:
    return ALIGN_MATCH_SCORE if reference_base == read_base else ALIGN_MISMATCH_SCORE


def _alignment_response(
    cells: tuple[AlignmentCell, ...],
    *,
    target_offset: int,
    trace: ParsedTrace | None,
    read: str,
) -> AlignResponse:
    reference_row = "".join(cell.reference_base for cell in cells)
    read_row = "".join(cell.read_base for cell in cells)
    match_line = "".join(
        (
            "|"
            if (
                cell.reference_base != "-"
                and cell.read_base != "-"
                and cell.reference_base == cell.read_base
            )
            else " "
        )
        for cell in cells
    )
    mismatch_positions = [
        index
        for index, cell in enumerate(cells)
        if cell.reference_base == "-"
        or cell.read_base == "-"
        or cell.reference_base != cell.read_base
    ]
    target_position = next(
        (index for index, cell in enumerate(cells) if cell.reference_index == target_offset),
        -1,
    )
    return AlignResponse(
        reference=reference_row,
        sanger_read=read_row,
        match_line=match_line,
        mismatch_positions=mismatch_positions,
        target_position=target_position,
        trace_channels=_response_trace_channels(trace),
        base_calls=list(trace.base_calls) if trace is not None else list(read),
        q_scores=list(trace.q_scores) if trace is not None else [],
    )


def _response_trace_channels(trace: ParsedTrace | None) -> list[TraceChannel]:
    if trace is None:
        return []
    return [
        TraceChannel(base=channel.base, values=list(channel.values))
        for channel in trace.trace_channels
    ]
