from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from app.cli import eamos_mavedb_local_materialize
from app.core.config import Settings
from app.services.build_ledger import build_backend_build_ledger
from app.services.mavedb_local import (
    MAVEDB_FIXTURE_RELEASE_PREFIX,
    MAVEDB_FIXTURE_SOURCE_URL,
    MAVEDB_LOCAL_SCHEMA_VERSION,
    MaveDbLocalStore,
    inspect_mavedb_local_store,
    materialize_mavedb_local_store,
    mavedb_record_to_canonical_dict,
    verify_mavedb_archive_file,
)


def _row(
    *,
    score_set_urn: str,
    variant_urn: str,
    hgvs: str,
    score: str,
    license_value: str | None = "CC0-1.0",
    data_usage_policy=None,
    target_accession: str = "NM_000329.3",
    target_id: str = "target:rpe65-nm_000329.3",
    vrs_id: str | None = None,
    genomic_identity: str | None = None,
    source_url: str | None = "https://attacker.invalid/not-authoritative",
) -> dict:
    score_set = {
        "urn": score_set_urn,
        "license": license_value,
        "dataUsagePolicy": data_usage_policy,
        "deprecated": False,
    }
    return {
        "score_set": score_set,
        "target": {
            "id": target_id,
            "accession": target_accession,
            "sequence_checksum": "sha256:synthetic-rpe65-target",
            "gene": "RPE65",
        },
        "variant_score": {
            "urn": variant_urn,
            "mave_hgvs": hgvs,
            "raw_score": score,
            "score_column": "score",
            "score_unit": "assay_specific_raw",
            "vrs_id": vrs_id,
            "genomic_identity": genomic_identity,
        },
        "source_url": source_url,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        jwt_secret="test-secret",
        mavedb_local_enabled=True,
        mavedb_local_sqlite_path=tmp_path / "mavedb-local.sqlite",
        mavedb_local_manifest_path=tmp_path / "mavedb-local.manifest.json",
    )


def _proof(path: Path):
    return verify_mavedb_archive_file(
        path,
        expected_digest_algorithm="sha256",
        expected_digest_value=sha256(path.read_bytes()).hexdigest(),
        release_doi=f"{MAVEDB_FIXTURE_RELEASE_PREFIX}pytest",
        source_url=MAVEDB_FIXTURE_SOURCE_URL,
        allow_synthetic_fixture=True,
    )


def _materialized_store(tmp_path: Path):
    source = tmp_path / "synthetic-mavedb-v2.jsonl"
    rows = [
        _row(
            score_set_urn="urn:mavedb:0001-a-1",
            variant_urn="urn:mavedb:0001-a-1#1",
            hgvs="c.1301C>T",
            score="0.1200",
            vrs_id="ga4gh:VA.rpe65-a434v",
            genomic_identity="NC_000001.11:g.68452000C>T",
        ),
        _row(
            score_set_urn="urn:mavedb:0001-a-1",
            variant_urn="urn:mavedb:0001-a-1#2",
            hgvs="c.260A>G",
            score="-1.750",
            vrs_id="ga4gh:VA.rpe65-d87g",
            genomic_identity="NC_000001.11:g.68444869T>C",
        ),
        _row(
            score_set_urn="urn:mavedb:0002-a-1",
            variant_urn="urn:mavedb:0002-a-1#1",
            hgvs="c.1301C>T",
            score="1.2300",
            target_id="target:rpe65-nm_000329.3-assay2",
            vrs_id="ga4gh:VA.rpe65-a434v",
            genomic_identity="NC_000001.11:g.68452000C>T",
        ),
        _row(
            score_set_urn="urn:mavedb:0003-a-1",
            variant_urn="urn:mavedb:0003-a-1#1",
            hgvs="c.1301C>T",
            score="0.8",
            license_value="CC BY 4.0",
        ),
        _row(
            score_set_urn="urn:mavedb:0004-a-1",
            variant_urn="urn:mavedb:0004-a-1#1",
            hgvs="c.1301C>T",
            score="0.9",
            data_usage_policy={"commercialUse": "prohibited"},
        ),
    ]
    _write_jsonl(source, rows)
    settings = _settings(tmp_path)
    result = materialize_mavedb_local_store(
        settings,
        jsonl_files=[source],
        archive_proof=_proof(source),
        source_version="synthetic-v2-fixture",
    )
    return source, settings, result


