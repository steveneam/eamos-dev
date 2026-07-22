from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher

from app.services.trace_parser import ParsedTrace

CRISPR_TIDE_INVALID_INPUT = "crispr_tide_invalid_input"
CRISPR_TIDE_LENGTH_MISMATCH = "crispr_tide_read_length_mismatch"
CRISPR_TIDE_CONSENSUS_ONLY = "crispr_tide_consensus_only"
CRISPR_TIDE_NO_INDEL_SHIFT = "crispr_tide_no_indel_shift_detected"
CRISPR_TIDE_LOW_QUALITY = "crispr_tide_low_quality_window"
CRISPR_TRACE_COMPARISON_PROVIDER_LABEL = "Eamos descriptive consensus trace comparison"

_ALIGN_UPSTREAM_BP = 30
_DECOMPOSE_DOWNSTREAM_BP = 140
_LOW_QUALITY_PHRED = 20.0


class CrisprTideInputError(Exception):
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
class DescriptiveTraceDifference:
    size: int
    observed_fraction: float


@dataclass(frozen=True)
class DescriptiveTraceComparison:
    analysis_kind: str
    provider_label: str
    cut_site_index: int
    comparison_window_start: int
    comparison_window_end: int
    consensus_difference_fraction: float
    sequence_identity: float
    differences: tuple[DescriptiveTraceDifference, ...]
    warnings: tuple[str, ...]
    notes: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def analyze_descriptive_trace_comparison(
    *,
    control_trace: ParsedTrace,
    edited_trace: ParsedTrace,
    cut_site_index: int,
) -> DescriptiveTraceComparison:
    """Compare two called consensus strings without claiming TIDE decomposition."""

    cut_zero = cut_site_index - 1
    control_sequence = control_trace.sequence.upper()
    edited_sequence = edited_trace.sequence.upper()
    shortest = min(len(control_sequence), len(edited_sequence))
    if cut_zero < 0 or cut_zero >= shortest:
        raise CrisprTideInputError(
            code=CRISPR_TIDE_INVALID_INPUT,
            message=(
                "Cut site index must be within both parsed trace consensus "
                f"sequences (1-{shortest})."
            ),
        )

    warnings = [CRISPR_TIDE_CONSENSUS_ONLY]
    if len(control_sequence) != len(edited_sequence):
        warnings.append(CRISPR_TIDE_LENGTH_MISMATCH)

    quality_warning = _quality_warning(control_trace, edited_trace, cut_zero)
    if quality_warning is not None:
        warnings.append(quality_warning)

    control_window, edited_window = _analysis_windows(
        control_sequence=control_sequence,
        edited_sequence=edited_sequence,
        cut_zero=cut_zero,
    )
    event_weights, mismatch_bases = _consensus_indel_events(control_window, edited_window)

    if not event_weights:
        if control_window != edited_window:
            warnings.append(CRISPR_TIDE_NO_INDEL_SHIFT)
        return DescriptiveTraceComparison(
            analysis_kind="descriptive_trace_comparison",
            provider_label=CRISPR_TRACE_COMPARISON_PROVIDER_LABEL,
            cut_site_index=cut_site_index,
            comparison_window_start=max(1, cut_site_index - _ALIGN_UPSTREAM_BP),
            comparison_window_end=max(1, cut_site_index - _ALIGN_UPSTREAM_BP)
            + max(len(control_window), len(edited_window))
            - 1,
            consensus_difference_fraction=round(
                mismatch_bases / max(len(control_window), len(edited_window), 1), 4
            ),
            sequence_identity=_sequence_identity(
                window_length=max(len(control_window), len(edited_window)),
                mismatch_bases=mismatch_bases,
            ),
            differences=(),
            notes=_notes(),
            warnings=tuple(warnings),
        )

    total_weight = sum(event_weights.values())
    window_length = max(len(control_window), len(edited_window), 1)
    nonzero_mass = min(0.95, max(0.05, (total_weight + mismatch_bases) / window_length))
    differences: list[DescriptiveTraceDifference] = []
    for size in sorted(event_weights):
        observed = nonzero_mass * (event_weights[size] / total_weight)
        differences.append(
            DescriptiveTraceDifference(
                size=size,
                observed_fraction=round(observed, 4),
            )
        )

    return DescriptiveTraceComparison(
        analysis_kind="descriptive_trace_comparison",
        provider_label=CRISPR_TRACE_COMPARISON_PROVIDER_LABEL,
        cut_site_index=cut_site_index,
        comparison_window_start=max(1, cut_site_index - _ALIGN_UPSTREAM_BP),
        comparison_window_end=max(1, cut_site_index - _ALIGN_UPSTREAM_BP) + window_length - 1,
        consensus_difference_fraction=round((total_weight + mismatch_bases) / window_length, 4),
        sequence_identity=_sequence_identity(
            window_length=window_length,
            mismatch_bases=mismatch_bases + total_weight,
        ),
        differences=tuple(sorted(differences, key=lambda item: item.size)),
        notes=_notes(),
        warnings=tuple(warnings),
    )


def _analysis_windows(
    *,
    control_sequence: str,
    edited_sequence: str,
    cut_zero: int,
) -> tuple[str, str]:
    left = max(0, cut_zero - _ALIGN_UPSTREAM_BP)
    right = min(
        len(control_sequence),
        len(edited_sequence),
        cut_zero + _DECOMPOSE_DOWNSTREAM_BP,
    )
    return control_sequence[left:right], edited_sequence[left:right]


def _consensus_indel_events(
    control_window: str,
    edited_window: str,
) -> tuple[dict[int, int], int]:
    matcher = SequenceMatcher(a=control_window, b=edited_window, autojunk=False)
    event_weights: dict[int, int] = {}
    mismatch_bases = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        control_len = i2 - i1
        edited_len = j2 - j1
        delta = edited_len - control_len
        if delta == 0:
            mismatch_bases += max(control_len, edited_len)
            continue
        size = max(-50, min(50, delta))
        event_weights[size] = event_weights.get(size, 0) + abs(delta)

    return event_weights, mismatch_bases


def _quality_warning(
    control_trace: ParsedTrace,
    edited_trace: ParsedTrace,
    cut_zero: int,
) -> str | None:
    control_quality = _mean_quality_near_cut(control_trace, cut_zero)
    edited_quality = _mean_quality_near_cut(edited_trace, cut_zero)
    qualities = [value for value in (control_quality, edited_quality) if value is not None]
    if qualities and min(qualities) < _LOW_QUALITY_PHRED:
        return CRISPR_TIDE_LOW_QUALITY
    return None


def _mean_quality_near_cut(trace: ParsedTrace, cut_zero: int) -> float | None:
    if not trace.q_scores:
        return None
    left = max(0, cut_zero - _ALIGN_UPSTREAM_BP)
    right = min(len(trace.q_scores), cut_zero + _DECOMPOSE_DOWNSTREAM_BP)
    values = trace.q_scores[left:right]
    if not values:
        return None
    return sum(values) / len(values)


def _sequence_identity(*, window_length: int, mismatch_bases: int) -> float:
    if window_length <= 0:
        return 0.0
    return round(max(0.0, min(1.0, 1.0 - (mismatch_bases / window_length))), 4)


def _notes() -> str:
    return (
        "Descriptive comparison of parsed AB1 consensus calls. It does not use "
        "chromatogram-signal decomposition, estimate editing efficiency, report "
        "goodness-of-fit, or implement the TIDE method."
    )
