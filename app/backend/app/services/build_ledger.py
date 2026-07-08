from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from app.core.config import Settings
from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    LOCAL_HG38_2BIT_SOURCE_ID,
    PROTEIN_ANNOTATION_SOURCE_IDS,
    SourceAssetMaterializationStore,
    inspect_hg38_runtime_asset,
    inspect_protein_annotation_assets,
)
from app.data_sources.registry import DataSourceRegistry
from app.data_sources.source_manifest import build_post_reference_source_readiness
from app.services.ai_gateway.retrieval import (
    LITERATURE_EMBEDDING_SOURCE_ID,
    inspect_literature_store,
)
from app.services.clinvar_local import CLINVAR_SOURCE_ID
from app.services.clingen_local import CLINGEN_LOCAL_SOURCE_ID, inspect_clingen_local_store
from app.services.compact_coordinate_index import inspect_compact_coordinate_index
from app.services.dbsnp_local import DBSNP_SOURCE_ID
from app.services.local_evidence_orchestrator import (
    LOCAL_EVIDENCE_RUNTIME_FLOWS,
    LocalEvidenceRuntimeGate,
)
from app.services.local_evidence_runtime_assets import inspect_local_evidence_runtime_assets
from app.services.mavedb_local import inspect_mavedb_local_store
from app.services.predictor_runtime import (
    ALPHAMISSENSE_SOURCE_ID,
    CAPICE_FEATURE_CACHE_SOURCE_ID,
    CAPICE_SOURCE_ID,
    CI_SPLICEAI_SOURCE_ID,
    ESM1B_SOURCE_ID,
    GPN_MSA_SOURCE_ID,
    PANGOLIN_SOURCE_ID,
    PRIMATEAI3D_LAUNCH_GATE,
    PRIMATEAI3D_SOURCE_ID,
    REVEL_LAUNCH_GATE,
    REVEL_SOURCE_ID,
    inspect_alphamissense_runtime_asset,
    inspect_capice_runtime_assets,
    inspect_ci_spliceai_runtime_assets,
    inspect_esm1b_runtime_asset,
    inspect_gpn_msa_runtime_assets,
    inspect_pangolin_runtime_assets,
    inspect_primateai3d_runtime_assets,
    inspect_revel_runtime_assets,
)
from app.services.esm1b_assembly import ESM1B_REGENERATION_REQUIRED_GATE
from app.services.pvs1_nmd import inspect_pvs1_nmd_runtime
from app.services.pubmed_local import inspect_pubmed_local_store
from app.services.repeatmasker_local import REPEATMASKER_SOURCE_ID
from app.services.transcript_model import GENCODE_SOURCE_ID, MANE_SOURCE_ID

LEDGER_SOURCE = "Wiki/syntheses/build-ledger.md"


@dataclass(frozen=True)
class BuildLedgerItem:
    item_id: str
    label: str
    group: str
    source_ids: tuple[str, ...]
    engine: str
    durable_source: str
    runtime_source: str
    render_disk_role: str
    storage_decision: str
    status: str
    runtime_wired: bool
    public_serialization_allowed: bool
    launch_gate: str | None = None
    startup_download_allowed: bool = False
    source_runtime_scan_allowed: bool = False
    blockers: tuple[str, ...] = ()
    wired_surfaces: tuple[str, ...] = ()
    next_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_ids"] = list(self.source_ids)
        payload["blockers"] = list(self.blockers)
        payload["wired_surfaces"] = list(self.wired_surfaces)
        return payload


