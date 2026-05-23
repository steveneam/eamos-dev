from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.tools.base import FixtureBackedTool
from app.tools.clingen import ClingenTool
from app.tools.clinvar import ClinvarTool
from app.tools.computational_annotations import ComputationalAnnotationsTool
from app.tools.gene_disease import GeneDiseaseTool
from app.tools.litvar2 import LitVar2Tool
from app.tools.molecular_context import MolecularContextTool
from app.tools.pubmed import PubmedTool
from app.tools.spliceai import SpliceAiTool
from app.tools.variant_validator import VariantValidatorTool, _mutate_variant


def _settings(**overrides) -> Settings:
    return Settings(jwt_secret="test-secret", **overrides)


def test_spliceai_live_stub_requires_genomic_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_get(*args, **kwargs):
        raise AssertionError("SpliceAI live request should not run without genomic_hg38")

    monkeypatch.setattr("app.tools.spliceai.httpx.get", fail_get)
    variant = SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        genomic_hg38=None,
    )

    result = SpliceAiTool(_settings(use_real_apis=True)).get_evidence(variant)

    assert result.status == "live_stub"
    assert result.summary == {}
    assert result.request_identity == {"gene": "RPE65", "cdna": "c.260A>G"}
    assert "requires genomic coordinates" in result.warnings[0]


def test_variant_validator_does_not_fabricate_defaults_without_coordinates() -> None:
    variant = SimpleNamespace(genomic_hg38=None, variation_type="", consequence="")

    _mutate_variant(variant, {"gene": "RPE65", "variant_id": None})

    assert variant.genomic_hg38 is None
    assert variant.variation_type == ""
    assert variant.consequence == ""


def test_variant_validator_defaults_only_after_coordinate_resolution() -> None:
    variant = SimpleNamespace(genomic_hg38=None, variation_type="", consequence="")

    _mutate_variant(variant, {"gene": "RPE65", "variant_id": "1-68444869-T-C"})

    assert variant.genomic_hg38 == "1-68444869-T-C"
    assert variant.variation_type == "single nucleotide variant"
    assert variant.consequence == ""


def test_variant_validator_mutates_genomic_hgvs_and_indel_type() -> None:
    variant = SimpleNamespace(
        genomic_hg38=None,
        genomic_hgvs="",
        variation_type="",
        consequence="",
    )

    _mutate_variant(
        variant,
        {
            "gene": "BRCA1",
            "variant_id": "17-43057062-T-TG",
            "hgvs_genomic_description": "NC_000017.11:g.43057065dup",
        },
    )

    assert variant.genomic_hg38 == "17-43057062-T-TG"
    assert variant.genomic_hgvs == "NC_000017.11:g.43057065dup"
    assert variant.variation_type == "insertion"


def test_variant_validator_fallback_does_not_infer_coordinates_from_vep_raw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_get(*args, **kwargs):
        raise TimeoutError("VariantValidator unavailable")

    monkeypatch.setattr("app.tools.variant_validator.httpx.get", fail_get)
    variant = SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.11+5G>A",
        genomic_hg38=None,
        genomic_hgvs="",
        variation_type="",
        consequence="",
        search_input_resolution=None,
        vep_raw={
            "seq_region_name": "1",
            "start": 68449890,
            "allele_string": "G/A",
            "gene_symbol": "RPE65",
            "input": "NM_000329.3:c.11+5G>A",
        },
    )

    result = VariantValidatorTool(_settings(use_real_apis=True)).get_evidence(variant)

    assert result.status == "fallback"
    assert result.summary == {}
    assert result.request_identity == {"query": "NM_000329.3:c.11+5G>A"}
    assert variant.genomic_hg38 is None
    assert variant.genomic_hgvs == ""


def test_pubmed_no_hit_miss_uses_empty_raw(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"esearchresult": {"idlist": []}}

    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return Response()

    monkeypatch.setattr("app.tools.pubmed.httpx.get", fake_get)
    variant = SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        protein_change="p.Asp87Gly",
        dbsnp_rsid="rs1645931040",
    )

    result = PubmedTool(_settings(use_real_apis=True)).get_evidence(variant)

    assert len(calls) == 2
    assert result.status == "live"
    assert result.summary == {"articles": [], "total": 0}
    assert result.raw == {}
    assert result.raw is not None


def test_litvar2_quotes_variant_id_path_segments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class Response:
        def __init__(self, payload) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self.payload

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def get(self, url, params=None):
            calls.append(url)
            if url.endswith("/variant/autocomplete/"):
                return Response([{"litvar_id": "litvar@rs752238803##"}])
            assert "litvar%40rs752238803%23%23" in url
            return Response({"pmids": ["41234567"], "pmids_count": 1})

    monkeypatch.setattr("app.tools.litvar2.httpx.Client", Client)
    variant = SimpleNamespace(
        gene="USH2A",
        transcript_hgvs="c.2276G>T",
        protein_change="p.Cys759Phe",
        dbsnp_rsid="rs752238803",
    )

    result = LitVar2Tool(_settings(use_real_apis=True)).get_evidence(variant)

    assert result.status == "live"
    assert result.summary["total_publications"] == 1
    assert result.summary["articles"][0]["pmid"] == "41234567"
    assert "litvar%40rs752238803%23%23" in result.source_url
    assert len(calls) == 2


