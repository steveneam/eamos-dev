from __future__ import annotations

from gzip import compress
from io import BytesIO
from pathlib import Path
import os
import stat
import time
import tracemalloc

import pytest

from app.schemas.batch import BatchFilters
from app.services.batch_engine.filters import (
    BatchPreFilterStats,
    BatchResourceLimitExceeded,
    GenomicInterval,
    filter_pre_annotation,
    iter_pre_annotation,
)
from app.services.batch_engine.intake import (
    cleanup_expired_staged_vcfs,
    iter_staged_variants,
    remove_staged_vcf,
    stage_vcf_file,
)
from app.services.batch_engine.runtime import SnapshotCursorCodec
from app.services.vcf_ingest import VcfIngestLimitError


def _vcf(
    *,
    rows: list[tuple[int, str, str, str]],
    sample_name: str = "sample-one",
) -> bytes:
    lines = [
        "##fileformat=VCFv4.2",
        "##reference=GRCh38.p14",
        "##contig=<ID=1,length=248956422,assembly=GRCh38>",
        '##INFO=<ID=GENE,Number=1,Type=String,Description="Unverified source annotation">',
        '##INFO=<ID=AF,Number=A,Type=Float,Description="Input provenance only">',
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
        '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read depth">',
        '##FORMAT=<ID=GQ,Number=1,Type=Float,Description="Genotype quality">',
        f"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t{sample_name}",
    ]
    lines.extend(
        f"1\t{position}\t.\t{ref}\t{alt}\t60\t{filter_value}\t"
        "GENE=RPE65;AF=0.0001\tGT:DP:GQ\t0/1:31:99"
        for position, ref, alt, filter_value in rows
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _write_vcf_file(path: Path, *, row_count: int) -> None:
    with path.open("w", encoding="ascii", newline="") as handle:
        handle.write(
            "##fileformat=VCFv4.2\n"
            "##reference=GRCh38.p14\n"
            "##contig=<ID=1,length=248956422,assembly=GRCh38>\n"
            '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tPROBAND\n"
        )
        for position in range(1, row_count + 1):
            handle.write(f"1\t{position}\t.\tA\tC\t60\tPASS\t.\tGT\t0/1\n")


def test_htslib_intake_issues_immutable_receipt_and_deidentifies_samples(tmp_path: Path) -> None:
    staged = stage_vcf_file(
        BytesIO(_vcf(rows=[(10, "A", "C", "PASS")], sample_name="PATIENT_SECRET")),
        staging_dir=tmp_path,
        filename="patient-name.vcf",
        max_compressed_bytes=1024 * 1024,
    )
    try:
        assert staged.envelope.raw_record_count == 1
        assert staged.envelope.sample_count == 1
        assert staged.envelope.accepted_variant_classes == ["snv"]
        assert stat.S_IMODE(staged.path.stat().st_mode) == 0o600
        assert "patient-name" not in staged.path.name

        streamed = list(iter_staged_variants(staged, upload_ref="batch-upload-secretless"))

        assert len(streamed) == 1
        row = streamed[0]
        assert row.variant.raw is None
        assert row.variant.sample_id is None
        assert row.samples[0].sample_key.startswith("sample-")
        assert row.samples[0].genotype == "0/1"
        assert row.samples[0].depth == 31
        assert "PATIENT_SECRET" not in str(row)
    finally:
        remove_staged_vcf(staged)
    assert not staged.path.exists()


def test_wes_stream_scans_25k_rows_before_small_interval_result(tmp_path: Path) -> None:
    rows = [(position, "A", "C", "PASS") for position in range(1, 25_001)]
    staged = stage_vcf_file(
        BytesIO(_vcf(rows=rows)),
        staging_dir=tmp_path,
        filename="wes.vcf",
        max_compressed_bytes=8 * 1024 * 1024,
        post_filter_variant_cap=5000,
    )
    try:
        filtered = filter_pre_annotation(
            iter_staged_variants(staged, upload_ref="batch-upload-25k"),
            legacy_filters=BatchFilters(panel_slug="test-panel"),
            filter_plan=None,
            panel_intervals=(GenomicInterval(chromosome="1", start=100, end=109),),
            source_snapshot_id="snapshot-25k",
            post_filter_cap=5000,
        )
    finally:
        remove_staged_vcf(staged)

    assert staged.envelope.raw_record_count == 25_000
    assert filtered.allele_count == 25_000
    assert len(filtered.candidates) == 10
    assert filtered.over_cap_count == 0
    assert {item.variant.pos for item in filtered.candidates} == set(range(100, 110))


@pytest.mark.parametrize(
    ("raw_rows", "retained_rows"),
    [(1_000, 0), (25_000, 10), (75_000, 500), (150_000, 5_000)],
)
def test_wes_size_matrix_stays_bounded_before_annotation(
    tmp_path: Path,
    raw_rows: int,
    retained_rows: int,
) -> None:
    source_path = tmp_path / f"wes-{raw_rows}.vcf"
    _write_vcf_file(source_path, row_count=raw_rows)
    tracemalloc.start()
    started = time.perf_counter()
    with source_path.open("rb") as source:
        staged = stage_vcf_file(
            source,
            staging_dir=tmp_path / "staged",
            filename=source_path.name,
            max_compressed_bytes=64 * 1024 * 1024,
            max_raw_records=200_000,
            post_filter_variant_cap=5_000,
        )
    try:
        filtered = filter_pre_annotation(
            iter_staged_variants(staged, upload_ref=f"batch-upload-{raw_rows}"),
            legacy_filters=BatchFilters(panel_slug="benchmark-panel"),
            filter_plan=None,
            panel_intervals=(
                GenomicInterval(
                    chromosome="1",
                    start=1 if retained_rows else raw_rows + 1,
                    end=retained_rows if retained_rows else raw_rows + 1,
                ),
            ),
            source_snapshot_id=f"snapshot-{raw_rows}",
            post_filter_cap=5_000,
        )
    finally:
        remove_staged_vcf(staged)
    elapsed_seconds = time.perf_counter() - started
    _current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert staged.envelope.raw_record_count == raw_rows
    assert len(filtered.candidates) == retained_rows
    assert filtered.allele_count == raw_rows
    assert peak_bytes < 256 * 1024 * 1024
    # Match the product preparation bound while leaving shared CI runners room
    # to run the traced 150k-row case under contention. The isolated benchmark
    # remains the tighter measured performance evidence.
    assert elapsed_seconds < 120


def test_post_filter_cap_counts_excess_instead_of_failing_at_raw_row_5001(
    tmp_path: Path,
) -> None:
    rows = [(position, "A", "C", "PASS") for position in range(1, 6_001)]
    staged = stage_vcf_file(
        BytesIO(_vcf(rows=rows)),
        staging_dir=tmp_path,
        filename="over-cap.vcf",
        max_compressed_bytes=4 * 1024 * 1024,
        post_filter_variant_cap=5000,
    )
    try:
        filtered = filter_pre_annotation(
            iter_staged_variants(staged, upload_ref="batch-upload-over-cap"),
            legacy_filters=BatchFilters(),
            filter_plan=None,
            panel_intervals=None,
            source_snapshot_id="snapshot-over-cap",
            post_filter_cap=5000,
        )
    finally:
        remove_staged_vcf(staged)

    assert len(filtered.candidates) == 5000
    assert filtered.over_cap_count == 1000
    assert any(item.reason == "annotation_cap" for item in filtered.dispositions)


def test_pre_annotation_stream_enforces_neutral_wall_time_bound(tmp_path: Path) -> None:
    staged = stage_vcf_file(
        BytesIO(_vcf(rows=[(position, "A", "C", "PASS") for position in range(1, 1025)])),
        staging_dir=tmp_path,
        filename="deadline.vcf",
        max_compressed_bytes=2 * 1024 * 1024,
    )
    try:
        stream = iter_pre_annotation(
            iter_staged_variants(staged, upload_ref="batch-upload-deadline"),
            legacy_filters=BatchFilters(),
            filter_plan=None,
            panel_intervals=None,
            stats=BatchPreFilterStats(),
            deadline_monotonic=1.0,
            clock=lambda: 2.0,
        )
        with pytest.raises(BatchResourceLimitExceeded, match="wall-time"):
            list(stream)
    finally:
        remove_staged_vcf(staged)


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"BCF\x02\x02not-a-bcf", "bcf_not_supported"),
        (_vcf(rows=[(10, "A", "<NON_REF>", "PASS")]), "gvcf_not_supported"),
        (_vcf(rows=[(10, "A", "<DEL>", "PASS")]), "unsupported_variant_class"),
    ],
)
def test_intake_rejects_unvalidated_formats_and_variant_classes(
    tmp_path: Path,
    payload: bytes,
    code: str,
) -> None:
    with pytest.raises(VcfIngestLimitError) as exc:
        stage_vcf_file(
            BytesIO(payload),
            staging_dir=tmp_path,
            filename="input.vcf",
            max_compressed_bytes=1024 * 1024,
        )
    assert exc.value.code == code
    assert not list(tmp_path.glob("*.upload"))


