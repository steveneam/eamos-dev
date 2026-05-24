from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, TypeVar

from fastapi import status
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.schemas.workbench import (
    AlignRequest,
    AlignResponse,
    CrisprRequest,
    CrisprResponse,
    PrimerPair,
    PrimerRequest,
    PrimerResponse,
    TraceChannel,
)
from app.services.crispr_design import (
    CRISPR_PROVIDER_CRISPRSCORE_R,
    CRISPR_PROVIDER_LOCAL_DETERMINISTIC,
    CrisprDesignInputError,
    CrisprScoreRAdapter,
    CrisprScoreRBackedCrisprProvider,
    LocalDeterministicCrisprProvider,
)
from app.services.sequence_context import (
    WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE,
    SequenceContext,
    SequenceContextResult,
    SequenceContextService,
    unsupported_input_warning,
)
from app.services.trace_parser import (
    TRACE_INVALID_BASE64,
    TRACE_PARSER_UNAVAILABLE,
    ParsedTrace,
    TraceParseError,
    parse_ab1_base64,
)

WORKBENCH_PROVIDER_FAILED_PREFIX = "workbench_provider_failed"
WORKBENCH_PROVIDER_MALFORMED = "workbench_provider_malformed"
WORKBENCH_PROVIDER_UNAVAILABLE = "workbench_provider_unavailable"
WORKBENCH_SERVICE_UNAVAILABLE = "workbench_service_unavailable"
HTTP_UNPROCESSABLE_ENTITY = 422
PRIMER_SPECIFICITY_TEMPLATE = "template"
PRIMER_SPECIFICITY_UCSC_ISPCR = "ucsc_ispcr"
ALIGN_MAX_SEQUENCE_BASES = 5000
ALIGN_MAX_MATRIX_CELLS = 4_000_000
ALIGN_MATCH_SCORE = 2
ALIGN_MISMATCH_SCORE = -1
ALIGN_GAP_SCORE = -2
WorkbenchModel = TypeVar("WorkbenchModel", bound=BaseModel)


class WorkbenchDesignError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
        warnings: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.warnings = warnings if warnings is not None else [code]

    def to_http_detail(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "warnings": self.warnings,
        }


class WorkbenchFixtureProvider:
    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self.fixtures_dir = fixtures_dir or (
            Path(__file__).resolve().parents[1] / "fixtures" / "workbench"
        )

    def primers(self, _payload: PrimerRequest) -> PrimerResponse:
        return self._validate_fixture("primer_rpe65.json", PrimerResponse)

    def crispr(self, _payload: CrisprRequest) -> CrisprResponse:
        return self._validate_fixture("crispr_rpe65.json", CrisprResponse)

    def align(self, _payload: AlignRequest) -> AlignResponse:
        return self._validate_fixture("align_rpe65.json", AlignResponse)

    def _validate_fixture(
        self,
        name: str,
        model: type[WorkbenchModel],
    ) -> WorkbenchModel:
        try:
            return model(**self._load(name))
        except ValidationError as exc:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_MALFORMED,
                message=f"Workbench fixture is malformed: {name}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc

    def _load(self, name: str) -> dict[str, Any]:
        try:
            return json.loads((self.fixtures_dir / name).read_text(encoding="utf-8"))
        except OSError as exc:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_UNAVAILABLE,
                message=f"Workbench fixture is unavailable: {name}",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        except ValueError as exc:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_MALFORMED,
                message=f"Workbench fixture is malformed: {name}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc


class PrimerDesignProvider(Protocol):
    def design(self, payload: PrimerRequest, context: SequenceContext) -> PrimerResponse: ...


class CrisprDesignProvider(Protocol):
    def design(self, payload: CrisprRequest, context: SequenceContext) -> CrisprResponse: ...


class AlignProvider(Protocol):
    def align(self, payload: AlignRequest, context: SequenceContext) -> AlignResponse: ...


@dataclass(frozen=True)
class AlignmentCell:
    reference_base: str
    read_base: str
    reference_index: int | None
    read_index: int | None


@dataclass(frozen=True)
class PrimerAmplicon:
    start: int
    end: int
    size: int
    spans_target: bool


@dataclass(frozen=True)
class IsPcrProduct:
    chrom: str | None
    start: int | None
    end: int | None
    strand: str | None
    size: int
    spans_target: bool


@dataclass(frozen=True)
class PrimerSpecificityResult:
    hits: int
    intended_hits: int
    product_sizes: tuple[int, ...]
    note: str

    @property
    def supports_recommendation(self) -> bool:
        return self.hits == 1 and self.intended_hits == 1


