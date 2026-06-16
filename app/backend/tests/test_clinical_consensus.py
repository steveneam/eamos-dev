from __future__ import annotations

import re
from types import SimpleNamespace

from app.schemas.run import AcmgCriteriaScaffold, AcmgCriterion, ReportPayload
from app.services import clinvar_vcv
from app.services.clinical_consensus import ClinicalConsensusBuilder
from app.services.functional_evidence import FunctionalEvidenceExtractor


def _payload() -> ReportPayload:
    return ReportPayload(
        patient_id="lookup_test",
        acmg_criteria_scaffold=AcmgCriteriaScaffold(
            criteria=[
                AcmgCriterion(code="PM2", verdict="met", note="Absent from gnomAD."),
                AcmgCriterion(code="PM5", verdict="met", note="Same codon evidence."),
                AcmgCriterion(code="PP3", verdict="met", note="Computational support."),
                AcmgCriterion(code="PS3", verdict="not_assessed"),
            ],
            note="Eamos scaffold note.",
        ),
    )


def _variant():
    return SimpleNamespace(gene="RPE65", transcript_hgvs="NM_000329.3:c.260A>G")


def test_clingen_consensus_outranks_clinvar_and_source_asserts_criteria() -> None:
    builder = ClinicalConsensusBuilder()

    result = builder.build_for_lookup(
        _variant(),
        _payload(),
        {
            "clinvar": {
                "classification": "Uncertain significance",
                "review_status": "criteria provided, single submitter",
                "accession": "VCV001421454",
            }
        },
        evidence_raw={
            "clingen": {
                "records": [
                    {
                        "uuid": "vcep-rpe65",
                        "classification": "Likely pathogenic",
                        "reviewStatus": "ClinGen RPE65 VCEP",
                        "metCodes": ["PM2_Moderate", "PP3_Supporting"],
                        "summaryDesc": (
                            "ClinGen VCEP source assertion records PM2_Moderate "
                            "and PP3_Supporting for this variant."
                        ),
                    }
                ]
            }
        },
        source_statuses={"clingen": "fixture", "clinvar": "fixture"},
    )

    assert result.ledger.classification == "Likely pathogenic"
    assert result.ledger.classification_source == "ClinGen"
    assert result.status == "fixture"
    criteria = {row.code: row for row in result.ledger.criteria}
    assert criteria["PM2"].assertion_level == "source_asserted"
    assert criteria["PM2"].strength == "Moderate"
    assert criteria["PM2"].source == "ClinGen Evidence Repository"
    assert criteria["PP3"].assertion_level == "source_asserted"
    assert criteria["PM5"].assertion_level == "eamos_hint"
    assert "ClinGen/VCEP source-reported classification" in (result.ledger.synthesis or "")


def test_clinvar_classification_and_vcv_criteria_fill_when_clingen_missing() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<ClinVarResult-Set>
  <VariationArchive VariationID="1421454">
    <ClassifiedRecord>
      <ClinicalAssertionList>
        <ClinicalAssertion>
          <Classification>
            <Comment>ACMG criteria applied: PM2 and PP3_Supporting (PMID: 35901234).</Comment>
          </Classification>
        </ClinicalAssertion>
      </ClinicalAssertionList>
    </ClassifiedRecord>
  </VariationArchive>
