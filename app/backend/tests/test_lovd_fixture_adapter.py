from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from pydantic import ValidationError
import pytest

from app.schemas.run import (
    EvidenceSourceSummary,
    LovdBasicObservation,
    LovdInstallationSource,
    ReportPayload,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.services.acmg_points_engine import compute_report_acmg_classification
from app.services.lovd_fixture_adapter import (
    LovdFixtureAdapter,
    LovdVariantQuery,
    validated_lovd_basic_records,
)
from app.services.report_call_cards import build_variant_report_call_cards
from app.services.search_input_resolver import SearchInputResolution
from app.services.variant_report_orchestrator import VariantReportDataOrchestrator

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "sources"
JSON_FIXTURE = FIXTURE_DIR / "lovd_global_variome_shared.synthetic.json"
ATOM_FIXTURE = FIXTURE_DIR / "lovd_global_variome_shared.synthetic.atom.xml"


def _query(**updates: str) -> LovdVariantQuery:
    values = {
        "genome_build": "GRCh38",
        "transcript_accession": "NM_000329.3",
        "hgvs_c": "c.260A>G",
    }
    values.update(updates)
    return LovdVariantQuery(**values)


def _json_fixture() -> dict:
    return json.loads(JSON_FIXTURE.read_text(encoding="utf-8"))


def _matched_section():
    return LovdFixtureAdapter().match_json(_json_fixture(), _query())


def _resolution() -> SearchInputResolution:
    return SearchInputResolution(
        gene="RPE65",
        hgvs="c.260A>G",
        transcript="NM_000329.3",
        protein_change="p.Asp87Gly",
        kind="cdna",
        transcript_hgvs="NM_000329.3:c.260A>G",
        resolver_transcript="NM_000329.3",
        resolver_transcript_hgvs="NM_000329.3:c.260A>G",
        genomic_hg38="1-68444869-T-C",
    )


def test_json_and_atom_fixtures_emit_the_same_exact_safe_observation() -> None:
    adapter = LovdFixtureAdapter()

    json_section = adapter.match_json(_json_fixture(), _query())
    atom_section = adapter.match_atom(ATOM_FIXTURE.read_text(encoding="utf-8"), _query())

    assert json_section.status == atom_section.status == "matched"
    assert json_section.live_request_performed is atom_section.live_request_performed is False
    assert json_section.observations == atom_section.observations

    observation = json_section.observations[0]
    assert observation.presence is True
    assert observation.installation.installation_id == "global_variome_shared_lovd"
    assert observation.installation.base_url == "https://databases.lovd.nl/shared"
    assert observation.source_record_id == (
        "global_variome_shared_lovd:variant:fixture-rpe65-c260ag"
    )
    assert observation.source_url == (
        "https://databases.lovd.nl/shared/variants/fixture-rpe65-c260ag"
    )
    assert observation.genome_build == "GRCh38"
    assert observation.transcript_accession == "NM_000329.3"
    assert observation.hgvs_c == "c.260A>G"
    assert observation.record_license == "CC-BY-4.0"
    assert observation.public_serialization_allowed is True
    assert observation.cache_allowed is False
    assert observation.export_allowed is False
    outcomes = {item.action: item.outcome for item in observation.policy_decisions}
    assert {
        "public_serialize": "allowed",
        "cache": "denied",
        "product_export": "denied",
        "log": "denied",
        "raw_debug": "denied",
    }.items() <= outcomes.items()


def test_installation_contract_keeps_live_rate_and_negative_cache_guards_frozen() -> None:
    installation = LovdInstallationSource()

    assert installation.live_access_enabled is False
    assert installation.maximum_requests_per_second == 5
    assert installation.minimum_negative_cache_ttl_seconds == 14_400
    assert installation.positive_cache_policy == "not_approved"
    assert installation.installation_permission_is_record_license is False

    with pytest.raises(ValidationError):
        LovdInstallationSource(maximum_requests_per_second=5.01)
    with pytest.raises(ValidationError):
        LovdInstallationSource(minimum_negative_cache_ttl_seconds=14_399)
    with pytest.raises(ValidationError):
        LovdInstallationSource(live_access_enabled=True)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        LovdInstallationSource(base_url="https://unreviewed.example/lovd")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("query_updates", "warning"),
    [
        ({"transcript_accession": "NM_000329.2"}, "exact_normalized_hgvs_match_not_found"),
        ({"genome_build": "GRCh37"}, "exact_normalized_hgvs_match_not_found"),
        ({"hgvs_c": "c.261A>G"}, "exact_normalized_hgvs_match_not_found"),
    ],
)
def test_exact_matching_rejects_transcript_build_and_hgvs_drift(
    query_updates: dict[str, str],
    warning: str,
) -> None:
    section = LovdFixtureAdapter().match_json(_json_fixture(), _query(**query_updates))

    assert section.status == "not_found"
    assert section.observations == []
    assert section.warnings == [warning]


def test_ambiguous_exact_matches_fail_closed() -> None:
    fixture = _json_fixture()
    fixture["records"].append(deepcopy(fixture["records"][0]))

    section = LovdFixtureAdapter().match_json(fixture, _query())

    assert section.status == "ambiguous"
    assert section.observations == []
    assert section.warnings == ["ambiguous_exact_normalized_hgvs_match"]


