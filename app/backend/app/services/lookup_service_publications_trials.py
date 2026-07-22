from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus

from app.schemas.run import (
    ClinicalTrialQueryExecution,
    EvidenceSourceSummary,
    PublicationLiterature,
    PublicationsCallout,
    PubMedArticle,
    ReportPayload,
    SourceProvenance,
    TherapiesTrialsSection,
    TrialMatch,
)
from app.services.lookup_service_cache import result_to_evidence
from app.services.lookup_service_utils import dedupe_values, text_value
from app.services.report_source_truth import report_source_is_weak
from app.tools.base import ToolResult

GENE_THERAPY_MAP: dict[str, str] = {
    gene: (
        f"No source-backed regulatory therapy record was evaluated for {gene}. "
        "ClinicalTrials.gov discovery results must be reviewed separately."
    )
    for gene in ("RPE65", "RPGR", "CNGA3", "CNGB3", "ABCA4")
}

SourceCachedResult = Callable[[str, Callable[[], ToolResult]], ToolResult]
RecordResult = Callable[[str, ToolResult], None]


@dataclass(frozen=True)
class TherapeuticLandscapeResult:
    text: str
    clinical_trials_tool_present: bool


def format_clinical_trials_summary(gene: str, rows: list[dict[str, Any]]) -> str:
    lines = [f"{len(rows)} active/not-yet ClinicalTrials.gov record(s) found for {gene}:"]
    for row in rows:
        nct_id = str(row.get("nct_id") or "NCT unavailable")
        phase = str(row.get("phase") or "Phase N/A")
        status = str(row.get("status") or "Unknown")
        title = str(row.get("title") or "Untitled clinical trial")
        lines.append(f"- {nct_id} - {phase} - {status} - {title}")
    return "\n".join(lines)


def clinical_trials_no_rows_summary(gene: str, result: ToolResult) -> str:
    summary = result.summary if isinstance(result.summary, dict) else {}
    warnings = [
        *[str(item) for item in summary.get("warnings", []) if isinstance(item, str)],
        *result.warnings,
    ]
    if "clinical_trials_no_active_matches" in warnings:
        return f"No active trials found for {gene} on ClinicalTrials.gov."
    if report_source_is_weak(result.status) or any(
        warning.startswith("clinical_trials_fetch_failed") for warning in warnings
    ):
        return f"Clinical trials lookup unavailable for {gene}. Check ClinicalTrials.gov directly."
    return "No structured ClinicalTrials.gov rows are available for this lookup."


def clinical_trial_disease_terms(evidence_map: dict[str, dict[str, Any]]) -> list[str]:
    gene_disease = evidence_map.get("gene_disease", {})
    terms: list[str] = []
    primary = text_value(gene_disease.get("primary_condition"))
    if primary:
        terms.append(primary)
    conditions = gene_disease.get("conditions")
    if isinstance(conditions, list):
        for condition in conditions:
            if not isinstance(condition, dict):
                continue
            name = text_value(condition.get("name"))
            if name:
                terms.append(name)
    return dedupe_values(terms)


def scholar_url(gene: str, cdna: str) -> str:
    return f"https://scholar.google.com/scholar?q={quote_plus(f'{gene} {cdna}')}"


