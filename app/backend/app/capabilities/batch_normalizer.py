from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.capabilities.errors import RuntimeCompositionError
from app.core.config import Settings
from app.services.batch_engine import (
    BatchAlleleNormalizer,
    BcftoolsBatchNormalizer,
    UnavailableBatchNormalizer,
)

# The licence the approved W3-BCF-01 build target carries. Reported while no
# manifest is mounted so a gated capability still states its real terms.
APPROVED_BCFTOOLS_LICENSE_SPDX = "MIT"


class _ManifestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BcftoolsBinaryManifestV1(_ManifestModel):
    path: str = Field(min_length=1, max_length=512)
    version: str = Field(min_length=1, max_length=128)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    # bcftools is dual-licensed: MIT/Expat, or GPL-3.0-or-later once GSL is
    # linked for `polysomy`. The licence is therefore a property of the build,
    # not of the project, so the manifest records which one this binary carries.
    # W3-BCF-01 approves the GSL-disabled MIT/Expat build.
    license_spdx: Literal["MIT", "GPL-3.0-or-later"] = "MIT"


class Grch38ReferenceManifestV1(_ManifestModel):
    path: str = Field(min_length=1, max_length=512)
    fai_path: str = Field(min_length=1, max_length=512)
    release: str = Field(min_length=1, max_length=128)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    fai_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    source_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )


class BatchNormalizerManifestV1(_ManifestModel):
    schema_version: Literal["batch_normalizer_manifest.v1"]
    approval_status: Literal["approved"]
    manifest_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )
    bcftools: BcftoolsBinaryManifestV1
    reference: Grch38ReferenceManifestV1
    validation_matrix_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._~-]*$",
    )


@dataclass(frozen=True)
class BatchNormalizerRuntime:
    normalizer: BatchAlleleNormalizer
    status: Literal["ready", "unavailable"]
    manifest_id: str | None
    manifest_sha256: str | None
    binary_version: str | None
    binary_sha256: str | None
    binary_license_spdx: str
    reference_release: str
    reference_sha256: str | None
    validation_matrix_id: str | None
    requirements: tuple[str, ...]


def build_batch_normalizer(settings: Settings) -> BatchNormalizerRuntime:
    manifest_path = settings.batch_normalizer_manifest_path
    manifest_digest = settings.batch_normalizer_manifest_sha256
    if manifest_path is None and manifest_digest is None:
        normalizer = UnavailableBatchNormalizer()
        return BatchNormalizerRuntime(
            normalizer=normalizer,
            status="unavailable",
            manifest_id=None,
            manifest_sha256=None,
            binary_version=None,
            binary_sha256=None,
            binary_license_spdx=APPROVED_BCFTOOLS_LICENSE_SPDX,
            reference_release=normalizer.reference_release,
            reference_sha256=None,
            validation_matrix_id=None,
            requirements=normalizer.requirements,
        )
    if manifest_path is None or manifest_digest is None:
        raise RuntimeCompositionError("batch_normalizer_manifest_config_incomplete")

    resolved_manifest = _resolve_from_backend(settings, manifest_path)
    raw_manifest = _read_bounded_json(resolved_manifest, max_bytes=64_000)
    actual_manifest_digest = sha256(raw_manifest).hexdigest()
    if actual_manifest_digest != manifest_digest.lower():
        raise RuntimeCompositionError("batch_normalizer_manifest_digest_mismatch")
    try:
        manifest = BatchNormalizerManifestV1.model_validate(json.loads(raw_manifest))
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeCompositionError("batch_normalizer_manifest_invalid") from exc

    binary_path = _resolve_from_manifest(resolved_manifest, manifest.bcftools.path)
    reference_path = _resolve_from_manifest(resolved_manifest, manifest.reference.path)
    reference_fai_path = _resolve_from_manifest(resolved_manifest, manifest.reference.fai_path)
    if reference_fai_path != Path(f"{reference_path}.fai"):
        raise RuntimeCompositionError("batch_normalizer_reference_index_path_invalid")
    _verify_executable(binary_path, manifest.bcftools.sha256)
    _verify_file(reference_path, manifest.reference.sha256, "batch_normalizer_reference")
    _verify_file(reference_fai_path, manifest.reference.fai_sha256, "batch_normalizer_index")
    _verify_bcftools_version(binary_path, manifest.bcftools.version)

    try:
        normalizer = BcftoolsBatchNormalizer(
            executable=binary_path,
            reference_fasta=reference_path,
            reference_release=manifest.reference.release,
            reference_manifest_id=manifest.manifest_id,
            reference_sha256=manifest.reference.sha256,
            algorithm_version=manifest.bcftools.version,
            validation_matrix_id=manifest.validation_matrix_id,
            timeout_seconds=settings.batch_normalizer_timeout_seconds,
            verify_reference_digest=False,
        )
    except Exception as exc:
        raise RuntimeCompositionError("batch_normalizer_initialization_failed") from exc
    return BatchNormalizerRuntime(
        normalizer=normalizer,
        status="ready",
        manifest_id=manifest.manifest_id,
        manifest_sha256=actual_manifest_digest,
        binary_version=manifest.bcftools.version,
        binary_sha256=manifest.bcftools.sha256.lower(),
        binary_license_spdx=manifest.bcftools.license_spdx,
        reference_release=manifest.reference.release,
        reference_sha256=manifest.reference.sha256.lower(),
        validation_matrix_id=manifest.validation_matrix_id,
        requirements=(),
    )


def _resolve_from_backend(settings: Settings, path: Path) -> Path:
    return (path if path.is_absolute() else settings.backend_root / path).resolve()


def _resolve_from_manifest(manifest_path: Path, value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else manifest_path.parent / path).resolve()


def _read_bounded_json(path: Path, *, max_bytes: int) -> bytes:
    try:
        if not path.is_file() or path.stat().st_size > max_bytes:
            raise RuntimeCompositionError("batch_normalizer_manifest_missing_or_oversized")
        return path.read_bytes()
    except OSError as exc:
        raise RuntimeCompositionError("batch_normalizer_manifest_unreadable") from exc


def _verify_file(path: Path, expected_sha256: str, code_prefix: str) -> None:
    if not path.is_file():
        raise RuntimeCompositionError(f"{code_prefix}_missing")
    if _sha256_file(path) != expected_sha256.lower():
        raise RuntimeCompositionError(f"{code_prefix}_digest_mismatch")


def _verify_executable(path: Path, expected_sha256: str) -> None:
    _verify_file(path, expected_sha256, "batch_normalizer_binary")
    if not os.access(path, os.X_OK):
        raise RuntimeCompositionError("batch_normalizer_binary_not_executable")


def _verify_bcftools_version(path: Path, expected_version: str) -> None:
    try:
        completed = subprocess.run(
            [str(path), "--version"],
            cwd=path.parent,
            env={"LC_ALL": "C", "LANG": "C", "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            check=False,
            timeout=5.0,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeCompositionError("batch_normalizer_binary_probe_failed") from exc
    first_line = (completed.stdout or "").splitlines()[:1]
    if completed.returncode != 0 or not first_line:
        raise RuntimeCompositionError("batch_normalizer_binary_probe_failed")
    tokens = first_line[0].strip().split()
    if len(tokens) < 2 or tokens[0] != "bcftools" or tokens[1] != expected_version:
        raise RuntimeCompositionError("batch_normalizer_binary_version_mismatch")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
