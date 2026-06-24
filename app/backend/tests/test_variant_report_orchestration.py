from __future__ import annotations

import json
import re

import pytest

from app.schemas.lookup import SearchInputInterpretation
from app.services.report_extraction_plan import ReportExtractionPlanBuilder
from app.services.search_input_resolver import SearchInputResolution, SourceSpecificInputs
from app.tools.base import ToolResult

_FORBIDDEN_ACMG_POPULATION_METRICS = re.compile(
    r"\bgnomad\b|\b(?:AF|AC|AN)\s*[=:]?\s*\d|allele[_ -]?(?:frequency|count|number)|"
    r"\bpopmax\b|\bhom(?:ozygote)?(?:[_ -]?count)?\b|"
    r"\b(?:afr|ami|amr|asj|eas|fin|mid|nfe|remaining|sas)\b|"
    r"age[_ -]?distribution|bin[_ -]?(?:edges|freq)|n_(?:smaller|larger)|"
    r">\s*250k\s+alleles",
    flags=re.IGNORECASE,
)


def _lookup_payload(client, gene: str, cdna: str) -> dict:
    response = client.post(
        "/api/v1/lookup?include_lazy_sections=true",
        json={"gene": gene, "cdna": cdna},
    )
    assert response.status_code == 200
    return response.json()["report_payload"]


def _assert_section_3_population_frequency(profile: dict, payload: dict) -> None:
    population = profile["population_frequency"]
    assert population["section_number"] == 3
    assert population["section_id"] == "section-3-population-frequency"
    assert population["panel_id"] == "gnomad-expansion"
    assert population["detail_ref"] == "population_frequency_detail"
    assert population["variant_id"] == payload["population_frequency_detail"]["variant_id"]
    assert population["visual_scale"]["basis"] == "popmax_frequency"
    assert population["visual_scale"]["max_group_id"] == "nfe"
    assert [group["id"] for group in population["visual_groups"]] == [
        "nfe",
        "afr",
        "ami",
        "amr",
        "asj",
        "eas",
        "fin",
        "mid",
        "remaining",
        "sas",
    ]
    assert all("genetic ancestry" in group["label"] for group in population["visual_groups"])
    assert population["visual_groups"][0]["is_popmax"] is True
    assert population["visual_groups"][0]["xx"]["allele_count"] == 1
    assert population["visual_groups"][0]["xy"]["allele_number"] == 17902
    assert population["visual_groups"][0]["exome"]["allele_count"] == 2
    assert population["visual_groups"][0]["genome"]["allele_number"] == 11152
    assert population["overall"]["total"]["allele_count"] == 2
    assert population["overall"]["total"]["exome"]["allele_number"] == 73500
    assert population["overall"]["total"]["genome"]["allele_count"] == 0
    assert population["overall"]["xx"]["allele_number"] == 67488
    assert population["overall"]["xy"]["allele_frequency"] == 0.0000172
    assert population["visual_groups"][1]["data_state"] == "zero_observed"
    assert population["source_rows"][0]["group_id"] == "nfe"
    assert {hist["scope"] for hist in population["age_histograms"]} == {"overall_release_samples"}
    assert all(hist["group_id"] is None for hist in population["age_histograms"])
    histograms_by_key = {
        (hist["sequencing_type"], hist["series_kind"]): hist
        for hist in population["age_histograms"]
    }
    assert set(histograms_by_key) == {
        ("exome", "variant_carriers"),
        ("genome", "variant_carriers"),
        ("exome", "all_individuals"),
        ("genome", "all_individuals"),
    }
    assert histograms_by_key[("exome", "variant_carriers")]["bins"][3]["count"] == 1
    assert histograms_by_key[("exome", "all_individuals")]["bins"][6]["count"] == 108358
    assert "age_distribution_scope:overall_release_samples" in population["warnings"]
    assert "per_genetic_ancestry_age_distribution_not_available" in population["warnings"]


def _assert_no_population_metrics_in_section_2_or_acmg(profile: dict) -> None:
    disease_text = json.dumps(profile["disease_mechanism"], sort_keys=True).lower()
    assert "gnomad" not in disease_text
    assert "popmax" not in disease_text
    assert "allele_frequency" not in disease_text
    assert "homozygote" not in disease_text
    for row in profile["acmg_worksheet"]["criteria"]:
        assert not _FORBIDDEN_ACMG_POPULATION_METRICS.search(row.get("rationale") or "")
        if row["code"] in {"PM2", "BA1", "BS1"} and row["state"] != "not_assessed":
            assert row["assertion_level"] in {"source_asserted", "eamos_hint"}


