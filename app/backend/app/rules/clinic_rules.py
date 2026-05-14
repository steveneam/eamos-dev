from __future__ import annotations

from app.rules.base import DecisionInput, DecisionOutput


class ClinicRules:
    def evaluate(self, payload: DecisionInput) -> DecisionOutput:
        clinvar = payload.evidence.get('clinvar', {})
        vep = payload.evidence.get('vep', {})
        spliceai = payload.evidence.get('spliceai', {})
        gnomad = payload.evidence.get('gnomad', {})

        subject = 'The patient'
        variant_summary = payload.variant_summary[0] if payload.variant_summary else payload.case_title
        clinical_context = payload.clinical_findings or payload.patient_context or 'the reported clinical context'
        max_splice = max(
            float(spliceai.get('acceptor_loss', 0.0) or 0.0),
            float(spliceai.get('donor_loss', 0.0) or 0.0),
            float(spliceai.get('acceptor_gain', 0.0) or 0.0),
            float(spliceai.get('donor_gain', 0.0) or 0.0),
        )
        if max_splice >= 0.5:
            splice_interpretation = 'scores fall in a range that can support a splice impact and should be reviewed clinically.'
        elif max_splice >= 0.2:
            splice_interpretation = 'scores suggest a possible splice effect, but the signal is not definitive on its own.'
        else:
            splice_interpretation = 'scores do not show a strong predicted splice-disruption signal.'

        gnomad_af = gnomad.get('allele_frequency')
        if gnomad_af is not None:
            af_str = f"{gnomad_af:.2e}" if gnomad_af < 0.001 else f"{gnomad_af:.4f}"
            hom = gnomad.get('homozygote_count', 'N/A')
            popmax = gnomad.get('popmax_frequency')
            popmax_str = (
                f", popmax {gnomad.get('popmax_population', '')} {popmax:.2e}"
                if popmax is not None else ""
            )
            gnomad_line = (
                f"gnomAD v4 allele frequency: {af_str} "
                f"(AC {gnomad.get('allele_count', 'N/A')}, "
                f"AN {gnomad.get('allele_number', 'N/A')}, "
                f"hom {hom}{popmax_str})."
            )
        else:
            gnomad_line = "gnomAD: population frequency data not available."

        evidence_lines = [
            f"ClinVar classification: {clinvar.get('classification', 'Unavailable')} ({clinvar.get('review_status', 'review status unavailable')}).",
            f"Predicted molecular consequence: {vep.get('most_severe_consequence', 'effect unavailable')} in a {vep.get('biotype', 'unknown biotype')} transcript.",
            f"SpliceAI: AL {spliceai.get('acceptor_loss', 0.0):.2f}, DL {spliceai.get('donor_loss', 0.0):.2f}, AG {spliceai.get('acceptor_gain', 0.0):.2f}, DG {spliceai.get('donor_gain', 0.0):.2f}; {splice_interpretation}",
            gnomad_line,
        ]

        fallback_sources = [
            name for name, status in payload.evidence_statuses.items() if status == 'fallback'
        ]
        warnings = []
        if fallback_sources:
            warnings.append(f"Fallback evidence mode for: {', '.join(sorted(fallback_sources))}.")

        uncertainty = (
            'This draft is limited to the uploaded report and linked evidence summaries. It does not assign formal ACMG evidence codes, '
            'does not replace specialist review, and should not be used as an autonomous diagnostic or treatment-eligibility decision.'
        )
        recommendation = (
            f"{subject} is being reviewed in the context of {clinical_context}. The report identifies {variant_summary}. "
            'Current external evidence supports clinician review of this finding, but it should be treated as a patient-specific interpretation step rather than a final stand-alone conclusion.'
        )
        next_step = (
            f"Confirm whether {variant_summary} fits the patient\'s phenotype and current referral question, review transcript-level and disease-context fit in clinic, "
            'and keep final interpretation and downstream action under human clinical governance.'
        )
        return DecisionOutput(
            recommendation=recommendation,
            evidence_lines=evidence_lines,
            uncertainty=uncertainty,
            next_step=next_step,
            confidence_label='medium',
            warnings=warnings,
        )
