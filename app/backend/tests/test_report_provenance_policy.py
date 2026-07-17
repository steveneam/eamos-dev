from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY
from app.schemas.run import (
    AssociatedCondition,
    DiseaseMechanismSection,
    ReportPayload,
    SourcePolicyDecision,
)
from app.services.report_provenance import source_provenance_from_mapping
from app.services.source_fact_policy import build_source_fact_policy_envelope


def test_private_source_table_provenance_normalizes_and_keeps_policy_envelope() -> None:
    provenance = source_provenance_from_mapping(
        {
            "source": "ClinGen Gene-Disease Validity",
            "status": "source_table",
            "query": {"gene": "RPE65"},
            "version": "private_clinical_source_table",
            "source_url": "https://search.clinicalgenome.org/kb/gene-validity",
            "warnings": [],
        }
    )

    assert provenance.status == "local"
    assert provenance.storage_kind == "private_source_table"
    assert provenance.source_id == "clingen_gene_validity"
    assert provenance.source_record_id == "gene=RPE65"
    assert provenance.public_serialization_allowed is True
    assert provenance.cache_allowed is True
    assert provenance.export_allowed is False
    assert provenance.terms_version_or_hash.startswith("sha256:")
    assert {decision.action for decision in provenance.policy_decisions} == {
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
    }

    section = DiseaseMechanismSection(provenance=[provenance])
    assert len(section.model_dump(mode="json")["provenance"]) == 1
    assert (
        section.model_dump(mode="json", context={"source_policy_action": "product_export"})[
            "provenance"
        ]
        == []
    )


def test_unregistered_source_table_is_visible_in_memory_but_filtered_from_public_output() -> None:
    provenance = source_provenance_from_mapping(
        {
            "source": "Unregistered Clinical Table",
            "status": "source_table",
            "query": {"disease_ids": ["MONDO:1", "MONDO:2"]},
        }
    )

    assert provenance.status == "local"
    assert provenance.query == {"disease_ids": "MONDO:1,MONDO:2"}
    assert provenance.public_serialization_allowed is False
    assert "source_table_policy_identity_unregistered" in provenance.warnings
    assert (
        DiseaseMechanismSection(provenance=[provenance]).model_dump(mode="json")["provenance"] == []
    )


def test_invalid_provenance_construction_returns_a_visible_warning_row() -> None:
    provenance = source_provenance_from_mapping(
        {
            "source": "Example public source",
            "status": "live",
            "query": {"gene": "RPE65"},
            "retrieved_at": "not-a-timestamp",
        }
    )

    assert provenance.status == "fallback"
    assert provenance.query == {"gene": "RPE65"}
    assert any(
        warning.startswith("provenance_validation_failed:") for warning in provenance.warnings
    )


def test_policy_decisions_recompute_and_override_stale_permission_booleans() -> None:
    decided_at = datetime(2026, 7, 17, tzinfo=timezone.utc)
    condition = AssociatedCondition(
        name="Synthetic condition",
        case_count=0,
        evidence_level="limited",
        inheritance="AR",
        source="fixture",
        public_serialization_allowed=True,
        export_allowed=True,
        cache_allowed=True,
        policy_decisions=[
            SourcePolicyDecision(
                action="public_serialize",
                field="name",
                outcome="denied",
                reason="test_denial",
                decided_at=decided_at,
            )
        ],
    )

    assert condition.public_serialization_allowed is False
    assert condition.export_allowed is False
    assert condition.cache_allowed is False
    assert condition.decision_at == decided_at
    assert condition.decision_reason == "public_serialize:name:test_denial"


def test_protected_legacy_fact_fails_closed_and_export_requires_explicit_allow() -> None:
    omim = AssociatedCondition(
        name="Identifier-only condition",
        case_count=0,
        evidence_level="limited",
        inheritance="AR",
        source="OMIM cross-reference",
    )
    legacy_public = AssociatedCondition(
        name="Synthetic fixture condition",
        case_count=0,
        evidence_level="limited",
        inheritance="AR",
        source="Eamos fixture",
    )
    payload = ReportPayload(
        patient_id="policy-test",
        associated_conditions=[omim, legacy_public],
    )

    assert [
        condition["name"] for condition in payload.model_dump(mode="json")["associated_conditions"]
    ] == ["Synthetic fixture condition"]
    assert (
        payload.model_dump(mode="json", context={"source_policy_action": "product_export"})[
            "associated_conditions"
        ]
        == []
    )


def test_terms_change_rebuilds_the_terms_fingerprint_and_decisions() -> None:
    source_id = "myvariant_gnomad_only"
    current = DEFAULT_DATA_SOURCE_REGISTRY.get(source_id)

    class OneRecordRegistry:
        def __init__(self, record):
            self.record = record

        def get(self, requested_source_id: str):
            if requested_source_id != source_id:
                raise KeyError(requested_source_id)
            return self.record

    first = build_source_fact_policy_envelope(
        source_id=source_id,
        field_paths=("gnomad_genome.af",),
        registry=OneRecordRegistry(replace(current, terms_status="terms-v1")),  # type: ignore[arg-type]
    )
    second = build_source_fact_policy_envelope(
        source_id=source_id,
        field_paths=("gnomad_genome.af",),
        registry=OneRecordRegistry(replace(current, terms_status="terms-v2")),  # type: ignore[arg-type]
    )

    assert first["terms_version_or_hash"] != second["terms_version_or_hash"]
    assert first["policy_decisions"] is not second["policy_decisions"]