def build_backend_build_ledger(
    settings: Settings,
    *,
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    materialization_store: SourceAssetMaterializationStore | None = None,
    protein_annotation_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a sanitized readiness ledger for backend source/model wiring.

    This object is intended for public-ish operational health and CLI preflight.
    It deliberately excludes local paths, private Storage object paths/URIs, and
    secret-derived values.
    """

    readiness_by_source = {
        item.source_id: item for item in build_post_reference_source_readiness(registry=registry)
    }
    local_gate = LocalEvidenceRuntimeGate.from_settings(settings)
    hg38_status = _hg38_status(settings, registry)
    predictor_statuses = _predictor_statuses(
        settings,
        registry=registry,
        materialization_store=materialization_store,
    )
    protein_status = _protein_status(
        registry=registry,
        protein_annotation_status=protein_annotation_status,
    )
    coordinate_index_status = _compact_coordinate_index_status(settings)
    clingen_local_status = _clingen_local_status(settings)
    pubmed_local_status = _pubmed_local_status(settings)
    literature_embedding_status = _literature_embedding_status(settings)
    mavedb_status = _mavedb_status(settings)
    local_evidence_runtime_statuses = _local_evidence_runtime_statuses(settings)
    pvs1_nmd_status = _pvs1_nmd_status()

    items = (
        _hg38_item(hg38_status),
        _source_backed_local_item(
            item_id="dbsnp_local_adapter",
            label="dbSNP local allele identity",
            source_id=DBSNP_SOURCE_ID,
            engine="DbSnpLocalStore / pysam TabixFile",
            readiness_by_source=readiness_by_source,
            runtime_source="render_disk_bgzip_tabix_cache",
            render_disk_role="runtime_cache_required",
            storage_decision=(
                "Supabase private Storage is durable; Render disk holds the indexed VCF cache "
                "because pysam needs local bgzip/tabix files."
            ),
            wired_surfaces=("local_evidence_orchestrator",),
            runtime_status=local_evidence_runtime_statuses.get("dbsnp_local_adapter"),
        ),
        _source_backed_local_item(
            item_id="clinvar_local_adapter",
            label="ClinVar local clinical assertion lookup",
            source_id=CLINVAR_SOURCE_ID,
            engine="ClinVarLocalStore / pysam TabixFile",
            readiness_by_source=readiness_by_source,
            runtime_source="render_disk_bgzip_tabix_cache",
            render_disk_role="runtime_cache_required",
            storage_decision=(
                "Supabase private Storage is durable; Render disk holds the indexed VCF cache "
                "for local ClinVar reads."
            ),
            wired_surfaces=("local_evidence_orchestrator", "acmg_classifier"),
            runtime_status=local_evidence_runtime_statuses.get("clinvar_local_adapter"),
        ),
        _source_backed_local_item(
            item_id="repeatmasker_local_adapter",
            label="RepeatMasker local interval lookup",
            source_id=REPEATMASKER_SOURCE_ID,
            engine="RepeatMaskerLocalStore",
            readiness_by_source=readiness_by_source,
            runtime_source="render_disk_compact_interval_index",
            render_disk_role="runtime_cache_required",
            storage_decision=(
                "Supabase private Storage keeps the release artifact; Render disk keeps a "
                "compact runtime interval index, not source-file scans."
            ),
            wired_surfaces=("local_evidence_orchestrator",),
            runtime_status=local_evidence_runtime_statuses.get("repeatmasker_local_adapter"),
        ),
        _source_backed_local_item(
            item_id="phylop_conservation_reader",
            label="phyloP conservation reader",
            source_id="ucsc_phylop100way_hg38",
            engine="PyBigWigConservationReader",
            readiness_by_source=readiness_by_source,
            runtime_source="render_disk_bigwig_cache",
            render_disk_role="runtime_cache_required",
            storage_decision=(
                "Supabase private Storage is durable; Render disk holds the bigWig file "
                "because the reader expects filesystem/range access."
            ),
            wired_surfaces=("lookup", "report"),
            runtime_status=local_evidence_runtime_statuses.get("phylop_conservation_reader"),
        ),
        _coordinate_index_item(readiness_by_source, coordinate_index_status),
        _local_evidence_gate_item(local_gate),
        _clinical_source_tables_item(readiness_by_source),
        _gene_view_item(hg38_status, coordinate_index_status, protein_status),
        _protein_pfam_item(protein_status),
        _predictor_item(
            item_id="alphamissense",
            label="AlphaMissense hg38 scores",
            source_id=ALPHAMISSENSE_SOURCE_ID,
            status=predictor_statuses["alphamissense"],
            storage_decision=(
                "Supabase private Storage is durable; Render disk holds the bgzip/tabix "
                "runtime cache. The computational evidence path serializes local rows when "
                "the artifact is materialized; launch filtering can use source metadata."
            ),
            public_serialization_allowed=True,
        ),
        _predictor_item(
            item_id="esm1b",
            label="ESM1b assembled hg38 scores",
            source_id=ESM1B_SOURCE_ID,
            status=predictor_statuses["esm1b"],
            storage_decision=(
                "Supabase private Storage is durable after offline MANE assembly; Render disk "
                "holds only the indexed runtime artifact. License-gate status is preserved as "
                "metadata for launch filtering, not as a backend integration blocker."
            ),
            public_serialization_allowed=True,
            launch_gate=_esm1b_launch_gate(
                settings,
                registry=registry,
                materialization_store=materialization_store,
            ),
        ),
        BuildLedgerItem(
            item_id="gpn_msa",
            label="GPN-MSA precomputed scores",
            group="predictor",
            source_ids=(GPN_MSA_SOURCE_ID,),
            engine="pysam TabixFile over HTTP byte-range",
            durable_source="remote_hf_or_signed_url_with_supabase_metadata",
            runtime_source="remote_http_byte_range",
            render_disk_role="not_required",
            storage_decision=(
                "Ledger calls for zero local cache first; keep remote byte-range reads until "
                "a measured runtime need justifies materialization."
            ),
            status=predictor_statuses["gpn_msa"],
            runtime_wired=False,
            public_serialization_allowed=False,
            blockers=("byte_range_reader_proof", "terms_review"),
            wired_surfaces=("lookup", "report"),
            next_action="Backfill source metadata and prove HTTP range reader semantics.",
        ),
        BuildLedgerItem(
            item_id="pangolin",
            label="Pangolin splice-effect scores",
            group="predictor",
            source_ids=(PANGOLIN_SOURCE_ID,),
            engine="planned local model or coordinate-keyed score cache",
            durable_source="source_decision_required",
            runtime_source="not_wired",
            render_disk_role="pending_design",
            storage_decision=(
                "Frontend exposes Pangolin as a free splice-predictor slot, but backend "
                "source, terms, and runtime shape still need review before any model/cache "
                "is staged."
            ),
            status=predictor_statuses["pangolin"],
            runtime_wired=False,
            public_serialization_allowed=False,
            blockers=(
                "source_terms_review",
                "runtime_design",
                "score_cache_or_model_materialization",
            ),
            wired_surfaces=("lookup", "report"),
            next_action="Choose the Pangolin source path, record terms, then add a fail-closed adapter.",
        ),
        BuildLedgerItem(
            item_id="ci_spliceai",
            label="CI-SpliceAI compute lane",
            group="predictor",
            source_ids=(CI_SPLICEAI_SOURCE_ID, LOCAL_HG38_2BIT_SOURCE_ID),
            engine="TensorFlow/Keras on-demand compute with tabix score cache",
            durable_source="supabase_private_storage",
            runtime_source="render_disk_model_reference_and_score_cache",
            render_disk_role="runtime_cache_required",
            storage_decision=(
                "Model, reference, and cache need local files. Backend serialization is allowed "
                "for Steven/admin use; launch filtering can use source metadata."
            ),
            status=predictor_statuses["ci_spliceai"],
            runtime_wired=True,
            public_serialization_allowed=True,
            launch_gate="ci_spliceai_launch_filter_metadata",
            blockers=(
                ()
                if predictor_statuses["ci_spliceai"] == "ready"
                else ("model_reference_materialization", "score_cache_materialization")
            ),
            wired_surfaces=("lookup", "report", "acmg_calibration"),
            next_action="Materialize model/reference/score cache and verify runtime resource envelope.",
        ),
        BuildLedgerItem(
            item_id="nmdetective_pvs1",
            label="NMDetective-B and PVS1 decision support",
            group="classifier",
            source_ids=(pvs1_nmd_status["source_id"],),
            engine="pure Python Abou-Tayoun-style PVS1/NMD decision tree",
            durable_source="repo_code_or_supabase_postgres_small_overrides",
            runtime_source="repo_code_with_optional_small_table",
            render_disk_role="not_required",
            storage_decision="The rule table is tiny; Render disk is not justified.",
            status=pvs1_nmd_status["status"],
            runtime_wired=bool(pvs1_nmd_status["runtime_wired"]),
            public_serialization_allowed=bool(pvs1_nmd_status["public_serialization_allowed"]),
            wired_surfaces=("acmg_classifier", "report"),
            next_action="Add full source import only if clean-room rules require extra tables.",
        ),
        BuildLedgerItem(
            item_id="capice",
            label="CAPICE",
            group="predictor",
            source_ids=(CAPICE_SOURCE_ID, CAPICE_FEATURE_CACHE_SOURCE_ID),
            engine="XGBoost over VEP-style features",
            durable_source="supabase_private_storage",
            runtime_source="render_disk_model_and_feature_cache",
            render_disk_role="runtime_cache_required",
            storage_decision=(
                "Model and SpliceAI-derived feature cache are backend runtime assets. "
                "Commercialization filtering is launch metadata, not a backend integration block."
            ),
            status=predictor_statuses["capice"],
            runtime_wired=True,
            public_serialization_allowed=True,
            launch_gate="capice_launch_filter_metadata",
            blockers=(
                ()
                if predictor_statuses["capice"] == "ready"
                else ("capice_model_materialization", "spliceai_feature_cache_materialization")
            ),
            wired_surfaces=("lookup", "report", "acmg_calibration"),
            next_action="Materialize CAPICE model and feature cache; connect scorer once artifacts exist.",
        ),
        BuildLedgerItem(
            item_id="revel",
            label="REVEL score cache",
            group="predictor",
            source_ids=(REVEL_SOURCE_ID,),
            engine="bgzip/tabix local predictor reader",
            durable_source="supabase_private_storage",
            runtime_source="render_disk_bgzip_tabix_cache",
            render_disk_role="runtime_cache_required",
            storage_decision=(
                "REVEL is wired as a backend/admin coordinate-keyed cache. License and launch "
                "metadata stay on serialized rows for downstream filtering."
            ),
            status=predictor_statuses["revel"],
            runtime_wired=True,
            public_serialization_allowed=True,
            launch_gate=REVEL_LAUNCH_GATE,
            blockers=(
                () if predictor_statuses["revel"] == "ready" else ("score_cache_materialization",)
            ),
            wired_surfaces=("lookup", "report", "acmg_calibration"),
            next_action=(
                None
                if predictor_statuses["revel"] == "ready"
                else "Materialize REVEL score cache with checksum manifest through explicit process."
            ),
        ),
        BuildLedgerItem(
            item_id="primateai3d",
            label="PrimateAI-3D score cache",
            group="predictor",
            source_ids=(PRIMATEAI3D_SOURCE_ID,),
            engine="bgzip/tabix local predictor reader",
            durable_source="supabase_private_storage",
            runtime_source="render_disk_bgzip_tabix_cache",
            render_disk_role="runtime_cache_required",
            storage_decision=(
                "PrimateAI-3D is wired as a backend/admin coordinate-keyed cache. License and "
                "launch metadata stay on serialized rows for downstream filtering."
            ),
            status=predictor_statuses["primateai3d"],
            runtime_wired=True,
            public_serialization_allowed=True,
            launch_gate=PRIMATEAI3D_LAUNCH_GATE,
            blockers=(
                ()
                if predictor_statuses["primateai3d"] == "ready"
                else ("score_cache_materialization",)
            ),
            wired_surfaces=("lookup", "report", "acmg_calibration"),
            next_action=(
                None
                if predictor_statuses["primateai3d"] == "ready"
                else "Materialize PrimateAI-3D score cache with checksum manifest through explicit process."
            ),
        ),
        BuildLedgerItem(
            item_id="mavedb",
            label="MaveDB functional evidence",
            group="functional_evidence",
            source_ids=("mavedb_cc0",),
            engine="URN/HGVS/genomic ETL with Postgres or tabix lookup",
            durable_source="supabase_postgres_or_private_storage_tabix",
            runtime_source="supabase_postgres_or_render_disk_tabix",
            render_disk_role="runtime_cache_optional",
            storage_decision=(
                "CC0 records fit Supabase Postgres first; add Render tabix only for measured "
                "lookup pressure."
            ),
            status=mavedb_status,
            runtime_wired=True,
            public_serialization_allowed=mavedb_status == "ready",
            blockers=() if mavedb_status == "ready" else ("cc0_import_materialization",),
            wired_surfaces=("lookup", "report"),
            next_action=(
                None
                if mavedb_status == "ready"
                else "Materialize CC0 import and validate public field policy."
            ),
        ),
        BuildLedgerItem(
            item_id="acmg_classifier",
            label="EAMOS ACMG source-aggregation classifier",
            group="classifier",
            source_ids=("clinvar", "clingen", "pubmed"),
            engine="clinical_consensus.py and computational_calibration.py",
            durable_source="repo_code_plus_optional_supabase_postgres_vcep_overrides",
            runtime_source="repo_code",
            render_disk_role="not_required",
            storage_decision="The classifier is pure code with tiny optional override tables.",
            status="pure_code_available",
            runtime_wired=True,
            public_serialization_allowed=True,
            wired_surfaces=("lookup", "report", "variant_library"),
            next_action="Keep local predictor serialization and calibration covered by tests.",
        ),
        BuildLedgerItem(
            item_id="clingen_local_adapter",
            label="ClinGen eRepo VCEP and CSpec local materialization",
            group="clinical_tables",
            source_ids=(CLINGEN_LOCAL_SOURCE_ID, "clingen_erepo", "clingen_cspec"),
            engine="ClinGenLocalStore / SQLite source asset",
            durable_source="operator_public_snapshot_jsonl",
            runtime_source="render_disk_sqlite_cache",
            render_disk_role="runtime_cache_required",
            storage_decision=(
                "Full public eRepo/CSpec snapshots are fetched by explicit operator CLI, "
                "materialized into SQLite, and read local-first by ClingenTool. Runtime "
                "startup and lookup requests never bulk-download ClinGen data."
            ),
            status=clingen_local_status,
            runtime_wired=True,
            public_serialization_allowed=True,
            launch_gate=(
                None if clingen_local_status == "ready" else "clingen_local_materialization"
            ),
            blockers=() if clingen_local_status == "ready" else ("clingen_local_materialization",),
            wired_surfaces=(
                "lookup",
                "clingen_vcep_section",
                "clinical_consensus",
                "functional_evidence",
            ),
            next_action=(
                None
                if clingen_local_status == "ready"
                else "Fetch ClinGen source JSONL, materialize SQLite, and pass preflight before enabling."
            ),
        ),
        BuildLedgerItem(
            item_id="literature_engine",
            label="Literature engine and PubMed local",
            group="literature",
            source_ids=("pubmed", "litvar2", "pubtator3", "pmc_oa", "medcpt_pgvector"),
            engine=(
                "EP-VLEx over PubMed local SQLite, operator PubTator/LitVar edge JSONL, "
                "PMC OA policy overlays later, and live E-utilities fallback"
            ),
            durable_source="supabase_private_storage_and_postgres_after_corpus_sizing",
            runtime_source="render_disk_pubmed_sqlite_now_supabase_corpus_planned",
            render_disk_role="runtime_cache_optional",
            storage_decision=(
                "PubMed local SQLite is the proof harness. The production corpus path is "
                "private Supabase Storage for approved source packages plus "
                "private Postgres search tables after explicit sizing approval. PubTator "
                "and LitVar edge JSONL are operator-fed inputs; API calls remain fallback "
                "or refresh."
            ),
            status=pubmed_local_status,
            runtime_wired=True,
            public_serialization_allowed=True,
            blockers=() if pubmed_local_status == "ready" else ("pubmed_local_materialization",),
            wired_surfaces=("lookup", "report", "search"),
            next_action=(
                None
                if pubmed_local_status == "ready"
                else "Run explicit PubMed local materialization/preflight before enabling local-first lookup."
            ),
        ),
        BuildLedgerItem(
            item_id="literature_rag_embeddings",
            label="Literature RAG embedding store",
            group="literature",
            source_ids=(LITERATURE_EMBEDDING_SOURCE_ID, "pubmed"),
            engine="LiteratureEmbeddingStore over gateway-materialized embeddings",
            durable_source="supabase_private_storage",
            runtime_source="render_disk_literature_embedding_sqlite",
            render_disk_role="runtime_cache_required",
            storage_decision=(
                "The embedding SQLite is built offline from PubMed local through the AI Gateway, "
                "uploaded to private Supabase Storage as the durable artifact, and synced to "
                "Render disk for runtime RAG. It is never built or downloaded at startup."
            ),
            status=literature_embedding_status,
            runtime_wired=True,
            public_serialization_allowed=True,
            launch_gate=(
                None if literature_embedding_status == "ready" else "literature_rag_materialization"
            ),
            blockers=(
                ()
                if literature_embedding_status == "ready"
                else ("literature_embedding_materialization",)
            ),
            wired_surfaces=("variant_chat",),
            next_action=(
                None
                if literature_embedding_status == "ready"
                else (
                    "Materialize PubMed local, embed license-permitted gene-scoped rows offline, "
                    "upload the SQLite artifact to private Storage, sync to Render disk, and pass preflight."
                )
            ),
        ),
        BuildLedgerItem(
            item_id="ai_gateway",
            label="AI gateway",
            group="ai",
            source_ids=("groq_llama_3_3_70b", "deepinfra_fallback"),
            engine="Render broker with de-ID, RAG, SSE, and provider fallback",
            durable_source="api_provider_config_and_supabase_metadata",
            runtime_source="render_service_process",
            render_disk_role="not_required",
            storage_decision="No source asset belongs on disk; keep provider config out of health.",
            status="gateway_planned",
            runtime_wired=False,
            public_serialization_allowed=False,
            blockers=("provider_broker_wiring", "deid_audit", "phi_log_policy"),
            wired_surfaces=("lookup_chat", "run_chat", "drafts"),
            next_action="Wire broker after PHI/de-ID and provider fallback contracts are reviewed.",
        ),
        BuildLedgerItem(
            item_id="workbench_local_tools",
            label="Sequence, primer, CRISPR, and alignment workbench",
            group="workbench",
            source_ids=(LOCAL_HG38_2BIT_SOURCE_ID,),
            engine="Primer3-py, UCSC isPcr, CRISPR Hsu/MIT, Biopython, local hg38",
            durable_source="repo_code_plus_supabase_private_storage_for_reference",
            runtime_source="repo_code_and_render_disk_hg38_cache",
            render_disk_role="runtime_cache_required_for_full_reference_reads",
            storage_decision=(
                "Tooling is local code, but full-reference operations depend on the same "
                "Render disk hg38 cache."
            ),
            status="code_available_reference_gated",
            runtime_wired=True,
            public_serialization_allowed=True,
            blockers=() if hg38_status == "ready" else ("hg38_runtime_asset_ready",),
            wired_surfaces=("primer_design", "crispr_design", "alignment", "viewer"),
            next_action=(
                None
                if hg38_status == "ready"
                else "Seed and verify hg38 runtime cache before enabling full-reference workbench paths."
            ),
        ),
    )

    return _ledger_payload(items)


def _ledger_payload(items: Iterable[BuildLedgerItem]) -> dict[str, Any]:
    rows = tuple(items)
    status_counts = Counter(item.status for item in rows)
    render_disk_counts = Counter(item.render_disk_role for item in rows)
    durable_source_counts = Counter(item.durable_source for item in rows)
    return {
        "mode": "backend_build_ledger",
        "source": LEDGER_SOURCE,
        "startup_downloads_allowed": False,
        "gff_runtime_scans_allowed": False,
        "supabase_private_storage_is_durable_source": True,
        "render_disk_is_runtime_cache_only": True,
        "items": [item.to_dict() for item in rows],
        "status_counts": dict(sorted(status_counts.items())),
        "storage_summary": {
            "render_disk_roles": dict(sorted(render_disk_counts.items())),
            "durable_sources": dict(sorted(durable_source_counts.items())),
        },
    }


def _hg38_status(settings: Settings, registry: DataSourceRegistry) -> str:
    try:
        inspection = inspect_hg38_runtime_asset(
            settings,
            registry=registry,
            verify_checksum=False,
        )
    except Exception:
        return "runtime_asset_probe_failed"
    return inspection.status.value


def _predictor_statuses(
    settings: Settings,
    *,
    registry: DataSourceRegistry,
    materialization_store: SourceAssetMaterializationStore | None,
) -> dict[str, str]:
    return {
        "alphamissense": _safe_predictor_status(
            inspect_alphamissense_runtime_asset,
            settings,
            registry=registry,
            materialization_store=materialization_store,
        ),
        "esm1b": _safe_predictor_status(
            inspect_esm1b_runtime_asset,
            settings,
            registry=registry,
            materialization_store=materialization_store,
        ),
        "ci_spliceai": _safe_admin_predictor_status(
            inspect_ci_spliceai_runtime_assets,
            settings,
        ),
        "gpn_msa": _safe_admin_predictor_status(
            inspect_gpn_msa_runtime_assets,
            settings,
        ),
        "pangolin": _safe_admin_predictor_status(
            inspect_pangolin_runtime_assets,
            settings,
        ),
        "capice": _safe_admin_predictor_status(
            inspect_capice_runtime_assets,
            settings,
        ),
        "revel": _safe_admin_predictor_status(
            inspect_revel_runtime_assets,
            settings,
        ),
        "primateai3d": _safe_admin_predictor_status(
            inspect_primateai3d_runtime_assets,
            settings,
        ),
    }


def _safe_predictor_status(inspector, settings: Settings, **kwargs: Any) -> str:
    try:
        return inspector(settings, verify_checksum=False, **kwargs).status.value
    except Exception:
        return "runtime_asset_probe_failed"


def _safe_admin_predictor_status(inspector, settings: Settings) -> str:
    try:
        return str(inspector(settings).status)
    except Exception:
        return "runtime_asset_probe_failed"


def _esm1b_launch_gate(
    settings: Settings,
    *,
    registry: DataSourceRegistry,
    materialization_store: SourceAssetMaterializationStore | None,
) -> str | None:
    try:
        return inspect_esm1b_runtime_asset(
            settings,
            registry=registry,
            materialization_store=materialization_store,
            verify_checksum=False,
        ).launch_gate
    except Exception:
        return ESM1B_REGENERATION_REQUIRED_GATE


def _protein_status(
    *,
    registry: DataSourceRegistry,
    protein_annotation_status: dict[str, Any] | None,
) -> str:
    if protein_annotation_status is not None:
        status = protein_annotation_status.get("status")
        if isinstance(status, str) and status:
            return status
    try:
        inspections = inspect_protein_annotation_assets(
            registry=registry,
            verify_checksums=False,
        )
    except Exception:
        return "asset_probe_failed"
    if all(item.ready for item in inspections):
        return "ready"
    if any(item.present for item in inspections):
        return "assets_partially_present"
    return "missing"


def _pvs1_nmd_status() -> dict[str, object]:
    try:
        inspection = inspect_pvs1_nmd_runtime()
    except Exception:
        return {
            "source_id": "nmdetective_b_pvs1",
            "status": "runtime_probe_failed",
            "runtime_wired": False,
            "public_serialization_allowed": False,
        }
    return {
        "source_id": inspection.source_id,
        "status": inspection.status,
        "runtime_wired": inspection.runtime_wired,
        "public_serialization_allowed": inspection.public_serialization_allowed,
    }


def _local_evidence_runtime_statuses(settings: Settings) -> dict[str, str]:
    try:
        inspection = inspect_local_evidence_runtime_assets(settings)
    except Exception:
        return {}
    return {
        str(source["item_id"]): str(source["status"])
        for source in inspection.get("sources", [])
        if isinstance(source, dict) and source.get("item_id") and source.get("status")
    }


def _hg38_item(status: str) -> BuildLedgerItem:
    return BuildLedgerItem(
        item_id="hg38_2bit",
        label="hg38.2bit reference genome",
        group="foundation",
        source_ids=(LOCAL_HG38_2BIT_SOURCE_ID,),
        engine="TwoBitReferenceGenomeStore / twobitreader",
        durable_source="supabase_private_storage",
        runtime_source="render_disk_local_cache",
        render_disk_role="runtime_cache_required",
        storage_decision=(
            "Supabase private Storage is durable; Render disk is the runtime local cache "
            "because twobit readers require a filesystem path."
        ),
        status=status,
        runtime_wired=True,
        public_serialization_allowed=False,
        blockers=() if status == "ready" else ("seed_verified_render_disk_cache",),
        wired_surfaces=("lookup", "search", "report", "gene_viewer", "workbench"),
        next_action=None if status == "ready" else "Seed and verify hg38.2bit on Render disk.",
    )


def _source_backed_local_item(
    *,
    item_id: str,
    label: str,
    source_id: str,
    engine: str,
    readiness_by_source: dict[str, Any],
    runtime_source: str,
    render_disk_role: str,
    storage_decision: str,
    wired_surfaces: tuple[str, ...],
    runtime_status: str | None = None,
) -> BuildLedgerItem:
    readiness = readiness_by_source.get(source_id)
    readiness_status = _readiness_status(readiness)
    status = "ready" if runtime_status == "ready" else readiness_status
    return BuildLedgerItem(
        item_id=item_id,
        label=label,
        group="foundation",
        source_ids=(source_id,),
        engine=engine,
        durable_source="supabase_private_storage",
        runtime_source=runtime_source,
        render_disk_role=render_disk_role,
        storage_decision=storage_decision,
        status=status,
        runtime_wired=True,
        public_serialization_allowed=False,
        blockers=_source_backed_local_blockers(
            readiness_status=readiness_status,
            runtime_status=runtime_status,
        ),
        wired_surfaces=wired_surfaces,
        next_action=(
            None
            if status == "ready"
            else "Seed/materialize the indexed runtime artifact through an explicit process."
        ),
    )


def _source_backed_local_blockers(
    *,
    readiness_status: str,
    runtime_status: str | None,
) -> tuple[str, ...]:
    if runtime_status == "ready":
        return ()
    if readiness_status != "source_ready_for_materialization":
        return ("source_readiness",)
    return ("seed_verified_render_disk_cache",)


def _compact_coordinate_index_status(settings: Settings) -> str:
    try:
        return inspect_compact_coordinate_index(
            settings,
            verify_checksum=False,
            load_records=False,
        ).status
    except Exception:
        return "runtime_asset_probe_failed"


def _pubmed_local_status(settings: Settings) -> str:
    try:
        inspection = inspect_pubmed_local_store(settings, verify_checksum=False)
    except Exception:
        return "runtime_asset_probe_failed"
    if inspection.ready:
        return "ready"
    if not settings.pubmed_local_enabled:
        return "local_adapter_disabled"
    return inspection.status


def _clingen_local_status(settings: Settings) -> str:
    try:
        inspection = inspect_clingen_local_store(settings, verify_checksum=False)
    except Exception:
        return "runtime_asset_probe_failed"
    if inspection.ready:
        return "ready"
    if not settings.clingen_local_enabled:
        return "local_adapter_disabled"
    return inspection.status


def _literature_embedding_status(settings: Settings) -> str:
    try:
        inspection = inspect_literature_store(settings)
    except Exception:
        return "runtime_asset_probe_failed"
    if inspection.ready:
        return "ready"
    if not settings.rag_enabled:
        return "rag_disabled"
    return inspection.status


def _mavedb_status(settings: Settings) -> str:
    try:
        inspection = inspect_mavedb_local_store(settings, verify_checksum=False)
    except Exception:
        return "runtime_asset_probe_failed"
    return inspection.status


def _coordinate_index_item(
    readiness_by_source: dict[str, Any],
    coordinate_index_status: str,
) -> BuildLedgerItem:
    sources = (MANE_SOURCE_ID, "ncbi_refseq_grch38_p14", GENCODE_SOURCE_ID)
    missing = [
        source_id
        for source_id in sources
        if _readiness_status(readiness_by_source.get(source_id))
        != "source_ready_for_materialization"
    ]
    return BuildLedgerItem(
        item_id="coordinate_compact_index",
        label="Compact coordinate and transcript projection index",
        group="coordinate",
        source_ids=sources,
        engine="offline GFF parser to immutable runtime index",
        durable_source="supabase_private_storage_for_offline_gff_inputs",
        runtime_source="render_disk_compact_immutable_index",
        render_disk_role="runtime_cache_required",
        storage_decision=(
            "MANE/RefSeq/Gencode GFF stays in private Storage for offline builds; "
            "runtime uses a compact immutable index on Render disk."
        ),
        status=coordinate_index_status if not missing else "source_readiness_pending",
        runtime_wired=True,
        public_serialization_allowed=False,
        blockers=(
            tuple(missing)
            if missing
            else (() if coordinate_index_status == "ready" else ("compact_index_materialization",))
        ),
        wired_surfaces=("lookup", "search", "report", "gene_viewer", "batch", "local_evidence"),
        next_action=(
            None
            if coordinate_index_status == "ready" and not missing
            else "Materialize and verify the checksum-pinned compact index."
        ),
    )


def _local_evidence_gate_item(gate: LocalEvidenceRuntimeGate) -> BuildLedgerItem:
    flow_decisions = [gate.for_flow(flow) for flow in LOCAL_EVIDENCE_RUNTIME_FLOWS]
    enabled_flows = tuple(decision.flow for decision in flow_decisions if decision.enabled)
    disabled_reasons = tuple(
        sorted({decision.reason for decision in flow_decisions if not decision.enabled})
    )
    blockers = () if enabled_flows else disabled_reasons
    return BuildLedgerItem(
        item_id="local_evidence_orchestrator",
        label="Local evidence orchestrator gate",
        group="foundation",
        source_ids=(DBSNP_SOURCE_ID, CLINVAR_SOURCE_ID, MANE_SOURCE_ID, GENCODE_SOURCE_ID),
        engine="LocalEvidenceOrchestrator",
        durable_source="mixed_supabase_private_storage_and_repo_code",
        runtime_source="render_disk_indexes_plus_repo_code",
        render_disk_role="runtime_cache_required",
        storage_decision=(
            "The orchestrator composes local indexed assets; enabling it requires the whole "
            "asset batch to be seeded, not a single-adapter toggle."
        ),
        status="enabled" if enabled_flows else "disabled",
        runtime_wired=True,
        public_serialization_allowed=False,
        blockers=blockers,
        wired_surfaces=enabled_flows or LOCAL_EVIDENCE_RUNTIME_FLOWS,
        next_action=(
            None
            if enabled_flows
            else "Enable only after the horizontal indexed-asset batch is verified."
        ),
    )


def _clinical_source_tables_item(readiness_by_source: dict[str, Any]) -> BuildLedgerItem:
    source_ids = (
        "mondo_disease_ontology",
        "human_phenotype_ontology",
        "clingen_gene_validity",
        "gencc_download",
    )
    statuses = {_readiness_status(readiness_by_source.get(source_id)) for source_id in source_ids}
    ready = statuses == {"source_ready_for_materialization"}
    return BuildLedgerItem(
        item_id="clinical_source_tables",
        label="MONDO, HPO, ClinGen, and GenCC tables",
        group="clinical_tables",
        source_ids=source_ids,
        engine="clinical_source_tables.py import bundle",
        durable_source="supabase_postgres",
        runtime_source="supabase_postgres",
        render_disk_role="not_required",
        storage_decision=(
            "These are small relational source tables. Supabase Postgres is sufficient; "
            "Render disk is not justified."
        ),
        status="import_ready" if ready else "source_readiness_pending",
        runtime_wired=True,
        public_serialization_allowed=True,
        blockers=() if ready else tuple(sorted(statuses)),
        wired_surfaces=("lookup", "gene_disease_tool", "report"),
        next_action="Import release-pinned tables into private Supabase Postgres.",
    )


def _gene_view_item(
    hg38_status: str,
    coordinate_index_status: str,
    protein_status: str,
) -> BuildLedgerItem:
    blockers = []
    if hg38_status != "ready":
        blockers.append("hg38_runtime_asset_ready")
    if coordinate_index_status != "ready":
        blockers.append("compact_coordinate_index")
    if protein_status not in {"available", "ready"}:
        blockers.append("protein_runtime_ready")
    return BuildLedgerItem(
        item_id="gene_view",
        label="Gene View backend source provider",
        group="viewer",
        source_ids=(
            LOCAL_HG38_2BIT_SOURCE_ID,
            MANE_SOURCE_ID,
            GENCODE_SOURCE_ID,
            *PROTEIN_ANNOTATION_SOURCE_IDS,
        ),
        engine="GeneViewerService / SourceBackedGeneViewerProvider",
        durable_source="mixed_supabase_private_storage_and_supabase_postgres",
        runtime_source="render_disk_reference_transcript_and_pfam_caches",
        render_disk_role="runtime_cache_required",
        storage_decision=(
            "Gene View consumes hg38, compact transcript indexes, and optional protein assets; "
            "only the filesystem-bound readers belong on Render disk."
        ),
        status="runtime_partial" if blockers else "ready",
        runtime_wired=True,
        public_serialization_allowed=True,
        blockers=tuple(dict.fromkeys(blockers)),
        wired_surfaces=("gene_viewer", "lookup_sections"),
        next_action=(
            None
            if not blockers
            else "Point Gene View at the compact coordinate index and verified protein runtime."
        ),
    )


def _protein_pfam_item(status: str) -> BuildLedgerItem:
    ready = status in {"available", "ready"}
    return BuildLedgerItem(
        item_id="protein_pfam",
        label="Protein View Pfam/HMMER runtime",
        group="protein",
        source_ids=PROTEIN_ANNOTATION_SOURCE_IDS,
        engine="LocalHmmerRunner / ProteinAnnotationService",
        durable_source="supabase_private_storage",
        runtime_source="render_disk_hmmer_indexes",
        render_disk_role="runtime_cache_required",
        storage_decision=(
            "Supabase private Storage keeps release bundles; Render disk holds extracted Pfam "
            "HMM and hmmpress indexes required by HMMER."
        ),
        status=status,
        runtime_wired=True,
        public_serialization_allowed=True,
        blockers=() if ready else ("pfam_hmm_and_hmmpress_indexes_ready",),
        wired_surfaces=("protein_annotation", "gene_viewer"),
        next_action=None if ready else "Seed Pfam/HMMER assets and run hmmpress off-startup.",
    )


def _predictor_item(
    *,
    item_id: str,
    label: str,
    source_id: str,
    status: str,
    storage_decision: str,
    public_serialization_allowed: bool,
    launch_gate: str | None = None,
) -> BuildLedgerItem:
    return BuildLedgerItem(
        item_id=item_id,
        label=label,
        group="predictor",
        source_ids=(source_id,),
        engine="bgzip/tabix local predictor reader",
        durable_source="supabase_private_storage",
        runtime_source="render_disk_bgzip_tabix_cache",
        render_disk_role="runtime_cache_required",
        storage_decision=storage_decision,
        status=status,
        runtime_wired=True,
        public_serialization_allowed=public_serialization_allowed,
        launch_gate=launch_gate,
        blockers=() if status == "ready" else ("indexed_artifact_materialization",),
        wired_surfaces=("lookup", "report", "acmg_calibration"),
        next_action=(
            None
            if status == "ready"
            else "Materialize bgzip/tabix artifact with checksum manifest through explicit process."
        ),
    )


def _readiness_status(readiness: Any | None) -> str:
    if readiness is None:
        return "source_not_registered"
    if readiness.ready_for_download_or_import:
        return "source_ready_for_materialization"
    return "source_readiness_pending"
