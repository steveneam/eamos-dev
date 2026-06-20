from __future__ import annotations

import json

import pytest

from app.cli import eamos_source_import
from app.core.config import Settings
from app.services.derived_runtime_artifacts import build_repeatmasker_compact_upload_item
from app.services.indexed_sources import REPEATMASKER_COMPACT_INDEX_SCHEMA
from app.services.source_imports import (
    CLINVAR_EXISTING_OBJECTS_ID,
    CLINVAR_STORAGE_PILOT_ID,
    DBSNP_PHYLOP_EXISTING_OBJECTS_ID,
    HG38_STORAGE_PILOT_ID,
    REPEATMASKER_COMPACT_EXISTING_OBJECTS_ID,
    REPEATMASKER_EXISTING_OBJECTS_ID,
    SourceImportError,
    apply_clinical_source_import_bundle,
    apply_existing_source_asset_metadata_registration,
    apply_storage_pilot_registration,
    build_clinical_source_import_bundle,
    build_clinical_release_source_import_bundle,
    build_existing_source_asset_metadata_registration,
    build_storage_pilot_registration,
    clinical_bundle_report,
    existing_source_asset_metadata_report,
    storage_pilot_report,
)
from app.services.source_storage_uploads import build_source_storage_upload_items


class FakeSourceImportStore:
    def __init__(self) -> None:
        self.source_versions: list[dict] = []
        self.clinical_rows: dict = {}
        self.source_asset_objects: list[dict] = []
        self.source_asset_materializations: list[dict] = []
        self.smoke_count = 0

    def smoke_test(self) -> None:
        self.smoke_count += 1

    def record_source_version(self, **kwargs) -> str:
        self.source_versions.append(kwargs)
        return f"source-version-{len(self.source_versions)}"

    def upsert_clinical_source_records(self, **kwargs) -> dict[str, int]:
        self.clinical_rows = kwargs
        return {
            "clinical_mondo_diseases": len(kwargs["mondo_rows"]),
            "clinical_hpo_terms": len(kwargs["hpo_term_rows"]),
            "clinical_hpo_disease_phenotypes": len(kwargs["hpo_disease_rows"]),
            "clinical_hpo_gene_phenotypes": len(kwargs["hpo_gene_rows"]),
            "clinical_clingen_gene_validity": len(kwargs["clingen_rows"]),
            "clinical_gencc_assertions": len(kwargs["gencc_rows"]),
        }

    def upsert_source_asset_object(self, **kwargs) -> str:
        self.source_asset_objects.append(kwargs)
        return "source-asset-object-1"

    def upsert_source_asset_materialization(self, **kwargs) -> None:
        self.source_asset_materializations.append(kwargs)


class FakeSocket:
    def __enter__(self) -> FakeSocket:
        return self

    def __exit__(self, *args) -> None:
        return None


def test_clinical_source_import_bundle_plans_fixture_rows_and_versions() -> None:
    bundle = build_clinical_source_import_bundle()
    report = clinical_bundle_report(bundle)

    assert bundle.import_scope == "dev_fixture"
    assert bundle.row_counts == {
        "clinical_mondo_diseases": 2,
        "clinical_hpo_terms": 3,
        "clinical_hpo_disease_phenotypes": 2,
        "clinical_hpo_gene_phenotypes": 3,
        "clinical_clingen_gene_validity": 2,
        "clinical_gencc_assertions": 2,
    }
    assert len(bundle.source_versions) == 6
    assert {version.source_id for version in bundle.source_versions} == {
        "mondo_disease_ontology",
        "human_phenotype_ontology",
        "clingen_gene_validity",
        "gencc_download",
    }
    assert report["guardrails"]["production_downloads"] == "not_used"
    assert report["guardrails"]["frontend_direct_sql"] == "blocked"


