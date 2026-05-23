from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote_plus
from uuid import uuid4

from app.rules.base import DecisionInput
from app.schemas.lookup import (
    LookupRequest,
    LookupResponse,
    PublicationPageRequest,
    SearchInputInterpretation,
    SearchInputParseRequest,
    SearchInputParseResponse,
)
from app.schemas.run import (
    EvidenceSourceSummary,
    FunctionalEvidenceSummary,
    PublicationLiterature,
    PublicationsCallout,
    PubMedArticle,
    ReportPayload,
    VariantSummaryRow,
)
from app.services.clinical_consensus import ClinicalConsensusBuilder
from app.services.functional_evidence import FunctionalEvidenceExtractor
from app.services.publication_literature import EamosProprietaryVariantLiteratureExtractor
from app.services.report_call_cards import (
    build_population_frequency_detail,
    build_variant_report_call_cards,
)
from app.services.sequence_context import SequenceContextService
from app.services.search_input_interpreter import SearchInputInterpreter
from app.services.search_input_resolver import EamosSearchInputResolver
from app.services.variant_report_orchestrator import VariantReportDataOrchestrator
from app.services.variant_decoder import decode_variant
from app.tools.base import ToolResult
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
        "No approved gene therapy. Phase I/II trial active (4D-150, subretinal AAV delivery) for Stargardt disease. "
        "Check ClinicalTrials.gov for current recruitment status."
    ),
}


def _format_clinical_trials_summary(gene: str, rows: list[dict[str, Any]]) -> str:
    lines = [f"{len(rows)} active/not-yet ClinicalTrials.gov record(s) found for {gene}:"]
    for row in rows:
        nct_id = str(row.get("nct_id") or "NCT unavailable")
        phase = str(row.get("phase") or "Phase N/A")
        status = str(row.get("status") or "Unknown")
        title = str(row.get("title") or "Untitled clinical trial")
        lines.append(f"- {nct_id} - {phase} - {status} - {title}")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _lookup_v2_modules_fixture() -> dict:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "lookup_v2_modules.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _lookup_v2_modules(gene: str, cdna: str) -> dict:
    return _lookup_v2_modules_fixture().get(gene, {}).get(cdna, {})


def _result_to_evidence(result: ToolResult) -> EvidenceSourceSummary:
    return EvidenceSourceSummary(
        source=result.source,
        status=result.status,
        request_identity=result.request_identity,
        summary=result.summary,
        warnings=result.warnings,
        source_url=result.source_url,
    )


