from __future__ import annotations

from fastapi.testclient import TestClient


def test_evidence_submission_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/evidence-submissions",
        json={"variant_hgvs": "NM_000492.4:c.199C>T", "submitted_pmid": "35901234"},
    )

    assert response.status_code == 401


def test_evidence_submission_records_pubmed_and_clinvar_draft(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/evidence-submissions",
        json={
            "variant_hgvs": "NM_000492.4:c.199C>T",
            "submitted_pmid": "35901234",
            "curator_notes": "Functional assay supports PS3_Supporting.",
            "condition_name": "Cystic fibrosis",
            "assay_type": "protein activity assay",
            "functional_consequence": ["SO:0002218"],
            "method": "Variant activity was measured in a validated in vitro assay.",
            "result": "reduced activity compared with wild type",
            "evidence_codes": ["PS3_Supporting"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ledger_status"] == "recorded"
    assert body["pubmed"]["status"] == "unchecked"
    assert body["clinvar_tracking_id"].startswith("EAMOS-EVS-")
    assert body["clinvar_payload"]["payload_status"] == "ready_for_clinvar_dry_run"

    payload = body["clinvar_payload"]["payload"]
    submission = payload["noClassificationSubmission"][0]
    assert submission["variantSet"]["variant"][0]["hgvs"] == "NM_000492.4:c.199C>T"
    assert submission["conditionSet"]["condition"][0]["name"] == "Cystic fibrosis"
    functional = submission["functionalObservedIn"][0]
    assert functional["methodCitation"] == [{"db": "PubMed", "id": "35901234"}]
    assert payload["eamosEvidenceCodes"] == ["PS3_Supporting"]


def test_evidence_submission_rejects_non_hgvs_variant(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/evidence-submissions",
        json={"variant_hgvs": "CFTR p.Leu441fs", "submitted_pmid": "35901234"},
    )

    assert response.status_code == 422


def test_evidence_submission_marks_incomplete_clinvar_payload(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/evidence-submissions",
        json={
            "variant_hgvs": "NM_000492.4:c.199C>T",
            "submitted_pmid": "PMID:35901234",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["submitted_pmid"] == "35901234"
    assert body["clinvar_payload"]["payload_status"] == "draft_needs_curator_fields"
    assert "condition_name" in body["clinvar_payload"]["missing_required_fields"]
    assert "clinvar_payload_needs_curator_fields" in body["warnings"]
