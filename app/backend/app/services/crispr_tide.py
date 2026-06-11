from __future__ import annotations

from difflib import SequenceMatcher

from app.schemas.workbench import CrisprTideResponse, CrisprTideSpectrumBin
from app.services.trace_parser import ParsedTrace

CRISPR_TIDE_INVALID_INPUT = "crispr_tide_invalid_input"
CRISPR_TIDE_LENGTH_MISMATCH = "crispr_tide_read_length_mismatch"
CRISPR_TIDE_CONSENSUS_ONLY = "crispr_tide_consensus_only"
CRISPR_TIDE_NO_INDEL_SHIFT = "crispr_tide_no_indel_shift_detected"
CRISPR_TIDE_LOW_QUALITY = "crispr_tide_low_quality_window"
CRISPR_TIDE_PROVIDER_LABEL = "Eamos observed-only TIDE-style analyzer"

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


def analyze_crispr_tide_observed(
    *,
    control_trace: ParsedTrace,
    edited_trace: ParsedTrace,
    cut_site_index: int,
) -> CrisprTideResponse:
    """Build a source-backed, observed-only TIDE-style result from parsed traces.

    This intentionally does not copy or embed the NKI/TIDE NNLS solver. It
    exposes the Workbench result surface expected from TIDE-like analysis while
    keeping provenance explicit until a validated decomposition backend lands.
    """

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
        return CrisprTideResponse(
            provider_label=CRISPR_TIDE_PROVIDER_LABEL,
            cut_site_index=cut_site_index,
            editing_efficiency=0.0,
            r_squared=_fit_proxy(
                window_length=max(len(control_window), len(edited_window)),
                mismatch_bases=mismatch_bases,
            ),
            spectrum=[CrisprTideSpectrumBin(size=0, observed=1.0, predicted=None)],
            predicted_available=False,
            notes=_notes(),
            warnings=warnings,
        )

    total_weight = sum(event_weights.values())
    window_length = max(len(control_window), len(edited_window), 1)
    nonzero_mass = min(0.95, max(0.05, (total_weight + mismatch_bases) / window_length))
    spectrum = [
        CrisprTideSpectrumBin(size=0, observed=round(1.0 - nonzero_mass, 4), predicted=None)
    ]
    for size in sorted(event_weights):
        observed = nonzero_mass * (event_weights[size] / total_weight)
        spectrum.append(
            CrisprTideSpectrumBin(
                size=size,
                observed=round(observed, 4),
                predicted=None,
            )
        )

    return CrisprTideResponse(
        provider_label=CRISPR_TIDE_PROVIDER_LABEL,
        cut_site_index=cut_site_index,
        editing_efficiency=round(nonzero_mass, 4),
        r_squared=_fit_proxy(window_length=window_length, mismatch_bases=mismatch_bases),
        spectrum=sorted(spectrum, key=lambda item: item.size),
        predicted_available=False,
        notes=_notes(),
        warnings=warnings,
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


def _fit_proxy(*, window_length: int, mismatch_bases: int) -> float:
    if window_length <= 0:
        return 0.0
    return round(max(0.0, min(1.0, 1.0 - (mismatch_bases / window_length))), 4)


def _notes() -> str:
    return (
        "Observed-only TIDE-style result from parsed AB1 consensus traces. "
        "The response provides the expected TIDE surface: editing efficiency, "
        "fit readout, and indel-size spectrum. It does not run the NKI/TIDE "
        "NNLS decomposition solver, does not estimate p-values, and does not "
        "include Lindel or TIDER template-directed repair prediction."
    )
