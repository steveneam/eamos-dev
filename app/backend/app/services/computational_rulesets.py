from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Literal, Mapping

RulesetStatus = Literal["published", "draft", "shadow", "withdrawn"]
ConflictResolutionPolicy = Literal["eamos_legacy_vus_cap", "none"]


@dataclass(frozen=True)
class ComputationalTierDefinition:
    label: str
    lower: Decimal | None
    lower_inclusive: bool
    upper: Decimal | None
    upper_inclusive: bool

    def contains(self, points: Decimal) -> bool:
        if self.lower is not None and (
            points < self.lower or (points == self.lower and not self.lower_inclusive)
        ):
            return False
        if self.upper is not None and (
            points > self.upper or (points == self.upper and not self.upper_inclusive)
        ):
            return False
        return True


@dataclass(frozen=True)
class ComputationalRulesetRecord:
    ruleset_id: str
    framework_name: str
    framework_version: str
    publication_url: str
    document_url: str
    document_checksum: str
    effective_date: str
    status: RulesetStatus
    prior_decimal: Decimal
    likelihood_ratio_base_decimal: Decimal
    tier_definitions: tuple[ComputationalTierDefinition, ...]
    criterion_definitions: tuple[tuple[str, Decimal], ...]
    predictor_selection_rules: tuple[str, ...]
    dependency_and_exclusion_edges: tuple[tuple[str, str, str], ...]
    standalone_overrides: tuple[str, ...]
    conflict_resolution_policy: ConflictResolutionPolicy
    population_policy_id: str
    functional_validation_policy_id: str
    functional_validation_policy_version: str
    functional_assertion_source_ids: tuple[str, ...]
    cspec_overlay_version: str | None
    activated_at: str | None


RICHARDS_TAVTIGIAN_EAMOS_V1 = ComputationalRulesetRecord(
    ruleset_id="richards_2015_tavtigian_2020_eamos_v1",
    framework_name="Richards-2015 + Tavtigian-2020 points",
    framework_version="eamos-historical-replay-v1",
    publication_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC8011844/",
    document_url=("https://pmc.ncbi.nlm.nih.gov/articles/PMC8011844/pdf/nihms-1681181.pdf"),
    document_checksum=("sha256:2714eb28dda9188e4567377554ec829c8d62b442f3dfbed7dfb9a4fa763b8a01"),
    effective_date="2026-07-17",
    status="published",
    prior_decimal=Decimal("0.1"),
    likelihood_ratio_base_decimal=Decimal("2.08"),
    tier_definitions=(
        ComputationalTierDefinition("Pathogenic", Decimal("10"), True, None, False),
        ComputationalTierDefinition("Likely Pathogenic", Decimal("6"), True, Decimal("10"), False),
        ComputationalTierDefinition("VUS", Decimal("0"), True, Decimal("6"), False),
        ComputationalTierDefinition("Likely Benign", Decimal("-7"), False, Decimal("0"), False),
        ComputationalTierDefinition("Benign", None, False, Decimal("-7"), True),
    ),
    criterion_definitions=(
        ("very_strong", Decimal("8")),
        ("strong", Decimal("4")),
        ("moderate", Decimal("2")),
        ("supporting", Decimal("1")),
    ),
    predictor_selection_rules=(
        "missense:revel_pejaver_2022_capped",
        "missing_selected_predictor:no_fallback",
        "non_missense:class_specific_or_not_assessed",
    ),
    dependency_and_exclusion_edges=(
        ("PP3", "BP4", "mutually_exclusive"),
        ("PP3", "PM1", "combined_pathogenic_points_cap_4"),
        ("PM2", "BS1", "mutually_exclusive"),
        ("PM2", "BA1", "mutually_exclusive"),
        ("PS3", "BS3", "mutually_exclusive"),
        ("PS3", "nonfunctional_pathogenic_evidence", "requires_same_direction_evidence"),
        ("BS3", "nonfunctional_benign_evidence", "requires_same_direction_evidence"),
    ),
    standalone_overrides=("BA1",),
    # The VUS conflict cap is retained only as an explicit, replayable Eamos-v1
    # behavior. A future ruleset must choose its own cited policy rather than
    # inheriting this field by accident.
    conflict_resolution_policy="eamos_legacy_vus_cap",
    population_policy_id="acmg_svi_general_frequency_v1",
    functional_validation_policy_id="clingen_svi_brnich_2020_v1",
    functional_validation_policy_version="1.0.0",
    functional_assertion_source_ids=("clingen", "clinvar"),
    cspec_overlay_version="cspec-registry-v1",
    activated_at="2026-07-17",
)

RULESET_REGISTRY: Mapping[str, ComputationalRulesetRecord] = MappingProxyType(
    {RICHARDS_TAVTIGIAN_EAMOS_V1.ruleset_id: RICHARDS_TAVTIGIAN_EAMOS_V1}
)


def active_ruleset() -> ComputationalRulesetRecord:
    record = RULESET_REGISTRY[RICHARDS_TAVTIGIAN_EAMOS_V1.ruleset_id]
    if record.status != "published" or record.activated_at is None:
        raise RuntimeError("active computational ruleset is not published and activated")
    return record
