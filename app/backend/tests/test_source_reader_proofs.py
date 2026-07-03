from __future__ import annotations

import gzip
import importlib.util
from pathlib import Path

import pytest

from app.services.source_reader_proofs import (
    SourceReaderProofStatus,
    execute_source_reader_proofs,
)


def test_source_reader_proofs_report_real_file_smokes_and_native_pending(
    tmp_path: Path,
) -> None:
    small_root = tmp_path / "small"
    large_root = tmp_path / "large"
    _write_test_sources(small_root=small_root, large_root=large_root)

    result = execute_source_reader_proofs(
        small_staging_root=small_root,
        large_staging_root=large_root,
    )

    by_source = {item.source_id: item for item in result.items}
    assert by_source["ncbi_dbsnp_gcf_000001405_40"].status == (
        SourceReaderProofStatus.PARTIAL_DOWNLOAD
    )
    assert by_source["repeatmasker_rmsk_bb"].status == SourceReaderProofStatus.PROVEN
    assert by_source["ncbi_mane_grch38_v1_4_select_ensembl"].status == (
        SourceReaderProofStatus.PROVEN
    )
    assert by_source["gencode_v45_annotation"].status == SourceReaderProofStatus.PROVEN
    assert by_source["mondo_disease_ontology"].status == SourceReaderProofStatus.PROVEN
    assert by_source["human_phenotype_ontology"].status == SourceReaderProofStatus.PROVEN
    assert by_source["clingen_gene_validity"].status == SourceReaderProofStatus.PROVEN
    assert by_source["gencc_download"].status == SourceReaderProofStatus.PROVEN
    assert by_source["ucsc_phylop100way_hg38"].status == (
        SourceReaderProofStatus.MISSING_LOCAL_FILE
    )

    clinvar_status = by_source["ncbi_clinvar_vcf"].status
    expected_clinvar = (
        SourceReaderProofStatus.PROVEN
        if importlib.util.find_spec("pysam") is not None
        else SourceReaderProofStatus.FORMAT_SMOKE_NATIVE_PENDING
    )
    assert clinvar_status == expected_clinvar
    assert by_source["ncbi_clinvar_vcf"].format_smoke_passed is True


