from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal
from types import MappingProxyType
from typing import Literal, Mapping

from app.services.computational_rulesets import active_ruleset

PolicyStatus = Literal["published", "draft", "shadow", "withdrawn"]
FrequencyMetric = Literal["popmax_filtering_allele_frequency"]


@dataclass(frozen=True)
class PopulationThresholdPolicy:
    policy_id: str
    version: str
    status: PolicyStatus
    source_url: str
    source_version: str
    released_at: str
    frequency_metric: FrequencyMetric
    allow_maximum_observed_frequency_fallback: bool
    ba1_minimum: Decimal
    bs1_minimum: Decimal
    pm2_maximum: Decimal
    pm2_maximum_inclusive: bool
    pm2_minimum_allele_number: int | None
    pm2_maximum_homozygotes: int | None


@dataclass(frozen=True)
class CspecOverlayRecord:
    overlay_id: str
    version: str
    status: PolicyStatus
    ruleset_id: str
    gene_symbol: str
    gene_id: str
    disease_id: str
    source_url: str
    released_at: str
    population_policy_id: str


@dataclass(frozen=True)
class PopulationPolicyDiff:
    field: str
    general_value: str
    overlay_value: str


@dataclass(frozen=True)
class PopulationPolicyResolution:
    general_policy: PopulationThresholdPolicy
    effective_policy: PopulationThresholdPolicy
    overlay: CspecOverlayRecord | None
    diff: tuple[PopulationPolicyDiff, ...]


ACMG_SVI_GENERAL_FREQUENCY_V1 = PopulationThresholdPolicy(
    policy_id="acmg_svi_general_frequency_v1",
    version="1.0.0",
    status="published",
    source_url="https://pubmed.ncbi.nlm.nih.gov/25741868/",
    source_version="Richards-2015 with Eamos-v1 PM2 supporting guardrail",
    released_at="2026-07-17",
    frequency_metric="popmax_filtering_allele_frequency",
    allow_maximum_observed_frequency_fallback=True,
    ba1_minimum=Decimal("0.05"),
    bs1_minimum=Decimal("0.01"),
    pm2_maximum=Decimal("0.0001"),
    pm2_maximum_inclusive=False,
    pm2_minimum_allele_number=1000,
    pm2_maximum_homozygotes=0,
)

RPE65_RECESSIVE_RETINOPATHY_FREQUENCY_V1 = PopulationThresholdPolicy(
    policy_id="clingen_cspec_gn120_rpe65_frequency_v1",
    version="1.0.0",
    status="published",
    source_url="https://cspec.clinicalgenome.org/cspec/ui/svi/doc/GN120",
    source_version="ClinGen RPE65 CSpec 1.0.0",
    released_at="2023-10-24",
    frequency_metric="popmax_filtering_allele_frequency",
    allow_maximum_observed_frequency_fallback=False,
    ba1_minimum=Decimal("0.008"),
    bs1_minimum=Decimal("0.0008"),
    pm2_maximum=Decimal("0.0002"),
    pm2_maximum_inclusive=True,
    pm2_minimum_allele_number=None,
    pm2_maximum_homozygotes=None,
)

RPE65_RECESSIVE_RETINOPATHY_CSPEC_V1 = CspecOverlayRecord(
    overlay_id="clingen_cspec_gn120_rpe65_v1",
    version="1.0.0",
    status="published",
    ruleset_id="richards_2015_tavtigian_2020_eamos_v1",
    gene_symbol="RPE65",
    gene_id="HGNC:10294",
    disease_id="MONDO:0100368",
    source_url="https://cspec.clinicalgenome.org/cspec/ui/svi/doc/GN120",
    released_at="2023-10-24",
    population_policy_id=RPE65_RECESSIVE_RETINOPATHY_FREQUENCY_V1.policy_id,
)

POPULATION_POLICY_REGISTRY: Mapping[str, PopulationThresholdPolicy] = MappingProxyType(
    {
        policy.policy_id: policy
        for policy in (
            ACMG_SVI_GENERAL_FREQUENCY_V1,
            RPE65_RECESSIVE_RETINOPATHY_FREQUENCY_V1,
        )
    }
)

CSPEC_OVERLAY_REGISTRY: Mapping[str, CspecOverlayRecord] = MappingProxyType(
    {RPE65_RECESSIVE_RETINOPATHY_CSPEC_V1.overlay_id: RPE65_RECESSIVE_RETINOPATHY_CSPEC_V1}
)


