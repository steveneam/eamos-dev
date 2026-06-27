from __future__ import annotations

from hashlib import md5
import json
from pathlib import Path

import pytest

from app.cli import (
    eamos_pubmed_local_materialize,
    eamos_pubmed_local_preflight,
    eamos_pubmed_seed_manifest,
)
from app.services.pubmed_local import read_seed_queries
from app.services.pubmed_seed_manifest import (
    PubMedSeedManifestError,
    load_seed_manifest,
    parse_seed_manifest,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "app" / "fixtures"
MANIFEST_PATH = FIXTURE_ROOT / "literature" / "pmat_seed_manifest_tiny.json"
PUBMED_XML = FIXTURE_ROOT / "tools" / "pubmed_local_sample.xml"


def test_tiny_seed_manifest_validates_and_renders_pubmed_query_tsv(tmp_path: Path) -> None:
    manifest = load_seed_manifest(MANIFEST_PATH)

    assert manifest.corpus_label == "targeted_seed"
    assert manifest.source_scope == "tiny_fixture"
    assert manifest.seed_count == 4
    assert manifest.genes == ("ABCA4", "CEP290", "RPE65")
    assert manifest.corpus_labels == ("targeted_seed",)

    query_file = tmp_path / "pubmed-seed.tsv"
    manifest.write_pubmed_query_tsv(query_file)
    seeds = read_seed_queries(query_file)

    assert [(seed.gene, seed.scope) for seed in seeds] == [
        ("RPE65", "variant"),
        ("RPE65", "gene"),
        ("ABCA4", "variant"),
        ("CEP290", "variant"),
    ]
    assert seeds[0].variant_terms == (
        "c.260A>G",
        "NM_000329.3:c.260A>G",
        "p.Asp87Gly",
        "rs1645931040",
        "1-68444869-T-C",
    )
    assert seeds[1].variant_terms == ()
    assert "c.5461-10T>C" in seeds[2].variant_terms


def test_tiny_seed_manifest_sanitized_report_has_no_rows_paths_or_sensitive_fields() -> None:
    manifest = load_seed_manifest(MANIFEST_PATH)

    report = manifest.to_sanitized_dict()
    encoded = json.dumps(report).lower()

    assert report["guardrails"]["network"]["used"] is False
    assert report["guardrails"]["materialization"] == "not_used"
    assert report["seed_count"] == 4
    assert "seed_id" not in encoded
    assert "c.260a>g" not in encoded
    assert "d:\\" not in encoded
    assert "/var/data/" not in encoded
    assert "api_key" not in encoded
    assert "request_headers" not in encoded
    assert "patient_note" not in encoded


def test_seed_manifest_cli_writes_query_file_without_leaking_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    query_file = tmp_path / "pubmed-seed.tsv"

    exit_code = eamos_pubmed_seed_manifest.main(
        [
            "--manifest-path",
            str(MANIFEST_PATH),
            "--write-query-file",
            str(query_file),
            "--compact",
            "--require-ready",
        ]
    )

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ready"
    assert report["pubmed_query_file_name"] == "pubmed-seed.tsv"
    assert report["validation"]["seed_count"] == 4
    encoded = json.dumps(report).lower()
    assert str(tmp_path).lower() not in encoded
    assert str(MANIFEST_PATH.parent).lower() not in encoded
    assert len(read_seed_queries(query_file)) == 4


def test_seed_manifest_drives_pubmed_local_fixture_materialization_and_preflight(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    query_file = tmp_path / "pmat-seed.tsv"
    seed_exit = eamos_pubmed_seed_manifest.main(
        [
            "--manifest-path",
            str(MANIFEST_PATH),
            "--write-query-file",
            str(query_file),
            "--compact",
            "--require-ready",
        ]
    )
    assert seed_exit == 0
    capsys.readouterr()

    xml_path = tmp_path / "pubmed25n0001.xml"
    xml_path.write_bytes(PUBMED_XML.read_bytes())
    xml_path.with_name(f"{xml_path.name}.md5").write_text(
        f"{md5(xml_path.read_bytes(), usedforsecurity=False).hexdigest()}  {xml_path.name}\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "pubmed-local.sqlite"
    materialization_manifest = tmp_path / "pubmed-local.manifest.json"

    materialize_exit = eamos_pubmed_local_materialize.main(
        [
            "--from-xml-file",
            str(xml_path),
            "--query-file",
            str(query_file),
            "--output",
            str(db_path),
            "--manifest",
            str(materialization_manifest),
            "--source-version",
            "pmat-tiny-fixture-2026-06-27",
            "--xml-source-kind",
            "baseline",
            "--verify-md5-sidecars",
            "--compact",
            "--require-ready",
        ]
    )

    assert materialize_exit == 0
    materialize_report = json.loads(capsys.readouterr().out)
    materialization = materialize_report["materialization"]
    assert materialize_report["guardrails"]["network"] == {"provider": None, "used": False}
    assert materialize_report["guardrails"]["startup_download"] == "not_used"
    assert materialize_report["guardrails"]["request_time_materialization"] == "not_used"
    assert materialization["ready"] is True
    assert materialization["status"] == "ready"
    assert materialization["article_count"] == 2
    assert materialization["licensed_abstract_count"] == 1
    assert materialization["metadata_only_count"] == 1
    assert materialization["deleted_count"] == 1
    assert materialization["coverage_count"] == 6
    assert materialization["source_file_count"] == 1
    assert materialization["source_kind_counts"] == {"pubmed_baseline": 1}
    assert materialization["input_checksum_status"] == "verified"
    assert materialization["input_checksum_verified_count"] == 1

    preflight_exit = eamos_pubmed_local_preflight.main(
        [
            "--db-path",
            str(db_path),
            "--manifest-path",
            str(materialization_manifest),
            "--compact",
            "--require-ready",
        ]
    )

    assert preflight_exit == 0
    preflight_report = json.loads(capsys.readouterr().out)
    assert preflight_report["ready"] is True
    assert preflight_report["status"] == "ready"
    assert preflight_report["checksum_verified"] is True
    assert preflight_report["article_count"] == 2
    assert preflight_report["licensed_abstract_count"] == 1
    assert preflight_report["metadata_only_count"] == 1
    assert preflight_report["coverage"]["queries"] == 6
    assert preflight_report["local_path_values_emitted"] is False
    assert preflight_report["abstract_values_emitted"] is False
    assert preflight_report["secret_values_emitted"] is False
    encoded = json.dumps(preflight_report).lower()
    assert str(tmp_path).lower() not in encoded
    assert "asp87gly variant was observed" not in encoded


def test_seed_manifest_rejects_variant_without_pubmed_alias() -> None:
    payload = _valid_payload()
    payload["seeds"][0]["variant_aliases"] = {}

    with pytest.raises(PubMedSeedManifestError) as exc:
        parse_seed_manifest(payload)

    assert "variant scope needs a PubMed-compatible variant alias" in str(exc.value)


def test_seed_manifest_rejects_user_patient_or_request_payload_fields() -> None:
    payload = _valid_payload()
    payload["seeds"][0]["patient_note"] = "Do not allow clinical free text here."
    payload["seeds"][1]["clinical_trials"]["request_headers"] = {"Authorization": "Bearer test"}

    with pytest.raises(PubMedSeedManifestError) as exc:
        parse_seed_manifest(payload)

    message = str(exc.value)
    assert "patient_note is not allowed" in message
    assert "request_headers is not allowed" in message


def _valid_payload() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