def test_unknown_license_and_prohibited_fields_are_denied_before_output() -> None:
    fixture = _json_fixture()
    record = fixture["records"][0]
    record["record_license"] = "unknown"
    record["patient"] = "sensitive-patient-value"
    record["phenotype"] = "sensitive-phenotype-value"
    record["classification"] = "Pathogenic"
    record["Times_reported"] = 42
    record["raw_payload"] = {"creator": "sensitive-creator-value"}

    section = LovdFixtureAdapter().match_json(fixture, _query())
    dumped = json.dumps(section.model_dump(mode="json"), sort_keys=True)

    assert section.status == "denied"
    assert section.observations == []
    assert section.warnings == ["record_license_denied"]
    for forbidden in (
        "sensitive-patient-value",
        "sensitive-phenotype-value",
        "Pathogenic",
        "Times_reported",
        "sensitive-creator-value",
        "raw_payload",
    ):
        assert forbidden not in dumped


def test_unreviewed_installation_and_record_url_fail_with_only_fixed_warning_codes() -> None:
    adapter = LovdFixtureAdapter()
    unreviewed_installation = _json_fixture()
    unreviewed_installation["installation_id"] = "https://unreviewed.example/lovd"
    denied_installation = adapter.match_json(unreviewed_installation, _query())

    unsafe_record = _json_fixture()
    unsafe_record["records"][0][
        "record_url"
    ] = "https://databases.lovd.nl.attacker.example/shared/variants/fixture-rpe65-c260ag"
    denied_record = adapter.match_json(unsafe_record, _query())

    assert denied_installation.warnings == ["installation_not_allowlisted"]
    assert denied_record.warnings == ["matched_record_invalid"]
    assert "unreviewed.example" not in json.dumps(denied_installation.model_dump(mode="json"))
    assert "attacker.example" not in json.dumps(denied_record.model_dump(mode="json"))


def test_atom_parser_rejects_entity_documents_without_echoing_source_text() -> None:
    document = (
        '<!DOCTYPE feed [<!ENTITY patient "sensitive-patient-value">]>'
        '<feed xmlns="http://www.w3.org/2005/Atom"><title>&patient;</title></feed>'
    )

    section = LovdFixtureAdapter().match_atom(document, _query())
    dumped = json.dumps(section.model_dump(mode="json"))

    assert section.status == "denied"
    assert section.warnings == ["fixture_document_invalid"]
    assert "sensitive-patient-value" not in dumped


def test_observation_model_forbids_classification_and_case_fields() -> None:
    observation = _matched_section().observations[0]
    raw = observation.model_dump(mode="json")
    raw["classification"] = "Pathogenic"

    with pytest.raises(ValidationError):
        LovdBasicObservation.model_validate(raw)

    unsafe_policy = observation.model_dump(mode="json")
    unsafe_policy["policy_decisions"][5]["reason"] = "sensitive-patient-value"
    with pytest.raises(ValidationError):
        LovdBasicObservation.model_validate(unsafe_policy)


def test_report_profile_admits_only_matched_fixture_and_blocks_product_export() -> None:
    section = _matched_section()
    profile = VariantReportDataOrchestrator().build_profile(
        resolution=_resolution(),
        interpretation=None,
        payload=ReportPayload(
            patient_id="lovd-fixture",
            report_generated_at="2026-07-19T00:00:00Z",
            variant_summary_rows=[
                VariantSummaryRow(
                    gene="RPE65",
                    transcript_hgvs="c.260A>G",
                    protein_change="p.Asp87Gly",
                    genomic_hg38="1-68444869-T-C",
                )
            ],
        ),
        evidence=[EvidenceSourceSummary(source="lovd_fixture", status="fixture")],
        evidence_map={"lovd_fixture": section.model_dump(mode="json")},
        evidence_statuses={"lovd_fixture": "fixture"},
    )

    assert profile.lovd_basic_records is not None
    public_dump = profile.model_dump(mode="json")
    assert public_dump["lovd_basic_records"]["status"] == "matched"
    export_dump = profile.model_dump(
        mode="json",
        context={"source_policy_action": "product_export"},
    )
    assert export_dump["lovd_basic_records"] is None

    denied = LovdFixtureAdapter().match_json(
        {**_json_fixture(), "fixture_status": "live_response"},
        _query(),
    )
    assert validated_lovd_basic_records(denied.model_dump(mode="json")) is None


def test_lovd_presence_cannot_change_acmg_points_or_any_call_card() -> None:
    section = _matched_section()
    baseline_payload = ReportPayload(patient_id="lovd-neutrality")
    lovd_payload = baseline_payload.model_copy(
        update={"report_profile": VariantReportProfile(lovd_basic_records=section)}
    )
    lovd_evidence = {
        "lovd_fixture": section.model_dump(mode="json"),
        "lovd": {
            "classification": "Pathogenic",
            "criteria": ["PVS1", "PS3"],
            "points": 999,
        },
    }
    lovd_statuses = {"lovd_fixture": "fixture", "lovd": "live"}

    baseline_acmg = compute_report_acmg_classification(baseline_payload, {}, {})
    lovd_acmg = compute_report_acmg_classification(lovd_payload, lovd_evidence, lovd_statuses)
    assert lovd_acmg == baseline_acmg

    baseline_cards = build_variant_report_call_cards(baseline_payload, {}, {})
    lovd_cards = build_variant_report_call_cards(lovd_payload, lovd_evidence, lovd_statuses)
    assert lovd_cards == baseline_cards
    assert [card.ui_color_theme for card in lovd_cards.cards] == [
        card.ui_color_theme for card in baseline_cards.cards
    ]