def test_clinvar_live_no_hit_does_not_return_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"esearchresult": {"idlist": []}}

    monkeypatch.setattr("app.tools.clinvar.httpx.get", lambda *args, **kwargs: Response())
    variant = SimpleNamespace(
        gene="RPGRIP1",
        transcript_hgvs="NM_020366.4:c.1997C>T",
        genomic_hg38="14-21324852-C-T",
        search_input_resolution=None,
    )

    result = ClinvarTool(_settings(use_real_apis=True)).get_evidence(variant)

    assert result.status == "live"
    assert result.request_identity == {"search_text": "NC_000014.9:g.21324852C>T"}
    assert result.summary["classification"] == "Unavailable"
    assert result.summary["review_status"] == "not found"
    assert result.summary["accession"] is None
    assert "clinvar_variant_not_found" in result.warnings


def test_clingen_fixture_filters_to_matching_variant() -> None:
    variant = SimpleNamespace(
        gene="RPE65",
        transcript_hgvs="NM_000329.3:c.260A>G",
        genomic_hgvs="",
        genomic_hg38="",
        protein_change="",
    )

    result = ClingenTool(_settings(use_real_apis=False)).get_evidence(variant)

    assert result.status == "fixture"
    assert result.summary["classification"] == "Likely pathogenic"
    assert result.summary["criteria"] == ["PM2_Moderate", "PM5_Supporting", "PP3_Supporting"]


def test_clingen_fixture_no_match_returns_missing_without_fixture_bleed() -> None:
    variant = SimpleNamespace(
        gene="ABCA4",
        transcript_hgvs="NM_000350.3:c.5882G>A",
        genomic_hgvs="",
        genomic_hg38="",
        protein_change="",
    )

    result = ClingenTool(_settings(use_real_apis=False)).get_evidence(variant)

    assert result.status == "missing"
    assert result.summary["classification"] == "Unavailable"
    assert result.raw == {"records": []}


def test_gene_disease_fixture_returns_source_backed_rpe65_mechanism() -> None:
    variant = SimpleNamespace(gene="RPE65")

    result = GeneDiseaseTool(_settings(use_real_apis=False)).get_evidence(variant)

    assert result.status == "fixture"
    assert result.summary["primary_condition"] == "Leber congenital amaurosis 2"
    assert result.summary["inheritance"] == "AR"
    assert result.summary["gene_disease_validity"] == "definitive"
    assert result.summary["penetrance"] is None
    assert "OMIM:204100" in result.summary["disease_ids"]
    assert "MedGen:C1859844" in result.summary["disease_ids"]
    assert "MONDO:0008765" in result.summary["disease_ids"]
    assert "ORPHA:65" in result.summary["disease_ids"]
    assert {item["source"] for item in result.summary["provenance"]} >= {
        "HGNC",
        "ClinGen Gene-Disease Validity",
        "NCBI MedGen",
        "Orphadata",
    }


def test_gene_disease_fixture_no_match_returns_missing_without_fixture_bleed() -> None:
    variant = SimpleNamespace(gene="ABCA4")

    result = GeneDiseaseTool(_settings(use_real_apis=False)).get_evidence(variant)

    assert result.status == "missing"
    assert result.summary["primary_condition"] is None
    assert result.summary["conditions"] == []
    assert result.raw is None
    assert "gene_disease_not_found" in result.warnings


def test_molecular_context_fixture_returns_source_backed_rpe65_context() -> None:
    variant = SimpleNamespace(
        gene="RPE65",
        genomic_hg38="1-68444869-T-C",
        transcript_hgvs="NM_000329.3:c.260A>G",
    )

    result = MolecularContextTool(_settings(use_real_apis=False)).get_evidence(variant)

    assert result.status == "fixture"
    assert result.summary["gnomad_constraint"]["loeuf"] == 1.0
    assert (
        result.summary["gnomad_constraint"]["version"]
        == "gnomAD v4.1.1 gene constraint; ClinGen gene facts snapshot 2025-02-27"
    )
    assert (
        result.summary["clingen_dosage"]["haploinsufficiency"]
        == "Gene Associated with Autosomal Recessive Phenotype (30)"
    )
    assert result.summary["overlapping_cnvs"] == []
    assert {item["source"] for item in result.summary["provenance"]} == {
        "gnomAD Gene Constraint",
        "ClinGen Dosage Sensitivity",
    }


