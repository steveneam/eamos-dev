from __future__ import annotations

import json
from datetime import date, datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from app.core.config import Settings
from app.services.clinvar_local import CLINVAR_SOURCE_ID, DEFAULT_CLINVAR_VCF_FIXTURE_PATH
from app.services.dbsnp_local import DBSNP_SOURCE_ID, DEFAULT_DBSNP_VCF_FIXTURE_PATH
from app.services.repeatmasker_local import (
    DEFAULT_REPEATMASKER_FIXTURE_PATH,
    REPEATMASKER_SOURCE_ID,
)

PHYLOP_SOURCE_ID = "ucsc_phylop100way_hg38"


@dataclass(frozen=True)
class LocalEvidenceRuntimeAssetRole:
    role: str
    path_setting: str
    expected_format: str


@dataclass(frozen=True)
class LocalEvidenceFreshnessPolicy:
    tier: str
    sla_days: int | None
    overdue_days: int | None = None


@dataclass(frozen=True)
class LocalEvidenceRuntimeSourceSpec:
    item_id: str
    source_id: str
    adapter: str
    roles: tuple[LocalEvidenceRuntimeAssetRole, ...]
    freshness_policy: LocalEvidenceFreshnessPolicy
    fixture_paths: tuple[Path, ...] = ()


_MANIFEST_SIZE_LIMIT_BYTES = 64 * 1024
_UNSAFE_PUBLIC_TEXT_MARKERS = (
    "://",
    "\\",
    "/app/",
    "/eamos/",
    "/tmp/",
    "/users/",
    "/var/",
    "api_key",
    "apikey",
    "c:/",
    "d:/",
    "password",
    "secret",
    "service_role",
    "token",
)


LOCAL_EVIDENCE_RUNTIME_SOURCE_SPECS: tuple[LocalEvidenceRuntimeSourceSpec, ...] = (
    LocalEvidenceRuntimeSourceSpec(
        item_id="dbsnp_local_adapter",
        source_id=DBSNP_SOURCE_ID,
        adapter="DbSnpLocalStore / pysam TabixFile",
        roles=(
            LocalEvidenceRuntimeAssetRole(
                role="dbsnp_bgzip_vcf",
                path_setting="dbsnp_runtime_vcf_path",
                expected_format="bgzip_vcf",
            ),
            LocalEvidenceRuntimeAssetRole(
                role="dbsnp_tabix_index",
                path_setting="dbsnp_runtime_index_path",
                expected_format="tabix_tbi",
            ),
        ),
        freshness_policy=LocalEvidenceFreshnessPolicy(tier="static", sla_days=None),
        fixture_paths=(DEFAULT_DBSNP_VCF_FIXTURE_PATH,),
    ),
    LocalEvidenceRuntimeSourceSpec(
        item_id="clinvar_local_adapter",
        source_id=CLINVAR_SOURCE_ID,
        adapter="ClinVarLocalStore / pysam TabixFile",
        roles=(
            LocalEvidenceRuntimeAssetRole(
                role="clinvar_bgzip_vcf",
                path_setting="clinvar_runtime_vcf_path",
                expected_format="bgzip_vcf",
            ),
            LocalEvidenceRuntimeAssetRole(
                role="clinvar_tabix_index",
                path_setting="clinvar_runtime_index_path",
                expected_format="tabix_tbi",
            ),
        ),
        freshness_policy=LocalEvidenceFreshnessPolicy(
            tier="volatile",
            sla_days=8,
            overdue_days=15,
        ),
        fixture_paths=(DEFAULT_CLINVAR_VCF_FIXTURE_PATH,),
    ),
    LocalEvidenceRuntimeSourceSpec(
        item_id="repeatmasker_local_adapter",
        source_id=REPEATMASKER_SOURCE_ID,
        adapter="RepeatMaskerLocalStore compact interval index",
        roles=(
            LocalEvidenceRuntimeAssetRole(
                role="repeatmasker_compact_interval_index",
                path_setting="repeatmasker_runtime_index_path",
                expected_format="compact_interval_index",
            ),
        ),
        freshness_policy=LocalEvidenceFreshnessPolicy(tier="static", sla_days=None),
        fixture_paths=(DEFAULT_REPEATMASKER_FIXTURE_PATH,),
    ),
    LocalEvidenceRuntimeSourceSpec(
        item_id="phylop_conservation_reader",
        source_id=PHYLOP_SOURCE_ID,
        adapter="PyBigWigConservationReader",
        roles=(
            LocalEvidenceRuntimeAssetRole(
                role="phylop_bigwig",
                path_setting="phylop_runtime_bigwig_path",
                expected_format="bigwig",
            ),
        ),
        freshness_policy=LocalEvidenceFreshnessPolicy(tier="static", sla_days=None),
    ),
)


