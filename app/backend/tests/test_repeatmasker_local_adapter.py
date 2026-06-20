from __future__ import annotations

import json
import re

from app.cli import (
    eamos_repeatmasker_compact_artifact_upload,
    eamos_repeatmasker_compact_index_build,
)
from app.services.indexed_sources import REPEATMASKER_COMPACT_INDEX_SCHEMA, RepeatMaskerIndexedTable
from app.services.repeatmasker_local import (
    REPEATMASKER_SOURCE_ID,
    RepeatMaskerLocalStore,
    build_repeatmasker_compact_index,
)


def test_store_provenance_records_repeatmasker_fixture_and_conversion_strategy() -> None:
    provenance = RepeatMaskerLocalStore().provenance()

    assert provenance.source_id == REPEATMASKER_SOURCE_ID
    assert provenance.source_version == "UCSC hg38 rmsk table dump 2022-10-18"
    assert (
        provenance.relative_path
        == "app/backend/app/fixtures/data_sources/repeatmasker_tiny.rmsk.txt"
    )
    assert provenance.checksum_algorithm == "sha256"
    assert re.fullmatch(r"[0-9a-f]{64}", provenance.checksum)
    assert provenance.conversion_strategy == "deterministic_rmsk_text_to_indexed_interval_table"
    assert provenance.source_format == "ucsc_rmsk_txt_rows"


def test_tiny_fixture_returns_repeat_overlaps_and_no_hit_windows() -> None:
    store = RepeatMaskerLocalStore()

    overlaps = store.query_window(chrom="NC_000001.11", start=101, end=120)
    no_hit = store.query_window(chrom="chr1", start=131, end=149)

    assert overlaps.available is True
    assert len(overlaps.repeats) == 1
    assert overlaps.repeats[0].chrom == "1"
    assert overlaps.repeats[0].start == 101
    assert overlaps.repeats[0].end == 130
    assert overlaps.repeats[0].name == "AluY"
    assert overlaps.repeats[0].repeat_class == "SINE"
    assert overlaps.repeats[0].repeat_family == "Alu"
    assert overlaps.repeats[0].strand == "+"
    assert overlaps.repeats[0].provenance.source_id == REPEATMASKER_SOURCE_ID
    assert no_hit.available is True
    assert no_hit.repeats == ()


def test_compact_index_path_returns_repeat_overlaps_and_provenance(tmp_path) -> None:
    index_path = tmp_path / "repeatmasker.interval-index.jsonl"
    RepeatMaskerIndexedTable.from_ucsc_rmsk_rows(
        [
            "585\t1200\t12\t1\t0\tchr1\t100\t130\t-870\t+\tAluY\tSINE\tAlu\t1\t30\t0\t1",
        ]
    ).write_compact_jsonl(
        index_path,
        source_id=REPEATMASKER_SOURCE_ID,
        source_version="pytest",
    )
    store = RepeatMaskerLocalStore(compact_index_path=index_path)

    provenance = store.provenance()
    overlaps = store.query_window(chrom="NC_000001.11", start=101, end=120)

    assert provenance.source_id == REPEATMASKER_SOURCE_ID
    assert provenance.source_format == REPEATMASKER_COMPACT_INDEX_SCHEMA
    assert provenance.relative_path.endswith("repeatmasker.interval-index.jsonl")
    assert overlaps.available is True
    assert len(overlaps.repeats) == 1
    assert overlaps.repeats[0].name == "AluY"


def test_compact_index_builder_writes_runtime_index(tmp_path) -> None:
    source_path = tmp_path / "rmsk.txt"
    output_path = tmp_path / "repeatmasker.interval-index.jsonl"
    source_path.write_text(
        "585\t1200\t12\t1\t0\tchr1\t100\t130\t-870\t+\tAluY\tSINE\tAlu\t1\t30\t0\t1\n",
        encoding="utf-8",
    )

    result = build_repeatmasker_compact_index(
        source_rmsk_path=source_path,
        output_path=output_path,
    )
    store = RepeatMaskerLocalStore(compact_index_path=output_path)

    assert result.source_id == REPEATMASKER_SOURCE_ID
    assert result.output_schema == REPEATMASKER_COMPACT_INDEX_SCHEMA
    assert result.interval_count == 1
    assert result.output_byte_size == output_path.stat().st_size
    assert re.fullmatch(r"[0-9a-f]{64}", result.output_sha256)
    assert store.query_window(chrom="1", start=101, end=101).repeats[0].name == "AluY"


def test_compact_index_builder_cli_is_build_time_only(tmp_path, capsys) -> None:
    source_path = tmp_path / "rmsk.txt"
    output_path = tmp_path / "repeatmasker.interval-index.jsonl"
    source_path.write_text(
        "585\t1200\t12\t1\t0\tchr1\t100\t130\t-870\t+\tAluY\tSINE\tAlu\t1\t30\t0\t1\n",
        encoding="utf-8",
    )

    exit_code = eamos_repeatmasker_compact_index_build.main(
        [
            "--source-rmsk-path",
            str(source_path),
            "--output",
            str(output_path),
            "--require-ready",
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ready"
    assert output["result"]["interval_count"] == 1
    assert output["guardrails"]["render_disk_seed"] == "not_used"
    assert output["guardrails"]["local_evidence_enabled_flip"] == "not_used"


def test_compact_index_upload_cli_plans_private_storage_object_without_paths(
    tmp_path,
    capsys,
) -> None:
    output_path = tmp_path / "repeatmasker.interval-index.jsonl"
    RepeatMaskerIndexedTable.from_ucsc_rmsk_rows(
        [
            "585\t1200\t12\t1\t0\tchr1\t100\t130\t-870\t+\tAluY\tSINE\tAlu\t1\t30\t0\t1",
        ]
    ).write_compact_jsonl(
        output_path,
        source_id=REPEATMASKER_SOURCE_ID,
        source_version="pytest",
    )

    exit_code = eamos_repeatmasker_compact_artifact_upload.main(
        [
            "--source-artifact",
            str(output_path),
            "--compact",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "eamos_repeatmasker_compact_artifact_upload"
    assert output["status"] == "planned"
    assert output["guardrails"]["render_disk_seed"] == "not_used"
    item = output["result"]["items"][0]
    assert item["status"] == "planned"
    assert item["object_path"].startswith("generated/repeatmasker_rmsk_bb/")
    assert item["sha256"]
    encoded = json.dumps(output).lower()
    assert str(tmp_path).lower() not in encoded
    assert "service_role" not in encoded


def test_repeat_overlap_boundaries_are_inclusive() -> None:
    store = RepeatMaskerLocalStore()

    start_edge = store.query_window(chrom="1", start=101, end=101)
    end_edge = store.query_window(chrom="1", start=130, end=130)
    just_after = store.query_window(chrom="1", start=131, end=131)

    assert start_edge.available is True
    assert len(start_edge.repeats) == 1
    assert end_edge.available is True
    assert len(end_edge.repeats) == 1
    assert just_after.available is True
    assert just_after.repeats == ()


def test_unknown_contig_and_invalid_window_fail_closed() -> None:
    store = RepeatMaskerLocalStore()

    unknown = store.query_window(chrom="chr7", start=101, end=120)
    invalid = store.query_window(chrom="chr1", start=120, end=101)

    assert unknown.available is False
    assert unknown.unavailable_reason == "contig_not_found"
    assert unknown.warnings == ("repeatmasker_local_contig_not_found",)
    assert invalid.available is False
    assert invalid.unavailable_reason == "invalid_coordinates"
    assert invalid.warnings == ("repeatmasker_local_invalid_coordinates",)
