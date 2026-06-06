from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.data_sources.registry import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry

DOCX_BLUEPRINT_NAME = "Data and sources 1.docx"

DOCX_BLUEPRINT_TIERS: tuple[dict[str, Any], ...] = (
    {
        "tier": "tier_1_object_storage_assets",
        "docx_items": (
            "hg38.2bit",
            "GCF_000001405.40.vcf.gz plus index",
            "clinvar.vcf.gz plus index",
            "rmsk.bb",
            "hg38.phyloP100way.bw",
        ),
        "current_state": "metadata_recorded_downloads_not_approved",
    },
    {
        "tier": "tier_2_repo_assets",
        "docx_items": (
            "MANE.GRCh38.v1.4.select_ensembl.gtf.gz",
            "gencode.v45.annotation.gtf.gz",
            "InterVar pipeline configs",
        ),
        "current_state": "verified_manifest_or_license_blocked",
    },
    {
        "tier": "tier_2_5_python_engines",
        "docx_items": ("primer3-py", "biopython", "pysam", "twobitreader", "pybigwig"),
        "current_state": "dependency_policy_recorded_no_new_install",
    },
    {
        "tier": "tier_3_supabase_postgres_tables",
        "docx_items": ("Mondo", "HPO annotations", "ClinGen gene validity", "GenCC"),
        "current_state": "metadata_recorded_imports_not_approved",
    },
    {
        "tier": "tier_4_live_apis",
        "docx_items": ("MyVariant.info gnomAD", "MyVariant.info restricted predictors"),
        "current_state": "gnomad_policy_preserved_predictors_admin_wired_launch_gated",
    },
)

DOCX_RECONCILIATION: tuple[dict[str, str], ...] = (
    {
        "item": "Supabase Storage, object storage, startup downloads, and imports",
        "state": "approval_required",
        "current_policy": "Not performed by this preflight and not enabled by the current plan.",
    },
    {
        "item": "dbSNP filename and size",
        "state": "corrected_in_registry",
        "current_policy": "Use NCBI GCF_000001405.40.gz plus .tbi identity from the official listing.",
    },
    {
        "item": "MANE Select file",
        "state": "corrected_in_registry",
        "current_policy": "Use MANE.GRCh38.v1.4.ensembl_genomic.gtf.gz and extract MANE Select rows by tag.",
    },
    {
        "item": "RepeatMasker bigBed",
        "state": "source_table_first",
        "current_policy": "Use official rmsk.txt.gz first; derive rmsk.bb only after an approved conversion proof.",
    },
    {
        "item": "HPO hp.gpad draft path",
        "state": "superseded",
        "current_policy": "Use official HPO annotation tables recorded in the registry.",
    },
    {
        "item": "InterVar, ANNOVAR, and OMIM production use",
        "state": "blocked",
        "current_policy": "Commercial/license review is required before production use.",
    },
    {
        "item": "SpliceAI, CADD, REVEL, PrimateAI-3D, and restricted dbNSFP fields",
        "state": "launch_gated",
        "current_policy": (
            "Backend/admin runtime serialization is allowed; public launch filtering remains "
            "required until commercial terms are finalized."
        ),
    },
)

_STATUS_NARRATIVE = "narrative_or_table_structure"
_STATUS_COVERED = "covered_by_fixture_or_tooling"
_STATUS_APPROVAL = "approval_required_before_runtime"
_STATUS_LICENSE_BLOCKED = "commercial_license_blocked"
_STATUS_POLICY_LOCKED = "covered_by_policy_lock"
_STATUS_CORRECTED = "corrected_by_registry_policy"
_STATUS_LOCAL_IMPLEMENTATION_PENDING = "local_offline_implementation_pending"

_NON_GAP_STATUSES = frozenset(
    {
        _STATUS_NARRATIVE,
        _STATUS_COVERED,
        _STATUS_APPROVAL,
        _STATUS_LICENSE_BLOCKED,
        _STATUS_POLICY_LOCKED,
        _STATUS_CORRECTED,
    }
)


@dataclass(frozen=True)
class DocxBlueprintLine:
    line_number: int
    docx_text: str
    category: str
    status: str
    source_ids: tuple[str, ...] = ()
    implementation_refs: tuple[str, ...] = ()
    blocker: str | None = None
    next_action: str | None = None

    @property
    def commercial_gated(self) -> bool:
        return self.status == _STATUS_LICENSE_BLOCKED

    @property
    def unresolved_gap(self) -> bool:
        return self.status not in _NON_GAP_STATUSES