def test_vcfgz_stream_and_multiallelic_split_have_receipt_parity(tmp_path: Path) -> None:
    payload = _vcf(rows=[(10, "A", "C,G", "PASS")])
    staged = stage_vcf_file(
        BytesIO(compress(payload)),
        staging_dir=tmp_path,
        filename="family.vcf.gz",
        max_compressed_bytes=1024 * 1024,
    )
    try:
        variants = list(iter_staged_variants(staged, upload_ref="batch-upload-gzip"))
    finally:
        remove_staged_vcf(staged)

    assert staged.envelope.format == "vcf_gz"
    assert staged.envelope.raw_record_count == 1
    assert [item.variant.query for item in variants] == ["1-10-A-C", "1-10-A-G"]
    assert all("multiallelic_alt_split" in item.variant.warnings for item in variants)


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (
            b"##fileformat=VCFv4.2\n##reference=GRCh38\n"
            b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
            b"1\t10\t.\tA\tC\t60\tPASS\t.\n",
            "vcf_sample_columns_required",
        ),
        (
            b"##fileformat=VCFv4.2\n##reference=GRCh38\n"
            b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tA\tB\tC\tD\n"
            b"1\t10\t.\tA\tC\t60\tPASS\t.\tGT\t0/1\t0/0\t0/1\t0/1\n",
            "cohort_vcf_not_supported",
        ),
        (
            b"##fileformat=VCFv4.2\n##reference=GRCh38\n"
            b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tP\n"
            b"GL000220.1\t10\t.\tA\tC\t60\tPASS\t.\tGT\t0/1\n",
            "unsupported_contig",
        ),
    ],
)
def test_intake_rejects_out_of_envelope_sample_and_contig_shapes(
    tmp_path: Path,
    payload: bytes,
    code: str,
) -> None:
    with pytest.raises(VcfIngestLimitError) as exc:
        stage_vcf_file(
            BytesIO(payload),
            staging_dir=tmp_path,
            filename="out-of-envelope.vcf",
            max_compressed_bytes=1024 * 1024,
        )
    assert exc.value.code == code