def resolve_population_policy(
    *,
    gene_symbol: str | None,
    gene_ids: tuple[str, ...] = (),
    disease_ids: tuple[str, ...] = (),
) -> PopulationPolicyResolution:
    ruleset = active_ruleset()
    general = POPULATION_POLICY_REGISTRY[ruleset.population_policy_id]
    normalized_gene = (gene_symbol or "").strip().upper()
    normalized_gene_ids = {_normalize_identifier(value) for value in gene_ids if value.strip()}
    normalized_disease_ids = {
        _normalize_identifier(value) for value in disease_ids if value.strip()
    }

    matches = [
        overlay
        for overlay in CSPEC_OVERLAY_REGISTRY.values()
        if overlay.status == "published"
        and overlay.ruleset_id == ruleset.ruleset_id
        and (
            normalized_gene == overlay.gene_symbol
            or _normalize_identifier(overlay.gene_id) in normalized_gene_ids
        )
        and _normalize_identifier(overlay.disease_id) in normalized_disease_ids
    ]
    if len(matches) > 1:
        match_ids = ", ".join(sorted(overlay.overlay_id for overlay in matches))
        raise RuntimeError(f"ambiguous ClinGen CSpec overlays: {match_ids}")
    if not matches:
        return PopulationPolicyResolution(general, general, None, ())

    overlay = matches[0]
    effective = POPULATION_POLICY_REGISTRY[overlay.population_policy_id]
    if effective.status != "published":
        raise RuntimeError(f"CSpec population policy is not published: {effective.policy_id}")
    return PopulationPolicyResolution(
        general_policy=general,
        effective_policy=effective,
        overlay=overlay,
        diff=_policy_diff(general, effective),
    )


def _policy_diff(
    general: PopulationThresholdPolicy,
    overlay: PopulationThresholdPolicy,
) -> tuple[PopulationPolicyDiff, ...]:
    ignored = {
        "policy_id",
        "version",
        "status",
        "source_url",
        "source_version",
        "released_at",
    }
    result: list[PopulationPolicyDiff] = []
    for item in fields(PopulationThresholdPolicy):
        if item.name in ignored:
            continue
        general_value = getattr(general, item.name)
        overlay_value = getattr(overlay, item.name)
        if general_value != overlay_value:
            result.append(
                PopulationPolicyDiff(
                    field=item.name,
                    general_value=_audit_value(general_value),
                    overlay_value=_audit_value(overlay_value),
                )
            )
    return tuple(result)


def _normalize_identifier(value: str) -> str:
    return value.strip().upper()


def _audit_value(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _validate_registry() -> None:
    ruleset = active_ruleset()
    if ruleset.population_policy_id not in POPULATION_POLICY_REGISTRY:
        raise RuntimeError("active ruleset references an unknown population policy")
    if POPULATION_POLICY_REGISTRY[ruleset.population_policy_id].status != "published":
        raise RuntimeError("active ruleset references an unpublished population policy")
    for key, policy in POPULATION_POLICY_REGISTRY.items():
        if key != policy.policy_id:
            raise RuntimeError(f"population policy registry key mismatch: {key}")
        if not policy.source_url.startswith("https://"):
            raise RuntimeError(f"population policy source must use HTTPS: {key}")
        if not policy.pm2_maximum < policy.bs1_minimum < policy.ba1_minimum:
            raise RuntimeError(f"population policy thresholds overlap or are unordered: {key}")

    exact_contexts: set[tuple[str, str, str]] = set()
    for key, overlay in CSPEC_OVERLAY_REGISTRY.items():
        if key != overlay.overlay_id:
            raise RuntimeError(f"CSpec overlay registry key mismatch: {key}")
        if overlay.population_policy_id not in POPULATION_POLICY_REGISTRY:
            raise RuntimeError(f"CSpec overlay references an unknown population policy: {key}")
        if not overlay.source_url.startswith("https://"):
            raise RuntimeError(f"CSpec overlay source must use HTTPS: {key}")
        exact_context = (
            overlay.ruleset_id,
            _normalize_identifier(overlay.gene_id),
            _normalize_identifier(overlay.disease_id),
        )
        if exact_context in exact_contexts:
            raise RuntimeError(f"duplicate exact CSpec overlay context: {key}")
        exact_contexts.add(exact_context)


_validate_registry()
