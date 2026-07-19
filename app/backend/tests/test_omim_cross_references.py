from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.run import (
    DiseaseMechanismSection,
    OmimCrossReference,
)
from app.services.omim_cross_references import (
    build_omim_cross_reference,
    normalize_omim_cross_references,
)


def test_mondo_supplied_omim_identifier_builds_a_canonical_non_evidentiary_link() -> None:
    reference, warning = build_omim_cross_reference(
        {
            "identifier": "OMIM:204100",
            "entry_type": "phenotype",
            "source_id": "mondo_disease_ontology",
            "source_record_id": "MONDO:0008765",
            "external_url": "https://attacker.test/ignored",
            "title": "protected content is ignored",
        }
    )

    assert warning is None
    assert reference is not None
    assert reference.identifier == "OMIM:204100"
    assert reference.entry_type == "phenotype"
    assert reference.origin_kind == "cross_reference"
    assert reference.external_link_provider == "omim_web"
    assert reference.external_url == "https://omim.org/entry/204100"
    assert reference.evidence_role == "identifier_only"
    assert reference.source_id == "mondo_disease_ontology"
    assert reference.source_record_id == "MONDO:0008765"
    assert reference.public_serialization_allowed is True
    assert reference.export_allowed is False
    assert {decision.action for decision in reference.policy_decisions} == {
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
    assert not hasattr(reference, "title")


def test_unknown_supplier_and_malformed_identifiers_fail_closed() -> None:
    references, warnings = normalize_omim_cross_references(
        [
            {
                "identifier": "OMIM:204100",
                "entry_type": "phenotype",
                "source_id": "omim_licensed_api",
                "source_record_id": "204100",
            },
            {
                "identifier": "OMIM #204100",
                "entry_type": "phenotype",
                "source_id": "mondo_disease_ontology",
                "source_record_id": "MONDO:0008765",
            },
            {
                "identifier": "OMIM:204100",
                "entry_type": "gene",
                "source_id": "mondo_disease_ontology",
                "source_record_id": "MONDO:0008765",
            },
        ]
    )

    assert references == []
    assert warnings == [
        "omim_cross_reference_supplier_unapproved",
        "omim_cross_reference_identifier_invalid",
        "omim_cross_reference_entry_type_invalid",
    ]


def test_report_serialization_requires_recorded_supplier_permission_and_denies_export() -> None:
    reference, warning = build_omim_cross_reference(
        {
            "identifier": "OMIM:204100",
            "entry_type": "phenotype",
            "source_id": "mondo_disease_ontology",
            "source_record_id": "MONDO:0008765",
        }
    )
    assert warning is None
    assert reference is not None

    with pytest.raises(ValidationError):
        OmimCrossReference(
            source_id="mondo_disease_ontology",
            source_record_id="MONDO:0008765",
            public_serialization_allowed=True,
            identifier="OMIM:204100",
            entry_type="phenotype",
            external_url="https://omim.org/entry/204100",
        )
    section = DiseaseMechanismSection(omim_cross_references=[reference])

    public = section.model_dump(mode="json")
    exported = section.model_dump(
        mode="json",
        context={"source_policy_action": "product_export"},
    )
    assert [item["identifier"] for item in public["omim_cross_references"]] == ["OMIM:204100"]
    assert exported["omim_cross_references"] == []


def test_schema_rejects_substituted_urls_and_requires_entry_type() -> None:
    reference, warning = build_omim_cross_reference(
        {
            "identifier": "OMIM:204100",
            "entry_type": "phenotype",
            "source_id": "mondo_disease_ontology",
            "source_record_id": "MONDO:0008765",
        }
    )
    assert warning is None
    assert reference is not None
    payload = reference.model_dump(mode="json")

    with pytest.raises(ValidationError):
        OmimCrossReference.model_validate(
            {**payload, "external_url": "https://example.test/redirect"}
        )

    payload.pop("entry_type")
    with pytest.raises(ValidationError):
        OmimCrossReference.model_validate(payload)
