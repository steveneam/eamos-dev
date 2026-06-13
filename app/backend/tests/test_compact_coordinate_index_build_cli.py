from __future__ import annotations

import json
from pathlib import Path

from app.cli.eamos_compact_index_build import main
from app.services.compact_coordinate_index import CompactCoordinateIndex
from app.services.compact_coordinate_index_builder import build_compact_coordinate_index


def _tiny_gff(
    tmp_path: Path,
    name: str = "tiny_refseq.gff",
    *,
    gene: str = "TEST",
    transcript: str = "NM_TEST.1",
) -> Path:
    path = tmp_path / name
    path.write_text(
        "\n".join(
            [
                "##gff-version 3",
                (
                    "NC_000001.11\tRefSeq\tmRNA\t100\t108\t.\t+\t.\t"
                    f"ID=rna-{transcript};transcript_id={transcript};gene={gene}"
                ),
                (
                    "NC_000001.11\tRefSeq\texon\t100\t108\t.\t+\t.\t"
                    f"ID=exon-{transcript}-1;Parent=rna-{transcript};gene={gene}"
                ),
                (
                    "NC_000001.11\tRefSeq\tCDS\t100\t108\t.\t+\t0\t"
                    f"ID=cds-{transcript}-1;Parent=rna-{transcript};gene={gene}"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _tiny_negative_strand_gff(tmp_path: Path) -> Path:
    path = tmp_path / "tiny_negative_refseq.gff"
    path.write_text(
        "\n".join(
            [
                "##gff-version 3",
                (
                    "NC_000001.11\tRefSeq\tmRNA\t100\t202\t.\t-\t.\t"
                    "ID=rna-NM_NEG.1;transcript_id=NM_NEG.1;gene=NEG"
                ),
                (
                    "NC_000001.11\tRefSeq\texon\t200\t202\t.\t-\t.\t"
                    "ID=exon-NM_NEG.1-1;Parent=rna-NM_NEG.1;gene=NEG"
                ),
                (
                    "NC_000001.11\tRefSeq\texon\t100\t102\t.\t-\t.\t"
                    "ID=exon-NM_NEG.1-2;Parent=rna-NM_NEG.1;gene=NEG"
                ),
                (
                    "NC_000001.11\tRefSeq\tCDS\t200\t202\t.\t-\t0\t"
                    "ID=cds-NM_NEG.1-1;Parent=rna-NM_NEG.1;gene=NEG"
                ),
                (
                    "NC_000001.11\tRefSeq\tCDS\t100\t102\t.\t-\t0\t"
                    "ID=cds-NM_NEG.1-2;Parent=rna-NM_NEG.1;gene=NEG"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_compact_index_builder_writes_valid_transcript_artifact(tmp_path: Path) -> None:
    gff = _tiny_gff(tmp_path)
    output = tmp_path / "eamos-coordinate-index.test.jsonl"

    result = build_compact_coordinate_index(
        output_path=output,
        gff_paths=(gff,),
        genes=("TEST",),
        artifact_version="test-artifact",
        generated_at="2026-06-13T00:00:00+00:00",
    )
    index = CompactCoordinateIndex(output)
    inspection = index.inspection(verify_checksum=True)
    transcript = index.transcript(gene="TEST", transcript="NM_TEST")

    assert result.ready is True
    assert result.status == "ready"
    assert result.requested_gene_count == 1
    assert result.gene_count == 1
    assert result.transcript_count == 1
    assert result.schema_validated is True
    assert inspection.ready is True
    assert inspection.variant_count == 0
    assert inspection.transcript_count == 1
    assert transcript is not None
    assert transcript.refseq_transcript == "NM_TEST.1"
    assert transcript.exons[0].cds_start == 1
    assert transcript.exons[0].cds_end == 9
    assert transcript.exons[0].genomic_start == 100
    assert transcript.exons[0].genomic_end == 108
    assert "MANE Select" not in transcript.transcript_aliases


def test_compact_index_builder_projects_negative_strand_cds_coordinates(
    tmp_path: Path,
) -> None:
    gff = _tiny_negative_strand_gff(tmp_path)
    output = tmp_path / "negative-index.jsonl"

    result = build_compact_coordinate_index(
        output_path=output,
        gff_paths=(gff,),
        genes=("NEG",),
        artifact_version="test-negative-artifact",
        generated_at="2026-06-13T00:00:00+00:00",
    )
    transcript = CompactCoordinateIndex(output).transcript(gene="NEG", transcript="NM_NEG")

    assert result.ready is True
    assert transcript is not None
    assert transcript.strand == "-"
    assert [(exon.number, exon.cds_start, exon.cds_end) for exon in transcript.exons] == [
        (1, 1, 3),
        (2, 4, 6),
    ]
    assert [(exon.genomic_start, exon.genomic_end) for exon in transcript.exons] == [
        (200, 202),
        (100, 102),
    ]


def test_compact_index_build_cli_requires_explicit_gene_scope(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "--refseq-gff",
            str(_tiny_gff(tmp_path)),
            "--output",
            str(tmp_path / "index.jsonl"),
            "--require-ready",
            "--compact",
        ]
    )

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert output["mode"] == "eamos_compact_index_build"
    assert output["guardrails"]["runtime_raw_gff_scan"] == "not_used"
    assert output["build"]["status"] == "gene_scope_required"
    assert not (tmp_path / "index.jsonl").exists()
    assert str(tmp_path).lower() not in json.dumps(output).lower()


def test_compact_index_build_cli_builds_sanitized_artifact(
    tmp_path: Path,
    capsys,
) -> None:
    gff = _tiny_gff(tmp_path)
    output_path = tmp_path / "eamos-coordinate-index.test.jsonl.gz"

    exit_code = main(
        [
            "--refseq-gff",
            str(gff),
            "--gene",
            "TEST",
            "--output",
            str(output_path),
            "--artifact-version",
            "test-artifact",
            "--require-ready",
            "--compact",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["build"]["status"] == "ready"
    assert output["build"]["ready"] is True
    assert output["build"]["transcript_count"] == 1
    assert output_path.exists()
    assert CompactCoordinateIndex(output_path).inspection().ready is True
    assert str(tmp_path).lower() not in json.dumps(output).lower()
