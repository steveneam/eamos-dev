from __future__ import annotations

from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    POST_REFERENCE_DAY1_SOURCE_IDS,
    build_post_reference_source_readiness,
)


def test_post_reference_manifest_covers_user_named_day1_sources() -> None:
    source_ids = set(POST_REFERENCE_DAY1_SOURCE_IDS)

    assert source_ids == {
        "ncbi_dbsnp_gcf_000001405_40",
        "ncbi_clinvar_vcf",
        "repeatmasker_rmsk_bb",
        "ucsc_phylop100way_hg38",
        "ncbi_mane_grch38_v1_4_select_ensembl",
        "gencode_v45_annotation",
        "mondo_disease_ontology",
        "human_phenotype_ontology",
        "clingen_gene_validity",
        "gencc_download",
    }
    for source_id in source_ids:
        assert DEFAULT_DATA_SOURCE_REGISTRY.has(source_id)


def test_manifest_reports_not_ready_until_approval_fields_are_filled() -> None:
    readiness = {item.source_id: item for item in build_post_reference_source_readiness()}

    clinvar = readiness["ncbi_clinvar_vcf"]
    assert clinvar.ready_for_download_or_import is False
    assert clinvar.source_url == (
        "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz"
    )
    assert clinvar.source_version == (
        "ClinVar GRCh38 VCF weekly release 2026-05-25 / clinvar_20260523"
    )
    assert clinvar.checksum_plan
    assert clinvar.terms_url == "https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/"
    assert "source_url" not in clinvar.missing_requirements
    assert "required_before_download" not in clinvar.missing_requirements
    assert "source_version_record" not in clinvar.missing_requirements
    assert "checksum_or_manifest" not in clinvar.missing_requirements
    assert "terms_review" in clinvar.missing_requirements
    assert "backend_storage_policy_review" in clinvar.missing_requirements
    assert "reader_compatibility_proof" in clinvar.missing_requirements
    assert "explicit_download_or_import_approval" in clinvar.missing_requirements


def test_manifest_records_official_source_metadata_without_approval() -> None:
    readiness = build_post_reference_source_readiness()

    for item in readiness:
        assert item.source_url
        assert item.source_url_status.startswith("verified_official")
        assert item.source_version
        assert item.checksum_plan
        assert item.terms_url
        assert item.terms_status
        assert item.download_approved is False
        assert item.ready_for_download_or_import is False
        assert "explicit_download_or_import_approval" in item.missing_requirements
        assert "terms_review" in item.missing_requirements


def test_manifest_preserves_verified_file_identity_corrections() -> None:
    readiness = {item.source_id: item for item in build_post_reference_source_readiness()}

    dbsnp = readiness["ncbi_dbsnp_gcf_000001405_40"]
    mane = readiness["ncbi_mane_grch38_v1_4_select_ensembl"]
    repeatmasker = readiness["repeatmasker_rmsk_bb"]
    hpo = readiness["human_phenotype_ontology"]

    assert dbsnp.files_or_api == ("GCF_000001405.40.gz", "GCF_000001405.40.gz.tbi")
    assert mane.files_or_api == ("MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz",)
    assert repeatmasker.files_or_api == (
        "rmsk.txt.gz",
        "derived rmsk.bb after approved conversion",
    )
    assert hpo.files_or_api == (
        "phenotype.hpoa",
        "genes_to_phenotype.txt",
        "phenotype_to_genes.txt",
        "genes_to_disease.txt",
    )


def test_manifest_flags_staging_and_actual_size_rules() -> None:
    readiness = {item.source_id: item for item in build_post_reference_source_readiness()}

    dbsnp = readiness["ncbi_dbsnp_gcf_000001405_40"]
    phylop = readiness["ucsc_phylop100way_hg38"]

    assert dbsnp.requires_c_drive_staging is True
    assert dbsnp.needs_actual_size_check is False
    assert phylop.requires_c_drive_staging is True
    assert phylop.needs_actual_size_check is False


def test_manifest_marks_supabase_and_repo_assets_backend_owned() -> None:
    readiness = build_post_reference_source_readiness()

    assert all(item.backend_owned_storage for item in readiness)
    assert all("backend_storage_policy_review" in item.missing_requirements for item in readiness)
