from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.clinical_source_tables import (
    CLINGEN_GENE_VALIDITY_SOURCE_ID,
    GENCC_SOURCE_ID,
    HPO_SOURCE_ID,
    MONDO_SOURCE_ID,
    ClinicalSourceTableError,
    ClinicalSourceTableStore,
    ClinicalTableProvenance,
    parse_clingen_gene_validity_csv,
    parse_gencc_download_csv,
    parse_mondo_json,
    parse_phenotype_hpoa,
)


def test_store_provenance_records_small_source_fixture_metadata() -> None:
    store = ClinicalSourceTableStore()
    provenance = store.provenance()

    assert {item.source_id for item in provenance} == {
        MONDO_SOURCE_ID,
        HPO_SOURCE_ID,
        CLINGEN_GENE_VALIDITY_SOURCE_ID,
        GENCC_SOURCE_ID,
    }
    assert {item.relative_path for item in provenance if item.source_id == HPO_SOURCE_ID} == {
        "app/backend/app/fixtures/source_tables/phenotype_tiny.hpoa",
        "app/backend/app/fixtures/source_tables/hpo_terms_tiny.tsv",
        "app/backend/app/fixtures/source_tables/genes_to_phenotype_tiny.txt",
    }
    for item in provenance:
        assert item.source_version
        assert item.checksum_algorithm == "sha256"
        assert re.fullmatch(r"[0-9a-f]{64}", item.checksum)


def test_mondo_fixture_resolves_disease_name_and_cross_references_without_omim_import() -> None:
    store = ClinicalSourceTableStore()

    disease = store.mondo_by_id("MONDO_0008765")
    by_omim = store.mondo_by_xref("OMIM:204100")

    assert disease is not None
    assert by_omim == disease
    assert disease.mondo_id == "MONDO:0008765"
    assert disease.name == "Leber congenital amaurosis 2"
    assert disease.xrefs == ("OMIM:204100", "ORPHANET:65", "MEDGEN:C1859844")
    assert disease.provenance.source_id == MONDO_SOURCE_ID
    assert disease.provenance.relative_path.endswith("mondo_tiny.json")


def test_hpo_fixture_links_disease_and_gene_context_to_hpo_ids_and_labels() -> None:
    links = ClinicalSourceTableStore().hpo_links(gene="rpe65", disease_id="OMIM:204100")

    assert [link.hpo_id for link in links] == ["HP:0000510", "HP:0000662"]
    assert [link.hpo_label for link in links] == ["Visual impairment", "Nyctalopia"]
    assert all(link.gene_symbol == "RPE65" for link in links)
    assert all(link.disease_id == "OMIM:204100" for link in links)
    assert links[0].disease_name == "Leber congenital amaurosis 2"
    assert links[0].disease_evidence == "PCS"
    assert {item.source_id for item in links[0].provenance} == {HPO_SOURCE_ID}


def test_clingen_gene_validity_fixture_returns_classification_and_source_date() -> None:
    records = ClinicalSourceTableStore().clingen_validity(
        gene="RPE65",
        disease_id="MONDO:0008765",
    )

    assert len(records) == 1
    record = records[0]
    assert record.gene_symbol == "RPE65"
    assert record.gene_hgnc_id == "HGNC:10294"
    assert record.disease_label == "Leber congenital amaurosis 2"
    assert record.classification == "Definitive"
    assert record.mode_of_inheritance == "Autosomal recessive inheritance"
    assert record.source_date == "2024-03-14"
    assert record.provenance.source_id == CLINGEN_GENE_VALIDITY_SOURCE_ID


def test_gencc_fixture_returns_assertion_submitter_disease_gene_and_source_date() -> None:
    records = ClinicalSourceTableStore().gencc_assertions(
        gene="RPE65",
        disease_id="MONDO:0008765",
    )

    assert len(records) == 1
    record = records[0]
    assert record.gene_symbol == "RPE65"
    assert record.gene_curie == "HGNC:10294"
    assert record.disease_title == "Leber congenital amaurosis 2"
    assert record.disease_curie == "MONDO:0008765"
    assert record.assertion == "Definitive"
    assert record.submitter == "ClinGen"
    assert record.source_date == "2024-03-14"
    assert record.provenance.source_id == GENCC_SOURCE_ID


def test_parser_failures_are_structured_and_do_not_drop_malformed_rows(tmp_path: Path) -> None:
    provenance = _test_provenance(tmp_path / "fixture.txt")

    bad_mondo = tmp_path / "bad_mondo.json"
    bad_mondo.write_text(
        '{"graphs":[{"nodes":[{"id":"http://purl.obolibrary.org/obo/MONDO_0000001"}]}]}',
        encoding="utf-8",
    )
    with pytest.raises(ClinicalSourceTableError) as mondo_exc:
        parse_mondo_json(bad_mondo, provenance=provenance)

    bad_hpoa = tmp_path / "bad.hpoa"
    bad_hpoa.write_text(
        "\n".join(
            [
                (
                    "#DatabaseID\tDiseaseName\tQualifier\tHPO_ID\tReference\tEvidence\tOnset\t"
                    "Frequency\tSex\tModifier\tAspect\tBiocuration"
                ),
                "OMIM:1\tBad disease\t\t\tPMID:1\tPCS\t\t\t\t\tP\tHPO:test",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ClinicalSourceTableError) as hpoa_exc:
        parse_phenotype_hpoa(
            bad_hpoa,
            hpo_terms={"HP:0000001": "All"},
            provenance=provenance,
        )

    bad_clingen = tmp_path / "bad_clingen.csv"
    bad_clingen.write_text(
        "\n".join(
            [
                (
                    "GENE SYMBOL,GENE ID (HGNC),DISEASE LABEL,DISEASE ID (MONDO),MOI,"
                    "CLASSIFICATION,CLASSIFICATION DATE,ONLINE REPORT"
                ),
                "RPE65,HGNC:10294,Leber congenital amaurosis 2,MONDO:0008765,AR,,2024-03-14,",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ClinicalSourceTableError) as clingen_exc:
        parse_clingen_gene_validity_csv(bad_clingen, provenance=provenance)

    bad_gencc = tmp_path / "bad_gencc.csv"
    bad_gencc.write_text(
        "\n".join(
            [
                (
                    "uuid,gene_curie,gene_symbol,disease_curie,disease_title,"
                    "classification_title,submitter_title,submitted_as_date"
                ),
                "GENCC_1,HGNC:10294,RPE65,MONDO:0008765,Leber congenital amaurosis 2,Definitive,,2024-03-14",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ClinicalSourceTableError) as gencc_exc:
        parse_gencc_download_csv(bad_gencc, provenance=provenance)

    assert mondo_exc.value.code == "malformed_mondo_node"
    assert hpoa_exc.value.code == "malformed_hpoa_row"
    assert clingen_exc.value.code == "malformed_clingen_gene_validity_row"
    assert gencc_exc.value.code == "malformed_gencc_row"


def _test_provenance(path: Path) -> ClinicalTableProvenance:
    return ClinicalTableProvenance(
        source_id="test_source",
        source_version="test",
        checksum_algorithm="sha256",
        checksum="0" * 64,
        relative_path=path.name,
    )