def test_decompressed_and_raw_record_limits_are_independent(tmp_path: Path) -> None:
    payload = _vcf(rows=[(position, "A", "C", "PASS") for position in range(1, 5)])
    with pytest.raises(VcfIngestLimitError) as raw_exc:
        stage_vcf_file(
            BytesIO(payload),
            staging_dir=tmp_path,
            filename="raw-limit.vcf",
            max_compressed_bytes=1024 * 1024,
            max_raw_records=3,
        )
    assert raw_exc.value.code == "vcf_raw_record_limit_exceeded"

    with pytest.raises(VcfIngestLimitError) as decompressed_exc:
        stage_vcf_file(
            BytesIO(compress(payload * 100)),
            staging_dir=tmp_path,
            filename="decompression-bomb.vcf.gz",
            max_compressed_bytes=1024 * 1024,
            max_decompressed_bytes=1024,
        )
    assert decompressed_exc.value.code == "vcf_decompressed_size_limit_exceeded"


def test_snapshot_cursor_is_tamper_evident_and_snapshot_bound() -> None:
    codec = SnapshotCursorCodec(b"x" * 32)
    cursor = codec.encode(snapshot_id="snapshot-a", offset=500)

    assert codec.decode(cursor, snapshot_id="snapshot-a") == 500
    with pytest.raises(ValueError, match="invalid"):
        codec.decode(cursor, snapshot_id="snapshot-b")
    with pytest.raises(ValueError, match="invalid"):
        codec.decode(cursor[:-1] + ("A" if cursor[-1] != "A" else "B"), snapshot_id="snapshot-a")


def test_crash_cleanup_removes_only_expired_opaque_uploads(tmp_path: Path) -> None:
    old_upload = tmp_path / "batch-old.upload"
    fresh_upload = tmp_path / "batch-fresh.upload"
    unrelated = tmp_path / "patient.vcf"
    old_upload.write_bytes(b"old")
    fresh_upload.write_bytes(b"fresh")
    unrelated.write_bytes(b"keep")
    now = time.time()
    os.utime(old_upload, (now - 120, now - 120))

    removed = cleanup_expired_staged_vcfs(
        tmp_path,
        older_than_seconds=60,
        now_timestamp=now,
    )

    assert removed == 1
    assert not old_upload.exists()
    assert fresh_upload.exists()
    assert unrelated.exists()
