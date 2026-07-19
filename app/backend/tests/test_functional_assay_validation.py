from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.run import (
    FunctionalAssayConfusionMatrix,
    FunctionalAssayValidation,
    FunctionalEvidenceAssertionCandidate,
)
from app.services.functional_assay_validation import (
    admit_functional_assertion,
    functional_oddspath_from_validation,
    functional_oddspath_strength,
)


@pytest.mark.parametrize(
    ("oddspath", "expected"),
    [
        ("0.0529", ("benign", "strong")),
        ("0.053", ("benign", "moderate")),
        ("0.23", ("benign", "supporting")),
        ("0.48", (None, None)),
        ("2.1", (None, None)),
        ("2.1001", ("pathogenic", "supporting")),
        ("4.3", ("pathogenic", "supporting")),
        ("4.3001", ("pathogenic", "moderate")),
        ("18.7", ("pathogenic", "moderate")),
        ("18.7001", ("pathogenic", "strong")),
        ("350", ("pathogenic", "strong")),
        ("350.0001", ("pathogenic", "very_strong")),
    ],
)
def test_brnich_functional_oddspath_boundaries_are_exact(oddspath, expected) -> None:
    assert functional_oddspath_strength(Decimal(oddspath)) == expected


def test_complete_selected_assay_assertion_is_admitted_at_supported_strength() -> None:
    candidate = _candidate()

    decision = admit_functional_assertion(
        candidate,
        gene_ids=("HGNC:10294",),
        disease_ids=("MONDO:0100368",),
    )

    assert decision.admitted is True
    assert decision.reasons == ()
    assert decision.code == "PS3"
    assert decision.applied_strength == "moderate"
    assert decision.functional_assay_oddspath == Decimal("10")
    assert decision.validation_policy_id == "clingen_svi_brnich_2020_v1"
    assert decision.validation_policy_version == "1.0.0"
    assert functional_oddspath_from_validation(candidate.validation) == Decimal("10")


def test_direction_specific_benign_oddspath_is_admitted_for_bs3() -> None:
    validation_payload = _validation().model_dump()
    validation_payload.update(
        {
            "direction": "benign",
            "functional_assay_oddspath": Decimal("0.1"),
            "confidence_interval_lower": Decimal("0.05"),
            "confidence_interval_upper": Decimal("0.2"),
            "maximum_supported_strength": "moderate",
        }
    )
    candidate_payload = _candidate().model_dump()
    candidate_payload.update(
        {
            "code": "BS3",
            "applied_strength": "moderate",
            "validation": validation_payload,
        }
    )
    candidate = FunctionalEvidenceAssertionCandidate.model_validate(candidate_payload)

    decision = admit_functional_assertion(
        candidate,
        gene_ids=("HGNC:10294",),
        disease_ids=("MONDO:0100368",),
    )

    assert decision.admitted is True
    assert decision.code == "BS3"
    assert functional_oddspath_from_validation(candidate.validation) == Decimal("0.1")


def test_assertion_fails_closed_on_source_context_ci_and_strength_gates() -> None:
    candidate = _candidate(
        source_id="pubmed",
        applied_strength="strong",
        confidence_interval_lower=Decimal("1.5"),
    )

    decision = admit_functional_assertion(
        candidate,
        gene_ids=("HGNC:OTHER",),
        disease_ids=("MONDO:OTHER",),
    )

    assert decision.admitted is False
    assert set(decision.reasons) >= {
        "source_not_allowed_by_ruleset",
        "assertion_gene_context_mismatch",
        "assertion_disease_context_mismatch",
        "asserted_strength_exceeds_oddspath",
        "functional_assay_confidence_interval_crosses_indeterminate",
    }


def test_truth_and_evaluation_overlap_is_rejected_by_the_contract() -> None:
    payload = _validation().model_dump()
    payload["evaluation_variant_ids"] = [" TRUTH-PATH-1 "]

    with pytest.raises(ValidationError, match="must not overlap"):
        FunctionalAssayValidation.model_validate(payload)