def _evidence_summary_to_result(item: dict[str, Any]) -> ToolResult:
    return ToolResult(
        source=item.get("source", ""),
        status=item.get("status", "cache"),
        request_identity=item.get("request_identity", {}),
        summary=item.get("summary", {}),
        warnings=item.get("warnings", []),
        raw=item.get("raw"),
        source_url=item.get("source_url"),
    )


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
        settings=None,
        functional_evidence_extractor=None,
        clinical_consensus_builder=None,
    ) -> None:
        self.tool_registry = tool_registry
        self.rule_engine = rule_engine
        self.draft_render_service = draft_render_service
        self.variant_cache_repo = variant_cache_repo
        self.settings = settings
        self.publication_literature = EamosProprietaryVariantLiteratureExtractor()
        self.functional_evidence = functional_evidence_extractor or FunctionalEvidenceExtractor(
            settings=settings
        )
        self.clinical_consensus = clinical_consensus_builder or ClinicalConsensusBuilder(
            settings=settings
        )
        self.search_input_resolver = EamosSearchInputResolver(settings=settings)
        self.search_input_interpreter = SearchInputInterpreter(settings=settings)
        self.sequence_context = SequenceContextService(settings=settings)
        self.report_orchestrator = VariantReportDataOrchestrator()

    def parse_search_input(self, request: SearchInputParseRequest) -> SearchInputParseResponse:
        return SearchInputParseResponse(
            interpretation=self.search_input_interpreter.interpret(
                request.search_text,
                species=request.species,
                allow_ai=request.allow_ai,
                resolve_coordinates=request.resolve_coordinates,
            )
        )

    def lookup(self, request: LookupRequest, refresh: bool = False) -> LookupResponse:
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
        input_resolution = self.search_input_resolver.resolve(
            gene=gene_input,
            cdna=cdna_input,
            transcript=request.transcript,
            protein_change=request.protein_change,
        )
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

        def record_result(name: str, result: ToolResult) -> None:
            evidence.append(_result_to_evidence(result))
            evidence_map[name] = result.summary or {}
            evidence_raw[name] = result.raw
            evidence_statuses[name] = result.status
            warnings.extend(result.warnings)

        # Phase 1 resolves coordinates. VEP and VariantValidator may mutate the shared variant.
        cached_strict = (cache_hit or {}).get("strict_genomic_cache", {})
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
                result = tool.get_evidence(variant=variant)
                if name == "vep":
                    variant.vep_raw = result.raw
                    consequence = (result.summary or {}).get("most_severe_consequence")
                    if consequence and not variant.consequence:
                        variant.consequence = consequence
                record_result(name, result)

            if not variant.genomic_hg38:
                warnings.append("no_genomic_resolution")

            # Phase 2 runs strict-genomic plugins after resolver mutation.
            for name in STRICT_GENOMIC_PLUGINS:
                tool = self.tool_registry[name]
                result = tool.get_evidence(variant=variant)
                record_result(name, result)

        # Phase 3 annotates with non-coordinate sources.
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
                result = tool.get_evidence(variant=variant)
            record_result(name, result)
            if name == "clinvar":
                variant.dbsnp_rsid = _extract_dbsnp_rsid(result.raw)

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
            litvar_result = self.tool_registry["litvar2"].get_evidence(variant=variant)
        record_result("litvar2", litvar_result)

        variant_row.genomic_hg38 = variant.genomic_hg38 or None
        variant_row.variation_type = variant.variation_type or None
        variant_row.consequence = variant.consequence or None

        # Rules engine
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
        trials_tool = self.tool_registry.get("clinical_trials")
        if trials_tool is not None:
            trial_rows: list[dict[str, Any]] = []
            if hasattr(trials_tool, "get_trial_matches"):
                trials_result = trials_tool.get_trial_matches(variant=variant, gene=gene, limit=15)
                record_result("clinical_trials", trials_result)
                trial_rows_raw = (
                    trials_result.summary.get("trial_rows", [])
                    if isinstance(trials_result.summary, dict)
                    else []
                )
                trial_rows = [row for row in trial_rows_raw if isinstance(row, dict)]
            if trial_rows:
                trials_text = _format_clinical_trials_summary(gene, trial_rows)
            else:
                trials_text = trials_tool.get_trials_summary(gene)
            therapeutic_landscape = f"{therapy_text}\n\n{trials_text}"
        else:
            therapeutic_landscape = therapy_text

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
        review_status_text = clinvar.get("review_status", "review status unavailable")
        acmg_classification = (
            f"ClinVar currently lists {gene} {cdna} as {classification} ({review_status_text}). "
            "This is a source snapshot only and should not be read as formal ACMG evidence-code "
            "assignment or a final laboratory classification."
        )

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

        litvar_summary = evidence_map.get("litvar2", {})
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

        cached_functional_evidence = (
            publication_cache.get("functional_evidence")
            if isinstance(publication_cache, dict)
            else None
        )
        try:
            if isinstance(cached_functional_evidence, dict):
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
        )
        gnomad_evidence = next((item for item in evidence if item.source == "gnomad"), None)
        base_payload.population_frequency_detail = build_population_frequency_detail(
            evidence_map.get("gnomad", {}),
            source_status=evidence_statuses.get("gnomad", ""),
            source_url=gnomad_evidence.source_url if gnomad_evidence is not None else None,
            source_warnings=gnomad_evidence.warnings if gnomad_evidence is not None else None,
        )
        base_payload.call_cards = build_variant_report_call_cards(
            base_payload,
            evidence_map,
            evidence_statuses,
        )
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
        if query_kind == "unknown":
            base_payload.limitations = (
                f"We could not parse '{cdna}' as cDNA, rsID, protein, or genomic HGVS. "
                "Check the variant syntax and retry."
            )

        if (
            self.settings is not None
            and self.settings.use_real_apis
            and self.variant_cache_repo is not None
            and not cached_evidence
            and variant.genomic_hg38
        ):
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
                    "functional_evidence": (
                        base_payload.functional_evidence.model_dump(mode="json")
                        if base_payload.functional_evidence is not None
                        else None
                    ),
                },
                strict_genomic_cache={
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
            )

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

        base_payload.report_profile = self.report_orchestrator.build_profile(
            resolution=input_resolution,
            interpretation=search_interpretation,
            payload=base_payload,
            evidence=evidence,
            evidence_map=evidence_map,
            evidence_statuses=evidence_statuses,
        )

        return LookupResponse(
            query=f"{gene}:{cdna}",
            species=request.species,
            report_payload=base_payload,
            evidence=evidence,
            warnings=[*warnings, *decision.warnings],
            search_interpretation=search_interpretation,
        )

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
        )
        literature.warnings.extend(warnings)
        return literature