def test_schema_v2_keeps_multiple_variants_and_exact_score_set_measurements(
    tmp_path: Path,
) -> None:
    source, settings, result = _materialized_store(tmp_path)

    assert result.ready is True
    assert result.status == "fixture_ready"
    assert result.schema_version == MAVEDB_LOCAL_SCHEMA_VERSION
    assert result.archive_digest_verified is True
    assert result.accepted_count == 3
    assert result.rejected_count == 2
    assert result.warnings == (
        "mavedb_non_cc0_rejected:urn:mavedb:0003-a-1#1",
        "mavedb_data_usage_policy_rejected:urn:mavedb:0004-a-1#1",
        "synthetic_fixture_not_public",
    )
    assert settings.mavedb_local_sqlite_path.is_file()
    assert settings.mavedb_local_manifest_path.is_file()

    unverified = MaveDbLocalStore(settings.mavedb_local_sqlite_path).inspect(verify_checksum=False)
    assert unverified.ready is False
    assert unverified.status == "verification_required"
    assert unverified.to_sanitized_dict()["public_serialization_allowed"] is False

    inspection = inspect_mavedb_local_store(settings, verify_checksum=True)
    assert inspection.ready is True
    assert inspection.status == "fixture_ready"
    assert inspection.archive_digest_verified is True
    assert inspection.checksum_verified is True
    assert inspection.source_version == "synthetic-v2-fixture"
    encoded = json.dumps(inspection.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in encoded
    assert "nm_000329" not in encoded
    assert source.name not in encoded

    records, request_inspection = MaveDbLocalStore(
        settings.mavedb_local_sqlite_path
    ).search_records(
        SimpleNamespace(vrs_id="ga4gh:VA.rpe65-a434v"),
        limit=10,
    )

    assert request_inspection.ready is True
    assert [record.score_set_id for record in records] == [
        "urn:mavedb:0001-a-1",
        "urn:mavedb:0002-a-1",
    ]
    assert [record.score for record in records] == [Decimal("0.12"), Decimal("1.23")]
    assert all(record.match_level == "exact_vrs" for record in records)
    assert all(record.archive_digest_verified for record in records)
    assert all(record.local_logical_checksum_verified for record in records)
    assert all(
        record.source_url.startswith("https://www.mavedb.org/score-sets/urn:mavedb:")
        for record in records
    )
    assert all("attacker.invalid" not in record.source_url for record in records)
    assert mavedb_record_to_canonical_dict(records[0])["variant_score"]["raw_score"] == "0.12"

    ledger_items = {item["item_id"]: item for item in build_backend_build_ledger(settings)["items"]}
    assert ledger_items["mavedb"]["status"] == "fixture_ready"
    assert ledger_items["mavedb"]["public_serialization_allowed"] is False
    assert ledger_items["mavedb"]["source_ids"] == [
        "mavedb_cc0_bulk",
        "mavedb_public_api_metadata",
    ]
    assert ledger_items["mavedb"]["blockers"] == [
        "archive_proof_and_logical_checksum_materialization"
    ]


def test_matching_precedence_is_exact_and_never_uses_loose_sequence_tokens(
    tmp_path: Path,
) -> None:
    _, settings, _ = _materialized_store(tmp_path)
    store = MaveDbLocalStore(settings.mavedb_local_sqlite_path)

    genomic, _ = store.search_records(
        SimpleNamespace(genomic_hgvs="NC_000001.11:g.68444869T>C"),
        limit=10,
    )
    target_hgvs, _ = store.search_records(
        SimpleNamespace(transcript_hgvs="NM_000329.3:c.260A>G"),
        limit=10,
    )
    loose, _ = store.search_records(
        SimpleNamespace(gene="RPE65", protein_change="p.Asp87Gly"),
        limit=10,
    )
    ambiguous, _ = store.search_records(
        SimpleNamespace(
            vrs_id=["ga4gh:VA.one", "ga4gh:VA.two"],
            transcript_hgvs=["NM_000329.3:c.260A>G", "NM_000329.3:c.1301C>T"],
        ),
        limit=10,
    )

    assert len(genomic) == 1
    assert genomic[0].match_level == "exact_genomic_identity"
    assert len(target_hgvs) == 1
    assert target_hgvs[0].match_level == "exact_target_accession_mave_hgvs"
    assert loose == []
    assert ambiguous == []


def test_unverified_archive_or_disabled_request_verification_never_returns_records(
    tmp_path: Path,
) -> None:
    source = tmp_path / "synthetic.jsonl"
    _write_jsonl(
        source,
        [
            _row(
                score_set_urn="urn:mavedb:0001-a-1",
                variant_urn="urn:mavedb:0001-a-1#1",
                hgvs="c.260A>G",
                score="0.5",
            )
        ],
    )
    settings = _settings(tmp_path)
    self_declared_proof = verify_mavedb_archive_file(
        source,
        expected_digest_algorithm="sha256",
        expected_digest_value=sha256(source.read_bytes()).hexdigest(),
    )
    assert self_declared_proof.upstream_digest_verified is False

    bad_proof = verify_mavedb_archive_file(
        source,
        expected_digest_algorithm="sha256",
        expected_digest_value="0" * 64,
    )

    refused = materialize_mavedb_local_store(
        settings,
        jsonl_files=[source],
        archive_proof=bad_proof,
    )

    assert refused.ready is False
    assert refused.status == "archive_proof_required"
    assert not settings.mavedb_local_sqlite_path.exists()

    _, settings, _ = _materialized_store(tmp_path / "verified")
    records, inspection = MaveDbLocalStore(settings.mavedb_local_sqlite_path).search_records(
        SimpleNamespace(transcript_hgvs="NM_000329.3:c.260A>G"),
        limit=10,
        verify_checksum=False,
    )
    assert records == []
    assert inspection.status == "verification_required"


def test_local_logical_checksum_mismatch_fails_readiness(tmp_path: Path) -> None:
    _, settings, _ = _materialized_store(tmp_path)
    with sqlite3.connect(settings.mavedb_local_sqlite_path) as conn:
        conn.execute(
            "update mavedb_variant_score set raw_score = '999' where variant_urn = ?",
            ("urn:mavedb:0001-a-1#1",),
        )
        conn.commit()

    inspection = inspect_mavedb_local_store(settings, verify_checksum=True)

    assert inspection.ready is False
    assert inspection.status == "checksum_mismatch"
    assert inspection.to_sanitized_dict()["public_serialization_allowed"] is False


def test_top_level_license_url_and_ambiguous_context_are_not_trusted(
    tmp_path: Path,
) -> None:
    source = tmp_path / "untrusted.jsonl"
    missing_authoritative_license = _row(
        score_set_urn="urn:mavedb:0001-a-1",
        variant_urn="urn:mavedb:0001-a-1#1",
        hgvs="c.260A>G",
        score="0.5",
        license_value=None,
    )
    missing_authoritative_license["license"] = "CC0"
    ambiguous = _row(
        score_set_urn="urn:mavedb:0002-a-1",
        variant_urn="urn:mavedb:0002-a-1#1",
        hgvs="c.260A>G",
        score="0.6",
    )
    ambiguous["targets"] = [{"id": "one"}, {"id": "two"}]
    _write_jsonl(source, [missing_authoritative_license, ambiguous])
    settings = _settings(tmp_path)

    result = materialize_mavedb_local_store(
        settings,
        jsonl_files=[source],
        archive_proof=_proof(source),
    )

    assert result.ready is True
    assert result.accepted_count == 0
    assert "mavedb_local_incomplete_v2_record" in result.warnings
    assert "mavedb_local_ambiguous_multi_context_rejected" in result.warnings


def test_mavedb_local_materialize_cli_requires_and_verifies_archive_proof(
    tmp_path: Path,
    capsys,
) -> None:
    source = tmp_path / "mavedb.jsonl"
    _write_jsonl(
        source,
        [
            _row(
                score_set_urn="urn:mavedb:0001-a-1",
                variant_urn="urn:mavedb:0001-a-1#1",
                hgvs="c.1301C>T",
                score="0.12",
            )
        ],
    )
    db_path = tmp_path / "mavedb-local.sqlite"
    manifest_path = tmp_path / "mavedb-local.manifest.json"
    digest = sha256(source.read_bytes()).hexdigest()

    exit_code = eamos_mavedb_local_materialize.main(
        [
            "--input-jsonl",
            str(source),
            "--archive-path",
            str(source),
            "--archive-digest-algorithm",
            "sha256",
            "--archive-digest",
            digest,
            "--fixture-only",
            "--output",
            str(db_path),
            "--manifest-path",
            str(manifest_path),
            "--source-version",
            "mavedb-test-v2",
            "--require-ready",
            "--compact",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "eamos_mavedb_local_materialize"
    assert payload["guardrails"] == {
        "network": "not_used",
        "provider_flips": "not_used",
        "render": "not_used",
        "startup_downloads": "not_used",
        "supabase": "not_used",
    }
    assert payload["materialization"]["ready"] is True
    assert payload["materialization"]["status"] == "fixture_ready"
    assert payload["materialization"]["archive_digest_verified"] is True
    encoded = json.dumps(payload).lower()
    assert str(tmp_path).lower() not in encoded
    assert "nm_000329" not in encoded
