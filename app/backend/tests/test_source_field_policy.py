from __future__ import annotations

from app.data_sources import (
    DEFAULT_DATA_SOURCE_REGISTRY,
    ProductTier,
    SourceFieldPolicy,
)
from app.data_sources.registry import RESTRICTED_PREDICTOR_SOURCE_IDS


def test_myvariant_allows_only_gnomad_fields_for_public_actions() -> None:
    policy = SourceFieldPolicy()

    for field_path in ("gnomad_genome", "gnomad_genome.af", "gnomad_exome.ac"):
        assert policy.can_request("myvariant_gnomad_only", field_path).allowed
        assert policy.can_cache("myvariant_gnomad_only", field_path).allowed
        assert policy.can_normalize("myvariant_gnomad_only", field_path).allowed
        assert policy.can_serialize("myvariant_gnomad_only", field_path).allowed

    for field_path in (
        "cadd",
        "CADD.phred",
        "dbnsfp.revel.score",
        "dbnsfp.primateai.score",
        "spliceai.ds_ag",
        "revel",
        "PrimateAI-3D",
    ):
        decision = policy.can_request("myvariant_gnomad_only", field_path)

        assert decision.allowed is False
        assert decision.reason in {"restricted_field", "restricted_unlicensed"}


def test_myvariant_filter_payload_removes_restricted_and_unknown_fields() -> None:
    policy = SourceFieldPolicy()
    payload = {
        "gnomad_genome": {"af": 0.001, "ac": 2},
        "gnomad_exome": {"af": 0.002},
        "cadd": {"phred": 24.1},
        "dbnsfp": {"revel": {"score": 0.82}, "benign_unused": True},
        "unexpected": "drop",
    }

    assert policy.filter_payload("myvariant_gnomad_only", payload) == {
        "gnomad_genome": {"af": 0.001, "ac": 2},
        "gnomad_exome": {"af": 0.002},
    }


def test_restricted_predictor_sources_are_denied_for_public_and_prod() -> None:
    policy = SourceFieldPolicy()

    for source_id in RESTRICTED_PREDICTOR_SOURCE_IDS:
        record = DEFAULT_DATA_SOURCE_REGISTRY.get(source_id)
        field_path = record.restricted_fields[0]

        assert policy.can_request(source_id, field_path).allowed is False
        assert policy.can_cache(source_id, field_path).allowed is False
        assert policy.can_serialize(source_id, field_path).allowed is False
        assert (
            policy.can_serialize(source_id, field_path, product_tier="prod").reason
            == "restricted_unlicensed"
        )


def test_unknown_sources_and_fields_deny_by_default() -> None:
    policy = SourceFieldPolicy()

    unknown_source = policy.can_request("missing_source", "gnomad_genome")
    assert unknown_source.allowed is False
    assert unknown_source.reason == "unknown_source"

    unknown_field = policy.can_request("myvariant_gnomad_only", "clinvar.significance")
    assert unknown_field.allowed is False
    assert unknown_field.reason == "field_not_allowlisted"


def test_commercial_review_sources_deny_public_serialization() -> None:
    policy = SourceFieldPolicy()

    decision = policy.can_serialize(
        "intervar_pipeline_config",
        "intervar_acmg_classification",
    )

    assert decision.allowed is False
    assert decision.reason == "commercial_license_review_required"


def test_modern_ai_predictor_policy_allows_free_reviewed_sources_and_gates_review_lanes() -> None:
    policy = SourceFieldPolicy()

    alpha = policy.can_serialize(
        "google_deepmind_alphamissense_hg38",
        "am_pathogenicity",
    )
    ci_spliceai = policy.can_serialize("ci_spliceai_model", "max_delta")
    gpn_msa = policy.can_serialize("gpn_msa_hg38_scores", "gpn_msa_score")
    pangolin_public = policy.can_serialize(
        "pangolin_splice_effect_scores",
        "pangolin_max_delta",
    )
    esm1b_public = policy.can_serialize(
        "esm1b_hg38_assembled_scores",
        "esm1b_llr",
    )
    esm1b_fixture = policy.can_serialize(
        "esm1b_hg38_assembled_scores",
        "esm1b_llr",
        product_tier=ProductTier.INTERNAL_FIXTURE,
    )

    assert alpha.allowed is True
    assert ci_spliceai.allowed is True
    assert gpn_msa.allowed is True
    assert pangolin_public.allowed is False
    assert pangolin_public.reason == "commercial_license_review_required"
    assert esm1b_public.allowed is False
    assert esm1b_public.reason == "commercial_license_review_required"
    assert esm1b_fixture.allowed is True


def test_internal_fixture_can_preserve_warning_labeled_restricted_examples() -> None:
    policy = SourceFieldPolicy()
    payload = {
        "fixture_status": "internal_fixture_only",
        "license_warning": "restricted_unlicensed predictor fixture; not public/prod",
        "spliceai": {"DS_AG": 0.12, "DS_AL": 0.02},
    }

    assert policy.can_serialize(
        "illumina_spliceai_precomputed_hg38",
        "spliceai.DS_AG",
        product_tier=ProductTier.INTERNAL_FIXTURE,
    ).allowed
    assert (
        policy.filter_payload(
            "illumina_spliceai_precomputed_hg38",
            payload,
            product_tier="internal_fixture",
        )
        == payload
    )
    assert policy.filter_payload("illumina_spliceai_precomputed_hg38", payload) == {}


def test_internal_fixture_without_warning_still_filters_restricted_examples() -> None:
    policy = SourceFieldPolicy()
    payload = {"spliceai": {"DS_AG": 0.12}}

    assert (
        policy.filter_payload(
            "illumina_spliceai_precomputed_hg38",
            payload,
            product_tier="internal_fixture",
        )
        == {}
    )


def test_filter_payload_fails_closed_when_depth_bound_exceeded() -> None:
    policy = SourceFieldPolicy(max_filter_depth=1)
    payload = {"gnomad_genome": {"af": 0.001}}

    assert policy.filter_payload("myvariant_gnomad_only", payload) == {}


def test_filter_payload_fails_closed_when_node_bound_exceeded() -> None:
    policy = SourceFieldPolicy(max_filter_nodes=2)
    payload = {
        "gnomad_genome": {"af": 0.001},
        "gnomad_exome": {"af": 0.002},
    }

    assert policy.filter_payload("myvariant_gnomad_only", payload) == {}
