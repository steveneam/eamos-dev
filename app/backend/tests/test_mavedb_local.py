from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
import inspect
import json
from pathlib import Path
import sqlite3
import stat
from types import SimpleNamespace
from zipfile import ZipFile, ZipInfo

import pytest

from app.cli import eamos_mavedb_local_materialize
from app.core.config import Settings
from app.services.build_ledger import build_backend_build_ledger
from app.services.mavedb_archive import DEFAULT_MAVEDB_ARCHIVE_LIMITS
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
from tests.mavedb_fixture import score_set, variant_row, write_mavedb_archive

SS1 = "urn:mavedb:00000001-a-1"
SS2 = "urn:mavedb:00000002-a-1"
SS3 = "urn:mavedb:00000003-a-1"
SS4 = "urn:mavedb:00000004-a-1"


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


def _base_score_sets() -> list[dict]:
    return [
        score_set(
            SS1,
            [
                variant_row(
                    f"{SS1}#1",
                    "NM_000329.3:c.1301C>T",
                    "0.1200",
                    hgvs_pro="NM_000329.3:p.Ala434Val",
                    SE="0.1150",
                    vrs_id="ga4gh:VA.rpe65-a434v",
                    genomic_identity="NC_000001.11:g.68452000C>T",
                    mapping_assembly="GRCh38",
                ),
                variant_row(
                    f"{SS1}#2",
                    "NM_000329.3:c.260A>G",
                    "-1.750",
                    SE="0.250",
                    vrs_id="ga4gh:VA.rpe65-d87g",
                    genomic_identity="NC_000001.11:g.68444869T>C",
                    mapping_assembly="GRCh38",
                ),
            ],
        ),
        score_set(
            SS2,
            [
                variant_row(
                    f"{SS2}#1",
                    "NM_000329.3:c.1301C>T",
                    "1.2300",
                    hgvs_pro="NM_000329.3:p.Ala434Val",
                    SE="0.3300",
                    vrs_id="ga4gh:VA.rpe65-a434v",
                    genomic_identity="NC_000001.11:g.68452000C>T",
                    mapping_assembly="GRCh38",
                )
            ],
            target_id=2,
        ),
        score_set(
            SS3,
            [variant_row(f"{SS3}#1", "NM_000329.3:c.1301C>T", "0.8")],
            license_short_name="CC BY 4.0",
            license_version=None,
        ),
        score_set(
            SS4,
            [variant_row(f"{SS4}#1", "NM_000329.3:c.1301C>T", "0.9")],
            data_usage_policy="Pre-publication analysis is restricted.",
        ),
    ]


def _materialized_store(tmp_path: Path):
    archive = write_mavedb_archive(tmp_path / "synthetic-mavedb-v2.zip", _base_score_sets())
    settings = _settings(tmp_path)
    result = materialize_mavedb_local_store(
        settings,
        archive_path=archive,
        archive_proof=_proof(archive),
        source_version="synthetic-v2-fixture",
    )
    return archive, settings, result


