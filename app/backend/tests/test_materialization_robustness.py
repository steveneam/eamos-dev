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


class FakeClinicalImportStore:
    def __init__(self) -> None:
        self.source_versions: list[dict] = []
        self.clinical_rows: dict = {}
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


def test_admin_clinical_release_import_requires_configured_store(
    auth_client,
) -> None:
    token = "admin-clinical-import-test-token"
    settings = auth_client.app.state.settings
    settings.admin_materialization_enabled = True
    settings.admin_materialization_token_sha256 = hashlib.sha256(token.encode()).hexdigest()
    auth_client.app.state.supabase_local_model_cache_store = None

    response = auth_client.post(
        "/api/v1/admin/materialization/clinical-release/import",
        json={},
        headers={"X-Eamos-Admin-Token": token},
    )

    assert response.status_code == 409
    output = response.json()["detail"]
    assert output["code"] == "clinical_release_import_store_unavailable"
    assert output["secret_values_emitted"] is False
    assert token not in json.dumps(output)


def test_admin_clinical_release_import_validates_files_before_smoke(
    auth_client,
    tmp_path,
) -> None:
    token = "admin-clinical-import-test-token"
    settings = auth_client.app.state.settings
    settings.admin_materialization_enabled = True
    settings.admin_materialization_token_sha256 = hashlib.sha256(token.encode()).hexdigest()
    settings.admin_materialization_clinical_source_asset_root = tmp_path / "missing_source_assets"
    store = FakeClinicalImportStore()
    auth_client.app.state.supabase_local_model_cache_store = store

    response = auth_client.post(
        "/api/v1/admin/materialization/clinical-release/import",
        json={},
        headers={"X-Eamos-Admin-Token": token},
    )

    assert response.status_code == 400
    output = response.json()["detail"]
    assert output["code"] == "fixture_unavailable"
    assert output["details"]["path"] == "[redacted]"
    assert store.smoke_count == 0
    encoded = json.dumps(output).lower()
    assert str(tmp_path).lower() not in encoded
    assert token not in encoded


def test_admin_clinical_release_import_applies_rows_without_path_leak(
    auth_client,
    tmp_path,
) -> None:
    token = "admin-clinical-import-test-token"
    settings = auth_client.app.state.settings
    settings.admin_materialization_enabled = True
    settings.admin_materialization_token_sha256 = hashlib.sha256(token.encode()).hexdigest()
    settings.admin_materialization_clinical_source_asset_root = _clinical_release_asset_root(
        tmp_path
    )
    store = FakeClinicalImportStore()
    auth_client.app.state.supabase_local_model_cache_store = store

    response = auth_client.post(
        "/api/v1/admin/materialization/clinical-release/import",
        json={
            "mondo_source_version": "MONDO pytest release",
            "hpo_source_version": "HPO pytest release",
            "clingen_source_version": "ClinGen pytest export",
            "gencc_source_version": "GenCC pytest export",
        },
        headers={"X-Eamos-Admin-Token": token},
    )

    assert response.status_code == 200
    output = response.json()
    assert output["mode"] == "eamos_admin_clinical_release_import"
    assert output["status"] == "applied"
    assert output["ready"] is True
    assert output["smoke_test"] == "used"
    assert store.smoke_count == 1
    assert output["row_counts"] == {
        "clinical_mondo_diseases": 1,
        "clinical_hpo_terms": 1,
        "clinical_hpo_disease_phenotypes": 1,
        "clinical_hpo_gene_phenotypes": 1,
        "clinical_clingen_gene_validity": 1,
        "clinical_gencc_assertions": 1,
    }
    assert store.clinical_rows["mondo_rows"][0]["source_version_id"] == "source-version-1"
    assert {version["source_release"] for version in output["source_versions"]} == {
        "MONDO pytest release",
        "HPO pytest release",
        "ClinGen pytest export",
        "GenCC pytest export",
    }
    assert output["guardrails"]["render_disk_seed"] == "not_used"
    assert output["guardrails"]["local_evidence_enabled_flip"] == "not_used"
    assert output["guardrails"]["provider_flip"] == "not_used"
    encoded = json.dumps(output).lower()
    assert str(tmp_path).lower() not in encoded
    assert "asset_path" not in encoded
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
