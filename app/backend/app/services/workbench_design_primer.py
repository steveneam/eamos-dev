from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

from fastapi import status

from app.core.config import Settings
from app.schemas.workbench import PrimerPair, PrimerRequest, PrimerResponse
from app.services.sequence_context import SequenceContext, unsupported_input_warning
from app.services.workbench_design_common import (
    HTTP_UNPROCESSABLE_ENTITY,
    PRIMER_SPECIFICITY_TEMPLATE,
    PRIMER_SPECIFICITY_UCSC_ISPCR,
    WORKBENCH_PROVIDER_FAILED_PREFIX,
    WORKBENCH_PROVIDER_MALFORMED,
    WORKBENCH_PROVIDER_UNAVAILABLE,
    WorkbenchDesignError,
    _clean_template,
    _reverse_complement,
)
from app.services.workbench_design_primer_snp import (
    NoopPrimerSnpMaskingProvider,
    PrimerSnpMaskingProvider,
    PrimerSnpMaskingResult,
    target_genomic_locus as _target_genomic_locus,
    template_genomic_coordinate as _template_genomic_coordinate,
    template_is_genomically_reversed as _template_is_genomically_reversed,
)

PRIMER_MAX_TEMPLATE_BASES = 20_000


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


@dataclass(frozen=True)
class PrimerSecondaryStructureAssessment:
    risk: str
    notes: str
    self_any_forward: float | None = None
    self_any_reverse: float | None = None
    self_end_forward: float | None = None
    self_end_reverse: float | None = None
    hairpin_tm_forward: float | None = None
    hairpin_tm_reverse: float | None = None
    pair_compl_end: float | None = None


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
            raise WorkbenchDesignError(
                code=f"{WORKBENCH_PROVIDER_FAILED_PREFIX}:isPcr",
                message="UCSC isPcr specificity check failed.",
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
                message="UCSC isPcr is missing one or more required local assets.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class Primer3PrimerProvider:
    def __init__(
        self,
        primer3_module: ModuleType | None = None,
        specificity_provider: PrimerSpecificityProvider | None = None,
        snp_masking_provider: PrimerSnpMaskingProvider | None = None,
    ) -> None:
        self._primer3_module = primer3_module
        self.specificity_provider = specificity_provider or TemplateAmpliconSpecificityProvider()
        self.snp_masking_provider = snp_masking_provider or NoopPrimerSnpMaskingProvider()

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
        if len(template) > PRIMER_MAX_TEMPLATE_BASES:
            code = unsupported_input_warning("primer_template_length")
            raise WorkbenchDesignError(
                code=code,
                message=(
                    "Primer design exceeds the bounded local template envelope "
                    f"({PRIMER_MAX_TEMPLATE_BASES} bases)."
                ),
                status_code=HTTP_UNPROCESSABLE_ENTITY,
                warnings=[code],
            )
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

        snp_masking = self.snp_masking_provider.prepare(
            payload=payload,
            context=context,
            template=template,
        )
        seq_args: dict[str, object] = {
            "SEQUENCE_ID": f"{context.gene}:{context.cdna}",
            "SEQUENCE_TEMPLATE": template,
            "SEQUENCE_TARGET": [context.target_offset, 1],
        }
        seq_args.update(snp_masking.seq_args())

        try:
            raw_result = primer3.bindings.design_primers(
                seq_args=seq_args,
                global_args=_primer3_global_args(
                    payload,
                    product_min=product_min,
                    product_max=product_max,
                ),
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
                snp_masking=snp_masking,
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
    snp_masking: PrimerSnpMaskingResult,
    product_min: int,
    product_max: int,
) -> list[PrimerPair]:
    returned = int(raw_result.get("PRIMER_PAIR_NUM_RETURNED") or 0)
    pair_rows: list[tuple[dict[str, Any], PrimerSpecificityResult]] = []
    snp_rejected_count = 0
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

        if _primer3_pair_has_3prime_snp_overlap(raw_result, idx, snp_masking=snp_masking):
            snp_rejected_count += 1
            continue

        specificity = specificity_provider.check(
            forward=forward,
            reverse=reverse,
            product_min=product_min,
            product_max=product_max,
            context=context,
        )
        secondary_structure = _primer3_secondary_structure(raw_result, idx)
        placement = _primer3_pair_placement(raw_result, idx, context=context)
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
                    "secondary_structure_risk": secondary_structure.risk,
                    "secondary_structure_notes": secondary_structure.notes,
                    "self_any_forward": secondary_structure.self_any_forward,
                    "self_any_reverse": secondary_structure.self_any_reverse,
                    "self_end_forward": secondary_structure.self_end_forward,
                    "self_end_reverse": secondary_structure.self_end_reverse,
                    "hairpin_tm_forward": secondary_structure.hairpin_tm_forward,
                    "hairpin_tm_reverse": secondary_structure.hairpin_tm_reverse,
                    "pair_compl_end": secondary_structure.pair_compl_end,
                    **placement,
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
                    snp_masking=snp_masking,
                    snp_rejected_count=snp_rejected_count,
                ),
                recommended=idx == recommended_row,
            )
        )
    return pairs


