from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote_plus
from uuid import uuid4

from app.rules.base import DecisionInput
from app.schemas.lookup import LookupRequest, LookupResponse
from app.schemas.run import (
    EvidenceSourceSummary,
    PublicationsCallout,
    PubMedArticle,
    ReportPayload,
    VariantSummaryRow,
)
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

CANONICAL_TRANSCRIPTS: dict[str, str] = {
    "RPE65": "NM_000329.3",
}


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


def normalize_variant_query(
    gene: str,
    cdna: str,
    transcript: str | None,
) -> tuple[str, str, str | None, str]:
    normalized_gene = gene.strip().upper()
    hgvs = re.sub(r"\s+", "", cdna.strip())
    normalized_transcript = transcript.strip() if transcript else None

    if ":" in hgvs:
        prefix, remainder = hgvs.split(":", 1)
        prefix_upper = prefix.upper()
        if prefix_upper == normalized_gene:
            hgvs = remainder
        elif prefix_upper.startswith(("NM_", "ENST")):
            normalized_transcript = prefix
            hgvs = remainder

    if re.match(r"^c\.", hgvs):
        kind = "cdna"
    elif re.match(r"^rs\d+$", hgvs, flags=re.IGNORECASE):
        kind = "rsid"
    elif re.match(r"^p\.", hgvs):
        kind = "protein"
    elif re.match(r"^(chr)?[\dXYM]+[:\-]", hgvs, flags=re.IGNORECASE) or re.match(
        r"^NC_\d+\.\d+:", hgvs
    ):
        kind = "genomic"
    else:
        kind = "unknown"

    return normalized_gene, hgvs, normalized_transcript, kind