def inspect_local_evidence_runtime_assets(
    settings: Settings,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    inspected_at = _as_utc(now or datetime.now(timezone.utc))
    sources = [
        _inspect_source(settings, spec, inspected_at)
        for spec in LOCAL_EVIDENCE_RUNTIME_SOURCE_SPECS
    ]
    ready_sources = [source for source in sources if source["ready"]]
    return {
        "mode": "local_evidence_runtime_assets",
        "ready": len(ready_sources) == len(sources),
        "ready_count": len(ready_sources),
        "total_sources": len(sources),
        "sources": sources,
        "startup_download_allowed": False,
        "request_time_materialization_allowed": False,
        "source_runtime_scan_allowed": False,
        "runtime_reader_opened": False,
        "secret_values_emitted": False,
        "local_path_values_emitted": False,
        "object_uri_values_emitted": False,
        "preflight_wires_runtime": False,
    }


def _inspect_source(
    settings: Settings,
    spec: LocalEvidenceRuntimeSourceSpec,
    inspected_at: datetime,
) -> dict[str, Any]:
    assets = [
        _inspect_role(settings, role, spec.freshness_policy, inspected_at) for role in spec.roles
    ]
    fixture_roles = [
        asset["role"]
        for asset in assets
        if _is_fixture_path(Path(getattr(settings, asset["path_setting"])), spec.fixture_paths)
    ]
    missing_roles = [asset["role"] for asset in assets if asset["status"] == "missing"]
    invalid_roles = [asset["role"] for asset in assets if asset["status"] == "not_file"]
    ready = not fixture_roles and not missing_roles and not invalid_roles
    if fixture_roles:
        status = "fixture_path_configured"
    elif invalid_roles:
        status = "runtime_path_not_file"
    elif missing_roles:
        status = "missing_runtime_file"
    else:
        status = "ready"
    return {
        "item_id": spec.item_id,
        "source_id": spec.source_id,
        "adapter": spec.adapter,
        "status": status,
        "ready": ready,
        "asset_count": len(assets),
        "ready_asset_count": sum(1 for asset in assets if asset["ready"]),
        "missing_roles": missing_roles,
        "fixture_roles": fixture_roles,
        "invalid_roles": invalid_roles,
        "freshness": _combine_asset_freshnesses(assets, spec.freshness_policy, inspected_at),
        "assets": assets,
        "reader_requires_local_path": True,
        "runtime_wired": True,
        "startup_download_allowed": False,
        "request_time_materialization_allowed": False,
        "source_runtime_scan_allowed": False,
        "fixture_default_used": bool(fixture_roles),
        "secret_values_emitted": False,
        "local_path_values_emitted": False,
        "object_uri_values_emitted": False,
    }


def _inspect_role(
    settings: Settings,
    role: LocalEvidenceRuntimeAssetRole,
    freshness_policy: LocalEvidenceFreshnessPolicy,
    inspected_at: datetime,
) -> dict[str, Any]:
    raw_path = Path(getattr(settings, role.path_setting))
    path = _resolve_backend_path(settings, raw_path)
    try:
        present = path.exists()
        is_file = path.is_file() if present else False
        actual_size_bytes = path.stat().st_size if is_file else None
    except OSError:
        present = False
        is_file = False
        actual_size_bytes = None
    if not present:
        status = "missing"
    elif not is_file:
        status = "not_file"
    else:
        status = "ready"
    return {
        "role": role.role,
        "path_setting": role.path_setting,
        "expected_format": role.expected_format,
        "status": status,
        "ready": status == "ready",
        "present": present,
        "actual_size_bytes": actual_size_bytes,
        "checksum_verified": False,
        "freshness": _freshness_from_manifest(
            path,
            freshness_policy,
            inspected_at,
        ),
    }


def _resolve_backend_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _is_fixture_path(path: Path, fixture_paths: tuple[Path, ...]) -> bool:
    if not fixture_paths:
        return False
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    for fixture_path in fixture_paths:
        try:
            if resolved == fixture_path.resolve():
                return True
        except OSError:
            if path == fixture_path:
                return True
    return False


def _freshness_from_manifest(
    path: Path,
    policy: LocalEvidenceFreshnessPolicy,
    inspected_at: datetime,
) -> dict[str, Any]:
    manifest = _read_adjacent_manifest(path)
    if manifest is None:
        return _freshness_payload(
            policy,
            inspected_at=inspected_at,
            materialized_at=None,
            upstream_released_at=None,
            upstream_version=None,
            source_version=None,
        )
    source_version = _first_public_text(
        manifest.get("source_version"),
        manifest.get("upstream_version"),
        manifest.get("source_release"),
        manifest.get("release"),
        manifest.get("version"),
    )
    upstream_version = _first_public_text(
        manifest.get("upstream_version"),
        manifest.get("source_version"),
        manifest.get("source_release"),
        manifest.get("release"),
        manifest.get("version"),
    )
    return _freshness_payload(
        policy,
        inspected_at=inspected_at,
        materialized_at=_first_temporal(
            manifest.get("materialized_at"),
            manifest.get("generated_at"),
            manifest.get("created_at"),
            _nested(manifest, "build", "materialized_at"),
        ),
        upstream_released_at=_first_temporal(
            manifest.get("upstream_released_at"),
            manifest.get("source_release_date"),
            manifest.get("release_date"),
            manifest.get("file_date"),
            manifest.get("source_date"),
        ),
        upstream_version=upstream_version,
        source_version=source_version,
    )


def _combine_asset_freshnesses(
    assets: list[dict[str, Any]],
    policy: LocalEvidenceFreshnessPolicy,
    inspected_at: datetime,
) -> dict[str, Any]:
    freshnesses = [
        asset.get("freshness") for asset in assets if isinstance(asset.get("freshness"), dict)
    ]
    return _freshness_payload(
        policy,
        inspected_at=inspected_at,
        materialized_at=_latest_temporal(freshnesses, "materialized_at"),
        upstream_released_at=_latest_temporal(freshnesses, "upstream_released_at"),
        upstream_version=_first_public_text(
            *(freshness.get("upstream_version") for freshness in freshnesses)
        ),
        source_version=_first_public_text(
            *(freshness.get("source_version") for freshness in freshnesses)
        ),
    )


def _freshness_payload(
    policy: LocalEvidenceFreshnessPolicy,
    *,
    inspected_at: datetime,
    materialized_at: str | None,
    upstream_released_at: str | None,
    upstream_version: str | None,
    source_version: str | None,
) -> dict[str, Any]:
    staleness_days = _staleness_days(upstream_released_at, inspected_at)
    return {
        "tier": policy.tier,
        "sla_days": policy.sla_days,
        "status": _freshness_status(policy, upstream_released_at, staleness_days),
        "staleness_days": staleness_days,
        "materialized_at": materialized_at,
        "upstream_released_at": upstream_released_at,
        "upstream_version": upstream_version,
        "source_version": source_version,
    }


def _freshness_status(
    policy: LocalEvidenceFreshnessPolicy,
    upstream_released_at: str | None,
    staleness_days: int | None,
) -> str:
    if upstream_released_at is None or staleness_days is None:
        return "unknown"
    if policy.tier == "static":
        return "fresh"
    if policy.overdue_days is not None and staleness_days > policy.overdue_days:
        return "overdue"
    if policy.sla_days is not None and staleness_days > policy.sla_days:
        return "stale"
    return "fresh"


def _read_adjacent_manifest(path: Path) -> Mapping[str, Any] | None:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    try:
        if not manifest_path.is_file():
            return None
        if manifest_path.stat().st_size > _MANIFEST_SIZE_LIMIT_BYTES:
            return None
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _first_public_text(*values: object) -> str | None:
    for value in values:
        text = _safe_public_text(value)
        if text is not None:
            return text
    return None


def _safe_public_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or len(text) > 240:
        return None
    if any(ord(char) < 32 for char in text):
        return None
    lowered = text.lower()
    if any(marker in lowered for marker in _UNSAFE_PUBLIC_TEXT_MARKERS):
        return None
    return text


def _first_temporal(*values: object) -> str | None:
    for value in values:
        normalized = _normalize_temporal_value(value)
        if normalized is not None:
            return normalized
    return None


def _latest_temporal(items: list[dict[str, Any]], key: str) -> str | None:
    candidates: list[tuple[datetime, str]] = []
    for item in items:
        normalized = _normalize_temporal_value(item.get(key))
        parsed = _parse_temporal_value(normalized)
        if normalized is not None and parsed is not None:
            candidates.append((parsed, normalized))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _normalize_temporal_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "unknown":
        return None
    if text.isdigit() and len(text) == 8:
        text = f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    parsed = _parse_temporal_value(text)
    if parsed is None:
        return None
    if "T" not in text and len(text) == 10:
        return parsed.date().isoformat()
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_temporal_value(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if len(text) == 10:
            return datetime.combine(date.fromisoformat(text), datetime.min.time(), timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _staleness_days(upstream_released_at: str | None, inspected_at: datetime) -> int | None:
    upstream_dt = _parse_temporal_value(upstream_released_at)
    if upstream_dt is None:
        return None
    return max(0, (inspected_at.date() - upstream_dt.date()).days)


def _nested(value: Mapping[str, Any], *keys: str) -> object | None:
    current: object = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
