from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.rules.base import DecisionInput
from app.schemas.lookup import LookupRequest, LookupResponse
from app.schemas.run import (
    EvidenceSourceSummary,
    PubMedArticle,
    ReportPayload,
    VariantSummaryRow,
)
from app.services.variant_decoder import decode_variant

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


class LookupService:
    def __init__(self, tool_registry, rule_engine, draft_render_service=None) -> None:
        self.tool_registry = tool_registry
        self.rule_engine = rule_engine
        self.draft_render_service = draft_render_service

    def lookup(self, request: LookupRequest) -> LookupResponse:
        if request.species == "mouse":
            gene = request.gene.strip().upper()
            cdna = request.cdna.strip()
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

        gene = request.gene.strip().upper()
        cdna = request.cdna.strip()
        transcript_hgvs = f"{request.transcript}:{cdna}" if request.transcript else cdna

        # Synthetic variant object matching what tools expect
        variant = SimpleNamespace(
            gene=gene,
            transcript_hgvs=transcript_hgvs,
            protein_change=request.protein_change or "",
            genomic_hg38="",
            variation_type="",
            consequence="",
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

        for name in ('vep', 'spliceai', 'clinvar', 'franklin', 'gnomad', 'pubmed'):
            tool = self.tool_registry[name]
            result = tool.get_evidence(variant=variant)
            evidence.append(EvidenceSourceSummary(
                source=result.source,
                status=result.status,
                request_identity=result.request_identity,
                summary=result.summary,
                warnings=result.warnings,
            ))
            evidence_map[name] = result.summary or {}
            evidence_statuses[name] = result.status
            warnings.extend(result.warnings)

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