@dataclass(frozen=True)
class DocxSupplementalRequest:
    request_id: str
    request_text: str
    category: str
    status: str
    source_ids: tuple[str, ...] = ()
    implementation_refs: tuple[str, ...] = ()
    blocker: str | None = None
    next_action: str | None = None
    local_strategy: str | None = None

    @property
    def unresolved_gap(self) -> bool:
        return self.status not in _NON_GAP_STATUSES


DOCX_BLUEPRINT_LINES: tuple[DocxBlueprintLine, ...] = (
    DocxBlueprintLine(
        1, "Your Final Master Blueprint (The Launch Plan)", "heading", _STATUS_NARRATIVE
    ),
    DocxBlueprintLine(
        2,
        "This complete dataset and code layout is structured to get your platform live on Day 1 for $25/month while keeping your startup legally compliant.",
        "narrative",
        _STATUS_NARRATIVE,
    ),
    DocxBlueprintLine(
        3,
        "Tier 1: Upload to Supabase Storage (Free 100GB Bucket)",
        "tier_heading",
        _STATUS_APPROVAL,
        blocker="Supabase/object-storage uploads and runtime local-cache wiring require explicit approval.",
    ),
    DocxBlueprintLine(
        4,
        "Massive binary indexed files streamed by the backend through pyBigWig or twobitreader.",
        "tier_description",
        _STATUS_APPROVAL,
        blocker="Runtime object-storage streaming is not enabled in the current guardrails.",
    ),
    DocxBlueprintLine(5, "Tier 1 table header", "table_header", _STATUS_NARRATIVE),
    DocxBlueprintLine(
        6,
        "Benchling reference sequence: hg38.2bit from UCSC Genome Browser.",
        "asset_row",
        _STATUS_COVERED,
        ("ucsc_hg38_2bit", "python_twobit_reader"),
        (
            "app/backend/app/data_sources/local_inventory.py",
            "app/backend/app/services/reference_genome.py",
            "app/backend/tests/test_reference_genome_store.py",
            "app/backend/tests/test_reference_genome_store_local_hg38.py",
        ),
        next_action="Runtime asset delivery remains approval-gated.",
    ),
    DocxBlueprintLine(
        7,
        "Retired third-party variant ID rs search: GCF_000001405.40 VCF plus .tbi from NCBI dbSNP.",
        "asset_row",
        _STATUS_COVERED,
        ("ncbi_dbsnp_gcf_000001405_40", "python_pysam"),
        (
            "app/backend/app/services/dbsnp_local.py",
            "app/backend/app/services/indexed_sources.py",
            "app/backend/tests/test_dbsnp_local_adapter.py",
            "app/backend/tests/test_indexed_source_readers.py",
        ),
        next_action="Production dbSNP download and request-time wiring remain approval-gated.",
    ),
    DocxBlueprintLine(
        8,
        "Retired third-party clinical classifications: clinvar.vcf.gz plus .tbi from NCBI ClinVar FTP.",
        "asset_row",
        _STATUS_COVERED,
        ("ncbi_clinvar_vcf", "python_pysam"),
        (
            "app/backend/app/services/clinvar_local.py",
            "app/backend/app/services/indexed_sources.py",
            "app/backend/tests/test_clinvar_local_adapter.py",
            "app/backend/tests/test_indexed_source_readers.py",
        ),
        next_action="Production ClinVar VCF download and provider preference wiring remain approval-gated.",
    ),
    DocxBlueprintLine(
        9,
        "Benchling CRISPR off-target blockers: rmsk.bb converted from RepeatMasker text.",
        "asset_row",
        _STATUS_CORRECTED,
        ("repeatmasker_rmsk_bb",),
        (
            "app/backend/app/services/repeatmasker_local.py",
            "app/backend/app/services/indexed_sources.py",
            "app/backend/tests/test_repeatmasker_local_adapter.py",
            "app/backend/tests/test_indexed_source_readers.py",
        ),
        next_action="Use official rmsk.txt.gz first; derive rmsk.bb only after an approved conversion proof.",
    ),
    DocxBlueprintLine(
        10,
        "VarSome alternative conservation: hg38.phyloP100way.bw from UCSC PhyloP directory.",
        "asset_row",
        _STATUS_COVERED,
        ("ucsc_phylop100way_hg38", "python_pybigwig"),
        (
            "app/backend/app/services/indexed_sources.py",
            "app/backend/tests/test_indexed_source_readers.py",
            "app/backend/tests/test_source_asset_manifest.py",
        ),
        next_action="Full phyloP download and production conservation adapter remain approval-gated.",
    ),
    DocxBlueprintLine(
        11,
        "Tier 2: Save natively in the Render code repository.",
        "tier_heading",
        _STATUS_APPROVAL,
        blocker="Bundling real source assets in Git still requires terms and size review.",
    ),
    DocxBlueprintLine(
        12,
        "Small files read locally by the Render app, with gffutils-style indexing in memory.",
        "tier_description",
        _STATUS_COVERED,
        implementation_refs=("app/backend/app/services/transcript_model.py",),
        next_action="Production GTF import remains approval-gated; fixture transcript models are active.",
    ),
    DocxBlueprintLine(13, "Tier 2 table header", "table_header", _STATUS_NARRATIVE),
    DocxBlueprintLine(
        14,
        "Retired third-party default clinical map: MANE GRCh38 v1.4 Select Ensembl GTF.",
        "asset_row",
        _STATUS_CORRECTED,
        ("ncbi_mane_grch38_v1_4_select_ensembl",),
        (
            "app/backend/app/services/transcript_model.py",
            "app/backend/app/fixtures/transcript_models/mane_gencode_tiny.json",
            "app/backend/tests/test_transcript_model_store.py",
        ),
        next_action="Registry uses the official ensembl_genomic file and extracts MANE Select rows by tag.",
    ),
    DocxBlueprintLine(
        15,
        "Benchling alternate isoforms: gencode.v45.annotation.gtf.gz.",
        "asset_row",
        _STATUS_COVERED,
        ("gencode_v45_annotation",),
        (
            "app/backend/app/services/transcript_model.py",
            "app/backend/app/fixtures/transcript_models/mane_gencode_tiny.json",
            "app/backend/tests/test_transcript_model_store.py",
        ),
        next_action="Production GENCODE import remains approval-gated.",
    ),
    DocxBlueprintLine(
        16,
        "VarSome alternative ACMG logic blueprints: InterVar pipeline configuration files.",
        "asset_row",
        _STATUS_LICENSE_BLOCKED,
        ("intervar_pipeline_config",),
        ("app/backend/app/data_sources/policy.py", "app/backend/tests/test_source_field_policy.py"),
        blocker="InterVar, ANNOVAR, and OMIM rights review is required before production use.",
    ),
    DocxBlueprintLine(
        17,
        "Tier 2.5: Python computational engines in Render requirements.txt.",
        "tier_heading",
        _STATUS_COVERED,
        implementation_refs=(
            "app/backend/requirements.txt",
            "app/backend/app/data_sources/registry.py",
        ),
    ),
    DocxBlueprintLine(
        18,
        "Code libraries process data inside Render RAM.",
        "tier_description",
        _STATUS_COVERED,
        implementation_refs=("app/backend/requirements.txt",),
    ),
    DocxBlueprintLine(
        19,
        "primer3-py runs Benchling-style thermodynamic primer calculations.",
        "engine_row",
        _STATUS_COVERED,
        ("python_primer3_py",),
        ("app/backend/requirements.txt", "app/backend/app/services/primer_design.py"),
        next_action="Primer3 licensing/distribution risk remains tracked.",
    ),
    DocxBlueprintLine(
        20,
        "biopython handles DNA strings, reverse complements, and CRISPR PAM matching.",
        "engine_row",
        _STATUS_COVERED,
        ("python_biopython",),
        (
            "app/backend/requirements.txt",
            "app/backend/app/services/crispr_design.py",
            "app/backend/app/services/trace_parser.py",
        ),
    ),
    DocxBlueprintLine(
        21,
        "pysam, twobitreader, and pyBigWig are streaming connectors for indexed assets.",
        "engine_row",
        _STATUS_COVERED,
        ("python_pysam", "python_twobit_reader", "python_pybigwig"),
        (
            "app/backend/requirements.txt",
            "app/backend/app/services/indexed_sources.py",
            "app/backend/app/services/reference_genome.py",
            "app/backend/tests/test_indexed_source_readers.py",
        ),
        next_action="pysam/pyBigWig stay Linux-only pins; no Windows install or WSL run in this session.",
    ),
    DocxBlueprintLine(
        22,
        "Tier 3: Import into Supabase Postgres SQL tables.",
        "tier_heading",
        _STATUS_APPROVAL,
        blocker="Supabase imports and storage policy changes require explicit approval.",
    ),
    DocxBlueprintLine(
        23,
        "Relational datasets loaded as rows for symptom or disease keyword search.",
        "tier_description",
        _STATUS_COVERED,
        implementation_refs=("app/backend/app/services/clinical_source_tables.py",),
        next_action="Current work is fixture/parser-only; production imports remain approval-gated.",
    ),
    DocxBlueprintLine(24, "Tier 3 table header", "table_header", _STATUS_NARRATIVE),
    DocxBlueprintLine(
        25,
        "OMIM and Orphanet combined: mondo.json or mondo.tsv from Mondo Disease Ontology.",
        "asset_row",
        _STATUS_CORRECTED,
        ("mondo_disease_ontology",),
        (
            "app/backend/app/services/clinical_source_tables.py",
            "app/backend/app/fixtures/source_tables/mondo_tiny.json",
            "app/backend/tests/test_clinical_source_tables.py",
        ),
        next_action="Mondo xrefs are parsed; licensed OMIM/Orphanet import remains blocked.",
    ),
    DocxBlueprintLine(
        26,
        "Retired third-party symptom-to-gene maps: phenotype.hpoa and hp.gpad from HPO.",
        "asset_row",
        _STATUS_CORRECTED,
        ("human_phenotype_ontology",),
        (
            "app/backend/app/services/clinical_source_tables.py",
            "app/backend/app/fixtures/source_tables/phenotype_tiny.hpoa",
            "app/backend/app/fixtures/source_tables/genes_to_phenotype_tiny.txt",
            "app/backend/tests/test_clinical_source_tables.py",
        ),
        next_action="Registry uses official HPO annotation files; hp.gpad draft path is superseded.",
    ),
    DocxBlueprintLine(
        27,
        "Retired third-party gene curation validity: clingen_gene_validity.csv from ClinGen.",
        "asset_row",
        _STATUS_COVERED,
        ("clingen_gene_validity",),
        (
            "app/backend/app/services/clinical_source_tables.py",
            "app/backend/app/fixtures/source_tables/clingen_gene_validity_tiny.csv",
            "app/backend/tests/test_clinical_source_tables.py",
        ),
    ),
    DocxBlueprintLine(
        28,
        "Retired third-party cross-lab evidence consortium: gencc-download.csv from GenCC.",
        "asset_row",
        _STATUS_COVERED,
        ("gencc_download",),
        (
            "app/backend/app/services/clinical_source_tables.py",
            "app/backend/app/fixtures/source_tables/gencc_download_tiny.csv",
            "app/backend/tests/test_clinical_source_tables.py",
        ),
    ),
    DocxBlueprintLine(
        29,
        "Tier 4: Zero-download live public cloud APIs.",
        "tier_heading",
        _STATUS_COVERED,
        implementation_refs=("app/backend/app/data_sources/policy.py",),
        next_action="No new live MyVariant runtime provider is wired by this matrix.",
    ),
    DocxBlueprintLine(
        30,
        "Render pings a free endpoint on the fly and filters restricted blocks.",
        "tier_description",
        _STATUS_POLICY_LOCKED,
        ("myvariant_gnomad_only",),
        ("app/backend/app/data_sources/policy.py", "app/backend/tests/test_source_field_policy.py"),
    ),
    DocxBlueprintLine(31, "Tier 4 table header", "table_header", _STATUS_NARRATIVE),
    DocxBlueprintLine(
        32,
        "Retired third-party population rarity: MyVariant.info API gnomAD v4 frequencies.",
        "api_row",
        _STATUS_POLICY_LOCKED,
        ("myvariant_gnomad_only",),
        (
            "app/backend/app/data_sources/registry.py",
            "app/backend/app/data_sources/policy.py",
            "app/backend/tests/test_source_field_policy.py",
        ),
        next_action="Only gnomAD fields are allowlisted; runtime enablement remains behind source review.",
    ),
    DocxBlueprintLine(
        33,
        "Retired third-party premium predictors: MyVariant.info SpliceAI, CADD, REVEL, and PrimateAI-3D fields.",
        "api_row",
        _STATUS_LICENSE_BLOCKED,
        (
            "myvariant_gnomad_only",
            "illumina_spliceai_precomputed_hg38",
            "uw_cadd_scores_hg38",
            "zenodo_revel_scores",
            "illumina_primateai3d_scores",
        ),
        ("app/backend/app/data_sources/policy.py", "app/backend/tests/test_source_field_policy.py"),
        blocker="Restricted predictor unlocks require reviewed commercial rights.",
    ),
    DocxBlueprintLine(34, "Implementation Strategy", "heading", _STATUS_NARRATIVE),
    DocxBlueprintLine(
        35,
        "Data architecture is optimized for low-cost, minimal-risk launch.",
        "strategy",
        _STATUS_COVERED,
        implementation_refs=("app/backend/app/cli/eamos_source_asset_preflight.py",),
    ),
    DocxBlueprintLine(
        36,
        "Day 1 runs a functional genetic tool using active data blocks.",
        "strategy",
        _STATUS_COVERED,
        implementation_refs=(
            "app/backend/app/services/local_evidence_orchestrator.py",
            "app/backend/tests/test_local_evidence_orchestrator.py",
        ),
        next_action="Runtime local-source flows remain disabled unless explicitly allowed.",
    ),
    DocxBlueprintLine(
        37,
        "Render hits MyVariant.info for free, strips raw predictor decimals, and keeps waitlist hook safe.",
        "strategy",
        _STATUS_POLICY_LOCKED,
        ("myvariant_gnomad_only",),
        ("app/backend/app/data_sources/policy.py", "app/backend/tests/test_source_field_policy.py"),
        next_action=(
            "Keep MyVariant gnomAD-only filtering, but do not use that policy to strip "
            "admin/backend predictor evidence."
        ),
    ),
    DocxBlueprintLine(
        38,
        "After commercial agreements, flip backend toggle and open Pro-tier predictor fields.",
        "strategy",
        _STATUS_LICENSE_BLOCKED,
        (
            "illumina_spliceai_precomputed_hg38",
            "uw_cadd_scores_hg38",
            "zenodo_revel_scores",
            "illumina_primateai3d_scores",
        ),
        ("app/backend/app/data_sources/registry.py", "app/backend/app/data_sources/policy.py"),
        blocker=(
            "Backend/admin runtime use is approved; public launch remains gated until licenses, "
            "source rights, and product gates are finalized."
        ),
    ),
)


