from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.capabilities.batch_normalizer import build_batch_normalizer
from app.capabilities.build_inventory import build_inventory
from app.capabilities.composition import _batch_normalizer_components
from app.capabilities.errors import RuntimeCompositionError
from app.core.config import Settings
from app.main import create_app
from app.services.batch_engine import BcftoolsBatchNormalizer, SnapshotCursorCodec

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "upload_dir": tmp_path / "uploads",
        "final_report_dir": tmp_path / "reports",
        "database_url": f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        "jwt_secret": "runtime-composition-test-secret",
        "llm_provider": "mock",
        "use_real_apis": False,
        "workbench_live_design_enabled": False,
        "supabase_local_model_cache_enabled": False,
        "supabase_local_model_cache_database_url": None,
        "supabase_url": None,
        "supabase_service_role_key": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_batch_cursor_key_is_restart_stable_and_domain_separated(tmp_path: Path) -> None:
    first = _settings(tmp_path / "first")
    second = _settings(tmp_path / "second")
    other = _settings(tmp_path / "other", jwt_secret="different-runtime-secret")

    encoded = SnapshotCursorCodec(first.batch_cursor_secret).encode(
        snapshot_id="batch-snapshot-stable",
        offset=321,
    )

    assert (
        SnapshotCursorCodec(second.batch_cursor_secret).decode(
            encoded,
            snapshot_id="batch-snapshot-stable",
        )
        == 321
    )
    with pytest.raises(ValueError, match="cursor is invalid"):
        SnapshotCursorCodec(other.batch_cursor_secret).decode(
            encoded,
            snapshot_id="batch-snapshot-stable",
        )
    assert first.batch_cursor_secret != first.jwt_secret.encode()


