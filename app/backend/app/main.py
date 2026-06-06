from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.client import (
    build_draft_chain,
    build_embeddings_model,
    build_extraction_chain,
    build_lookup_chat_chain,
    build_run_chat_chain,
)
from app.api.routes import build_api_router
from app.core.config import ensure_runtime_dirs, get_settings
from app.core.db import build_session_factory, initialize_database
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import InMemoryRateLimiter
from app.repos.reports_repo import ReportsRepo
from app.repos.evidence_submissions_repo import (
    EvidenceSubmissionsRepo,
    SupabaseEvidenceSubmissionsRepo,
)
from app.repos.protein_annotation_cache_repo import ProteinAnnotationCacheRepo
from app.repos.run_repo import RunRepo
from app.repos.subscriptions_repo import SubscriptionsRepo
from app.repos.source_cache_repo import SourceCacheRepo
from app.repos.supabase_local_model_cache_repo import (
    HybridProteinAnnotationCacheRepo,
    HybridSourceCacheRepo,
    HybridVariantCacheRepo,
    SupabaseProteinAnnotationCacheRepo,
    SupabaseSourceCacheRepo,
    SupabaseVariantCacheRepo,
    build_supabase_local_model_cache_store,
)
from app.repos.users_repo import UsersRepo
from app.repos.variant_cache_repo import VariantCacheRepo
from app.repos.variant_library_repo import (
    SupabaseVariantLibraryRepo,
    VariantLibraryRepo,
)
from app.rules.clinic_rules import ClinicRules
from app.services.auth import AuthService
from app.services.batch import BatchService
from app.services.chat_service import ChatService
from app.services.draft_render import DraftRenderService
from app.services.final_report import FinalReportService
from app.services.evidence_submissions import EvidenceSubmissionService
from app.services.gene_context_snapshot import GeneContextSnapshotService
from app.services.gene_viewer import (
    GeneViewerService,
    HttpGeneViewerSourceClient,
    SourceBackedGeneViewerProvider,
)
from app.services.intake import IntakeService
from app.services.lookup_service import LookupService
from app.services.local_evidence_orchestrator import LocalEvidenceOrchestrator
from app.services.panels import PanelService
from app.services.payments import PaymentsService
from app.services.protein_annotation import ProteinAnnotationService
from app.services.recommendation import RecommendationService
from app.services.report_draft import ReportDraftService
from app.services.run_chat import RunChatService
from app.services.sequence_context import (
    EnsemblVariantSequenceResolver,
    MaterializedHg38SequenceResolver,
    SequenceContextService,
)
from app.services.search_input_resolver import build_runtime_coordinate_resolver
from app.services.source_cache import HeroExampleSourceCacheWarmer
from app.services.variant_library import VariantLibraryService
from app.services.workbench_design import WorkbenchDesignService
from app.services.workflow import WorkflowService
from app.tools.registry import build_tool_registry
from app.tools.report_pdf import ReportPdfTool

logger = get_logger(__name__)