def merge_litvar_articles(
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


def extract_dbsnp_rsid(clinvar_raw: Any) -> str | None:
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


def pubmed_articles_from_evidence_map(
    evidence_map: dict[str, dict[str, Any]],
) -> list[PubMedArticle]:
    pubmed_raw = evidence_map.get("pubmed", {}).get("articles", [])
    articles: list[PubMedArticle] = []
    for item in pubmed_raw if isinstance(pubmed_raw, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            articles.append(PubMedArticle(**item))
        except Exception:
            pass
    return articles


def build_publications_section_literature(
    variant: Any,
    *,
    publication_cache: dict[str, Any],
    tool_registry: dict[str, Any],
    publication_literature: Any,
    report_source_result_cache_writer: Callable[..., None],
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
        tool = tool_registry.get(name)
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
        evidence.append(result_to_evidence(result))
        evidence_map[name] = result.summary or {}
        evidence_raw[name] = result.raw
        evidence_statuses[name] = result.status
        warnings.extend(result.warnings)
        try:
            report_source_result_cache_writer(
                cache_key,
                variant=variant,
                result=result,
                species=species,
            )
        except Exception as exc:
            warnings.append(f"source_result_cache_write_failed:{name}:{type(exc).__name__}")
        if name == "clinvar":
            variant.dbsnp_rsid = extract_dbsnp_rsid(result.raw)
            if not variant.protein_change:
                variant.protein_change = str(result.summary.get("protein_change") or "")

    literature = publication_literature.build_for_lookup(
        variant,
        evidence_map,
        evidence_raw=evidence_raw,
        source_statuses=evidence_statuses,
        limit=5,
    )
    warnings.extend(literature.warnings)
    return literature


def build_trials_section(
    variant: Any,
    *,
    tool_registry: dict[str, Any],
    report_source_result_cache_writer: Callable[..., None],
    evidence: list[EvidenceSourceSummary],
    warnings: list[str],
    cache_key: str,
    species: str,
    cached_source_results: dict[str, ToolResult] | None = None,
    refresh: bool = False,
) -> TherapiesTrialsSection:
    cached_result = None if refresh else (cached_source_results or {}).get("clinical_trials")
    tool = tool_registry.get("clinical_trials")
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

    evidence.append(result_to_evidence(result))
    warnings.extend(result.warnings)
    if cached_result is None:
        try:
            report_source_result_cache_writer(
                cache_key,
                variant=variant,
                result=result,
                species=species,
            )
        except Exception as exc:
            warnings.append(
                f"source_result_cache_write_failed:clinical_trials:{type(exc).__name__}"
            )
    return trials_section_from_result(result)


def trials_section_from_result(result: ToolResult) -> TherapiesTrialsSection:
    summary = result.summary if isinstance(result.summary, dict) else {}
    source_fetched_at = text_value(result.fetched_at) or text_value(summary.get("fetched_at"))
    section_warnings = dedupe_values(
        [
            *[str(item) for item in summary.get("warnings", []) if isinstance(item, str)],
            *result.warnings,
        ]
    )
    if report_source_is_weak(result.status):
        section_warnings = dedupe_values([*section_warnings, "clinical_trials_source_unavailable"])
        return TherapiesTrialsSection(
            warnings=section_warnings,
            provenance=[
                SourceProvenance(
                    source="ClinicalTrials.gov",
                    status=result.status,
                    query={},
                    source_url=result.source_url,
                    warnings=section_warnings,
                    version=result.source_version,
                )
            ],
        )

    trial_rows: list[TrialMatch] = []
    raw_rows = summary.get("trial_rows", [])
    if isinstance(raw_rows, list):
        for item in raw_rows:
            if not isinstance(item, dict):
                continue
            try:
                row_payload = dict(item)
                if source_fetched_at and not text_value(row_payload.get("fetched_at")):
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
    elif (
        result.status
        in {
            "fixture",
            "missing",
        }
        and "clinical_trials_no_active_matches" not in section_warnings
    ):
        section_warnings.append("clinical_trials_structured_rows_unavailable")

    query_term = text_value(summary.get("query_term"))
    source_url = text_value(summary.get("source_url")) or result.source_url
    section_warnings = dedupe_values(section_warnings)
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


def build_therapeutic_landscape(
    *,
    gene: str,
    variant: Any,
    evidence_map: dict[str, dict[str, Any]],
    tool_registry: dict[str, Any],
    cached_report_source_results: dict[str, ToolResult],
    source_cached_result: SourceCachedResult,
    record_result: RecordResult,
) -> TherapeuticLandscapeResult:
    therapy_text = (
        f"No source-backed regulatory therapy record was evaluated for {gene}. "
        "ClinicalTrials.gov discovery results, when available, are listed separately below."
    )
    trials_tool = tool_registry.get("clinical_trials")
    cached_trials_result = cached_report_source_results.get("clinical_trials")
    if trials_tool is None and cached_trials_result is None:
        return TherapeuticLandscapeResult(
            text=therapy_text,
            clinical_trials_tool_present=False,
        )

    trial_rows: list[dict[str, Any]] = []
    trials_result: ToolResult | None = cached_trials_result
    if trials_tool is not None and hasattr(trials_tool, "get_trial_matches"):
        if trials_result is None:
            trials_result = source_cached_result(
                "clinical_trials",
                lambda tool=trials_tool: tool.get_trial_matches(
                    variant=variant,
                    gene=gene,
                    disease_terms=clinical_trial_disease_terms(evidence_map),
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
        trial_rows = (
            [row for row in trial_rows_raw if isinstance(row, dict)]
            if not report_source_is_weak(trials_result.status)
            else []
        )
    if trial_rows:
        trials_text = format_clinical_trials_summary(gene, trial_rows)
    elif trials_result is not None and trials_result.status != "fixture":
        trials_text = clinical_trials_no_rows_summary(gene, trials_result)
    elif trials_tool is not None:
        trials_text = trials_tool.get_trials_summary(gene)
    else:
        trials_text = clinical_trials_no_rows_summary(
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

    return TherapeuticLandscapeResult(
        text=f"{therapy_text}\n\n{trials_text}",
        clinical_trials_tool_present=trials_tool is not None,
    )


def build_lookup_publication_literature(
    *,
    publication_literature: Any,
    variant: Any,
    evidence_map: dict[str, dict[str, Any]],
    evidence_raw: dict[str, Any],
    evidence_statuses: dict[str, str],
    warnings: list[str],
) -> PublicationLiterature | None:
    try:
        literature = publication_literature.build_for_lookup(
            variant,
            evidence_map,
            evidence_raw=evidence_raw,
            source_statuses=evidence_statuses,
            limit=5,
        )
        warnings.extend(literature.warnings)
        return literature
    except Exception as exc:
        warnings.append(f"publication_literature_failed:{type(exc).__name__}")
        return None


def build_publications_callout(
    *,
    payload: ReportPayload,
    litvar_summary: dict[str, Any],
    gene: str,
    cdna: str,
) -> PublicationsCallout:
    total_count = (
        payload.publications_literature.total_count
        if payload.publications_literature is not None
        else len(payload.pubmed_articles)
    )
    existing_callout = payload.publications_callout
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
    return PublicationsCallout(
        total_count=total_count,
        scholar_url=litvar_summary.get("scholar_url") or scholar_url(gene, cdna),
        blurb=blurb,
        ai_summary_prompt=ai_summary_prompt,
        scope_counts=(
            payload.publications_literature.scope_counts
            if payload.publications_literature is not None
            else None
        ),
    )
