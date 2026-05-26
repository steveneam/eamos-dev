from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from app.data_sources.registry import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    DataSourceRecord,
    DataSourceRegistry,
    LicenseStatus,
)


class PolicyAction(str, Enum):
    REQUEST = "request"
    CACHE = "cache"
    NORMALIZE = "normalize"
    SERIALIZE = "serialize"


class ProductTier(str, Enum):
    PUBLIC = "public"
    INTERNAL_FIXTURE = "internal_fixture"
    LICENSED = "licensed"


@dataclass(frozen=True)
class FieldPolicyDecision:
    source_id: str
    field_path: str
    action: PolicyAction
    product_tier: ProductTier
    allowed: bool
    reason: str


class SourceFieldPolicy:
    """Backend field allowlist/denylist for source adapters and payloads."""

    def __init__(self, registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY) -> None:
        self._registry = registry

    def can_request(
        self,
        source_id: str,
        field_path: str,
        *,
        product_tier: str | ProductTier = ProductTier.PUBLIC,
    ) -> FieldPolicyDecision:
        return self.decide(
            source_id,
            field_path,
            action=PolicyAction.REQUEST,
            product_tier=product_tier,
        )

    def can_cache(
        self,
        source_id: str,
        field_path: str,
        *,
        product_tier: str | ProductTier = ProductTier.PUBLIC,
    ) -> FieldPolicyDecision:
        return self.decide(
            source_id,
            field_path,
            action=PolicyAction.CACHE,
            product_tier=product_tier,
        )

    def can_normalize(
        self,
        source_id: str,
        field_path: str,
        *,
        product_tier: str | ProductTier = ProductTier.PUBLIC,
    ) -> FieldPolicyDecision:
        return self.decide(
            source_id,
            field_path,
            action=PolicyAction.NORMALIZE,
            product_tier=product_tier,
        )

    def can_serialize(
        self,
        source_id: str,
        field_path: str,
        *,
        product_tier: str | ProductTier = ProductTier.PUBLIC,
    ) -> FieldPolicyDecision:
        return self.decide(
            source_id,
            field_path,
            action=PolicyAction.SERIALIZE,
            product_tier=product_tier,
        )

    def decide(
        self,
        source_id: str,
        field_path: str,
        *,
        action: str | PolicyAction,
        product_tier: str | ProductTier = ProductTier.PUBLIC,
    ) -> FieldPolicyDecision:
        action_value = PolicyAction(action)
        product_tier_value = _normalize_product_tier(product_tier)
        normalized_field = _normalize_field_path(field_path)

        if not normalized_field:
            return _deny(
                source_id,
                field_path,
                action_value,
                product_tier_value,
                "field_path_required",
            )

        try:
            record = self._registry.get(source_id)
        except KeyError:
            return _deny(
                source_id,
                field_path,
                action_value,
                product_tier_value,
                "unknown_source",
            )

        if _matches_any_field(record.restricted_fields, normalized_field):
            if (
                product_tier_value is ProductTier.INTERNAL_FIXTURE
                and action_value is PolicyAction.SERIALIZE
            ):
                return _allow(
                    source_id,
                    field_path,
                    action_value,
                    product_tier_value,
                    "internal_fixture_only",
                )
            if record.license_status is LicenseStatus.RESTRICTED_UNLICENSED:
                reason = "restricted_unlicensed"
            elif record.license_status is LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED:
                reason = "commercial_license_review_required"
            else:
                reason = "restricted_field"
            return _deny(source_id, field_path, action_value, product_tier_value, reason)

        license_denial = _license_denial_reason(record, product_tier_value)
        if license_denial:
            return _deny(
                source_id,
                field_path,
                action_value,
                product_tier_value,
                license_denial,
            )

        if not _product_tier_allowed(record, product_tier_value):
            return _deny(
                source_id,
                field_path,
                action_value,
                product_tier_value,
                "product_tier_not_allowed",
            )

        if not _matches_any_field(record.allowed_fields, normalized_field):
            return _deny(
                source_id,
                field_path,
                action_value,
                product_tier_value,
                "field_not_allowlisted",
            )

        return _allow(
            source_id,
            field_path,
            action_value,
            product_tier_value,
            "allowed_by_source_allowlist",
        )

    def filter_payload(
        self,
        source_id: str,
        payload: Mapping[str, Any],
        *,
        product_tier: str | ProductTier = ProductTier.PUBLIC,
    ) -> dict[str, Any]:
        product_tier_value = _normalize_product_tier(product_tier)
        has_fixture_warning = _has_internal_fixture_warning(payload)
        filtered = self._filter_value(
            source_id,
            payload,
            field_path="",
            product_tier=product_tier_value,
            has_fixture_warning=has_fixture_warning,
        )
        return filtered if isinstance(filtered, dict) else {}

    def _filter_value(
        self,
        source_id: str,
        value: Any,
        *,
        field_path: str,
        product_tier: ProductTier,
        has_fixture_warning: bool,
    ) -> Any | None:
        if isinstance(value, Mapping):
            kept: dict[str, Any] = {}
            for key, child in value.items():
                child_path = _join_field_path(field_path, str(key))
                if (
                    product_tier is ProductTier.INTERNAL_FIXTURE
                    and has_fixture_warning
                    and _is_internal_fixture_metadata(child_path)
                ):
                    kept[str(key)] = child
                    continue

                child_value = self._filter_value(
                    source_id,
                    child,
                    field_path=child_path,
                    product_tier=product_tier,
                    has_fixture_warning=has_fixture_warning,
                )
                if child_value is not None and child_value != {} and child_value != []:
                    kept[str(key)] = child_value
            return kept

        if isinstance(value, list):
            kept_list = [
                filtered
                for item in value
                if (
                    filtered := self._filter_value(
                        source_id,
                        item,
                        field_path=field_path,
                        product_tier=product_tier,
                        has_fixture_warning=has_fixture_warning,
                    )
                )
                is not None
            ]
            return kept_list

        if (
            product_tier is ProductTier.INTERNAL_FIXTURE
            and has_fixture_warning
            and self._restricted_field_serializable_for_fixture(source_id, field_path)
        ):
            return value
        if (
            product_tier is ProductTier.INTERNAL_FIXTURE
            and not has_fixture_warning
            and self._field_is_restricted(source_id, field_path)
        ):
            return None

        decision = self.can_serialize(
            source_id,
            field_path,
            product_tier=product_tier,
        )
        return value if decision.allowed else None

    def _restricted_field_serializable_for_fixture(self, source_id: str, field_path: str) -> bool:
        decision = self.can_serialize(
            source_id,
            field_path,
            product_tier=ProductTier.INTERNAL_FIXTURE,
        )
        return decision.allowed and decision.reason == "internal_fixture_only"

    def _field_is_restricted(self, source_id: str, field_path: str) -> bool:
        try:
            record = self._registry.get(source_id)
        except KeyError:
            return False
        return _matches_any_field(record.restricted_fields, _normalize_field_path(field_path))