DOCX_SUPPLEMENTAL_REQUESTS: tuple[DocxSupplementalRequest, ...] = (
    DocxSupplementalRequest(
        request_id="S1",
        request_text=(
            "Rich Workbench/report protein annotation requires UniProtKB plus "
            "InterPro/Pfam style domain architecture, and novel user sequences "
            "must be annotatable without depending on live third-party APIs."
        ),
        category="supplemental_protein_annotation",
        status=_STATUS_LOCAL_IMPLEMENTATION_PENDING,
        source_ids=(
            "uniprotkb_reviewed_swissprot",
            "interpro_pfam_protein_matches",
            "interproscan_standalone",
            "interproscan_optional_licensed_apps",
            "hmmer_pfam_a",
        ),
        implementation_refs=(
            "app/backend/app/services/gene_viewer.py",
            "app/backend/app/schemas/gene_viewer.py",
            "app/backend/tests/test_gene_viewer.py",
        ),
        blocker=(
            "Core UniProtKB, InterPro/Pfam, InterProScan, and HMMER terms "
            "are recorded as commercially usable with attribution/citation "
            "requirements, but the local worker and reviewed import pipeline "
            "are not implemented or runtime-enabled. No live API dependency "
            "is approved by this matrix. Optional SignalP, Phobius, and "
            "DeepTMHMM apps remain disabled unless separately licensed."
        ),
        next_action=(
            "Design a local/offline protein annotation worker: translate the "
            "submitted coding sequence to protein, run InterProScan standalone "
            "or HMMER hmmscan against a reviewed local Pfam-A/InterPro data "
            "bundle, parse protein-coordinate ranges, cache by sequence hash "
            "and release version, then feed the Workbench ProteinDomainTrack."
        ),
        local_strategy=(
            "Prefer InterProScan standalone for broad families/domains/sites. "
            "Use HMMER+Pfam-A as the lighter local fallback. Mirror "
            "release-pinned UniProtKB reviewed annotations locally with "
            "attribution and provenance; do not attempt to generate "
            "UniProtKB-level expert curation locally."
        ),
    ),
)


