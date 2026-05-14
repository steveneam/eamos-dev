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
    jwt_algorithm: str = 'HS256'
    jwt_ttl_days: int = 7

    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embeddings_model: str = "text-embedding-3-small"
    run_chat_top_k: int = 4
    use_real_apis: bool = False
    vep_base_url: str = "https://rest.ensembl.org"
    spliceai_base_url: str = "https://spliceai-38-xwkwwwxdwq-uc.a.run.app/spliceai/"
    clinvar_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

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