def _allow(
    source_id: str,
    field_path: str,
    action: PolicyAction,
    product_tier: ProductTier,
    reason: str,
) -> FieldPolicyDecision:
    return FieldPolicyDecision(
        source_id=source_id,
        field_path=field_path,
        action=action,
        product_tier=product_tier,
        allowed=True,
        reason=reason,
    )


def _deny(
    source_id: str,
    field_path: str,
    action: PolicyAction,
    product_tier: ProductTier,
    reason: str,
) -> FieldPolicyDecision:
    return FieldPolicyDecision(
        source_id=source_id,
        field_path=field_path,
        action=action,
        product_tier=product_tier,
        allowed=False,
        reason=reason,
    )


def _license_denial_reason(record: DataSourceRecord, product_tier: ProductTier) -> str | None:
    if record.license_status is LicenseStatus.RESTRICTED_UNLICENSED:
        return "restricted_unlicensed"
    if (
        record.license_status is LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED
        and product_tier is not ProductTier.INTERNAL_FIXTURE
    ):
        return "commercial_license_review_required"
    if (
        record.license_status is LicenseStatus.INTERNAL_FIXTURE_ONLY
        and product_tier is not ProductTier.INTERNAL_FIXTURE
    ):
        return "internal_fixture_only"
    if product_tier is ProductTier.LICENSED and record.license_status not in {
        LicenseStatus.LICENSED_ENABLED,
        LicenseStatus.COMMERCIAL_ALLOWED,
    }:
        return "licensed_tier_not_enabled"
    return None