def test_archive_materialization_preserves_identity_precision_and_provenance(
    tmp_path: Path,
) -> None:
    archive, settings, result = _materialized_store(tmp_path)

    assert result.ready is True
    assert result.status == "fixture_ready"
    assert result.schema_version == MAVEDB_LOCAL_SCHEMA_VERSION
    assert result.archive_digest_verified is True
    assert result.archive_sha256 == sha256(archive.read_bytes()).hexdigest()
    assert result.archive_size_bytes == archive.stat().st_size
    assert result.archive_citation == "PMID:39838450"
    assert result.metadata_schema_version == "mavedb.bulk.synthetic.v4"
    assert result.archive_member_count == 5
    assert result.archive_member_digests_verified is True
    assert result.accepted_count == 3
    assert result.rejected_count == 2
    assert result.warnings == (
        "mavedb_data_usage_policy_rejected:1",
        "mavedb_non_cc0_rejected:1",
        "synthetic_fixture_not_public",
    )

    unverified = MaveDbLocalStore(settings.mavedb_local_sqlite_path).inspect(verify_checksum=False)
    assert unverified.ready is False
    assert unverified.status == "verification_required"
    assert unverified.to_sanitized_dict()["public_serialization_allowed"] is False

    inspection = inspect_mavedb_local_store(settings, verify_checksum=True)
    assert inspection.ready is True
    assert inspection.archive_member_digests_verified is True
    assert inspection.archive_citation == "PMID:39838450"
    encoded = json.dumps(inspection.to_sanitized_dict()).lower()
    assert str(tmp_path).lower() not in encoded
    assert "attacker.invalid" not in encoded
    assert "nm_000329" not in encoded

    records, request_inspection = MaveDbLocalStore(
        settings.mavedb_local_sqlite_path
    ).search_records(SimpleNamespace(vrs_id="ga4gh:VA.rpe65-a434v"), limit=10)

    assert request_inspection.ready is True
    assert [record.score_set_id for record in records] == [SS1, SS2]
    assert [record.score for record in records] == [Decimal("0.12"), Decimal("1.23")]
    assert [record.variant_score.raw_score_source for record in records] == ["0.1200", "1.2300"]
    assert records[0].variant_score.uncertainty_values[0].source_value == "0.1150"
    assert records[0].variant_score.uncertainty_values[0].parsed_value == Decimal("0.115")
    assert all(record.match_level == "exact_vrs" for record in records)
    assert all(record.archive_member_digests_verified for record in records)
    assert all(record.local_logical_checksum_verified for record in records)
    assert all(
        record.source_url == f"https://www.mavedb.org/score-sets/{record.score_set_id}"
        for record in records
    )
    canonical = mavedb_record_to_canonical_dict(records[0])
    assert canonical["variant_score"]["raw_score"] == "0.1200"
    assert canonical["variant_score"]["parsed_raw_score"] == "0.12"
    assert canonical["variant_score"]["uncertainty_values"][0]["parsed_value"] == "0.115"

    ledger_items = {item["item_id"]: item for item in build_backend_build_ledger(settings)["items"]}
    assert ledger_items["mavedb"]["status"] == "fixture_ready"
    assert ledger_items["mavedb"]["public_serialization_allowed"] is False

    limited, limited_inspection = MaveDbLocalStore(
        settings.mavedb_local_sqlite_path
    ).search_records(SimpleNamespace(vrs_id="ga4gh:VA.rpe65-a434v"), limit=1)
    assert limited == []
    assert "mavedb_exact_match_limit_exceeded" in limited_inspection.warnings


def test_matching_falls_through_exact_identities_and_never_uses_loose_tokens(
    tmp_path: Path,
) -> None:
    _, settings, _ = _materialized_store(tmp_path)
    store = MaveDbLocalStore(settings.mavedb_local_sqlite_path)

    genomic, _ = store.search_records(
        SimpleNamespace(genomic_hg38="NC_000001.11:g.68444869T>C"), limit=10
    )
    transcript, _ = store.search_records(
        SimpleNamespace(
            genomic_hg38="NC_000001.11:g.not-present",
            transcript_hgvs="NM_000329.3:c.260A>G",
        ),
        limit=10,
    )
    loose, _ = store.search_records(
        SimpleNamespace(gene="RPE65", protein_change="p.Asp87Gly"), limit=10
    )
    ambiguous_input, _ = store.search_records(
        SimpleNamespace(
            vrs_id=["ga4gh:VA.one", "ga4gh:VA.two"],
            transcript_hgvs=["NM_000329.3:c.260A>G", "NM_000329.3:c.1301C>T"],
        ),
        limit=10,
    )

    assert len(genomic) == 1
    assert genomic[0].match_level == "exact_genomic_identity"
    assert len(transcript) == 1
    assert transcript[0].match_level == "exact_target_accession_mave_hgvs"
    assert loose == []
    assert ambiguous_input == []

    transcript_drift, _ = store.search_records(
        SimpleNamespace(transcript_hgvs="NM_000329.2:c.260A>G"), limit=10
    )
    assembly_drift, _ = store.search_records(
        SimpleNamespace(
            genomic_hgvs="NC_000001.11:g.68444869T>C",
            assembly="GRCh37",
        ),
        limit=10,
    )
    assert transcript_drift == []
    assert assembly_drift == []