def _computed_rows(payload: dict) -> dict:
    computed = payload["eamos_computed_classification"]
    return {row["code"]: row for row in computed["per_criterion"]}


def test_lookup_returns_typed_variant_report_profile(client) -> None:
    response = client.post(
        "/api/v1/lookup?include_lazy_sections=true",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 200
    report_payload = response.json()["report_payload"]
    profile = report_payload["report_profile"]
    assert report_payload["report_generated_at"]
    assert report_payload["report_data_currency"]["generated_at"] == report_payload[
        "report_generated_at"
    ]
    data_currency_sources = {
        source["source"]: source for source in report_payload["report_data_currency"]["sources"]
    }
    assert data_currency_sources["gnomad"]["source_version"] == "gnomad_r4"
    assert data_currency_sources["gnomad"]["status"] == "unknown"
    assert profile["header"]["gene"] == "RPE65"
    assert profile["header"]["cdna"] == "c.260A>G"
    assert profile["header"]["updated_at"] == report_payload["report_generated_at"]
    assert profile["header"]["genomic_hg38"] == "1-68444869-T-C"
    assert profile["header"]["classification_source"] == "ClinVar"
    assert profile["interpretation_summary"]["mode"] == "deterministic"
    assert "clinical_consensus" in profile["interpretation_summary"]["fact_refs"]
    assert profile["expert_panel"] is None
    assert profile["acmg_worksheet"]["classification"] == "Uncertain significance"
    assert profile["acmg_worksheet"]["classification_source"] == "ClinVar"
    _assert_section_3_population_frequency(profile, report_payload)
    _assert_no_population_metrics_in_section_2_or_acmg(profile)
    assert (
        report_payload["population_frequency_detail"]["source_url"]
        == "https://gnomad.broadinstitute.org/variant/1-68444869-T-C?dataset=gnomad_r4"
    )
    assert (
        profile["population_frequency"]["source_url"]
        == report_payload["population_frequency_detail"]["source_url"]
    )

    plan = profile["extraction_plan"]
    assert plan["mode"] == "structured"
    assert plan["canonical_identity"]["gene"] == "RPE65"
    assert plan["canonical_identity"]["cdna"] == "c.260A>G"
    assert plan["source_query_bundle"]["publication_gene_fallback_terms"] == ["RPE65"]
    assert "RPE65" not in plan["source_query_bundle"]["publication_variant_terms"]
    assert "c.260A>G" in plan["source_query_bundle"]["publication_variant_terms"]

    targets = {target["section_id"]: target for target in plan["section_targets"]}
    assert targets["computational_deep_dive"]["match_level"] == "variant_level"
    assert targets["acmg_worksheet"]["match_level"] == "variant_level"
    assert targets["publications"]["match_level"] == "variant_level"
    assert targets["gene_context_snapshot"]["match_level"] == "variant_level"
    assert targets["therapies_trials"]["match_level"] == "gene_level"
    assert "clinical_trials_gene_level_fallback" in targets["therapies_trials"]["warnings"]

    computational = profile["computational_deep_dive"]
    predictor_names = {row["name"] for row in computational["predictors"]}
    assert {"REVEL", "CADD PHRED", "PrimateAI-3D", "MetaLR", "SpliceAI"} <= predictor_names
    predictor_versions = {
        row["name"]: row["version"] for row in computational["predictors"] if row["version"]
    }
    assert predictor_versions["REVEL"] == "dbNSFP v5.3.1 / REVEL v1.3"
    assert predictor_versions["CADD PHRED"] == "CADD v1.7 GRCh38"
    assert predictor_versions["PrimateAI-3D"] == "dbNSFP v5.3.1 / PrimateAI-3D"
    predictors_by_name = {row["name"]: row for row in computational["predictors"]}
    assert predictors_by_name["REVEL"]["calibrated_label"] == "Moderate damaging"
    assert predictors_by_name["REVEL"]["calibration_bucket"] == "Likely pathogenic"
    assert predictors_by_name["REVEL"]["calibration_version"] == "PMID:36413997"
    assert predictors_by_name["CADD PHRED"]["calibration_bucket"] == "VUS"
    assert predictors_by_name["SpliceAI"]["calibration_bucket"] == "VUS"
    assert predictors_by_name["SpliceAI"]["calibration_method"] == (
        "Walker 2023 / ClinGen SVI splicing"
    )
    assert predictors_by_name["PrimateAI-3D"]["calibration_bucket"] is None
    assert predictors_by_name["MetaLR"]["calibration_bucket"] is None
    assert computational["spliceai_max_delta"] == 0.12
    assert computational["spliceai_consequence"] == "acceptor_loss"
    assert {row["name"] for row in computational["conservation"]} == {
        "phyloP100way",
        "GERP++ RS",
    }
    assert {item["source"] for item in computational["provenance"]} >= {
        "dbNSFP",
        "CADD",
        "SpliceAI",
    }
    assert "alphamissense_on_hold" not in computational["warnings"]
    assert "alphamissense_missing_source_file" in computational["warnings"]
    assert "esm1b_missing_source_file" in computational["warnings"]
    computational_card = next(
        card for card in report_payload["call_cards"]["cards"] if card["card_id"] == "computational"
    )
    computational_badges = [badge["text"] for badge in computational_card["support_badges"]]
    assert computational_card["primary_label"] == "Damaging"
    assert computational_badges[:2] == ["REVEL: 0.78", "CADD PHRED: 23.4"]
    assert "REVEL: 0.82" not in computational_badges
    assert "MetaLR: 0.78" not in computational_badges

    disease = profile["disease_mechanism"]
    assert disease["primary_condition"] == "Leber congenital amaurosis 2"
    assert disease["inheritance"] == "AR"
    assert disease["penetrance"] is None
    assert disease["gene_disease_validity"] == "definitive"
    assert "OMIM:204100" in disease["disease_ids"]
    assert "MedGen:C1859844" in disease["disease_ids"]
    assert "ORPHA:65" in disease["disease_ids"]
    assert "penetrance_not_source_backed" in disease["warnings"]
    assert {item["source"] for item in disease["provenance"]} >= {
        "HGNC",
        "ClinGen Gene-Disease Validity",
        "NCBI MedGen",
        "Orphadata",
    }

    gene_context = profile["gene_context_snapshot"]
    assert gene_context["section_id"] == "section-2-gene-context"
    assert gene_context["panel_id"] == "gene-context-snapshot"
    assert gene_context["source_status"] == "fixture"
    assert gene_context["gene"] == "RPE65"
    assert gene_context["transcript"] == "NM_000329.3"
    assert len(gene_context["exons"]) == 14
    assert len(gene_context["introns"]) == 13
    assert gene_context["variant"]["membership"] == "exon"
    assert gene_context["variant"]["exon_number"] == 4
    assert gene_context["variant"]["genomic_hg38"] == "1-68444869-T-C"
    assert gene_context["zoom_window"]["display_cds_start"] == 217
    assert gene_context["zoom_segments"][2]["exon_number"] == 4
    assert gene_context["workbench_link"]["url"] == (
        "/workbench?gene=RPE65&cdna=c.260A%3EG&transcript=NM_000329.3"
    )
    assert "transcript_model_from_rpe65_fixture_scaffold" in gene_context["warnings"]

    molecular = profile["molecular_context"]
    assert molecular["chromosome"] == "1"
    assert molecular["strand"] == "-"
    assert molecular["exon"] == "4"
    assert molecular["codon_change"] == "GAC>GGC"
    assert molecular["protein_position"] == "87"
    assert molecular["domain"] is None
    assert molecular["hotspot_flag"] is None
    assert molecular["loeuf"] == 1.0
    assert (
        molecular["clingen_haploinsufficiency"]
        == "Gene Associated with Autosomal Recessive Phenotype (30)"
    )
    assert molecular["overlapping_cnvs"] == []
    molecular_versions = {
        item["source"]: item["version"] for item in molecular["provenance"] if item["version"]
    }
    assert (
        molecular_versions["gnomAD Gene Constraint"]
        == "gnomAD v4.1.1 gene constraint; ClinGen gene facts snapshot 2025-02-27"
    )
    assert (
        molecular_versions["ClinGen Dosage Sensitivity"]
        == "ClinGen Dosage Sensitivity curation 2025-02-27"
    )
    assert molecular_versions["sequence_context"] == "workbench_rpe65"
    assert "protein_domain_source_not_hydrated" in molecular["warnings"]
    assert "hotspot_source_not_hydrated" in molecular["warnings"]
    assert "structural_cnv_overlap_source_not_hydrated" in molecular["warnings"]

    criteria = {row["code"]: row for row in profile["acmg_worksheet"]["criteria"]}
    assert criteria["PM2"]["state"] == "met"
    assert criteria["PM2"]["assertion_level"] == "eamos_hint"
    assert criteria["PM2"]["source"] == "Eamos worksheet scaffold"
    assert criteria["PM5"]["assertion_level"] == "eamos_hint"
    assert criteria["PP3"]["assertion_level"] == "eamos_hint"
    assert criteria["PS3"]["assertion_level"] == "not_assessed"
    assert profile["therapies_trials"]["trial_rows"] == []
    assert "structured_clinical_trials_require_live_api" in profile["therapies_trials"]["warnings"]
    assert "clinical_trials_structured_rows_unavailable" in profile["therapies_trials"]["warnings"]
    section_signals = profile["section_signals"]
    assert section_signals == sorted(
        section_signals,
        key=lambda item: (-item["priority"], item["section_id"]),
    )
    signals_by_id = {item["section_id"]: item for item in section_signals}
    assert signals_by_id["population_frequency"]["relevance"] == "exact_variant"
    assert signals_by_id["population_frequency"]["source_strength"] == "primary_db"
    assert signals_by_id["population_frequency"]["default_open"] is True
    assert signals_by_id["computational_deep_dive"]["default_open"] is True
    assert signals_by_id["publications"]["default_open"] is True
    assert signals_by_id["therapies_trials"]["relevance"] == "disease_discovery"
    assert signals_by_id["therapies_trials"]["default_open"] is True
    assert signals_by_id["therapies_trials"]["priority"] < signals_by_id["acmg_worksheet"][
        "priority"
    ]
    assert "clinical_trials_structured_rows_unavailable" in signals_by_id["therapies_trials"][
        "data_notes"
    ]
    assert {item["source"] for item in profile["provenance"]} >= {"gnomad", "clinvar", "pubmed"}
    population_card = next(
        card
        for card in report_payload["call_cards"]["cards"]
        if card["card_id"] == "population_frequency"
    )
    assert population_card["interaction"] == {
        "action": "scroll_and_expand",
        "target_section_id": "section-3-population-frequency",
        "target_panel_id": "gnomad-expansion",
    }

    computed = report_payload["eamos_computed_classification"]
    computed_rows = _computed_rows(report_payload)
    assert computed["acmg_version_pin"]["framework"] == ("Richards-2015 + Tavtigian-2020 points")
    assert computed["tier"] == "VUS"
    assert computed["net_points"] == 3
    assert computed["sum_pathogenic"] == 3
    assert computed["sum_benign"] == 0
    assert computed["conflict"] == {"is_conflicting": False, "reason": None}
    assert computed["ba1_override"] is False
    assert 0.49 < computed["posterior"] < 0.51
    assert computed_rows["PM2"]["triggered"] is True
    assert computed_rows["PM2"]["applied_strength"] == "supporting"
    assert computed_rows["PM2"]["source_db"] == "gnomAD"
    assert computed_rows["PM2"]["source_version"] == "gnomad_r4"
    assert computed_rows["PP3"]["triggered"] is True
    assert computed_rows["PP3"]["applied_strength"] == "moderate"
    assert computed_rows["PP3"]["source_db"] == "REVEL"
    assert computed_rows["PP3"]["source_version"] == "dbNSFP v5.3.1 / REVEL v1.3"
    assert computed_rows["BA1"]["triggered"] is False
    assert computed_rows["BP4"]["triggered"] is False


def test_lookup_rpe65_splice_functional_prior_is_source_scoped(client) -> None:
    report_payload = _lookup_payload(client, "RPE65", "c.11+5G>A")
    profile = report_payload["report_profile"]
    plan = profile["extraction_plan"]

    assert plan["canonical_identity"]["gene"] == "RPE65"
    assert plan["canonical_identity"]["cdna"] == "c.11+5G>A"
    assert plan["canonical_identity"]["transcript_hgvs"] == "NM_000329.3:c.11+5G>A"
    assert profile["header"]["gene"] == "RPE65"
    assert profile["header"]["cdna"] == "c.11+5G>A"
    assert profile["header"]["genomic_hg38"] != "1-68444869-T-C"
    assert profile["header"]["classification_source"] == "ClinGen"

    functional = report_payload["functional_evidence"]
    assert functional["total_count"] == 1
    assert functional["evidence_codes"] == ["PS3"]
    assert functional["source_asserted_codes"] == ["PS3_Supporting"]
    assert functional["display_metrics"]["primary_label"] == "Functional Deficit"
    lab_card = next(
        card
        for card in report_payload["call_cards"]["cards"]
        if card["card_id"] == "lab_functional"
    )
    assert lab_card["source_status"] == "fixture"
    assert {badge["text"] for badge in lab_card["support_badges"]} == {
        "PS3_Supporting",
        "1 Unique",
    }

    criteria = {row["code"]: row for row in profile["acmg_worksheet"]["criteria"]}
    assert criteria["PS3"]["state"] == "met"
    assert criteria["PS3"]["assertion_level"] == "source_asserted"
    assert criteria["PS3"]["source"] == "ClinGen Evidence Repository"
    computed = report_payload["eamos_computed_classification"]
    computed_rows = _computed_rows(report_payload)
    assert computed["tier"] == "VUS"
    assert computed["net_points"] == 1
    assert computed_rows["PS3"]["triggered"] is True
    assert computed_rows["PS3"]["applied_strength"] == "supporting"
    assert computed_rows["PS3"]["source_db"] == "ClinGen Evidence Repository"
    assert computed_rows["PM2"]["triggered"] is False
    assert "c.260A>G" not in json.dumps(profile)
    assert report_payload["population_frequency_detail"]["allele_frequency"] is None


def test_lookup_structured_clinical_trials_flow_into_report_profile(client) -> None:
    class StructuredTrialsTool:
        def get_trial_matches(self, *args, **kwargs):
            warnings = ["variant_level_trial_not_found:using_lower_match_level"]
            return ToolResult(
                source="clinical_trials",
                status="live",
                request_identity={"gene": "RPE65"},
                summary={
                    "trial_rows": [
                        {
                            "nct_id": "NCT01234567",
                            "title": "RPE65 gene therapy in inherited retinal disease",
                            "status": "RECRUITING",
                            "phase": "Phase 1/Phase 2",
                            "conditions": ["Leber congenital amaurosis"],
                            "interventions": ["AAV2-RPE65"],
                            "locations": ["Inherited Retinal Disease Center"],
                            "match_level": "gene_level",
                            "matched_terms": ["RPE65"],
                            "source_url": "https://clinicaltrials.gov/study/NCT01234567",
                            "warnings": [
                                "clinical_trials_gene_level_match:not_variant_specific",
                                "clinical_trials_discovery_only:not_eligibility",
                            ],
                        }
                    ],
                    "total": 1,
                    "query_term": "RPE65",
                    "source_url": "https://clinicaltrials.gov/search?term=RPE65",
                    "warnings": warnings,
                },
                warnings=warnings,
                raw=None,
                source_url="https://clinicaltrials.gov/search?term=RPE65",
            )

        def get_trials_summary(self, gene: str) -> str:
            return "fallback summary should not be used"

    registry = client.app.state.lookup_service.tool_registry
    original_tool = registry["clinical_trials"]
    registry["clinical_trials"] = StructuredTrialsTool()
    try:
        report_payload = _lookup_payload(client, "RPE65", "c.260A>G")
    finally:
        registry["clinical_trials"] = original_tool

    trials = report_payload["report_profile"]["therapies_trials"]
    assert len(trials["trial_rows"]) == 1
    row = trials["trial_rows"][0]
    assert row["nct_id"] == "NCT01234567"
    assert row["match_level"] == "gene_level"
    assert row["matched_terms"] == ["RPE65"]
    assert row["source_url"] == "https://clinicaltrials.gov/study/NCT01234567"
    assert "clinical_trials_gene_level_target_only" in trials["warnings"]
    assert "variant_level_trial_not_found:using_lower_match_level" in trials["warnings"]
    assert trials["provenance"][0]["status"] == "live"


def test_lookup_abca4_tinlarebant_trial_flows_into_report_profile(client) -> None:
    class TinlarebantTrialsTool:
        def get_trial_matches(self, *args, **kwargs):
            warnings = [
                "clinical_trials_variant_level_not_found",
                "variant_level_trial_not_found:using_lower_match_level",
            ]
            return ToolResult(
                source="clinical_trials",
                status="live",
                request_identity={
                    "gene": "ABCA4",
                    "variant_aliases": ["NM_000350.3:c.5461-10T>C", "c.5461-10T>C"],
                    "selected_query": '"Tinlarebant"',
                },
                summary={
                    "trial_rows": [
                        {
                            "nct_id": "NCT06388083",
                            "title": (
                                "A Phase 2/3 Study to Evaluate the Efficacy and Safety "
                                "of Tinlarebant in Subjects With Stargardt Disease"
                            ),
                            "status": "ACTIVE_NOT_RECRUITING",
                            "phase": "Phase 2/Phase 3",
                            "conditions": ["STGD1", "Stargardt Disease 1"],
                            "interventions": ["Tinlarebant", "Placebo"],
                            "locations": ["Belite Study Site - US08"],
                            "match_level": "disease_level",
                            "matched_terms": ["Tinlarebant"],
                            "source_url": "https://clinicaltrials.gov/study/NCT06388083",
                            "warnings": [
                                "clinical_trials_discovery_only:not_eligibility",
                                "clinical_trials_disease_level_match:not_variant_specific",
                            ],
                        }
                    ],
                    "total": 1,
                    "query_term": '"Tinlarebant"',
                    "source_url": "https://clinicaltrials.gov/search?term=Tinlarebant",
                    "warnings": warnings,
                },
                warnings=warnings,
                raw=None,
                source_url="https://clinicaltrials.gov/search?term=Tinlarebant",
            )

        def get_trials_summary(self, gene: str) -> str:
            return "fallback summary should not be used"

    registry = client.app.state.lookup_service.tool_registry
    original_tool = registry["clinical_trials"]
    registry["clinical_trials"] = TinlarebantTrialsTool()
    try:
        report_payload = _lookup_payload(client, "ABCA4", "c.5461-10T>C")
    finally:
        registry["clinical_trials"] = original_tool

    trials = report_payload["report_profile"]["therapies_trials"]
    assert len(trials["trial_rows"]) == 1
    row = trials["trial_rows"][0]
    assert row["nct_id"] == "NCT06388083"
    assert row["match_level"] == "disease_level"
    assert "Tinlarebant" in row["interventions"]
    assert row["source_url"] == "https://clinicaltrials.gov/study/NCT06388083"
    assert "clinical_trials_gene_level_target_only" in trials["warnings"]
    assert "variant_level_trial_not_found:using_lower_match_level" in trials["warnings"]


def test_lookup_clingen_identity_match_flows_into_expert_panel_provenance(client) -> None:
    class IdentityClingenTool:
        def get_evidence(self, *args, **kwargs):
            identity_match = {
                "tier": "transcript_hgvs",
                "source_field": "hgvs",
                "requested": "NM_000350.3:c.5461-10T>C",
                "matched": "NM_000350.3:c.5461-10T>C",
                "normalized_requested": "nm_000350.3:c.5461-10t>c",
                "normalized_matched": "nm_000350.3:c.5461-10t>c",
                "auto_attach_allowed": True,
            }
            return ToolResult(
                source="clingen",
                status="local",
                request_identity={"gene": "ABCA4"},
                summary={
                    "gene": "ABCA4",
                    "classification": "Pathogenic",
                    "review_status": "approved",
                    "conditions": ["ABCA4-related retinopathy"],
                    "accession": "64d8e05f-18c1-4092-9ce7-8880f952e96e",
                    "identity_match": identity_match,
                    "criteria": ["PVS1_Strong", "PM3_Very Strong", "PP4"],
                    "assertion_method": "ABCA4 VCEP",
                    "source_url": "https://erepo.clinicalgenome.org/evrepo/",
                    "expert_panel": {
                        "vcep": {
                            "id": "50140",
                            "name": "ABCA4 VCEP",
                            "affiliation_id": "50140",
                            "last_curated_date": "2026-04-28",
                            "vcep_url": "https://erepo.clinicalgenome.org/evrepo/",
                        },
                        "final_classification": "pathogenic",
                        "narrative": "ABCA4 VCEP assertion for NM_000350.3:c.5461-10T>C.",
                        "criteria": [
                            {
                                "code": "PM3",
                                "applied_strength": "PM3_Very Strong",
                                "default_strength": "PM3",
                                "state": "met",
                                "assertion_level": "vcep_specified",
                                "source": "ClinGen Evidence Repository",
                                "evidence_refs": ["64d8e05f-18c1-4092-9ce7-8880f952e96e"],
                                "warnings": [],
                            }
                        ],
                        "source_scope": "ClinGen Evidence Repository - ABCA4 VCEP curation",
                        "provenance": {
                            "source_url": "https://erepo.clinicalgenome.org/evrepo/",
                            "fetched_at": "2026-04-30",
                            "source_version": "ClinGen Evidence Repository",
                            "identity_match": identity_match,
                        },
                    },
                },
                warnings=[],
                raw=None,
                source_url="https://erepo.clinicalgenome.org/evrepo/",
                source_version="ClinGen pytest snapshot",
            )

    registry = client.app.state.lookup_service.tool_registry
    original_tool = registry["clingen"]
    registry["clingen"] = IdentityClingenTool()
    try:
        report_payload = _lookup_payload(client, "ABCA4", "c.5461-10T>C")
    finally:
        registry["clingen"] = original_tool

    provenance = report_payload["report_profile"]["expert_panel"]["provenance"]
    assert provenance["source_version"] == "ClinGen pytest snapshot"
    assert provenance["identity_match"]["tier"] == "transcript_hgvs"
    assert provenance["identity_match"]["source_field"] == "hgvs"
    assert provenance["identity_match"]["auto_attach_allowed"] is True


def test_lookup_clingen_expert_panel_without_identity_match_does_not_attach(client) -> None:
    class NoIdentityClingenTool:
        def get_evidence(self, *args, **kwargs):
            return ToolResult(
                source="clingen",
                status="local",
                request_identity={"gene": "ABCA4"},
                summary={
                    "gene": "ABCA4",
                    "classification": "Pathogenic",
                    "expert_panel": {
                        "vcep": {
                            "id": "50140",
                            "name": "ABCA4 VCEP",
                            "affiliation_id": "50140",
                            "last_curated_date": "2026-04-28",
                            "vcep_url": "https://erepo.clinicalgenome.org/evrepo/",
                        },
                        "final_classification": "pathogenic",
                        "narrative": "Narrative text mentions NM_000350.3:c.5461-10T>C.",
                        "criteria": [],
                        "source_scope": "ClinGen Evidence Repository - ABCA4 VCEP curation",
                        "provenance": {
                            "source_url": "https://erepo.clinicalgenome.org/evrepo/",
                            "fetched_at": "2026-04-30",
                            "source_version": "ClinGen Evidence Repository",
                        },
                    },
                },
                warnings=[],
                raw=None,
                source_url="https://erepo.clinicalgenome.org/evrepo/",
                source_version="ClinGen pytest snapshot",
            )

    registry = client.app.state.lookup_service.tool_registry
    original_tool = registry["clingen"]
    registry["clingen"] = NoIdentityClingenTool()
    try:
        report_payload = _lookup_payload(client, "ABCA4", "c.5461-10T>C")
    finally:
        registry["clingen"] = original_tool

    assert report_payload["report_profile"]["expert_panel"] is None


def test_lookup_cftr_leu441_frameshift_requires_confirmation_without_report_metrics(
    client,
) -> None:
    response = client.post("/api/v1/lookup", json={"search_text": "CFTR:p.Leu441fs"})

    assert response.status_code == 200
    body = response.json()
    interpretation = body["search_interpretation"]
    payload = body["report_payload"]
    assert interpretation["gene"] == "CFTR"
    assert interpretation["protein_change"] == "p.Leu441fs"
    assert interpretation["mode"] == "suggestions"
    assert interpretation["requires_confirmation"] is True
    assert interpretation["candidates"][0]["display_label"] == "CFTR c.1321_1323del (p.Leu441del)"
    assert payload["report_title"] == "Variant search recommendations"
    assert payload["report_profile"] is None
    assert payload["call_cards"] is None
    assert payload["population_frequency_detail"] is None


@pytest.mark.parametrize(
    ("gene", "cdna"),
    [
        ("USH2A", "c.2276G>T"),
        ("BRCA1", "c.5266dup"),
        ("RPGRIP1", "c.1997C>T"),
    ],
)
def test_lookup_non_rpe65_variants_degrade_without_rpe65_fixture_bleed(
    client,
    gene: str,
    cdna: str,
) -> None:
    report_payload = _lookup_payload(client, gene, cdna)
    profile = report_payload["report_profile"]

    assert profile["header"]["gene"] == gene
    assert profile["header"]["cdna"] == cdna
    assert profile["header"]["classification"] is None
    assert profile["header"]["classification_source"] is None
    assert profile["interpretation_summary"]["fact_refs"] == ["header"]

    assert profile["disease_mechanism"]["primary_condition"] is None
    assert profile["disease_mechanism"]["disease_ids"] == []
    assert profile["molecular_context"]["loeuf"] is None
    assert profile["molecular_context"]["clingen_haploinsufficiency"] is None
    assert profile["molecular_context"]["codon_change"] != "GAC>GGC"
    assert profile["molecular_context"]["protein_position"] != "87"

    assert profile["computational_deep_dive"]["predictors"] == []
    assert profile["computational_deep_dive"]["spliceai_max_delta"] is None
    assert profile["acmg_worksheet"]["criteria"] == []
    computed = report_payload["eamos_computed_classification"]
    assert computed["tier"] == "VUS"
    assert computed["net_points"] == 0
    assert computed["sum_pathogenic"] == 0
    assert computed["sum_benign"] == 0
    assert all(row["triggered"] is False for row in computed["per_criterion"])
    assert report_payload["publications_literature"]["total_count"] == 0
    assert report_payload["functional_evidence"]["total_count"] == 0
    assert report_payload["call_cards"]["cards"][0]["primary_label"] == "No Population Data"
    assert (
        report_payload["call_cards"]["cards"][0]["source_status"]
        == profile["population_frequency"]["source_status"]
    )
    assert report_payload["population_frequency_detail"]["allele_frequency"] is None
    assert (
        report_payload["population_frequency_detail"]["unavailable_reason"]
        == "frequency_metrics_unavailable"
    )
    assert profile["population_frequency"]["visual_groups"] == []
    assert profile["population_frequency"]["unavailable_reason"] == "frequency_metrics_unavailable"
    assert "genetic_ancestry_groups_unavailable" in profile["population_frequency"]["warnings"]
    assert profile["gene_context_snapshot"]["source_status"] == "missing"
    assert profile["gene_context_snapshot"]["gene"] == gene
    assert profile["gene_context_snapshot"]["exons"] == []
    assert (
        "gene_context_snapshot_fixture_unavailable" in profile["gene_context_snapshot"]["warnings"]
    )
    signals = {signal["section_id"]: signal for signal in profile["section_signals"]}
    for section_id in (
        "expert_panel",
        "population_frequency",
        "computational_deep_dive",
        "gene_context_snapshot",
        "publications",
        "therapies_trials",
    ):
        assert section_id in signals
    assert signals["expert_panel"]["status"] == "empty"
    assert signals["therapies_trials"]["default_open"] is True
    assert "clinical_trials_structured_rows_unavailable" in profile["therapies_trials"][
        "warnings"
    ]
    assert "clinical_trials_structured_rows_unavailable" in signals["therapies_trials"][
        "data_notes"
    ]
    assert computed["limitations"] == []

    serialized = json.dumps(report_payload)
    for forbidden in (
        "Leber congenital amaurosis 2",
        "1-68444869-T-C",
        "VCV001421454",
        "GAC>GGC",
        "p.Asp87Gly",
        "38191234",
        "37042101",
        "35901234",
    ):
        assert forbidden not in serialized


def test_report_extraction_plan_blocks_variant_level_sections_for_gene_only_input() -> None:
    resolution = SearchInputResolution(
        gene="ABCA4",
        hgvs="",
        transcript=None,
        protein_change=None,
        kind="unknown",
        transcript_hgvs="",
        resolver_transcript=None,
        resolver_transcript_hgvs="",
        source_inputs=SourceSpecificInputs(literature_terms=("ABCA4",)),
    )
    interpretation = SearchInputInterpretation(
        submitted_text="the Stargardt gene variant",
        mode="suggestions",
        confidence="low",
        gene="ABCA4",
        requires_confirmation=True,
        exact_variant_available=False,
        warnings=["variant_detail_missing"],
    )

    plan = ReportExtractionPlanBuilder().build(
        resolution=resolution,
        interpretation=interpretation,
    )

    targets = {target.section_id: target for target in plan.section_targets}
    for section_id in (
        "computational_deep_dive",
        "acmg_worksheet",
        "publications",
        "population_frequency",
        "gene_context_snapshot",
    ):
        assert targets[section_id].match_level == "unavailable"

    assert targets["disease_mechanism"].match_level == "gene_level"
    assert targets["therapies_trials"].match_level == "gene_level"
    assert "variant_identity_unavailable:suggestions" in plan.warnings
