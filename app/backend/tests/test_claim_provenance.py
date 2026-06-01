from __future__ import annotations

import json

from app.cli import eamos_press
from app.services.claim_provenance import build_assertion, evaluate_claims


def _popfreq_pm2_vs_bs1_payload() -> tuple[dict, dict, dict[str, str]]:
    worksheet = {
        "criteria": [
            {
                "code": "BS1",
                "state": "met",
                "assertion_level": "vcep_specified",
                "rationale": "VCEP asserts BS1 because the Latino/Admixed American AF is too high.",
                "source": "ClinGen Hearing Loss VCEP",
                "evidence_refs": ["ClinGen ERepo accession 3b9c6310"],
            }
        ]
    }
    payload = {
        "variant_summary_rows": [
            {
                "gene": "USH2A",
                "transcript_hgvs": "c.2276G>T",
                "protein_change": None,
                "genomic_hg38": "1-216247118-C-A",
            }
        ],
        "population_frequency_detail": {
            "dataset": "gnomad_r4",
            "variant_id": "1-216247118-C-A",
            "sequencing_type": "joint",
            "allele_frequency": 0.0014603125824794708,
            "allele_count": 2357,
            "allele_number": 1614080,
            "homozygote_count": 5,
            "popmax_frequency": 0.001817,
            "popmax_population": "amr",
            "genetic_ancestry_groups": [
                {
                    "id": "amr",
                    "allele_frequency": 0.00212,
                    "allele_count": 632,
                    "allele_number": 298100,
                    "homozygote_count": 3,
                }
            ],
            "source_url": "https://gnomad.broadinstitute.org/variant/1-216247118-C-A",
        },
        "call_cards": {
            "cards": [
                {
                    "card_id": "population_frequency",
                    "title": "Population Frequency",
                    "primary_label": "Low Frequency (0.182% max AF)",
                    "support_badges": [
                        {"text": "PM2", "kind": "acmg"},
                        {"text": "Max AMR: 0.182%", "kind": "metric"},
                        {"text": "AC 2357", "kind": "metric"},
                    ],
                    "ui_color_theme": "neutral_slate_state",
                    "source_status": "cache",
                    "provenance": [
                        "gnomAD gnomad_r4 joint",
                        "https://gnomad.broadinstitute.org/variant/1-216247118-C-A",
                    ],
                    "warnings": [],
                }
            ]
        },
        "report_profile": {"acmg_worksheet": worksheet},
    }
    evidence_map = {"clinical_consensus": {"acmg_worksheet": worksheet}}
    statuses = {"gnomad": "cache", "clinical_consensus": "cache", "clingen": "cache"}
    return payload, evidence_map, statuses


def test_popfreq_pm2_badge_is_contradicted_by_vcep_bs1_and_gnomad_facts() -> None:
    payload, evidence_map, statuses = _popfreq_pm2_vs_bs1_payload()

    result = evaluate_claims(payload, evidence_map, statuses, sections="popfreq")
    section = result["sections"][0]
    pm2_claim = next(
        claim for claim in section["claims"] if claim["claim_id"] == "popfreq.pm2_badge"
    )

    assert pm2_claim["verdict"] == "contradicted"
    assert pm2_claim["claim_level"] == "unsupported"
    assert "pill_claim_contradicts_source:PM2_vs_BS1" in pm2_claim["warnings"]
    assert "rarity_code_with_homozygotes" in pm2_claim["warnings"]
    assert any(fact["field"] == "BS1.state" for fact in pm2_claim["source_facts"])
    assert any(fact["field"] == "popmax_frequency" for fact in pm2_claim["source_facts"])
    assert result["summary"]["contradicted"] == 1

    assertion = build_assertion(result["sections"], mode="source_backed_pills")
    assert assertion == {
        "mode": "source_backed_pills",
        "passed": False,
        "failed_claim_ids": ["popfreq.pm2_badge"],
    }