def test_multi_target_or_multi_variant_exact_context_fails_closed(tmp_path: Path) -> None:
    target2 = "NM_004958.4"
    sets = [
        score_set(
            SS1,
            [
                variant_row(
                    f"{SS1}#1",
                    "NM_000329.3:c.1301C>T",
                    "0.1",
                    vrs_id="ga4gh:VA.shared",
                )
            ],
        ),
        score_set(
            SS2,
            [
                variant_row(
                    f"{SS2}#1",
                    f"{target2}:c.100A>G",
                    "0.2",
                    vrs_id="ga4gh:VA.shared",
                )
            ],
            target_accession=target2,
            target_gene="MTOR",
        ),
    ]
    archive = write_mavedb_archive(tmp_path / "ambiguous.zip", sets)
    settings = _settings(tmp_path)
    result = materialize_mavedb_local_store(
        settings, archive_path=archive, archive_proof=_proof(archive)
    )
    assert result.ready is True

    records, inspection = MaveDbLocalStore(settings.mavedb_local_sqlite_path).search_records(
        SimpleNamespace(vrs_id="ga4gh:VA.shared"), limit=10
    )
    assert records == []
    assert "mavedb_ambiguous_exact_context" in inspection.warnings


def test_deprecated_score_set_is_preserved_but_never_returned(tmp_path: Path) -> None:
    superseding = "urn:mavedb:00000001-a-2"
    sets = [
        score_set(
            SS1,
            [variant_row(f"{SS1}#1", "NM_000329.3:c.1301C>T", "0.1")],
            superseded_by=superseding,
        ),
        score_set(
            superseding,
            [variant_row(f"{superseding}#1", "NM_000329.3:c.1301C>T", "0.2")],
        ),
    ]
    archive = write_mavedb_archive(tmp_path / "deprecated.zip", sets)
    settings = _settings(tmp_path)
    result = materialize_mavedb_local_store(
        settings, archive_path=archive, archive_proof=_proof(archive)
    )
    assert result.accepted_count == 2
    with sqlite3.connect(settings.mavedb_local_sqlite_path) as conn:
        deprecated = conn.execute(
            "select deprecated, superseded_by from mavedb_score_set where score_set_urn = ?",
            (SS1,),
        ).fetchone()
    assert deprecated == (1, superseding)
    records, _ = MaveDbLocalStore(settings.mavedb_local_sqlite_path).search_records(
        SimpleNamespace(transcript_hgvs="NM_000329.3:c.1301C>T"), limit=10
    )
    assert [record.score_set_id for record in records] == [superseding]


def test_authoritative_metadata_license_cannot_be_counterfeited_by_csv_comment(
    tmp_path: Path,
) -> None:
    sets = [
        score_set(
            SS1,
            [variant_row(f"{SS1}#1", "NM_000329.3:c.1301C>T", "0.5")],
            license_short_name=None,
        )
    ]
    archive = write_mavedb_archive(tmp_path / "unknown-license.zip", sets)
    _prepend_score_comment(archive, SS1, "# license: CC0-1.0\n# source_url: https://evil\n")
    settings = _settings(tmp_path)
    result = materialize_mavedb_local_store(
        settings, archive_path=archive, archive_proof=_proof(archive)
    )
    assert result.ready is True
    assert result.accepted_count == 0
    assert result.rejected_count == 1
    assert "mavedb_non_cc0_rejected:1" in result.warnings


