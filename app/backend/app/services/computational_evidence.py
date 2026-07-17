from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any

from app.schemas.run import (
    ComputationalAlternate,
    ComputationalDeepDiveSection,
    ComputationalEvidenceDecision,
    ComputationalPredictorRow,
    DiseaseMechanismSection,
    ReportPayload,
)
from app.services.computational_calibration import calibrate_predictor
from app.services.computational_rulesets import active_ruleset

SELECTOR_ID = "eamos_preselected_predictor_policy_v1"
MISSENSE_MECHANISM_POLICY_ID = "gene_disease_missense_applicability_v1"
PP3_PM1_DEPENDENCY_GROUP = "computational_regional_pathogenic_cap_4"

_STRENGTH_POINTS = {
    "very_strong": Decimal("8"),
    "strong": Decimal("4"),
    "moderate": Decimal("2"),
    "supporting": Decimal("1"),
}


def build_computational_evidence_decision(
    *,
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    disease_mechanism: DiseaseMechanismSection | None,
    deep_dive: ComputationalDeepDiveSection | None,
) -> ComputationalEvidenceDecision:
    ruleset = active_ruleset()
    row = payload.variant_summary_rows[0] if payload.variant_summary_rows else None
    consequence = str(row.consequence if row is not None and row.consequence else "").lower()
    variant_scope = _variant_scope(consequence, row.variation_type if row is not None else None)
    gene_summary = evidence_map.get("gene_disease", {})
    gene_id = _first_text(
        gene_summary.get("approved_symbol"),
        gene_summary.get("gene"),
        row.gene if row is not None else None,
    )
    disease_id = _first_text(
        *((disease_mechanism.disease_ids if disease_mechanism is not None else [])[:1]),
        *(
            (gene_summary.get("disease_ids") or [])[:1]
            if isinstance(gene_summary.get("disease_ids"), list)
            else []
        ),
    )
    transcript_id = _transcript_id(payload)
    normalized_variant_id = _normalized_variant_id(payload)
    mechanism_version = _first_text(
        gene_summary.get("missense_mechanism_policy_version"),
        gene_summary.get("mechanism_profile_version"),
    )
    missense_applicable = (
        variant_scope == "missense"
        and gene_summary.get("missense_mechanism_applicable") is True
        and mechanism_version is not None
    )
    mechanism_applicability = (
        f"applicable:{MISSENSE_MECHANISM_POLICY_ID}:{mechanism_version}"
        if missense_applicable
        else f"not_established:{MISSENSE_MECHANISM_POLICY_ID}"
    )

    rows = list(deep_dive.predictors if deep_dive is not None else [])
    alternates = [
        _alternate_from_row(item)
        for item in rows
        if _predictor_id(item.name) != "revel" and item.public_serialization_allowed is True
    ]
    selected = next((item for item in rows if _predictor_id(item.name) == "revel"), None)
    base = {
        "ruleset_id": ruleset.ruleset_id,
        "ruleset_version": ruleset.framework_version,
        "standard_label": ruleset.framework_name,
        "standard_status": ruleset.status,
        "application_id": _application_id(
            ruleset.ruleset_id,
            gene_id,
            disease_id,
            transcript_id,
            normalized_variant_id,
        ),
        "gene_id": gene_id,
        "disease_id": disease_id,
        "transcript_id": transcript_id,
        "protein_id": None,
        "normalized_variant_id": normalized_variant_id,
        "variant_scope": variant_scope,
        "mechanism_applicability": mechanism_applicability,
        "selection_policy": SELECTOR_ID,
        "declared_fallback_policy": "none",
        "dependency_group": PP3_PM1_DEPENDENCY_GROUP,
        "alternates": alternates,
    }

    if variant_scope != "missense":
        family = "SPLICE" if variant_scope == "splice" else "other"
        return ComputationalEvidenceDecision(
            **base,
            evidence_family=family,
            selected_predictor_id=None,
            selection_rationale="REVEL is not applied outside missense variants.",
            applicability="not_assessed",
            evidence_points=Decimal("0"),
            evidence_label="No validated selector for this variant class",
            counted_status="separate_mechanism" if family == "SPLICE" else "context_only",
            non_counted_reason="class_specific_selector_required",
        )

    if selected is None:
        return ComputationalEvidenceDecision(
            **base,
            evidence_family="PP3_BP4",
            selected_predictor_id="revel",
            selection_rationale="REVEL is preselected for applicable missense evidence.",
            applicability="unavailable",
            evidence_points=Decimal("0"),
            evidence_label="REVEL unavailable",
            counted_status="rejected",
            non_counted_reason="selected_predictor_score_unavailable",
        )

    if selected.public_serialization_allowed is not True:
        return ComputationalEvidenceDecision(
            **base,
            evidence_family="PP3_BP4",
            selected_predictor_id="revel",
            selection_rationale="REVEL is preselected for applicable missense evidence.",
            applicability="unavailable",
            evidence_points=Decimal("0"),
            evidence_label="REVEL unavailable",
            counted_status="rejected",
            non_counted_reason="source_policy_public_serialization_denied",
        )

    if selected.score is None:
        return ComputationalEvidenceDecision(
            **base,
            evidence_family="PP3_BP4",
            selected_predictor_id="revel",
            selection_rationale="REVEL is preselected for applicable missense evidence.",
            applicability="unavailable",
            evidence_points=Decimal("0"),
            evidence_label="REVEL unavailable",
            counted_status="rejected",
            non_counted_reason="selected_predictor_score_unavailable",
        )

    calibration = calibrate_predictor(
        "REVEL",
        selected.score,
        profile_id="revel_pejaver_2022_capped",
    )
    if calibration is None:
        return ComputationalEvidenceDecision(
            **base,
            evidence_family="PP3_BP4",
            selected_predictor_id="revel",
            selection_rationale="REVEL is preselected for applicable missense evidence.",
            applicability="unavailable",
            raw_score=_decimal_or_none(selected.score),
            evidence_points=Decimal("0"),
            evidence_label="REVEL unavailable",
            counted_status="rejected",
            non_counted_reason="selected_predictor_score_invalid",
            warnings=["revel_score_failed_active_calibration"],
        )

    common = {
        **base,
        "evidence_family": "PP3_BP4",
        "selected_predictor_id": "revel",
        "selection_rationale": (
            "REVEL was selected before score evaluation under the active missense policy."
        ),
        "raw_score": calibration.raw_score,
        "calibration_normalized_score": calibration.calibration_normalized_score,
        "score_unit": calibration.score_unit,
        "score_native_precision": calibration.score_native_precision,
        "score_quantization_rule": calibration.score_quantization_rule,
        "evidence_code": calibration.evidence_code,
        "calibration_points": calibration.evidence_points,
        "calibration_id": calibration.calibration_id,
        "calibration_version": calibration.calibration_version,
        "calibration_profile_checksum": calibration.profile_checksum,
        "interval_lower": calibration.interval_lower,
        "interval_lower_inclusive": calibration.interval_lower_inclusive,
        "interval_upper": calibration.interval_upper,
        "interval_upper_inclusive": calibration.interval_upper_inclusive,
        "tool_version": selected.version,
        "model_version": selected.version,
        "data_version": selected.version,
        "source_version": selected.version,
        "source_url": selected.source_url,
        "source_checksum": calibration.profile_checksum,
    }

    if not missense_applicable:
        return ComputationalEvidenceDecision(
            **common,
            applicability="not_applicable",
            evidence_points=Decimal("0"),
            evidence_label="REVEL not applicable",
            counted_status="context_only",
            non_counted_reason="missense_disease_mechanism_not_established",
        )

    if calibration.evidence_code is None or calibration.evidence_points == 0:
        return ComputationalEvidenceDecision(
            **common,
            applicability="applicable",
            evidence_points=Decimal("0"),
            evidence_label="REVEL Indeterminate",
            counted_status="context_only",
            non_counted_reason="calibration_indeterminate",
        )

    evidence_points = calibration.evidence_points
    warnings: list[str] = []
    if calibration.evidence_code == "PP3" and evidence_points > 0:
        pm1_points = _pm1_points(evidence_map)
        allowed = max(Decimal("0"), Decimal("4") - pm1_points)
        if evidence_points > allowed:
            evidence_points = allowed
            warnings.append("pp3_points_capped_by_pm1_dependency_group")

    if evidence_points == 0:
        counted_status = "rejected"
        non_counted_reason = "pp3_pm1_dependency_cap_exhausted"
    else:
        counted_status = "counted"
        non_counted_reason = None

    return ComputationalEvidenceDecision(
        **common,
        applicability="applicable",
        evidence_points=evidence_points,
        evidence_label=f"REVEL {calibration.calibrated_label}",
        counted_status=counted_status,
        non_counted_reason=non_counted_reason,
        warnings=warnings,
    )


