from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.schemas.run import (
    OMIM_CROSS_REFERENCE_SUPPLIER_POLICY,
    AssociatedCondition,
    OmimCrossReference,
)
from app.services.source_fact_policy import build_source_fact_policy_envelope

_OMIM_IDENTIFIER_RE = re.compile(r"^OMIM:([0-9]{6})$")
_SOURCE_RECORD_ID_RE = re.compile(r"^[A-Za-z0-9_.:|=-]{1,160}$")


def normalize_omim_cross_references(
    raw_references: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate supplier-owned identifier links and fail closed on policy gaps."""

    if raw_references is None:
        return [], []
    if not isinstance(raw_references, list):
        return [], ["omim_cross_reference_list_malformed"]

    references: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in raw_references:
        reference, warning = build_omim_cross_reference(raw)
        if warning is not None:
            warnings.append(warning)
        if reference is None:
            continue
        key = (
            reference.identifier,
            reference.source_id or "",
            reference.source_record_id or "",
        )
        if key in seen:
            continue
        seen.add(key)
        references.append(reference.model_dump(mode="json"))
    return references, list(dict.fromkeys(warnings))


def legacy_condition_ids(condition: AssociatedCondition) -> list[str]:
    candidates = [condition.source, condition.db_tag, condition.source_list]
    ids: list[str] = []
    for text in candidates:
        if text:
            ids.extend(re.findall(r"(OMIM\s*#?\d+|ORPHA:\d+|MONDO:\d+)", text, flags=re.I))
    seen: set[str] = set()
    result: list[str] = []
    for item in ids:
        normalized = item.replace(" ", "")
        if normalized not in seen:
            seen.add(normalized)
            result.append(item)
    return result


def validated_omim_cross_references(
    raw_references: Any,
) -> tuple[list[OmimCrossReference], list[str]]:
    """Revalidate normalized report facts at the typed orchestration boundary."""

    if not isinstance(raw_references, list):
        return [], []
    references: list[OmimCrossReference] = []
    warnings: list[str] = []
    for raw in raw_references:
        if not isinstance(raw, Mapping):
            warnings.append("omim_cross_reference_profile_validation_failed")
            continue
        try:
            reference = OmimCrossReference.model_validate(raw)
        except ValidationError:
            warnings.append("omim_cross_reference_profile_validation_failed")
            continue
        if reference not in references:
            references.append(reference)
    return references, list(dict.fromkeys(warnings))


def build_omim_cross_reference(
    raw: Any,
) -> tuple[OmimCrossReference | None, str | None]:
    if not isinstance(raw, Mapping):
        return None, "omim_cross_reference_malformed"

    identifier = _text(raw.get("identifier"))
    match = _OMIM_IDENTIFIER_RE.fullmatch(identifier or "")
    if match is None:
        return None, "omim_cross_reference_identifier_invalid"

    source_id = _text(raw.get("source_id"))
    supplier_policy = OMIM_CROSS_REFERENCE_SUPPLIER_POLICY.get(source_id or "")
    if supplier_policy is None:
        return None, "omim_cross_reference_supplier_unapproved"
    policy_field, allowed_entry_types = supplier_policy

    source_record_id = _text(raw.get("source_record_id"))
    if source_record_id is None or _SOURCE_RECORD_ID_RE.fullmatch(source_record_id) is None:
        return None, "omim_cross_reference_source_record_invalid"

    entry_type = _text(raw.get("entry_type"))
    if entry_type not in allowed_entry_types:
        return None, "omim_cross_reference_entry_type_invalid"

    envelope = build_source_fact_policy_envelope(
        source_id=source_id,
        field_paths=(policy_field,),
        source_record_id=source_record_id,
        origin_kind="cross_reference",
        match_level="identifier",
    )
    if envelope["public_serialization_allowed"] is not True:
        return None, "omim_cross_reference_policy_denied"

    try:
        reference = OmimCrossReference.model_validate(
            {
                **envelope,
                "identifier": identifier,
                "entry_type": entry_type,
                "external_url": f"https://omim.org/entry/{match.group(1)}",
            }
        )
    except ValidationError:
        return None, "omim_cross_reference_validation_failed"
    return reference, None


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
