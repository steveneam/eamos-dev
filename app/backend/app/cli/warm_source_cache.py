from __future__ import annotations

import argparse
import json

from app.core.config import Settings, ensure_runtime_dirs
from app.core.db import build_session_factory, initialize_database
from app.repos.report_cache_repo import ReportCacheRepo
from app.repos.source_cache_repo import SourceCacheRepo
from app.repos.supabase_local_model_cache_repo import (
    HybridSourceCacheRepo,
    HybridVariantCacheRepo,
    SupabaseSourceCacheRepo,
    SupabaseVariantCacheRepo,
    build_supabase_local_model_cache_store,
)
from app.repos.variant_cache_repo import VariantCacheRepo
from app.rules.clinic_rules import ClinicRules
from app.services.lookup_service import LookupService
from app.services.source_cache import HeroExampleSourceCacheWarmer
from app.tools.registry import build_tool_registry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Warm source-cache rows for the landing hero example variants."
    )
    parser.add_argument(
        "--real-apis",
        action="store_true",
        help="Force USE_REAL_APIS=true for the warm run.",
    )
    parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="Allow fresh cache hits instead of forcing live refresh.",
    )
    parser.add_argument(
        "--skip-supabase-smoke",
        action="store_true",
        help="Skip the fail-fast Supabase cache write/read/delete smoke.",
    )
    args = parser.parse_args()

    settings = Settings(use_real_apis=True) if args.real_apis else Settings()
    ensure_runtime_dirs(settings)
    session_factory = build_session_factory(settings.database_url)
    initialize_database(session_factory)
    variant_cache_repo, source_cache_repo, supabase_store = _build_cache_repos(
        settings,
        session_factory,
    )
    supabase_cache_enabled = supabase_store is not None
    if supabase_store is not None and not args.skip_supabase_smoke:
        supabase_store.smoke_test()

    service = LookupService(
        tool_registry=build_tool_registry(settings),
        rule_engine=ClinicRules(),
        variant_cache_repo=variant_cache_repo,
        report_cache_repo=ReportCacheRepo(session_factory),
        source_cache_repo=source_cache_repo,
        settings=settings,
    )
    results = HeroExampleSourceCacheWarmer(service).warm(refresh=not args.no_refresh)
    print(
        json.dumps(
            {
                "use_real_apis": settings.use_real_apis,
                "supabase_local_model_cache_enabled": supabase_cache_enabled,
                "results": results,
            },
            indent=2,
        )
    )
    return 0


def _build_cache_repos(settings: Settings, session_factory):
    variant_cache_repo = VariantCacheRepo(session_factory)
    source_cache_repo = SourceCacheRepo(session_factory)
    supabase_store = build_supabase_local_model_cache_store(settings)
    if supabase_store is None:
        return variant_cache_repo, source_cache_repo, None
    return (
        HybridVariantCacheRepo(
            local_repo=variant_cache_repo,
            remote_repo=SupabaseVariantCacheRepo(supabase_store),
        ),
        HybridSourceCacheRepo(
            local_repo=source_cache_repo,
            remote_repo=SupabaseSourceCacheRepo(supabase_store),
        ),
        supabase_store,
    )


if __name__ == "__main__":
    raise SystemExit(main())
