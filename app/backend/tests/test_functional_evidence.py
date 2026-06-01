from __future__ import annotations

from types import SimpleNamespace

from app.services.functional_evidence import FunctionalEvidenceExtractor


def _variant(
    *,
    gene: str = "RPE65",
    transcript_hgvs: str = "NM_000329.3:c.11+5G>A",
    protein_change: str = "",
):
    return SimpleNamespace(
        gene=gene,
        transcript_hgvs=transcript_hgvs,
        protein_change=protein_change,
        dbsnp_rsid="",
        genomic_hg38="",
    )


class _StaticClinGenClient:
    def __init__(self, records: list[dict]) -> None:
        self.records = records

    def search(self, *, gene: str, hgvs: str, limit: int = 10) -> list[dict]:
        return self.records


class _FailingClinGenClient:
    def search(self, *, gene: str, hgvs: str, limit: int = 10) -> list[dict]:
        raise RuntimeError("ClinGen unavailable")


class _StaticClinVarClient:
    def __init__(self, xml_text: str) -> None:
        self.xml_text = xml_text
        self.calls = 0

    def fetch_vcv_xml(self, variation_id: str) -> str:
        self.calls += 1
        return self.xml_text


def test_clingen_ps3_supporting_counts_source_native_functional_study() -> None:
    extractor = FunctionalEvidenceExtractor(
        clingen_client=_StaticClinGenClient(
            [
                {
                    "uuid": "ps3-rpe65",
                    "metCodes": ["PS3_Supporting"],
                    "summaryDesc": (
                        "VCEP-member provided data from a mini-gene assay in HEK-293 cells "
                        "show that this variant reduces normal splicing and leads to >400x "
                        "reduction of mature mRNA, relative to the wild-type control "
                        "(PS3_Supporting, Guan et al., 2024)."
                    ),
                }
            ]
        )
    )

    summary = extractor.build_for_lookup(
        _variant(),
        {},
        allow_live=True,
    )

    assert summary.total_count == 1
    assert summary.source_breakdown.clingen == 1
    assert summary.evidence_codes == ["PS3"]
    assert summary.source_asserted_codes == ["PS3_Supporting"]
    assert summary.display_metrics.state == "emerging_deficit"
    assert summary.display_metrics.primary_label == "Functional Deficit"
    assert summary.display_metrics.acmg_badge_text == "PS3_Supporting"
    assert summary.display_metrics.verdict_source == "clingen"
    assert summary.display_metrics.study_count_badge_text == "1 Unique"
    assert summary.studies[0].pmid is None
    assert summary.studies[0].citation == "Guan et al., 2024"
    assert summary.studies[0].asserted_codes == ["PS3_Supporting"]


def test_clingen_bs3_supporting_counts_unique_pubmed_functional_studies() -> None:
    extractor = FunctionalEvidenceExtractor(
        clingen_client=_StaticClinGenClient(
            [
                {
                    "uuid": "bs3-rpe65",
                    "metCodes": ["BS3_Supporting"],
                    "summaryDesc": (
                        "The variant exhibited 110% or 55% enzymatic activity in two "
                        "retinoid isomerase assays relative to the wild-type control, "
                        "indicating that it largely preserves normal protein function "
                        "(PMID: 19431183, PMID: 16150724, BS3_Supporting)."
                    ),
                }
            ]
        )
    )

    summary = extractor.build_for_lookup(
        _variant(transcript_hgvs="NM_000329.3:c.1301C>T", protein_change="p.Ala434Val"),
        {},
        allow_live=True,
    )

    assert summary.total_count == 2
    assert summary.source_breakdown.clingen == 2
    assert summary.evidence_codes == ["BS3"]
    assert summary.source_asserted_codes == ["BS3_Supporting"]
    assert summary.display_metrics.state == "normal"
    assert summary.display_metrics.primary_label == "Normal Function"
    assert summary.display_metrics.acmg_badge_text == "BS3_Supporting"
    assert summary.display_metrics.verdict_source == "clingen"
    assert summary.display_metrics.study_count_badge_text == "2 Unique"
    assert {study.pmid for study in summary.studies} == {"16150724", "19431183"}