class PrimerSpecificityProvider(Protocol):
    def check(
        self,
        *,
        forward: str,
        reverse: str,
        product_min: int,
        product_max: int,
        context: SequenceContext,
    ) -> PrimerSpecificityResult: ...


class TemplateAmpliconSpecificityProvider:
    """Exact primer-pair screen against the resolved design template."""

    def check(
        self,
        *,
        forward: str,
        reverse: str,
        product_min: int,
        product_max: int,
        context: SequenceContext,
    ) -> PrimerSpecificityResult:
        template = _clean_template(context.window_sequence)
        forward_template = _clean_template(forward)
        reverse_template = _reverse_complement(_clean_template(reverse))
        amplicons = _template_amplicons(
            template=template,
            forward=forward_template,
            reverse_template=reverse_template,
            product_min=product_min,
            product_max=product_max,
            target_offset=context.target_offset,
        )
        intended_hits = sum(1 for amplicon in amplicons if amplicon.spans_target)
        product_sizes = tuple(sorted(amplicon.size for amplicon in amplicons))
        return PrimerSpecificityResult(
            hits=len(amplicons),
            intended_hits=intended_hits,
            product_sizes=product_sizes,
            note=_template_specificity_note(
                hit_count=len(amplicons),
                intended_hits=intended_hits,
                product_sizes=product_sizes,
            ),
        )