</ClinVarResult-Set>"""
    builder = ClinicalConsensusBuilder()

    result = builder.build_for_lookup(
        _variant(),
        _payload(),
        {
            "clinvar": {
                "classification": "Likely pathogenic",
                "review_status": "criteria provided, single submitter",
                "accession": "VCV001421454",
            }
        },
        evidence_raw={"clinvar": {"vcv_xml": xml_text}},
        source_statuses={"clingen": "missing", "clinvar": "live"},
    )

    assert result.ledger.classification == "Likely pathogenic"
    assert result.ledger.classification_source == "ClinVar"
    assert result.status == "live"
    criteria = {row.code: row for row in result.ledger.criteria}
    assert criteria["PM2"].assertion_level == "source_asserted"
    assert criteria["PM2"].source == "ClinVar VCV"
    assert criteria["PP3"].strength == "Supporting"
    assert criteria["PP3"].evidence_refs == ["PMID:35901234"]
    assert criteria["PS3"].assertion_level == "not_assessed"


def test_source_asserted_criteria_summary_excludes_eamos_hints() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<ClinVarResult-Set>
  <VariationArchive VariationID="1421454">
    <ClassifiedRecord>
      <ClinicalAssertionList>
        <ClinicalAssertion>
          <Classification>
            <Comment>ACMG criteria applied: PM2 and PS3_Moderate (PMID: 35901234).</Comment>
          </Classification>
        </ClinicalAssertion>
      </ClinicalAssertionList>
    </ClassifiedRecord>
  </VariationArchive>
</ClinVarResult-Set>"""
    payload = ReportPayload(
        patient_id="lookup_test",
        acmg_criteria_scaffold=AcmgCriteriaScaffold(
            criteria=[
                AcmgCriterion(code="PM2", verdict="met", note="Eamos frequency hint."),
                AcmgCriterion(code="PS3", verdict="not_assessed"),
                AcmgCriterion(code="BA1", verdict="met", note="Synthetic benign hint."),
            ],
        ),
    )
    builder = ClinicalConsensusBuilder()

    result = builder.build_for_lookup(
        _variant(),
        payload,
        {"clinvar": {"classification": "Likely pathogenic", "review_status": "single submitter"}},
        evidence_raw={"clinvar": {"vcv_xml": xml_text}},
        source_statuses={"clingen": "missing", "clinvar": "fixture"},
    )

    criteria = {row.code: row for row in result.ledger.criteria}
    assert result.ledger.classification == "Likely pathogenic"
    assert result.ledger.classification_source == "ClinVar"
    assert criteria["PM2"].assertion_level == "source_asserted"
    assert criteria["PM2"].source == "ClinVar VCV"
    assert criteria["PS3"].assertion_level == "source_asserted"
    assert criteria["PS3"].state == "met"
    assert criteria["BA1"].assertion_level == "eamos_hint"
    assert criteria["BA1"].source == "Eamos worksheet scaffold"
    assert result.summary["source_asserted_criteria"] == ["PM2", "PS3"]


def test_eamos_hints_do_not_overwrite_source_classification() -> None:
    payload = ReportPayload(
        patient_id="lookup_test",
        acmg_criteria_scaffold=AcmgCriteriaScaffold(
            criteria=[
                AcmgCriterion(code="BA1", verdict="met", note="Synthetic high-frequency hint."),
            ],
        ),
    )
    builder = ClinicalConsensusBuilder()

    result = builder.build_for_lookup(
        _variant(),
        payload,
        {"clinvar": {"classification": "Benign", "review_status": "single submitter"}},
        evidence_raw={
            "clingen": {
                "records": [
                    {
                        "uuid": "vcep-rpe65",
                        "classification": "Likely pathogenic",
                        "reviewStatus": "ClinGen RPE65 VCEP",
                        "metCodes": ["PM2_Moderate"],
                    }
                ]
            }
        },
        source_statuses={"clingen": "fixture", "clinvar": "fixture"},
    )

    assert result.ledger.classification == "Likely pathogenic"
    assert result.ledger.classification_source == "ClinGen"
    criteria = {row.code: row for row in result.ledger.criteria}
    assert criteria["BA1"].assertion_level == "eamos_hint"
    assert criteria["BA1"].source == "Eamos worksheet scaffold"


def test_acmg_rationales_scrub_raw_population_metrics() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<ClinVarResult-Set>
  <VariationArchive VariationID="1421454">
    <ClassifiedRecord>
      <ClinicalAssertionList>
        <ClinicalAssertion>
          <Classification>
            <Comment>PM2 met because gnomAD AF=0.00001, AC=2, AN=125748, popmax NFE.</Comment>
          </Classification>
        </ClinicalAssertion>
      </ClinicalAssertionList>
    </ClassifiedRecord>
  </VariationArchive>