def test_clinical_release_source_import_bundle_uses_staged_release_paths(tmp_path) -> None:
    root = _clinical_release_asset_root(tmp_path)

    bundle = build_clinical_release_source_import_bundle(
        source_asset_root=root,
        source_version_overrides={
            "mondo_disease_ontology": "MONDO pytest release",
            "human_phenotype_ontology": "HPO pytest release",
            "clingen_gene_validity": "ClinGen pytest export",
            "gencc_download": "GenCC pytest export",
        },
    )
    report = clinical_bundle_report(bundle)

    assert bundle.import_scope == "release_files"
    assert bundle.asset_role == "tier3_clinical_source_release_file"
    assert bundle.row_counts == {
        "clinical_mondo_diseases": 1,
        "clinical_hpo_terms": 1,
        "clinical_hpo_disease_phenotypes": 1,
        "clinical_hpo_gene_phenotypes": 1,
        "clinical_clingen_gene_validity": 1,
        "clinical_gencc_assertions": 1,
    }
    assert {version.asset_role for version in bundle.source_versions} == {
        "tier3_clinical_source_release_file"
    }
    assert {version.metadata["import_scope"] for version in bundle.source_versions} == {
        "release_files"
    }
    assert {version.metadata["production_download_used"] for version in bundle.source_versions} == {
        True
    }
    assert {version.source_id: version.source_release for version in bundle.source_versions} == {
        "mondo_disease_ontology": "MONDO pytest release",
        "human_phenotype_ontology": "HPO pytest release",
        "clingen_gene_validity": "ClinGen pytest export",
        "gencc_download": "GenCC pytest export",
    }
    assert report["mode"] == "tier3_clinical_source_release_files_import"
    assert report["guardrails"]["storage_uploads"] == "not_used"


def test_clinical_source_import_apply_records_source_versions_and_idempotent_rows() -> None:
    store = FakeSourceImportStore()
    bundle = build_clinical_source_import_bundle()

    result = apply_clinical_source_import_bundle(store, bundle)

    assert result.applied is True
    assert len(store.source_versions) == 6
    assert result.row_counts["clinical_hpo_terms"] == 3
    assert store.clinical_rows["mondo_rows"][0]["source_version_id"] == "source-version-1"
    assert store.clinical_rows["mondo_rows"][0]["mondo_id"] == "MONDO:0008765"
    assert store.clinical_rows["hpo_disease_rows"][0]["source_version_id"] is not None
    assert store.clinical_rows["clingen_rows"][0]["classification"] == "Definitive"
    assert store.clinical_rows["gencc_rows"][0]["submitter"] == "ClinGen"


def test_hg38_storage_pilot_is_metadata_only_and_private() -> None:
    pilot = build_storage_pilot_registration(pilot_id=HG38_STORAGE_PILOT_ID)
    report = storage_pilot_report(pilot)

    assert pilot.object.source_id == "ucsc_hg38_2bit"
    assert pilot.object.bucket_id == "eamos-source-assets"
    assert pilot.object.object_path.startswith("ucsc_hg38_2bit/hg38/md5-")
    assert pilot.object.object_path.endswith("/hg38.2bit")
    assert pilot.object.upload_status == "metadata_only"
    assert pilot.object.approval_status == "pending_storage_approval"
    assert pilot.object.metadata["frontend_direct_access_allowed"] is False
    assert "storage_object_not_uploaded" in pilot.object.warnings
    assert pilot.materialization.materialization_status == "not_materialized"
    assert pilot.materialization.fail_closed_reason == "private_storage_object_not_uploaded"
    assert report["guardrails"]["public_bucket"] == "blocked"


def test_clinvar_storage_pilot_fails_until_checksum_is_recorded() -> None:
    with pytest.raises(SourceImportError) as exc_info:
        build_storage_pilot_registration(pilot_id=CLINVAR_STORAGE_PILOT_ID)

    assert exc_info.value.code == "storage_pilot_checksum_unavailable"
    assert exc_info.value.details["source_id"] == "ncbi_clinvar_vcf"


