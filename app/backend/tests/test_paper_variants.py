from __future__ import annotations

import json
from types import SimpleNamespace

from app.cli import eamos_paper_variants as cli
from app.core.config import Settings
from app.services.paper_variants import PaperVariantsService
from app.tools.base import ToolResult


def _settings(**overrides) -> Settings:
    base = {"jwt_secret": "paper-variants-test", "llm_provider": "mock"}
    base.update(overrides)
    return Settings(**base)


class FakeChain:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def invoke(self, _payload: dict) -> dict:
        return self.payload


class BoomChain:
    def invoke(self, _payload: dict) -> dict:
        raise RuntimeError("provider down")


class FakeValidator:
    """Maps gene -> ToolResult, defaulting to a 'missing' (unresolved) result."""

    def __init__(self, mapping: dict[str, ToolResult]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def get_evidence(self, variant) -> ToolResult:
        self.calls.append(variant.gene)
        return self.mapping.get(
            variant.gene,
            ToolResult(
                source="variant_validator", status="missing", request_identity={}, summary={}
            ),
        )


def _resolved(variant_id: str) -> ToolResult:
    return ToolResult(
        source="variant_validator",
        status="fixture",
        request_identity={},
        summary={
            "variant_id": variant_id,
            "hgvs_genomic_description": "NC_000001.11:g.68444869T>C",
        },
    )


# --- mock extraction + real VariantValidator fixture gate ------------------


def test_mock_extract_validates_fixture_variant_and_rejects_unknown() -> None:
    text = (
        "We identified RPE65 c.260A>G (p.Asp87Gly) in two probands. "
        "A separate ABCA4 c.9999A>T mention was a typo."
    )
    result = PaperVariantsService(_settings()).extract(text)

    by_gene = {v.gene: v for v in result.variants}
    assert by_gene["RPE65"].validated is True
    assert by_gene["RPE65"].validation_status == "fixture"
    assert by_gene["RPE65"].variant_id == "1-68444869-T-C"  # fixture resolves to GRCh38
    assert (
        by_gene["ABCA4"].validated is False
    )  # no VariantValidator match → dropped from "validated"


def test_mock_extract_pairs_gene_cdna_and_protein() -> None:
    result = PaperVariantsService(_settings()).extract("RPE65 c.260A>G (p.Asp87Gly)")
    assert len(result.variants) == 1
    v = result.variants[0]
    assert v.gene == "RPE65"
    assert v.transcript_hgvs == "c.260A>G"
    assert v.protein_change == "p.Asp87Gly"
    assert v.level == "cdna"
    assert "mock_paper_variants_extractor" in result.provenance


def test_mock_extracts_protein_substitutions_gene_agnostic() -> None:
    # Functional-paper style: single-letter residue subs on an arbitrary (non-curated)
    # gene. Normalization comes from the reused lexicon; gene detection is agnostic.
    text = (
        "Site-directed mutagenesis of FAKEGENE produced H241A and C231S mutants "
        "that abolished enzymatic activity."
    )
    result = PaperVariantsService(_settings()).extract(text)

    by_p = {v.protein_hgvs: v for v in result.variants}
    assert "p.His241Ala" in by_p  # normalized via SearchInputReference, not a hardcoded map
    assert "p.Cys231Ser" in by_p
    hit = by_p["p.His241Ala"]
    assert hit.level == "protein"
    assert hit.gene == "FAKEGENE"  # gene-agnostic: not limited to the 8 curated symbols
    assert hit.context == "experimental_construct"  # "site-directed mutagenesis"
    assert hit.validated is False
    assert hit.validation_status == "protein_only_unresolved"  # Phase 3 resolves these


def test_mock_extracts_three_letter_protein_via_lexicon() -> None:
    result = PaperVariantsService(_settings()).extract("The His313Ala mutant lost function.")
    assert any(v.protein_hgvs == "p.His313Ala" for v in result.variants)


# --- gateway path (structured) + gate -------------------------------------


def _gateway_settings() -> SimpleNamespace:
    return SimpleNamespace(llm_provider="gateway", ai_gateway_api_key="vck_test")


def test_gateway_extraction_gate_keeps_resolved_drops_unresolved() -> None:
    chain = FakeChain(
        {
            "variants": [
                {
                    "gene": "RPE65",
                    "transcript_hgvs": "NM_000329.3:c.260A>G",
                    "protein_change": "p.Asp87Gly",
                },
                {"gene": "MADEUP", "transcript_hgvs": "c.1A>T"},
            ]
        }
    )
    validator = FakeValidator({"RPE65": _resolved("1-68444869-T-C")})
    service = PaperVariantsService(_gateway_settings(), chain=chain, validator=validator)

    result = service.extract("paper body")

    by_gene = {v.gene: v for v in result.variants}
    assert by_gene["RPE65"].validated is True
    assert by_gene["RPE65"].variant_id == "1-68444869-T-C"
    assert by_gene["MADEUP"].validated is False
    assert by_gene["MADEUP"].validation_status == "missing"
    assert validator.calls == ["RPE65", "MADEUP"]


def test_gate_skips_candidate_missing_identity() -> None:
    chain = FakeChain({"variants": [{"gene": "RPE65"}]})  # no transcript_hgvs
    validator = FakeValidator({"RPE65": _resolved("x")})
    service = PaperVariantsService(_gateway_settings(), chain=chain, validator=validator)

    result = service.extract("paper")

    assert result.variants[0].validated is False
    assert result.variants[0].validation_status == "insufficient_identity"
    assert validator.calls == []  # never probed without gene + hgvs


def test_no_validate_flag_skips_the_gate() -> None:
    chain = FakeChain({"variants": [{"gene": "RPE65", "transcript_hgvs": "c.260A>G"}]})
    validator = FakeValidator({"RPE65": _resolved("1-68444869-T-C")})
    service = PaperVariantsService(_gateway_settings(), chain=chain, validator=validator)

    result = service.extract("paper", validate=False)

    assert result.variants[0].validated is False
    assert result.variants[0].validation_status == "not_validated"
    assert validator.calls == []


def test_extraction_failure_is_graceful() -> None:
    service = PaperVariantsService(_gateway_settings(), chain=BoomChain())
    result = service.extract("paper")
    assert result.variants == []
    assert any(w.startswith("paper_variants_failed:") for w in result.warnings)


def test_gateway_unavailable_without_chain_is_graceful() -> None:
    # gateway provider but no key/chain → build_gateway_* returns None
    service = PaperVariantsService(SimpleNamespace(llm_provider="gateway", ai_gateway_api_key=None))
    result = service.extract("RPE65 c.260A>G")
    assert result.variants == []
    assert "paper_variants_unavailable" in result.warnings


# --- CLI ------------------------------------------------------------------


def test_cli_mock_reports_validated_variant(capsys) -> None:
    code = cli.main(["--text", "RPE65 c.260A>G was identified", "--require-validated"])
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "paper_variants_extract"
    assert report["llm_provider"] == "mock"
    assert report["validated_count"] == 1
    assert report["variants"][0]["variant_id"] == "1-68444869-T-C"


def test_cli_pdf_ingest(capsys) -> None:
    from app.core.config import Settings

    pdf = (
        Settings(jwt_secret="x").fixtures_root / "reports" / "backend_report_recommendations_v2.pdf"
    )
    code = cli.main(["--pdf", str(pdf)])
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["pdf"]["engine"] == "pypdf"
    assert report["pdf"]["page_count"] >= 1
