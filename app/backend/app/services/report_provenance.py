from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.schemas.run import EvidenceSourceSummary, SourceProvenance, SourceStatus
from app.services.report_source_truth import normalize_report_source_status
from app.services.source_fact_policy import build_source_fact_policy_envelope

_SOURCE_TABLE_POLICY_IDENTITIES: dict[str, tuple[str, str]] = {
    "clingen gene-disease validity": ("clingen_gene_validity", "gene"),
    "gencc": ("gencc_download", "gene"),
    "mondo": ("mondo_disease_ontology", "disease_ids"),
    "human phenotype ontology": ("human_phenotype_ontology", "phenotype_ids"),
}


def provenance_from_evidence(
    evidence: list[EvidenceSourceSummary],
    *,
    retrieved_at: datetime | None = None,
) -> list[SourceProvenance]:
    default_timestamp = retrieved_at or datetime.now(timezone.utc)
    return [
        SourceProvenance(
            source=item.source,
            status=normalize_source_status(item.status),
            query=_string_query_identity(item.request_identity),
            source_url=item.source_url,
            retrieved_at=_parse_timestamp(item.fetched_at) or default_timestamp,
            version=item.source_version,
            warnings=list(item.warnings),
        )
        for item in evidence
    ]


def provenance_for_source(
    source: str,
    *,
    status: str,
    query: dict[str, Any] | None = None,
    source_url: str | None = None,
    version: str | None = None,
    warnings: list[str] | None = None,
) -> SourceProvenance:
    return SourceProvenance(
        source=source,
        status=normalize_source_status(status),
        query=_string_query_identity(query or {}),
        source_url=source_url,
        version=version,
        retrieved_at=datetime.now(timezone.utc),
        warnings=list(warnings or []),
    )


def source_provenance_from_mapping(raw: dict[str, Any]) -> SourceProvenance:
    """Validate source provenance without silently losing malformed live rows."""

    source = str(raw.get("source") or "unknown_source").strip() or "unknown_source"
    raw_status = str(raw.get("status") or "missing").strip().lower()
    warnings = _string_list(raw.get("warnings"))
    normalized: dict[str, Any] = {
        **raw,
        "source": source,
        "status": normalize_source_status(raw_status),
        "query": _string_query_identity(
            raw.get("query") if isinstance(raw.get("query"), dict) else {}
        ),
        "warnings": warnings,
    }

    if raw_status == "source_table":
        normalized["status"] = "local"
        normalized["storage_kind"] = str(raw.get("storage_kind") or "private_source_table")
        identity = _SOURCE_TABLE_POLICY_IDENTITIES.get(source.casefold())
        if identity is None:
            source_id = f"unregistered_source_table_{_identifier(source)}"
            policy_field = "record"
            warnings.append("source_table_policy_identity_unregistered")
        else:
            source_id, policy_field = identity
        query = normalized["query"]
        normalized.update(
            build_source_fact_policy_envelope(
                source_id=source_id,
                field_paths=(policy_field,),
                source_record_id=_query_record_id(query),
                source_version=_optional_text(raw.get("version")),
                source_url=_optional_text(raw.get("source_url")),
                retrieved_at=_timestamp_or_none(raw.get("retrieved_at")),
                origin_kind="direct",
                match_level="gene_disease",
            )
        )
        normalized["warnings"] = _dedupe(warnings)

    origin_kind = normalized.get("origin_kind")
    if origin_kind not in {None, "direct", "cross_reference", "derived"}:
        normalized["origin_kind"] = "direct"
        normalized["warnings"] = _dedupe(
            [*normalized["warnings"], "provenance_origin_kind_invalid"]
        )

    try:
        return SourceProvenance.model_validate(normalized)
    except ValidationError as exc:
        return SourceProvenance(
            source=source,
            status="fallback",
            query=_string_query_identity(
                raw.get("query") if isinstance(raw.get("query"), dict) else {}
            ),
            source_url=_optional_text(raw.get("source_url")),
            version=_optional_text(raw.get("version")),
            storage_kind=("private_source_table" if raw_status == "source_table" else None),
            warnings=_dedupe(
                [*warnings, f"provenance_validation_failed:{exc.error_count()}_errors"]
            ),
        )


def normalize_source_status(status: str | None) -> SourceStatus:
    return normalize_report_source_status(status)  # type: ignore[return-value]


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _string_query_identity(identity: dict[str, Any]) -> dict[str, str]:
    query: dict[str, str] = {}
    for key, value in identity.items():
        if value is None:
            continue
        if isinstance(value, str):
            text = value.strip()
        elif isinstance(value, bool | int | float):
            text = str(value)
        elif isinstance(value, list | tuple | set):
            text = ",".join(
                item_text for item in value if (item_text := _optional_text(item)) is not None
            )
        else:
            continue
        if text:
            query[str(key)] = text
    return query


def _timestamp_or_none(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return _parse_timestamp(_optional_text(value))


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _optional_text(item)) is not None]


def _identifier(value: str) -> str:
    normalized = "_".join(value.casefold().split())
    return "".join(character for character in normalized if character.isalnum() or character == "_")


def _query_record_id(query: dict[str, str]) -> str | None:
    if not query:
        return None
    return ";".join(f"{key}={query[key]}" for key in sorted(query))


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