def test_storage_pilot_apply_records_object_and_fail_closed_materialization() -> None:
    store = FakeSourceImportStore()
    pilot = build_storage_pilot_registration()

    result = apply_storage_pilot_registration(store, pilot)

    assert result.applied is True
    assert result.source_version_id == "source-version-1"
    assert result.source_asset_object_id == "source-asset-object-1"
    assert store.source_asset_objects[0]["upload_status"] == "metadata_only"
    assert store.source_asset_objects[0]["metadata"]["frontend_direct_access_allowed"] is False
    assert store.source_asset_materializations[0]["source_asset_object_id"] == (
        "source-asset-object-1"
    )
    assert store.source_asset_materializations[0]["materialization_status"] == "not_materialized"


def test_existing_dbsnp_phylop_metadata_registration_is_private_and_fail_closed(
    tmp_path,
) -> None:
    items = _dbsnp_phylop_upload_items(tmp_path)

    registration = build_existing_source_asset_metadata_registration(
        metadata_set_id=DBSNP_PHYLOP_EXISTING_OBJECTS_ID,
        upload_items=items,
        storage_heads_verified=True,
    )
    report = existing_source_asset_metadata_report(registration)

    assert len(registration.source_versions) == 2
    assert len(registration.objects) == 5
    assert len(registration.materializations) == 5
    by_role = {source_object.asset_role: source_object for source_object in registration.objects}
    assert by_role["dbsnp_bgzip_vcf"].upload_status == "verified"
    assert by_role["dbsnp_bgzip_vcf"].approval_status == "approved"
    assert by_role["dbsnp_bgzip_vcf"].metadata["public_access_allowed"] is False
    assert by_role["dbsnp_bgzip_vcf"].metadata["frontend_direct_access_allowed"] is False
    assert by_role["dbsnp_bgzip_vcf"].checksum_algorithm == "sha256"
    assert by_role["phylop_bigwig"].byte_size == 11
    assert by_role["upstream_checksum"].materialization_required is False
    assert {item.materialization_status for item in registration.materializations} == {
        "not_materialized"
    }
    assert {item.fail_closed_reason for item in registration.materializations} == {
        "render_disk_seed_not_performed"
    }
    dbsnp_materialization = next(
        item
        for item in registration.materializations
        if item.metadata["asset_role"] == "dbsnp_bgzip_vcf"
    )
    assert dbsnp_materialization.metadata["reader_requires_local_path"] is True
    assert "mounted_volume" in dbsnp_materialization.metadata["runtime_delivery_modes"]
    assert report["guardrails"]["render_disk_seed"] == "not_used"
    assert report["guardrails"]["local_evidence_enablement"] == "not_used"


def test_existing_clinvar_metadata_registration_is_private_and_fail_closed(
    tmp_path,
) -> None:
    items = _clinvar_upload_items(tmp_path)

    registration = build_existing_source_asset_metadata_registration(
        metadata_set_id=CLINVAR_EXISTING_OBJECTS_ID,
        upload_items=items,
        storage_heads_verified=True,
    )
    report = existing_source_asset_metadata_report(registration)

    assert len(registration.source_versions) == 1
    assert len(registration.objects) == 3
    assert len(registration.materializations) == 3
    by_role = {source_object.asset_role: source_object for source_object in registration.objects}
    assert by_role["clinvar_bgzip_vcf"].upload_status == "verified"
    assert by_role["clinvar_bgzip_vcf"].approval_status == "approved"
    assert by_role["clinvar_bgzip_vcf"].metadata["public_access_allowed"] is False
    assert by_role["clinvar_tabix_index"].materialization_required is True
    assert by_role["upstream_checksum"].materialization_required is False
    clinvar_materialization = next(
        item
        for item in registration.materializations
        if item.metadata["asset_role"] == "clinvar_bgzip_vcf"
    )
    assert clinvar_materialization.local_cache_path == (
        "/var/data/eamos/bio_assets/clinvar/clinvar.vcf.gz"
    )
    assert clinvar_materialization.fail_closed_reason == "render_disk_seed_not_performed"
    assert clinvar_materialization.metadata["reader_requires_local_path"] is True
    assert "mounted_volume" in clinvar_materialization.metadata["runtime_delivery_modes"]
    assert report["guardrails"]["render_disk_seed"] == "not_used"


