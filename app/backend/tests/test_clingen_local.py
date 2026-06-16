from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
from fastapi.testclient import TestClient

import app.services.clingen_local as clingen_local_module
from app.cli.eamos_clingen_local_preflight import main as preflight_main
from app.core.config import Settings
from app.main import create_app
from app.services.clingen_local import (
    ClinGenLocalStore,
    inspect_clingen_local_store,
    materialize_clingen_local_store,
)
from app.services.clingen_source_fetch import fetch_clingen_source_snapshots
from app.services.functional_evidence import FunctionalEvidenceExtractor
from app.tools.clingen import ClingenTool


def test_clingen_source_fetch_pages_erepo_and_cspec_with_retry(tmp_path: Path) -> None:
    calls: dict[str, int] = {}
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.url.path}?{request.url.query.decode()}"
        calls[key] = calls.get(key, 0) + 1
        query = parse_qs(request.url.query.decode())
        page = int(query.get("pg", ["1"])[0])
        if request.url.path == "/evrepo/api/summary/classifications":
            if page == 1:
                return _json_response({"data": [_erepo_record()]})
            return _json_response({"status": {"code": 404, "name": "Not Found"}})
        if request.url.path == "/cspec/srvc":
            return _json_response(
                {
                    "data": {
                        "entTypes": {
                            "SequenceVariantInterpretation": {
                                "entCount": 1,
                                "iri": "https://example.test/cspec/SequenceVariantInterpretation",
                            }
                        }
                    }
                }
            )
        if request.url.path == "/cspec/SequenceVariantInterpretation/id":
            if page == 1 and calls[key] == 1:
                return httpx.Response(429, json={"status": {"code": 429}})
            if page == 1:
                return _json_response({"data": [_cspec_record()]})
            return _json_response({"status": {"code": 404, "name": "Not Found"}})
        return httpx.Response(404, json={"status": {"code": 404}})

    settings = _settings(
        tmp_path,
        clingen_erepo_base_url="https://example.test/evrepo",
        clingen_cspec_base_url="https://example.test/cspec",
    )
    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        result = fetch_clingen_source_snapshots(
            settings,
            output_dir=tmp_path / "source",
            max_pages=3,
            force=True,
            client=client,
            sleep=delays.append,
        )

    assert result.ready is True
    assert result.erepo_classification_count == 1
    assert result.erepo_page_count == 1
    assert result.cspec_entity_count == 1
    assert result.cspec_entity_type_counts == {"SequenceVariantInterpretation": 1}
    assert delays == [0.5]
    source_dir = tmp_path / "source"
    assert (source_dir / "clingen-erepo-classifications.jsonl").is_file()
    assert (source_dir / "clingen-cspec-entities.jsonl").is_file()
    assert "rpe65 local fixture" not in json.dumps(result.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in json.dumps(result.to_sanitized_dict()).lower()


def test_clingen_local_materialize_and_preflight_are_sanitized(
    tmp_path: Path,
    capsys,
) -> None:
    erepo_path, cspec_path = _write_source_jsonl(tmp_path)
    settings = _settings(tmp_path)

    result = materialize_clingen_local_store(
        settings,
        erepo_jsonl_files=[erepo_path],
        cspec_jsonl_files=[cspec_path],
        source_version="ClinGen local pytest snapshot",
        force=True,
    )

    assert result.ready is True
    assert result.classification_count == 1
    assert result.cspec_entity_count == 1
    assert result.cspec_link_count == 2
    inspection = inspect_clingen_local_store(settings, verify_checksum=True)
    assert inspection.ready is True
    assert inspection.checksum_verified is True
    assert inspection.source_version == "ClinGen local pytest snapshot"
    assert str(tmp_path).lower() not in json.dumps(inspection.to_sanitized_dict()).lower()

    exit_code = preflight_main(
        [
            "--db-path",
            str(settings.clingen_local_sqlite_path),
            "--manifest-path",
            str(settings.clingen_local_manifest_path),
            "--enabled",
            "--compact",
            "--require-ready",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert '"ready": true' in captured
    assert '"local_path_values_emitted": false' in captured
    assert str(tmp_path).lower() not in captured.lower()


def test_clingen_tool_uses_local_rows_without_fixture_bleed(tmp_path: Path) -> None:
    settings = _materialized_settings(tmp_path)
    tool = ClingenTool(settings)

    result = tool.get_evidence(_variant())

    assert result.status == "local"
    assert result.source_version == "ClinGen local pytest snapshot"
    assert result.summary["classification"] == "Likely Pathogenic"
    assert result.summary["expert_panel"]["vcep"]["name"] == "Inherited Retinal Dystrophies VCEP"
    assert result.summary["expert_panel"]["final_classification"] == "likely_pathogenic"
    assert result.summary["expert_panel"]["criteria"][0]["code"] == "PM2"

    no_hit = tool.get_evidence(SimpleNamespace(gene="ABCA4", transcript_hgvs="NM_000350.3:c.1A>G"))
    assert no_hit.status == "missing"
    assert no_hit.raw == {"records": []}
    assert "clingen_local_variant_not_found" in no_hit.warnings


def test_clingen_tool_local_request_path_skips_logical_checksum(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = _materialized_settings(tmp_path)

    def fail_checksum(*_args, **_kwargs):
        raise AssertionError("request-path ClinGen lookup must not logical-checksum the corpus")

    monkeypatch.setattr(clingen_local_module, "_logical_checksum", fail_checksum)

    result = ClingenTool(settings).get_evidence(_variant())

    assert result.status == "local"
    assert result.summary["classification"] == "Likely Pathogenic"


def test_clingen_raw_text_search_uses_indexed_terms_not_raw_json_like(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = _materialized_settings(tmp_path)

    def fail_raw_json_like(*_args, **_kwargs):
        raise AssertionError("request-path ClinGen search must not scan raw_json")

    monkeypatch.setattr(clingen_local_module, "_search_records_by_raw_text", fail_raw_json_like)

    rows, inspection, needs_live_fallback = ClinGenLocalStore(
        settings.clingen_local_sqlite_path,
        manifest_path=settings.clingen_local_manifest_path,
        enabled=True,
    ).search_records_by_raw_text(
        gene="RPE65",
        terms=["CA1421454"],
        limit=5,
        verify_checksum=False,
    )

    assert inspection.ready is True
    assert needs_live_fallback is False
    assert rows[0]["caId"] == "CA1421454"

    protein_rows, _inspection, _needs_live_fallback = ClinGenLocalStore(
        settings.clingen_local_sqlite_path,
        manifest_path=settings.clingen_local_manifest_path,
        enabled=True,
    ).search_records_by_raw_text(
        gene="RPE65",
        terms=["p.Asp87Gly"],
        limit=5,
        verify_checksum=False,
    )

    assert protein_rows[0]["caId"] == "CA1421454"


def test_lookup_sections_render_clingen_vcep_from_local_materialization(tmp_path: Path) -> None:
    settings = _materialized_settings(tmp_path)

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/lookup/sections",
            json={
                "gene": "RPE65",
                "cdna": "c.260A>G",
                "include": ["clingen_vcep"],
            },
        )

    assert response.status_code == 200
    clingen = response.json()["sections"]["clingen_vcep"]
    assert clingen["status"] == "available"
    assert clingen["payload"]["vcep"]["name"] == "Inherited Retinal Dystrophies VCEP"
    assert clingen["payload"]["final_classification"] == "likely_pathogenic"
    assert clingen["payload"]["criteria"][0]["applied_strength"] == "PM2_Moderate"
    assert clingen["payload"]["freshness"] == "fresh"
    assert clingen["freshness"]["source_status"] == "local"
    assert clingen["freshness"]["source_version"] == "ClinGen local pytest snapshot"
    assert clingen["warnings"] == []


def test_functional_evidence_reads_local_clingen_raw_records(tmp_path: Path) -> None:
    settings = _materialized_settings(tmp_path)
    result = ClingenTool(settings).get_evidence(_variant())

    summary = FunctionalEvidenceExtractor().build_for_lookup(
        _variant(),
        {},
        evidence_raw={"clingen": result.raw},
    )

    assert summary.total_count == 1
    assert summary.source_breakdown.clingen == 1
    assert summary.evidence_codes == ["PS3"]
    assert summary.source_asserted_codes == ["PS3_Supporting"]
    assert summary.studies[0].pmid == "31194252"


def test_provider_cache_health_reports_clingen_local_ready_without_paths(tmp_path: Path) -> None:
    settings = _materialized_settings(tmp_path)

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/provider-cache")

    assert response.status_code == 200
    clingen_local = response.json()["source_assets"]["clingen_local"]
    assert clingen_local["source_id"] == "eamos_clingen_local"
    assert clingen_local["status"] == "ready"
    assert clingen_local["ready"] is True
    assert clingen_local["enabled"] is True
    assert clingen_local["classification_count"] == 1
    assert clingen_local["cspec_entity_count"] == 1
    assert clingen_local["cspec_link_count"] == 2
    assert clingen_local["local_path_values_emitted"] is False
    assert clingen_local["raw_source_rows_emitted"] is False
    assert str(tmp_path).lower() not in json.dumps(response.json()).lower()


def _materialized_settings(tmp_path: Path) -> Settings:
    erepo_path, cspec_path = _write_source_jsonl(tmp_path)
    settings = _settings(
        tmp_path,
        clingen_local_enabled=True,
        use_real_apis=False,
    )
    result = materialize_clingen_local_store(
        settings,
        erepo_jsonl_files=[erepo_path],
        cspec_jsonl_files=[cspec_path],
        source_version="ClinGen local pytest snapshot",
        force=True,
    )
    assert result.ready is True
    return settings


def _settings(tmp_path: Path, **overrides) -> Settings:
    defaults = {
        "upload_dir": tmp_path / "uploads",
        "final_report_dir": tmp_path / "final_reports",
        "database_url": f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        "llm_provider": "mock",
        "use_real_apis": False,
        "workbench_live_design_enabled": False,
        "jwt_secret": "test-secret",
        "clingen_local_sqlite_path": tmp_path / "clingen-local.sqlite",
        "clingen_local_manifest_path": tmp_path / "clingen-local.manifest.json",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _write_source_jsonl(tmp_path: Path) -> tuple[Path, Path]:
    source_dir = tmp_path / "source"
    source_dir.mkdir(exist_ok=True)
    erepo_path = source_dir / "erepo.jsonl"
    cspec_path = source_dir / "cspec.jsonl"
    _write_jsonl(erepo_path, [_erepo_record()])
    _write_jsonl(cspec_path, [_cspec_record()])
    return erepo_path, cspec_path


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _variant():
    return SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        genomic_hgvs="NC_000001.11:g.68444869T>C",
        genomic_hg38="1-68444869-T-C",
        protein_change="p.Asp87Gly",
    )


def _erepo_record() -> dict:
    return {
        "_id": "AlleleRecords/rpe65-local-fixture",
        "_key": "rpe65-local-fixture",
        "affiliationId": "50081",
        "approvedDate": "2026-06-01",
        "caId": "CA1421454",
        "classification": "Likely Pathogenic",
        "condition": "Leber congenital amaurosis",
        "docVersion": "1.0.0",
        "ep": "Inherited Retinal Dystrophies VCEP",
        "gene": "RPE65",
        "hgvs": [
            "NM_000329.3:c.260A>G",
            "NC_000001.11:g.68444869T>C",
        ],
        "metCodes": ["PM2_Moderate", "PS3_Supporting"],
        "moi": "Autosomal recessive inheritance",
        "mondoId": "MONDO:0019173",
        "preferredVarTitle": "NM_000329.3:c.260A>G",
        "publishedDate": "2026-06-02",
        "sourceUrl": "https://erepo.genome.network/evrepo/ui/classification/rpe65-local",
        "summaryDesc": (
            "RPE65 local fixture: a minigene assay showed abnormal splicing "
            "for NM_000329.3:c.260A>G / p.Asp87Gly "
            "(PMID:31194252, PS3_Supporting). This variant also meets PM2_Moderate."
        ),
        "uuid": "local-rpe65-vcep",
        "vcepId": "50081",
        "vcepName": "Inherited Retinal Dystrophies VCEP",
        "versionsList": ["1.0.0"],
    }


def _cspec_record() -> dict:
    return {
        "entContent": {
            "description": "ACMG/AMP sequence variant interpretation criteria",
            "shortTitle": "RPE65 pytest criteria",
            "version": "1.0.0",
        },
        "entId": "GN167",
        "entIri": "https://cspec.genome.network/cspec/SequenceVariantInterpretation/id/GN167",
        "entType": "SequenceVariantInterpretation",
        "ld": [
            {
                "CriteriaCode": [
                    {
                        "entId": "PM2",
                        "entType": "CriteriaCode",
                        "ldhId": "criterion-pm2",
                    }
                ]
            },
            {
                "RuleSet": [
                    {
                        "entId": "ruleset-rpe65",
                        "entType": "RuleSet",
                        "ldhId": "ruleset-rpe65",
                    }
                ]
            },
        ],
        "ldhId": "cspec-rpe65",
        "ldhIri": "https://cspec.genome.network/cspec/SequenceVariantInterpretation/id/cspec-rpe65",
        "modified": "2026-06-01T00:00:00Z",
    }


def _json_response(payload: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload)
