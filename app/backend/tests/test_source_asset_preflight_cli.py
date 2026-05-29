from __future__ import annotations

import json
from pathlib import Path

from app.cli.eamos_source_asset_preflight import main
from app.data_sources import (
    DOCX_BLUEPRINT_LINES,
    DOCX_SUPPLEMENTAL_REQUESTS,
    build_docx_task_matrix,
)


def test_source_asset_preflight_reports_guarded_readiness(
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
    assert output["mode"] == "source_asset_readiness"
    assert output["guardrails"] == {
        "network": "not_used",
        "production_downloads": "not_used",
        "restricted_predictor_unlocks": "not_used",
        "runtime_local_source_wiring": "not_used",
        "supabase": "not_used",
        "uploads_or_imports": "not_used",
    }

    manifest = output["source_manifest"]
    assert manifest["total_sources"] == 10
    assert manifest["download_approved_count"] == 0
    assert manifest["ready_for_download_or_import_count"] == 0
    assert manifest["backend_owned_storage_count"] == 10
    assert manifest["requires_c_drive_staging"] == [
        "ncbi_dbsnp_gcf_000001405_40",
        "ucsc_phylop100way_hg38",
    ]
    assert manifest["missing_requirement_counts"]["explicit_download_or_import_approval"] == 10
    assert manifest["missing_requirement_counts"]["backend_storage_policy_review"] == 10

    hg38 = output["hg38_runtime_asset"]
    assert hg38["status"] == "missing"
    assert hg38["ready"] is False
    assert hg38["checksum_verified"] is False

    gate = output["local_evidence_gate"]
    assert gate["configured_runtime_flows_enabled"] is False
    assert gate["preflight_wires_runtime"] is False
    assert {flow["reason"] for flow in gate["flows"]} == {"local_evidence_disabled"}


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
        == "locked"
    )

    assert output["restricted_predictors"]["locked"] is True
    assert output["myvariant_policy"]["enabled_for_runtime"] is False
    assert output["myvariant_policy"]["allowed_fields"] == ["gnomad_genome", "gnomad_exome"]
    assert "spliceai" in output["myvariant_policy"]["restricted_fields"]


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


def test_docx_task_matrix_keeps_restricted_predictors_locked() -> None:
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