def test_existing_repeatmasker_metadata_registration_is_source_only(
    tmp_path,
) -> None:
    items = _repeatmasker_upload_items(tmp_path)

    registration = build_existing_source_asset_metadata_registration(
        metadata_set_id=REPEATMASKER_EXISTING_OBJECTS_ID,
        upload_items=items,
        storage_heads_verified=True,
    )

    assert len(registration.source_versions) == 1
    assert len(registration.objects) == 1
    assert len(registration.materializations) == 1
    source_object = registration.objects[0]
    materialization = registration.materializations[0]
    assert source_object.asset_role == "repeatmasker_source_table"
    assert source_object.materialization_required is False
    assert source_object.upload_status == "verified"
    assert source_object.metadata["public_access_allowed"] is False
    assert materialization.local_cache_path == (
        "source_only://repeatmasker_rmsk_bb/ucsc_hg38_rmsk_txt_gz"
    )
    assert materialization.fail_closed_reason == (
        "runtime_uses_derived_compact_index_not_source_table"
    )
    assert materialization.metadata["reader_requires_local_path"] is False
    assert materialization.metadata["runtime_delivery_modes"] == [
        "offline_compact_index_build_input"
    ]


def test_existing_repeatmasker_compact_metadata_registration_materializes_runtime_index(
    tmp_path,
) -> None:
    item = build_repeatmasker_compact_upload_item(
        source_artifact_path=_repeatmasker_compact_index(tmp_path),
        manifest_staging_root=tmp_path / "manifests",
    )

    registration = build_existing_source_asset_metadata_registration(
        metadata_set_id=REPEATMASKER_COMPACT_EXISTING_OBJECTS_ID,
        upload_items=(item,),
        storage_heads_verified=True,
    )

    assert len(registration.source_versions) == 1
    assert len(registration.objects) == 1
    assert len(registration.materializations) == 1
    source_object = registration.objects[0]
    materialization = registration.materializations[0]
    assert source_object.asset_role == "repeatmasker_compact_interval_index"
    assert source_object.materialization_required is True
    assert source_object.object_path.startswith("generated/repeatmasker_rmsk_bb/")
    assert materialization.local_cache_path == (
        "/var/data/eamos/bio_assets/repeatmasker/repeatmasker.interval-index.jsonl"
    )
    assert materialization.fail_closed_reason == "render_disk_seed_not_performed"
    assert materialization.metadata["reader_requires_local_path"] is True
    assert "mounted_volume" in materialization.metadata["runtime_delivery_modes"]


def test_existing_dbsnp_phylop_metadata_apply_records_objects_and_materializations(
    tmp_path,
) -> None:
    store = FakeSourceImportStore()
    registration = build_existing_source_asset_metadata_registration(
        upload_items=_dbsnp_phylop_upload_items(tmp_path),
        storage_heads_verified=True,
    )

    result = apply_existing_source_asset_metadata_registration(store, registration)

    assert result.applied is True
    assert result.metadata_set_id == DBSNP_PHYLOP_EXISTING_OBJECTS_ID
    assert result.materialization_count == 5
    assert len(store.source_versions) == 2
    assert len(store.source_asset_objects) == 5
    assert len(store.source_asset_materializations) == 5
    assert store.source_asset_objects[0]["upload_status"] == "verified"
    assert store.source_asset_objects[0]["approval_status"] == "approved"
    assert store.source_asset_objects[0]["metadata"]["public_access_allowed"] is False
    assert store.source_asset_materializations[0]["materialization_status"] == "not_materialized"
    assert store.source_asset_materializations[0]["fail_closed_reason"] == (
        "render_disk_seed_not_performed"
    )


