from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import pytest

STACK_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "fixtures"
    / "tools"
    / "clinvar_gene_agnostic_report_stack.json"
)
TRANSCRIPT_MODEL_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "fixtures"
    / "workbench"
    / "gene_viewer_transcript_models.json"
)

CATEGORY_SIGNIFICANCE = {
    "pathogenic_lp": {
        "Pathogenic",
        "Likely pathogenic",
        "Pathogenic/Likely pathogenic",
    },
    "benign_lb": {
        "Benign",
        "Likely benign",
        "Benign/Likely benign",
    },
    "vus": {"Uncertain significance"},
}

REQUIRED_VARIANT_TYPES = {
    "missense",
    "insertion",
    "deletion",
    "duplication",
    "splicing",
}


def _stack() -> dict:
    return json.loads(STACK_PATH.read_text(encoding="utf-8"))


def _variants(stack: dict) -> list[dict]:
    return [variant for gene_entry in stack["stack_genes"] for variant in gene_entry["variants"]]


def _transcript_model_records() -> list[dict]:
    return json.loads(TRANSCRIPT_MODEL_FIXTURE_PATH.read_text(encoding="utf-8"))["records"]


def test_clinvar_gene_agnostic_stack_has_requested_shape() -> None:
    stack = _stack()
    variants = _variants(stack)

    assert stack["verified_with"]["source"] == "NCBI ClinVar E-utilities"
    assert stack["selection_policy"]["reference_control_gene"] == "RPE65"
    assert len(stack["stack_genes"]) == 10
    assert {entry["gene"] for entry in stack["stack_genes"]}.isdisjoint({"RPE65"})
    assert len(variants) == 90

    category_counts = Counter(variant["category"] for variant in variants)
    assert category_counts == {
        "pathogenic_lp": 30,
        "benign_lb": 30,
        "vus": 30,
    }
    assert stack["coverage"]["category_counts"] == dict(category_counts)

    for gene_entry in stack["stack_genes"]:
        assert gene_entry["variant_count"] == 9
        assert len(gene_entry["variants"]) == 9
        assert Counter(variant["category"] for variant in gene_entry["variants"]) == {
            "pathogenic_lp": 3,
            "benign_lb": 3,
            "vus": 3,
        }


def test_clinvar_gene_agnostic_stack_rows_are_report_query_ready() -> None:
    stack = _stack()

    for variant in _variants(stack):
        category = variant["category"]
        assert variant["clinical_significance"] in CATEGORY_SIGNIFICANCE[category]
        assert variant["accession"].startswith("VCV")
        assert variant["clinvar_variation_id"].isdigit()
        assert variant["source_url"] == (
            "https://www.ncbi.nlm.nih.gov/clinvar/variation/" f"{variant['clinvar_variation_id']}/"
        )
        assert variant["title"].startswith(f"{variant['transcript']}({variant['gene']}):")
        assert variant["report_query"] == {
            "gene": variant["gene"],
            "cdna": variant["cdna"],
            "transcript_hgvs": f"{variant['transcript']}:{variant['cdna']}",
            "raw_text": f"{variant['gene']} {variant['transcript']}:{variant['cdna']}",
        }

    control = stack["reference_control_gene"]["control_variant"]
    assert control["gene"] == "RPE65"
    assert control["accession"] == "VCV001421454"
    assert control["report_query"]["transcript_hgvs"] == "NM_000329.3:c.260A>G"


def test_clinvar_gene_agnostic_stack_covers_required_variant_classes() -> None:
    stack = _stack()
    variants = _variants(stack)
    variant_type_counts = Counter(variant["variant_type"] for variant in variants)

    assert REQUIRED_VARIANT_TYPES.issubset(variant_type_counts)
    assert stack["coverage"]["variant_type_counts"] == dict(variant_type_counts)