def test_clingen_source_native_functional_terms_include_transcript_and_model_assays() -> None:
    extractor = FunctionalEvidenceExtractor(
        clingen_client=_StaticClinGenClient(
            [
                {
                    "uuid": "ps3-rna",
                    "metCodes": ["PS3_Supporting"],
                    "summaryDesc": (
                        "RNA analysis by RT-PCR in a cell model showed abnormal splicing "
                        "for this variant (PS3_Supporting, Example et al., 2025)."
                    ),
                }
            ]
        )
    )

    summary = extractor.build_for_lookup(_variant(), {}, allow_live=True)

    assert summary.total_count == 1
    assert summary.studies[0].citation == "Example et al., 2025"


def test_clinvar_vcv_functional_comment_harvests_only_functional_pmids() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<ClinVarResult-Set>
  <VariationArchive VariationID="2356">
    <ClassifiedRecord>
      <ClinicalAssertionList>
        <ClinicalAssertion>
          <Classification>
            <Comment>Published functional studies using a zebrafish knock-in model suggest
            a damaging effect with decreased expression and impaired visual function
            (PMID: 35672333); This variant is associated with the following publications:
            (PMID: 12525556, PMID: 25262649).</Comment>
          </Classification>
        </ClinicalAssertion>
      </ClinicalAssertionList>
    </ClassifiedRecord>
  </VariationArchive>