class LocalIsPcrSpecificityProvider:
    """Whole-genome primer-pair screen using UCSC standalone isPcr."""

    def __init__(
        self,
        settings: Settings,
        *,
        binary_path: Path | None = None,
        genome_path: Path | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.settings = settings
        self.binary_path = _settings_path(
            settings,
            binary_path if binary_path is not None else settings.ucsc_ispcr_binary_path,
        )
        self.genome_path = _settings_path(
            settings,
            genome_path if genome_path is not None else settings.ucsc_ispcr_hg38_path,
        )
        self.timeout_seconds = settings.ucsc_ispcr_timeout_seconds
        self.min_perfect = settings.ucsc_ispcr_min_perfect
        self.min_good = settings.ucsc_ispcr_min_good
        self.runner = runner

    def check(
        self,
        *,
        forward: str,
        reverse: str,
        product_min: int,
        product_max: int,
        context: SequenceContext,
    ) -> PrimerSpecificityResult:
        self._validate_context(context)
        self._validate_assets()

        command = [
            str(self.binary_path),
            f"-minSize={product_min}",
            f"-maxSize={product_max}",
            f"-minPerfect={self.min_perfect}",
            f"-minGood={self.min_good}",
            str(self.genome_path),
            "stdin",
            "stdout",
        ]
        query = f"{context.gene}_{context.cdna}\t{forward}\t{reverse}\n"
        try:
            completed = self.runner(
                command,
                input=query,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:TimeoutExpired",
                message="UCSC isPcr specificity check timed out.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        except OSError as exc:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_UNAVAILABLE,
                message="UCSC isPcr provider could not be executed.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            message = "UCSC isPcr specificity check failed."
            if stderr:
                message = f"{message} {stderr[:240]}"
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:isPcr",
                message=message,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        target_chrom, target_pos = _target_genomic_locus(context)
        products = _parse_ispcr_products(
            completed.stdout or "",
            target_chrom=target_chrom,
            target_pos=target_pos,
        )
        intended_hits = sum(1 for product in products if product.spans_target)
        product_sizes = tuple(sorted(product.size for product in products))
        return PrimerSpecificityResult(
            hits=len(products),
            intended_hits=intended_hits,
            product_sizes=product_sizes,
            note=_ispcr_specificity_note(
                hit_count=len(products),
                intended_hits=intended_hits,
                product_sizes=product_sizes,
                has_target_locus=target_chrom is not None and target_pos is not None,
            ),
        )

    def _validate_context(self, context: SequenceContext) -> None:
        if context.species != "human":
            code = unsupported_input_warning("species")
            raise WorkbenchDesignError(
                code=code,
                message="UCSC isPcr specificity is currently configured for human genomes only.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=[code],
            )
        if context.genome_build not in {"GRCh38", "hg38"}:
            code = unsupported_input_warning("genome_build")
            raise WorkbenchDesignError(
                code=code,
                message="UCSC isPcr specificity is currently configured for hg38/GRCh38 only.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=[code],
            )

    def _validate_assets(self) -> None:
        missing = [str(path) for path in (self.binary_path, self.genome_path) if not path.is_file()]
        if missing:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_UNAVAILABLE,
                message=(
                    "UCSC isPcr specificity provider is not configured. "
                    f"Missing local asset(s): {', '.join(missing)}."
                ),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class Primer3PrimerProvider:
    def __init__(
        self,
        primer3_module: ModuleType | None = None,
        specificity_provider: PrimerSpecificityProvider | None = None,
    ) -> None:
        self._primer3_module = primer3_module
        self.specificity_provider = specificity_provider or TemplateAmpliconSpecificityProvider()

    def design(self, payload: PrimerRequest, context: SequenceContext) -> PrimerResponse:
        if payload.mode == "arms":
            code = unsupported_input_warning("primer_mode_arms")
            raise WorkbenchDesignError(
                code=code,
                message="Real-mode ARMS primer design is not implemented yet.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=[code],
            )

        primer3 = self._primer3()
        template = _clean_template(context.window_sequence)
        if context.target_offset < 0 or context.target_offset >= len(template):
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_MALFORMED,
                message="Sequence context target offset is outside the design template.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        product_min = max(1, payload.product_size_min)
        product_max = max(product_min, payload.product_size_max)
        if len(template) < product_min:
            return PrimerResponse(mode=payload.mode, pairs=[])

        try:
            raw_result = primer3.bindings.design_primers(
                seq_args={
                    "SEQUENCE_ID": f"{context.gene}:{context.cdna}",
                    "SEQUENCE_TEMPLATE": template,
                    "SEQUENCE_TARGET": [context.target_offset, 1],
                },
                global_args={
                    "PRIMER_NUM_RETURN": 3,
                    "PRIMER_OPT_SIZE": 20,
                    "PRIMER_MIN_SIZE": 18,
                    "PRIMER_MAX_SIZE": 25,
                    "PRIMER_MIN_TM": payload.tm_min,
                    "PRIMER_OPT_TM": (payload.tm_min + payload.tm_max) / 2,
                    "PRIMER_MAX_TM": payload.tm_max,
                    "PRIMER_MIN_GC": 35.0,
                    "PRIMER_MAX_GC": 70.0,
                    "PRIMER_MAX_NS_ACCEPTED": 0,
                    "PRIMER_PRODUCT_SIZE_RANGE": [[product_min, product_max]],
                },
            )
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Primer3 failed to design primers for the requested context.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        return PrimerResponse(
            mode=payload.mode,
            pairs=_primer3_pairs(
                raw_result,
                payload=payload,
                context=context,
                specificity_provider=self.specificity_provider,
                product_min=product_min,
                product_max=product_max,
            ),
        )

    def _primer3(self):
        if self._primer3_module is not None:
            return self._primer3_module
        try:
            return import_module("primer3")
        except ModuleNotFoundError as exc:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_UNAVAILABLE,
                message=(
                    "Primer3 provider is unavailable. Install primer3-py to enable "
                    "real-mode primer design."
                ),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc


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


def _clean_template(sequence: str) -> str:
    return re.sub(r"[^ACGTN]", "N", sequence.upper())


_COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


def _reverse_complement(sequence: str) -> str:
    return sequence.translate(_COMPLEMENT)[::-1]


def _alignment_read(payload: AlignRequest) -> tuple[str, ParsedTrace | None]:
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
        if exc.code == TRACE_PARSER_UNAVAILABLE:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_UNAVAILABLE,
                message=exc.message,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                warnings=[WORKBENCH_PROVIDER_UNAVAILABLE, exc.code],
            ) from exc

        kind = "ab1_blob_base64" if exc.code == TRACE_INVALID_BASE64 else "ab1"
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

    if (len(reference) + 1) * (len(read) + 1) > ALIGN_MAX_MATRIX_CELLS:
        return _positional_alignment(reference=reference, read=read)

    cells, score = _smith_waterman_alignment(reference=reference, read=read)
    if score > 0 and cells:
        return cells
    return _positional_alignment(reference=reference, read=read)


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


def _find_subsequence_positions(template: str, query: str) -> list[int]:
    if not query:
        return []
    positions: list[int] = []
    start = template.find(query)
    while start != -1:
        positions.append(start)
        start = template.find(query, start + 1)
    return positions


def _template_amplicons(
    *,
    template: str,
    forward: str,
    reverse_template: str,
    product_min: int,
    product_max: int,
    target_offset: int,
) -> list[PrimerAmplicon]:
    amplicons: list[PrimerAmplicon] = []
    forward_positions = _find_subsequence_positions(template, forward)
    reverse_positions = _find_subsequence_positions(template, reverse_template)
    for forward_start in forward_positions:
        for reverse_start in reverse_positions:
            if reverse_start <= forward_start:
                continue
            end = reverse_start + len(reverse_template)
            size = end - forward_start
            if product_min <= size <= product_max:
                amplicons.append(
                    PrimerAmplicon(
                        start=forward_start,
                        end=end,
                        size=size,
                        spans_target=forward_start <= target_offset < end,
                    )
                )
    return amplicons


def _product_sizes_note(product_sizes: tuple[int, ...]) -> str:
    unique_sizes = tuple(dict.fromkeys(product_sizes))
    if not unique_sizes:
        return "none"
    if len(unique_sizes) <= 3:
        return ", ".join(f"{size} bp" for size in unique_sizes)
    head = ", ".join(f"{size} bp" for size in unique_sizes[:3])
    return f"{head}, +{len(unique_sizes) - 3} more"


def _template_specificity_note(
    *,
    hit_count: int,
    intended_hits: int,
    product_sizes: tuple[int, ...],
) -> str:
    genome_caveat = "This is not a genome-wide Primer-BLAST/UCSC specificity check."
    if hit_count == 0:
        return f"Exact in-template PCR screen found no product. {genome_caveat}"
    size_note = _product_sizes_note(product_sizes)
    if hit_count == 1 and intended_hits == 1:
        return (
            f"Exact in-template PCR screen found 1 product ({size_note}) "
            f"spanning the queried base. {genome_caveat}"
        )
    if intended_hits:
        return (
            f"Exact in-template PCR screen found {hit_count} products ({size_note}); "
            f"{intended_hits} span the queried base. {genome_caveat}"
        )
    return (
        f"Exact in-template PCR screen found {hit_count} products ({size_note}), "
        f"none spanning the queried base. {genome_caveat}"
    )


def _settings_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _target_genomic_locus(context: SequenceContext) -> tuple[str | None, int | None]:
    if not context.genomic_hg38:
        return None, None
    parts = context.genomic_hg38.split("-")
    if len(parts) < 2 or not parts[1].isdigit():
        return None, None
    chrom = parts[0]
    if not chrom.startswith("chr"):
        chrom = f"chr{chrom}"
    return chrom, int(parts[1])


def _fasta_records(output: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header: str | None = None
    sequence_parts: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(sequence_parts)))
            header = line[1:].strip()
            sequence_parts = []
            continue
        if header is not None:
            sequence_parts.append(re.sub(r"[^ACGTNacgtn]", "", line).upper())
    if header is not None:
        records.append((header, "".join(sequence_parts)))
    return records


