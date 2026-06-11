from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: str = "dev"
    app_name: str = "eamos-backend"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    search_answer_enabled: bool = False
    search_answer_top_k: int = 5
    api_prefix: str = "/api/v1"
    allowed_origins_raw: str = "http://localhost:5173"
    upload_dir: Path = Path("./data/uploads")
    final_report_dir: Path = Path("./data/final_reports")
    max_upload_mb: int = 20
    database_url: str = "sqlite+pysqlite:///./data/app.db"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_ttl_days: int = 7
    supabase_jwt_secret: str | None = None
    supabase_jwt_algorithm: str = "auto"
    supabase_jwks_url: str | None = None
    supabase_jwt_public_key: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_rest_timeout_seconds: float = 10.0
    supabase_storage_s3_endpoint_url: str | None = None
    supabase_storage_s3_region: str | None = None
    supabase_storage_s3_access_key_id: str | None = None
    supabase_storage_s3_secret_access_key: str | None = None
    supabase_local_model_cache_enabled: bool = False
    supabase_local_model_cache_database_url: str | None = None
    supabase_local_model_cache_schema: str = "eamos_private"
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_default_max_requests: int = 60
    rate_limit_auth_max_requests: int = 20
    rate_limit_lookup_max_requests: int = 30
    rate_limit_chat_max_requests: int = 10
    rate_limit_evidence_max_requests: int = 10
    rate_limit_library_max_requests: int = 60
    rate_limit_payments_checkout_max_requests: int = 6
    rate_limit_payments_webhook_max_requests: int = 60
    rate_limit_workbench_max_requests: int = 20
    rate_limit_trust_proxy_headers: bool = False

    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embeddings_model: str = "text-embedding-3-small"
    lookup_chat_timeout_seconds: float = 10.0
    search_input_ai_enabled: bool = False
    search_input_ai_timeout_seconds: float = 8.0
    run_chat_top_k: int = 4
    use_real_apis: bool = False
    workbench_live_design_enabled: bool = True
    local_evidence_enabled: bool = False
    local_evidence_allowed_flows_raw: str = ""
    local_evidence_require_real_apis: bool = True
    pubmed_local_enabled: bool = False
    pubmed_local_sqlite_path: Path = Path("./data/bio_assets/pubmed/pubmed-local.sqlite")
    pubmed_local_manifest_path: Path = Path("./data/bio_assets/pubmed/pubmed-local.manifest.json")
    pubmed_local_startup_materialization_enabled: bool = False
    pubmed_local_fallback_on_no_hit: bool = True
    pubmed_local_max_results: int = 50
    pubmed_local_require_licensed_abstracts: bool = True
    pubmed_local_materialize_timeout_seconds: float = 1200.0
    ncbi_eutils_api_key: str | None = None
    ncbi_eutils_tool: str = "eamos"
    ncbi_eutils_email: str | None = None
    crispr_provider: str = "local_deterministic"
    crispr_rscript_path: Path = Path("Rscript")
    crispr_ruleset3_conda_env: Path | None = None
    crispr_lindel_conda_env: Path | None = None
    crispr_offtarget_provider: str = "auto"
    crispr_offtarget_index_path: Path = Path("./data/bio_assets/crispr/spcas9_offtargets.sqlite")
    crispr_offtarget_index_object_uri: str | None = None
    crispr_offtarget_max_results: int = 200
    primer_specificity_provider: str = "template"
    ucsc_ispcr_binary_path: Path = Path("./bio_assets/bin/isPcr")
    ucsc_ispcr_hg38_path: Path = Path("./bio_assets/genomes/hg38.2bit")
    ucsc_ispcr_timeout_seconds: float = 30.0
    ucsc_ispcr_min_perfect: int = 15
    ucsc_ispcr_min_good: int = 15
    hg38_2bit_runtime_asset_mode: str = "local_path"
    hg38_2bit_runtime_asset_path: Path = Path("./data/bio_assets/genomes/hg38.2bit")
    hg38_2bit_runtime_asset_object_uri: str | None = None
    coordinate_resolver_mane_gff_path: Path = Path(
        "./data/bio_assets/transcripts/MANE.GRCh38.v1.5.refseq_genomic.gff.gz"
    )
    coordinate_resolver_refseq_gff_path: Path = Path(
        "./data/bio_assets/transcripts/GCF_000001405.40_GRCh38.p14_genomic.gff.gz"
    )
    coordinate_resolver_compact_index_path: Path = Path(
        "./data/bio_assets/transcripts/eamos-coordinate-index.latest.jsonl.gz"
    )
    coordinate_resolver_compact_index_object_uri: str | None = None
    coordinate_resolver_compact_index_materialize_timeout_seconds: float = 1200.0
    coordinate_resolver_hg38_2bit_path: Path | None = None
    coordinate_resolver_asset_materialization_enabled: bool = False
    coordinate_resolver_asset_materialization_timeout_seconds: float = 1200.0
    coordinate_resolver_asset_bucket_id: str = "eamos-source-assets"
    coordinate_resolver_mane_gff_object_path: str = (
        "transcripts/mane_refseq_gff/MANE.GRCh38.v1.5.refseq_genomic.gff.gz"
    )
    coordinate_resolver_refseq_gff_object_path: str = (
        "transcripts/refseq_grch38_p14_gff/" "GCF_000001405.40_GRCh38.p14_genomic.gff.gz"
    )
    coordinate_resolver_hg38_2bit_object_path: str = "genomes/ucsc_hg38_2bit/hg38.2bit"
    protein_annotation_enabled: bool = False
    protein_annotation_hmmscan_path: Path = Path("hmmscan")
    protein_annotation_hmmpress_path: Path = Path("hmmpress")
    protein_annotation_pfam_hmm_path: Path = Path("./data/bio_assets/protein_annotation/Pfam-A.hmm")
    protein_annotation_pfam_hmm_gz_path: Path = Path(
        "./data/bio_assets/protein_annotation/downloads/Pfam-A.hmm.gz"
    )
    protein_annotation_pfam_hmm_gz_object_uri: str | None = None
    protein_annotation_pfam_materialize_timeout_seconds: float = 1200.0
    protein_annotation_hmmscan_timeout_seconds: float = 30.0
    protein_annotation_hmmpress_timeout_seconds: float = 900.0
    protein_annotation_require_pfam_indexes: bool = True
    protein_annotation_uniprot_features_enabled: bool = False
    protein_annotation_uniprot_dat_path: Path = Path(
        "./data/bio_assets/protein_annotation/downloads/uniprot_sprot.dat.gz"
    )
    protein_annotation_uniprot_scan_timeout_seconds: float = 20.0
    alphamissense_hg38_runtime_asset_path: Path = Path(
        "./data/bio_assets/predictors/alphamissense/AlphaMissense_hg38.tsv.gz"
    )
    alphamissense_hg38_runtime_asset_mode: str = "local_path"
    alphamissense_hg38_runtime_asset_object_uri: str | None = None
    esm1b_hg38_runtime_asset_path: Path = Path(
        "./data/bio_assets/predictors/esm1b/esm1b_hg38.tsv.gz"
    )
    esm1b_hg38_runtime_asset_mode: str = "local_path"
    esm1b_hg38_runtime_asset_object_uri: str | None = None
    ci_spliceai_model_path: Path = Path(
        "./data/bio_assets/predictors/ci_spliceai/ci_spliceai.keras"
    )
    ci_spliceai_reference_path: Path = Path(
        "./data/bio_assets/predictors/ci_spliceai/hg38_reference.json"
    )
    ci_spliceai_score_cache_path: Path = Path(
        "./data/bio_assets/predictors/ci_spliceai/ci_spliceai_hg38_scores.vcf.gz"
    )
    capice_model_path: Path = Path("./data/bio_assets/predictors/capice/capice_model.json")
    capice_feature_cache_path: Path = Path(
        "./data/bio_assets/predictors/capice/capice_hg38_features.tsv.gz"
    )
    vep_base_url: str = "https://rest.ensembl.org"
    spliceai_base_url: str = "https://spliceai-38-xwkwwwxdwq-uc.a.run.app/spliceai/"
    clinvar_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    variant_validator_base_url: str = "https://rest.variantvalidator.org"
    litvar2_base_url: str = "https://www.ncbi.nlm.nih.gov/research/litvar2-api"
    clingen_erepo_base_url: str = "https://erepo.clinicalgenome.org/evrepo"
    hgnc_rest_base_url: str = "https://rest.genenames.org"
    cache_ttl_days: int = 30
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_webhook_tolerance_seconds: int = 300
    stripe_checkout_success_url: str = (
        "https://eamos-dev.vercel.app/checkout/success?session_id={CHECKOUT_SESSION_ID}"
    )
    stripe_checkout_cancel_url: str = "https://eamos-dev.vercel.app/checkout"
    stripe_price_pro_monthly: str | None = None
    stripe_price_max_monthly: str | None = None

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins_raw.split(",") if item.strip()]

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def fixtures_root(self) -> Path:
        return self.backend_root / "app" / "fixtures"


def _resolve_runtime_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def ensure_runtime_dirs(settings: Settings) -> None:
    settings.upload_dir = _resolve_runtime_path(settings, settings.upload_dir)
    settings.final_report_dir = _resolve_runtime_path(settings, settings.final_report_dir)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.final_report_dir.mkdir(parents=True, exist_ok=True)

    for prefix in ("sqlite+pysqlite:///", "sqlite:///"):
        if settings.database_url.startswith(prefix):
            db_path = Path(settings.database_url[len(prefix) :])
            if not db_path.is_absolute():
                db_path = settings.backend_root / db_path
                settings.database_url = f"{prefix}{db_path.as_posix()}"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            break


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    ensure_runtime_dirs(settings)
    return settings