def test_source_import_cli_plans_clinical_and_storage_without_supabase(
    capsys,
) -> None:
    exit_code = eamos_source_import.main(["--compact"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "planned"
    assert output["applied"] is False
    assert output["clinical_fixtures"]["row_counts"]["clinical_mondo_diseases"] == 2
    assert output["storage_pilot"]["pilot_id"] == HG38_STORAGE_PILOT_ID
    assert output["guardrails"]["secrets_in_output"] == "blocked"


def test_source_import_cli_plans_clinical_release_files(tmp_path, capsys) -> None:
    root = _clinical_release_asset_root(tmp_path)

    exit_code = eamos_source_import.main(
        [
            "--clinical-release-files",
            "--clinical-source-asset-root",
            str(root),
            "--mondo-source-version",
            "MONDO pytest release",
            "--hpo-source-version",
            "HPO pytest release",
            "--clingen-source-version",
            "ClinGen pytest export",
            "--gencc-source-version",
            "GenCC pytest export",
            "--storage-pilot",
            "none",
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    clinical = output["clinical_fixtures"]
    assert clinical["import_scope"] == "release_files"
    assert clinical["row_counts"]["clinical_mondo_diseases"] == 1
    assert clinical["row_counts"]["clinical_hpo_terms"] == 1
    assert "storage_pilot" not in output


def test_source_import_cli_plans_existing_dbsnp_phylop_metadata(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    items = _dbsnp_phylop_upload_items(tmp_path)
    monkeypatch.setattr(eamos_source_import, "build_source_storage_upload_items", lambda **_: items)

    exit_code = eamos_source_import.main(
        [
            "--skip-clinical-fixtures",
            "--storage-pilot",
            "none",
            "--existing-object-set",
            DBSNP_PHYLOP_EXISTING_OBJECTS_ID,
            "--storage-heads-verified",
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    metadata = output["existing_object_metadata"]
    assert output["status"] == "planned"
    assert metadata["metadata_set_id"] == DBSNP_PHYLOP_EXISTING_OBJECTS_ID
    assert metadata["storage_heads_verified"] is True
    assert len(metadata["objects"]) == 5
    assert metadata["objects"][0]["upload_status"] == "verified"
    assert metadata["materializations"][0]["materialization_status"] == "not_materialized"


def test_source_import_cli_can_verify_existing_storage_heads(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    items = _dbsnp_phylop_upload_items(tmp_path)
    monkeypatch.setattr(eamos_source_import, "build_source_storage_upload_items", lambda **_: items)
    monkeypatch.setattr(
        eamos_source_import,
        "_verify_existing_storage_heads",
        lambda settings, upload_items: True,
    )

    exit_code = eamos_source_import.main(
        [
            "--skip-clinical-fixtures",
            "--storage-pilot",
            "none",
            "--existing-object-set",
            DBSNP_PHYLOP_EXISTING_OBJECTS_ID,
            "--verify-storage-heads",
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    metadata = output["existing_object_metadata"]
    assert metadata["storage_heads_verified"] is True
    assert {item["upload_status"] for item in metadata["objects"]} == {"verified"}


def test_source_import_cli_plans_repeatmasker_compact_metadata(
    tmp_path,
    capsys,
) -> None:
    compact_index = _repeatmasker_compact_index(tmp_path)

    exit_code = eamos_source_import.main(
        [
            "--skip-clinical-fixtures",
            "--storage-pilot",
            "none",
            "--existing-object-set",
            REPEATMASKER_COMPACT_EXISTING_OBJECTS_ID,
            "--repeatmasker-compact-artifact",
            str(compact_index),
            "--storage-heads-verified",
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    metadata = output["existing_object_metadata"]
    assert metadata["metadata_set_id"] == REPEATMASKER_COMPACT_EXISTING_OBJECTS_ID
    assert metadata["objects"][0]["asset_role"] == "repeatmasker_compact_interval_index"
    assert metadata["objects"][0]["upload_status"] == "verified"
    assert metadata["materializations"][0]["materialization_status"] == "not_materialized"
    assert metadata["materializations"][0]["fail_closed_reason"] == (
        "render_disk_seed_not_performed"
    )
    assert str(tmp_path).lower() not in json.dumps(output).lower()


def test_source_import_apply_uses_configured_store_and_smoke(monkeypatch) -> None:
    store = FakeSourceImportStore()
    monkeypatch.setattr(
        eamos_source_import,
        "build_supabase_local_model_cache_store",
        lambda settings: store,
    )

    output = eamos_source_import.build_source_import_report(
        apply_supabase=True,
        check_supabase_tcp=False,
    )

    assert output["status"] == "applied"
    assert store.smoke_count == 1
    assert len(store.source_versions) == 7
    assert (
        output["clinical_fixtures"]["apply_result"]["row_counts"]["clinical_clingen_gene_validity"]
        == 2
    )
    assert output["storage_pilot"]["apply_result"]["source_asset_object_id"] == (
        "source-asset-object-1"
    )


def test_source_import_tcp_preflight_uses_sanitized_host_port(monkeypatch) -> None:
    calls = []

    def fake_create_connection(target, timeout):
        calls.append((target, timeout))
        return FakeSocket()

    monkeypatch.setattr(eamos_source_import.socket, "create_connection", fake_create_connection)

    settings = Settings(
        jwt_secret="test-secret",
        supabase_local_model_cache_enabled=True,
        supabase_local_model_cache_database_url=(
            "postgresql+psycopg://postgres.secret:super-secret"
            "@pooler.example.supabase.co:6543/postgres?sslmode=require"
        ),
    )

    eamos_source_import._check_supabase_database_tcp_reachable(
        settings,
        timeout_seconds=1.25,
    )

    assert calls == [(("pooler.example.supabase.co", 6543), 1.25)]


def test_source_import_tcp_preflight_fails_without_secret_leak(monkeypatch) -> None:
    def fake_create_connection(target, timeout):
        raise TimeoutError("timed out while connecting")

    monkeypatch.setattr(eamos_source_import.socket, "create_connection", fake_create_connection)

    settings = Settings(
        jwt_secret="test-secret",
        supabase_local_model_cache_enabled=True,
        supabase_local_model_cache_database_url=(
            "postgresql+psycopg://postgres.secret:super-secret"
            "@pooler.example.supabase.co:5432/postgres?sslmode=require"
        ),
    )

    with pytest.raises(SourceImportError) as exc_info:
        eamos_source_import._check_supabase_database_tcp_reachable(settings, timeout_seconds=0.1)

    assert exc_info.value.code == "supabase_import_database_unreachable"
    assert exc_info.value.details == {
        "host": "pooler.example.supabase.co",
        "port": 5432,
        "timeout_seconds": 0.1,
        "error_type": "TimeoutError",
    }
    assert "super-secret" not in str(exc_info.value)


def _dbsnp_phylop_upload_items(tmp_path):
    large_root = tmp_path / "large"
    files = {
        "ncbi_dbsnp_gcf_000001405_40/GCF_000001405.40.gz": b"dbsnp-vcf",
        "ncbi_dbsnp_gcf_000001405_40/GCF_000001405.40.gz.tbi": b"dbsnp-tbi",
        "ncbi_dbsnp_gcf_000001405_40/GCF_000001405.40.gz.md5": b"dbsnp-md5",
        "ucsc_phylop100way_hg38/hg38.phyloP100way.bw": b"phylop-bwig",
        "ucsc_phylop100way_hg38/md5sum.txt": b"phylop-md5",
    }
    for relative, payload in files.items():
        path = large_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.with_suffix(path.suffix + ".manifest.json").write_text(
            json.dumps(
                {
                    "md5": "a" * 32,
                    "sha256": f"{len(payload):064x}"[-64:],
                }
            ),
            encoding="utf-8",
        )
    return build_source_storage_upload_items(
        source_ids=(
            "ncbi_dbsnp_gcf_000001405_40",
            "ucsc_phylop100way_hg38",
        ),
        large_staging_root=large_root,
    )


def _clinvar_upload_items(tmp_path):
    root = tmp_path / "source_assets"
    files = {
        "ncbi_clinvar_vcf/clinvar.vcf.gz": b"clinvar-vcf",
        "ncbi_clinvar_vcf/clinvar.vcf.gz.tbi": b"clinvar-tbi",
        "ncbi_clinvar_vcf/clinvar.vcf.gz.md5": b"clinvar-md5",
    }
    for relative, payload in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.with_suffix(path.suffix + ".manifest.json").write_text(
            json.dumps(
                {
                    "md5": "b" * 32,
                    "sha256": f"{len(payload):064x}"[-64:],
                }
            ),
            encoding="utf-8",
        )
    return build_source_storage_upload_items(
        source_ids=("ncbi_clinvar_vcf",),
        small_staging_root=root,
    )


def _repeatmasker_upload_items(tmp_path):
    root = tmp_path / "source_assets"
    path = root / "repeatmasker_rmsk_bb" / "rmsk.txt.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"repeatmasker-source")
    path.with_suffix(path.suffix + ".manifest.json").write_text(
        json.dumps(
            {
                "md5": "c" * 32,
                "sha256": f"{path.stat().st_size:064x}"[-64:],
            }
        ),
        encoding="utf-8",
    )
    return build_source_storage_upload_items(
        source_ids=("repeatmasker_rmsk_bb",),
        small_staging_root=root,
    )


def _repeatmasker_compact_index(tmp_path):
    path = tmp_path / "repeatmasker.interval-index.jsonl"
    path.write_text(
        json.dumps(
            {
                "schema": REPEATMASKER_COMPACT_INDEX_SCHEMA,
                "source_id": "repeatmasker_rmsk_bb",
                "source_version": "pytest",
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _clinical_release_asset_root(tmp_path):
    root = tmp_path / "source_assets"
    (root / "mondo_disease_ontology").mkdir(parents=True)
    (root / "human_phenotype_ontology").mkdir(parents=True)
    (root / "clingen_gene_validity").mkdir(parents=True)
    (root / "gencc_download").mkdir(parents=True)
    (root / "mondo_disease_ontology" / "mondo.json").write_text(
        """
        {
          "graphs": [
            {
              "nodes": [
                {
                  "id": "http://purl.obolibrary.org/obo/MONDO_0008765",
                  "lbl": "Leber congenital amaurosis 2"
                }
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    (root / "human_phenotype_ontology" / "hp.json").write_text(
        """
        {
          "graphs": [
            {
              "nodes": [
                {
                  "id": "http://purl.obolibrary.org/obo/HP_0000510",
                  "lbl": "Visual impairment"
                }
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    (root / "human_phenotype_ontology" / "phenotype.hpoa").write_text(
        "\n".join(
            [
                "#version: 2026-02-16",
                "database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\t"
                "frequency\tsex\tmodifier\taspect\tbiocuration",
                "OMIM:204100\tLeber congenital amaurosis 2\t\tHP:0000510\tPMID:1\tPCS\t\t1/2\t\t\tP\tHPO:test",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "human_phenotype_ontology" / "genes_to_phenotype.txt").write_text(
        "\n".join(
            [
                "ncbi_gene_id\tgene_symbol\thpo_id\thpo_name\tfrequency\tdisease_id",
                "6121\tRPE65\tHP:0000510\tVisual impairment\t1/2\tOMIM:204100",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "clingen_gene_validity" / "clingen_gene_validity.csv").write_text(
        "\n".join(
            [
                '"CLINGEN GENE DISEASE VALIDITY CURATIONS","","","","","","","","",""',
                (
                    '"GENE SYMBOL","GENE ID (HGNC)","DISEASE LABEL","DISEASE ID (MONDO)",'
                    '"MOI","SOP","CLASSIFICATION","ONLINE REPORT","CLASSIFICATION DATE","GCEP"'
                ),
                (
                    '"RPE65","HGNC:10294","Leber congenital amaurosis 2","MONDO:0008765",'
                    '"AR","SOP10","Definitive","https://example.test","2024-03-14","Panel"'
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "gencc_download" / "gencc-download.csv").write_text(
        "\n".join(
            [
                "uuid,gene_curie,gene_symbol,disease_curie,disease_title,classification_title,"
                "submitter_title,submitted_as_date,submitted_as_public_report_url",
                "GENCC_1,HGNC:10294,RPE65,MONDO:0008765,Leber congenital amaurosis 2,"
                "Definitive,ClinGen,2024-03-14,https://example.test/gencc",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return root