def test_evaluation_variant_ids_must_be_nonempty_and_unique() -> None:
    payload = _validation().model_dump()
    payload["evaluation_variant_ids"] = ["query-variant", " QUERY-VARIANT "]

    with pytest.raises(ValidationError, match="evaluation-set variant IDs"):
        FunctionalAssayValidation.model_validate(payload)


def test_claimed_oddspath_must_match_the_control_confusion_matrix() -> None:
    payload = _validation().model_dump()
    payload["functional_assay_oddspath"] = Decimal("11")
    payload["confidence_interval_upper"] = Decimal("15")
    candidate = _candidate(validation=FunctionalAssayValidation.model_validate(payload))

    decision = admit_functional_assertion(
        candidate,
        gene_ids=("HGNC:10294",),
        disease_ids=("MONDO:0100368",),
    )

    assert decision.admitted is False
    assert "functional_assay_oddspath_confusion_matrix_mismatch" in decision.reasons


def test_unselected_source_assertion_remains_context_only() -> None:
    candidate = _candidate(selected_for_counting=False, selection_rationale=None)

    decision = admit_functional_assertion(
        candidate,
        gene_ids=("HGNC:10294",),
        disease_ids=("MONDO:0100368",),
    )

    assert decision.admitted is False
    assert decision.reasons == ("not_selected_for_counting",)


def _validation(
    *,
    confidence_interval_lower: Decimal = Decimal("5"),
) -> FunctionalAssayValidation:
    return FunctionalAssayValidation(
        validation_id="rpe65-isomerohydrolase-calibration",
        validation_version="1.0.0",
        validation_policy_id="clingen_svi_brnich_2020_v1",
        validation_policy_version="1.0.0",
        status="published",
        gene_id="HGNC:10294",
        disease_id="MONDO:0100368",
        disease_mechanism="Biallelic loss of RPE65 isomerohydrolase activity",
        assay_name="RPE65 isomerohydrolase activity",
        assay_relevance="Measures the disease-relevant enzymatic mechanism",
        pathogenic_truth_variant_ids=[f"truth-path-{index}" for index in range(1, 11)],
        benign_truth_variant_ids=[f"truth-benign-{index}" for index in range(1, 11)],
        evaluation_variant_ids=["query-variant"],
        truth_set_independence_basis="Truth variants were classified without this assay",
        truth_evaluation_overlap_rejected=True,
        circularity_reviewed=True,
        confusion_matrix=FunctionalAssayConfusionMatrix(
            pathogenic_abnormal=10,
            pathogenic_normal=0,
            benign_abnormal=0,
            benign_normal=10,
        ),
        pseudocount_policy="brnich_2020_one_discordant_control",
        pseudocount=Decimal("1"),
        direction="pathogenic",
        functional_assay_oddspath=Decimal("10"),
        confidence_interval_lower=confidence_interval_lower,
        confidence_interval_upper=Decimal("15"),
        maximum_supported_strength="moderate",
        curator="ClinGen VCEP curator",
        validation_date=date(2023, 8, 10),
        source_url="https://cspec.clinicalgenome.org/cspec/ui/svi/doc/GN120",
        source_version="RPE65 CSpec 1.0.0",
    )


def _candidate(
    *,
    source_id: str = "clingen",
    applied_strength: str = "moderate",
    selected_for_counting: bool = True,
    selection_rationale: str | None = "Best validated disease-mechanism assay",
    confidence_interval_lower: Decimal = Decimal("5"),
    validation: FunctionalAssayValidation | None = None,
) -> FunctionalEvidenceAssertionCandidate:
    return FunctionalEvidenceAssertionCandidate(
        assertion_id="GN120:PS3:query-variant",
        code="PS3",
        applied_strength=applied_strength,
        variant_id="query-variant",
        gene_id="HGNC:10294",
        disease_id="MONDO:0100368",
        source_id=source_id,
        source_record_id="GN120",
        source_version="1.0.0",
        source_url="https://cspec.clinicalgenome.org/cspec/ui/svi/doc/GN120",
        selected_for_counting=selected_for_counting,
        selection_rationale=selection_rationale,
        validation=validation or _validation(confidence_interval_lower=confidence_interval_lower),
    )
