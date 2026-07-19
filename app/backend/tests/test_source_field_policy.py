from __future__ import annotations

from types import SimpleNamespace

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


def test_unknown_action_and_product_export_deny_without_raising() -> None:
    policy = SourceFieldPolicy()

    unknown = policy.decide(
        "myvariant_gnomad_only",
        "gnomad_genome.af",
        action="exception",
    )
    export = policy.can_export("myvariant_gnomad_only", "gnomad_genome.af")

    assert unknown.allowed is False
    assert unknown.reason == "unknown_action"
    assert export.allowed is False
    assert export.reason == "action_not_allowlisted"


def test_sensitive_sinks_require_explicit_action_and_field_allowlists() -> None:
    default_policy = SourceFieldPolicy()
    protected_actions = (
        "product_export",
        "log",
        "analyze",
        "backup",
        "stage",
        "restore",
        "raw_debug",
    )

    for action in protected_actions:
        decision = default_policy.decide(
            "myvariant_gnomad_only",
            "gnomad_genome.af",
            action=action,
        )
        assert decision.allowed is False
        assert decision.reason == "action_not_allowlisted"

    export_policy = SourceFieldPolicy(
        action_field_allowlists={
            "myvariant_gnomad_only": {
                "product_export": ("gnomad_genome.af",),
            }
        }
    )
    assert export_policy.can_export("myvariant_gnomad_only", "gnomad_genome.af").allowed
    assert not export_policy.can_export("myvariant_gnomad_only", "gnomad_genome.ac").allowed
    assert export_policy.filter_payload(
        "myvariant_gnomad_only",
        {
            "gnomad_genome": {"af": 0.001, "ac": 2},
            "gnomad_exome": {"af": 0.002},
        },
        action="product_export",
    ) == {"gnomad_genome": {"af": 0.001}}


def test_unregistered_omim_lovd_and_mavedb_sources_deny_every_action() -> None:
    policy = SourceFieldPolicy()
    actions = (
        "acquire",
        "normalize",
        "cache",
        "public_serialize",
        "product_export",
        "log",
        "analyze",
        "backup",
        "stage",
        "restore",
        "raw_debug",
    )

    for source_id in ("omim_api", "lovd_api", "mavedb_bulk"):
        for action in actions:
            decision = policy.decide(source_id, "record.raw", action=action)
            assert decision.allowed is False
            assert decision.reason == "protected_source_not_registered"


def test_registered_mavedb_contract_does_not_authorize_archive_acquisition() -> None:
    policy = SourceFieldPolicy()

    acquire = policy.can_request("mavedb_cc0_bulk", "variant_scores.raw_score")
    serialize = policy.can_serialize("mavedb_cc0_bulk", "variant_scores.raw_score")

    assert acquire.allowed is False
    assert acquire.reason == "acquisition_not_approved"
    # Serialization remains a separate decision for a locally verified match.
    assert serialize.allowed is True


def test_reserved_omim_content_sources_deny_every_action() -> None:
    policy = SourceFieldPolicy()
    actions = (
        "acquire",
        "normalize",
        "cache",
        "public_serialize",
        "product_export",
        "log",
        "analyze",
        "backup",
        "stage",
        "restore",
        "raw_debug",
    )

    for source_id in ("omim_mim2gene", "omim_licensed_api"):
        for action in actions:
            decision = policy.decide(source_id, "gene_disease_validity", action=action)
            assert decision.allowed is False


def test_unknown_license_and_product_tier_deny_by_default() -> None:
    class RegistryWithUnknownLicense:
        def get(self, source_id: str):
            assert source_id == "source_with_unknown_license"
            return SimpleNamespace(license_status="unreviewed-new-license")

    policy = SourceFieldPolicy(registry=RegistryWithUnknownLicense())  # type: ignore[arg-type]

    license_decision = policy.can_serialize("source_with_unknown_license", "record.value")
    tier_decision = SourceFieldPolicy().can_serialize(
        "myvariant_gnomad_only",
        "gnomad_genome.af",
        product_tier="mystery_tier",
    )

    assert license_decision.allowed is False
    assert license_decision.reason == "unknown_license"
    assert tier_decision.allowed is False
    assert tier_decision.reason == "unknown_product_tier"