@pytest.mark.parametrize(
    "gene_entry",
    _stack()["stack_genes"],
    ids=[entry["gene"] for entry in _stack()["stack_genes"]],
)
def test_clinvar_stack_report_queries_degrade_without_rpe65_bleed(
    client,
    gene_entry: dict,
) -> None:
    variant = gene_entry["variants"][0]

    response = client.post(
        "/api/v1/lookup",
        json={
            "gene": variant["gene"],
            "cdna": variant["cdna"],
            "transcript": variant["transcript"],
        },
    )

    assert response.status_code == 200
    payload = response.json()["report_payload"]
    profile = payload["report_profile"]
    assert profile["header"]["gene"] == variant["gene"]
    assert profile["header"]["cdna"] == variant["cdna"]

    serialized = json.dumps(payload)
    for forbidden in (
        "Leber congenital amaurosis 2",
        "1-68444869-T-C",
        "VCV001421454",
        "p.Asp87Gly",
    ):
        assert forbidden not in serialized


@pytest.mark.parametrize(
    "record",
    _transcript_model_records(),
    ids=[record["gene"] for record in _transcript_model_records()],
)
def test_clinvar_stack_representatives_hydrate_transcript_model_snapshots(
    client,
    record: dict,
) -> None:
    response = client.post(
        "/api/v1/lookup",
        json={
            "gene": record["gene"],
            "cdna": record["cdna"],
            "transcript": record["transcript"],
        },
    )

    assert response.status_code == 200
    payload = response.json()["report_payload"]
    profile = payload["report_profile"]
    snapshot = profile["gene_context_snapshot"]

    assert profile["header"]["gene"] == record["gene"]
    assert profile["header"]["cdna"] == record["cdna"]
    assert snapshot["source_status"] == "fixture"
    assert snapshot["gene"] == record["gene"]
    assert snapshot["transcript"] == record["transcript"]
    assert len(snapshot["exons"]) == len(record["exons"])
    assert len(snapshot["introns"]) == len(record["introns"])
    assert snapshot["variant"]["hgvs_c"] == record["cdna"]
    assert snapshot["variant"]["membership"] == "exon"
    assert snapshot["variant"]["genomic_hg38"] == record["variant"]["genomic_hg38"]
    assert snapshot["zoom_segments"]
    assert snapshot["zoom_sequences"]["reference_window_sequence"]
    assert snapshot["workbench_link"]["url"].startswith(f"/workbench?gene={record['gene']}&")
    assert "transcript_model_from_ensembl_rest_fixture" in snapshot["warnings"]
    assert "transcript_model_from_rpe65_fixture_scaffold" not in snapshot["warnings"]

    serialized = json.dumps(payload)
    for forbidden in (
        "Leber congenital amaurosis 2",
        "1-68444869-T-C",
        "VCV001421454",
        "p.Asp87Gly",
    ):
        assert forbidden not in serialized


@pytest.mark.skipif(
    os.getenv("EAMOS_VERIFY_CLINVAR_STACK") != "1",
    reason="Set EAMOS_VERIFY_CLINVAR_STACK=1 to refresh-check the stack against live ClinVar summaries.",
)
def test_clinvar_gene_agnostic_stack_matches_live_clinvar_summaries() -> None:
    stack = _stack()
    variants = _variants(stack) + [stack["reference_control_gene"]["control_variant"]]
    by_id = {variant["clinvar_variation_id"]: variant for variant in variants}

    for batch_start in range(0, len(variants), 100):
        batch = variants[batch_start : batch_start + 100]
        params = urllib.parse.urlencode(
            {
                "db": "clinvar",
                "retmode": "json",
                "id": ",".join(variant["clinvar_variation_id"] for variant in batch),
            }
        )
        with urllib.request.urlopen(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{params}",
            timeout=30,
        ) as response:
            payload = json.load(response)

        for uid in payload["result"]["uids"]:
            live = payload["result"][uid]
            fixture = by_id[uid]
            assert live["accession"] == fixture["accession"]
            assert (
                live["germline_classification"]["description"] == fixture["clinical_significance"]
            )