def test_molecular_context_fixture_no_match_returns_missing_without_fixture_bleed() -> None:
    variant = SimpleNamespace(
        gene="ABCA4",
        genomic_hg38="1-94458394-G-A",
        transcript_hgvs="NM_000350.3:c.5882G>A",
    )

    result = MolecularContextTool(_settings(use_real_apis=False)).get_evidence(variant)

    assert result.status == "missing"
    assert result.summary["gnomad_constraint"] is None
    assert result.summary["clingen_dosage"] is None
    assert result.raw is None
    assert "molecular_context_not_found" in result.warnings


def test_computational_annotations_fixture_returns_source_labeled_rows() -> None:
    variant = SimpleNamespace(
        gene="RPE65",
        genomic_hg38="1-68444869-T-C",
        genomic_hgvs="NC_000001.11:g.68444869T>C",
        transcript_hgvs="NM_000329.3:c.260A>G",
        protein_change="p.Asp87Gly",
        dbsnp_rsid="",
    )

    result = ComputationalAnnotationsTool(_settings(use_real_apis=False)).get_evidence(variant)

    assert result.status == "fixture"
    names = {row["name"] for row in result.summary["predictors"]}
    assert {"SpliceAI", "REVEL", "CADD PHRED", "PrimateAI-3D", "MetaLR"} <= names
    assert "AlphaMissense" not in names
    assert result.summary["spliceai"]["max_delta"] == 0.12
    assert result.summary["spliceai"]["component_scores"]["DS_AL"] == 0.12
    assert {row["name"] for row in result.summary["conservation"]} == {
        "phyloP100way",
        "GERP++ RS",
    }
    assert {item["source"] for item in result.summary["provenance"]} == {
        "dbNSFP",
        "CADD",
        "SpliceAI",
    }
    assert "alphamissense_on_hold" in result.summary["warnings"]


def test_computational_annotations_fixture_no_match_returns_missing_without_bleed() -> None:
    variant = SimpleNamespace(
        gene="ABCA4",
        genomic_hg38="1-94458394-G-A",
        genomic_hgvs="NC_000001.11:g.94458394G>A",
        transcript_hgvs="NM_000350.3:c.5882G>A",
        protein_change="p.Gly1961Glu",
        dbsnp_rsid="",
    )

    result = ComputationalAnnotationsTool(_settings(use_real_apis=False)).get_evidence(variant)

    assert result.status == "missing"
    assert result.summary["predictors"] == []
    assert result.summary["spliceai"] is None
    assert result.raw is None
    assert "computational_annotations_not_found" in result.warnings


def test_clinvar_prefers_resolved_genomic_hgvs_over_transcript_source_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"esearchresult": {"idlist": []}}

    captured_terms: list[str] = []

    def fake_get(*args, params=None, **kwargs):
        captured_terms.append(params["term"])
        return Response()

    monkeypatch.setattr("app.tools.clinvar.httpx.get", fake_get)
    variant = SimpleNamespace(
        gene="USH2A",
        transcript_hgvs="NM_206933.4:c.2276G>T",
        genomic_hg38="1-216247118-C-A",
        search_input_resolution=SimpleNamespace(
            source_inputs=SimpleNamespace(clinvar="NM_206933.4:c.2276G>T")
        ),
    )

    result = ClinvarTool(_settings(use_real_apis=True)).get_evidence(variant)

    assert captured_terms == ["NC_000001.11:g.216247118C>A"]
    assert result.request_identity == {"search_text": "NC_000001.11:g.216247118C>A"}


def test_clinvar_prefers_variant_genomic_hgvs_for_indels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"esearchresult": {"idlist": []}}

    captured_terms: list[str] = []

    def fake_get(*args, params=None, **kwargs):
        captured_terms.append(params["term"])
        return Response()

    monkeypatch.setattr("app.tools.clinvar.httpx.get", fake_get)
    variant = SimpleNamespace(
        gene="BRCA1",
        transcript_hgvs="NM_007294.4:c.5266dupC",
        genomic_hg38="17-43057062-T-TG",
        genomic_hgvs="NC_000017.11:g.43057065dup",
        search_input_resolution=SimpleNamespace(
            source_inputs=SimpleNamespace(clinvar="NM_007294.4:c.5266dupC")
        ),
    )

    result = ClinvarTool(_settings(use_real_apis=True)).get_evidence(variant)

    assert captured_terms == ["NC_000017.11:g.43057065dup"]
    assert result.request_identity == {"search_text": "NC_000017.11:g.43057065dup"}


def test_load_fixture_missing_or_corrupt_degrades_to_empty_dict(tmp_path: Path) -> None:
    class Tool(FixtureBackedTool):
        source = "test"

        def __init__(self, path: Path) -> None:
            super().__init__(_settings())
            self.path = path

        def fixture_path(self) -> Path:
            return self.path

    missing = tmp_path / "missing.json"
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{", encoding="utf-8")

    assert Tool(missing).load_fixture() == {}
    assert Tool(corrupt).load_fixture() == {}