_UCSC_PCR_HEADER_RE = re.compile(
    r"\b(?P<chrom>chr[^\s:]+):(?P<start>\d+)(?P<strand>[+-])(?P<end>\d+)\b"
)


def _parse_ispcr_products(
    output: str,
    *,
    target_chrom: str | None,
    target_pos: int | None,
) -> tuple[IsPcrProduct, ...]:
    products: list[IsPcrProduct] = []
    for header, sequence in _fasta_records(output):
        match = _UCSC_PCR_HEADER_RE.search(header)
        chrom: str | None = None
        start: int | None = None
        end: int | None = None
        strand: str | None = None
        spans_target = False
        if match:
            chrom = match.group("chrom")
            start = int(match.group("start"))
            end = int(match.group("end"))
            strand = match.group("strand")
            lower = min(start, end)
            upper = max(start, end)
            spans_target = (
                target_chrom is not None
                and target_pos is not None
                and chrom == target_chrom
                and lower <= target_pos <= upper
            )
        size = len(sequence)
        if not size and start is not None and end is not None:
            size = abs(end - start) + 1
        products.append(
            IsPcrProduct(
                chrom=chrom,
                start=start,
                end=end,
                strand=strand,
                size=size,
                spans_target=spans_target,
            )
        )
    return tuple(products)


