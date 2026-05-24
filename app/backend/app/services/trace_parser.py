from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from importlib import import_module
from io import BytesIO
from typing import Any

TRACE_INVALID_BASE64 = "trace_invalid_base64"
TRACE_PARSER_UNAVAILABLE = "trace_parser_unavailable"
TRACE_UNSUPPORTED_FORMAT = "trace_unsupported_format"


@dataclass(frozen=True)
class TraceChannelData:
    base: str
    values: tuple[float, ...]


@dataclass(frozen=True)
class ParsedTrace:
    sequence: str
    base_calls: tuple[str, ...]
    q_scores: tuple[int, ...]
    trace_channels: tuple[TraceChannelData, ...]
    peak_locations: tuple[int, ...]


class TraceParseError(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def parse_ab1_base64(blob: str, *, seqio_module: Any | None = None) -> ParsedTrace:
    encoded = blob.strip()
    if encoded.lower().startswith("data:") and "," in encoded:
        encoded = encoded.split(",", 1)[1]

    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise TraceParseError(
            code=TRACE_INVALID_BASE64,
            message="AB1 trace payload is not valid base64.",
        ) from exc

    if not data:
        raise TraceParseError(
            code=TRACE_UNSUPPORTED_FORMAT,
            message="AB1 trace payload is empty.",
        )

    return parse_ab1_bytes(data, seqio_module=seqio_module)


def parse_ab1_bytes(data: bytes, *, seqio_module: Any | None = None) -> ParsedTrace:
    seqio = seqio_module if seqio_module is not None else _bio_seqio()
    try:
        record = seqio.read(BytesIO(data), "abi")
    except Exception as exc:
        raise TraceParseError(
            code=TRACE_UNSUPPORTED_FORMAT,
            message="AB1 trace payload could not be parsed.",
        ) from exc

    annotations = getattr(record, "annotations", {})
    abif_raw = annotations.get("abif_raw", {}) if isinstance(annotations, dict) else {}
    sequence = _clean_sequence(str(getattr(record, "seq", "")))
    if not sequence:
        sequence = "".join(_base_calls(abif_raw, ""))
    if not sequence:
        raise TraceParseError(
            code=TRACE_UNSUPPORTED_FORMAT,
            message="AB1 trace did not contain base calls.",
        )

    base_calls = _base_calls(abif_raw, sequence)
    return ParsedTrace(
        sequence=sequence,
        base_calls=base_calls,
        q_scores=_quality_scores(record, abif_raw),
        trace_channels=_trace_channels(abif_raw),
        peak_locations=_int_tuple(_first_value(abif_raw, "PLOC2", "PLOC1")),
    )


def _bio_seqio() -> Any:
    try:
        return import_module("Bio.SeqIO")
    except ModuleNotFoundError as exc:
        raise TraceParseError(
            code=TRACE_PARSER_UNAVAILABLE,
            message="Biopython is required to parse AB1 trace files.",
        ) from exc


def _base_calls(abif_raw: dict[str, Any], fallback_sequence: str) -> tuple[str, ...]:
    raw_bases = _first_value(abif_raw, "PBAS2", "PBAS1")
    sequence = _clean_sequence(_ascii_text(raw_bases))
    if not sequence:
        sequence = fallback_sequence
    return tuple(sequence)


def _quality_scores(record: Any, abif_raw: dict[str, Any]) -> tuple[int, ...]:
    letter_annotations = getattr(record, "letter_annotations", {})
    if isinstance(letter_annotations, dict):
        qualities = letter_annotations.get("phred_quality")
        if qualities is not None:
            return _int_tuple(qualities)
    return _int_tuple(_first_value(abif_raw, "PCON2", "PCON1"))


def _trace_channels(abif_raw: dict[str, Any]) -> tuple[TraceChannelData, ...]:
    order = _ascii_text(abif_raw.get("FWO_1")).upper()
    if len(order) < 4:
        order = "GATC"

    by_base: dict[str, TraceChannelData] = {}
    for base, tag in zip(order[:4], ("DATA9", "DATA10", "DATA11", "DATA12"), strict=True):
        if base not in {"A", "T", "C", "G"}:
            continue
        values = _normalized_values(abif_raw.get(tag))
        if values:
            by_base[base] = TraceChannelData(base=base, values=values)

    return tuple(by_base[base] for base in ("A", "T", "C", "G") if base in by_base)


def _first_value(values: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = values.get(key)
        if value is not None:
            return value
    return None


def _ascii_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("ascii", errors="ignore")
    if isinstance(value, str):
        return value
    return str(value)


def _clean_sequence(sequence: str) -> str:
    cleaned: list[str] = []
    for char in sequence.upper():
        if char in {"A", "C", "G", "T", "N"}:
            cleaned.append(char)
        elif char == "U":
            cleaned.append("T")
    return "".join(cleaned)


def _int_tuple(values: Any) -> tuple[int, ...]:
    if values is None:
        return ()
    try:
        iterable = values if not isinstance(values, str) else values.encode("ascii")
        return tuple(max(0, int(value)) for value in iterable)
    except (TypeError, ValueError):
        return ()


def _normalized_values(values: Any) -> tuple[float, ...]:
    if values is None:
        return ()

    try:
        numbers = [float(value) for value in values]
    except (TypeError, ValueError):
        return ()

    if not numbers:
        return ()
    high = max(numbers)
    if high <= 0:
        return tuple(0.0 for _ in numbers)
    return tuple(round(value / high, 4) for value in numbers)
