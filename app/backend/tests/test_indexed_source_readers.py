from __future__ import annotations

from pathlib import Path

import pytest

from app.services.indexed_sources import (
    IndexedSourceError,
    TabixTsvPredictorColumns,
    TabixTsvPredictorReader,
    PysamIndexedVcfReader,
    PyBigWigConservationReader,
    RepeatMaskerIndexedTable,
    _build_alias_map,
    _normalize_contig_alias,
    repeatmasker_path_decision,
)


def test_pysam_reader_reports_missing_index_before_opening_vcf(tmp_path: Path) -> None:
    vcf_path = tmp_path / "tiny.vcf.gz"
    vcf_path.write_bytes(b"not a real bgzip vcf")

    with pytest.raises(IndexedSourceError) as exc_info:
        PysamIndexedVcfReader(vcf_path, source_id="ncbi_clinvar_vcf")

    assert exc_info.value.code == "missing_index"
    assert exc_info.value.details == {
        "path": str(vcf_path),
        "index_path": str(vcf_path) + ".tbi",
    }


def test_pysam_reader_queries_tiny_vcf_by_contig_alias_and_range(tmp_path: Path) -> None:
    pysam = pytest.importorskip("pysam")
    vcf_path = _write_tiny_indexed_vcf(tmp_path, pysam)

    with PysamIndexedVcfReader(vcf_path, source_id="ncbi_clinvar_vcf") as reader:
        records = reader.query_position("NC_000001.11", 101)
        ranged = reader.query_range("chr1", 100, 102)
        metadata = reader.metadata()

    assert metadata.reader == "pysam"
    assert metadata.version == "0.24.0"
    assert len(records) == 1
    assert len(ranged) == 1
    record = records[0]
    ranged_record = ranged[0]
    assert ranged_record.requested_chrom == "chr1"
    assert ranged_record.position == record.position
    assert ranged_record.ref == record.ref
    assert ranged_record.alts == record.alts
    assert record.requested_chrom == "NC_000001.11"
    assert record.chrom == "1"
    assert record.position == 101
    assert record.record_id == "VCV000000001"
    assert record.ref == "A"
    assert record.alts == ("G",)
    assert record.info["CLNSIG"] == ("Pathogenic",)


def test_pysam_reader_unknown_contig_and_invalid_window_fail_closed(tmp_path: Path) -> None:
    pysam = pytest.importorskip("pysam")
    vcf_path = _write_tiny_indexed_vcf(tmp_path, pysam)

    with PysamIndexedVcfReader(vcf_path, source_id="ncbi_clinvar_vcf") as reader:
        with pytest.raises(IndexedSourceError) as unknown_exc:
            reader.query_position("chr7", 101)
        with pytest.raises(IndexedSourceError) as coordinate_exc:
            reader.query_range("chr1", 102, 101)

    assert unknown_exc.value.code == "unknown_contig"
    assert unknown_exc.value.details == {"requested_chrom": "chr7"}
    assert coordinate_exc.value.code == "invalid_coordinates"
    assert coordinate_exc.value.details == {"chrom": "1", "start": 102, "end": 101}


def test_tabix_predictor_reader_reports_missing_index_before_opening_tsv(tmp_path: Path) -> None:
    tsv_path = tmp_path / "scores.tsv.gz"
    tsv_path.write_bytes(b"not a real bgzip tsv")

    with pytest.raises(IndexedSourceError) as exc_info:
        TabixTsvPredictorReader(tsv_path, source_id="google_deepmind_alphamissense_hg38")

    assert exc_info.value.code == "missing_index"
    assert exc_info.value.details == {
        "path": str(tsv_path),
        "index_path": str(tsv_path) + ".tbi",
    }


def test_tabix_predictor_reader_queries_exact_variant_match(tmp_path: Path) -> None:
    pysam = pytest.importorskip("pysam")
    tsv_path = _write_tiny_indexed_predictor_tsv(tmp_path, pysam)

    with TabixTsvPredictorReader(
        tsv_path,
        source_id="google_deepmind_alphamissense_hg38",
        columns=TabixTsvPredictorColumns(
            score=4,
            extra_columns=(("protein_variant", 5), ("source_class", 6)),
        ),
    ) as reader:
        matches = reader.query_variant("NC_000001.11", 101, "A", "G")
        position_rows = reader.query_position("chr1", 101)
        metadata = reader.metadata()

    assert metadata.reader == "pysam.TabixFile"
    assert len(matches) == 1
    assert len(position_rows) == 2
    assert matches[0].chrom == "1"
    assert matches[0].position == 101
    assert matches[0].ref == "A"
    assert matches[0].alt == "G"
    assert matches[0].score == pytest.approx(0.792)
    assert matches[0].extra == {
        "protein_variant": "V1M",
        "source_class": "likely_pathogenic",
    }