def _primer3_pair_has_3prime_snp_overlap(
    raw_result: dict[str, Any],
    pair_index: int,
    *,
    snp_masking: PrimerSnpMaskingResult,
) -> bool:
    if not snp_masking.active:
        return False
    risk_offsets = snp_masking.risk_offsets()
    if not risk_offsets:
        return False

    left = _primer3_position(raw_result.get(f"PRIMER_LEFT_{pair_index}"))
    if left is not None:
        left_start_zero, left_length = left
        three_prime_start = max(left_start_zero, left_start_zero + left_length - 5)
        three_prime_end = left_start_zero + left_length
        if risk_offsets.intersection(range(three_prime_start, three_prime_end)):
            return True

    right = _primer3_position(raw_result.get(f"PRIMER_RIGHT_{pair_index}"))
    if right is not None:
        right_start_zero, right_length = right
        three_prime_start = max(0, right_start_zero - right_length + 1)
        three_prime_end = min(right_start_zero + 1, three_prime_start + 5)
        if risk_offsets.intersection(range(three_prime_start, three_prime_end)):
            return True

    return False


def _primer3_pair_placement(
    raw_result: dict[str, Any],
    pair_index: int,
    *,
    context: SequenceContext,
) -> dict[str, Any]:
    left = _primer3_position(raw_result.get(f"PRIMER_LEFT_{pair_index}"))
    right = _primer3_position(raw_result.get(f"PRIMER_RIGHT_{pair_index}"))
    if left is None or right is None:
        return {}

    left_start_zero, left_length = left
    right_start_zero, right_length = right
    forward_template_start = left_start_zero + 1
    forward_template_stop = left_start_zero + left_length
    reverse_template_start = right_start_zero + 1
    reverse_template_stop = right_start_zero - right_length + 2
    amplicon_template_start = forward_template_start
    amplicon_template_end = reverse_template_start

    placement: dict[str, Any] = {
        "forward_strand": "Plus",
        "reverse_strand": "Minus",
        "forward_template_start": forward_template_start,
        "forward_template_stop": forward_template_stop,
        "reverse_template_start": reverse_template_start,
        "reverse_template_stop": reverse_template_stop,
        "amplicon_template_start": amplicon_template_start,
        "amplicon_template_end": amplicon_template_end,
    }

    chrom, target_pos = _target_genomic_locus(context)
    if chrom is None or target_pos is None:
        return placement

    def genomic_pos(template_pos: int) -> int | None:
        return _template_genomic_coordinate(context, template_pos - 1)

    template_reversed = _template_is_genomically_reversed(context)
    forward_genomic_start = genomic_pos(forward_template_start)
    forward_genomic_stop = genomic_pos(forward_template_stop)
    reverse_genomic_start = genomic_pos(reverse_template_start)
    reverse_genomic_stop = genomic_pos(reverse_template_stop)
    amplicon_start = genomic_pos(amplicon_template_start)
    amplicon_end = genomic_pos(amplicon_template_end)
    genomic_positions = (
        forward_genomic_start,
        forward_genomic_stop,
        reverse_genomic_start,
        reverse_genomic_stop,
        amplicon_start,
        amplicon_end,
    )
    if any(position is None for position in genomic_positions):
        return placement

    placement.update(
        {
            "forward_strand": "Minus" if template_reversed else "Plus",
            "reverse_strand": "Plus" if template_reversed else "Minus",
            "genomic_chromosome": chrom,
            "genome_build": context.genome_build,
            "forward_genomic_start": forward_genomic_start,
            "forward_genomic_stop": forward_genomic_stop,
            "reverse_genomic_start": reverse_genomic_start,
            "reverse_genomic_stop": reverse_genomic_stop,
            "amplicon_genomic_start": min(amplicon_start, amplicon_end),
            "amplicon_genomic_end": max(amplicon_start, amplicon_end),
        }
    )
    return placement


