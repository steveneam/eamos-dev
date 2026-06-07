from __future__ import annotations

import math
from collections.abc import Iterable
from statistics import fmean

from app.schemas.workbench import (
    AlignTraceHetCall,
    AlignTraceResponse,
    AlignTraceTrimRange,
    TraceChannel,
)
from app.services.trace_parser import ParsedTrace

TRACE_ANALYSIS_METHOD = "modified_mott_q20_phfinder3"
TRACE_SCIPY_FALLBACK = "trace_scipy_find_peaks_unavailable"
MOTT_Q_CUTOFF = 20
HET_MAIN_RATIO_MIN = 0.5
HET_FLANK_RATIO_MIN = 2.0
HET_AVG_Q_MIN = 20.0
HET_WINDOW_SAMPLES = 5
HET_FLANK_BASES = 3
NOISE_FLOOR_PERCENTILE = 5.0


def analyze_parsed_trace(trace: ParsedTrace) -> AlignTraceResponse:
    warnings: list[str] = []
    raw_channels = {
        channel.base: channel.raw_values or channel.values for channel in trace.trace_channels
    }
    sample_count = max((len(values) for values in raw_channels.values()), default=0)
    if not raw_channels:
        warnings.append("trace_channels_missing")
    if len(trace.q_scores) != len(trace.base_calls):
        warnings.append("trace_quality_length_mismatch")
    if len(trace.peak_locations) != len(trace.base_calls):
        warnings.append("trace_peak_location_length_mismatch")

    noise_floor = _noise_floor(raw_channels.values())
    peak_warning: list[str] = []
    peak_sets = {
        base: _find_signal_peaks(values, noise_floor=noise_floor, warnings=peak_warning)
        for base, values in raw_channels.items()
    }
    warnings.extend(dict.fromkeys(peak_warning))

    trim = _mott_trim(trace.q_scores, base_count=len(trace.base_calls), warnings=warnings)
    return AlignTraceResponse(
        sequence=trace.sequence,
        base_calls=list(trace.base_calls),
        q_scores=list(trace.q_scores),
        base_confidence=_base_confidence(trace.q_scores),
        peak_locations=list(trace.peak_locations),
        trace_channels=[
            TraceChannel(base=channel.base, values=list(channel.values))
            for channel in trace.trace_channels
        ],
        sample_count=sample_count,
        trim=trim,
        het=_het_calls(
            trace,
            raw_channels=raw_channels,
            peak_sets=peak_sets,
            noise_floor=noise_floor,
            trim_start=trim.start,
            trim_end=trim.end,
        ),
        noise_floor=round(noise_floor, 4),
        warnings=list(dict.fromkeys(warnings)),
    )


def _mott_trim(
    q_scores: tuple[int, ...],
    *,
    base_count: int,
    warnings: list[str],
) -> AlignTraceTrimRange:
    if not q_scores:
        warnings.append("trace_quality_scores_missing")
        return AlignTraceTrimRange(
            start=0,
            end=base_count,
            method=TRACE_ANALYSIS_METHOD,
            q_cutoff=MOTT_Q_CUTOFF,
        )

    cutoff_error = 10 ** (-MOTT_Q_CUTOFF / 10)
    best_score = 0.0
    best_start = 0
    best_end = len(q_scores)
    running_score = 0.0
    running_start = 0
    for index, quality in enumerate(q_scores):
        error_probability = 10 ** (-(max(0, quality)) / 10)
        running_score += cutoff_error - error_probability
        if running_score < 0:
            running_score = 0.0
            running_start = index + 1
            continue
        if running_score > best_score:
            best_score = running_score
            best_start = running_start
            best_end = index + 1

    if best_score <= 0 or best_end <= best_start:
        warnings.append("trace_mott_trim_no_q20_segment")
        best_start = 0
        best_end = base_count

    best_start = min(best_start, base_count)
    best_end = min(max(best_end, best_start), base_count)
    return AlignTraceTrimRange(
        start=best_start,
        end=best_end,
        method=TRACE_ANALYSIS_METHOD,
        q_cutoff=MOTT_Q_CUTOFF,
    )