def test_tabix_predictor_reader_unknown_contig_and_bad_schema_fail_closed(
    tmp_path: Path,
) -> None:
    pysam = pytest.importorskip("pysam")
    tsv_path = _write_tiny_indexed_predictor_tsv(tmp_path, pysam)

    with TabixTsvPredictorReader(
        tsv_path,
        source_id="esm1b_hg38_assembled_scores",
        columns=TabixTsvPredictorColumns(),
    ) as reader:
        with pytest.raises(IndexedSourceError) as unknown_exc:
            reader.query_position("chr7", 101)

    assert unknown_exc.value.code == "unknown_contig"
    assert unknown_exc.value.details == {"requested_chrom": "chr7"}

    with pytest.raises(IndexedSourceError) as schema_exc:
        TabixTsvPredictorReader(
            tsv_path,
            source_id="esm1b_hg38_assembled_scores",
            columns=TabixTsvPredictorColumns(score=-1),
        )

    assert schema_exc.value.code == "invalid_predictor_tsv_schema"


def test_pybigwig_reader_rejects_missing_file_before_import(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing_phylop.bw"

    with pytest.raises(IndexedSourceError) as exc_info:
        PyBigWigConservationReader(missing_path)

    assert exc_info.value.code == "missing_bigwig_file"
    assert exc_info.value.details == {"path": str(missing_path)}


def test_indexed_alias_map_canonicalizes_refseq_nc_contigs_without_native_readers() -> None:
    aliases = _build_alias_map(["1", "X", "Y", "M"])

    assert aliases["1"] == "1"
    assert aliases[_normalize_contig_alias("NC_000001.11")] == "1"
    assert aliases["X"] == "X"
    assert aliases[_normalize_contig_alias("NC_000023.11")] == "X"
    assert aliases["Y"] == "Y"
    assert aliases[_normalize_contig_alias("NC_000024.10")] == "Y"
    assert aliases["M"] == "M"
    assert aliases[_normalize_contig_alias("NC_012920.1")] == "M"


def test_indexed_alias_map_rejects_duplicate_ncbi_contig_aliases() -> None:
    with pytest.raises(IndexedSourceError) as exc_info:
        _build_alias_map(["1", "NC_000001.11"])

    assert exc_info.value.code == "duplicate_contig_alias"
    assert exc_info.value.details["first_contig"] == "1"
    assert exc_info.value.details["second_contig"] == "NC_000001.11"


def test_pybigwig_reader_returns_position_score_and_window_summary(tmp_path: Path) -> None:
    pybigwig = pytest.importorskip("pyBigWig")
    bw_path = _write_tiny_bigwig(tmp_path, pybigwig)

    with PyBigWigConservationReader(bw_path) as reader:
        score = reader.score("NC_000001.11", 3)
        summary = reader.window_summary("chr1", 2, 4)
        metadata = reader.metadata()

    assert metadata.reader == "pyBigWig"
    assert metadata.version == "0.3.25"
    assert score.chrom == "1"
    assert score.position == 3
    assert score.score == pytest.approx(1.5)
    assert summary.chrom == "1"
    assert summary.bases_with_scores == 3
    assert summary.mean_score == pytest.approx((1.0 + 1.5 + 2.0) / 3)


def test_pybigwig_reader_unknown_contig_and_out_of_range_fail_closed(tmp_path: Path) -> None:
    pybigwig = pytest.importorskip("pyBigWig")
    bw_path = _write_tiny_bigwig(tmp_path, pybigwig)

    with PyBigWigConservationReader(bw_path) as reader:
        with pytest.raises(IndexedSourceError) as unknown_exc:
            reader.score("chr7", 1)
        with pytest.raises(IndexedSourceError) as bounds_exc:
            reader.score("chr1", 11)

    assert unknown_exc.value.code == "unknown_contig"
    assert unknown_exc.value.details == {"requested_chrom": "chr7"}
    assert bounds_exc.value.code == "out_of_bounds"
    assert bounds_exc.value.details == {
        "chrom": "1",
        "start": 11,
        "end": 11,
        "contig_length": 10,
    }


def test_repeatmasker_path_decision_records_conversion_first_strategy() -> None:
    decision = repeatmasker_path_decision()

    assert decision.strategy == "deterministic_rmsk_text_to_indexed_interval_table"
    assert decision.direct_bigbed_reader is False
    assert decision.fixture_format == "ucsc_rmsk_txt_rows"
    assert "rmsk.txt.gz" in decision.reason


def test_repeatmasker_index_queries_ucsc_rmsk_text_rows_by_alias() -> None:
    table = RepeatMaskerIndexedTable.from_ucsc_rmsk_rows(
        [
            "585\t1200\t12\t1\t0\tchr1\t100\t130\t-870\t+\tAluY\tSINE\tAlu\t1\t30\t0\t1",
            "585\t900\t20\t2\t0\tchr2\t400\t420\t-580\tC\tL1PA2\tLINE\tL1\t5\t25\t0\t2",
        ]
    )

    overlaps = table.query("NC_000001.11", 101, 105)
    no_hit = table.query("chr1", 140, 150)

    assert len(overlaps) == 1
    assert overlaps[0].chrom == "1"
    assert overlaps[0].start == 101
    assert overlaps[0].end == 130
    assert overlaps[0].name == "AluY"
    assert overlaps[0].repeat_class == "SINE"
    assert overlaps[0].repeat_family == "Alu"
    assert overlaps[0].strand == "+"
    assert no_hit == ()


def test_repeatmasker_index_malformed_unknown_and_invalid_queries_fail_closed() -> None:
    with pytest.raises(IndexedSourceError) as malformed_exc:
        RepeatMaskerIndexedTable.from_ucsc_rmsk_rows(["too\tshort"])

    table = RepeatMaskerIndexedTable.from_ucsc_rmsk_rows(
        ["585\t1200\t12\t1\t0\tchr1\t100\t130\t-870\t+\tAluY\tSINE\tAlu\t1\t30\t0\t1"]
    )

    with pytest.raises(IndexedSourceError) as unknown_exc:
        table.query("chr7", 101, 105)
    with pytest.raises(IndexedSourceError) as coordinate_exc:
        table.query("chr1", 105, 101)

    assert malformed_exc.value.code == "malformed_repeatmasker_row"
    assert unknown_exc.value.code == "unknown_contig"
    assert unknown_exc.value.details == {"requested_chrom": "chr7"}
    assert coordinate_exc.value.code == "invalid_coordinates"
    assert coordinate_exc.value.details == {"chrom": "1", "start": 105, "end": 101}


def _write_tiny_indexed_vcf(tmp_path: Path, pysam: object) -> Path:
    vcf_path = tmp_path / "tiny.vcf"
    bgzip_path = tmp_path / "tiny.vcf.gz"
    vcf_path.write_text(
        "\n".join(
            [
                "##fileformat=VCFv4.2",
                "##contig=<ID=1,length=1000>",
                ("##INFO=<ID=CLNSIG,Number=.,Type=String," 'Description="Clinical significance">'),
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                "1\t101\tVCV000000001\tA\tG\t.\t.\tCLNSIG=Pathogenic",
                "",
            ]
        ),
        encoding="utf-8",
    )
    pysam.tabix_compress(str(vcf_path), str(bgzip_path), force=True)
    pysam.tabix_index(str(bgzip_path), preset="vcf", force=True)
    return bgzip_path


def _write_tiny_indexed_predictor_tsv(tmp_path: Path, pysam: object) -> Path:
    tsv_path = tmp_path / "scores.tsv"
    bgzip_path = tmp_path / "scores.tsv.gz"
    tsv_path.write_text(
        "\n".join(
            [
                "chr1\t101\tA\tG\t0.792\tV1M\tlikely_pathogenic",
                "chr1\t101\tA\tT\t0.100\tV1L\tambiguous",
                "chr1\t102\tC\tT\t-14.0\tV2M\tPP3_Strong",
                "",
            ]
        ),
        encoding="utf-8",
    )
    pysam.tabix_compress(str(tsv_path), str(bgzip_path), force=True)
    pysam.tabix_index(
        str(bgzip_path),
        seq_col=0,
        start_col=1,
        end_col=1,
        force=True,
    )
    return bgzip_path


def _write_tiny_bigwig(tmp_path: Path, pybigwig: object) -> Path:
    bw_path = tmp_path / "tiny.bw"
    bigwig = pybigwig.open(str(bw_path), "w")
    bigwig.addHeader([("chr1", 10)])
    bigwig.addEntries(
        ["chr1", "chr1", "chr1", "chr1"],
        [0, 1, 2, 3],
        ends=[1, 2, 3, 4],
        values=[0.5, 1.0, 1.5, 2.0],
    )
    bigwig.close()
    return bw_path