def _primer3_position(value: Any) -> tuple[int, int] | None:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        start, length = value[0], value[1]
    elif isinstance(value, str):
        match = re.fullmatch(r"\s*(?P<start>\d+)\s*,\s*(?P<length>\d+)\s*", value)
        if match is None:
            return None
        start = match.group("start")
        length = match.group("length")
    else:
        return None

    try:
        start_int = int(start)
        length_int = int(length)
    except (TypeError, ValueError):
        return None
    if start_int < 0 or length_int <= 0:
        return None
    return start_int, length_int


def _primer3_secondary_structure(
    raw_result: dict[str, Any],
    pair_index: int,
) -> PrimerSecondaryStructureAssessment:
    metric_keys = {
        "self_any_forward": (
            "forward self-any",
            f"PRIMER_LEFT_{pair_index}_SELF_ANY_TH",
        ),
        "self_end_forward": (
            "forward self-end",
            f"PRIMER_LEFT_{pair_index}_SELF_END_TH",
        ),
        "hairpin_tm_forward": (
            "forward hairpin",
            f"PRIMER_LEFT_{pair_index}_HAIRPIN_TH",
        ),
        "self_any_reverse": (
            "reverse self-any",
            f"PRIMER_RIGHT_{pair_index}_SELF_ANY_TH",
        ),
        "self_end_reverse": (
            "reverse self-end",
            f"PRIMER_RIGHT_{pair_index}_SELF_END_TH",
        ),
        "hairpin_tm_reverse": (
            "reverse hairpin",
            f"PRIMER_RIGHT_{pair_index}_HAIRPIN_TH",
        ),
        "pair_compl_any": (
            "pair complement-any",
            f"PRIMER_PAIR_{pair_index}_COMPL_ANY_TH",
        ),
        "pair_compl_end": (
            "pair complement-end",
            f"PRIMER_PAIR_{pair_index}_COMPL_END_TH",
        ),
    }
    metrics: dict[str, tuple[str, float]] = {}
    for field_name, (label, key) in metric_keys.items():
        value = raw_result.get(key)
        if value in (None, ""):
            continue
        try:
            metrics[field_name] = (label, float(value))
        except (TypeError, ValueError):
            continue

    if not metrics:
        return PrimerSecondaryStructureAssessment(
            risk="not_assessed",
            notes="Primer3 secondary-structure metrics were not returned.",
        )

    worst_label, worst_value = max(metrics.values(), key=lambda item: item[1])
    if worst_value >= 47.0:
        risk = "high"
    elif worst_value >= 35.0:
        risk = "moderate"
    else:
        risk = "low"
    exposed_metrics = {
        key: round(value, 1) for key, (_label, value) in metrics.items() if key != "pair_compl_any"
    }
    return PrimerSecondaryStructureAssessment(
        risk=risk,
        notes=(
            "Primer3 thermodynamic secondary-structure screen "
            f"{risk}; max {worst_label} {worst_value:.1f}."
        ),
        **exposed_metrics,
    )


def _primer3_notes(
    *,
    payload: PrimerRequest,
    context: SequenceContext,
    specificity: PrimerSpecificityResult,
    snp_masking: PrimerSnpMaskingResult,
    snp_rejected_count: int,
) -> str:
    notes = [
        "Primer3 local design.",
        specificity.note,
        f"Template: {context.genome_build} {context.genomic_hg38 or context.transcript_hgvs}.",
    ]
    snp_note = snp_masking.note(rejected_pair_count=snp_rejected_count)
    if snp_note:
        notes.append(snp_note)
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


def _primer3_global_args(
    payload: PrimerRequest,
    *,
    product_min: int,
    product_max: int,
) -> dict[str, object]:
    """Exact versioned Sanger/qPCR constraint profiles passed to Primer3."""

    args: dict[str, object] = {
        "PRIMER_TASK": "generic",
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
        "PRIMER_THERMODYNAMIC_OLIGO_ALIGNMENT": 1,
        "PRIMER_PRODUCT_SIZE_RANGE": [[product_min, product_max]],
    }
    if payload.mode == "sanger":
        args.update(
            {
                "PRIMER_MAX_POLY_X": 5,
                "PRIMER_GC_CLAMP": 0,
            }
        )
    elif payload.mode == "qpcr":
        args.update(
            {
                "PRIMER_MAX_POLY_X": 4,
                "PRIMER_GC_CLAMP": 1,
                "PRIMER_MAX_END_GC": 3,
            }
        )
    return args