def _het_calls(
    trace: ParsedTrace,
    *,
    raw_channels: dict[str, tuple[float, ...]],
    peak_sets: dict[str, set[int]],
    noise_floor: float,
    trim_start: int,
    trim_end: int,
) -> list[AlignTraceHetCall]:
    het: list[AlignTraceHetCall] = []
    if not trace.peak_locations:
        return het

    base_count = min(len(trace.base_calls), len(trace.peak_locations))
    for index in range(base_count):
        if index < trim_start or index >= trim_end:
            continue
        called_base = trace.base_calls[index]
        if called_base not in {"A", "C", "G", "T"}:
            continue
        sample = trace.peak_locations[index]
        primary_values = raw_channels.get(called_base)
        if not primary_values:
            continue
        primary_signal = _signal_at(primary_values, sample)
        if primary_signal <= max(noise_floor * 5, 0):
            continue

        secondary_base, secondary_signal = _secondary_peak(
            called_base=called_base,
            sample=sample,
            raw_channels=raw_channels,
            peak_sets=peak_sets,
        )
        if secondary_base is None or secondary_signal <= max(noise_floor * 3, 0):
            continue

        main_ratio = secondary_signal / primary_signal if primary_signal else 0.0
        if main_ratio < HET_MAIN_RATIO_MIN:
            continue

        flank_ratio = secondary_signal / max(
            noise_floor,
            _flank_signal_mean(
                base=secondary_base,
                trace=trace,
                raw_channels=raw_channels,
                center_index=index,
            ),
            1e-9,
        )
        if flank_ratio < HET_FLANK_RATIO_MIN:
            continue

        avg_q = _average_quality(trace.q_scores, center=index)
        if avg_q < HET_AVG_Q_MIN:
            continue

        het.append(
            AlignTraceHetCall(
                index=index,
                called_base=called_base,
                secondary_base=secondary_base,
                main_ratio=round(main_ratio, 4),
                flank_ratio=round(flank_ratio, 4),
                avg_q=round(avg_q, 2),
                primary_signal=round(primary_signal, 4),
                secondary_signal=round(secondary_signal, 4),
            )
        )
    return het


def _secondary_peak(
    *,
    called_base: str,
    sample: int,
    raw_channels: dict[str, tuple[float, ...]],
    peak_sets: dict[str, set[int]],
) -> tuple[str | None, float]:
    best_base: str | None = None
    best_signal = 0.0
    for base, values in raw_channels.items():
        if base == called_base:
            continue
        if not _has_peak_near(peak_sets.get(base, set()), sample):
            continue
        signal = _window_max(values, sample, HET_WINDOW_SAMPLES)
        if signal > best_signal:
            best_base = base
            best_signal = signal
    return best_base, best_signal


def _find_signal_peaks(
    values: tuple[float, ...],
    *,
    noise_floor: float,
    warnings: list[str],
) -> set[int]:
    if len(values) < 3:
        return set()
    prominence = max(noise_floor * 3, max(values) * 0.02, 1e-9)
    try:
        from scipy.signal import find_peaks

        peaks, _properties = find_peaks(values, prominence=prominence, distance=3)
        return {int(peak) for peak in peaks}
    except Exception:
        warnings.append(TRACE_SCIPY_FALLBACK)
        return _fallback_peaks(values, prominence=prominence)


def _fallback_peaks(values: tuple[float, ...], *, prominence: float) -> set[int]:
    peaks: set[int] = set()
    for index in range(1, len(values) - 1):
        value = values[index]
        if value <= values[index - 1] or value < values[index + 1]:
            continue
        local_floor = min(values[index - 1], values[index + 1])
        if value - local_floor >= prominence:
            peaks.add(index)
    return peaks


def _has_peak_near(peaks: set[int], sample: int) -> bool:
    return any(abs(peak - sample) <= HET_WINDOW_SAMPLES for peak in peaks)


def _window_max(values: tuple[float, ...], center: int, radius: int) -> float:
    if not values:
        return 0.0
    start = max(0, center - radius)
    end = min(len(values), center + radius + 1)
    return max(values[start:end], default=0.0)


def _signal_at(values: tuple[float, ...], index: int) -> float:
    if index < 0 or index >= len(values):
        return 0.0
    return values[index]


def _flank_signal_mean(
    *,
    base: str,
    trace: ParsedTrace,
    raw_channels: dict[str, tuple[float, ...]],
    center_index: int,
) -> float:
    values = raw_channels.get(base, ())
    if not values:
        return 0.0
    signals: list[float] = []
    start = max(0, center_index - HET_FLANK_BASES)
    end = min(len(trace.peak_locations), center_index + HET_FLANK_BASES + 1)
    for index in range(start, end):
        if index == center_index:
            continue
        signals.append(_signal_at(values, trace.peak_locations[index]))
    return fmean(signals) if signals else 0.0


def _average_quality(q_scores: tuple[int, ...], *, center: int) -> float:
    if not q_scores:
        return 0.0
    start = max(0, center - HET_FLANK_BASES)
    end = min(len(q_scores), center + HET_FLANK_BASES + 1)
    return fmean(q_scores[start:end]) if end > start else 0.0


def _base_confidence(q_scores: tuple[int, ...]) -> list[float]:
    confidence: list[float] = []
    for quality in q_scores:
        probability = 1 - 10 ** (-(max(0, quality)) / 10)
        confidence.append(round(min(max(probability, 0.0), 1.0), 6))
    return confidence


def _noise_floor(channel_values: Iterable[Iterable[float]]) -> float:
    values: list[float] = []
    for channel in channel_values:
        values.extend(
            float(value) for value in channel if math.isfinite(float(value)) and float(value) > 0
        )
    if not values:
        return 0.0
    values.sort()
    position = (len(values) - 1) * (NOISE_FLOOR_PERCENTILE / 100)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction
