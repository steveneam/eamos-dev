from decimal import Decimal

from app.services.acmg_policy_registry import resolve_population_policy


def test_general_population_policy_is_versioned_when_no_exact_cspec_matches() -> None:
    resolution = resolve_population_policy(
        gene_symbol="RPE65",
        gene_ids=("HGNC:10294",),
        disease_ids=("MONDO:0008765",),
    )

    assert resolution.overlay is None
    assert resolution.effective_policy.policy_id == "acmg_svi_general_frequency_v1"
    assert resolution.effective_policy.ba1_minimum == Decimal("0.05")
    assert resolution.diff == ()


def test_exact_gene_disease_cspec_has_deterministic_precedence_and_auditable_diff() -> None:
    resolution = resolve_population_policy(
        gene_symbol="RPE65",
        gene_ids=("HGNC:10294",),
        disease_ids=("MONDO:0100368",),
    )

    assert resolution.overlay is not None
    assert resolution.overlay.overlay_id == "clingen_cspec_gn120_rpe65_v1"
    assert resolution.overlay.version == "1.0.0"
    assert resolution.effective_policy.policy_id == "clingen_cspec_gn120_rpe65_frequency_v1"
    assert resolution.effective_policy.ba1_minimum == Decimal("0.008")
    assert resolution.effective_policy.bs1_minimum == Decimal("0.0008")
    assert resolution.effective_policy.pm2_maximum == Decimal("0.0002")
    assert {(item.field, item.general_value, item.overlay_value) for item in resolution.diff} >= {
        ("ba1_minimum", "0.05", "0.008"),
        ("bs1_minimum", "0.01", "0.0008"),
        ("pm2_maximum", "0.0001", "0.0002"),
        ("pm2_maximum_inclusive", "false", "true"),
        ("allow_maximum_observed_frequency_fallback", "true", "false"),
    }


def test_gene_only_match_cannot_apply_a_disease_specific_cspec() -> None:
    resolution = resolve_population_policy(
        gene_symbol="RPE65",
        gene_ids=("HGNC:10294",),
        disease_ids=(),
    )

    assert resolution.overlay is None
    assert resolution.effective_policy is resolution.general_policy