def create_app(settings=None) -> FastAPI:
    settings = settings or get_settings()
    ensure_runtime_dirs(settings)
    configure_logging(settings.debug)
    db_session_factory = build_session_factory(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.coordinate_resolver_asset_materialization_enabled:
            logger.error(
                "Coordinate resolver startup materialization is disabled by backend policy"
            )
            raise RuntimeError(
                "coordinate resolver startup materialization is disabled; "
                "seed and verify runtime assets with an explicit off-peak process"
            )
        initialize_database(db_session_factory)
        logger.info("Eamos backend ready at %s:%s", settings.host, settings.port)
        yield

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    reports_repo = ReportsRepo(db_session_factory)
    evidence_submissions_repo = _build_evidence_submissions_repo(settings, db_session_factory)
    run_repo = RunRepo(db_session_factory)
    subscriptions_repo = SubscriptionsRepo(db_session_factory)
    users_repo = UsersRepo(db_session_factory)
    variant_cache_repo = VariantCacheRepo(db_session_factory)
    variant_library_repo = _build_variant_library_repo(settings, db_session_factory)
    source_cache_repo = SourceCacheRepo(db_session_factory)
    protein_annotation_cache_repo = ProteinAnnotationCacheRepo(db_session_factory)
    supabase_local_model_cache_store = build_supabase_local_model_cache_store(settings)
    if supabase_local_model_cache_store is not None:
        variant_cache_repo = HybridVariantCacheRepo(
            local_repo=variant_cache_repo,
            remote_repo=SupabaseVariantCacheRepo(supabase_local_model_cache_store),
        )
        source_cache_repo = HybridSourceCacheRepo(
            local_repo=source_cache_repo,
            remote_repo=SupabaseSourceCacheRepo(supabase_local_model_cache_store),
        )
        protein_annotation_cache_repo = HybridProteinAnnotationCacheRepo(
            local_repo=protein_annotation_cache_repo,
            remote_repo=SupabaseProteinAnnotationCacheRepo(supabase_local_model_cache_store),
        )
    protein_annotation_service = ProteinAnnotationService(
        settings=settings,
        cache_repo=protein_annotation_cache_repo,
    )
    report_pdf_tool = ReportPdfTool()
    extraction_chain = build_extraction_chain(settings)
    draft_chain = build_draft_chain(settings)
    lookup_chat_chain = build_lookup_chat_chain(settings)
    run_chat_chain = build_run_chat_chain(settings)
    embeddings_model = build_embeddings_model(settings)
    tool_registry = build_tool_registry(
        settings,
        clinical_source_store=supabase_local_model_cache_store,
    )
    sequence_context_resolver = (
        MaterializedHg38SequenceResolver(
            settings,
            supabase_local_model_cache_store,
        )
        if supabase_local_model_cache_store is not None
        else EnsemblVariantSequenceResolver(settings)
    )
    sequence_context_service = SequenceContextService(
        settings=settings,
        resolver=sequence_context_resolver,
    )
    gene_viewer_source_client = HttpGeneViewerSourceClient(
        settings,
        materialization_store=supabase_local_model_cache_store,
    )
    gene_viewer_source_provider = SourceBackedGeneViewerProvider(
        settings=settings,
        source_client=gene_viewer_source_client,
        protein_annotation_service=protein_annotation_service,
    )
    gene_context_snapshot_service = GeneContextSnapshotService(
        settings=settings,
        source_provider=gene_viewer_source_provider if settings.use_real_apis else None,
    )

    panel_service = PanelService()
    runtime_coordinate_resolver = build_runtime_coordinate_resolver(settings)
    local_evidence_orchestrator = LocalEvidenceOrchestrator(
        coordinate_resolver=runtime_coordinate_resolver
    )
    batch_service = BatchService(
        upload_dir=settings.upload_dir,
        panel_service=panel_service,
        coordinate_resolver=runtime_coordinate_resolver,
    )

    app.state.settings = settings
    app.state.db_session_factory = db_session_factory
    app.state.rate_limiter = InMemoryRateLimiter()
    app.state.reports_repo = reports_repo
    app.state.evidence_submissions_repo = evidence_submissions_repo
    app.state.run_repo = run_repo
    app.state.subscriptions_repo = subscriptions_repo
    app.state.users_repo = users_repo
    app.state.variant_cache_repo = variant_cache_repo
    app.state.variant_library_repo = variant_library_repo
    app.state.source_cache_repo = source_cache_repo
    app.state.protein_annotation_cache_repo = protein_annotation_cache_repo
    app.state.supabase_local_model_cache_store = supabase_local_model_cache_store
    app.state.protein_annotation_service = protein_annotation_service
    app.state.gene_viewer_source_client = gene_viewer_source_client
    app.state.gene_viewer_source_provider = gene_viewer_source_provider
    app.state.gene_context_snapshot_service = gene_context_snapshot_service
    app.state.panel_service = panel_service
    app.state.runtime_coordinate_resolver = runtime_coordinate_resolver
    app.state.local_evidence_orchestrator = local_evidence_orchestrator
    app.state.batch_service = batch_service
    app.state.auth_service = AuthService(settings=settings, users_repo=users_repo)
    app.state.evidence_submission_service = EvidenceSubmissionService(
        settings=settings,
        submissions_repo=evidence_submissions_repo,
    )
    app.state.payments_service = PaymentsService(
        settings=settings,
        subscriptions_repo=subscriptions_repo,
    )
    app.state.variant_library_service = VariantLibraryService(variant_library_repo)
    app.state.intake_service = IntakeService(
        settings, reports_repo, report_pdf_tool, extraction_chain
    )
    app.state.workflow_service = WorkflowService(
        reports_repo=reports_repo,
        run_repo=run_repo,
        tool_registry=tool_registry,
        rule_engine=ClinicRules(),
        draft_render_service=DraftRenderService(draft_chain),
    )
    app.state.recommendation_service = RecommendationService(run_repo)
    app.state.report_draft_service = ReportDraftService(run_repo)
    app.state.run_chat_service = RunChatService(
        settings=settings,
        run_repo=run_repo,
        reports_repo=reports_repo,
        answer_chain=run_chat_chain,
        embeddings=embeddings_model,
    )
    app.state.chat_service = ChatService(settings=settings, llm_client=lookup_chat_chain)
    app.state.final_report_service = FinalReportService(settings, run_repo)
    app.state.sequence_context_service = sequence_context_service
    app.state.gene_viewer_service = GeneViewerService(
        settings=settings,
        protein_annotation_service=protein_annotation_service,
        live_provider=gene_viewer_source_provider,
    )
    app.state.workbench_design_service = WorkbenchDesignService(
        settings=settings,
        sequence_context_service=sequence_context_service,
    )
    app.state.lookup_service = LookupService(
        tool_registry=tool_registry,
        rule_engine=ClinicRules(),
        draft_render_service=DraftRenderService(draft_chain),
        variant_cache_repo=variant_cache_repo,
        source_cache_repo=source_cache_repo,
        settings=settings,
        sequence_context_service=sequence_context_service,
        gene_context_snapshot=gene_context_snapshot_service,
    )
    app.state.hero_example_source_cache_warmer = HeroExampleSourceCacheWarmer(
        app.state.lookup_service
    )

    app.include_router(build_api_router())
    return app


def _build_evidence_submissions_repo(settings, db_session_factory):
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseEvidenceSubmissionsRepo(
            supabase_url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
            timeout_seconds=settings.supabase_rest_timeout_seconds,
        )
    return EvidenceSubmissionsRepo(db_session_factory)


def _build_variant_library_repo(settings, db_session_factory):
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseVariantLibraryRepo(
            supabase_url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
            timeout_seconds=settings.supabase_rest_timeout_seconds,
        )
    return VariantLibraryRepo(db_session_factory)
