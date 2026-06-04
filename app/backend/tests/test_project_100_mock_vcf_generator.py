from __future__ import annotations

from app.services.eamos_coordinate_resolver import EamosCoordinateResolution
from scripts.generate_project_100_mock_vcf import generate_project_100_mock_vcf
from scripts.validate_project_100_coordinates import _project_100_source_rows


class _FakeProject100Resolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, *, gene, cdna, transcript=None, **_kwargs):
        self.calls += 1
        pos = 1000 + self.calls
        return EamosCoordinateResolution(
            gene=gene,
            transcript=transcript or "",
            cdna=cdna,
            chrom="1",
            pos=pos,
            ref="A",
            alt="T",
            genomic_hg38=f"1-{pos}-A-T",
            genomic_hgvs=f"NC_000001.11:g.{pos}A>T",
            source="eamos_local_transcript_reference",
            provenance=("eamos_mane_refseq_gff", "ucsc_hg38_2bit_reference_base"),
        )


def test_generate_project_100_mock_vcf_writes_vcf_and_truth_manifest(tmp_path) -> None:
    source_rows = _project_100_source_rows()[:2]
    output_vcf = tmp_path / "project_100.vcf"
    truth_manifest = tmp_path / "project_100.truth.json"

    payload = generate_project_100_mock_vcf(
        output_vcf=output_vcf,
        truth_manifest=truth_manifest,
        source_rows=source_rows,
        resolver=_FakeProject100Resolver(),
    )

    assert payload["coverage"]["rows"] == 2
    assert payload["coverage"]["unresolved"] == 0
    assert payload["coverage"]["genes"] == 1
    assert payload["runtime_policy"].startswith("Coordinates are generated with the Eamos local")
    assert truth_manifest.is_file()

    vcf = output_vcf.read_text(encoding="utf-8").splitlines()
    assert vcf[0] == "##fileformat=VCFv4.2"
    assert (
        '##INFO=<ID=EXPECTED_PANEL,Number=0,Type=Flag,Description="Expected panel membership">'
        in vcf
    )
    assert "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tPROJECT100" in vcf
    records = [line for line in vcf if not line.startswith("#")]
    assert len(records) == 2
    first_fields = records[0].split("\t")
    assert first_fields[2] == source_rows[0]["sample_id"]
    assert "SAMPLE_ID=" in first_fields[7]
    assert "GENE=ABCA4" in first_fields[7]
    assert "EXPECTED_PANEL" in first_fields[7]
    assert first_fields[8:] == ["GT", "0/1"]

    first_truth = payload["rows"][0]
    assert first_truth["source"] == "eamos_local_transcript_reference"
    assert "project_100_mock_vcf_generator" in first_truth["provenance"]
    assert first_truth["truth"]["expected_panel_membership"] is True
