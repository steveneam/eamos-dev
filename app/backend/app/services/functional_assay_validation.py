from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.schemas.run import (
    EamosComputedDirection,
    EamosComputedStrength,
    FunctionalAssayValidation,
    FunctionalEvidenceAssertionCandidate,
)
from app.services.computational_rulesets import active_ruleset

_STRENGTH_RANK: dict[EamosComputedStrength, int] = {
    "supporting": 1,
    "moderate": 2,
    "strong": 3,
    "very_strong": 4,
}


@dataclass(frozen=True)
class FunctionalAssertionAdmission:
    admitted: bool
    reasons: tuple[str, ...]
    code: str
    applied_strength: EamosComputedStrength
    functional_assay_oddspath: Decimal
    confidence_interval_lower: Decimal
    confidence_interval_upper: Decimal
    source_id: str
    source_record_id: str
    source_version: str
    source_url: str
    validation_id: str
    validation_version: str
    validation_policy_id: str
    validation_policy_version: str
    validation_source_url: str


def admit_functional_assertion(
    candidate: FunctionalEvidenceAssertionCandidate,
    *,
    gene_ids: tuple[str, ...],
    disease_ids: tuple[str, ...],
) -> FunctionalAssertionAdmission:
    ruleset = active_ruleset()
    validation = candidate.validation
    reasons: list[str] = []

    if not candidate.selected_for_counting:
        reasons.append("not_selected_for_counting")
    if candidate.source_id not in ruleset.functional_assertion_source_ids:
        reasons.append("source_not_allowed_by_ruleset")
    if validation.validation_policy_id != ruleset.functional_validation_policy_id:
        reasons.append("validation_policy_mismatch")
    if validation.validation_policy_version != ruleset.functional_validation_policy_version:
        reasons.append("validation_policy_version_mismatch")
    if validation.status != "published":
        reasons.append("validation_not_published")

    normalized_gene_ids = {_normalize_identifier(value) for value in gene_ids}
    normalized_disease_ids = {_normalize_identifier(value) for value in disease_ids}
    if _normalize_identifier(candidate.gene_id) not in normalized_gene_ids:
        reasons.append("assertion_gene_context_mismatch")
    if _normalize_identifier(candidate.disease_id) not in normalized_disease_ids:
        reasons.append("assertion_disease_context_mismatch")
    if _normalize_identifier(validation.gene_id) != _normalize_identifier(candidate.gene_id):
        reasons.append("validation_gene_mismatch")
    if _normalize_identifier(validation.disease_id) != _normalize_identifier(candidate.disease_id):
        reasons.append("validation_disease_mismatch")
    if _normalize_identifier(candidate.variant_id) not in {
        _normalize_identifier(value) for value in validation.evaluation_variant_ids
    }:
        reasons.append("assertion_variant_missing_from_validation_evaluation_set")

    expected_direction: EamosComputedDirection = (
        "pathogenic" if candidate.code == "PS3" else "benign"
    )
    if validation.direction != expected_direction:
        reasons.append("validation_direction_mismatch")

    matrix = validation.confusion_matrix
    if matrix.pathogenic_abnormal + matrix.pathogenic_normal == 0:
        reasons.append("pathogenic_truth_controls_missing")
    if matrix.benign_abnormal + matrix.benign_normal == 0:
        reasons.append("benign_truth_controls_missing")

    if validation.pseudocount != Decimal("1"):
        reasons.append("unsupported_functional_assay_pseudocount")
    calculated_oddspath = functional_oddspath_from_validation(validation)
    if calculated_oddspath is None:
        reasons.append("functional_assay_oddspath_not_calculable")
    elif not _decimal_close(
        calculated_oddspath,
        validation.functional_assay_oddspath,
    ):
        reasons.append("functional_assay_oddspath_confusion_matrix_mismatch")

    calibrated_direction, calibrated_strength = functional_oddspath_strength(
        validation.functional_assay_oddspath
    )
    if calibrated_direction != expected_direction:
        reasons.append("functional_assay_oddspath_direction_mismatch")
    if calibrated_strength is None:
        reasons.append("functional_assay_oddspath_indeterminate")
    else:
        applied_rank = _STRENGTH_RANK[candidate.applied_strength]
        if applied_rank > _STRENGTH_RANK[calibrated_strength]:
            reasons.append("asserted_strength_exceeds_oddspath")
        if applied_rank > _STRENGTH_RANK[validation.maximum_supported_strength]:
            reasons.append("asserted_strength_exceeds_validation_maximum")

    if expected_direction == "pathogenic":
        if validation.confidence_interval_lower <= Decimal("2.1"):
            reasons.append("functional_assay_confidence_interval_crosses_indeterminate")
    elif validation.confidence_interval_upper >= Decimal("0.48"):
        reasons.append("functional_assay_confidence_interval_crosses_indeterminate")

    return FunctionalAssertionAdmission(
        admitted=not reasons,
        reasons=tuple(_dedupe(reasons)),
        code=candidate.code,
        applied_strength=candidate.applied_strength,
        functional_assay_oddspath=validation.functional_assay_oddspath,
        confidence_interval_lower=validation.confidence_interval_lower,
        confidence_interval_upper=validation.confidence_interval_upper,
        source_id=candidate.source_id,
        source_record_id=candidate.source_record_id,
        source_version=candidate.source_version,
        source_url=candidate.source_url,
        validation_id=validation.validation_id,
        validation_version=validation.validation_version,
        validation_policy_id=validation.validation_policy_id,
        validation_policy_version=validation.validation_policy_version,
        validation_source_url=validation.source_url,
    )


def functional_oddspath_from_validation(
    validation: FunctionalAssayValidation,
) -> Decimal | None:
    matrix = validation.confusion_matrix
    pathogenic_total = matrix.pathogenic_abnormal + matrix.pathogenic_normal
    benign_total = matrix.benign_abnormal + matrix.benign_normal
    if pathogenic_total == 0 or benign_total == 0:
        return None

    if validation.direction == "pathogenic":
        pathogenic_readout_count = Decimal(matrix.pathogenic_abnormal)
        benign_readout_count = Decimal(matrix.benign_abnormal)
        if benign_readout_count == 0:
            benign_readout_count = validation.pseudocount
    else:
        pathogenic_readout_count = Decimal(matrix.pathogenic_normal)
        benign_readout_count = Decimal(matrix.benign_normal)
        if pathogenic_readout_count == 0:
            pathogenic_readout_count = validation.pseudocount

    if pathogenic_readout_count == 0 or benign_readout_count == 0:
        return None
    return (
        pathogenic_readout_count
        * Decimal(benign_total)
        / (benign_readout_count * Decimal(pathogenic_total))
    )


def functional_oddspath_strength(
    value: Decimal,
) -> tuple[EamosComputedDirection | None, EamosComputedStrength | None]:
    if value < Decimal("0.053"):
        return "benign", "strong"
    if value < Decimal("0.23"):
        return "benign", "moderate"
    if value < Decimal("0.48"):
        return "benign", "supporting"
    if value <= Decimal("2.1"):
        return None, None
    if value <= Decimal("4.3"):
        return "pathogenic", "supporting"
    if value <= Decimal("18.7"):
        return "pathogenic", "moderate"
    if value <= Decimal("350"):
        return "pathogenic", "strong"
    return "pathogenic", "very_strong"


def _normalize_identifier(value: str) -> str:
    return value.strip().upper()


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _decimal_close(left: Decimal, right: Decimal) -> bool:
    tolerance = max(Decimal("0.000001"), abs(left) * Decimal("0.000001"))
    return abs(left - right) <= tolerance
