from __future__ import annotations

from app.data_sources.registry_models import DataSourceRecord, LicenseStatus
from app.data_sources.registry_records_mavedb import MAVEDB_SOURCE_RECORDS
from app.data_sources.registry_records_omim import OMIM_SOURCE_RECORDS

DEFAULT_SOURCE_RECORDS: tuple[DataSourceRecord, ...] = (
    DataSourceRecord(
        source_id="ucsc_hg38_2bit",
        display_name="hg38.2bit",
        priority="p0_first_asset_proof",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("hg38.2bit",),
        upstream_source="UCSC Genome Browser",
        source_url="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.2bit",
        source_url_status="known_from_prior_isPcr_asset_install",
        expected_size="about 800 MB",
        storage_target="supabase_storage_after_review",
        temporary_staging="not_expected",
        adapter="twobitreader_or_py2bit_after_compatibility_proof",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("reference_sequence_windows",),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_asset_with_manifest_checksum",
        download_approved=True,
        actual_size_bytes_local=835393456,
        current_local_path="app/backend/data/bio_assets/genomes/hg38.2bit",
        current_local_md5="dcc3ea27079aa6dc3f9deccd7275e0f8",
        source_version="UCSC hg38.2bit initial GRCh38 release / GCA_000001405.15",
        terms_url="https://genome.ucsc.edu/license/",
        terms_status=(
            "Reviewed 2026-05-31: UCSC raw binary data are freely available "
            "for public and commercial use with UCSC citation/credit and "
            "source/version notices."
        ),
        runtime_delivery_modes=(
            "local_path",
            "object_storage_local_cache",
            "mounted_volume",
        ),
        reader_requires_local_path=True,
        storage_policy_reviewed=True,
        notes=(
            "Runtime readers require a local filesystem path. Hosted deployments "
            "should use object storage plus checksum-validated local cache, or a "
            "persistent mounted volume, before enabling full reference reads."
        ),
    ),
    DataSourceRecord(
        source_id="ncbi_dbsnp_gcf_000001405_40",
        display_name="dbSNP GRCh38 GCF_000001405.40",
        priority="p1_day1_identity_after_reference_proof",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("GCF_000001405.40.gz", "GCF_000001405.40.gz.tbi"),
        upstream_source="NCBI dbSNP",
        source_url="https://ftp.ncbi.nih.gov/snp/latest_release/VCF/GCF_000001405.40.gz",
        source_url_status="verified_official_ftp_listing_2026_05_27",
        expected_size="28 GB plus 3.0 MB tabix index in NCBI latest_release listing",
        storage_target="supabase_storage_after_review",
        temporary_staging="stage_on_C_drive",
        adapter="pysam_tabix_after_compatibility_proof",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=(
            "rsid",
            "chrom",
            "position",
            "ref",
            "alt",
            "merge_identity_if_later_approved",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="local_identity_store_plus_source_cache",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="dbSNP latest_release GRCh38 GCF_000001405.40",
        checksum_plan=(
            "Use NCBI CHECKSUMS plus GCF_000001405.40.gz.md5 and "
            "GCF_000001405.40.gz.tbi.md5 before any approved download."
        ),
        terms_url="https://www.ncbi.nlm.nih.gov/home/about/policies/",
        terms_status=(
            "Reviewed 2026-05-31: NCBI places no restrictions on use or "
            "distribution of molecular data it provides, with standard "
            "third-party-rights caveats, attribution, and disclaimer display."
        ),
        notes=(
            "Day 1 large asset. Preserve upstream GCF_000001405.40 naming even "
            "if a local alias later adds a .vcf.gz suffix."
        ),
    ),
    DataSourceRecord(
        source_id="ncbi_clinvar_vcf",
        display_name="ClinVar VCF",
        priority="p2_day1_variant_classification",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("clinvar.vcf.gz", "clinvar.vcf.gz.tbi"),
        upstream_source="NCBI ClinVar FTP",
        source_url="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz",
        source_url_status="verified_official_ftp_listing_2026_05_27",
        expected_size="183 MB plus 595 KB tabix index in 2026-05-25 listing",
        storage_target="supabase_storage_after_review",
        temporary_staging="not_expected",
        adapter="pysam_tabix_after_compatibility_proof",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=(
            "variation_id",
            "classification",
            "review_status",
            "condition_summary",
            "hgvs_aliases",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="local_variant_classification_store_plus_source_cache",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="ClinVar GRCh38 VCF weekly release 2026-05-25 / clinvar_20260523",
        checksum_plan=(
            "Use upstream clinvar.vcf.gz.md5; record index size/checksum and "
            "VCF header fileDate during approved staging."
        ),
        terms_url="https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/",
        terms_status=(
            "Reviewed 2026-05-31: ClinVar is a freely accessible public NCBI "
            "archive; use requires source/submission attribution, release "
            "labeling, and medical-use disclaimers."
        ),
    ),
    DataSourceRecord(
        source_id="repeatmasker_rmsk_bb",
        display_name="RepeatMasker rmsk table / derived bigBed",
        priority="p2_day1_design_context",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("rmsk.txt.gz", "derived rmsk.bb after approved conversion"),
        upstream_source="UCSC Genome Browser hg38 database",
        source_url="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/rmsk.txt.gz",
        source_url_status="verified_official_database_listing_2026_05_27",
        expected_size="148 MB text table before derived bigBed conversion",
        storage_target="supabase_storage_after_review",
        temporary_staging="not_expected",
        adapter="bigbed_reader_or_conversion_path_after_proof",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("repeat_overlap", "repeat_family", "design_warning"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_indexed_asset",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="UCSC hg38 rmsk table dump 2022-10-18",
        checksum_plan=(
            "No verified UCSC per-table md5 sidecar found for rmsk.txt.gz; "
            "record downloaded source SHA256 and derived rmsk.bb SHA256 in manifest."
        ),
        terms_url="https://genome.ucsc.edu/FAQ/FAQdownloads.html",
        terms_status=(
            "Reviewed 2026-05-31: UCSC raw table data are freely available "
            "for public and commercial use with citation/credit; preserve "
            "RepeatMasker/RepBase provenance."
        ),
    ),
    DataSourceRecord(
        source_id="ucsc_phylop100way_hg38",
        display_name="hg38.phyloP100way.bw",
        priority="p2_day1_conservation",
        tier="tier_1_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("hg38.phyloP100way.bw",),
        upstream_source="UCSC PhyloP directory",
        source_url="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/phyloP100way/hg38.phyloP100way.bw",
        source_url_status="verified_official_directory_listing_2026_05_27",
        expected_size="9.2 GB in UCSC phyloP100way listing",
        storage_target="supabase_storage_after_review",
        temporary_staging="stage_on_C_drive",
        adapter="pyBigWig_after_compatibility_proof",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("conservation_score",),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_indexed_asset_plus_small_window_cache",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="UCSC hg38 100-way phyloP bigWig 2015-05-08",
        checksum_plan="Use UCSC md5sum.txt plus manifest SHA256/size before any approved download.",
        terms_url="https://genome.ucsc.edu/goldenPath/credits.html",
        terms_status=(
            "Reviewed 2026-05-31: UCSC phyloP100way files are available for "
            "public use and UCSC data terms allow commercial use with citation, "
            "credits, and derived-genome provenance."
        ),
        notes=(
            "Listed size is below the original 10 GB automatic C-drive rule, "
            "but user directed phyloP to C-drive staging with dbSNP/GCF on "
            "2026-05-27 because it is still a large 9.2 GB asset."
        ),
    ),
    DataSourceRecord(
        source_id="google_deepmind_alphamissense_hg38",
        display_name="AlphaMissense hg38 canonical predictions",
        priority="p6_free_tier_modern_ai_predictor",
        tier="tier_1_object_storage_asset",
        day1_status="approved_not_materialized",
        files_or_api=("AlphaMissense_hg38.tsv.gz", "derived AlphaMissense_hg38.tsv.gz.tbi"),
        upstream_source="Google DeepMind / Zenodo 10813168",
        source_url="https://zenodo.org/records/10813168/files/AlphaMissense_hg38.tsv.gz?download=1",
        source_url_status="verified_official_zenodo_record_2026_06_03",
        expected_size="643.0 MB in Zenodo 10813168 v3 listing",
        storage_target="object_storage_or_mounted_volume_after_download_approval",
        temporary_staging="stage_under_backend_data_or_runtime_volume",
        adapter="tabix_tsv_predictor_reader",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=(
            "am_pathogenicity",
            "am_class",
            "protein_variant",
            "uniprot_id",
            "transcript_id",
            "calibrated_label",
            "calibration_bucket",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_indexed_asset_with_manifest_checksum",
        download_approved=True,
        source_version="AlphaMissense Zenodo 10813168 v3 / record modified 2024-03-13",
        checksum_plan=(
            "Verify Zenodo MD5 9fd167735f16a1b87da6eb3e4c25fcb5 for "
            "AlphaMissense_hg38.tsv.gz, then create and checksum the derived .tbi."
        ),
        terms_url="https://creativecommons.org/licenses/by/4.0/legalcode",
        terms_status=(
            "Reviewed 2026-06-03: Zenodo 10813168 states all materials are "
            "licensed under CC BY 4.0; commercial use is allowed with "
            "attribution, licence link, and no-endorsement/disclaimer handling."
        ),
        runtime_delivery_modes=("local_path", "object_storage_local_cache", "mounted_volume"),
        reader_requires_local_path=True,
        reader_compatibility_proofed=True,
        notes=(
            "Primary Free-tier PP3/BP4 activator once materialized. Use "
            "Bergquist 2025 bands, not the AlphaMissense developer class "
            "thresholds, for ACMG evidence activation."
        ),
    ),
    DataSourceRecord(
        source_id="esm1b_hg38_assembled_scores",
        display_name="ESM1b hg38 assembled missense LLR scores",
        priority="p6_free_tier_modern_ai_predictor",
        tier="tier_1_object_storage_asset",
        day1_status="buildable_mit_regeneration_required",
        files_or_api=("esm1b_hg38.tsv.gz", "esm1b_hg38.tsv.gz.tbi", "manifest.json"),
        upstream_source="EAMOS MANE assembly from ESM1b missense LLR scores",
        source_url="https://github.com/ntranoslab/esm-variants",
        source_url_status="mit_code_verified_precomputed_hf_zip_noncommercial_2026_06_17",
        expected_size="about 2-4 GB compressed assembled MANE Select hg38 table",
        storage_target="mounted_volume_or_object_storage_after_mit_regeneration",
        temporary_staging="offline_build_workspace",
        adapter="tabix_tsv_predictor_reader",
        license_status=LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED,
        allowed_product_tiers=("internal_fixture_only",),
        allowed_fields=(
            "esm1b_llr",
            "aa_sub",
            "uniprot_isoform",
            "mane_tx",
            "calibrated_label",
            "calibration_bucket",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_indexed_asset_with_manifest_checksum",
        download_approved=False,
        source_version="ESM1b assembly target v1; MANE/score-source versions recorded in manifest",
        checksum_plan=(
            "Record source score SHA256, MANE release, GRCh38 reference checksum, "
            "assembly code version, bgzip SHA256, and tabix index SHA256."
        ),
        terms_url="https://huggingface.co/spaces/ntranoslab/esm_variants/blob/main/README.md",
        terms_status=(
            "Reviewed 2026-06-17: the ntranoslab/esm-variants GitHub code is "
            "MIT, but the Hugging Face Space that carries the precomputed "
            "ALL_hum_isoforms_ESM1b_LLR.zip score file declares CC-BY-NC-4.0. "
            "Do not treat that score zip as commercial-safe. Internal-only "
            "staging still requires explicit terms acceptance; commercial ship "
            "requires regeneration from the MIT model with manifest provenance."
        ),
        runtime_delivery_modes=("local_path", "object_storage_local_cache", "mounted_volume"),
        reader_requires_local_path=True,
        reader_compatibility_proofed=True,
        notes=(
            "Pure-code assembly and runtime adapter are buildable now. The "
            "precomputed Hugging Face zip stays non-commercial/internal-only; "
            "public launch clears only when the runtime manifest proves MIT "
            "model regeneration and carries no launch gate."
        ),
    ),
    DataSourceRecord(
        source_id="ci_spliceai_model",
        display_name="CI-SpliceAI offline annotation model",
        priority="p6_free_tier_modern_splice_predictor",
        tier="tier_1_model_and_score_cache_asset",
        day1_status="complete_artifact_set_required",
        files_or_api=(
            "ci_spliceai.keras",
            "hg38_reference.json",
            "ci_spliceai_hg38_scores.vcf.gz",
            "ci_spliceai_hg38_scores.vcf.gz.tbi",
            "manifest.json",
        ),
        upstream_source="CI-SpliceAI offline annotation package",
        source_url="https://github.com/YStrauch/CI-SpliceAI__Annotation",
        source_url_status="official_offline_annotation_repo_reviewed_2026_07_04",
        expected_size="model/reference/score-cache set; exact approved release size pending",
        storage_target="supabase_private_storage_after_complete_artifact_review",
        temporary_staging="offline_build_workspace",
        adapter="ci_spliceai_local_adapter",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=(
            "ds_ag",
            "ds_al",
            "ds_dg",
            "ds_dl",
            "dp_ag",
            "dp_al",
            "dp_dg",
            "dp_dl",
            "max_delta",
            "max_component",
            "calibrated_label",
            "calibration_bucket",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="complete_artifact_set_with_sidecar_manifests",
        download_approved=False,
        source_version=None,
        checksum_plan=(
            "Record exact model, reference bundle, score cache, tabix index, and "
            "sidecar manifest checksums before runtime enablement."
        ),
        terms_url="https://github.com/YStrauch/CI-SpliceAI__Annotation/blob/master/LICENSE",
        terms_status=(
            "Reviewed 2026-07-04: official offline annotation repository license is "
            "CC BY 4.0. Hosted ci-spliceai.com service separately states it may not "
            "be used commercially, so Eamos must self-host reviewed artifacts and "
            "must not depend on the hosted service for production."
        ),
        runtime_delivery_modes=("local_path", "object_storage_local_cache", "mounted_volume"),
        reader_requires_local_path=True,
        reader_compatibility_proofed=True,
        notes=(
            "Backend/admin runtime code is present. Public launch still requires a "
            "complete local artifact set with manifests and bounded resource proof."
        ),
    ),
    DataSourceRecord(
        source_id="gpn_msa_hg38_scores",
        display_name="GPN-MSA hg38 precomputed scores",
        priority="p6_free_tier_modern_ai_predictor",
        tier="tier_1_remote_or_object_storage_asset",
        day1_status="remote_range_reader_planned",
        files_or_api=("scores.tsv.bgz", "scores.tsv.bgz.tbi", "manifest.json"),
        upstream_source="songlab/gpn-msa-hg38-scores Hugging Face dataset",
        source_url="https://huggingface.co/datasets/songlab/gpn-msa-hg38-scores",
        source_url_status="official_huggingface_score_dataset_reviewed_2026_07_04",
        expected_size="81.2 GB total Hugging Face dataset as of 2026-07-04",
        storage_target="remote_range_reader_or_private_storage_after_terms_review",
        temporary_staging="none_until_source_identity_approved",
        adapter="planned_http_range_or_tabix_score_reader",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=(
            "gpn_msa_score",
            "gpn_msa_llr",
            "calibrated_label",
            "calibration_bucket",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="planned_static_score_cache_with_manifest_checksum",
        download_approved=False,
        source_version="songlab/gpn-msa-hg38-scores main; collection updated 2025-09-11",
        checksum_plan=(
            "Record Hugging Face commit/snapshot, scores.tsv.bgz SHA256, "
            "scores.tsv.bgz.tbi SHA256, byte-range proof, and public row schema."
        ),
        terms_url="https://huggingface.co/datasets/songlab/gpn-msa-hg38-scores",
        terms_status=(
            "Reviewed 2026-07-04: Hugging Face dataset card lists MIT license and "
            "documents tabix queries against a remote scores.tsv.bgz file. Runtime "
            "still needs a byte-range reader proof and exact snapshot manifest."
        ),
        runtime_delivery_modes=("remote_http_byte_range", "object_storage_local_cache"),
        reader_requires_local_path=False,
        reader_compatibility_proofed=False,
        notes=(
            "Do not emit report rows until provider-cache reports a reviewed source and "
            "the backend has a fail-closed reader/cache."
        ),
    ),
    DataSourceRecord(
        source_id="pangolin_splice_effect_scores",
        display_name="Pangolin splice-effect scores",
        priority="p6_free_tier_modern_ai_predictor",
        tier="tier_1_model_or_score_cache_asset",
        day1_status="source_and_runtime_design_required",
        files_or_api=("model or coordinate-keyed score cache", "manifest.json"),
        upstream_source="tkzeng/Pangolin",
        source_url="https://github.com/tkzeng/Pangolin",
        source_url_status="official_github_repo_reviewed_2026_07_04",
        expected_size="pending model/cache source decision",
        storage_target="private_storage_or_repo_dependency_after_terms_review",
        temporary_staging="none_until_source_identity_approved",
        adapter="planned_splice_predictor_adapter",
        license_status=LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED,
        allowed_product_tiers=("internal_fixture_only",),
        allowed_fields=(
            "pangolin_delta",
            "pangolin_max_delta",
            "splice_consequence",
            "calibrated_label",
            "calibration_bucket",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="planned_model_or_score_cache_with_manifest_checksum",
        download_approved=False,
        source_version=None,
        checksum_plan=(
            "Record model/cache release identity, artifact checksums, index checksums "
            "when applicable, and runtime resource envelope before enabling."
        ),
        terms_url="https://github.com/tkzeng/Pangolin",
        terms_status=(
            "Reviewed 2026-07-04: Pangolin paper records GitHub/Zenodo availability "
            "under GPL-3.0. It is not non-commercial, but server-side dependency, "
            "packaging, attribution, and redistribution obligations need Eamos "
            "architecture/legal review before runtime enablement."
        ),
        runtime_delivery_modes=("local_path", "object_storage_local_cache", "mounted_volume"),
        reader_requires_local_path=True,
        reader_compatibility_proofed=False,
        notes=(
            "Treat as a visible planned free slot only. It is not report-row materialized "
            "until a backend adapter or cache exists and provider-cache is green."
        ),
    ),
    DataSourceRecord(
        source_id="illumina_spliceai_precomputed_hg38",
        display_name="SpliceAI masked SNV hg38 precomputed scores",
        priority="p6_restricted_predictor",
        tier="tier_1_object_storage_asset",
        day1_status="pro_waitlist_only",
        files_or_api=(
            "spliceai_scores.masked.snv.hg38.vcf.gz",
            "spliceai_scores.masked.snv.hg38.vcf.gz.tbi",
        ),
        upstream_source="Illumina BaseSpace",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 20 GB",
        storage_target="supabase_storage_after_license_approval",
        temporary_staging="stage_on_C_drive",
        adapter="pysam_tabix_after_license_and_compatibility_proof",
        license_status=LicenseStatus.RESTRICTED_UNLICENSED,
        allowed_product_tiers=("licensed_pro_future", "internal_fixture_only"),
        allowed_fields=(),
        restricted_fields=(
            "spliceai",
            "DS_AG",
            "DS_AL",
            "DS_DG",
            "DS_DL",
            "DP_AG",
            "DP_AL",
            "DP_DG",
            "DP_DL",
        ),
        checksum_required=True,
        source_version_required=True,
        cache_policy="locked_until_license_enabled",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="illumina_primateai3d_scores",
        display_name="PrimateAI-3D precomputed scores",
        priority="p6_restricted_predictor",
        tier="tier_1_object_storage_asset",
        day1_status="pro_waitlist_only",
        files_or_api=("primateai3d_scores.vcf.gz", "primateai3d_scores.vcf.gz.tbi"),
        upstream_source="Illumina GitHub/BaseSpace",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 10 GB",
        storage_target="supabase_storage_after_license_approval",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="pysam_tabix_after_license_and_compatibility_proof",
        license_status=LicenseStatus.RESTRICTED_UNLICENSED,
        allowed_product_tiers=("licensed_pro_future", "internal_fixture_only"),
        allowed_fields=(),
        restricted_fields=("primateai_3d", "PrimateAI-3D"),
        checksum_required=True,
        source_version_required=True,
        cache_policy="locked_until_license_enabled",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="uw_cadd_scores_hg38",
        display_name="CADD scores",
        priority="p6_restricted_predictor",
        tier="tier_1_object_storage_asset",
        day1_status="pro_waitlist_only",
        files_or_api=("cadd_scores.tsv.gz", "cadd_scores.tsv.gz.tbi"),
        upstream_source="University of Washington",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 30 GB",
        storage_target="supabase_storage_after_license_approval",
        temporary_staging="stage_on_C_drive",
        adapter="pysam_tabix_after_license_and_compatibility_proof",
        license_status=LicenseStatus.RESTRICTED_UNLICENSED,
        allowed_product_tiers=("licensed_pro_future", "internal_fixture_only"),
        allowed_fields=(),
        restricted_fields=("cadd", "CADD", "CADD PHRED"),
        checksum_required=True,
        source_version_required=True,
        cache_policy="locked_until_license_enabled",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="zenodo_revel_scores",
        display_name="REVEL scores",
        priority="p6_restricted_predictor",
        tier="tier_1_object_storage_asset",
        day1_status="pro_waitlist_only",
        files_or_api=("revel_scores.tsv.gz", "revel_scores.tsv.gz.tbi"),
        upstream_source="Zenodo public repo",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 2 GB",
        storage_target="supabase_storage_after_license_approval",
        temporary_staging="not_expected",
        adapter="pysam_tabix_after_license_and_compatibility_proof",
        license_status=LicenseStatus.RESTRICTED_UNLICENSED,
        allowed_product_tiers=("licensed_pro_future", "internal_fixture_only"),
        allowed_fields=(),
        restricted_fields=("revel", "REVEL"),
        checksum_required=True,
        source_version_required=True,
        cache_policy="locked_until_license_enabled",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="ncbi_mane_grch38_v1_4_select_ensembl",
        display_name="MANE GRCh38 v1.4 Ensembl genomic GTF",
        priority="p3_transcript_model",
        tier="tier_2_repo_asset_candidate",
        day1_status="active_day1",
        files_or_api=("MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz",),
        upstream_source="NCBI MANE FTP",
        source_url=(
            "https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/release_1.4/"
            "MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz"
        ),
        source_url_status="verified_official_release_page_2026_05_27",
        expected_size="8.1 MB in MANE release 1.4 FTP listing",
        storage_target="render_repo_candidate_after_review",
        temporary_staging="not_expected",
        adapter="transcript_model_parser",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("mane_select_transcripts", "gene_transcript_mapping", "exon_cds_model"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_repo_asset_or_object_asset_manifest",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version=("MANE v1.4; RefSeq GCF_000001405.40-RS_2024_08; Ensembl release 114"),
        checksum_plan=(
            "Record upstream FTP size/date plus manifest SHA256; use an upstream "
            "checksum sidecar if present during approved staging."
        ),
        terms_url="https://www.ncbi.nlm.nih.gov/refseq/MANE/",
        terms_status=(
            "Reviewed 2026-05-31: MANE bulk FTP use appears allowed under "
            "NCBI molecular-data policy; retain NCBI/EMBL-EBI attribution, "
            "release identity, retrieval date, and disclaimer."
        ),
        notes=(
            "Official v1.4 GTF observed as ensembl_genomic; select rows must be "
            "extracted by MANE Select tags rather than assuming a separate "
            "select_ensembl GTF file."
        ),
    ),
    DataSourceRecord(
        source_id="ncbi_refseq_grch38_p14",
        display_name="NCBI RefSeq GRCh38.p14 genomic GFF",
        priority="p3_transcript_model",
        tier="tier_2_object_storage_asset",
        day1_status="active_day1",
        files_or_api=("GCF_000001405.40_GRCh38.p14_genomic.gff.gz",),
        upstream_source="NCBI RefSeq assembly FTP",
        source_url=(
            "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/405/"
            "GCF_000001405.40_GRCh38.p14/"
            "GCF_000001405.40_GRCh38.p14_genomic.gff.gz"
        ),
        source_url_status="verified_official_uploaded_coordinate_asset_2026_06_04",
        expected_size="56,923,273 bytes in approved 2026-06-04 coordinate asset upload",
        storage_target="supabase_storage_after_review",
        temporary_staging="not_expected",
        adapter="offline_compact_coordinate_index_builder_input",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gene_transcript_mapping", "exon_cds_model", "refseq_projection_model"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="offline_builder_input_with_manifest_checksum",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="NCBI RefSeq GRCh38.p14 / GCF_000001405.40",
        checksum_plan=(
            "Use the uploaded sidecar manifest plus SHA256/size before approved "
            "offline compact-index builds."
        ),
        terms_url="https://www.ncbi.nlm.nih.gov/home/about/policies/",
        terms_status=(
            "Reviewed 2026-05-31: NCBI molecular data use is allowed with "
            "standard third-party-rights caveats, attribution, release identity, "
            "retrieval date, and disclaimer."
        ),
        notes=(
            "Offline build input only. Runtime lookup/search/report/viewer/batch "
            "must consume the compact coordinate index instead of scanning this GFF."
        ),
    ),
    DataSourceRecord(
        source_id="gencode_v45_annotation",
        display_name="GENCODE v45 annotation GTF",
        priority="p3_transcript_model",
        tier="tier_2_repo_asset_candidate",
        day1_status="active_day1",
        files_or_api=("gencode.v45.annotation.gtf.gz",),
        upstream_source="GENCODE Project",
        source_url=(
            "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/"
            "release_45/gencode.v45.annotation.gtf.gz"
        ),
        source_url_status="verified_official_release_page_2026_05_27",
        expected_size="GENCODE release 45 comprehensive CHR GTF",
        storage_target="render_repo_candidate_after_review",
        temporary_staging="not_expected",
        adapter="transcript_model_parser",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gene_transcript_mapping", "exon_cds_model"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="static_repo_asset_or_object_asset_manifest",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="GENCODE v45; GRCh38.p14; Ensembl release 111; released 2024-01",
        checksum_plan=(
            "Use GENCODE/EBI FTP checksum metadata if present plus manifest "
            "SHA256/size before approved staging."
        ),
        terms_url="https://www.ebi.ac.uk/about/terms-of-use/",
        terms_status=(
            "Reviewed 2026-05-31: GENCODE data are open access and EMBL-EBI "
            "adds no extra redistribution restrictions beyond original-owner "
            "terms; retain attribution and exact release metadata."
        ),
    ),
    DataSourceRecord(
        source_id="intervar_pipeline_config",
        display_name="InterVar pipeline configuration files",
        priority="p6_license_blocked_optional",
        tier="tier_2_repo_asset_candidate",
        day1_status="docx_intended_day1_blocked_for_commercial_production",
        files_or_api=("InterVar pipeline configuration files",),
        upstream_source="GitHub InterVar repo",
        source_url=None,
        source_url_status="required_before_download",
        expected_size="about 10 MB",
        storage_target="blocked_until_license_review",
        temporary_staging="not_expected",
        adapter="optional_licensed_intervar_integration",
        license_status=LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED,
        allowed_product_tiers=("internal_review_only",),
        allowed_fields=(),
        restricted_fields=(
            "intervar_acmg_classification",
            "annovar_dependencies",
            "omim_derived_inputs",
        ),
        checksum_required=True,
        source_version_required=True,
        cache_policy="blocked_until_license_enabled",
        download_approved=False,
        notes=(
            "DOCX-intended, but commercial production requires InterVar, "
            "ANNOVAR, and OMIM rights review."
        ),
    ),
    DataSourceRecord(
        source_id="python_primer3_py",
        display_name="primer3-py",
        priority="p_existing_runtime_dependency",
        tier="tier_2_5_python_engine",
        day1_status="already_present",
        files_or_api=("app/backend/requirements.txt",),
        upstream_source="primer3-py package",
        source_url=None,
        source_url_status="record_package_source_before_runtime_policy_change",
        expected_size="package_dependency",
        storage_target="backend_runtime_dependency",
        temporary_staging="not_applicable",
        adapter="existing_primer_provider",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("existing_runtime",),
        allowed_fields=("primer_thermodynamics",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="provider_version_invalidation",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="python_biopython",
        display_name="biopython",
        priority="p_existing_runtime_dependency",
        tier="tier_2_5_python_engine",
        day1_status="already_present",
        files_or_api=("app/backend/requirements.txt",),
        upstream_source="Biopython package",
        source_url=None,
        source_url_status="record_package_source_before_runtime_policy_change",
        expected_size="package_dependency",
        storage_target="backend_runtime_dependency",
        temporary_staging="not_applicable",
        adapter="existing_alignment_and_sequence_helpers",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("existing_runtime",),
        allowed_fields=("sequence_helpers", "alignment_support"),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="provider_version_invalidation",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="python_pysam",
        display_name="pysam",
        priority="p_future_reader_dependency",
        tier="tier_2_5_python_engine",
        day1_status="selected_for_task_9_linux_reader_proof_windows_unavailable",
        files_or_api=("pysam==0.24.0",),
        upstream_source="PyPI pysam package",
        source_url="https://pypi.org/project/pysam/0.24.0/",
        source_url_status="verified_pypi_metadata_2026_05_27",
        expected_size=(
            "22.7 MB CPython 3.10 manylinux x86_64 wheel; no Windows wheels "
            "found in PyPI release metadata"
        ),
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="pysam_indexed_vcf_reader",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("indexed_variant_file_access",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="not_applicable",
        download_approved=False,
        source_version="pysam 0.24.0",
        checksum_plan=(
            "Pin exact PyPI distribution version; use pip hash lock before "
            "production dependency freeze."
        ),
        terms_url="https://github.com/pysam-developers/pysam",
        terms_status="Package metadata recorded; dependency/license review still required",
        notes=(
            "PyPI provides Linux/mac wheels for 0.24.0 but no Windows wheels. "
            "The Windows host cannot install this natively; Render/Linux can "
            "install via the platform-marked requirements pin."
        ),
    ),
    DataSourceRecord(
        source_id="python_twobit_reader",
        display_name="twobitreader",
        priority="p_future_reader_dependency",
        tier="tier_2_5_python_engine",
        day1_status="selected_for_task_7_reference_proof",
        files_or_api=("twobitreader==3.1.8",),
        upstream_source="PyPI twobitreader package",
        source_url="https://pypi.org/project/twobitreader/3.1.8/",
        source_url_status="verified_pypi_metadata_2026_05_27",
        expected_size="14.1 kB py3-none-any wheel",
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="twobitreader_reference_genome_store",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("reference_sequence_windows",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="not_applicable",
        download_approved=False,
        notes=(
            "Selected over py2bit for Task 7 because PyPI publishes a pure "
            "Python py3-none-any wheel for twobitreader 3.1.8, while py2bit is "
            "a C extension with POSIX/manylinux-oriented artifacts."
        ),
    ),
    DataSourceRecord(
        source_id="python_pybigwig",
        display_name="pyBigWig",
        priority="p_future_reader_dependency",
        tier="tier_2_5_python_engine",
        day1_status="selected_for_task_9_linux_reader_proof_windows_unavailable",
        files_or_api=("pyBigWig==0.3.25",),
        upstream_source="PyPI pyBigWig package",
        source_url="https://pypi.org/project/pyBigWig/0.3.25/",
        source_url_status="verified_pypi_metadata_2026_05_27",
        expected_size=(
            "183.5 kB CPython 3.10 manylinux x86_64 wheel; no Windows wheels "
            "found in PyPI release metadata"
        ),
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="pybigwig_conservation_reader",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("conservation_score",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="not_applicable",
        download_approved=False,
        source_version="pyBigWig 0.3.25",
        checksum_plan=(
            "Pin exact PyPI distribution version; use pip hash lock before "
            "production dependency freeze."
        ),
        terms_url="https://github.com/deeptools/pyBigWig",
        terms_status="Package metadata recorded; dependency/license review still required",
        notes=(
            "PyPI provides Linux wheels for 0.3.25 but no Windows wheels. The "
            "Windows host cannot install this natively; Render/Linux can "
            "install via the platform-marked requirements pin."
        ),
    ),
    DataSourceRecord(
        source_id="python_duckdb_pyarrow",
        display_name="duckdb and optional pyarrow",
        priority="p_future_reader_dependency",
        tier="tier_2_5_python_engine",
        day1_status="candidate_after_store_design",
        files_or_api=("python_package",),
        upstream_source="DuckDB and PyArrow packages",
        source_url=None,
        source_url_status="required_before_install",
        expected_size="package_dependency",
        storage_target="backend_runtime_dependency_after_review",
        temporary_staging="not_applicable",
        adapter="optional_columnar_local_store",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("future_after_review",),
        allowed_fields=("local_columnar_queries",),
        restricted_fields=(),
        checksum_required=False,
        source_version_required=True,
        cache_policy="provider_version_invalidation",
        download_approved=False,
    ),
    DataSourceRecord(
        source_id="mondo_disease_ontology",
        display_name="Mondo Disease Ontology",
        priority="p4_small_source_table",
        tier="tier_3_supabase_postgres_table",
        day1_status="active_day1",
        files_or_api=("mondo.json", "derived mondo.tsv after parser proof"),
        upstream_source="Mondo Disease Ontology",
        source_url="https://purl.obolibrary.org/obo/mondo.json",
        source_url_status="verified_official_download_page_2026_05_27",
        expected_size="about 100 MB JSON edition",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="disease_ontology_table",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("disease_ids", "disease_names", "cross_references"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="Mondo stable release; latest observed release 2026-05-05",
        checksum_plan=(
            "Record release version IRI and local SHA256/size for mondo.json; "
            "record derived TSV checksum if generated."
        ),
        terms_url="https://mondo.monarchinitiative.org/pages/download/",
        terms_status=(
            "Reviewed 2026-05-31: Mondo is CC BY 4.0; commercial use and "
            "redistribution are allowed with attribution, license link, "
            "change notices, and release/version display."
        ),
        notes=(
            "DOCX label says OMIM and Orphanet combined, but listed files are "
            "Mondo. Do not import OMIM-derived files without separate review."
        ),
    ),
    DataSourceRecord(
        source_id="human_phenotype_ontology",
        display_name="Human Phenotype Ontology annotations",
        priority="p4_small_source_table",
        tier="tier_3_supabase_postgres_table",
        day1_status="active_day1",
        files_or_api=(
            "hp.json",
            "phenotype.hpoa",
            "genes_to_phenotype.txt",
            "phenotype_to_genes.txt",
            "genes_to_disease.txt",
        ),
        upstream_source="Human Phenotype Ontology",
        source_url="https://obophenotype.github.io/human-phenotype-ontology/annotations/phenotype_hpoa/",
        source_url_status="verified_official_annotation_docs_2026_05_27",
        expected_size="small annotation files; exact sizes recorded at import approval",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="phenotype_annotation_table",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("phenotype_ids", "phenotype_terms", "gene_or_disease_links"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="HPO release 2026-02-16 observed; record annotation file headers at import",
        checksum_plan=(
            "Use GitHub release SHA256 assets where available; otherwise record "
            "local SHA256/size for approved HPO ontology and annotation files "
            "before import."
        ),
        terms_url="https://human-phenotype-ontology.github.io/license.html",
        terms_status=(
            "Reviewed 2026-05-31: HPO files are freely available with required "
            "HPO acknowledgement/citation and file date/version display; do "
            "not alter HPO meanings in transformed tables."
        ),
        notes=(
            "The draft hp.gpad path was not verified at the expected OBO PURL; "
            "start from the official HPO annotation files documented by HPO."
        ),
    ),
    DataSourceRecord(
        source_id="clingen_gene_validity",
        display_name="ClinGen gene validity",
        priority="p4_small_source_table",
        tier="tier_3_supabase_postgres_table",
        day1_status="active_day1",
        files_or_api=("clingen_gene_validity.csv",),
        upstream_source="ClinGen",
        source_url="https://search.clinicalgenome.org/kb/gene-validity/download",
        source_url_status="verified_official_download_page_2026_05_27",
        expected_size="real-time generated CSV; exact size recorded at import approval",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="gene_disease_validity_table",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gene", "disease", "validity_classification", "source_date"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="ClinGen Gene-Disease Validity real-time CSV export",
        checksum_plan="Record export timestamp, source URL, local SHA256, and row count before import.",
        terms_url="https://clinicalgenome.org/docs/terms-of-use/",
        terms_status=(
            "Reviewed 2026-05-31: ClinGen curated content is available under "
            "CC0 with requested attribution/date accessed and medical-use "
            "disclaimer display."
        ),
    ),
    DataSourceRecord(
        source_id="gencc_download",
        display_name="GenCC download",
        priority="p4_small_source_table",
        tier="tier_3_supabase_postgres_table",
        day1_status="active_day1",
        files_or_api=("gencc-download.csv",),
        upstream_source="GenCC",
        source_url="https://search.thegencc.org/download/action/submissions-export-csv",
        source_url_status="verified_official_site_2026_05_27",
        expected_size="live submissions export; exact size recorded at import approval",
        storage_target="supabase_postgres_after_review",
        temporary_staging="not_expected",
        adapter="gene_disease_assertion_table",
        license_status=LicenseStatus.PUBLIC_ALLOWED_AFTER_TERMS_REVIEW,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gene", "disease", "assertion", "submitter", "source_date"),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="postgres_import_with_source_version",
        download_approved=True,
        storage_policy_reviewed=True,
        reader_compatibility_proofed=True,
        source_version="GenCC live submissions export; version by export date",
        checksum_plan="Record export timestamp, local SHA256, row count, and source statistics before import.",
        terms_url="https://search.thegencc.org/terms",
        terms_status=(
            "Reviewed 2026-05-31: GenCC download data are CC0 with requested "
            "GenCC/contributor attribution and access date; OMIM-derived data "
            "are excluded and must not be added without separate license."
        ),
    ),
    *MAVEDB_SOURCE_RECORDS,
    *OMIM_SOURCE_RECORDS,
    DataSourceRecord(
        source_id="uniprotkb_reviewed_swissprot",
        display_name="UniProtKB reviewed Swiss-Prot protein annotations",
        priority="p5_protein_annotation_terms_recorded",
        tier="tier_3_5_protein_annotation_asset",
        day1_status="candidate_terms_recorded_not_enabled",
        files_or_api=(
            "UniProtKB reviewed Swiss-Prot canonical entries",
            "optional human reviewed subset",
        ),
        upstream_source="UniProt Consortium",
        source_url="https://www.uniprot.org/help/downloads",
        source_url_status="official_download_docs_recorded_no_runtime_api_dependency",
        expected_size="download/subset size to be recorded during approved staging",
        storage_target="object_storage_or_mounted_volume_after_import_approval",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="local_uniprotkb_feature_store",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_and_commercial_after_import_approval",),
        allowed_fields=(
            "protein_accession",
            "protein_name",
            "sequence_length",
            "curated_feature_ranges",
            "active_sites",
            "binding_sites",
            "ptm_sites",
            "cross_references",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="local_static_release_with_manifest_checksum",
        download_approved=False,
        actual_size_bytes_local=692563345,
        current_local_path=(
            "app/backend/data/bio_assets/protein_annotation/downloads/" "uniprot_sprot.dat.gz"
        ),
        current_local_md5="d6bd6e9435cd819b64cd888068530a45",
        source_version="UniProtKB/Swiss-Prot current_release downloaded 2026-05-29",
        checksum_plan=(
            "Local staged SHA256 "
            "bb3815e7b6445566ad9c8479f659033aa2115ed3cf2b06e61ae37c1dabc60438; "
            "record upstream release notes before production import."
        ),
        terms_url="https://www.uniprot.org/help/license",
        terms_status=(
            "UniProt databases are CC BY 4.0 for copyrightable database "
            "content. Commercial use is allowed with attribution, license "
            "link, change notices when applicable, no endorsement implication, "
            "and UniProt disclaimer/patent caveats recorded."
        ),
        notes=(
            "Use as the curated protein-feature source via release-pinned "
            "local import/mirror only. Live UniProt API calls are not an "
            "approved runtime dependency."
        ),
    ),
    DataSourceRecord(
        source_id="interpro_pfam_protein_matches",
        display_name="InterPro/Pfam protein-domain matches",
        priority="p5_protein_annotation_terms_recorded",
        tier="tier_3_5_protein_annotation_asset",
        day1_status="candidate_terms_recorded_not_enabled",
        files_or_api=("InterPro/Pfam protein match data", "Pfam protein-coordinate ranges"),
        upstream_source="EMBL-EBI InterPro / Pfam",
        source_url="https://interpro-documentation.readthedocs.io/en/latest/license.html",
        source_url_status="official_license_docs_recorded_no_runtime_api_dependency",
        expected_size="download/subset size to be recorded during approved staging",
        storage_target="object_storage_or_mounted_volume_after_import_approval",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="local_interpro_pfam_match_store",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_and_commercial_after_import_approval",),
        allowed_fields=(
            "pfam_accession",
            "interpro_accession",
            "domain_name",
            "aa_start",
            "aa_end",
            "match_score",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="local_static_release_with_manifest_checksum",
        download_approved=False,
        actual_size_bytes_local=384357362,
        current_local_path=(
            "app/backend/data/bio_assets/protein_annotation/downloads/" "Pfam-A.hmm.gz"
        ),
        current_local_md5="dc814cc181ece09102c09c4e6c19f2fd",
        source_version="Pfam current_release downloaded 2026-05-29",
        checksum_plan=(
            "Local staged Pfam-A.hmm.gz SHA256 "
            "d3d30c8e6801bfedecf783408ecc98916f8f1dda8974c6e51036fcbdd765f591; "
            "Pfam-A.hmm.dat.gz sidecar size 718721 bytes, MD5 "
            "41a8fb4c9391e814795587fcdc8baa33, SHA256 "
            "4da981816a630fd77171cc5d369716bbe16e58dae8be8047ac1118e0bd64ebe4."
        ),
        terms_url="https://www.ebi.ac.uk/about/terms-of-use/",
        terms_status=(
            "InterPro, Pfam, PRINTS, and SFLD downloadable data on the "
            "InterPro website are CC0; no special commercial license is "
            "required, so commercial use is allowed. Citations and bundled "
            "copyright statements still need to be retained."
        ),
        notes=(
            "Preferred domain-architecture source for the richer protein "
            "view. Use local release data only; API access is not approved by "
            "this row."
        ),
    ),
    DataSourceRecord(
        source_id="interproscan_standalone",
        display_name="InterProScan standalone sequence annotator",
        priority="p5_local_sequence_annotation_terms_recorded",
        tier="tier_2_5_local_annotation_engine",
        day1_status="candidate_terms_recorded_not_enabled",
        files_or_api=("InterProScan standalone package", "InterProScan data bundle"),
        upstream_source="EMBL-EBI InterPro",
        source_url="https://interproscan-docs.readthedocs.io/en/v6/HowToInstall.html",
        source_url_status="official_install_docs_recorded_no_runtime_api_dependency",
        expected_size="large local tool/data bundle; exact size to be recorded before staging",
        storage_target="mounted_volume_or_worker_image_after_import_approval",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="offline_sequence_to_interpro_features_worker",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_and_commercial_after_import_approval",),
        allowed_fields=(
            "local_sequence_domain_predictions",
            "families",
            "domains",
            "functional_sites",
            "go_terms_if_available",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="offline_job_cache_by_sequence_hash_and_tool_release",
        download_approved=False,
        actual_size_bytes_local=58031205,
        current_local_path=(
            "app/backend/data/bio_assets/protein_annotation/downloads/" "interproscan6-main.zip"
        ),
        current_local_md5="97d76552a7886ebe6ac944786fae4363",
        source_version="ebi-pf-team/interproscan6 main zip downloaded 2026-05-29",
        checksum_plan=(
            "Local staged SHA256 "
            "80ed03963f9f313c1e717b53fae54f063938e30bfaf415801599df18cab670e5; "
            "pin a tagged InterProScan release before production worker image build."
        ),
        terms_url="https://interproscan-docs.readthedocs.io/en/v6/index.html",
        terms_status=(
            "InterProScan software is Apache licensed. Core local processing "
            "is allowed, but included tools/signature collections can have "
            "different terms; SignalP, Phobius, and DeepTMHMM remain disabled "
            "unless separately licensed."
        ),
        notes=(
            "This is the no-API path for annotating novel user sequences. It "
            "should run as a bounded backend job with --no-matches-api or a "
            "local MLS, not a Render startup download."
        ),
    ),
    DataSourceRecord(
        source_id="interproscan_optional_licensed_apps",
        display_name="InterProScan optional licensed apps",
        priority="p5_optional_protein_annotation_licensed_apps",
        tier="tier_2_5_local_annotation_engine",
        day1_status="blocked_until_component_licenses",
        files_or_api=("SignalP", "Phobius", "DeepTMHMM"),
        upstream_source="SignalP, Phobius, and DeepTMHMM providers",
        source_url="https://interproscan-docs.readthedocs.io/en/v6/InstallingLicensedApps.html",
        source_url_status="official_docs_recorded_separate_licenses_required",
        expected_size="component-specific licensed downloads",
        storage_target="not_enabled_until_license_proof",
        temporary_staging="not_applicable_until_licensed",
        adapter="disabled_optional_interproscan_apps_policy",
        license_status=LicenseStatus.COMMERCIAL_LICENSE_REVIEW_REQUIRED,
        allowed_product_tiers=("blocked_until_licensed",),
        allowed_fields=(),
        restricted_fields=(
            "signal_peptide_predictions",
            "transmembrane_topology_predictions",
        ),
        checksum_required=True,
        source_version_required=True,
        cache_policy="disabled_until_component_license_and_version_record",
        download_approved=False,
        terms_url="https://interproscan-docs.readthedocs.io/en/v6/InstallingLicensedApps.html",
        terms_status=(
            "InterProScan docs state SignalP, Phobius, and DeepTMHMM analyses "
            "are deactivated by default due to licensing and require licenses "
            "and files from their respective providers."
        ),
        notes=(
            "Not required for the core Pfam/InterPro domain track. Keep these "
            "apps disabled until component licenses, checksums, and leak tests "
            "are recorded."
        ),
    ),
    DataSourceRecord(
        source_id="hmmer_pfam_a",
        display_name="HMMER hmmscan with Pfam-A profiles",
        priority="p5_local_sequence_annotation_terms_recorded",
        tier="tier_2_5_local_annotation_engine",
        day1_status="candidate_terms_recorded_not_enabled",
        files_or_api=("hmmscan", "Pfam-A.hmm", "hmmpress indexes"),
        upstream_source="HMMER / EMBL-EBI Pfam",
        source_url="http://hmmer.org/",
        source_url_status="official_source_docs_recorded_no_runtime_api_dependency",
        expected_size="Pfam-A profile database is large; exact size to be recorded before staging",
        storage_target="mounted_volume_or_worker_image_after_import_approval",
        temporary_staging="check_actual_size_stage_on_C_if_greater_than_10gb",
        adapter="offline_hmmscan_pfam_domain_worker",
        license_status=LicenseStatus.COMMERCIAL_ALLOWED,
        allowed_product_tiers=("public_and_commercial_after_import_approval",),
        allowed_fields=(
            "pfam_accession",
            "domain_name",
            "aa_start",
            "aa_end",
            "e_value",
            "bit_score",
        ),
        restricted_fields=(),
        checksum_required=True,
        source_version_required=True,
        cache_policy="offline_job_cache_by_sequence_hash_and_pfam_release",
        download_approved=False,
        actual_size_bytes_local=19669667,
        current_local_path=(
            "app/backend/data/bio_assets/protein_annotation/downloads/" "hmmer.tar.gz"
        ),
        current_local_md5="b1ed21ceea33930222c84f8c4d9f4240",
        source_version="HMMER source tarball 3.4 downloaded 2026-05-29",
        checksum_plan=(
            "Local staged SHA256 "
            "ca70d94fd0cf271bd7063423aabb116d42de533117343a9b27a65c17ff06fbf3; "
            "build/install step remains explicit and is not performed by "
            "download staging."
        ),
        terms_url="https://raw.githubusercontent.com/EddyRivasLab/hmmer/master/LICENSE",
        terms_status=(
            "HMMER source is BSD 3-clause licensed. Pfam is CC0 through the "
            "InterPro/Pfam docs. Commercial local hmmscan use is allowed when "
            "notices and citations are retained."
        ),
        notes=(
            "Lean fallback if full InterProScan is too heavy. This predicts "
            "Pfam domains locally, but it is not a substitute for UniProtKB "
            "expert curation."
        ),
    ),
    DataSourceRecord(
        source_id="myvariant_gnomad_only",
        display_name="MyVariant gnomAD-only API adapter",
        priority="p2_day1_api_after_policy",
        tier="tier_4_live_api",
        day1_status="active_day1",
        files_or_api=("myvariant.info API", "gnomad_genome", "gnomad_exome"),
        upstream_source="MyVariant.info",
        source_url=None,
        source_url_status="required_before_adapter_enablement",
        expected_size="zero-download live public cloud API",
        storage_target="live_api_plus_source_cache",
        temporary_staging="not_applicable",
        adapter="httpx_provider",
        license_status=LicenseStatus.PENDING_TERMS_RECORD,
        allowed_product_tiers=("public_day1_after_review",),
        allowed_fields=("gnomad_genome", "gnomad_exome"),
        restricted_fields=(
            "cadd",
            "dbnsfp.revel",
            "dbnsfp.primateai",
            "spliceai",
            "revel",
            "primateai_3d",
        ),
        checksum_required=False,
        source_version_required=True,
        cache_policy="source_cache_by_normalized_variant_field_set_and_adapter_version",
        download_approved=False,
        notes=(
            "Use only for gnomAD frequency lookup. Aggregation does not remove "
            "upstream licensing obligations."
        ),
    ),
)