def _product_tier_allowed(record: DataSourceRecord, product_tier: ProductTier) -> bool:
    allowed_tiers = {_normalize_registry_tier(tier) for tier in record.allowed_product_tiers}
    if product_tier is ProductTier.PUBLIC:
        return "public" in allowed_tiers or "existing_runtime" in allowed_tiers
    if product_tier is ProductTier.INTERNAL_FIXTURE:
        return True
    if product_tier is ProductTier.LICENSED:
        return "licensed" in allowed_tiers or "public" in allowed_tiers
    return False


def _normalize_product_tier(product_tier: str | ProductTier) -> ProductTier:
    if isinstance(product_tier, ProductTier):
        return product_tier
    normalized = _normalize_field_segment(str(product_tier))
    if normalized in {"prod", "production", "public", "free", "public_day1_after_review"}:
        return ProductTier.PUBLIC
    if normalized in {"fixture", "internal", "internal_fixture", "internal_fixture_only", "test"}:
        return ProductTier.INTERNAL_FIXTURE
    if normalized in {"licensed", "licensed_pro", "pro", "licensed_pro_future"}:
        return ProductTier.LICENSED
    return ProductTier.PUBLIC


def _normalize_registry_tier(product_tier: str) -> str:
    normalized = _normalize_field_segment(product_tier)
    if normalized.startswith("public"):
        return "public"
    if normalized in {"existing_runtime"}:
        return normalized
    if normalized.startswith("licensed"):
        return "licensed"
    if normalized.startswith("internal"):
        return "internal_fixture"
    return normalized


def _matches_any_field(field_patterns: tuple[str, ...], normalized_field_path: str) -> bool:
    return any(
        _field_matches(_normalize_field_path(pattern), normalized_field_path)
        for pattern in field_patterns
    )


def _field_matches(normalized_pattern: str, normalized_field_path: str) -> bool:
    return normalized_field_path == normalized_pattern or normalized_field_path.startswith(
        f"{normalized_pattern}."
    )


def _join_field_path(parent: str, child: str) -> str:
    return child if not parent else f"{parent}.{child}"


def _normalize_field_path(field_path: str) -> str:
    return ".".join(
        segment
        for segment in (
            _normalize_field_segment(part) for part in str(field_path).split(".") if part.strip()
        )
        if segment
    )


def _normalize_field_segment(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return re.sub(r"_+", "_", normalized)


def _has_internal_fixture_warning(payload: Mapping[str, Any]) -> bool:
    warning_fields = (
        payload.get("license_warning"),
        payload.get("license_status"),
        payload.get("fixture_status"),
        payload.get("source_context"),
        payload.get("warnings"),
    )
    warning_text = " ".join(_flatten_warning_text(warning_fields)).lower()
    return (
        "internal_fixture" in warning_text
        or ("fixture" in warning_text and "restricted" in warning_text)
        or ("internal" in warning_text and "restricted" in warning_text)
    )


def _flatten_warning_text(values: tuple[Any, ...]) -> list[str]:
    flattened: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            flattened.append(value)
        elif isinstance(value, Mapping):
            flattened.extend(_flatten_warning_text(tuple(value.values())))
        elif isinstance(value, list):
            flattened.extend(_flatten_warning_text(tuple(value)))
        else:
            flattened.append(str(value))
    return flattened


def _is_internal_fixture_metadata(field_path: str) -> bool:
    return _normalize_field_path(field_path) in {
        "fixture_status",
        "license_status",
        "license_warning",
        "source_context",
        "warnings",
    }