def selection_accounting(decision: ComputationalEvidenceDecision) -> str:
    selected = (
        "REVEL counted"
        if decision.counted_status == "counted"
        else (f"REVEL {decision.counted_status.replace('_', ' ')}")
    )
    alternate_names = sorted(
        {
            alternate.predictor_id
            for alternate in decision.alternates
            if alternate.predictor_id not in {"spliceai"}
        }
    )
    alternate_text = (
        f"{'/'.join(_display_predictor(name) for name in alternate_names)} context only"
        if alternate_names
        else "No alternate missense scores"
    )
    splice_text = (
        "SpliceAI separate mechanism"
        if any(alternate.predictor_id == "spliceai" for alternate in decision.alternates)
        else "No splice score"
    )
    return f"{selected} | {alternate_text} | {splice_text}"


def _alternate_from_row(row: ComputationalPredictorRow) -> ComputationalAlternate:
    predictor_id = _predictor_id(row.name)
    score = _decimal_or_none(row.score)
    calibration = calibrate_predictor(row.name, score) if score is not None else None
    return ComputationalAlternate(
        predictor_id=predictor_id,
        raw_score=score,
        calibration_normalized_score=(
            calibration.calibration_normalized_score if calibration is not None else None
        ),
        score_unit=calibration.score_unit if calibration is not None else row.score_unit,
        calibration_id=(
            calibration.calibration_id if calibration is not None else row.calibration_id
        ),
        calibration_version=(
            calibration.calibration_version if calibration is not None else row.calibration_version
        ),
        evidence_code=(
            calibration.evidence_code
            if calibration is not None and calibration.evidence_code in {"PP3", "BP4"}
            else None
        ),
        calibration_points=calibration.evidence_points if calibration is not None else None,
        counted_status="separate_mechanism" if predictor_id == "spliceai" else "context_only",
        non_counted_reason=(
            "separate_splice_mechanism"
            if predictor_id == "spliceai"
            else "alternate_predictor_not_selected"
        ),
        tool_version=row.version,
        model_version=row.version,
        data_version=row.version,
        source_version=row.version,
        source_url=row.source_url,
    )