</ClinVarResult-Set>"""
    extractor = FunctionalEvidenceExtractor(
        clinvar_client=_StaticClinVarClient(xml_text),
    )

    summary = extractor.build_for_lookup(
        _variant(gene="USH2A", transcript_hgvs="NM_206933.2:c.2276G>T"),
        {"clinvar": {"accession": "VCV000002356"}},
        allow_live=True,
    )

    assert summary.total_count == 1
    assert summary.source_breakdown.clinvar == 1
    assert summary.studies[0].pmid == "35672333"
    assert "12525556" not in {study.pmid for study in summary.studies}


def test_pubmed_parser_does_not_capture_clinvar_variation_id_as_pmid() -> None:
    extractor = FunctionalEvidenceExtractor(
        clingen_client=_StaticClinGenClient(
            [
                {
                    "uuid": "mixed-ids",
                    "metCodes": ["PS3_Supporting"],
                    "summaryDesc": (
                        "Expression of the variant in cells indicated altered protein function "
                        "(PMID: 31194252, ClinVar Variation ID: 638074) (PS3_Supporting)."
                    ),
                }
            ]
        )
    )

    summary = extractor.build_for_lookup(_variant(), {}, allow_live=True)

    assert {study.pmid for study in summary.studies} == {"31194252"}


def test_pubmed_functional_screen_requires_variant_alias_not_gene_only() -> None:
    extractor = FunctionalEvidenceExtractor()

    summary = extractor.build_for_lookup(
        _variant(),
        {
            "pubmed": {
                "articles": [
                    {
                        "pmid": "12345678",
                        "title": "RPE65 function in retinal cells",
                        "abstract": "A broad assay studied RPE65 expression.",
                    },
                    {
                        "pmid": "23456789",
                        "title": "Functional assay of RPE65 c.11+5G>A",
                        "abstract": "The NM_000329.3:c.11+5G>A variant altered splicing.",
                    },
                ]
            }
        },
    )

    assert summary.total_count == 1
    assert summary.source_breakdown.pubmed == 1
    assert summary.evidence_codes == []
    assert summary.display_metrics.state == "uncurated"
    assert summary.display_metrics.primary_label == "Functional Work Found - Not ACMG-graded"
    assert summary.display_metrics.acmg_badge_text == "No code asserted"
    assert summary.display_metrics.verdict_source == "uncurated"
    assert summary.display_metrics.study_count_badge_text == "1 Unique"
    assert summary.studies[0].pmid == "23456789"


def test_no_functional_evidence_has_neutral_call_card_metrics() -> None:
    summary = FunctionalEvidenceExtractor().build_for_lookup(_variant(), {})

    assert summary.total_count == 0
    assert summary.evidence_codes == []
    assert summary.source_asserted_codes == []
    assert summary.display_metrics.state == "none"
    assert summary.display_metrics.primary_label == "No Functional Data Available"
    assert summary.display_metrics.acmg_badge_text == "None"
    assert summary.display_metrics.verdict_source == "none"
    assert summary.display_metrics.study_count_badge_text == "0 Unique"


def test_conflicting_ps3_bs3_sources_flag_review_without_using_count_as_category() -> None:
    extractor = FunctionalEvidenceExtractor(
        clingen_client=_StaticClinGenClient(
            [
                {
                    "uuid": "ps3-rpe65",
                    "metCodes": ["PS3_Supporting"],
                    "summaryDesc": (
                        "A minigene assay showed abnormal splicing "
                        "(PMID: 23456789, PS3_Supporting)."
                    ),
                },
                {
                    "uuid": "bs3-rpe65",
                    "metCodes": ["BS3_Supporting"],
                    "summaryDesc": (
                        "A retinoid isomerase assay showed normal function "
                        "(PMID: 34567890, BS3_Supporting)."
                    ),
                },
            ]
        )
    )

    summary = extractor.build_for_lookup(_variant(), {}, allow_live=True)

    assert summary.total_count == 2
    assert summary.evidence_codes == ["PS3", "BS3"]
    assert summary.source_asserted_codes == ["PS3_Supporting", "BS3_Supporting"]
    assert summary.display_metrics.state == "conflict"
    assert summary.display_metrics.primary_label == "Conflicting Functional Data"
    assert summary.display_metrics.acmg_badge_text == "Review Required"
    assert summary.display_metrics.verdict_source == "conflict"
    assert summary.display_metrics.study_count_badge_text == "2 Unique"


def test_clingen_live_failure_records_warning_and_keeps_pubmed_hits() -> None:
    extractor = FunctionalEvidenceExtractor(clingen_client=_FailingClinGenClient())

    summary = extractor.build_for_lookup(
        _variant(),
        {
            "pubmed": {
                "articles": [
                    {
                        "pmid": "23456789",
                        "title": "Functional assay of RPE65 c.11+5G>A",
                        "abstract": "The NM_000329.3:c.11+5G>A variant altered splicing.",
                    }
                ]
            }
        },
        allow_live=True,
    )

    assert summary.total_count == 1
    assert summary.source_breakdown.pubmed == 1
    assert "functional_clingen_failed:RuntimeError" in summary.warnings


def test_clinvar_failed_source_status_skips_live_vcv_fetch() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<ClinVarResult-Set>
  <VariationArchive VariationID="2356">
    <ClassifiedRecord>
      <ClinicalAssertionList>
        <ClinicalAssertion>
          <Classification>
            <Comment>Published functional studies show altered expression (PMID: 35672333).</Comment>
          </Classification>
        </ClinicalAssertion>
      </ClinicalAssertionList>
    </ClassifiedRecord>
  </VariationArchive>
</ClinVarResult-Set>"""
    clinvar_client = _StaticClinVarClient(xml_text)
    extractor = FunctionalEvidenceExtractor(clinvar_client=clinvar_client)

    summary = extractor.build_for_lookup(
        _variant(),
        {"clinvar": {"accession": "VCV000002356"}},
        source_statuses={"clinvar": "fallback"},
        allow_live=True,
    )

    assert summary.total_count == 0
    assert summary.source_breakdown.clinvar == 0
    assert clinvar_client.calls == 0


def test_functional_evidence_dedupes_pmids_across_sources() -> None:
    extractor = FunctionalEvidenceExtractor(
        clingen_client=_StaticClinGenClient(
            [
                {
                    "uuid": "bs3-rpe65",
                    "metCodes": ["BS3_Supporting"],
                    "summaryDesc": (
                        "Retinoid isomerase assays preserve normal protein function "
                        "(PMID: 16150724, BS3_Supporting)."
                    ),
                }
            ]
        )
    )

    summary = extractor.build_for_lookup(
        _variant(transcript_hgvs="NM_000329.3:c.1301C>T", protein_change="p.Ala434Val"),
        {
            "pubmed": {
                "articles": [
                    {
                        "pmid": "16150724",
                        "title": "RPE65 p.Ala434Val enzyme assay",
                        "abstract": "The p.Ala434Val variant had normal protein function.",
                    }
                ]
            }
        },
        allow_live=True,
    )

    assert summary.total_count == 1
    assert summary.source_breakdown.clingen == 1
    assert summary.source_breakdown.pubmed == 1
    assert summary.studies[0].source_tags == ["clingen", "pubmed"]
