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
    debug: bool = True
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

    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embeddings_model: str = "text-embedding-3-small"
    search_input_ai_enabled: bool = False
    search_input_ai_timeout_seconds: float = 8.0
    run_chat_top_k: int = 4
    use_real_apis: bool = False
    crispr_provider: str = "local_deterministic"
    crispr_rscript_path: Path = Path("Rscript")
    crispr_ruleset3_conda_env: Path | None = None
    crispr_lindel_conda_env: Path | None = None
    primer_specificity_provider: str = "template"
    ucsc_ispcr_binary_path: Path = Path("./bio_assets/bin/isPcr")
    ucsc_ispcr_hg38_path: Path = Path("./bio_assets/genomes/hg38.2bit")
    ucsc_ispcr_timeout_seconds: float = 30.0
    ucsc_ispcr_min_perfect: int = 15
    ucsc_ispcr_min_good: int = 15
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
        "https://eamos.com.au/checkout/success?session_id={CHECKOUT_SESSION_ID}"
    )
    stripe_checkout_cancel_url: str = "https://eamos.com.au/pricing"
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
