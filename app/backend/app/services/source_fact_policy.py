from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Mapping

from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    DataSourceRegistry,
    PolicyAction,
    ProductTier,
    SourceFieldPolicy,
)

SOURCE_FACT_POLICY_VERSION = "source-fact-policy-v2"
SOURCE_FACT_POLICY_ACTIONS: tuple[PolicyAction, ...] = (
    PolicyAction.ACQUIRE,
    PolicyAction.NORMALIZE,
    PolicyAction.CACHE,
    PolicyAction.PUBLIC_SERIALIZE,
    PolicyAction.PRODUCT_EXPORT,
    PolicyAction.LOG,
    PolicyAction.ANALYZE,
    PolicyAction.BACKUP,
    PolicyAction.STAGE,
    PolicyAction.RESTORE,
    PolicyAction.RAW_DEBUG,
)


def build_source_fact_policy_envelope(
    *,
    source_id: str,
    field_paths: tuple[str, ...],
    source_record_id: str | None = None,
    source_version: str | None = None,
    source_url: str | None = None,
    retrieved_at: datetime | None = None,
    origin_kind: str = "direct",
    match_level: str | None = None,
    product_tier: str | ProductTier = ProductTier.PUBLIC,
    action_field_allowlists: (
        Mapping[str, Mapping[str | PolicyAction, tuple[str, ...]]] | None
    ) = None,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
) -> dict[str, object]:
    """Recompute one fact's policy envelope from the current registry and terms."""

    decided_at = datetime.now(timezone.utc)
    policy = SourceFieldPolicy(
        registry,
        action_field_allowlists=action_field_allowlists,
    )
    try:
        record = registry.get(source_id)
    except KeyError:
        record = None

    decisions: list[dict[str, object]] = []
    effective_fields = field_paths or ("__unspecified__",)
    for action in SOURCE_FACT_POLICY_ACTIONS:
        for field_path in effective_fields:
            decision = policy.decide(
                source_id,
                field_path,
                action=action,
                product_tier=product_tier,
            )
            decisions.append(
                {
                    "action": action.value,
                    "field": field_path,
                    "outcome": "allowed" if decision.allowed else "denied",
                    "reason": decision.reason,
                    "decided_at": decided_at,
                }
            )

    terms_fingerprint = _terms_fingerprint(
        record.terms_url if record is not None else None,
        record.terms_status if record is not None else None,
    )
    public_allowed = _projection(decisions, PolicyAction.PUBLIC_SERIALIZE)
    export_allowed = _projection(decisions, PolicyAction.PRODUCT_EXPORT)
    cache_allowed = _projection(decisions, PolicyAction.CACHE)
    denied = next(
        (
            decision
            for decision in decisions
            if decision["action"] in {"public_serialize", "product_export", "cache"}
            and decision["outcome"] == "denied"
        ),
        None,
    )

    return {
        "source_id": source_id,
        "source_record_id": source_record_id,
        "source_version": source_version or (record.source_version if record is not None else None),
        "source_url": source_url or (record.source_url if record is not None else None),
        "retrieved_at": retrieved_at or decided_at,
        "origin_kind": origin_kind,
        "match_level": match_level,
        "record_license": (
            record.license_status.value if record is not None else "unregistered_source"
        ),
        "terms_version_or_hash": terms_fingerprint,
        "license_gate": (
            record.license_status.value if record is not None else "registry_record_required"
        ),
        "launch_gate": record.day1_status if record is not None else "registry_record_required",
        "public_serialization_allowed": public_allowed,
        "export_allowed": export_allowed,
        "cache_allowed": cache_allowed,
        "attribution": record.upstream_source if record is not None else None,
        "policy_version": SOURCE_FACT_POLICY_VERSION,
        "decision_reason": (
            f"{denied['action']}:{denied['field']}:{denied['reason']}"
            if denied is not None
            else "all_recorded_policy_decisions_allowed"
        ),
        "decision_at": decided_at,
        "policy_decisions": decisions,
    }


def _projection(decisions: list[dict[str, object]], action: PolicyAction) -> bool:
    relevant = [decision for decision in decisions if decision["action"] == action.value]
    return bool(relevant) and all(decision["outcome"] == "allowed" for decision in relevant)


def _terms_fingerprint(terms_url: str | None, terms_status: str | None) -> str | None:
    if not terms_url and not terms_status:
        return None
    canonical = f"{terms_url or ''}\n{terms_status or ''}"
    return f"sha256:{sha256(canonical.encode('utf-8')).hexdigest()}"
