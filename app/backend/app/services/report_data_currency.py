from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any

from app.schemas.run import (
    EvidenceSourceSummary,
    ReportDataCurrency,
    ReportDataCurrencySource,
    ReportDataCurrencyStatus,
    ReportDataCurrencyTier,
)

_SOURCE_META: dict[str, tuple[str, ReportDataCurrencyTier | None]] = {
    "clinvar": ("ClinVar", "volatile"),
    "clingen": ("ClinGen", "volatile"),
    "clinical_consensus": ("Clinical consensus", "volatile"),
    "clinical_trials": ("ClinicalTrials.gov", "volatile"),
    "gnomad": ("gnomAD", "static"),
    "pubmed": ("PubMed", "volatile"),
    "litvar2": ("LitVar2", "volatile"),
    "gene_disease": ("Gene disease", "volatile"),
    "computational_annotations": ("Computational annotations", "static"),
    "molecular_context": ("Molecular context", "static"),
    "sequence_context": ("Sequence context", "static"),
    "gene_context_snapshot": ("Gene context", "static"),
    "vep": ("Ensembl VEP", "volatile"),
    "variant_validator": ("VariantValidator", "volatile"),
}

_UNSAFE_PUBLIC_TEXT_MARKERS = (
    "://",
    "\\",
    "/var/",
    "/app/",
    "/tmp/",
    "secret",
    "token=",
    "apikey",
    "api_key",
)
_SOURCE_KEY_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,80}$")


def current_report_timestamp(now: datetime | None = None) -> str:
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def build_report_data_currency(
    evidence: list[EvidenceSourceSummary],
    evidence_map: dict[str, dict[str, Any]],
    *,
    generated_at: str,
) -> ReportDataCurrency | None:
    sources: list[ReportDataCurrencySource] = []
    seen: set[str] = set()
    for item in evidence:
        source = _safe_source_key(item.source)
        if source is None or source in seen:
            continue
        seen.add(source)
        summary = evidence_map.get(item.source, {})
        source_currency = _source_currency(item, summary, generated_at=generated_at)
        if source_currency is not None:
            sources.append(source_currency)

    if not sources:
        return None
    return ReportDataCurrency(generated_at=generated_at, sources=sources)


def latest_evidence_timestamp(
    evidence: list[EvidenceSourceSummary],
    evidence_map: dict[str, dict[str, Any]] | None = None,
) -> str | None:
    evidence_map = evidence_map or {}
    candidates: list[tuple[datetime, str]] = []
    for item in evidence:
        summary = evidence_map.get(item.source, {})
        for value in (
            item.fetched_at,
            _summary_materialized_at(summary),
            _summary_upstream_released_at(summary),
        ):
            normalized = _normalize_temporal_value(value)
            parsed = _parse_temporal_value(normalized)
            if normalized is not None and parsed is not None:
                candidates.append((parsed, normalized))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _source_currency(
    item: EvidenceSourceSummary,
    summary: dict[str, Any],
    *,
    generated_at: str,
) -> ReportDataCurrencySource | None:
    source = _safe_source_key(item.source)
    if source is None:
        return None
    label, tier = _SOURCE_META.get(source, (_display_label(source), None))
    materialized_at = _normalize_temporal_value(item.fetched_at) or _summary_materialized_at(
        summary
    )
    upstream_released_at = _summary_upstream_released_at(summary)
    source_version = (
        _safe_public_text(item.source_version)
        or _summary_source_version(summary)
        or _source_specific_version(source, summary)
    )
    date_for_staleness = materialized_at or upstream_released_at
    return ReportDataCurrencySource(
        source=source,
        label=label,
        materialized_at=materialized_at,
        upstream_released_at=upstream_released_at,
        tier=tier,
        status=_freshness_status(item, date_for_staleness),
        staleness_days=_staleness_days(date_for_staleness, generated_at),
        source_version=source_version,
    )


def _summary_materialized_at(summary: dict[str, Any]) -> str | None:
    return _first_temporal(
        summary.get("materialized_at"),
        summary.get("fetched_at"),
        _nested(summary, "freshness", "materialized_at"),
        _nested(summary, "expert_panel", "provenance", "fetched_at"),
    )


def _summary_upstream_released_at(summary: dict[str, Any]) -> str | None:
    return _first_temporal(
        summary.get("upstream_released_at"),
        summary.get("source_release_date"),
        summary.get("release_date"),
        summary.get("file_date"),
        _nested(summary, "freshness", "upstream_released_at"),
        _nested(summary, "expert_panel", "vcep", "last_curated_date"),
    )


def _summary_source_version(summary: dict[str, Any]) -> str | None:
    for value in (
        summary.get("source_version"),
        summary.get("upstream_version"),
        _nested(summary, "freshness", "source_version"),
        _nested(summary, "expert_panel", "provenance", "source_version"),
    ):
        safe = _safe_public_text(value)
        if safe is not None:
            return safe
    return None


def _source_specific_version(source: str, summary: dict[str, Any]) -> str | None:
    if source == "gnomad":
        return _safe_public_text(summary.get("dataset"))
    return None


def _freshness_status(
    item: EvidenceSourceSummary,
    dated_value: str | None,
) -> ReportDataCurrencyStatus:
    status = (item.status or "").strip().lower()
    cache_status = (item.cache_status or "").strip().lower()
    if cache_status == "stale_on_failure" or status == "stale":
        return "stale"
    if dated_value is None:
        return "unknown"
    if status in {"live", "local", "cache", "fixture"}:
        return "fresh"
    return "unknown"


def _staleness_days(source_timestamp: str | None, generated_at: str) -> int | None:
    source_dt = _parse_temporal_value(source_timestamp)
    generated_dt = _parse_temporal_value(generated_at)
    if source_dt is None or generated_dt is None:
        return None
    return max(0, (generated_dt.date() - source_dt.date()).days)


def _first_temporal(*values: object) -> str | None:
    for value in values:
        normalized = _normalize_temporal_value(value)
        if normalized is not None:
            return normalized
    return None


def _normalize_temporal_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "unknown":
        return None
    if re.fullmatch(r"\d{8}", text):
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    parsed = _parse_temporal_value(text)
    if parsed is None:
        return None
    if "T" not in text and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return parsed.date().isoformat()
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_temporal_value(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return datetime.combine(date.fromisoformat(text), datetime.min.time(), timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _nested(value: dict[str, Any], *keys: str) -> object | None:
    current: object = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _safe_source_key(value: object) -> str | None:
    text = str(value or "").strip()
    if not _SOURCE_KEY_RE.fullmatch(text):
        return None
    return text


def _safe_public_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    if any(marker in lowered for marker in _UNSAFE_PUBLIC_TEXT_MARKERS):
        return None
    return text


def _display_label(source: str) -> str:
    return source.replace("_", " ").strip().title()