def test_unverified_archive_and_checksum_mismatch_never_return_records(tmp_path: Path) -> None:
    archive = write_mavedb_archive(tmp_path / "archive.zip", [_base_score_sets()[0]])
    settings = _settings(tmp_path)
    self_declared = verify_mavedb_archive_file(
        archive,
        expected_digest_algorithm="sha256",
        expected_digest_value=sha256(archive.read_bytes()).hexdigest(),
    )
    assert self_declared.upstream_digest_verified is False
    refused = materialize_mavedb_local_store(
        settings, archive_path=archive, archive_proof=self_declared
    )
    assert refused.status == "archive_proof_required"
    assert not settings.mavedb_local_sqlite_path.exists()

    _, verified_settings, _ = _materialized_store(tmp_path / "verified")
    with sqlite3.connect(verified_settings.mavedb_local_sqlite_path) as conn:
        conn.execute(
            "update mavedb_variant_score set raw_score_source = '999' where variant_urn = ?",
            (f"{SS1}#1",),
        )
        conn.commit()
    inspection = inspect_mavedb_local_store(verified_settings, verify_checksum=True)
    assert inspection.ready is False
    assert inspection.status == "checksum_mismatch"


def test_materialization_rejects_archive_output_and_manifest_path_collisions(
    tmp_path: Path,
) -> None:
    archive = write_mavedb_archive(tmp_path / "archive.zip", [_base_score_sets()[0]])
    original = archive.read_bytes()
    settings = _settings(tmp_path)

    archive_collision = materialize_mavedb_local_store(
        settings,
        archive_path=archive,
        archive_proof=_proof(archive),
        output_path=archive,
        force=True,
    )
    shared_output = tmp_path / "same.sqlite"
    output_manifest_collision = materialize_mavedb_local_store(
        settings,
        archive_path=archive,
        archive_proof=_proof(archive),
        output_path=shared_output,
        manifest_path=shared_output,
    )

    assert archive_collision.status == "materialization_path_collision"
    assert output_manifest_collision.status == "materialization_path_collision"
    assert archive.read_bytes() == original
    assert not shared_output.exists()


@pytest.mark.parametrize(
    ("member_name", "expected_code"),
    [
        ("../escape.csv", "unsafe_member_path"),
        ("/absolute.csv", "unsafe_member_path"),
        ("unexpected.txt", "unexpected_member"),
    ],
)
def test_hostile_archive_members_fail_atomically(
    tmp_path: Path,
    member_name: str,
    expected_code: str,
) -> None:
    archive = write_mavedb_archive(
        tmp_path / "hostile.zip",
        [_base_score_sets()[0]],
        extra_members=[(member_name, "hostile")],
    )
    settings = _settings(tmp_path)
    settings.mavedb_local_sqlite_path.write_bytes(b"existing-destination")
    result = materialize_mavedb_local_store(
        settings,
        archive_path=archive,
        archive_proof=_proof(archive),
        force=True,
    )
    assert result.status == f"archive_rejected:{expected_code}"
    assert settings.mavedb_local_sqlite_path.read_bytes() == b"existing-destination"
    encoded = json.dumps(result.to_sanitized_dict())
    assert member_name not in encoded


def test_symlink_and_resource_limit_archives_are_rejected(tmp_path: Path) -> None:
    link = ZipInfo(f"{SS1}_counts.csv")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    symlink_archive = write_mavedb_archive(
        tmp_path / "symlink.zip",
        [_base_score_sets()[0]],
        extra_members=[(link, "main.json")],
    )
    settings = _settings(tmp_path / "symlink")
    symlink_result = materialize_mavedb_local_store(
        settings,
        archive_path=symlink_archive,
        archive_proof=_proof(symlink_archive),
    )
    assert symlink_result.status == "archive_rejected:unsupported_member_type"

    limited_archive = write_mavedb_archive(tmp_path / "limited.zip", [_base_score_sets()[0]])
    limits = replace(DEFAULT_MAVEDB_ARCHIVE_LIMITS, max_members=1)
    limited_result = materialize_mavedb_local_store(
        _settings(tmp_path / "limited"),
        archive_path=limited_archive,
        archive_proof=_proof(limited_archive),
        archive_limits=limits,
    )
    assert limited_result.status == "archive_rejected:member_count_out_of_bounds"


