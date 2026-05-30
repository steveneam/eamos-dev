from __future__ import annotations

import json

import pytest

from app.cli import eamos_source_import
from app.services.source_imports import (
    CLINVAR_STORAGE_PILOT_ID,
    HG38_STORAGE_PILOT_ID,
    SourceImportError,
    apply_clinical_source_import_bundle,
    apply_storage_pilot_registration,
    build_clinical_source_import_bundle,
    build_storage_pilot_registration,
    clinical_bundle_report,
    storage_pilot_report,
)


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


def test_clinical_source_import_bundle_plans_fixture_rows_and_versions() -> None:
    bundle = build_clinical_source_import_bundle()
    report = clinical_bundle_report(bundle)

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


def test_source_import_apply_uses_configured_store_and_smoke(monkeypatch) -> None:
    store = FakeSourceImportStore()
    monkeypatch.setattr(
        eamos_source_import,
        "build_supabase_local_model_cache_store",
        lambda settings: store,
    )

    output = eamos_source_import.build_source_import_report(apply_supabase=True)

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
