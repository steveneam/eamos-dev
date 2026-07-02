from __future__ import annotations

import json
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote_plus
from uuid import uuid4

from app.rules.base import DecisionInput
from app.schemas.lookup import (
    LookupInitialSummaryResponse,
    LookupRequest,
    LookupResponse,
    LookupSectionFetchRequest,
    LookupSectionFetchResponse,
    PublicationPageRequest,
    SearchInputInterpretation,
    SearchInputParseRequest,
    SearchInputParseResponse,
)
from app.schemas.run import (
    ClinicalTrialQueryExecution,
    EvidenceSourceSummary,
    FunctionalEvidenceSummary,
    PublicationLiterature,
    PublicationsCallout,
    PubMedArticle,
    ReportPayload,
    SourceProvenance,
    TherapiesTrialsSection,
    TrialMatch,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.services.clinical_consensus import ClinicalConsensusBuilder
from app.services.acmg_points_engine import compute_report_acmg_classification
from app.services.clinvar_local import ClinVarLocalError
from app.services.functional_evidence import FunctionalEvidenceExtractor
from app.services.gene_context_snapshot import GeneContextSnapshotService
from app.services.lookup_sections import (
    build_lookup_initial_summary,
    build_lookup_section_fetch_response,
)
from app.services.lookup_service_cache import (
    FUNCTIONAL_EVIDENCE_CACHE_VERSION,
    GENE_CONTEXT_SNAPSHOT_CACHE_VERSION,
    LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING,
    LEGACY_REPORT_SHELL_CACHE_READ_WARNING,
    PUBLICATION_DATA_CACHE_VERSION,
    REPORT_SECTION_CACHE_VERSION,
    REPORT_SHELL_CACHE_VERSION,
    SOURCE_RESULT_CACHE_VERSION,
    STRICT_GENOMIC_CACHE_VERSION,
    annotate_source_cached_result as _annotate_source_cached_result,
    cached_functional_evidence_is_current as _cached_functional_evidence_is_current,
    evidence_summary_to_result as _evidence_summary_to_result,
    gene_context_snapshot_cache_is_current as _gene_context_snapshot_cache_is_current,
    hydrate_variant_from_source_result as _hydrate_variant_from_source_result,
    merged_report_sections_cache_payload as _merged_report_sections_cache_payload,
    publication_data_cache_is_current as _publication_data_cache_is_current,
    report_cache_identity_from_response as _report_cache_identity_from_response,
    report_cache_identity_from_variant as _report_cache_identity_from_variant,
    report_sections_cache_payload as _report_sections_cache_payload,
    report_shell_cache_payload as _report_shell_cache_payload,
    result_to_evidence as _result_to_evidence,
    sections_from_report_section_cache as _sections_from_report_section_cache,
    sections_from_report_section_payload as _sections_from_report_section_payload,
    source_cache_token as _source_cache_token,
    source_result_cache_to_result as _source_result_cache_to_result,
    source_version_from_result as _source_version_from_result,
    strict_genomic_cache_is_current as _strict_genomic_cache_is_current,
    summary_from_report_shell_cache as _summary_from_report_shell_cache,
    summary_from_report_shell_payload as _summary_from_report_shell_payload,
)
from app.services.lookup_service_clinvar_distribution import (
    CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX,
    clinvar_distribution_runtime_path as _clinvar_distribution_runtime_path,
    clinvar_gene_distribution_exclusion_warning as _clinvar_gene_distribution_exclusion_warning,
    local_clinvar_gene_distribution as _local_clinvar_gene_distribution,
)
from app.services.lookup_service_utils import dedupe_values as _dedupe_values
from app.services.lookup_service_utils import text_value as _text_value
from app.services.lookup_timing import LookupTimingCollector
from app.services.publication_literature import EamosProprietaryVariantLiteratureExtractor
from app.services.report_call_cards import (
    build_population_frequency_detail,
    build_variant_report_call_cards,
)
from app.services.report_data_currency import (
    build_source_version_pins,
    build_report_data_currency,
    current_report_timestamp,
)
from app.services.sequence_context import SequenceContextService
from app.services.search_input_interpreter import SearchInputInterpreter
from app.services.search_input_resolver import EamosSearchInputResolver
from app.services.variant_report_orchestrator import VariantReportDataOrchestrator
from app.services.variant_decoder import decode_variant
from app.services.source_cache import (
    clingen_vcep_source_cache_key,
    is_hero_example_variant,
    source_cache_key,
)
from app.tools.base import ToolResult
from app.tools.clingen import cached_clingen_result_matches_variant
from app.tools.registry import STRICT_GENOMIC_PLUGINS

GENE_THERAPY_MAP: dict[str, str] = {
    "RPE65": (
        "Luxturna (voretigene neparvovec) — FDA approved 2017, EMA approved 2018. "
        "Subretinal injection of AAV2 vector. Indicated for RPE65-associated inherited retinal dystrophy. "
        "Marketed by Spark Therapeutics (Eli Lilly). Requires biallelic RPE65 mutations with sufficient viable retinal cells."
    ),
    "RPGR": (
        "No approved gene therapy. Multiple phase I/II trials active, including AGTC-501 and AAV-RPGR programmes. "
        "Check ClinicalTrials.gov for current recruitment status."
    ),
    "CNGA3": (
        "No approved gene therapy. Phase I/II trial active (NCT02610582) targeting achromatopsia due to CNGA3 mutations. "
        "Check ClinicalTrials.gov for current recruitment status."
    ),
    "CNGB3": (
        "No approved gene therapy. Phase I/II trial active targeting achromatopsia due to CNGB3 mutations. "
        "Check ClinicalTrials.gov for current recruitment status."
    ),
    "ABCA4": (
        "No approved gene therapy identified for ABCA4-related Stargardt disease. "
        "Use the ClinicalTrials.gov discovery rows below for current recruitment status."
    ),
}

SOURCE_CACHE_PERSIST_STATUSES = {"live", "cache"}
SOURCE_CACHE_FAILURE_STATUSES = {"fallback", "degraded", "error", "failed"}
SOURCE_CACHE_GENERAL_SOURCES = {"gnomad"}
SOURCE_SPECIFIC_SECTION_IDS = frozenset(
    {"publications", "therapies_trials", "computational_deep_dive", "clingen_vcep"}
)
SOURCE_RESULT_SECTION_SOURCES: dict[str, tuple[str, ...]] = {
    "therapies_trials": ("clinical_trials",),
    "computational_deep_dive": ("computational_annotations", "spliceai"),
    "clingen_vcep": ("clinvar", "clingen"),
}

__all__ = [
    "CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX",
    "FUNCTIONAL_EVIDENCE_CACHE_VERSION",
    "GENE_CONTEXT_SNAPSHOT_CACHE_VERSION",
    "GENE_THERAPY_MAP",
    "LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING",
    "LEGACY_REPORT_SHELL_CACHE_READ_WARNING",
    "LookupEvidenceContext",
    "LookupService",
    "LookupWithEvidenceContext",
    "PUBLICATION_DATA_CACHE_VERSION",
    "REPORT_SECTION_CACHE_VERSION",
    "REPORT_SHELL_CACHE_VERSION",
    "SOURCE_RESULT_CACHE_VERSION",
    "STRICT_GENOMIC_CACHE_VERSION",
    "_clinvar_distribution_runtime_path",
    "_clinvar_gene_distribution_exclusion_warning",
]


@dataclass(frozen=True)
class LookupEvidenceContext:
    evidence_map: dict[str, dict[str, Any]]
    evidence_statuses: dict[str, str]


@dataclass(frozen=True)
class LookupWithEvidenceContext:
    response: LookupResponse
    evidence_map: dict[str, dict[str, Any]]
    evidence_statuses: dict[str, str]


def _format_clinical_trials_summary(gene: str, rows: list[dict[str, Any]]) -> str:
    lines = [f"{len(rows)} active/not-yet ClinicalTrials.gov record(s) found for {gene}:"]
    for row in rows:
        nct_id = str(row.get("nct_id") or "NCT unavailable")
        phase = str(row.get("phase") or "Phase N/A")
        status = str(row.get("status") or "Unknown")
        title = str(row.get("title") or "Untitled clinical trial")
        lines.append(f"- {nct_id} - {phase} - {status} - {title}")
    return "\n".join(lines)


def _clinical_trials_no_rows_summary(gene: str, result: ToolResult) -> str:
    summary = result.summary if isinstance(result.summary, dict) else {}
    warnings = [
        *[str(item) for item in summary.get("warnings", []) if isinstance(item, str)],
        *result.warnings,
    ]
    if "clinical_trials_no_active_matches" in warnings:
        return f"No active trials found for {gene} on ClinicalTrials.gov."
    if result.status in {"fallback", "error", "failed"} or any(
        warning.startswith("clinical_trials_fetch_failed") for warning in warnings
    ):
        return (
            f"Clinical trials lookup unavailable for {gene}. " "Check ClinicalTrials.gov directly."
        )
    return "No structured ClinicalTrials.gov rows are available for this lookup."


def _clinical_trial_disease_terms(evidence_map: dict[str, dict[str, Any]]) -> list[str]:
    gene_disease = evidence_map.get("gene_disease", {})
    terms: list[str] = []
    primary = _text_value(gene_disease.get("primary_condition"))
    if primary:
        terms.append(primary)
    conditions = gene_disease.get("conditions")
    if isinstance(conditions, list):
        for condition in conditions:
            if not isinstance(condition, dict):
                continue
            name = _text_value(condition.get("name"))
            if name:
                terms.append(name)
    return _dedupe_values(terms)


def _acmg_classification_snapshot(gene: str, cdna: str, clinvar: dict[str, Any]) -> str:
    classification = clinvar.get("classification", "Unavailable")
    review_status_text = clinvar.get("review_status", "review status unavailable")
    return (
        f"ClinVar currently lists {gene} {cdna} as {classification} ({review_status_text}). "
        "This is a source snapshot only and should not be read as formal ACMG evidence-code "
        "assignment or a final laboratory classification."
    )


@lru_cache(maxsize=1)
def _lookup_v2_modules_fixture() -> dict:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "lookup_v2_modules.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _lookup_v2_modules(gene: str, cdna: str) -> dict:
    return _lookup_v2_modules_fixture().get(gene, {}).get(cdna, {})


def _scholar_url(gene: str, cdna: str) -> str:
    return f"https://scholar.google.com/scholar?q={quote_plus(f'{gene} {cdna}')}"


def _merge_litvar_articles(
    pubmed_articles: list[PubMedArticle],
    litvar_summary: dict[str, Any],
) -> list[PubMedArticle]:
    by_pmid = {article.pmid: article for article in pubmed_articles}
    for item in litvar_summary.get("articles", []) if isinstance(litvar_summary, dict) else []:
        if not isinstance(item, dict):
            continue
        pmid = str(item.get("pmid") or "")
        if not pmid:
            continue
        if pmid in by_pmid:
            existing = by_pmid[pmid]
            by_pmid[pmid] = existing.model_copy(
                update={"url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
            )
            continue
        by_pmid[pmid] = PubMedArticle(
            pmid=pmid,
            title=item.get("title") or "Untitled",
            authors=item.get("authors") or "",
            journal=item.get("journal") or "",
            year=str(item.get("year") or ""),
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            abstract=item.get("abstract"),
        )
    return list(by_pmid.values())


def _extract_dbsnp_rsid(clinvar_raw: Any) -> str | None:
    if not isinstance(clinvar_raw, dict):
        return None
    for variation in clinvar_raw.get("variation_set") or []:
        if not isinstance(variation, dict):
            continue
        for xref in variation.get("variation_xrefs") or []:
            if not isinstance(xref, dict):
                continue
            if xref.get("db_source") != "dbSNP":
                continue
            db_id = str(xref.get("db_id") or "").strip()
            if not db_id:
                continue
            return db_id if db_id.startswith("rs") else f"rs{db_id}"
    return None


def _interpretation_can_run(interpretation: SearchInputInterpretation) -> bool:
    return (
        interpretation.mode in {"deterministic", "ai_assisted", "auto_resolved"}
        and bool(interpretation.cdna)
        and not interpretation.requires_confirmation
    )


def _lookup_request_from_interpretation(
    request: LookupRequest,
    interpretation: SearchInputInterpretation,
) -> LookupRequest:
    return request.model_copy(
        update={
            "search_text": None,
            "query": None,
            "selected_candidate_id": None,
            "gene": interpretation.gene or "",
            "cdna": interpretation.cdna
            or interpretation.genomic_hgvs
            or interpretation.genomic_hg38,
            "transcript": interpretation.transcript,
            "protein_change": interpretation.protein_change,
        }
    )


def _interpretation_only_response(
    interpretation: SearchInputInterpretation,
    species: str,
) -> LookupResponse:
    title = "Variant search recommendations"
    if interpretation.mode == "needs_selection":
        title = "Variant search candidate selection"
    prompt = interpretation.ui_prompt or "Review the ranked interpretation options to continue."
    return LookupResponse(
        query=interpretation.normalized_query or interpretation.submitted_text,
        species=species,
        report_payload=ReportPayload(
            patient_id=f"lookup_search_{uuid4().hex[:8]}",
            report_title=title,
            limitations=prompt,
        ),
        evidence=[],
        warnings=list(interpretation.warnings),
        search_interpretation=interpretation,
    )


class LookupService:
    def __init__(
        self,
        tool_registry,
        rule_engine,
        draft_render_service=None,
        variant_cache_repo=None,
        report_cache_repo=None,
        source_cache_repo=None,
        settings=None,
        functional_evidence_extractor=None,
        clinical_consensus_builder=None,
        sequence_context_service=None,
        gene_context_snapshot=None,
    ) -> None:
        self.tool_registry = tool_registry
        self.rule_engine = rule_engine
        self.draft_render_service = draft_render_service
        self.variant_cache_repo = variant_cache_repo
        self.report_cache_repo = report_cache_repo
        self.source_cache_repo = source_cache_repo
        self.settings = settings
        self.publication_literature = EamosProprietaryVariantLiteratureExtractor()
        self.functional_evidence = functional_evidence_extractor or FunctionalEvidenceExtractor(
            settings=settings
        )
        self.clinical_consensus = clinical_consensus_builder or ClinicalConsensusBuilder(
            settings=settings
        )
        self.search_input_resolver = EamosSearchInputResolver(
            settings=settings,
            resolve_coordinates=bool(settings and settings.use_real_apis),
        )
        self.search_input_interpreter = SearchInputInterpreter(settings=settings)
        self.sequence_context = sequence_context_service or SequenceContextService(
            settings=settings
        )
        self.gene_context_snapshot = gene_context_snapshot or GeneContextSnapshotService(
            settings=settings
        )
        self.report_orchestrator = VariantReportDataOrchestrator()

    def lookup_with_evidence_context(
        self,
        request: LookupRequest,
        refresh: bool = False,
    ) -> LookupWithEvidenceContext:
        """Run the normal lookup path and expose the in-process evidence tap."""
        context_sink: list[LookupEvidenceContext] = []
        response = self.lookup(request, refresh=refresh, _evidence_context_sink=context_sink)
        context = (
            context_sink[0]
            if context_sink
            else LookupEvidenceContext(
                evidence_map={},
                evidence_statuses={item.source: item.status for item in response.evidence},
            )
        )
        return LookupWithEvidenceContext(
            response=response,
            evidence_map=context.evidence_map,
            evidence_statuses=context.evidence_statuses,
        )

    def parse_search_input(self, request: SearchInputParseRequest) -> SearchInputParseResponse:
        return SearchInputParseResponse(
            interpretation=self.search_input_interpreter.interpret(
                request.search_text,
                species=request.species,
                allow_ai=request.allow_ai,
                resolve_coordinates=request.resolve_coordinates,
            )
        )

    def lookup_summary(
        self,
        request: LookupRequest,
        refresh: bool = False,
    ) -> LookupInitialSummaryResponse:
        timing = (
            LookupTimingCollector(
                max_entries=int(
                    getattr(self.settings, "lookup_timing_diagnostics_max_entries", 80) or 80
                )
            )
            if bool(getattr(self.settings, "lookup_timing_diagnostics_enabled", False))
            else None
        )
        prepared_started = timing.start() if timing is not None else 0.0
        prepared = self._summary_from_prepared_report_shell(request, refresh=refresh)
        if timing is not None:
            timing.record_phase(
                "prepared_report_shell",
                prepared_started,
                outcome="hit" if prepared is not None else "miss",
            )
        if prepared is not None:
            if timing is not None:
                prepared.attach_lookup_timing_header(timing.header_value())
            return prepared

        response = self.lookup(request, refresh=refresh)
        summary = build_lookup_initial_summary(response)
        summary.attach_lookup_timing_header(response.lookup_timing_header)
        return summary

    def _summary_from_prepared_report_shell(
        self,
        request: LookupRequest,
        *,
        refresh: bool = False,
    ) -> LookupInitialSummaryResponse | None:
        if (
            refresh
            or request.species != "human"
            or request.raw_search_text
            or request.selected_candidate_id
            or self.settings is None
            or not self.settings.use_real_apis
            or (self.report_cache_repo is None and self.variant_cache_repo is None)
        ):
            return None

        input_resolution = self.search_input_resolver.resolve(
            gene=request.gene or "",
            cdna=request.cdna or "",
            transcript=request.transcript,
            protein_change=request.protein_change,
        )
        if input_resolution.kind == "unknown":
            return None
        cache_key = f"{input_resolution.gene}:{input_resolution.hgvs}"
        if self.report_cache_repo is not None:
            table_payload = self.report_cache_repo.get_report_shell(
                cache_key,
                schema_version=REPORT_SHELL_CACHE_VERSION,
                ttl_days=self.settings.cache_ttl_days,
            )
            if isinstance(table_payload, dict):
                table_summary = _summary_from_report_shell_payload(table_payload)
                if table_summary is not None:
                    return table_summary

        if self.variant_cache_repo is None:
            return None
        cache_hit = self.variant_cache_repo.get_fresh(cache_key, self.settings.cache_ttl_days)
        publication_cache = (
            cache_hit.get("publication_data", {}) if isinstance(cache_hit, dict) else {}
        )
        if not (
            isinstance(publication_cache, dict)
            and _publication_data_cache_is_current(publication_cache)
        ):
            return None
        return _summary_from_report_shell_cache(publication_cache)

    def _store_report_shell_cache(self, cache_key: str, response: LookupResponse) -> None:
        if (
            self.settings is None
            or not self.settings.use_real_apis
            or (self.report_cache_repo is None and self.variant_cache_repo is None)
        ):
            return
        summary = build_lookup_initial_summary(response)
        if self.report_cache_repo is not None:
            self.report_cache_repo.upsert_report_shell(
                cache_key,
                normalized_identity=_report_cache_identity_from_response(
                    cache_key=cache_key,
                    response=response,
                ),
                schema_version=REPORT_SHELL_CACHE_VERSION,
                payload=summary.model_dump(mode="json"),
                ttl_days=self.settings.cache_ttl_days,
            )
            return
        if self.variant_cache_repo is not None and hasattr(
            self.variant_cache_repo,
            "update_report_shell",
        ):
            self.variant_cache_repo.update_report_shell(
                cache_key,
                report_shell=_report_shell_cache_payload(summary),
            )

    def lookup_sections(
        self,
        request: LookupSectionFetchRequest,
        refresh: bool = False,
    ) -> LookupSectionFetchResponse:
        timing = (
            LookupTimingCollector(
                max_entries=int(
                    getattr(self.settings, "lookup_timing_diagnostics_max_entries", 80) or 80
                )
            )
            if bool(getattr(self.settings, "lookup_timing_diagnostics_enabled", False))
            else None
        )
        prepared_started = timing.start() if timing is not None else 0.0
        prepared = self._sections_from_prepared_report_cache(request, refresh=refresh)
        if timing is not None:
            timing.record_phase(
                "prepared_report_sections",
                prepared_started,
                outcome="hit" if prepared is not None else "miss",
                metadata={"section_count": len(request.include)},
            )
        if prepared is not None:
            if timing is not None:
                prepared.attach_lookup_timing_header(timing.header_value())
            return prepared

        source_started = timing.start() if timing is not None else 0.0
        source_specific = self._sections_from_source_specific_builders(
            request,
            refresh=refresh,
        )
        if timing is not None:
            timing.record_phase(
                "source_specific_report_sections",
                source_started,
                outcome="hit" if source_specific is not None else "miss",
                metadata={"section_count": len(request.include)},
            )
        if source_specific is not None:
            if timing is not None:
                source_specific.attach_lookup_timing_header(timing.header_value())
            return source_specific

        lookup_request = LookupRequest.model_validate(request.model_dump(exclude={"include"}))
        response = self.lookup(lookup_request, refresh=refresh)
        sections = build_lookup_section_fetch_response(response, request.include)
        sections.attach_lookup_timing_header(response.lookup_timing_header)
        return sections

    def _sections_from_prepared_report_cache(
        self,
        request: LookupSectionFetchRequest,
        *,
        refresh: bool = False,
    ) -> LookupSectionFetchResponse | None:
        if (
            refresh
            or request.species != "human"
            or request.raw_search_text
            or request.selected_candidate_id
            or self.settings is None
            or not self.settings.use_real_apis
            or (self.report_cache_repo is None and self.variant_cache_repo is None)
        ):
            return None

        input_resolution = self.search_input_resolver.resolve(
            gene=request.gene or "",
            cdna=request.cdna or "",
            transcript=request.transcript,
            protein_change=request.protein_change,
        )
        if input_resolution.kind == "unknown":
            return None
        cache_key = f"{input_resolution.gene}:{input_resolution.hgvs}"
        if self.report_cache_repo is not None:
            table_payload = self.report_cache_repo.get_report_sections(
                cache_key,
                section_ids=list(request.include),
                schema_version=REPORT_SECTION_CACHE_VERSION,
                ttl_days=self.settings.cache_ttl_days,
            )
            if isinstance(table_payload, dict):
                table_sections = _sections_from_report_section_payload(
                    table_payload,
                    list(request.include),
                )
                if table_sections is not None:
                    return table_sections

        if self.variant_cache_repo is None:
            return None
        cache_hit = self.variant_cache_repo.get_fresh(cache_key, self.settings.cache_ttl_days)
        publication_cache = (
            cache_hit.get("publication_data", {}) if isinstance(cache_hit, dict) else {}
        )
        if not (
            isinstance(publication_cache, dict)
            and _publication_data_cache_is_current(publication_cache)
        ):
            return None
        return _sections_from_report_section_cache(publication_cache, list(request.include))

    def _store_report_sections_cache(self, cache_key: str, response: LookupResponse) -> None:
        if (
            self.settings is None
            or not self.settings.use_real_apis
            or (self.report_cache_repo is None and self.variant_cache_repo is None)
        ):
            return
        report_sections = _report_sections_cache_payload(response)
        if self.report_cache_repo is not None:
            self.report_cache_repo.upsert_report_sections(
                cache_key,
                normalized_identity=_report_cache_identity_from_response(
                    cache_key=cache_key,
                    response=response,
                ),
                schema_version=REPORT_SECTION_CACHE_VERSION,
                response_payload=report_sections["response"],
                ttl_days=self.settings.cache_ttl_days,
            )
            return
        if self.variant_cache_repo is not None and hasattr(
            self.variant_cache_repo,
            "update_report_sections",
        ):
            self.variant_cache_repo.update_report_sections(
                cache_key,
                report_sections=report_sections,
            )

    def _store_section_response_cache(
        self,
        cache_key: str,
        publication_cache: dict[str, Any],
        response: LookupSectionFetchResponse,
    ) -> None:
        if (
            self.settings is None
            or not self.settings.use_real_apis
            or (self.report_cache_repo is None and self.variant_cache_repo is None)
        ):
            return
        if self.report_cache_repo is not None:
            self.report_cache_repo.upsert_report_sections(
                cache_key,
                normalized_identity={
                    "identity_version": 1,
                    "query_string": cache_key,
                    "species": response.species,
                    "genome_build": "GRCh38",
                    "gene": cache_key.partition(":")[0] or None,
                    "cdna": cache_key.partition(":")[2] or None,
                    "request_identity": {"query": cache_key},
                },
                schema_version=REPORT_SECTION_CACHE_VERSION,
                response_payload=response.model_dump(mode="json"),
                ttl_days=self.settings.cache_ttl_days,
            )
            return
        if self.variant_cache_repo is not None and hasattr(
            self.variant_cache_repo,
            "update_report_sections",
        ):
            self.variant_cache_repo.update_report_sections(
                cache_key,
                report_sections=_merged_report_sections_cache_payload(publication_cache, response),
            )

    def _store_report_source_result_cache(
        self,
        cache_key: str,
        *,
        variant: Any,
        result: ToolResult,
        species: str = "human",
    ) -> None:
        if (
            self.settings is None
            or not self.settings.use_real_apis
            or self.report_cache_repo is None
        ):
            return
        source_version = _source_version_from_result(result)
        self.report_cache_repo.upsert_source_result(
            cache_key,
            normalized_identity=_report_cache_identity_from_variant(
                cache_key=cache_key,
                variant=variant,
                species=species,
            ),
            source_id=result.source,
            schema_version=SOURCE_RESULT_CACHE_VERSION,
            status=result.status,
            payload=result.summary or {},
            raw=result.raw,
            warnings=list(result.warnings),
            ttl_days=self.settings.cache_ttl_days,
            freshness={
                "fetched_at": result.fetched_at,
                "source_status": result.status,
                "source_url": result.source_url,
                "source_version": source_version,
                "stale_on_failure": result.cache_status == "stale_on_failure",
            },
            source_versions={"source_version": source_version} if source_version else {},
        )

    def _cached_report_source_results(
        self,
        cache_key: str,
        *,
        source_ids: list[str],
        refresh: bool,
    ) -> dict[str, ToolResult]:
        if (
            refresh
            or self.settings is None
            or not self.settings.use_real_apis
            or self.report_cache_repo is None
        ):
            return {}
        rows = self.report_cache_repo.get_source_results(
            cache_key,
            source_ids=source_ids,
            schema_version=SOURCE_RESULT_CACHE_VERSION,
            ttl_days=self.settings.cache_ttl_days,
        )
        return {
            source_id: _source_result_cache_to_result(source_id, row)
            for source_id, row in rows.items()
        }

    def _section_source_result(
        self,
        source_id: str,
        *,
        cache_key: str,
        variant: Any,
        cached_source_results: dict[str, ToolResult],
        species: str,
        refresh: bool,
        warnings: list[str],
    ) -> ToolResult:
        cached = cached_source_results.get(source_id)
        if cached is not None:
            return cached

        tool = self.tool_registry.get(source_id)
        if tool is None:
            return ToolResult(
                source=source_id,
                status="missing",
                request_identity={"gene": getattr(variant, "gene", None)},
                summary={},
                warnings=[f"{source_id}_unavailable"],
                raw=None,
            )
        try:
            if source_id == "clingen":
                result = tool.get_evidence(variant=variant, refresh=refresh)
            else:
                result = tool.get_evidence(variant=variant)
        except Exception as exc:
            return ToolResult(
                source=source_id,
                status="fallback",
                request_identity={"gene": getattr(variant, "gene", None)},
                summary={},
                warnings=[f"{source_id}_section_fetch_failed:{type(exc).__name__}"],
                raw=None,
            )

        try:
            self._store_report_source_result_cache(
                cache_key,
                variant=variant,
                result=result,
                species=species,
            )
        except Exception as exc:
            warnings.append(f"source_result_cache_write_failed:{source_id}:{type(exc).__name__}")
        return result

    def _clingen_vcep_section_source_result(
        self,
        *,
        cache_key: str,
        cdna: str,
        variant: Any,
        clinvar_result: ToolResult,
        cached_source_results: dict[str, ToolResult],
        species: str,
        refresh: bool,
        warnings: list[str],
    ) -> ToolResult:
        cached = cached_source_results.get("clingen")
        if cached is not None:
            return cached

        source_cache_lookup_key = None
        use_source_cache = (
            self.settings is not None
            and self.settings.use_real_apis
            and self.source_cache_repo is not None
        )
        if use_source_cache:
            source_cache_lookup_key = clingen_vcep_source_cache_key(
                gene=getattr(variant, "gene", ""),
                transcript_hgvs=getattr(variant, "transcript_hgvs", None),
                cdna=cdna,
                genomic_hgvs=getattr(variant, "genomic_hgvs", None),
                genomic_hg38=getattr(variant, "genomic_hg38", None),
                clinvar_summary=clinvar_result.summary,
                clinvar_raw=clinvar_result.raw,
            )

        skip_fresh_source_cache = self.settings is not None and self.settings.clingen_local_enabled
        if source_cache_lookup_key and not refresh and not skip_fresh_source_cache:
            hit = self.source_cache_repo.get_fresh("clingen", source_cache_lookup_key)
            if hit is not None:
                hit_result = hit.to_tool_result(status="cache", cache_status="cache_hit")
                if cached_clingen_result_matches_variant(hit_result, variant):
                    return hit_result
                warnings.append("source_cache_identity_mismatch:clingen")

        result = self._section_source_result(
            "clingen",
            cache_key=cache_key,
            variant=variant,
            cached_source_results={},
            species=species,
            refresh=refresh,
            warnings=warnings,
        )

        if source_cache_lookup_key and result.status in SOURCE_CACHE_FAILURE_STATUSES:
            stale = self.source_cache_repo.get_stale("clingen", source_cache_lookup_key)
            if stale is not None:
                stale_result = stale.to_tool_result(
                    status="stale",
                    cache_status="stale_on_failure",
                    extra_warnings=[
                        "source_cache_stale_on_failure:clingen",
                        f"live_status:{result.status}",
                        *result.warnings,
                    ],
                )
                if cached_clingen_result_matches_variant(stale_result, variant):
                    return stale_result
                result.warnings.append("source_cache_identity_mismatch:clingen")

        if (
            source_cache_lookup_key
            and result.status != "local"
            and result.status in SOURCE_CACHE_PERSIST_STATUSES
            and "clingen_variant_not_found" not in result.warnings
            and (result.summary or {}).get("expert_panel")
            and cached_clingen_result_matches_variant(result, variant)
        ):
            _annotate_source_cached_result(
                "clingen",
                result,
                cache_key=source_cache_lookup_key,
            )
            self.source_cache_repo.upsert(
                result.source,
                source_cache_lookup_key,
                normalized_identity={
                    "query": source_cache_lookup_key,
                    "gene": getattr(variant, "gene", None),
                    "cdna": cdna,
                    "genomic_hg38": getattr(variant, "genomic_hg38", None),
                    "genomic_hgvs": getattr(variant, "genomic_hgvs", None),
                },
                request_identity=result.request_identity,
                status=result.status,
                summary=result.summary,
                raw=result.raw,
                warnings=result.warnings,
                source_url=result.source_url,
                ttl_days=self.settings.cache_ttl_days,
                source_version=_source_version_from_result(result),
            )
        return result

    def _record_section_source_result(
        self,
        name: str,
        result: ToolResult,
        *,
        evidence: list[EvidenceSourceSummary],
        evidence_map: dict[str, dict[str, Any]],
        evidence_raw: dict[str, Any],
        evidence_statuses: dict[str, str],
        warnings: list[str],
    ) -> None:
        evidence.append(_result_to_evidence(result))
        evidence_map[name] = result.summary or {}
        evidence_raw[name] = result.raw
        evidence_statuses[name] = result.status
        warnings.extend(result.warnings)

    def _build_computational_section_profile(
        self,
        *,
        cache_key: str,
        variant: Any,
        input_resolution: Any,
        report_payload: ReportPayload,
        cached_source_results: dict[str, ToolResult],
        evidence: list[EvidenceSourceSummary],
        evidence_map: dict[str, dict[str, Any]],
        evidence_raw: dict[str, Any],
        evidence_statuses: dict[str, str],
        warnings: list[str],
        species: str,
        refresh: bool,
    ) -> VariantReportProfile:
        computational_result = self._section_source_result(
            "computational_annotations",
            cache_key=cache_key,
            variant=variant,
            cached_source_results=cached_source_results,
            species=species,
            refresh=refresh,
            warnings=warnings,
        )
        self._record_section_source_result(
            "computational_annotations",
            computational_result,
            evidence=evidence,
            evidence_map=evidence_map,
            evidence_raw=evidence_raw,
            evidence_statuses=evidence_statuses,
            warnings=warnings,
        )
        spliceai_result = cached_source_results.get("spliceai")
        if spliceai_result is not None:
            self._record_section_source_result(
                "spliceai",
                spliceai_result,
                evidence=evidence,
                evidence_map=evidence_map,
                evidence_raw=evidence_raw,
                evidence_statuses=evidence_statuses,
                warnings=warnings,
            )
        return self.report_orchestrator.build_profile(
            resolution=input_resolution,
            interpretation=None,
            payload=report_payload,
            evidence=evidence,
            evidence_map=evidence_map,
            evidence_statuses=evidence_statuses,
        )

    def _build_clingen_vcep_section_profile(
        self,
        *,
        cache_key: str,
        variant: Any,
        input_resolution: Any,
        report_payload: ReportPayload,
        cached_source_results: dict[str, ToolResult],
        evidence: list[EvidenceSourceSummary],
        evidence_map: dict[str, dict[str, Any]],
        evidence_raw: dict[str, Any],
        evidence_statuses: dict[str, str],
        warnings: list[str],
        species: str,
        refresh: bool,
    ) -> VariantReportProfile:
        clinvar_result: ToolResult | None = None
        for source_id in ("clinvar", "clingen"):
            if source_id == "clingen" and clinvar_result is not None:
                result = self._clingen_vcep_section_source_result(
                    cache_key=cache_key,
                    cdna=input_resolution.hgvs,
                    variant=variant,
                    clinvar_result=clinvar_result,
                    cached_source_results=cached_source_results,
                    species=species,
                    refresh=refresh,
                    warnings=warnings,
                )
            else:
                result = self._section_source_result(
                    source_id,
                    cache_key=cache_key,
                    variant=variant,
                    cached_source_results=cached_source_results,
                    species=species,
                    refresh=refresh,
                    warnings=warnings,
                )
            if source_id == "clinvar":
                variant.dbsnp_rsid = _extract_dbsnp_rsid(result.raw)
                if variant.dbsnp_rsid:
                    result.summary = {
                        **(result.summary or {}),
                        "dbsnp_rsid": variant.dbsnp_rsid,
                    }
                if not variant.protein_change:
                    variant.protein_change = str(result.summary.get("protein_change") or "")
                clinvar_result = result
            self._record_section_source_result(
                source_id,
                result,
                evidence=evidence,
                evidence_map=evidence_map,
                evidence_raw=evidence_raw,
                evidence_statuses=evidence_statuses,
                warnings=warnings,
            )

        report_payload.acmg_classification = _acmg_classification_snapshot(
            variant.gene,
            input_resolution.hgvs,
            evidence_map.get("clinvar", {}),
        )
        try:
            clinical_consensus = self.clinical_consensus.build_for_lookup(
                variant,
                report_payload,
                evidence_map,
                evidence_raw=evidence_raw,
                source_statuses=evidence_statuses,
                allow_live=False,
            )
            evidence_map["clinical_consensus"] = clinical_consensus.summary
            evidence_statuses["clinical_consensus"] = clinical_consensus.status
            warnings.extend(clinical_consensus.warnings)
        except Exception as exc:
            warnings.append(f"clinical_consensus_failed:{type(exc).__name__}")

        return self.report_orchestrator.build_profile(
            resolution=input_resolution,
            interpretation=None,
            payload=report_payload,
            evidence=evidence,
            evidence_map=evidence_map,
            evidence_statuses=evidence_statuses,
        )

    def _sections_from_source_specific_builders(
        self,
        request: LookupSectionFetchRequest,
        *,
        refresh: bool = False,
    ) -> LookupSectionFetchResponse | None:
        include = list(request.include)
        if any(section_id not in SOURCE_SPECIFIC_SECTION_IDS for section_id in include):
            return None
        if request.species != "human" or request.raw_search_text or request.selected_candidate_id:
            return None

        input_resolution = self.search_input_resolver.resolve(
            gene=request.gene or "",
            cdna=request.cdna or "",
            transcript=request.transcript,
            protein_change=request.protein_change,
        )
        if input_resolution.kind == "unknown":
            return None

        gene = input_resolution.gene
        cdna = input_resolution.hgvs
        cache_key = f"{gene}:{cdna}"
        cache_hit = None
        if (
            self.settings is not None
            and self.settings.use_real_apis
            and self.variant_cache_repo is not None
            and not refresh
        ):
            cache_hit = self.variant_cache_repo.get_fresh(cache_key, self.settings.cache_ttl_days)
        publication_cache = (
            cache_hit.get("publication_data", {}) if isinstance(cache_hit, dict) else {}
        )
        if not (
            isinstance(publication_cache, dict)
            and _publication_data_cache_is_current(publication_cache)
        ):
            publication_cache = {}

        variant = SimpleNamespace(
            gene=gene,
            transcript_hgvs=input_resolution.resolver_transcript_hgvs,
            protein_change=request.protein_change or input_resolution.protein_change or "",
            genomic_hg38=input_resolution.genomic_hg38 or "",
            genomic_hgvs=input_resolution.genomic_hgvs or "",
            variation_type="",
            consequence="",
            query_kind=input_resolution.kind,
            dbsnp_rsid=None,
            search_input_resolution=input_resolution,
        )
        evidence: list[EvidenceSourceSummary] = []
        evidence_map: dict[str, dict[str, Any]] = {}
        evidence_raw: dict[str, Any] = {}
        evidence_statuses: dict[str, str] = {}
        warnings: list[str] = list(input_resolution.warnings)

        report_payload = ReportPayload(
            patient_id=f"lookup_section_{uuid4().hex[:8]}",
            **_lookup_v2_modules(gene, cdna),
        )
        source_result_ids = _dedupe_values(
            [
                source_id
                for section_id in include
                for source_id in SOURCE_RESULT_SECTION_SOURCES.get(section_id, ())
            ]
        )
        cached_source_results = self._cached_report_source_results(
            cache_key,
            source_ids=source_result_ids,
            refresh=refresh,
        )
        profile_updates: dict[str, Any] = {}

        if "publications" in include:
            literature = self._build_publications_section_literature(
                variant,
                publication_cache=publication_cache,
                evidence=evidence,
                evidence_map=evidence_map,
                evidence_raw=evidence_raw,
                evidence_statuses=evidence_statuses,
                warnings=warnings,
                cache_key=cache_key,
                species=request.species,
                refresh=refresh,
            )
            report_payload.publications_literature = literature

        if "therapies_trials" in include:
            trials_section = self._build_trials_section(
                variant,
                evidence=evidence,
                warnings=warnings,
                cache_key=cache_key,
                species=request.species,
                cached_source_results=cached_source_results,
                refresh=refresh,
            )
            profile_updates["therapies_trials"] = trials_section

        if "computational_deep_dive" in include:
            computational_profile = self._build_computational_section_profile(
                cache_key=cache_key,
                variant=variant,
                input_resolution=input_resolution,
                report_payload=report_payload,
                cached_source_results=cached_source_results,
                evidence=evidence,
                evidence_map=evidence_map,
                evidence_raw=evidence_raw,
                evidence_statuses=evidence_statuses,
                warnings=warnings,
                species=request.species,
                refresh=refresh,
            )
            profile_updates["computational_deep_dive"] = (
                computational_profile.computational_deep_dive
            )

        if "clingen_vcep" in include:
            clingen_profile = self._build_clingen_vcep_section_profile(
                cache_key=cache_key,
                variant=variant,
                input_resolution=input_resolution,
                report_payload=report_payload,
                cached_source_results=cached_source_results,
                evidence=evidence,
                evidence_map=evidence_map,
                evidence_raw=evidence_raw,
                evidence_statuses=evidence_statuses,
                warnings=warnings,
                species=request.species,
                refresh=refresh,
            )
            profile_updates["acmg_worksheet"] = clingen_profile.acmg_worksheet
            profile_updates["expert_panel"] = clingen_profile.expert_panel

        if profile_updates:
            base_profile = report_payload.report_profile or VariantReportProfile()
            report_payload.report_profile = base_profile.model_copy(update=profile_updates)

        response = build_lookup_section_fetch_response(
            LookupResponse(
                query=cache_key,
                species=request.species,
                report_payload=report_payload,
                evidence=evidence,
                warnings=warnings,
            ),
            include,
        )
        try:
            self._store_section_response_cache(cache_key, publication_cache, response)
        except Exception as exc:
            response.warnings.append(f"report_sections_cache_write_failed:{type(exc).__name__}")
        return response

    def _build_publications_section_literature(
        self,
        variant,
        *,
        publication_cache: dict[str, Any],
        evidence: list[EvidenceSourceSummary],
        evidence_map: dict[str, dict[str, Any]],
        evidence_raw: dict[str, Any],
        evidence_statuses: dict[str, str],
        warnings: list[str],
        cache_key: str,
        species: str,
        refresh: bool,
    ) -> PublicationLiterature:
        cached_literature = publication_cache.get("ep_vlex")
        if not refresh and isinstance(cached_literature, dict):
            try:
                return PublicationLiterature.model_validate(cached_literature)
            except Exception:
                warnings.append("publication_section_cached_payload_invalid")

        for name in ("clinvar", "pubmed", "litvar2"):
            tool = self.tool_registry.get(name)
            if tool is None:
                warnings.append(f"publication_{name}_unavailable")
                continue
            try:
                if name == "pubmed":
                    result = tool.get_evidence(variant=variant, refresh=refresh)
                else:
                    result = tool.get_evidence(variant=variant)
            except Exception as exc:
                warnings.append(f"publication_{name}_failed:{type(exc).__name__}")
                continue
            evidence.append(_result_to_evidence(result))
            evidence_map[name] = result.summary or {}
            evidence_raw[name] = result.raw
            evidence_statuses[name] = result.status
            warnings.extend(result.warnings)
            try:
                self._store_report_source_result_cache(
                    cache_key,
                    variant=variant,
                    result=result,
                    species=species,
                )
            except Exception as exc:
                warnings.append(f"source_result_cache_write_failed:{name}:{type(exc).__name__}")
            if name == "clinvar":
                variant.dbsnp_rsid = _extract_dbsnp_rsid(result.raw)
                if not variant.protein_change:
                    variant.protein_change = str(result.summary.get("protein_change") or "")

        literature = self.publication_literature.build_for_lookup(
            variant,
            evidence_map,
            evidence_raw=evidence_raw,
            source_statuses=evidence_statuses,
            limit=5,
        )
        warnings.extend(literature.warnings)
        return literature

    def _build_trials_section(
        self,
        variant,
        *,
        evidence: list[EvidenceSourceSummary],
        warnings: list[str],
        cache_key: str,
        species: str,
        cached_source_results: dict[str, ToolResult] | None = None,
        refresh: bool = False,
    ) -> TherapiesTrialsSection:
        cached_result = None if refresh else (cached_source_results or {}).get("clinical_trials")
        tool = self.tool_registry.get("clinical_trials")
        if cached_result is None and (tool is None or not hasattr(tool, "get_trial_matches")):
            section_warning = "clinical_trials_unavailable"
            warnings.append(section_warning)
            return TherapiesTrialsSection(warnings=[section_warning])

        if cached_result is not None:
            result = cached_result
        else:
            try:
                result = tool.get_trial_matches(
                    variant=variant,
                    gene=variant.gene,
                    disease_terms=[],
                    limit=15,
                )
            except Exception as exc:
                result = ToolResult(
                    source="clinical_trials",
                    status="fallback",
                    request_identity={"gene": variant.gene},
                    summary={"warnings": [f"clinical_trials_fetch_failed:{type(exc).__name__}"]},
                    warnings=[f"clinical_trials_fetch_failed:{type(exc).__name__}"],
                    raw=None,
                )

        evidence.append(_result_to_evidence(result))
        warnings.extend(result.warnings)
        if cached_result is None:
            try:
                self._store_report_source_result_cache(
                    cache_key,
                    variant=variant,
                    result=result,
                    species=species,
                )
            except Exception as exc:
                warnings.append(
                    f"source_result_cache_write_failed:clinical_trials:{type(exc).__name__}"
                )
        summary = result.summary if isinstance(result.summary, dict) else {}
        source_fetched_at = _text_value(result.fetched_at) or _text_value(summary.get("fetched_at"))
        section_warnings = _dedupe_values(
            [
                *[str(item) for item in summary.get("warnings", []) if isinstance(item, str)],
                *result.warnings,
            ]
        )

        trial_rows: list[TrialMatch] = []
        raw_rows = summary.get("trial_rows", [])
        if isinstance(raw_rows, list):
            for item in raw_rows:
                if not isinstance(item, dict):
                    continue
                try:
                    row_payload = dict(item)
                    if source_fetched_at and not _text_value(row_payload.get("fetched_at")):
                        row_payload["fetched_at"] = source_fetched_at
                    trial_rows.append(TrialMatch.model_validate(row_payload))
                except Exception:
                    section_warnings.append("clinical_trials_row_validation_failed")

        query_executions: list[ClinicalTrialQueryExecution] = []
        raw_executions = summary.get("query_executions", [])
        if isinstance(raw_executions, list):
            for item in raw_executions:
                if not isinstance(item, dict):
                    continue
                try:
                    query_executions.append(ClinicalTrialQueryExecution.model_validate(item))
                except Exception:
                    section_warnings.append("clinical_trials_query_execution_validation_failed")

        if trial_rows:
            if any(row.match_level in {"gene_level", "disease_level"} for row in trial_rows):
                section_warnings.append("clinical_trials_gene_level_target_only")
        elif result.status in {
            "fixture",
            "missing",
        } and "clinical_trials_no_active_matches" not in (section_warnings):
            section_warnings.append("clinical_trials_structured_rows_unavailable")

        query_term = _text_value(summary.get("query_term"))
        source_url = _text_value(summary.get("source_url")) or result.source_url
        section_warnings = _dedupe_values(section_warnings)
        return TherapiesTrialsSection(
            trial_rows=trial_rows,
            query_executions=query_executions,
            warnings=section_warnings,
            provenance=[
                SourceProvenance(
                    source="ClinicalTrials.gov",
                    status=result.status,
                    query={"query": query_term} if query_term else {},
                    source_url=source_url,
                    warnings=section_warnings,
                    version=result.source_version,
                )
            ],
        )

    def lookup(
        self,
        request: LookupRequest,
        refresh: bool = False,
        *,
        _evidence_context_sink: list[LookupEvidenceContext] | None = None,
    ) -> LookupResponse:
        timing = (
            LookupTimingCollector(
                max_entries=int(
                    getattr(self.settings, "lookup_timing_diagnostics_max_entries", 80) or 80
                )
            )
            if bool(getattr(self.settings, "lookup_timing_diagnostics_enabled", False))
            else None
        )

        def timing_start() -> float:
            return timing.start() if timing is not None else 0.0

        def record_phase(
            name: str,
            started_at: float,
            *,
            outcome: str = "ok",
            metadata: dict[str, Any] | None = None,
        ) -> None:
            if timing is not None:
                timing.record_phase(name, started_at, outcome=outcome, metadata=metadata)

        search_interpretation: SearchInputInterpretation | None = None
        if request.selected_candidate_id:
            search_interpretation = self.search_input_interpreter.from_selected_candidate(
                request.selected_candidate_id
            )
            if not _interpretation_can_run(search_interpretation):
                return _interpretation_only_response(search_interpretation, request.species)
            request = _lookup_request_from_interpretation(request, search_interpretation)
        elif request.raw_search_text:
            search_interpretation = self.search_input_interpreter.interpret(
                request.raw_search_text,
                species=request.species,
                allow_ai=True,
            )
            if not _interpretation_can_run(search_interpretation):
                return _interpretation_only_response(search_interpretation, request.species)
            request = _lookup_request_from_interpretation(request, search_interpretation)

        gene_input = request.gene or ""
        cdna_input = request.cdna or ""
        phase_started = timing_start()
        input_resolution = self.search_input_resolver.resolve(
            gene=gene_input,
            cdna=cdna_input,
            transcript=request.transcript,
            protein_change=request.protein_change,
        )
        record_phase("input_resolution", phase_started)
        if search_interpretation is not None and search_interpretation.genomic_hg38:
            phase_started = timing_start()
            input_resolution = replace(
                input_resolution,
                genomic_hg38=search_interpretation.genomic_hg38,
                genomic_hgvs=search_interpretation.genomic_hgvs or input_resolution.genomic_hgvs,
                source_inputs=replace(
                    input_resolution.source_inputs,
                    gnomad=search_interpretation.genomic_hg38,
                    spliceai=search_interpretation.genomic_hg38,
                    clinvar=(
                        search_interpretation.genomic_hgvs or input_resolution.source_inputs.clinvar
                    ),
                ),
            )
            record_phase("search_interpretation_resolution", phase_started)
        gene = input_resolution.gene
        cdna = input_resolution.hgvs
        query_kind = input_resolution.kind

        if request.species == "mouse":
            msg = "Mouse (mm39) variant lookup is not yet implemented. Human (hg38) is fully supported."
            return LookupResponse(
                query=f"{gene}:{cdna}",
                species="mouse",
                report_payload=ReportPayload(
                    patient_id=f"lookup_mouse_{uuid4().hex[:8]}",
                    report_title=f"{gene} {cdna}",
                    limitations=msg,
                ),
                evidence=[],
                warnings=[msg],
            )

        transcript_hgvs = input_resolution.transcript_hgvs
        resolver_transcript_hgvs = input_resolution.resolver_transcript_hgvs

        # Synthetic variant object matching what tools expect
        variant = SimpleNamespace(
            gene=gene,
            transcript_hgvs=resolver_transcript_hgvs,
            protein_change=request.protein_change or "",
            genomic_hg38=input_resolution.genomic_hg38 or "",
            genomic_hgvs=input_resolution.genomic_hgvs or "",
            variation_type="",
            consequence="",
            query_kind=query_kind,
            dbsnp_rsid=None,
            search_input_resolution=input_resolution,
        )

        variant_row = VariantSummaryRow(
            gene=gene,
            transcript_hgvs=transcript_hgvs,
            protein_change=request.protein_change,
            genomic_hg38=None,
            variation_type=None,
            consequence=None,
        )

        variant_label = gene + " " + transcript_hgvs
        if request.protein_change:
            variant_label += f" ({request.protein_change})"

        # Run evidence tools
        evidence: list[EvidenceSourceSummary] = []
        evidence_map: dict[str, dict] = {}
        evidence_raw: dict[str, Any] = {}
        evidence_statuses: dict[str, str] = {}
        warnings: list[str] = []
        if query_kind == "unknown":
            warnings.append("input_unparseable:unknown")
        warnings.extend(input_resolution.warnings)

        cache_key = f"{gene}:{cdna}"
        source_key = source_cache_key(gene, cdna)
        source_cache_enabled = (
            self.settings is not None
            and self.settings.use_real_apis
            and self.source_cache_repo is not None
        )
        source_cache_hero_variant = is_hero_example_variant(gene, cdna)

        def source_cache_key_for(name: str) -> str | None:
            if not source_cache_enabled:
                return None
            if name == "clingen":
                return clingen_vcep_source_cache_key(
                    gene=gene,
                    transcript_hgvs=variant.transcript_hgvs,
                    cdna=cdna,
                    genomic_hgvs=variant.genomic_hgvs,
                    genomic_hg38=variant.genomic_hg38,
                    clinvar_summary=evidence_map.get("clinvar"),
                    clinvar_raw=evidence_raw.get("clinvar"),
                )
            if source_cache_hero_variant:
                return source_key
            if name not in SOURCE_CACHE_GENERAL_SOURCES:
                return None
            variant_id = _source_cache_token(variant.genomic_hg38)
            if not variant_id:
                return None
            dataset = str(getattr(self.tool_registry.get("gnomad"), "DATASET", "gnomad_r4"))
            return f"gnomad:{dataset}:{variant_id}"

        def should_persist_source_cache(name: str, result: ToolResult) -> bool:
            if result.status not in SOURCE_CACHE_PERSIST_STATUSES:
                return False
            if (
                not source_cache_hero_variant
                and name == "gnomad"
                and "gnomad_variant_not_found" in result.warnings
            ):
                return False
            if name == "clingen" and (
                "clingen_variant_not_found" in result.warnings
                or not (result.summary or {}).get("expert_panel")
            ):
                return False
            return True

        def source_cache_result_matches_request(name: str, result: ToolResult) -> bool:
            if name != "clingen":
                return True
            return cached_clingen_result_matches_variant(result, variant)

        def source_cached_result(name: str, producer) -> ToolResult:
            provider_started = timing_start()
            result_for_timing: ToolResult | None = None
            outcome = "producer"
            error_type: str | None = None
            allow_stale_on_exception = False
            try:
                source_cache_lookup_key = source_cache_key_for(name)
                use_source_cache = source_cache_lookup_key is not None
                skip_fresh_source_cache = (
                    name == "clingen"
                    and self.settings is not None
                    and self.settings.clingen_local_enabled
                )
                if use_source_cache and not refresh and not skip_fresh_source_cache:
                    hit = self.source_cache_repo.get_fresh(name, source_cache_lookup_key)
                    if hit is not None:
                        hit_result = hit.to_tool_result(status="cache", cache_status="cache_hit")
                        if source_cache_result_matches_request(name, hit_result):
                            outcome = "source_cache_fresh_hit"
                            result_for_timing = hit_result
                            return hit_result
                        warnings.append(f"source_cache_identity_mismatch:{name}")

                allow_stale_on_exception = True
                result = producer()
                allow_stale_on_exception = False
                result_for_timing = result
                if use_source_cache and result.status in SOURCE_CACHE_FAILURE_STATUSES:
                    stale = self.source_cache_repo.get_stale(name, source_cache_lookup_key)
                    if stale is not None:
                        stale_result = stale.to_tool_result(
                            status="stale",
                            cache_status="stale_on_failure",
                            extra_warnings=[
                                f"source_cache_stale_on_failure:{name}",
                                f"live_status:{result.status}",
                                *result.warnings,
                            ],
                        )
                        if source_cache_result_matches_request(name, stale_result):
                            outcome = "source_cache_stale_on_failure"
                            result_for_timing = stale_result
                            return stale_result
                        result.warnings.append(f"source_cache_identity_mismatch:{name}")

                if (
                    use_source_cache
                    and result.status != "local"
                    and should_persist_source_cache(name, result)
                ):
                    _annotate_source_cached_result(
                        name,
                        result,
                        cache_key=source_cache_lookup_key,
                    )
                    self.source_cache_repo.upsert(
                        result.source,
                        source_cache_lookup_key,
                        normalized_identity={
                            "query": source_cache_lookup_key,
                            "gene": gene,
                            "cdna": cdna,
                            "genomic_hg38": variant.genomic_hg38,
                            "genomic_hgvs": variant.genomic_hgvs,
                        },
                        request_identity=result.request_identity,
                        status=result.status,
                        summary=result.summary,
                        raw=result.raw,
                        warnings=result.warnings,
                        source_url=result.source_url,
                        ttl_days=self.settings.cache_ttl_days,
                        source_version=_source_version_from_result(result),
                    )
                    outcome = "producer_persisted"
                try:
                    self._store_report_source_result_cache(
                        cache_key,
                        variant=variant,
                        result=result,
                        species=request.species,
                    )
                except Exception:
                    pass
                return result
            except Exception as exc:
                error_type = type(exc).__name__
                if allow_stale_on_exception and "use_source_cache" in locals() and use_source_cache:
                    stale = self.source_cache_repo.get_stale(name, source_cache_lookup_key)
                    if stale is not None:
                        stale_result = stale.to_tool_result(
                            status="stale",
                            cache_status="stale_on_failure",
                            extra_warnings=[
                                f"source_cache_stale_on_failure:{name}",
                                f"live_fetch_failed:{type(exc).__name__}",
                            ],
                        )
                        if source_cache_result_matches_request(name, stale_result):
                            outcome = "source_cache_stale_on_exception"
                            result_for_timing = stale_result
                            return stale_result
                        warnings.append(f"source_cache_identity_mismatch:{name}")
                raise
            finally:
                if timing is not None:
                    timing.record_provider(
                        name,
                        provider_started,
                        status=result_for_timing.status if result_for_timing is not None else None,
                        cache_status=(
                            result_for_timing.cache_status
                            if result_for_timing is not None
                            else None
                        ),
                        outcome="error" if error_type and result_for_timing is None else outcome,
                        warning_count=(
                            len(result_for_timing.warnings) if result_for_timing is not None else 0
                        ),
                        error_type=error_type,
                    )

        cache_hit = None
        phase_started = timing_start()
        if (
            self.settings is not None
            and self.settings.use_real_apis
            and self.variant_cache_repo is not None
            and not refresh
        ):
            cache_hit = self.variant_cache_repo.get_fresh(cache_key, self.settings.cache_ttl_days)
        record_phase(
            "variant_cache_read",
            phase_started,
            metadata={"hit": isinstance(cache_hit, dict) and bool(cache_hit)},
        )
        publication_cache = (
            cache_hit.get("publication_data", {}) if isinstance(cache_hit, dict) else {}
        )
        rebuild_publication_cache = bool(
            publication_cache and not _publication_data_cache_is_current(publication_cache)
        )
        if rebuild_publication_cache:
            publication_cache = {}
        cached_report_source_results = self._cached_report_source_results(
            cache_key,
            source_ids=["clinical_trials"],
            refresh=refresh,
        )

        def record_result(name: str, result: ToolResult) -> None:
            evidence.append(_result_to_evidence(result))
            summary = dict(result.summary or {})
            if result.fetched_at and not _text_value(summary.get("fetched_at")):
                summary["fetched_at"] = result.fetched_at
            evidence_map[name] = summary
            evidence_raw[name] = result.raw
            evidence_statuses[name] = result.status
            warnings.extend(result.warnings)

        # Phase 1 resolves coordinates. VEP and VariantValidator may mutate the shared variant.
        phase_started = timing_start()
        cached_strict = (cache_hit or {}).get("strict_genomic_cache", {})
        if isinstance(cached_strict, dict) and cached_strict:
            if not _strict_genomic_cache_is_current(cached_strict):
                cached_strict = {}
        cached_evidence = (
            cached_strict.get("evidence", {}) if isinstance(cached_strict, dict) else {}
        )
        if cached_evidence:
            variant_cache = cached_strict.get("variant", {})
            variant.genomic_hg38 = variant_cache.get("genomic_hg38") or variant.genomic_hg38
            variant.genomic_hgvs = variant_cache.get("genomic_hgvs") or variant.genomic_hgvs
            variant.variation_type = variant_cache.get("variation_type") or variant.variation_type
            variant.consequence = variant_cache.get("consequence") or variant.consequence
            for name in ("vep", "variant_validator", *STRICT_GENOMIC_PLUGINS):
                item = cached_evidence.get(name)
                if item:
                    result = _evidence_summary_to_result(item)
                    result.status = "cache"
                    record_result(name, result)
        else:
            for name in ("vep", "variant_validator"):
                tool = self.tool_registry[name]
                result = source_cached_result(
                    name,
                    lambda tool=tool, name=name: (
                        tool.get_evidence(variant=variant, refresh=refresh)
                        if name == "pubmed"
                        else tool.get_evidence(variant=variant)
                    ),
                )
                if name == "vep":
                    variant.vep_raw = result.raw
                    consequence = (result.summary or {}).get("most_severe_consequence")
                    if consequence and not variant.consequence:
                        variant.consequence = consequence
                elif name == "variant_validator":
                    _hydrate_variant_from_source_result(variant, name, result)
                record_result(name, result)

            if not variant.genomic_hg38:
                warnings.append("no_genomic_resolution")

            # Phase 2 runs strict-genomic plugins after resolver mutation.
            for name in STRICT_GENOMIC_PLUGINS:
                tool = self.tool_registry[name]
                result = source_cached_result(
                    name,
                    lambda tool=tool: tool.get_evidence(variant=variant),
                )
                record_result(name, result)
        record_phase(
            "strict_genomic_sources",
            phase_started,
            metadata={"cached": bool(cached_evidence)},
        )

        # Phase 3 annotates with non-coordinate sources.
        phase_started = timing_start()
        for name in (
            "clinvar",
            "clingen",
            "gene_disease",
            "molecular_context",
            "computational_annotations",
            "pubmed",
        ):
            tool = self.tool_registry.get(name)
            if tool is None:
                continue
            if (
                name == "pubmed"
                and isinstance(publication_cache, dict)
                and isinstance(publication_cache.get("pubmed_summary"), dict)
                and not bool(self.settings and self.settings.pubmed_local_enabled)
            ):
                result = ToolResult(
                    source="pubmed",
                    status="cache",
                    request_identity=publication_cache.get("pubmed_request_identity", {}),
                    summary=publication_cache.get("pubmed_summary", {}),
                    warnings=[],
                    raw=publication_cache.get("pubmed_raw"),
                    source_url=publication_cache.get("pubmed_source_url"),
                )
            else:
                result = source_cached_result(
                    name,
                    lambda tool=tool, name=name: (
                        tool.get_evidence(variant=variant, refresh=refresh)
                        if name in {"clingen", "pubmed"}
                        else tool.get_evidence(variant=variant)
                    ),
                )
            if name == "clinvar":
                variant.dbsnp_rsid = _extract_dbsnp_rsid(result.raw)
                if variant.dbsnp_rsid:
                    result.summary = {
                        **(result.summary or {}),
                        "dbsnp_rsid": variant.dbsnp_rsid,
                    }
            record_result(name, result)
        record_phase("non_coordinate_sources", phase_started)

        phase_started = timing_start()
        if isinstance(publication_cache, dict) and publication_cache:
            litvar_summary = publication_cache.get("summary", {})
            litvar_result = ToolResult(
                source="litvar2",
                status="cache",
                request_identity=publication_cache.get("request_identity", {}),
                summary=litvar_summary,
                warnings=[],
                raw=publication_cache.get("raw"),
                source_url=publication_cache.get("source_url"),
            )
        else:
            litvar_tool = self.tool_registry["litvar2"]
            litvar_result = source_cached_result(
                "litvar2",
                lambda tool=litvar_tool: tool.get_evidence(variant=variant),
            )
        record_result("litvar2", litvar_result)
        record_phase(
            "litvar2_source",
            phase_started,
            metadata={"cached": isinstance(publication_cache, dict) and bool(publication_cache)},
        )

        variant_row.genomic_hg38 = variant.genomic_hg38 or None
        variant_row.variation_type = variant.variation_type or None
        variant_row.consequence = variant.consequence or None

        # Rules engine
        phase_started = timing_start()
        decision = self.rule_engine.evaluate(
            DecisionInput(
                case_title=f"{gene}:{cdna}",
                evidence=evidence_map,
                evidence_statuses=evidence_statuses,
                case_label=None,
                patient_context=None,
                clinical_findings=None,
                variant_summary=[variant_label],
            )
        )
        record_phase("rules_engine", phase_started)

        # Variant decoder
        variant_decoder_text = decode_variant(
            gene=gene,
            transcript_hgvs=transcript_hgvs,
            protein_change=request.protein_change,
        )

        # Therapeutic landscape — gene therapy map + clinical trials
        therapy_text = GENE_THERAPY_MAP.get(gene) or (
            f"No approved gene therapy identified for {gene}. "
            "Check ClinicalTrials.gov for active trials."
        )
        phase_started = timing_start()
        trials_tool = self.tool_registry.get("clinical_trials")
        cached_trials_result = cached_report_source_results.get("clinical_trials")
        if trials_tool is not None or cached_trials_result is not None:
            trial_rows: list[dict[str, Any]] = []
            trials_result: ToolResult | None = cached_trials_result
            if trials_tool is not None and hasattr(trials_tool, "get_trial_matches"):
                if trials_result is None:
                    trials_result = source_cached_result(
                        "clinical_trials",
                        lambda tool=trials_tool: tool.get_trial_matches(
                            variant=variant,
                            gene=gene,
                            disease_terms=_clinical_trial_disease_terms(evidence_map),
                            limit=15,
                        ),
                    )
            if trials_result is not None:
                record_result("clinical_trials", trials_result)
                trial_rows_raw = (
                    trials_result.summary.get("trial_rows", [])
                    if isinstance(trials_result.summary, dict)
                    else []
                )
                trial_rows = [row for row in trial_rows_raw if isinstance(row, dict)]
            if trial_rows:
                trials_text = _format_clinical_trials_summary(gene, trial_rows)
            elif trials_result is not None and trials_result.status != "fixture":
                trials_text = _clinical_trials_no_rows_summary(gene, trials_result)
            elif trials_tool is not None:
                trials_text = trials_tool.get_trials_summary(gene)
            else:
                trials_text = _clinical_trials_no_rows_summary(
                    gene,
                    ToolResult(
                        source="clinical_trials",
                        status="missing",
                        request_identity={"gene": gene},
                        summary={},
                        warnings=["clinical_trials_unavailable"],
                        raw=None,
                    ),
                )
            therapeutic_landscape = f"{therapy_text}\n\n{trials_text}"
        else:
            therapeutic_landscape = therapy_text
        record_phase(
            "clinical_trials",
            phase_started,
            metadata={"tool_present": trials_tool is not None},
        )

        # PubMed articles
        pubmed_raw = evidence_map.get("pubmed", {}).get("articles", [])
        pubmed_articles: list[PubMedArticle] = []
        for a in (pubmed_raw if isinstance(pubmed_raw, list) else []):
            if isinstance(a, dict):
                try:
                    pubmed_articles.append(PubMedArticle(**a))
                except Exception:
                    pass

        # Classification snapshot
        clinvar = evidence_map.get("clinvar", {})
        classification = clinvar.get("classification", "Unavailable")
        acmg_classification = _acmg_classification_snapshot(gene, cdna, clinvar)

        # Evidence snapshot
        lines = list(decision.evidence_lines)
        degraded = sorted(
            n.upper()
            for n, s in evidence_statuses.items()
            if s in {"fallback", "degraded", "error", "failed"}
        )
        if degraded:
            lines.append(f"Source quality note: {', '.join(degraded)} evidence was not fully live.")
        expanded_evidence = "\n".join(line for line in lines if line).strip() or None

        # Clinical integration (variant-level, no patient context for Layer 1)
        vep_data = evidence_map.get("vep", {})
        consequence = vep_data.get("most_severe_consequence", "")
        clinical_integration = (
            f'{variant_label}: {consequence or "consequence pending VEP annotation"}. '
            f"External classification: {classification}. "
            "Interpret in the context of the clinical phenotype and family history before drawing conclusions."
        )

        recommendations = (
            f"Confirm the reported variant {gene} {cdna} against the original sequencing data. "
            f"{decision.next_step} "
            "Seek specialist review before drawing clinical conclusions."
        )

        base_payload = ReportPayload(
            patient_id=f"lookup_{uuid4().hex[:8]}",
            case_label=None,
            report_title=f"{gene} {cdna}",
            source_filenames=[],
            patient_context=None,
            clinical_phenotype=None,
            ai_clinical_summary=decision.recommendation,
            variant_summary_rows=[variant_row],
            expanded_evidence=expanded_evidence,
            acmg_classification=acmg_classification,
            clinical_integration=clinical_integration,
            expected_symptoms=None,
            recommendations=recommendations,
            limitations=(
                "Variant lookup report presenting publicly available database information. "
                "No clinical recommendations are made. "
                "All data should be independently verified before clinical use."
            ),
            variant_decoder=variant_decoder_text,
            therapeutic_landscape=therapeutic_landscape,
            pubmed_articles=pubmed_articles,
            **_lookup_v2_modules(gene, cdna),
        )
        clinvar_distribution_warning = _clinvar_gene_distribution_exclusion_warning(self.settings)
        if clinvar_distribution_warning:
            base_payload.curated_variants_distribution = None
            warnings.append(clinvar_distribution_warning)
        else:
            try:
                base_payload.curated_variants_distribution = _local_clinvar_gene_distribution(
                    gene,
                    self.settings,
                    variant_id=variant.genomic_hg38 or None,
                )
            except ClinVarLocalError as exc:
                base_payload.curated_variants_distribution = None
                warnings.append(f"clinvar_local_gene_distribution_failed:{exc.code}")

        litvar_summary = evidence_map.get("litvar2", {})
        phase_started = timing_start()
        try:
            publication_literature = self.publication_literature.build_for_lookup(
                variant,
                evidence_map,
                evidence_raw=evidence_raw,
                source_statuses=evidence_statuses,
                limit=5,
            )
            base_payload.publications_literature = publication_literature
            base_payload.pubmed_articles = publication_literature.articles
            warnings.extend(publication_literature.warnings)
        except Exception as exc:
            warnings.append(f"publication_literature_failed:{type(exc).__name__}")
            base_payload.pubmed_articles = _merge_litvar_articles(pubmed_articles, litvar_summary)
        record_phase("publication_literature", phase_started)

        cached_functional_evidence = (
            publication_cache.get("functional_evidence")
            if isinstance(publication_cache, dict)
            else None
        )
        rebuild_functional_evidence_cache = (
            isinstance(publication_cache, dict)
            and isinstance(cached_functional_evidence, dict)
            and not _cached_functional_evidence_is_current(
                publication_cache,
                cached_functional_evidence,
            )
        )
        phase_started = timing_start()
        try:
            if (
                isinstance(cached_functional_evidence, dict)
                and not rebuild_functional_evidence_cache
            ):
                functional_evidence = FunctionalEvidenceSummary.model_validate(
                    cached_functional_evidence
                )
            else:
                functional_evidence = self.functional_evidence.build_for_lookup(
                    variant,
                    evidence_map,
                    evidence_raw=evidence_raw,
                    source_statuses=evidence_statuses,
                    allow_live=bool(self.settings is not None and self.settings.use_real_apis),
                )
            base_payload.functional_evidence = functional_evidence
            warnings.extend(functional_evidence.warnings)
        except Exception as exc:
            warnings.append(f"functional_evidence_failed:{type(exc).__name__}")
        record_phase(
            "functional_evidence",
            phase_started,
            metadata={
                "cached": isinstance(cached_functional_evidence, dict)
                and not rebuild_functional_evidence_cache
            },
        )

        phase_started = timing_start()
        try:
            clinical_consensus = self.clinical_consensus.build_for_lookup(
                variant,
                base_payload,
                evidence_map,
                evidence_raw=evidence_raw,
                source_statuses=evidence_statuses,
                allow_live=bool(self.settings is not None and self.settings.use_real_apis),
            )
            evidence_map["clinical_consensus"] = clinical_consensus.summary
            evidence_statuses["clinical_consensus"] = clinical_consensus.status
            warnings.extend(clinical_consensus.warnings)
        except Exception as exc:
            warnings.append(f"clinical_consensus_failed:{type(exc).__name__}")
        record_phase("clinical_consensus", phase_started)

        total_count = (
            base_payload.publications_literature.total_count
            if base_payload.publications_literature is not None
            else len(base_payload.pubmed_articles)
        )
        scholar_url = litvar_summary.get("scholar_url") or _scholar_url(gene, cdna)
        existing_callout = base_payload.publications_callout
        blurb = (
            existing_callout.blurb
            if existing_callout is not None and existing_callout.blurb
            else f"Variant-specific publications linked to {gene} {cdna} from LitVar2 and PubMed."
        )
        ai_summary_prompt = (
            existing_callout.ai_summary_prompt
            if existing_callout is not None
            else f"Summarise the key publications on {gene} {cdna} in plain language for a clinician."
        )
        base_payload.publications_callout = PublicationsCallout(
            total_count=total_count,
            scholar_url=scholar_url,
            blurb=blurb,
            ai_summary_prompt=ai_summary_prompt,
            scope_counts=(
                base_payload.publications_literature.scope_counts
                if base_payload.publications_literature is not None
                else None
            ),
        )
        gnomad_evidence = next((item for item in evidence if item.source == "gnomad"), None)
        gnomad_identity = dict(gnomad_evidence.request_identity) if gnomad_evidence else None
        if gnomad_identity is not None:
            if not gnomad_identity.get("variant_id"):
                gnomad_identity["variant_id"] = variant.genomic_hg38 or None
            if not gnomad_identity.get("dataset"):
                gnomad_identity["dataset"] = str(
                    getattr(self.tool_registry.get("gnomad"), "DATASET", "gnomad_r4")
                )
        base_payload.population_frequency_detail = build_population_frequency_detail(
            evidence_map.get("gnomad", {}),
            source_status=evidence_statuses.get("gnomad", ""),
            source_url=gnomad_evidence.source_url if gnomad_evidence is not None else None,
            source_warnings=gnomad_evidence.warnings if gnomad_evidence is not None else None,
            source_identity=gnomad_identity,
        )
        base_payload.call_cards = build_variant_report_call_cards(
            base_payload,
            evidence_map,
            evidence_statuses,
        )
        phase_started = timing_start()
        sequence_context_result = self.sequence_context.resolve(
            gene=gene,
            cdna=cdna,
            transcript=input_resolution.resolver_transcript,
            species=request.species,
        )
        if sequence_context_result.context is not None:
            evidence_map["sequence_context"] = sequence_context_result.context.model_dump(
                mode="json"
            )
            evidence_statuses["sequence_context"] = sequence_context_result.context.source
        elif sequence_context_result.warnings:
            evidence_map["sequence_context"] = {"warnings": list(sequence_context_result.warnings)}
            evidence_statuses["sequence_context"] = "missing"
        record_phase("sequence_context", phase_started)

        cached_gene_context = (
            (cache_hit or {}).get("gene_context_snapshot", {})
            if isinstance(cache_hit, dict)
            else {}
        )
        if not (
            isinstance(cached_gene_context, dict)
            and _gene_context_snapshot_cache_is_current(cached_gene_context)
        ):
            cached_gene_context = {}
        gene_context_snapshot_payload = (
            cached_gene_context.get("snapshot") if isinstance(cached_gene_context, dict) else None
        )
        rebuild_gene_context_snapshot_cache = not isinstance(
            gene_context_snapshot_payload,
            dict,
        )
        phase_started = timing_start()
        if isinstance(gene_context_snapshot_payload, dict):
            evidence_map["gene_context_snapshot"] = gene_context_snapshot_payload
            evidence_statuses["gene_context_snapshot"] = str(
                gene_context_snapshot_payload.get("source_status") or "cache"
            )
        else:
            gene_context_snapshot_payload = None
            try:
                gene_context_snapshot = self.gene_context_snapshot.build(
                    gene=gene,
                    cdna=cdna,
                    transcript=input_resolution.resolver_transcript,
                    species=request.species,
                )
                gene_context_snapshot_payload = gene_context_snapshot.model_dump(mode="json")
                evidence_map["gene_context_snapshot"] = gene_context_snapshot_payload
                evidence_statuses["gene_context_snapshot"] = gene_context_snapshot.source_status
            except Exception as exc:
                warnings.append(f"gene_context_snapshot_failed:{type(exc).__name__}")
        record_phase(
            "gene_context_snapshot",
            phase_started,
            metadata={
                "cached": isinstance(cached_gene_context, dict) and bool(cached_gene_context)
            },
        )
        if query_kind == "unknown":
            base_payload.limitations = (
                f"We could not parse '{cdna}' as cDNA, rsID, protein, or genomic HGVS. "
                "Check the variant syntax and retry."
            )

        gene_context_snapshot_cache = (
            {
                "gene_context_snapshot_cache_version": GENE_CONTEXT_SNAPSHOT_CACHE_VERSION,
                "snapshot": gene_context_snapshot_payload,
            }
            if gene_context_snapshot_payload is not None
            else None
        )
        should_upsert_variant_cache = (
            self.settings is not None
            and self.settings.use_real_apis
            and self.variant_cache_repo is not None
            and (
                not cached_evidence
                or rebuild_publication_cache
                or rebuild_functional_evidence_cache
            )
            and variant.genomic_hg38
        )
        should_update_gene_context_snapshot_cache = (
            self.settings is not None
            and self.settings.use_real_apis
            and self.variant_cache_repo is not None
            and not should_upsert_variant_cache
            and rebuild_gene_context_snapshot_cache
            and gene_context_snapshot_cache is not None
            and variant.genomic_hg38
        )
        phase_started = timing_start()
        if should_upsert_variant_cache:
            cached_names = ("vep", "variant_validator", *STRICT_GENOMIC_PLUGINS)
            evidence_by_source = {item.source: item.model_dump() for item in evidence}
            ep_vlex_cache = (
                base_payload.publications_literature.model_dump(mode="json")
                if base_payload.publications_literature is not None
                else None
            )
            self.variant_cache_repo.upsert(
                cache_key,
                litvar_id=litvar_summary.get("litvar_id"),
                total_publications=total_count,
                publication_data={
                    "publication_data_cache_version": PUBLICATION_DATA_CACHE_VERSION,
                    "request_identity": litvar_result.request_identity,
                    "summary": litvar_result.summary,
                    "raw": litvar_result.raw,
                    "source_url": litvar_result.source_url,
                    "pubmed_request_identity": evidence_by_source.get("pubmed", {}).get(
                        "request_identity", {}
                    ),
                    "pubmed_summary": evidence_map.get("pubmed", {}),
                    "pubmed_raw": evidence_raw.get("pubmed"),
                    "pubmed_source_url": evidence_by_source.get("pubmed", {}).get("source_url"),
                    "ep_vlex": ep_vlex_cache,
                    "functional_evidence_cache_version": FUNCTIONAL_EVIDENCE_CACHE_VERSION,
                    "functional_evidence": (
                        base_payload.functional_evidence.model_dump(mode="json")
                        if base_payload.functional_evidence is not None
                        else None
                    ),
                },
                strict_genomic_cache={
                    "strict_genomic_cache_version": STRICT_GENOMIC_CACHE_VERSION,
                    "variant": {
                        "genomic_hg38": variant.genomic_hg38,
                        "genomic_hgvs": variant.genomic_hgvs,
                        "variation_type": variant.variation_type,
                        "consequence": variant.consequence,
                    },
                    "evidence": {
                        name: evidence_by_source[name]
                        for name in cached_names
                        if name in evidence_by_source
                    },
                },
                gene_context_snapshot=gene_context_snapshot_cache or {},
            )
        elif should_update_gene_context_snapshot_cache:
            self.variant_cache_repo.update_gene_context_snapshot(
                cache_key,
                gene_context_snapshot=gene_context_snapshot_cache,
            )
        record_phase(
            "variant_cache_write",
            phase_started,
            metadata={
                "upsert": should_upsert_variant_cache,
                "gene_context_update": should_update_gene_context_snapshot_cache,
            },
        )

        phase_started = timing_start()
        if self.draft_render_service is not None:
            draft_payload, draft_warnings = self.draft_render_service.render(
                case_title=f"{gene}:{cdna}",
                patient_context=None,
                clinical_phenotype=None,
                variant_summary=variant_label,
                decision=decision,
                evidence_statuses=evidence_statuses,
                warnings=[*warnings, *decision.warnings],
                base_payload=base_payload,
            )
            base_payload.ai_clinical_summary = draft_payload.ai_clinical_summary
            base_payload.expanded_evidence = draft_payload.expanded_evidence
            base_payload.clinical_integration = draft_payload.clinical_integration
            base_payload.recommendations = draft_payload.recommendations
            base_payload.limitations = draft_payload.limitations
            warnings = [*warnings, *draft_warnings]
        record_phase(
            "draft_render",
            phase_started,
            metadata={"enabled": self.draft_render_service is not None},
        )

        phase_started = timing_start()
        report_generated_at = current_report_timestamp()
        base_payload.report_generated_at = report_generated_at
        base_payload.report_data_currency = build_report_data_currency(
            evidence,
            evidence_map,
            generated_at=report_generated_at,
        )
        base_payload.source_versions = build_source_version_pins(base_payload.report_data_currency)
        base_payload.report_profile = self.report_orchestrator.build_profile(
            resolution=input_resolution,
            interpretation=search_interpretation,
            payload=base_payload,
            evidence=evidence,
            evidence_map=evidence_map,
            evidence_statuses=evidence_statuses,
        )
        record_phase("report_profile", phase_started)
        phase_started = timing_start()
        try:
            base_payload.eamos_computed_classification = compute_report_acmg_classification(
                base_payload,
                evidence_map,
                evidence_statuses,
            )
        except Exception as exc:
            warnings.append(f"eamos_computed_classification_failed:{type(exc).__name__}")
        record_phase("eamos_computed_classification", phase_started)

        response = LookupResponse(
            query=f"{gene}:{cdna}",
            species=request.species,
            report_payload=base_payload,
            evidence=evidence,
            warnings=[*warnings, *decision.warnings],
            search_interpretation=search_interpretation,
        )
        try:
            self._store_report_shell_cache(cache_key, response)
        except Exception as exc:
            response.warnings.append(f"report_shell_cache_write_failed:{type(exc).__name__}")
        try:
            self._store_report_sections_cache(cache_key, response)
        except Exception as exc:
            response.warnings.append(f"report_sections_cache_write_failed:{type(exc).__name__}")
        if timing is not None:
            response.attach_lookup_timing_header(timing.header_value())
        if _evidence_context_sink is not None:
            _evidence_context_sink.append(
                LookupEvidenceContext(
                    evidence_map=dict(evidence_map),
                    evidence_statuses=dict(evidence_statuses),
                )
            )
        return response

    def page_publications(self, request: PublicationPageRequest) -> PublicationLiterature:
        input_resolution = self.search_input_resolver.resolve(
            gene=request.gene,
            cdna=request.cdna,
            transcript=request.transcript,
            protein_change=request.protein_change,
        )
        gene = input_resolution.gene
        query_kind = input_resolution.kind
        if request.species == "mouse":
            raise ValueError(
                "Mouse (mm39) publication lookup is not yet implemented. Human (hg38) is supported."
            )

        variant = SimpleNamespace(
            gene=gene,
            transcript_hgvs=input_resolution.resolver_transcript_hgvs,
            protein_change=request.protein_change or "",
            genomic_hg38=input_resolution.genomic_hg38 or "",
            genomic_hgvs=input_resolution.genomic_hgvs or "",
            variation_type="",
            consequence="",
            query_kind=query_kind,
            dbsnp_rsid=None,
            search_input_resolution=input_resolution,
        )
        evidence_map: dict[str, dict[str, Any]] = {}
        evidence_raw: dict[str, Any] = {}
        evidence_statuses: dict[str, str] = {}
        warnings: list[str] = list(input_resolution.warnings)

        for name in ("clinvar", "pubmed", "litvar2"):
            try:
                if name == "pubmed":
                    result = self.tool_registry[name].get_evidence(
                        variant=variant,
                        refresh=request.refresh,
                    )
                else:
                    result = self.tool_registry[name].get_evidence(variant=variant)
            except Exception as exc:
                warnings.append(f"publication_{name}_failed:{type(exc).__name__}")
                continue
            evidence_map[name] = result.summary or {}
            evidence_raw[name] = result.raw
            evidence_statuses[name] = result.status
            warnings.extend(result.warnings)
            if name == "clinvar":
                variant.dbsnp_rsid = _extract_dbsnp_rsid(result.raw)
                if not variant.protein_change:
                    variant.protein_change = str(result.summary.get("protein_change") or "")

        literature = self.publication_literature.build_for_lookup(
            variant,
            evidence_map,
            evidence_raw=evidence_raw,
            source_statuses=evidence_statuses,
            limit=request.limit,
            offset=request.offset,
            scope=request.scope,
        )
        literature.warnings.extend(warnings)
        return literature