def _ispcr_specificity_note(
    *,
    hit_count: int,
    intended_hits: int,
    product_sizes: tuple[int, ...],
    has_target_locus: bool,
) -> str:
    provider_note = "UCSC isPcr whole-genome hg38 specificity screen."
    primer_blast_note = "This is not an NCBI Primer-BLAST validation."
    if hit_count == 0:
        return (
            f"{provider_note} Found no product; validate primer orientation and "
            f"local genome assets before accepting the pair. {primer_blast_note}"
        )
    size_note = _product_sizes_note(product_sizes)
    if hit_count == 1 and intended_hits == 1:
        return (
            f"{provider_note} Found 1 product ({size_note}) spanning the queried "
            f"base. {primer_blast_note}"
        )
    if intended_hits:
        return (
            f"{provider_note} Found {hit_count} products ({size_note}); "
            f"{intended_hits} span the queried base. {primer_blast_note}"
        )
    if has_target_locus:
        return (
            f"{provider_note} Found {hit_count} products ({size_note}), none "
            f"spanning the queried base. {primer_blast_note}"
        )
    return (
        f"{provider_note} Found {hit_count} products ({size_note}); target-locus "
        f"mapping was unavailable. {primer_blast_note}"
    )


def _primer3_pairs(
    raw_result: dict[str, Any],
    *,
    payload: PrimerRequest,
    context: SequenceContext,
    specificity_provider: PrimerSpecificityProvider,
    product_min: int,
    product_max: int,
) -> list[PrimerPair]:
    returned = int(raw_result.get("PRIMER_PAIR_NUM_RETURNED") or 0)
    pair_rows: list[tuple[dict[str, Any], PrimerSpecificityResult]] = []
    for idx in range(returned):
        try:
            forward = str(raw_result[f"PRIMER_LEFT_{idx}_SEQUENCE"])
            reverse = str(raw_result[f"PRIMER_RIGHT_{idx}_SEQUENCE"])
            tm_forward = float(raw_result[f"PRIMER_LEFT_{idx}_TM"])
            tm_reverse = float(raw_result[f"PRIMER_RIGHT_{idx}_TM"])
            gc_forward = float(raw_result[f"PRIMER_LEFT_{idx}_GC_PERCENT"])
            gc_reverse = float(raw_result[f"PRIMER_RIGHT_{idx}_GC_PERCENT"])
            product_size = int(raw_result[f"PRIMER_PAIR_{idx}_PRODUCT_SIZE"])
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkbenchDesignError(
                code=WORKBENCH_PROVIDER_MALFORMED,
                message="Primer3 returned an incomplete primer pair.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc

        specificity = specificity_provider.check(
            forward=forward,
            reverse=reverse,
            product_min=product_min,
            product_max=product_max,
            context=context,
        )
        pair_rows.append(
            (
                {
                    "index": idx + 1,
                    "forward": forward,
                    "reverse": reverse,
                    "tm_forward": round(tm_forward, 1),
                    "tm_reverse": round(tm_reverse, 1),
                    "gc_forward": round(gc_forward, 1),
                    "gc_reverse": round(gc_reverse, 1),
                    "product_size": product_size,
                },
                specificity,
            )
        )

    recommended_row = next(
        (
            idx
            for idx, (_pair, specificity) in enumerate(pair_rows)
            if specificity.supports_recommendation
        ),
        0 if pair_rows else None,
    )
    pairs: list[PrimerPair] = []
    for idx, (pair, specificity) in enumerate(pair_rows):
        pairs.append(
            PrimerPair(
                **pair,
                specificity_hits=specificity.hits,
                notes=_primer3_notes(
                    payload=payload,
                    context=context,
                    specificity=specificity,
                ),
                recommended=idx == recommended_row,
            )
        )
    return pairs


def _primer3_notes(
    *,
    payload: PrimerRequest,
    context: SequenceContext,
    specificity: PrimerSpecificityResult,
) -> str:
    notes = [
        "Primer3 local design.",
        specificity.note,
        f"Template: {context.genome_build} {context.genomic_hg38 or context.transcript_hgvs}.",
    ]
    if payload.avoid_snps:
        notes.append("SNP masking was requested but is not yet applied.")
    return " ".join(notes)


def _default_specificity_provider(settings: Settings | None) -> PrimerSpecificityProvider:
    provider_name = (
        (
            settings.primer_specificity_provider
            if settings is not None
            else PRIMER_SPECIFICITY_TEMPLATE
        )
        .strip()
        .lower()
    )
    if provider_name == PRIMER_SPECIFICITY_TEMPLATE:
        return TemplateAmpliconSpecificityProvider()
    if provider_name == PRIMER_SPECIFICITY_UCSC_ISPCR:
        if settings is None:
            raise ValueError("UCSC isPcr specificity requires backend settings.")
        return LocalIsPcrSpecificityProvider(settings)
    raise ValueError(f"Unknown primer specificity provider: {provider_name}")


def _default_crispr_provider(settings: Settings | None) -> CrisprDesignProvider:
    provider_name = (
        (settings.crispr_provider if settings is not None else CRISPR_PROVIDER_LOCAL_DETERMINISTIC)
        .strip()
        .lower()
    )
    if provider_name == CRISPR_PROVIDER_LOCAL_DETERMINISTIC:
        return LocalDeterministicCrisprProvider()
    if provider_name == CRISPR_PROVIDER_CRISPRSCORE_R:
        adapter_kwargs = {}
        if settings is not None:
            adapter_kwargs = {
                "rscript_path": settings.crispr_rscript_path,
                "rule_set3_conda_env": settings.crispr_ruleset3_conda_env,
                "lindel_conda_env": settings.crispr_lindel_conda_env,
            }
        return CrisprScoreRBackedCrisprProvider(
            scoring_adapter=CrisprScoreRAdapter(**adapter_kwargs)
        )
    raise ValueError(f"Unknown CRISPR provider: {provider_name}")


class WorkbenchDesignService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        fixture_provider: WorkbenchFixtureProvider | None = None,
        sequence_context_service: SequenceContextService | None = None,
        primer_provider: PrimerDesignProvider | None = None,
        crispr_provider: CrisprDesignProvider | None = None,
        align_provider: AlignProvider | None = None,
    ) -> None:
        self.settings = settings
        self.fixture_provider = fixture_provider or WorkbenchFixtureProvider()
        self.sequence_context_service = sequence_context_service or SequenceContextService(
            settings=settings
        )
        self.primer_provider = primer_provider or Primer3PrimerProvider(
            specificity_provider=_default_specificity_provider(settings)
        )
        self.crispr_provider = crispr_provider or _default_crispr_provider(settings)
        self.align_provider = align_provider or LocalSangerAlignmentProvider()

    def design_primers(self, payload: PrimerRequest) -> PrimerResponse:
        if self.settings is not None and self.settings.use_real_apis:
            return self._design_real_primers(payload)
        return self.fixture_provider.primers(payload)

    def design_guides(self, payload: CrisprRequest) -> CrisprResponse:
        if self.settings is not None and self.settings.use_real_apis:
            return self._design_real_guides(payload)
        return self.fixture_provider.crispr(payload)

    def align(self, payload: AlignRequest) -> AlignResponse:
        if self.settings is not None and self.settings.use_real_apis:
            return self._align_real(payload)
        return self.fixture_provider.align(payload)

    def _design_real_primers(self, payload: PrimerRequest) -> PrimerResponse:
        try:
            sequence_result = self.sequence_context_service.resolve(
                gene=payload.gene,
                cdna=payload.cdna,
            )
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sequence context provider failed while preparing primer design.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        context = self._sequence_context_or_error(sequence_result)
        return self.primer_provider.design(payload, context)

    def _design_real_guides(self, payload: CrisprRequest) -> CrisprResponse:
        try:
            sequence_result = self.sequence_context_service.resolve(
                gene=payload.gene,
                cdna=payload.cdna,
            )
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sequence context provider failed while preparing CRISPR design.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        context = self._sequence_context_or_error(sequence_result, purpose="CRISPR design")
        try:
            return self.crispr_provider.design(payload, context)
        except CrisprDesignInputError as exc:
            raise WorkbenchDesignError(
                code=exc.code,
                message=exc.message,
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=exc.warnings,
            ) from exc
        except WorkbenchDesignError:
            raise
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="CRISPR provider failed to design guides for the requested context.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def _align_real(self, payload: AlignRequest) -> AlignResponse:
        try:
            sequence_result = self.sequence_context_service.resolve(
                gene=payload.gene,
                cdna=payload.cdna,
            )
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sequence context provider failed while preparing Sanger alignment.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        context = self._sequence_context_or_error(sequence_result, purpose="Sanger alignment")
        try:
            return self.align_provider.align(payload, context)
        except WorkbenchDesignError:
            raise
        except Exception as exc:
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Sanger alignment provider failed for the requested context.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

    def _sequence_context_or_error(
        self,
        result: SequenceContextResult,
        *,
        purpose: str = "primer design",
    ) -> SequenceContext:
        if result.context is not None:
            return result.context

        code = result.warnings[0] if result.warnings else WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE
        raise WorkbenchDesignError(
            code=code,
            message=f"Workbench sequence context is unavailable for real-mode {purpose}.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=result.warnings or [code],
        )
