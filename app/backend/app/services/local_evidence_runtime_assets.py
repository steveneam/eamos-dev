from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
class LocalEvidenceRuntimeSourceSpec:
    item_id: str
    source_id: str
    adapter: str
    roles: tuple[LocalEvidenceRuntimeAssetRole, ...]
    fixture_paths: tuple[Path, ...] = ()


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
    ),
)


def inspect_local_evidence_runtime_assets(settings: Settings) -> dict[str, Any]:
    sources = [_inspect_source(settings, spec) for spec in LOCAL_EVIDENCE_RUNTIME_SOURCE_SPECS]
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


def _inspect_source(settings: Settings, spec: LocalEvidenceRuntimeSourceSpec) -> dict[str, Any]:
    assets = [_inspect_role(settings, role) for role in spec.roles]
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


def _inspect_role(settings: Settings, role: LocalEvidenceRuntimeAssetRole) -> dict[str, Any]:
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