def _pm1_points(evidence_map: dict[str, dict[str, Any]]) -> Decimal:
    worksheet = evidence_map.get("clinical_consensus", {}).get("acmg_worksheet")
    if isinstance(worksheet, dict) and isinstance(worksheet.get("criteria"), list):
        for item in worksheet["criteria"]:
            if not isinstance(item, dict):
                continue
            if item.get("code") != "PM1" or item.get("state") != "met":
                continue
            if item.get("assertion_level") not in {"source_asserted", "vcep_specified"}:
                continue
            return _STRENGTH_POINTS.get(str(item.get("strength") or "").lower(), Decimal("0"))
    return Decimal("0")


def _variant_scope(consequence: str, variation_type: str | None) -> str:
    text = f"{consequence} {variation_type or ''}".lower()
    if "missense" in text:
        return "missense"
    if "splice" in text:
        return "splice"
    if any(token in text for token in ("stop", "frameshift", "truncat")):
        return "loss_of_function"
    if "indel" in text or "insertion" in text or "deletion" in text:
        return "indel"
    if "noncoding" in text or "non-coding" in text:
        return "noncoding"
    return "unknown"


def _transcript_id(payload: ReportPayload) -> str | None:
    header = payload.report_profile.header if payload.report_profile is not None else None
    if header is not None and header.transcript:
        return header.transcript
    row = payload.variant_summary_rows[0] if payload.variant_summary_rows else None
    text = str(row.transcript_hgvs or "") if row is not None else ""
    return text.split(":", 1)[0] if ":" in text else None


def _normalized_variant_id(payload: ReportPayload) -> str | None:
    header = payload.report_profile.header if payload.report_profile is not None else None
    if header is not None:
        return _first_text(header.genomic_hg38, header.cdna)
    row = payload.variant_summary_rows[0] if payload.variant_summary_rows else None
    return _first_text(
        row.genomic_hg38 if row is not None else None,
        row.transcript_hgvs if row is not None else None,
    )


def _application_id(*parts: str | None) -> str:
    canonical = "|".join(part or "" for part in parts)
    return f"computational:{sha256(canonical.encode('utf-8')).hexdigest()[:24]}"


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return parsed if parsed.is_finite() else None


def _predictor_id(value: str) -> str:
    normalized = value.strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    aliases = {
        "alphamissense": "alphamissense",
        "esm1b": "esm1b",
        "esm1bllr": "esm1b",
        "cadd": "caddphred",
        "caddphred": "caddphred",
        "spliceai": "spliceai",
        "primateai3d": "primateai",
    }
    return aliases.get(normalized, normalized)


def _display_predictor(value: str) -> str:
    return {
        "alphamissense": "AlphaMissense",
        "esm1b": "ESM-1b",
        "caddphred": "CADD",
        "primateai": "PrimateAI-3D",
    }.get(value, value)


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        if isinstance(value, datetime):
            return value.isoformat()
        text = str(value).strip()
        if text:
            return text
    return None