def build_docx_task_matrix(
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
) -> dict[str, Any]:
    lines = [_line_summary(line, registry) for line in DOCX_BLUEPRINT_LINES]
    status_counts = Counter(line.status for line in DOCX_BLUEPRINT_LINES)
    category_counts = Counter(line.category for line in DOCX_BLUEPRINT_LINES)
    commercial_gated = [line.line_number for line in DOCX_BLUEPRINT_LINES if line.commercial_gated]
    unresolved_gaps = [line.line_number for line in DOCX_BLUEPRINT_LINES if line.unresolved_gap]
    return {
        "line_count": len(DOCX_BLUEPRINT_LINES),
        "status_counts": dict(sorted(status_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "commercial_gated_line_numbers": commercial_gated,
        "non_commercial_line_count": len(DOCX_BLUEPRINT_LINES) - len(commercial_gated),
        "non_commercial_unresolved_gap_count": len(
            [
                line
                for line in DOCX_BLUEPRINT_LINES
                if not line.commercial_gated and line.unresolved_gap
            ]
        ),
        "unresolved_gap_line_numbers": unresolved_gaps,
        "lines": lines,
    }


def build_docx_supplemental_matrix(
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
) -> dict[str, Any]:
    requests = [_supplement_summary(request, registry) for request in DOCX_SUPPLEMENTAL_REQUESTS]
    status_counts = Counter(request.status for request in DOCX_SUPPLEMENTAL_REQUESTS)
    category_counts = Counter(request.category for request in DOCX_SUPPLEMENTAL_REQUESTS)
    unresolved = [
        request.request_id for request in DOCX_SUPPLEMENTAL_REQUESTS if request.unresolved_gap
    ]
    return {
        "request_count": len(DOCX_SUPPLEMENTAL_REQUESTS),
        "status_counts": dict(sorted(status_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "unresolved_gap_count": len(unresolved),
        "unresolved_request_ids": unresolved,
        "requests": requests,
    }


def docx_blueprint_summary(
    registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
) -> dict[str, Any]:
    return {
        "source_file": DOCX_BLUEPRINT_NAME,
        "interpretation": "current_registry_and_guardrails_supersede_the_older_blueprint",
        "tiers": list(DOCX_BLUEPRINT_TIERS),
        "reconciliation": list(DOCX_RECONCILIATION),
        "task_matrix": build_docx_task_matrix(registry=registry),
        "supplemental_requests": build_docx_supplemental_matrix(registry=registry),
    }


def _line_summary(line: DocxBlueprintLine, registry: DataSourceRegistry) -> dict[str, Any]:
    return {
        "line_number": line.line_number,
        "docx_text": line.docx_text,
        "category": line.category,
        "status": line.status,
        "commercial_gated": line.commercial_gated,
        "source_ids": list(line.source_ids),
        "sources": [_source_summary(registry, source_id) for source_id in line.source_ids],
        "implementation_refs": list(line.implementation_refs),
        "blocker": line.blocker,
        "next_action": line.next_action,
    }


def _supplement_summary(
    request: DocxSupplementalRequest, registry: DataSourceRegistry
) -> dict[str, Any]:
    return {
        "request_id": request.request_id,
        "request_text": request.request_text,
        "category": request.category,
        "status": request.status,
        "unresolved_gap": request.unresolved_gap,
        "source_ids": list(request.source_ids),
        "sources": [_source_summary(registry, source_id) for source_id in request.source_ids],
        "implementation_refs": list(request.implementation_refs),
        "blocker": request.blocker,
        "next_action": request.next_action,
        "local_strategy": request.local_strategy,
    }


def _source_summary(registry: DataSourceRegistry, source_id: str) -> dict[str, Any]:
    record = registry.get(source_id)
    return {
        "source_id": record.source_id,
        "display_name": record.display_name,
        "day1_status": record.day1_status,
        "license_status": record.license_status.value,
        "download_approved": record.download_approved,
        "allowed_fields": list(record.allowed_fields),
        "restricted_fields": list(record.restricted_fields),
    }
