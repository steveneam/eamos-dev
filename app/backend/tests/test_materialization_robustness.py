from __future__ import annotations

import hashlib
import json

from app.core.config import Settings
from app.services.materialization_orchestrator import materialize_all_from_manifest


class FakeMaterializationStore:
    def __init__(self) -> None:
        self.objects: list[dict] = []
        self.materializations: list[dict] = []

    def upsert_source_asset_object(self, **kwargs) -> str:
        self.objects.append(kwargs)
        return "source-asset-object-1"

    def upsert_source_asset_materialization(self, **kwargs) -> None:
        self.materializations.append(kwargs)


def test_render_defaults_runtime_paths_to_var_data(monkeypatch) -> None:
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-test")
    monkeypatch.delenv("DBSNP_RUNTIME_VCF_PATH", raising=False)

    settings = Settings(jwt_secret="test-secret")

    assert settings.dbsnp_runtime_vcf_path.as_posix() == (
        "/var/data/eamos/bio_assets/dbsnp/GCF_000001405.40.gz"
    )
    assert settings.clinvar_runtime_index_path.as_posix() == (
        "/var/data/eamos/bio_assets/clinvar/clinvar.vcf.gz.tbi"
    )
    assert settings.repeatmasker_runtime_index_path.as_posix() == (
        "/var/data/eamos/bio_assets/repeatmasker/repeatmasker.interval-index.jsonl"
    )
    assert settings.local_evidence_enabled is False
    assert settings.llm_provider == "mock"


def test_render_defaults_respect_explicit_runtime_env(monkeypatch, tmp_path) -> None:
    explicit = tmp_path / "custom-dbsnp.vcf.gz"
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-test")
    monkeypatch.setenv("DBSNP_RUNTIME_VCF_PATH", str(explicit))

    settings = Settings(jwt_secret="test-secret")

    assert settings.dbsnp_runtime_vcf_path == explicit


def test_materialize_all_local_item_reconciles_metadata_without_path_leak(tmp_path) -> None:
    payload = b"tiny-phylop"
    source = tmp_path / "source" / "hg38.phyloP100way.bw"
    destination = tmp_path / "runtime" / "hg38.phyloP100way.bw"
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)
    manifest_path = _manifest_path(
        tmp_path,
        source=source,
        destination=destination,
        payload=payload,
    )
    store = FakeMaterializationStore()

    report = materialize_all_from_manifest(
        Settings(jwt_secret="test-secret"),
        manifest_path=manifest_path,
        materialization_store=store,
    )

    assert report["ready"] is True
    assert report["counts"]["metadata_reconciled_count"] == 1
    assert destination.read_bytes() == payload
    assert store.objects[0]["source_id"] == "ucsc_phylop100way_hg38"
    assert store.objects[0]["asset_role"] == "phylop_bigwig"
    assert store.materializations[0]["materialization_status"] == "ready"
    assert store.materializations[0]["fail_closed_reason"] is None
    encoded = json.dumps(report).lower()
    assert str(tmp_path).lower() not in encoded
    assert "supabase://" not in encoded


def test_admin_materialization_route_requires_token_and_runs_sanitized(
    auth_client,
    tmp_path,
) -> None:
    payload = b"tiny-phylop"
    source = tmp_path / "source" / "hg38.phyloP100way.bw"
    destination = tmp_path / "runtime" / "hg38.phyloP100way.bw"
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)
    manifest_path = _manifest_path(
        tmp_path,
        source=source,
        destination=destination,
        payload=payload,
    )
    token = "admin-materialize-test-token"
    settings = auth_client.app.state.settings
    settings.admin_materialization_enabled = True
    settings.admin_materialization_token_sha256 = hashlib.sha256(token.encode()).hexdigest()
    settings.admin_materialization_manifest_path = manifest_path

    forbidden = auth_client.post(
        "/api/v1/admin/materialization/run",
        json={"download_mode": "s3_multipart"},
        headers={"X-Eamos-Admin-Token": "wrong"},
    )
    assert forbidden.status_code == 403

    response = auth_client.post(
        "/api/v1/admin/materialization/run",
        json={"download_mode": "s3_multipart"},
        headers={"X-Eamos-Admin-Token": token},
    )

    assert response.status_code == 200
    output = response.json()
    assert output["ready"] is True
    assert output["items"][0]["status"] == "ready"
    assert destination.read_bytes() == payload
    encoded = json.dumps(output).lower()
    assert str(tmp_path).lower() not in encoded
    assert "supabase://" not in encoded
    assert token not in encoded


def _manifest_path(tmp_path, *, source, destination, payload: bytes):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "eamos.materialization_manifest.v1",
                "manifest_id": "pytest-materialization",
                "environment": "pytest",
                "backend_runtime": "test_backend",
                "items": [
                    {
                        "item_id": "phylop_bigwig",
                        "kind": "local_evidence_runtime_asset",
                        "source_id": "ucsc_phylop100way_hg38",
                        "asset_id": "ucsc_hg38_phylop100way_bw",
                        "role": "phylop_bigwig",
                        "bucket_id": "eamos-source-assets",
                        "object_path": "ucsc_phylop100way_hg38/test/hg38.phyloP100way.bw",
                        "source_artifact_path": str(source),
                        "destination_path": str(destination),
                        "env_var": "PHYLOP_RUNTIME_BIGWIG_PATH",
                        "byte_size": len(payload),
                        "md5": hashlib.md5(payload).hexdigest(),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "license_status": "public_allowed_after_terms_review",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path
