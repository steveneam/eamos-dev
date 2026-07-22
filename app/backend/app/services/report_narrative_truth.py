from __future__ import annotations

import math
import re
from typing import Any

from app.rules.base import DecisionOutput
from app.services.report_source_truth import report_source_allows_payload


def report_safe_evidence_map(
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> dict[str, dict[str, Any]]:
    return {
        source: summary
        for source, summary in evidence_map.items()
        if report_source_allows_payload(evidence_statuses.get(source, "missing"))
    }


def acmg_classification_snapshot(gene: str, cdna: str, clinvar: dict[str, Any]) -> str:
    classification = safe_clinvar_classification(clinvar.get("classification")) or "Unavailable"
    review_status = safe_report_label(clinvar.get("review_status")) or "review status unavailable"
    return (
        f"ClinVar currently lists {gene} {cdna} as {classification} ({review_status}). "
        "This is a source snapshot only and should not be read as formal ACMG evidence-code "
        "assignment or a final laboratory classification."
    )


def build_report_safe_decision(
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> DecisionOutput:
    evidence = report_safe_evidence_map(evidence_map, evidence_statuses)
    evidence_lines: list[str] = []

    clinvar = evidence.get("clinvar", {})
    classification = safe_clinvar_classification(clinvar.get("classification"))
    review_status = safe_report_label(clinvar.get("review_status"))
    if classification:
        review_suffix = f" ({review_status})" if review_status else ""
        evidence_lines.append(f"ClinVar classification: {classification}{review_suffix}.")

    vep = evidence.get("vep", {})
    consequence = safe_report_label(vep.get("most_severe_consequence"))
    biotype = safe_report_label(vep.get("biotype"))
    if consequence:
        biotype_suffix = f" in a {biotype} transcript" if biotype else ""
        evidence_lines.append(f"Predicted molecular consequence: {consequence}{biotype_suffix}.")

    spliceai = evidence.get("spliceai", {})
    splice_parts = [
        f"{label} {score:.2f}"
        for key, label in (
            ("acceptor_loss", "AL"),
            ("donor_loss", "DL"),
            ("acceptor_gain", "AG"),
            ("donor_gain", "DG"),
        )
        if (score := _safe_probability(spliceai.get(key))) is not None
    ]
    if splice_parts:
        evidence_lines.append(f"SpliceAI: {', '.join(splice_parts)}.")

    gnomad = evidence.get("gnomad", {})
    allele_frequency = _safe_probability(gnomad.get("allele_frequency"))
    if allele_frequency is not None:
        evidence_lines.append(f"gnomAD allele frequency: {allele_frequency:.6g}.")

    if evidence_lines:
        recommendation = (
            "Source-backed external evidence is available for clinician review. "
            "Treat it as contextual evidence, not a final classification."
        )
        next_step = (
            "Confirm the submitted variant and review the source-backed evidence with a specialist."
        )
        uncertainty = (
            "The available source records do not replace patient-specific clinical interpretation."
        )
        confidence_label = "source_backed_context"
    else:
        recommendation = (
            "No source-backed external evidence was available for this lookup. "
            "Confirm the submitted variant before interpretation."
        )
        next_step = (
            "Restore identity-bound evidence sources, then repeat the lookup and specialist review."
        )
        uncertainty = "Scientific interpretation is unavailable without source-backed evidence."
        confidence_label = "unavailable"
    return DecisionOutput(
        recommendation=recommendation,
        evidence_lines=evidence_lines,
        uncertainty=uncertainty,
        next_step=next_step,
        confidence_label=confidence_label,
        warnings=([] if evidence_lines else ["report_sources_unavailable"]),
    )


def safe_clinvar_classification(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text or len(text) > 128:
        return None
    allowed = {
        "affects",
        "association",
        "benign",
        "conflicting classifications of pathogenicity",
        "conflicting interpretations of pathogenicity",
        "drug response",
        "likely benign",
        "likely pathogenic",
        "not provided",
        "other",
        "pathogenic",
        "protective",
        "risk factor",
        "uncertain significance",
    }
    parts = [part.strip().casefold().replace("_", " ") for part in text.split("/")]
    return text if parts and all(part in allowed for part in parts) else None


def safe_report_label(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text or len(text) > 128:
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .,_()+*'-]{0,127}", text):
        return None
    return text


def _safe_probability(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and 0 <= number <= 1 else None