def test_trials_empty_matched_terms_and_unsurfaced_protein_change_are_assertable() -> None:
    payload = {
        "variant_summary_rows": [
            {
                "gene": "USH2A",
                "transcript_hgvs": "c.2276G>T",
                "protein_change": None,
                "genomic_hg38": "1-216247118-C-A",
            }
        ],
        "report_profile": {
            "header": {
                "gene": "USH2A",
                "cdna": "c.2276G>T",
                "protein_change": None,
                "genomic_hg38": "1-216247118-C-A",
            },
            "molecular_context": {
                "protein_position": "759",
                "codon_change": "TGC>TTC",
                "provenance": [{"source": "sequence_context", "status": "cache"}],
                "warnings": [],
            },
            "gene_context_snapshot": {
                "source_status": "cache",
                "gene": "USH2A",
                "variant": {"hgvs_p": None},
            },
            "therapies_trials": {
                "trial_rows": [
                    {
                        "nct_id": "NCT05919342",
                        "title": "Early Heart Failure Trial",
                        "match_level": "gene_level",
                        "matched_terms": [],
                        "source_url": "https://clinicaltrials.gov/study/NCT05919342",
                        "warnings": ["clinical_trials_gene_level_fallback"],
                    }
                ],
                "provenance": [
                    {
                        "source": "ClinicalTrials.gov",
                        "status": "cache",
                        "query": {"query": "USH2A"},
                    }
                ],
            },
        },
    }

    result = evaluate_claims(
        payload,
        {},
        {"clinical_trials": "cache", "molecular_context": "cache"},
        sections="trials,protein",
    )
    trials = result["sections"][0]["claims"]
    protein = result["sections"][1]["claims"][0]

    assert trials[0]["claim_id"] == "trials.NCT05919342"
    assert trials[0]["verdict"] == "unsupported"
    assert "match_without_matched_terms" in trials[0]["warnings"]
    assert protein["claim_id"] == "protein.protein_change"
    assert protein["verdict"] == "contradicted"
    assert "protein_change_derivable_not_surfaced" in protein["warnings"]
    assert any(fact["value"] == "p.Cys759Phe" for fact in protein["source_facts"])

    assertion = build_assertion(result["sections"], mode="source_backed_pills")
    assert assertion["failed_claim_ids"] == ["trials.NCT05919342", "protein.protein_change"]


def test_eamos_press_cli_exits_two_when_selected_claim_is_contradicted(monkeypatch, capsys) -> None:
    payload, evidence_map, statuses = _popfreq_pm2_vs_bs1_payload()

    def fake_lookup_in_process(request, args):
        return {
            "payload": payload,
            "evidence_map": evidence_map,
            "source_statuses": statuses,
        }

    monkeypatch.setattr(eamos_press, "_lookup_in_process", fake_lookup_in_process)

    exit_code = eamos_press.main(
        [
            "USH2A:c.2276G>T",
            "--sections",
            "popfreq",
            "--assert-source-backed-pills",
            "--compact",
        ]
    )

    assert exit_code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["assert"]["failed_claim_ids"] == ["popfreq.pm2_badge"]
    assert output["resolved"]["gene"] == "USH2A"


def test_eamos_press_cli_batches_input_file(monkeypatch, tmp_path, capsys) -> None:
    payload, evidence_map, statuses = _popfreq_pm2_vs_bs1_payload()
    input_file = tmp_path / "variant-stack.txt"
    input_file.write_text(
        "\ufeffUSH2A:c.2276G>T\tpositive contradiction control\n" "USH2A c.2276G>T\n",
        encoding="utf-8",
    )

    def fake_lookup_in_process(request, args):
        return {
            "payload": payload,
            "evidence_map": evidence_map,
            "source_statuses": statuses,
        }

    monkeypatch.setattr(eamos_press, "_lookup_in_process", fake_lookup_in_process)

    exit_code = eamos_press.main(
        [
            "--input-file",
            str(input_file),
            "--sections",
            "popfreq",
            "--assert-source-backed-pills",
            "--compact",
        ]
    )

    assert exit_code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["count"] == 2
    assert [item["query"] for item in output["results"]] == [
        "USH2A:c.2276G>T",
        "USH2A c.2276G>T",
    ]
    assert all(
        item["assert"]["failed_claim_ids"] == ["popfreq.pm2_badge"] for item in output["results"]
    )