</ClinVarResult-Set>"""
    payload = ReportPayload(
        patient_id="lookup_test",
        acmg_criteria_scaffold=AcmgCriteriaScaffold(
            criteria=[
                AcmgCriterion(
                    code="BA1",
                    verdict="met",
                    note="BA1 hint from allele_frequency=0.06 and >250k alleles.",
                ),
            ],
        ),
    )
    builder = ClinicalConsensusBuilder()

    result = builder.build_for_lookup(
        _variant(),
        payload,
        {"clinvar": {"classification": "Likely pathogenic", "review_status": "single submitter"}},
        evidence_raw={
            "clingen": {
                "records": [
                    {
                        "uuid": "vcep-rpe65",
                        "classification": "Likely pathogenic",
                        "reviewStatus": "ClinGen RPE65 VCEP",
                        "metCodes": ["PM2_Moderate"],
                        "summaryDesc": "PM2 due to gnomAD popmax NFE and homozygote_count=0.",
                    }
                ]
            },
            "clinvar": {"vcv_xml": xml_text},
        },
        source_statuses={"clingen": "fixture", "clinvar": "fixture"},
    )

    forbidden = re.compile(
        r"\bgnomad\b|\b(?:AF|AC|AN)\s*[=:]?\s*\d|allele_frequency|"
        r"\bpopmax\b|\bhomozygote\b|\bNFE\b|>\s*250k\s+alleles",
        flags=re.IGNORECASE,
    )
    for row in result.ledger.criteria:
        assert not forbidden.search(row.rationale or "")

    criteria = {row.code: row for row in result.ledger.criteria}
    assert criteria["PM2"].assertion_level == "source_asserted"
    assert criteria["BA1"].assertion_level == "eamos_hint"
    assert "Section 3 population frequency detail" in (criteria["PM2"].rationale or "")
    assert "Section 3 population frequency detail" in (criteria["BA1"].rationale or "")


def test_clinvar_vcv_over_size_limit_is_skipped_with_warning() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<ClinVarResult-Set>
  <VariationArchive VariationID="1421454">
    <ClassifiedRecord>
      <ClinicalAssertionList>
        <ClinicalAssertion>
          <Classification>
            <Comment>ACMG criteria applied: PM2 and PP3_Supporting (PMID: 35901234).</Comment>
          </Classification>
        </ClinicalAssertion>
      </ClinicalAssertionList>
    </ClassifiedRecord>
  </VariationArchive>
</ClinVarResult-Set>"""
    builder = ClinicalConsensusBuilder(clinvar_vcv_max_xml_bytes=64)

    result = builder.build_for_lookup(
        _variant(),
        _payload(),
        {"clinvar": {"classification": "Likely pathogenic", "review_status": "single submitter"}},
        evidence_raw={"clinvar": {"vcv_xml": xml_text}},
        source_statuses={"clingen": "missing", "clinvar": "fixture"},
    )

    criteria = {row.code: row for row in result.ledger.criteria}
    assert "clinical_consensus_clinvar_vcv_too_large" in result.warnings
    assert criteria["PM2"].assertion_level == "eamos_hint"
    assert "PP3" not in criteria or criteria["PP3"].assertion_level != "source_asserted"


def test_clinvar_vcv_parse_is_reused_by_functional_and_consensus(monkeypatch) -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<ClinVarResult-Set>
  <VariationArchive VariationID="1421454">
    <ClassifiedRecord>
      <ClinicalAssertionList>
        <ClinicalAssertion>
          <Classification>
            <Comment>Published functional assay showed decreased expression
            (PMID: 35672333, PS3_Supporting). ACMG criteria applied: PM2.</Comment>
          </Classification>
        </ClinicalAssertion>
      </ClinicalAssertionList>
    </ClassifiedRecord>
  </VariationArchive>
</ClinVarResult-Set>"""
    parse_calls = 0
    original_parse = clinvar_vcv._parse_vcv_texts

    def counting_parse(xml: str):
        nonlocal parse_calls
        parse_calls += 1
        return original_parse(xml)

    monkeypatch.setattr(clinvar_vcv, "_parse_vcv_texts", counting_parse)
    evidence_raw = {"clinvar": {"vcv_xml": xml_text}}
    evidence_map = {
        "clinvar": {
            "classification": "Likely pathogenic",
            "review_status": "criteria provided, single submitter",
            "accession": "VCV001421454",
        }
    }

    functional = FunctionalEvidenceExtractor().build_for_lookup(
        _variant(),
        evidence_map,
        evidence_raw=evidence_raw,
    )
    consensus = ClinicalConsensusBuilder().build_for_lookup(
        _variant(),
        _payload(),
        evidence_map,
        evidence_raw=evidence_raw,
        source_statuses={"clingen": "missing", "clinvar": "fixture"},
    )

    criteria = {row.code: row for row in consensus.ledger.criteria}
    assert parse_calls == 1
    assert functional.source_breakdown.clinvar == 1
    assert functional.studies[0].pmid == "35672333"
    assert criteria["PS3"].assertion_level == "source_asserted"
    assert criteria["PM2"].assertion_level == "source_asserted"