def test_csv_line_limit_and_variant_count_mismatch_fail_atomically(tmp_path: Path) -> None:
    long_score = "1." + ("0" * 300)
    long_archive = write_mavedb_archive(
        tmp_path / "long.zip",
        [score_set(SS1, [variant_row(f"{SS1}#1", "NM_000329.3:c.1A>G", long_score)])],
    )
    limits = replace(DEFAULT_MAVEDB_ARCHIVE_LIMITS, max_line_bytes=160)
    long_result = materialize_mavedb_local_store(
        _settings(tmp_path / "long"),
        archive_path=long_archive,
        archive_proof=_proof(long_archive),
        archive_limits=limits,
    )
    assert long_result.status == "archive_rejected:csv_line_too_large"

    mismatch_archive = write_mavedb_archive(
        tmp_path / "mismatch.zip",
        [
            score_set(
                SS1,
                [variant_row(f"{SS1}#1", "NM_000329.3:c.1A>G", "0.1")],
                expected_variant_count=2,
            )
        ],
    )
    mismatch_result = materialize_mavedb_local_store(
        _settings(tmp_path / "mismatch"),
        archive_path=mismatch_archive,
        archive_proof=_proof(mismatch_archive),
    )
    assert mismatch_result.status == "archive_rejected:variant_count_mismatch"


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("duplicate_json_key", "main_json_invalid"),
        ("metadata_control", "metadata_control_character_rejected"),
        ("invalid_csv_encoding", "score_csv_invalid"),
        ("csv_control", "score_csv_control_character_rejected"),
    ],
)
def test_malformed_metadata_and_csv_fail_with_safe_codes(
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    archive = write_mavedb_archive(
        tmp_path / f"{mutation}.zip",
        [score_set(SS1, [variant_row(f"{SS1}#1", "NM_000329.3:c.1A>G", "0.1")])],
    )
    if mutation == "duplicate_json_key":
        _replace_archive_member(
            archive,
            "main.json",
            b'{"schemaVersion":"first","schemaVersion":"second"}',
        )
    elif mutation == "metadata_control":
        with ZipFile(archive, "r") as handle:
            metadata = json.loads(handle.read("main.json"))
        metadata["schemaVersion"] = "invalid\u0001schema"
        _replace_archive_member(
            archive,
            "main.json",
            json.dumps(metadata, separators=(",", ":")).encode("utf-8"),
        )
    elif mutation == "invalid_csv_encoding":
        _replace_archive_member(
            archive,
            f"{SS1}_scores.csv",
            b"urn,hgvs_nt,hgvs_splice,hgvs_pro,score\n\xff\n",
        )
    else:
        with ZipFile(archive, "r") as handle:
            score_csv = handle.read(f"{SS1}_scores.csv")
        _replace_archive_member(
            archive,
            f"{SS1}_scores.csv",
            score_csv.replace(b"0.1", b"0.\t1"),
        )

    settings = _settings(tmp_path / "output")
    result = materialize_mavedb_local_store(
        settings,
        archive_path=archive,
        archive_proof=_proof(archive),
    )

    assert result.status == f"archive_rejected:{expected_code}"
    assert not settings.mavedb_local_sqlite_path.exists()


def test_duplicate_variant_identity_and_compression_ratio_fail_closed(tmp_path: Path) -> None:
    duplicate_archive = write_mavedb_archive(
        tmp_path / "duplicate.zip",
        [
            score_set(
                SS1,
                [
                    variant_row(f"{SS1}#1", "NM_000329.3:c.1A>G", "0.1"),
                    variant_row(f"{SS1}#1", "NM_000329.3:c.1A>G", "0.1"),
                ],
            )
        ],
    )
    duplicate_settings = _settings(tmp_path / "duplicate")
    duplicate_result = materialize_mavedb_local_store(
        duplicate_settings,
        archive_path=duplicate_archive,
        archive_proof=_proof(duplicate_archive),
    )
    assert duplicate_result.status == "materialization_failed:ValueError"
    assert not duplicate_settings.mavedb_local_sqlite_path.exists()

    ratio_archive = write_mavedb_archive(
        tmp_path / "ratio.zip",
        [score_set(SS1, [variant_row(f"{SS1}#1", "NM_000329.3:c.1A>G", "0.1")])],
    )
    ratio_result = materialize_mavedb_local_store(
        _settings(tmp_path / "ratio"),
        archive_path=ratio_archive,
        archive_proof=_proof(ratio_archive),
        archive_limits=replace(DEFAULT_MAVEDB_ARCHIVE_LIMITS, max_compression_ratio=1),
    )
    assert ratio_result.status == "archive_rejected:compression_ratio_exceeded"


def test_same_version_stale_schema_signature_is_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "stale.sqlite"
    table_names = (
        "mavedb_archive_member",
        "mavedb_experiment_set",
        "mavedb_experiment",
        "mavedb_target",
        "mavedb_score_set",
        "mavedb_variant_score",
        "mavedb_variant_numeric_value",
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "create table mavedb_local_manifest (id integer primary key, schema_version text)"
        )
        conn.execute(
            "insert into mavedb_local_manifest (id, schema_version) values (1, ?)",
            (MAVEDB_LOCAL_SCHEMA_VERSION,),
        )
        for name in table_names:
            conn.execute(f"create table {name} (legacy text)")
        conn.commit()
    inspection = MaveDbLocalStore(db_path).inspect()
    assert inspection.ready is False
    assert inspection.status == "schema_v2_signature_mismatch"


def test_materialize_cli_streams_only_archive_contract(tmp_path: Path, capsys) -> None:
    archive = write_mavedb_archive(tmp_path / "mavedb.zip", [_base_score_sets()[0]])
    db_path = tmp_path / "mavedb-local.sqlite"
    manifest_path = tmp_path / "mavedb-local.manifest.json"
    digest = sha256(archive.read_bytes()).hexdigest()

    exit_code = eamos_mavedb_local_materialize.main(
        [
            "--archive-path",
            str(archive),
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
    assert payload["materialization"]["archive_member_digests_verified"] is True
    encoded = json.dumps(payload).lower()
    assert str(tmp_path).lower() not in encoded
    assert "nm_000329" not in encoded


def test_archive_boundary_has_no_network_extraction_or_jsonl_compatibility() -> None:
    archive_module = (
        Path(__file__).parents[1] / "app" / "services" / "mavedb_archive.py"
    ).read_text(encoding="utf-8")
    materializer_parameters = inspect.signature(materialize_mavedb_local_store).parameters

    assert "jsonl_files" not in materializer_parameters
    assert "archive_path" in materializer_parameters
    assert "extractall(" not in archive_module
    assert ".extract(" not in archive_module
    assert "httpx" not in archive_module
    assert "requests" not in archive_module
    assert "urlopen" not in archive_module


def _prepend_score_comment(archive_path: Path, score_set_urn: str, prefix: str) -> None:
    with ZipFile(archive_path, "r") as archive:
        payloads = {info.filename: archive.read(info) for info in archive.infolist()}
    member_name = f"{score_set_urn}_scores.csv"
    payloads[member_name] = prefix.encode("utf-8") + payloads[member_name]
    with ZipFile(archive_path, "w") as archive:
        for name, payload in payloads.items():
            archive.writestr(name, payload)


def _replace_archive_member(archive_path: Path, member_name: str, payload: bytes) -> None:
    with ZipFile(archive_path, "r") as archive:
        payloads = {info.filename: archive.read(info) for info in archive.infolist()}
    payloads[member_name] = payload
    with ZipFile(archive_path, "w") as archive:
        for name, member_payload in payloads.items():
            archive.writestr(name, member_payload)
