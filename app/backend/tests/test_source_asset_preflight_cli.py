from __future__ import annotations

import json
from hashlib import md5, sha256
from pathlib import Path
from types import SimpleNamespace

from app.cli.eamos_source_asset_preflight import (
    _render_persistent_disk_gate_summary,
    build_source_asset_preflight_report,
    main,
)
from app.core.config import Settings
from app.data_sources import (
    DOCX_BLUEPRINT_LINES,
    DOCX_SUPPLEMENTAL_REQUESTS,
    build_post_reference_source_readiness,
    build_docx_task_matrix,
    SourceAssetMaterializationRecord,
)
from app.services.esm1b_assembly import ESM1B_REGENERATION_REQUIRED_GATE
from app.services.clinvar_local import (
    DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
    materialize_clinvar_gene_distribution_index,
)
from app.services.predictor_runtime import (
    CAPICE_FEATURE_CACHE_ASSET_ROLE,
    CAPICE_FEATURE_CACHE_SOURCE_ID,
    CAPICE_LAUNCH_GATE,
    CAPICE_MODEL_ASSET_ROLE,
    CAPICE_SOURCE_ID,
    CI_SPLICEAI_LAUNCH_GATE,
    CI_SPLICEAI_MODEL_ASSET_ROLE,
    CI_SPLICEAI_REFERENCE_ASSET_ROLE,
    CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE,
    CI_SPLICEAI_SOURCE_ID,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures"
COMPACT_INDEX_FIXTURE = FIXTURES_DIR / "coordinate_index" / "eamos_coordinate_index_tiny.jsonl"


def test_source_asset_preflight_reports_guarded_readiness(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.delenv("LOCAL_EVIDENCE_ENABLED", raising=False)
    monkeypatch.delenv("LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW", raising=False)
    monkeypatch.delenv("USE_REAL_APIS", raising=False)
    monkeypatch.setenv("CLINGEN_LOCAL_SQLITE_PATH", str(tmp_path / "missing-clingen.sqlite"))
    monkeypatch.setenv(
        "CLINGEN_LOCAL_MANIFEST_PATH", str(tmp_path / "missing-clingen.manifest.json")
    )
    monkeypatch.setenv("PUBMED_LOCAL_SQLITE_PATH", str(tmp_path / "missing-pubmed.sqlite"))
    monkeypatch.setenv("PUBMED_LOCAL_MANIFEST_PATH", str(tmp_path / "missing-pubmed.manifest.json"))
    monkeypatch.setenv("RAG_SQLITE_PATH", str(tmp_path / "missing-literature.sqlite"))
    monkeypatch.setenv("RAG_MANIFEST_PATH", str(tmp_path / "missing-literature.manifest.json"))
    monkeypatch.setenv("DBSNP_RUNTIME_VCF_PATH", str(tmp_path / "missing-dbsnp.vcf.gz"))
    monkeypatch.setenv("DBSNP_RUNTIME_INDEX_PATH", str(tmp_path / "missing-dbsnp.vcf.gz.tbi"))
    monkeypatch.setenv("CLINVAR_RUNTIME_VCF_PATH", str(tmp_path / "missing-clinvar.vcf.gz"))
    monkeypatch.setenv(
        "CLINVAR_RUNTIME_INDEX_PATH",
        str(tmp_path / "missing-clinvar.vcf.gz.tbi"),
    )
    monkeypatch.setenv(
        "CLINVAR_GENE_DISTRIBUTION_INDEX_PATH",
        str(tmp_path / "missing-clinvar-gene-distribution.sqlite"),
    )
    monkeypatch.setenv(
        "CLINVAR_GENE_DISTRIBUTION_MANIFEST_PATH",
        str(tmp_path / "missing-clinvar-gene-distribution.manifest.json"),
    )
    monkeypatch.setenv(
        "REPEATMASKER_RUNTIME_INDEX_PATH",
        str(tmp_path / "missing-repeatmasker.index"),
    )
    monkeypatch.setenv("PHYLOP_RUNTIME_BIGWIG_PATH", str(tmp_path / "missing-phylop.bw"))

    exit_code = main(
        [
            "--hg38-path",
            str(tmp_path / "missing-hg38.2bit"),
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "source_asset_readiness"
    assert output["guardrails"] == {
        "network": "not_used",
        "production_downloads": "not_used",
        "restricted_predictor_unlocks": "admin_runtime_allowed_launch_filter_later",
        "runtime_local_source_wiring": "not_used",
        "supabase": "not_used",
        "uploads_or_imports": "not_used",
    }

    manifest = output["source_manifest"]
    assert manifest["total_sources"] == 11
    assert manifest["download_approved_count"] == 11
    assert manifest["ready_for_download_or_import_count"] == 11
    assert manifest["backend_owned_storage_count"] == 11
    assert manifest["requires_c_drive_staging"] == [
        "ncbi_dbsnp_gcf_000001405_40",
        "ucsc_phylop100way_hg38",
    ]
    assert "explicit_download_or_import_approval" not in manifest["missing_requirement_counts"]
    assert "backend_storage_policy_review" not in manifest["missing_requirement_counts"]
    assert "reader_compatibility_proof" not in manifest["missing_requirement_counts"]

    assert output["download_staging"]["network_used"] is False
    assert output["download_staging"]["download_performed"] is False
    assert "status_counts" in output["download_staging"]
    assert output["private_storage_upload_plan"]["network_used"] is False
    assert output["private_storage_upload_plan"]["upload_performed"] is False
    assert output["private_storage_upload_plan"]["planned_count"] >= 0
    generated_artifacts = output["generated_artifact_upload_plan"]
    assert generated_artifacts["network_used"] is False
    assert generated_artifacts["upload_performed"] is False
    assert generated_artifacts["planned_count"] == 0
    assert generated_artifacts["status_counts"]["missing_local_file"] == 3
    assert all(item["local_path_values_emitted"] is False for item in generated_artifacts["items"])
    tier2_artifacts = output["tier2_predictor_artifact_upload_plan"]
    assert tier2_artifacts["network_used"] is False
    assert tier2_artifacts["upload_performed"] is False
    assert tier2_artifacts["planned_count"] == 0
    assert tier2_artifacts["status_counts"]["missing_local_file"] == 9
    assert all(item["local_path_values_emitted"] is False for item in tier2_artifacts["items"])
    assert output["reader_compatibility_proofs"]["network_used"] is False
    assert output["reader_compatibility_proofs"]["runtime_mutation_performed"] is False
    assert "status_counts" in output["reader_compatibility_proofs"]
    probe = output["runtime_materialization_probe"]
    assert probe["enabled"] is False
    assert probe["probe_performed"] is False
    assert probe["ready"] is False
    assert probe["status"] == "not_requested"
    assert probe["read_only"] is True
    assert probe["mutations_performed"] is False
    assert probe["secret_values_emitted"] is False
    assert probe["local_path_values_emitted"] is False
    assert probe["object_uri_values_emitted"] is False
    assert probe["failure_boundaries"] == {
        "health_and_preflight_probe": "sanitized_status_no_exception",
        "lookup_sequence_context_runtime": "fail_open",
        "metadata_and_local_cache_resolution": "fail_closed",
    }
    assert "terms_review" not in manifest["missing_requirement_counts"]

    render_gate = output["render_persistent_disk_gate"]
    assert render_gate["mutations_performed"] is False
    assert render_gate["network_used"] is False
    assert render_gate["secret_values_emitted"] is False
    assert render_gate["object_uri_values_emitted"] is False
    assert render_gate["status"] == "full_tier_stack_ready_for_paid_render_disk"

    current_runtime = render_gate["current_hg38_pfam_web_runtime"]
    assert current_runtime["ready_for_paid_render_disk_decision"] is False
    assert current_runtime["recommended_disk_gb"] == 15
    assert current_runtime["disk_mount_required_before_env_enablement"] is True
    assert "PROTEIN_ANNOTATION_ENABLED" in current_runtime["required_env_names"]
    assert "hg38_runtime_asset_ready" in current_runtime["remaining_before_runtime_enablement"]

    full_stack = render_gate["full_noncommercial_tier_stack"]
    assert full_stack["ready_for_paid_render_disk_decision"] is True
    assert full_stack["recommended_disk_gb_after_unpaid_readiness"] == 60
    assert full_stack["ready_for_download_or_import_count"] == 11
    assert full_stack["total_sources"] == 11
    assert full_stack["blocking_requirement_counts"] == {}
    assert "AlphaMissense" not in render_gate["excluded_from_disk_estimates"]

    hg38 = output["hg38_runtime_asset"]
    assert hg38["status"] == "missing"
    assert hg38["ready"] is False
    assert hg38["checksum_verified"] is False

    compact_index = output["compact_coordinate_index"]
    assert compact_index["source_id"] == "eamos_compact_coordinate_index"
    assert compact_index["ready"] is False
    assert compact_index["status"] == "missing"
    assert compact_index["source_runtime_scan_allowed"] is False
    assert compact_index["startup_download_allowed"] is False
    clinvar_gene_index = output["clinvar_gene_distribution_index"]
    assert clinvar_gene_index["source_id"] == "eamos_clinvar_gene_distribution_index"
    assert clinvar_gene_index["ready"] is False
    assert clinvar_gene_index["status"] == "missing"
    assert clinvar_gene_index["source_runtime_scan_allowed"] is False
    assert clinvar_gene_index["startup_download_allowed"] is False
    assert clinvar_gene_index["local_path_values_emitted"] is False
    assert clinvar_gene_index["raw_source_rows_emitted"] is False

    local_evidence_runtime = output["local_evidence_runtime_assets"]
    assert local_evidence_runtime["ready"] is False
    assert local_evidence_runtime["ready_count"] == 0
    assert local_evidence_runtime["total_sources"] == 4
    assert local_evidence_runtime["runtime_reader_opened"] is False
    assert local_evidence_runtime["source_runtime_scan_allowed"] is False
    assert local_evidence_runtime["local_path_values_emitted"] is False
    runtime_sources = {item["item_id"]: item for item in local_evidence_runtime["sources"]}
    assert runtime_sources["dbsnp_local_adapter"]["status"] == "missing_runtime_file"
    assert runtime_sources["clinvar_local_adapter"]["status"] == "missing_runtime_file"
    assert runtime_sources["repeatmasker_local_adapter"]["status"] == "missing_runtime_file"
    assert runtime_sources["phylop_conservation_reader"]["status"] == "missing_runtime_file"
    assert runtime_sources["repeatmasker_local_adapter"]["source_runtime_scan_allowed"] is False

    predictors = output["predictor_runtime_assets"]
    assert predictors["alphamissense"]["status"] == "missing_source_file"
    assert predictors["alphamissense"]["public_serialization_allowed"] is True
    assert predictors["esm1b"]["status"] == "missing_source_file"
    assert predictors["esm1b"]["public_serialization_allowed"] is True
    assert predictors["esm1b"]["launch_gate"] == ESM1B_REGENERATION_REQUIRED_GATE
    assert predictors["pvs1_nmd"]["status"] == "pure_code_available"
    assert predictors["pvs1_nmd"]["storage_required"] is False
    assert predictors["public_serialization_locked"] == []
    assert predictors["ci_spliceai"]["status"] == "score_cache_missing"
    assert predictors["ci_spliceai"]["runtime_wired"] is True
    assert predictors["ci_spliceai"]["public_serialization_allowed"] is True
    assert predictors["capice"]["status"] == "model_artifact_missing"
    assert predictors["capice"]["runtime_wired"] is True
    assert predictors["capice"]["public_serialization_allowed"] is True
    assert predictors["revel"]["status"] == "score_cache_missing"
    assert predictors["revel"]["runtime_wired"] is True
    assert predictors["revel"]["public_serialization_allowed"] is True
    assert predictors["primateai3d"]["status"] == "score_cache_missing"
    assert predictors["primateai3d"]["runtime_wired"] is True
    assert predictors["primateai3d"]["public_serialization_allowed"] is True
    assert predictors["launch_gated"] == [
        "esm1b",
        "ci_spliceai",
        "capice",
        "revel",
        "primateai3d",
    ]

    gate = output["local_evidence_gate"]
    assert gate["configured_runtime_flows_enabled"] is False
    assert gate["preflight_wires_runtime"] is False
    assert {flow["reason"] for flow in gate["flows"]} == {"local_evidence_disabled"}

    ledger = output["build_ledger"]
    assert ledger["mode"] == "backend_build_ledger"
    assert ledger["startup_downloads_allowed"] is False
    assert ledger["gff_runtime_scans_allowed"] is False
    items = {item["item_id"]: item for item in ledger["items"]}
    assert items["alphamissense"]["status"] == "missing_source_file"
    assert items["alphamissense"]["runtime_wired"] is True
    assert items["esm1b"]["runtime_wired"] is True
    assert items["ci_spliceai"]["runtime_wired"] is True
    assert items["capice"]["runtime_wired"] is True
    assert items["capice"]["launch_gate"] == "capice_launch_filter_metadata"
    assert items["revel"]["runtime_wired"] is True
    assert items["revel"]["launch_gate"] == "revel_launch_filter_metadata"
    assert items["primateai3d"]["runtime_wired"] is True
    assert items["primateai3d"]["launch_gate"] == "primateai3d_launch_filter_metadata"
    assert items["clinical_source_tables"]["durable_source"] == "supabase_postgres"
    assert items["clinical_source_tables"]["render_disk_role"] == "not_required"
    assert items["coordinate_compact_index"]["runtime_source"] == (
        "render_disk_compact_immutable_index"
    )
    assert items["dbsnp_local_adapter"]["status"] == "source_ready_for_materialization"
    assert items["dbsnp_local_adapter"]["blockers"] == ["seed_verified_render_disk_cache"]
    assert items["phylop_conservation_reader"]["status"] == "source_ready_for_materialization"
    assert items["phylop_conservation_reader"]["blockers"] == ["seed_verified_render_disk_cache"]
    assert items["gene_view"]["runtime_wired"] is True
    assert items["protein_pfam"]["runtime_source"] == "render_disk_hmmer_indexes"
    encoded_ledger = json.dumps(ledger).lower()
    assert str(tmp_path).lower() not in encoded_ledger
    assert "supabase://" not in encoded_ledger
    assert "service_role" not in encoded_ledger


def test_source_asset_preflight_reports_compact_coordinate_index_ready_without_paths(
    tmp_path: Path,
) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_path=tmp_path / "missing-hg38.2bit",
        coordinate_resolver_compact_index_path=COMPACT_INDEX_FIXTURE,
    )

    output = build_source_asset_preflight_report(settings=settings)

    compact_index = output["compact_coordinate_index"]
    assert compact_index["ready"] is True
    assert compact_index["status"] == "ready"
    assert compact_index["schema_version"] == "eamos.coordinate_index.v1"
    assert compact_index["variant_count"] == 2
    assert compact_index["transcript_count"] == 2
    assert compact_index["source_runtime_scan_allowed"] is False
    encoded = json.dumps(output).lower()
    assert str(COMPACT_INDEX_FIXTURE).lower() not in encoded
    assert "eamos-coordinate-index" not in encoded


def test_source_asset_preflight_reports_clinvar_gene_index_ready_without_paths(
    tmp_path: Path,
) -> None:
    index_path = tmp_path / "clinvar-gene-distribution.sqlite"
    manifest_path = tmp_path / "clinvar-gene-distribution.manifest.json"
    materialize_clinvar_gene_distribution_index(
        vcf_path=DEFAULT_CLINVAR_VCF_FIXTURE_PATH,
        index_path=index_path,
        manifest_path=manifest_path,
        force=True,
    )
    settings = Settings(
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_path=tmp_path / "missing-hg38.2bit",
        clinvar_gene_distribution_index_path=index_path,
        clinvar_gene_distribution_manifest_path=manifest_path,
    )

    output = build_source_asset_preflight_report(settings=settings)

    clinvar_gene_index = output["clinvar_gene_distribution_index"]
    assert clinvar_gene_index["ready"] is True
    assert clinvar_gene_index["status"] == "ready"
    assert clinvar_gene_index["schema_version"] == "eamos.clinvar_gene_distribution.v1"
    assert clinvar_gene_index["gene_count"] == 1
    assert clinvar_gene_index["variant_count"] == 1
    assert clinvar_gene_index["source_runtime_scan_allowed"] is False
    assert clinvar_gene_index["local_path_values_emitted"] is False
    assert clinvar_gene_index["raw_source_rows_emitted"] is False
    encoded = json.dumps(clinvar_gene_index).lower()
    assert str(tmp_path).lower() not in encoded
    assert "supabase://" not in encoded


def test_source_asset_preflight_reports_ready_admin_predictors_without_paths(
    tmp_path: Path,
) -> None:
    ci_model = _write_runtime_file(tmp_path / "ci" / "model.keras", b"model")
    ci_reference = _write_runtime_file(tmp_path / "ci" / "reference.json", b"reference")
    ci_cache = _write_indexed_runtime_file(tmp_path / "ci" / "scores.vcf.gz", b"scores")
    capice_model = _write_runtime_file(tmp_path / "capice" / "model.json", b"model")
    capice_features = _write_indexed_runtime_file(
        tmp_path / "capice" / "features.tsv.gz",
        b"features",
    )
    _write_admin_predictor_manifest(
        ci_model,
        artifact_id="ci_spliceai",
        component_id="model",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_keras_model",
        role=CI_SPLICEAI_MODEL_ASSET_ROLE,
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    _write_admin_predictor_manifest(
        ci_reference,
        artifact_id="ci_spliceai",
        component_id="reference_bundle",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_reference_bundle",
        role=CI_SPLICEAI_REFERENCE_ASSET_ROLE,
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    _write_admin_predictor_manifest(
        ci_cache,
        artifact_id="ci_spliceai",
        component_id="score_cache",
        source_id=CI_SPLICEAI_SOURCE_ID,
        asset_id="ci_spliceai_hg38_score_cache_vcf_gz",
        role=CI_SPLICEAI_SCORE_CACHE_ASSET_ROLE,
        launch_gate=CI_SPLICEAI_LAUNCH_GATE,
    )
    _write_admin_predictor_manifest(
        capice_model,
        artifact_id="capice",
        component_id="model",
        source_id=CAPICE_SOURCE_ID,
        asset_id="capice_xgboost_model",
        role=CAPICE_MODEL_ASSET_ROLE,
        launch_gate=CAPICE_LAUNCH_GATE,
    )
    _write_admin_predictor_manifest(
        capice_features,
        artifact_id="capice",
        component_id="feature_cache",
        source_id=CAPICE_FEATURE_CACHE_SOURCE_ID,
        asset_id="capice_hg38_feature_cache_tsv_gz",
        role=CAPICE_FEATURE_CACHE_ASSET_ROLE,
        launch_gate=CAPICE_LAUNCH_GATE,
    )
    settings = Settings(
        jwt_secret="test-secret",
        ci_spliceai_model_path=ci_model,
        ci_spliceai_reference_path=ci_reference,
        ci_spliceai_score_cache_path=ci_cache,
        capice_model_path=capice_model,
        capice_feature_cache_path=capice_features,
    )

    output = build_source_asset_preflight_report(settings=settings)

    predictors = output["predictor_runtime_assets"]
    assert predictors["ci_spliceai"]["status"] == "ready"
    assert predictors["ci_spliceai"]["available"] is True
    assert predictors["ci_spliceai"]["status_notes"] == []
    assert predictors["capice"]["status"] == "ready"
    assert predictors["capice"]["available"] is True
    assert predictors["capice"]["status_notes"] == []
    ledger_items = {item["item_id"]: item for item in output["build_ledger"]["items"]}
    assert ledger_items["ci_spliceai"]["status"] == "ready"
    assert ledger_items["ci_spliceai"]["blockers"] == []
    assert ledger_items["capice"]["status"] == "ready"
    assert ledger_items["capice"]["blockers"] == []
    encoded = json.dumps(
        {
            "predictor_runtime_assets": predictors,
            "build_ledger": output["build_ledger"],
        }
    ).lower()
    assert str(tmp_path).lower() not in encoded
    assert "supabase://" not in encoded


def test_source_asset_preflight_reports_local_evidence_runtime_ready_without_paths(
    tmp_path: Path,
) -> None:
    dbsnp_vcf = _write_indexed_runtime_file(tmp_path / "dbsnp" / "GCF_000001405.40.gz", b"vcf")
    clinvar_vcf = _write_indexed_runtime_file(
        tmp_path / "clinvar" / "clinvar.vcf.gz",
        b"clinvar",
    )
    repeatmasker_index = _write_runtime_file(
        tmp_path / "repeatmasker" / "repeatmasker.interval-index.jsonl",
        b"index",
    )
    phylop_bigwig = _write_runtime_file(tmp_path / "phylop" / "hg38.phyloP100way.bw", b"bw")
    settings = Settings(
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_path=tmp_path / "missing-hg38.2bit",
        dbsnp_runtime_vcf_path=dbsnp_vcf,
        dbsnp_runtime_index_path=Path(f"{dbsnp_vcf}.tbi"),
        clinvar_runtime_vcf_path=clinvar_vcf,
        clinvar_runtime_index_path=Path(f"{clinvar_vcf}.tbi"),
        repeatmasker_runtime_index_path=repeatmasker_index,
        phylop_runtime_bigwig_path=phylop_bigwig,
    )

    output = build_source_asset_preflight_report(settings=settings)

    runtime = output["local_evidence_runtime_assets"]
    assert runtime["ready"] is True
    assert runtime["ready_count"] == 4
    assert runtime["runtime_reader_opened"] is False
    by_item = {item["item_id"]: item for item in runtime["sources"]}
    assert {item["status"] for item in by_item.values()} == {"ready"}
    assert by_item["dbsnp_local_adapter"]["ready_asset_count"] == 2
    assert by_item["clinvar_local_adapter"]["ready_asset_count"] == 2
    assert by_item["repeatmasker_local_adapter"]["ready_asset_count"] == 1
    assert by_item["phylop_conservation_reader"]["ready_asset_count"] == 1
    ledger_items = {item["item_id"]: item for item in output["build_ledger"]["items"]}
    assert ledger_items["dbsnp_local_adapter"]["status"] == "ready"
    assert ledger_items["dbsnp_local_adapter"]["blockers"] == []
    assert ledger_items["clinvar_local_adapter"]["status"] == "ready"
    assert ledger_items["repeatmasker_local_adapter"]["status"] == "ready"
    assert ledger_items["phylop_conservation_reader"]["status"] == "ready"
    encoded = json.dumps(
        {
            "runtime": runtime,
            "build_ledger": output["build_ledger"],
        }
    ).lower()
    assert str(tmp_path).lower() not in encoded
    assert "supabase://" not in encoded


def test_source_asset_preflight_records_docx_reconciliation_and_policy(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.delenv("LOCAL_EVIDENCE_ENABLED", raising=False)
    monkeypatch.delenv("LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW", raising=False)
    monkeypatch.delenv("USE_REAL_APIS", raising=False)

    exit_code = main(
        [
            "--hg38-path",
            str(tmp_path / "missing-hg38.2bit"),
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)

    docx = output["docx_blueprint"]
    assert docx["source_file"] == "Data and sources 1.docx"
    assert docx["interpretation"] == (
        "current_registry_and_guardrails_supersede_the_older_blueprint"
    )
    matrix = docx["task_matrix"]
    assert matrix["line_count"] == 38
    assert matrix["line_count"] == len(DOCX_BLUEPRINT_LINES)
    assert matrix["non_commercial_unresolved_gap_count"] == 0
    assert matrix["unresolved_gap_line_numbers"] == []
    assert matrix["commercial_gated_line_numbers"] == [16, 33, 38]

    lines = {line["line_number"]: line for line in matrix["lines"]}
    assert lines[6]["source_ids"] == ["ucsc_hg38_2bit", "python_twobit_reader"]
    assert lines[6]["status"] == "covered_by_fixture_or_tooling"
    assert "app/backend/app/services/reference_genome.py" in lines[6]["implementation_refs"]
    assert lines[9]["status"] == "corrected_by_registry_policy"
    assert lines[16]["status"] == "commercial_license_blocked"
    assert lines[25]["status"] == "corrected_by_registry_policy"
    assert lines[32]["status"] == "covered_by_policy_lock"
    assert lines[37]["status"] == "covered_by_policy_lock"

    supplements = docx["supplemental_requests"]
    assert supplements["request_count"] == len(DOCX_SUPPLEMENTAL_REQUESTS)
    assert supplements["unresolved_gap_count"] == 1
    assert supplements["unresolved_request_ids"] == ["S1"]
    protein_request = supplements["requests"][0]
    assert protein_request["status"] == "local_offline_implementation_pending"
    assert "No live API dependency is approved" in protein_request["blocker"]
    assert "SignalP" in protein_request["blocker"]
    assert "InterProScan standalone" in protein_request["local_strategy"]
    assert protein_request["source_ids"] == [
        "uniprotkb_reviewed_swissprot",
        "interpro_pfam_protein_matches",
        "interproscan_standalone",
        "interproscan_optional_licensed_apps",
        "hmmer_pfam_a",
    ]
    sources = {source["source_id"]: source for source in protein_request["sources"]}
    assert sources["uniprotkb_reviewed_swissprot"]["license_status"] == "commercial_allowed"
    assert sources["interpro_pfam_protein_matches"]["license_status"] == "commercial_allowed"
    assert sources["interproscan_standalone"]["license_status"] == "commercial_allowed"
    assert (
        sources["interproscan_optional_licensed_apps"]["license_status"]
        == "commercial_license_review_required"
    )

    reconciliation = {item["item"]: item for item in docx["reconciliation"]}
    assert reconciliation["InterVar, ANNOVAR, and OMIM production use"]["state"] == "blocked"
    assert (
        reconciliation["SpliceAI, CADD, REVEL, PrimateAI-3D, and restricted dbNSFP fields"]["state"]
        == "launch_gated"
    )

    assert output["restricted_predictors"]["locked"] is False
    assert output["restricted_predictors"]["admin_runtime_allowed"] is True
    assert output["restricted_predictors"]["launch_filter_required"] is True
    assert output["myvariant_policy"]["enabled_for_runtime"] is False
    assert output["myvariant_policy"]["allowed_fields"] == ["gnomad_genome", "gnomad_exome"]
    assert "spliceai" in output["myvariant_policy"]["restricted_fields"]


def test_source_asset_preflight_can_run_sanitized_materialization_probe(
    tmp_path: Path,
) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_path=tmp_path / "missing-hg38.2bit",
    )

    output = build_source_asset_preflight_report(
        settings=settings,
        probe_materialization=True,
        materialization_store=ExplodingMaterializationStore(),
    )

    assert output["guardrails"]["network"] == "read_only_supabase_materialization_probe"
    assert output["guardrails"]["supabase"] == "read_only_materialization_probe"
    assert output["guardrails"]["uploads_or_imports"] == "not_used"
    probe = output["runtime_materialization_probe"]
    assert probe["enabled"] is True
    assert probe["probe_performed"] is True
    assert probe["ready"] is False
    assert probe["status"] == "materialization_metadata_unavailable"
    assert probe["read_only"] is True
    assert probe["mutations_performed"] is False
    assert probe["secret_values_emitted"] is False
    assert probe["local_path_values_emitted"] is False
    assert probe["object_uri_values_emitted"] is False
    encoded = json.dumps(probe).lower()
    assert "private.example" not in encoded
    assert str(tmp_path).lower() not in encoded


def test_source_asset_preflight_reports_m2_metadata_without_runtime_ready(
    tmp_path: Path,
) -> None:
    settings = Settings(
        jwt_secret="test-secret",
        hg38_2bit_runtime_asset_path=tmp_path / "missing-hg38.2bit",
    )

    output = build_source_asset_preflight_report(
        settings=settings,
        probe_materialization=True,
        materialization_store=FakeM2MetadataStore(),
    )

    probe = output["source_asset_metadata_probe"]
    assert probe["enabled"] is True
    assert probe["probe_performed"] is True
    assert probe["status"] == "metadata_ready"
    by_source = {item["source_id"]: item for item in probe["sources"]}
    assert by_source["ncbi_dbsnp_gcf_000001405_40"]["metadata_ready"] is True
    assert by_source["ucsc_phylop100way_hg38"]["metadata_ready"] is True
    dbsnp_roles = {
        item["asset_role"]: item for item in by_source["ncbi_dbsnp_gcf_000001405_40"]["roles"]
    }
    assert dbsnp_roles["dbsnp_bgzip_vcf"]["upload_status"] == "verified"
    assert dbsnp_roles["dbsnp_bgzip_vcf"]["approval_status"] == "approved"
    assert dbsnp_roles["dbsnp_bgzip_vcf"]["materialization_status"] == "not_materialized"
    assert dbsnp_roles["dbsnp_bgzip_vcf"]["fail_closed_reason"] == (
        "render_disk_seed_not_performed"
    )
    encoded = json.dumps(probe).lower()
    assert str(tmp_path).lower() not in encoded
    assert "supabase://" not in encoded
    assert "object_path" not in encoded


def test_docx_task_matrix_maps_every_noncommercial_line_to_coverage_or_blocker() -> None:
    matrix = build_docx_task_matrix()

    assert matrix["line_count"] == 38
    assert matrix["non_commercial_line_count"] == 35
    assert matrix["non_commercial_unresolved_gap_count"] == 0

    lines = matrix["lines"]
    for line in lines:
        assert line["status"]
        if line["category"] in {"asset_row", "engine_row", "api_row"}:
            assert line["source_ids"]
            assert line["sources"]

        if line["commercial_gated"]:
            assert line["blocker"]
        elif line["status"] != "narrative_or_table_structure":
            assert line["implementation_refs"] or line["blocker"] or line["next_action"]


def test_render_disk_gate_separates_current_runtime_from_full_stack() -> None:
    gate = _render_persistent_disk_gate_summary(
        readiness=build_post_reference_source_readiness(),
        hg38=SimpleNamespace(ready=True),
        protein_assets=(SimpleNamespace(asset_id="pfam_a_hmm_gz", present=True),),
        verify_hg38_checksum=True,
        verify_protein_checksums=True,
    )

    current_runtime = gate["current_hg38_pfam_web_runtime"]
    assert current_runtime["ready_for_paid_render_disk_decision"] is True
    assert current_runtime["remaining_before_runtime_enablement"] == []
    assert current_runtime["next_paid_step_if_approved"] == "provision_render_persistent_disk"

    full_stack = gate["full_noncommercial_tier_stack"]
    assert full_stack["ready_for_paid_render_disk_decision"] is True
    assert full_stack["ready_for_download_or_import_count"] == 11
    assert full_stack["total_sources"] == 11
    assert full_stack["blocked_by"] == []


def test_docx_task_matrix_marks_restricted_predictors_launch_gated() -> None:
    matrix = build_docx_task_matrix()
    lines = {line["line_number"]: line for line in matrix["lines"]}

    restricted_lines = (33, 38)
    for line_number in restricted_lines:
        line = lines[line_number]
        assert line["commercial_gated"] is True
        assert line["status"] == "commercial_license_blocked"
        assert any(
            source["license_status"] == "restricted_unlicensed" for source in line["sources"]
        )
        assert all(source["download_approved"] is False for source in line["sources"])


def test_docx_supplement_records_local_protein_annotation_gap_without_api_dependency() -> None:
    matrix = build_docx_task_matrix()

    assert matrix["line_count"] == 38

    supplement = DOCX_SUPPLEMENTAL_REQUESTS[0]
    assert supplement.request_id == "S1"
    assert supplement.status == "local_offline_implementation_pending"
    assert supplement.unresolved_gap is True
    assert "UniProtKB" in supplement.request_text
    assert "without depending on live third-party APIs" in supplement.request_text
    assert "HMMER hmmscan" in supplement.next_action
    assert "commercially usable" in (supplement.blocker or "")


class ExplodingMaterializationStore:
    def get_source_asset_materialization(self, **kwargs) -> SourceAssetMaterializationRecord:
        raise RuntimeError("database unavailable at postgresql://private.example/path")


class FakeM2MetadataStore:
    def __init__(self) -> None:
        self.records = {
            ("ncbi_dbsnp_gcf_000001405_40", "dbsnp_bgzip_vcf"): _metadata_record(
                source_id="ncbi_dbsnp_gcf_000001405_40",
                asset_role="dbsnp_bgzip_vcf",
                byte_size=29_552_227_779,
            ),
            ("ncbi_dbsnp_gcf_000001405_40", "dbsnp_tabix_index"): _metadata_record(
                source_id="ncbi_dbsnp_gcf_000001405_40",
                asset_role="dbsnp_tabix_index",
                byte_size=3_140_346,
            ),
            ("ucsc_phylop100way_hg38", "phylop_bigwig"): _metadata_record(
                source_id="ucsc_phylop100way_hg38",
                asset_role="phylop_bigwig",
                byte_size=9_870_053_206,
            ),
        }

    def get_source_asset_materialization(self, **kwargs) -> SourceAssetMaterializationRecord | None:
        return self.records.get((kwargs["source_id"], kwargs["asset_role"]))


def _write_runtime_file(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _write_indexed_runtime_file(path: Path, payload: bytes) -> Path:
    _write_runtime_file(path, payload)
    Path(f"{path}.tbi").write_bytes(b"index")
    return path


def _write_admin_predictor_manifest(
    path: Path,
    *,
    artifact_id: str,
    component_id: str,
    source_id: str,
    asset_id: str,
    role: str,
    launch_gate: str,
) -> None:
    payload = path.read_bytes()
    md5_value = md5(payload, usedforsecurity=False).hexdigest()
    sha256_value = sha256(payload).hexdigest()
    path.with_suffix(path.suffix + ".manifest.json").write_text(
        json.dumps(
            {
                "artifact_id": artifact_id,
                "component_id": component_id,
                "source_id": source_id,
                "asset_id": asset_id,
                "role": role,
                "byte_size": len(payload),
                "md5": md5_value,
                "sha256": sha256_value,
                "checksums": {"md5": md5_value, "sha256": sha256_value},
                "launch_gate": launch_gate,
                "storage_contract": {
                    "bucket_policy": "private",
                    "frontend_direct_access_allowed": False,
                    "signed_urls_created": False,
                    "startup_download_allowed": False,
                    "request_time_materialization_allowed": False,
                    "runtime_sync_required": True,
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _metadata_record(
    *,
    source_id: str,
    asset_role: str,
    byte_size: int,
) -> SourceAssetMaterializationRecord:
    return SourceAssetMaterializationRecord(
        source_id=source_id,
        asset_role=asset_role,
        bucket_id="eamos-source-assets",
        object_path=f"{source_id}/{asset_role}/sha256-{'1' * 64}/asset.dat",
        upload_status="verified",
        approval_status="approved",
        public_access_allowed=False,
        frontend_direct_access_allowed=False,
        environment="sg-render",
        backend_runtime="render_backend",
        local_cache_path=f"/var/data/eamos/bio_assets/{asset_role}/asset.dat",
        materialization_status="not_materialized",
        byte_size=byte_size,
        checksum_algorithm="sha256",
        checksum_value="1" * 64,
        verified_at=None,
        fail_closed_reason="render_disk_seed_not_performed",
        metadata={"metadata_set_id": "dbsnp_phylop"},
        warnings=[],
    )