def test_runtime_composition_injects_direct_lookup_before_serving(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))

    assert app.state.batch_service.lookup_service is None
    with TestClient(app) as client:
        assert app.state.batch_service.lookup_service is app.state.lookup_service
        response = client.get("/api/v1/health/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "runtime_capability_registry.v1"
    assert body["core_services_ready"] is True
    assert body["policy"] == {
        "startup_downloads_allowed": False,
        "request_time_installs_allowed": False,
        "host_binary_autodiscovery_allowed": False,
        "raw_paths_emitted": False,
        "secret_values_emitted": False,
    }
    components = {item["component_id"]: item for item in body["components"]}
    assert components["service.direct_lookup"]["status"] == "ready"
    assert components["service.batch_cursor_signing"]["status"] == "ready"
    assert components["binary.bcftools"]["status"] == "unavailable"
    # A gated capability still states the terms of the build W3-BCF-01 approves:
    # the GSL-disabled MIT/Expat one, never a blanket GPL claim.
    assert components["binary.bcftools"]["license_spdx"] == "MIT"
    assert components["binary.bcftools"]["license_posture"] == "permissive"
    assert components["binary.bcftools"]["notice_ids"] == [
        "bcftools-mit",
        "htslib-mit-bsd",
    ]
    assert components["material.grch38_batch_reference"]["status"] == "unavailable"
    assert components["python.primer3"]["pinned_version"] == "2.3.0"
    assert components["python.biopython"]["pinned_version"] == "1.87"
    assert components["python.pysam"]["pinned_version"] == "0.24.0"
    assert components["python.pypdfium2"]["pinned_version"] == "5.12.1"
    assert components["python.pypdf"]["pinned_version"] == "6.14.2"
    assert components["isolation.paper_pdf_worker"]["status"] == "ready"
    assert components["isolation.paper_pdf_worker"]["probe"]["status"] == "passed"
    serialized = response.text
    assert "runtime-composition-test-secret" not in serialized
    assert str(tmp_path) not in serialized


def test_unconfigured_batch_normalizer_is_typed_unavailable(tmp_path: Path) -> None:
    runtime = build_batch_normalizer(_settings(tmp_path))

    assert runtime.status == "unavailable"
    disclosure = runtime.normalizer.disclosure()
    assert disclosure.execution == "unavailable"
    assert disclosure.source_status == "unavailable"
    assert disclosure.requirements


def test_incomplete_or_tampered_normalizer_manifest_fails_startup(tmp_path: Path) -> None:
    with pytest.raises(
        RuntimeCompositionError,
        match="batch_normalizer_manifest_config_incomplete",
    ):
        build_batch_normalizer(
            _settings(
                tmp_path / "incomplete",
                batch_normalizer_manifest_path=tmp_path / "manifest.json",
            )
        )

    manifest_path = tmp_path / "tampered.json"
    manifest_path.write_text("{}", encoding="utf-8")
    with pytest.raises(
        RuntimeCompositionError,
        match="batch_normalizer_manifest_digest_mismatch",
    ):
        build_batch_normalizer(
            _settings(
                tmp_path / "tampered",
                batch_normalizer_manifest_path=manifest_path,
                batch_normalizer_manifest_sha256="0" * 64,
            )
        )


def test_approved_immutable_normalizer_manifest_constructs_adapter(tmp_path: Path) -> None:
    executable = tmp_path / "bcftools"
    executable.write_text("#!/bin/sh\nprintf 'bcftools 1.20\\n'\n", encoding="utf-8")
    executable.chmod(0o700)
    reference = tmp_path / "GRCh38.fa"
    reference.write_text(">1\nACGTACGT\n", encoding="ascii")
    reference_index = tmp_path / "GRCh38.fa.fai"
    reference_index.write_text("1\t8\t3\t8\t9\n", encoding="ascii")
    manifest = {
        "schema_version": "batch_normalizer_manifest.v1",
        "approval_status": "approved",
        "manifest_id": "grch38-bcftools-test-v1",
        "bcftools": {
            "path": executable.name,
            "version": "1.20",
            "sha256": _digest(executable),
            "license_spdx": "MIT",
        },
        "reference": {
            "path": reference.name,
            "fai_path": reference_index.name,
            "release": "GRCh38.test",
            "sha256": _digest(reference),
            "fai_sha256": _digest(reference_index),
            "source_id": "grch38-test",
        },
        "validation_matrix_id": "batch-normalizer-test-v1",
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    runtime = build_batch_normalizer(
        _settings(
            tmp_path / "runtime",
            batch_normalizer_manifest_path=manifest_path,
            batch_normalizer_manifest_sha256=_digest(manifest_path),
        )
    )

    assert runtime.status == "ready"
    assert isinstance(runtime.normalizer, BcftoolsBatchNormalizer)
    assert runtime.manifest_id == "grch38-bcftools-test-v1"
    assert runtime.binary_version == "1.20"
    assert runtime.binary_license_spdx == "MIT"
    assert runtime.reference_release == "GRCh38.test"
    assert runtime.normalizer.disclosure().validation_status == "validated"

    components = {item.component_id: item for item in _batch_normalizer_components(runtime)}
    bcftools = components["binary.bcftools"]
    assert bcftools.license_spdx == "MIT"
    assert bcftools.license_posture == "permissive"
    assert bcftools.notice_ids == ["bcftools-mit", "htslib-mit-bsd"]


def test_gsl_linked_normalizer_build_reports_copyleft_review(tmp_path: Path) -> None:
    """A GPL-3.0 build must still disclose copyleft, not inherit the MIT default."""
    executable = tmp_path / "bcftools"
    executable.write_text("#!/bin/sh\nprintf 'bcftools 1.20\\n'\n", encoding="utf-8")
    executable.chmod(0o700)
    reference = tmp_path / "GRCh38.fa"
    reference.write_text(">1\nACGTACGT\n", encoding="ascii")
    reference_index = tmp_path / "GRCh38.fa.fai"
    reference_index.write_text("1\t8\t3\t8\t9\n", encoding="ascii")
    manifest = {
        "schema_version": "batch_normalizer_manifest.v1",
        "approval_status": "approved",
        "manifest_id": "grch38-bcftools-gsl-v1",
        "bcftools": {
            "path": executable.name,
            "version": "1.20",
            "sha256": _digest(executable),
            "license_spdx": "GPL-3.0-or-later",
        },
        "reference": {
            "path": reference.name,
            "fai_path": reference_index.name,
            "release": "GRCh38.test",
            "sha256": _digest(reference),
            "fai_sha256": _digest(reference_index),
            "source_id": "grch38-test",
        },
        "validation_matrix_id": "batch-normalizer-test-v1",
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    runtime = build_batch_normalizer(
        _settings(
            tmp_path / "runtime",
            batch_normalizer_manifest_path=manifest_path,
            batch_normalizer_manifest_sha256=_digest(manifest_path),
        )
    )

    assert runtime.binary_license_spdx == "GPL-3.0-or-later"
    components = {item.component_id: item for item in _batch_normalizer_components(runtime)}
    bcftools = components["binary.bcftools"]
    assert bcftools.license_spdx == "GPL-3.0-or-later"
    assert bcftools.license_posture == "copyleft_review_required"
    assert bcftools.notice_ids == ["bcftools-gpl3"]


def test_container_contract_pins_base_binary_and_build_inventory() -> None:
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text(encoding="utf-8")
    requirements = (BACKEND_ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert (
        "FROM python:3.12.13-slim-bookworm@sha256:"
        "d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b"
    ) in dockerfile
    assert "hmmer=3.3.2+dfsg-1" in dockerfile
    assert "python -m app.capabilities.build_inventory" in dockerfile
    assert "RUNTIME_BUILD_INVENTORY_PATH=/app/runtime-component-inventory.json" in dockerfile
    for requirement in (
        "primer3-py==2.3.0",
        "biopython==1.87",
        "pysam==0.24.0",
        "pypdfium2==5.12.1",
        "pypdf==6.14.2",
    ):
        assert requirement in requirements

    inventory = build_inventory()
    packages = {item["name"].lower(): item for item in inventory["packages"]}
    pdfium_notices = packages["pypdfium2"]["notice_files"]
    assert any(value.endswith("LICENSES/Apache-2.0.txt") for value in pdfium_notices)
    assert any("BUILD_LICENSES/pdfium.txt" in value for value in pdfium_notices)
    assert inventory["measurement"]["runtime_payload_size_bytes"] > 0


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