class LookupService:
    def __init__(
        self,
        tool_registry,
        rule_engine,
        draft_render_service=None,
        variant_cache_repo=None,
        settings=None,
    ) -> None:
        self.tool_registry = tool_registry
        self.rule_engine = rule_engine
        self.draft_render_service = draft_render_service
        self.variant_cache_repo = variant_cache_repo
        self.settings = settings

    def lookup(self, request: LookupRequest, refresh: bool = False) -> LookupResponse:
        gene, cdna, transcript, query_kind = normalize_variant_query(
            request.gene,
            request.cdna,
            request.transcript,
        )

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

        transcript_hgvs = f"{transcript}:{cdna}" if transcript else cdna
        resolver_transcript = transcript
        if resolver_transcript is None and query_kind == "cdna":
            resolver_transcript = CANONICAL_TRANSCRIPTS.get(gene)
        resolver_transcript_hgvs = (
            f"{resolver_transcript}:{cdna}" if resolver_transcript else transcript_hgvs
        )

        # Synthetic variant object matching what tools expect
        variant = SimpleNamespace(
            gene=gene,
            transcript_hgvs=resolver_transcript_hgvs,
            protein_change=request.protein_change or "",
            genomic_hg38="",
            variation_type="",
            consequence="",
            query_kind=query_kind,
            dbsnp_rsid=None,
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
        evidence_statuses: dict[str, str] = {}
        warnings: list[str] = []
        if query_kind == "unknown":
            warnings.append("input_unparseable:unknown")

        cache_key = f"{gene}:{cdna}"
        cache_hit = None
        if (
            self.settings is not None
            and self.settings.use_real_apis
            and self.variant_cache_repo is not None
            and not refresh
        ):
            cache_hit = self.variant_cache_repo.get_fresh(cache_key, self.settings.cache_ttl_days)

        def record_result(name: str, result: ToolResult) -> None:
            evidence.append(_result_to_evidence(result))
            evidence_map[name] = result.summary or {}
            evidence_statuses[name] = result.status
            warnings.extend(result.warnings)

        # Phase 1 resolves coordinates. VEP and VariantValidator may mutate the shared variant.
        cached_strict = (cache_hit or {}).get("strict_genomic_cache", {})
        cached_evidence = cached_strict.get("evidence", {}) if isinstance(cached_strict, dict) else {}
        if cached_evidence:
            variant_cache = cached_strict.get("variant", {})
            variant.genomic_hg38 = variant_cache.get("genomic_hg38") or variant.genomic_hg38
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
                record_result(name, result)

            if not variant.genomic_hg38:
                warnings.append("no_genomic_resolution")

            # Phase 2 runs strict-genomic plugins after resolver mutation.
            for name in STRICT_GENOMIC_PLUGINS:
                tool = self.tool_registry[name]
                result = tool.get_evidence(variant=variant)
                record_result(name, result)

        # Phase 3 annotates with non-coordinate sources.
        for name in ("clinvar", "pubmed"):
            tool = self.tool_registry[name]
            result = tool.get_evidence(variant=variant)
            record_result(name, result)
            if name == "clinvar":
                variant.dbsnp_rsid = _extract_dbsnp_rsid(result.raw)

        if cache_hit and isinstance(cache_hit.get("publication_data"), dict):
            litvar_summary = cache_hit["publication_data"].get("summary", {})
            litvar_result = ToolResult(
                source="litvar2",
                status="cache",
                request_identity=cache_hit["publication_data"].get("request_identity", {}),
                summary=litvar_summary,
                warnings=[],
                raw=cache_hit["publication_data"].get("raw"),
                source_url=cache_hit["publication_data"].get("source_url"),
            )
        else:
            litvar_result = self.tool_registry["litvar2"].get_evidence(variant=variant)
        record_result("litvar2", litvar_result)

        variant_row.genomic_hg38 = variant.genomic_hg38 or None
        variant_row.variation_type = variant.variation_type or None
        variant_row.consequence = variant.consequence or None

        # Rules engine
        decision = self.rule_engine.evaluate(DecisionInput(
            case_title=f'{gene}:{cdna}',
            evidence=evidence_map,
            evidence_statuses=evidence_statuses,
            case_label=None,
            patient_context=None,
            clinical_findings=None,
            variant_summary=[variant_label],
        ))

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
        trials_tool = self.tool_registry.get('clinical_trials')
        if trials_tool is not None:
            trials_text = trials_tool.get_trials_summary(gene)
            therapeutic_landscape = f"{therapy_text}\n\n{trials_text}"
        else:
            therapeutic_landscape = therapy_text

        # PubMed articles
        pubmed_raw = evidence_map.get('pubmed', {}).get('articles', [])
        pubmed_articles: list[PubMedArticle] = []
        for a in (pubmed_raw if isinstance(pubmed_raw, list) else []):
            if isinstance(a, dict):
                try:
                    pubmed_articles.append(PubMedArticle(**a))
                except Exception:
                    pass

        # Classification snapshot
        clinvar = evidence_map.get('clinvar', {})
        classification = clinvar.get('classification', 'Unavailable')
        review_status_text = clinvar.get('review_status', 'review status unavailable')
        acmg_classification = (
            f'ClinVar currently lists {gene} {cdna} as {classification} ({review_status_text}). '
            'This is a source snapshot only and should not be read as formal ACMG evidence-code '
            'assignment or a final laboratory classification.'
        )

        # Evidence snapshot
        lines = list(decision.evidence_lines)
        degraded = sorted(n.upper() for n, s in evidence_statuses.items() if s in {'fallback', 'degraded', 'error', 'failed'})
        if degraded:
            lines.append(f"Source quality note: {', '.join(degraded)} evidence was not fully live.")
        expanded_evidence = '\n'.join(line for line in lines if line).strip() or None

        # Clinical integration (variant-level, no patient context for Layer 1)
        vep_data = evidence_map.get('vep', {})
        consequence = vep_data.get('most_severe_consequence', '')
        clinical_integration = (
            f'{variant_label}: {consequence or "consequence pending VEP annotation"}. '
            f'External classification: {classification}. '
            'Interpret in the context of the clinical phenotype and family history before drawing conclusions.'
        )

        recommendations = (
            f'Confirm the reported variant {gene} {cdna} against the original sequencing data. '
            f'{decision.next_step} '
            'Seek specialist review before drawing clinical conclusions.'
        )

        base_payload = ReportPayload(
            patient_id=f'lookup_{uuid4().hex[:8]}',
            case_label=None,
            report_title=f'{gene} {cdna}',
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
                'Variant lookup report presenting publicly available database information. '
                'No clinical recommendations are made. '
                'All data should be independently verified before clinical use.'
            ),
            variant_decoder=variant_decoder_text,
            therapeutic_landscape=therapeutic_landscape,
            pubmed_articles=pubmed_articles,
            **_lookup_v2_modules(gene, cdna),
        )

        litvar_summary = evidence_map.get("litvar2", {})
        base_payload.pubmed_articles = _merge_litvar_articles(pubmed_articles, litvar_summary)
        litvar_count = litvar_summary.get("total_publications")
        litvar_int = (
            int(litvar_count)
            if isinstance(litvar_count, int | float | str) and str(litvar_count).isdigit()
            else 0
        )
        # Prefer LitVar2's authoritative total when it has data; when LitVar2 has
        # no entry for the variant (legitimately 0) fall back to the merged
        # article count so the callout never contradicts the articles shown.
        total_count = litvar_int if litvar_int > 0 else len(base_payload.pubmed_articles)
        scholar_url = litvar_summary.get("scholar_url") or _scholar_url(gene, cdna)
        existing_callout = base_payload.publications_callout
        blurb = (
            existing_callout.blurb
            if existing_callout is not None and existing_callout.blurb
            else f"Publications linked to {gene} {cdna} from LitVar2 and PubMed."
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
            self.variant_cache_repo.upsert(
                cache_key,
                litvar_id=litvar_summary.get("litvar_id"),
                total_publications=total_count,
                publication_data={
                    "request_identity": litvar_result.request_identity,
                    "summary": litvar_result.summary,
                    "raw": litvar_result.raw,
                    "source_url": litvar_result.source_url,
                },
                strict_genomic_cache={
                    "variant": {
                        "genomic_hg38": variant.genomic_hg38,
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
                case_title=f'{gene}:{cdna}',
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

        return LookupResponse(
            query=f'{gene}:{cdna}',
            species=request.species,
            report_payload=base_payload,
            evidence=evidence,
            warnings=[*warnings, *decision.warnings],
        )