def _write_test_sources(*, small_root: Path, large_root: Path) -> None:
    _write_indexed_vcf_if_native_reader_available(
        small_root / "ncbi_clinvar_vcf" / "clinvar.vcf.gz",
        "\n".join(
            [
                "##fileformat=VCFv4.1",
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
                (
                    "1\t101\tVCV000000001\tA\tG\t.\t.\t"
                    "CLNSIG=Pathogenic;CLNREVSTAT=criteria_provided,_single_submitter"
                ),
                "",
            ]
        ),
    )
    _write_gzip(
        small_root / "repeatmasker_rmsk_bb" / "rmsk.txt.gz",
        (
            "585\t463\t13\t6\t17\tchr1\t10000\t10468\t-248945954\t+\t(TAACCC)n\t"
            "Simple_repeat\tSimple_repeat\t1\t471\t0\t1\n"
        ),
    )
    _write_gzip(
        small_root
        / "ncbi_mane_grch38_v1_4_select_ensembl"
        / "MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz",
        (
            'chr1\tensembl_havana\ttranscript\t3069203\t3438621\t.\t+\t.\tgene_id "G"; '
            'transcript_id "T"; tag "MANE_Select";\n'
        ),
    )
    _write_gzip(
        small_root / "gencode_v45_annotation" / "gencode.v45.annotation.gtf.gz",
        'chr1\tHAVANA\tgene\t11869\t14409\t.\t+\t.\tgene_id "G"; gene_name "DDX11L2";\n',
    )
    (small_root / "mondo_disease_ontology").mkdir(parents=True, exist_ok=True)
    (small_root / "mondo_disease_ontology" / "mondo.json").write_text(
        """
        {
          "graphs": [
            {
              "nodes": [
                {
                  "id": "http://purl.obolibrary.org/obo/MONDO_0008765",
                  "lbl": "Leber congenital amaurosis 2"
                }
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    hpo_root = small_root / "human_phenotype_ontology"
    hpo_root.mkdir(parents=True, exist_ok=True)
    (hpo_root / "hp.json").write_text(
        """
        {
          "graphs": [
            {
              "nodes": [
                {
                  "id": "http://purl.obolibrary.org/obo/HP_0000001",
                  "lbl": "All"
                }
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    (hpo_root / "phenotype.hpoa").write_text(
        "\n".join(
            [
                "database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\t"
                "frequency\tsex\tmodifier\taspect\tbiocuration",
                "OMIM:2\tDisease\t\tHP:0000001\tPMID:1\tPCS\t\t1/2\t\t\tP\tHPO:test",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (hpo_root / "genes_to_phenotype.txt").write_text(
        "ncbi_gene_id\tgene_symbol\thpo_id\thpo_name\tfrequency\tdisease_id\n"
        "10\tNAT2\tHP:0000001\tAll\t-\tOMIM:2\n",
        encoding="utf-8",
    )
    (hpo_root / "phenotype_to_genes.txt").write_text(
        "hpo_id\thpo_name\tncbi_gene_id\tgene_symbol\tdisease_id\n"
        "HP:0000001\tAll\t10\tNAT2\tOMIM:2\n",
        encoding="utf-8",
    )
    (hpo_root / "genes_to_disease.txt").write_text(
        "ncbi_gene_id\tgene_symbol\tassociation_type\tdisease_id\tsource\n"
        "NCBIGene:10\tNAT2\tMENDELIAN\tOMIM:2\tNCBI\n",
        encoding="utf-8",
    )
    (small_root / "clingen_gene_validity").mkdir(parents=True, exist_ok=True)
    (small_root / "clingen_gene_validity" / "clingen_gene_validity.csv").write_text(
        "\n".join(
            [
                '"CLINGEN GENE DISEASE VALIDITY CURATIONS","","","","","","","","",""',
                (
                    '"GENE SYMBOL","GENE ID (HGNC)","DISEASE LABEL","DISEASE ID (MONDO)",'
                    '"MOI","SOP","CLASSIFICATION","ONLINE REPORT","CLASSIFICATION DATE","GCEP"'
                ),
                (
                    '"RPE65","HGNC:10294","Leber congenital amaurosis 2","MONDO:0008765",'
                    '"AR","SOP10","Definitive","https://example.test","2024-03-14","Panel"'
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (small_root / "gencc_download").mkdir(parents=True, exist_ok=True)
    (small_root / "gencc_download" / "gencc-download.csv").write_text(
        (
            "uuid,gene_curie,gene_symbol,disease_curie,disease_title,classification_title,"
            "submitter_title,submitted_as_date\n"
            "GENCC_1,HGNC:10294,RPE65,MONDO:0008765,Disease,Definitive,ClinGen,2024-03-14\n"
        ),
        encoding="utf-8",
    )
    partial = large_root / "ncbi_dbsnp_gcf_000001405_40" / ".GCF_000001405.40.gz.part"
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_bytes(b"partial")


def _write_gzip(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as file:
        file.write(text)


def _write_indexed_vcf_if_native_reader_available(path: Path, text: str) -> None:
    if importlib.util.find_spec("pysam") is None:
        _write_gzip(path, text)
        return

    plain_path = path.with_suffix("")
    plain_path.parent.mkdir(parents=True, exist_ok=True)
    plain_path.write_text(text, encoding="utf-8")
    try:
        import pysam

        pysam.tabix_compress(str(plain_path), str(path), force=True)
        pysam.tabix_index(str(path), preset="vcf", force=True)
    except Exception as exc:  # noqa: BLE001 - optional native proof setup.
        pytest.skip(f"native indexed VCF test asset unavailable: {type(exc).__name__}: {exc}")
    finally:
        plain_path.unlink(missing_ok=True)
