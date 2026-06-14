from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.cli import eamos_paper_variants as cli
from app.core.config import Settings
from app.services.clingen_local import materialize_clingen_local_store
from app.services.paper_variants import PaperVariantsService
from app.services.search_candidate_resolver import SearchCandidateResolver
from app.tools.base import ToolResult


def _settings(**overrides) -> Settings:
    base = {
        "jwt_secret": "paper-variants-test",
        "llm_provider": "mock",
        "clingen_local_enabled": False,
    }
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
    """Legacy compatibility seam. Phase 3 no longer calls this directly."""

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
    assert by_gene["RPE65"].validation_status == "resolved"
    assert by_gene["RPE65"].variant_id == "1-68444869-T-C"  # fixture resolves to GRCh38
    assert by_gene["RPE65"].resolved_candidate_id == "clinvar:VCV001421454"
    assert "ClinVar VCV001421454" in by_gene["RPE65"].source_support
    assert "eamos_search_input_resolver" in by_gene["RPE65"].resolver_provenance
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
    assert hit.validation_status == "experimental_construct"
    assert hit.candidates == []


def test_mock_extracts_three_letter_protein_via_lexicon() -> None:
    result = PaperVariantsService(_settings()).extract("The His313Ala mutant lost function.")
    assert any(v.protein_hgvs == "p.His313Ala" for v in result.variants)


def test_mock_protein_series_ignores_prior_variant_tokens_as_gene_symbols() -> None:
    text = "RPE65 mutants H68Y, H182A, H313A, and H527A abolished activity."

    result = PaperVariantsService(_settings()).extract(text)

    by_protein = {v.protein_hgvs: v for v in result.variants}
    assert by_protein["p.His68Tyr"].gene == "RPE65"
    assert by_protein["p.His182Ala"].gene == "RPE65"
    assert by_protein["p.His313Ala"].gene == "RPE65"
    assert by_protein["p.His527Ala"].gene == "RPE65"
    assert all(v.validated is False for v in result.variants)


def test_mock_protein_only_rows_offer_same_residue_not_distant_candidates() -> None:
    text = "RPE65 mutants H313A and H527A abolished activity."

    result = PaperVariantsService(_settings()).extract(text)

    by_protein = {v.protein_hgvs: v for v in result.variants}
    hit = by_protein["p.His313Ala"]
    assert hit.validated is False
    assert hit.validation_status == "candidates"
    assert {candidate.cdna for candidate in hit.candidates} == {"c.938A>G", "c.938A>C"}
    assert {candidate.confidence for candidate in hit.candidates} == {"medium"}
    assert all(candidate.protein_change.startswith("p.His313") for candidate in hit.candidates)
    assert "c.260A>G" not in {candidate.cdna for candidate in hit.candidates}
    assert by_protein["p.His527Ala"].validation_status == "experimental_construct"


def test_mock_protein_only_candidates_use_local_clingen_gene_agnostically(
    tmp_path: Path,
) -> None:
    settings = _settings(
        clingen_local_enabled=True,
        clingen_local_sqlite_path=tmp_path / "clingen-local.sqlite",
        clingen_local_manifest_path=tmp_path / "clingen-local.manifest.json",
    )
    source_path = tmp_path / "erepo.jsonl"
    source_path.write_text(
        json.dumps(
            {
                "_id": "AlleleRecords/fakegene-his241",
                "uuid": "fakegene-his241",
                "gene": "FAKEGENE",
                "classification": "Likely Pathogenic",
                "cvId": "1234567",
                "preferredVarTitle": "NM_123456.1(FAKEGENE):c.721A>G (p.His241Arg)",
                "hgvs": [
                    "NM_123456.1:c.721A>G",
                    "NC_000001.11:g.100A>G",
                    "NM_123456.1(FAKEGENE):c.721A>G (p.His241Arg)",
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    result = materialize_clingen_local_store(
        settings,
        erepo_jsonl_files=[source_path],
        source_version="pytest-gene-agnostic",
        force=True,
    )
    assert result.ready is True

    paper_result = PaperVariantsService(settings).extract(
        "Site-directed mutagenesis of FAKEGENE produced H241A."
    )

    variant = next(item for item in paper_result.variants if item.protein_hgvs == "p.His241Ala")
    assert variant.gene == "FAKEGENE"
    assert variant.validated is False
    assert variant.validation_status == "candidates"
    assert len(variant.candidates) == 1
    assert variant.candidates[0].gene == "FAKEGENE"
    assert variant.candidates[0].cdna == "c.721A>G"
    assert variant.candidates[0].protein_change == "p.His241Arg"
    assert variant.candidates[0].confidence == "medium"

    selected = SearchCandidateResolver(settings=settings).get_candidate(
        variant.candidates[0].candidate_id
    )
    assert selected is not None
    assert selected.gene == "FAKEGENE"
    assert selected.cdna == "c.721A>G"


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
    assert by_gene["RPE65"].resolved_candidate_id == "clinvar:VCV001421454"
    assert by_gene["MADEUP"].validated is False
    assert by_gene["MADEUP"].validation_status == "missing"
    assert validator.calls == []  # Phase 3 reuses EamosSearchInputResolver instead


def test_gateway_protein_candidate_auto_resolves_source_backed_match() -> None:
    chain = FakeChain(
        {
            "variants": [
                {
                    "gene": "CFTR",
                    "protein_hgvs": "p.Leu441del",
                    "level": "protein",
                    "context": "clinical_allele",
                }
            ]
        }
    )
    service = PaperVariantsService(_gateway_settings(), chain=chain)

    result = service.extract("paper body")

    variant = result.variants[0]
    assert variant.validated is True
    assert variant.validation_status == "resolved"
    assert variant.variant_id == "source:CFTR_c.1321_1323del"
    assert variant.resolved_candidate_id == "source:CFTR_c.1321_1323del"
    assert variant.candidates[0].cdna == "c.1321_1323del"
    assert variant.candidates[0].protein_change == "p.Leu441del"
    assert variant.source_support == ["User-supplied source correction"]
    assert "search_candidate_resolver" in variant.resolver_provenance


def test_gateway_experimental_protein_match_stays_candidate_not_validated() -> None:
    chain = FakeChain(
        {
            "variants": [
                {
                    "gene": "CFTR",
                    "protein_hgvs": "p.Leu441del",
                    "level": "protein",
                    "context": "experimental_construct",
                }
            ]
        }
    )
    service = PaperVariantsService(_gateway_settings(), chain=chain)

    result = service.extract("paper body")

    variant = result.variants[0]
    assert variant.validated is False
    assert variant.validation_status == "candidates"
    assert variant.variant_id is None
    assert variant.candidates[0].candidate_id == "source:CFTR_c.1321_1323del"
    assert variant.candidates[0].confidence == "high"


def test_gateway_protein_candidate_suggestion_stays_fail_closed() -> None:
    chain = FakeChain(
        {
            "variants": [
                {
                    "gene": "CFTR",
                    "protein_hgvs": "p.Leu441fs",
                    "level": "protein",
                    "context": "clinical_allele",
                }
            ]
        }
    )
    service = PaperVariantsService(_gateway_settings(), chain=chain)

    result = service.extract("paper body")

    variant = result.variants[0]
    assert variant.validated is False
    assert variant.validation_status == "candidates"
    assert variant.variant_id is None
    assert variant.candidates[0].candidate_id == "source:CFTR_c.1321_1323del"
    assert variant.candidates[0].confidence == "medium"
    assert "search_candidate_resolver" in variant.resolver_provenance


def test_gate_skips_candidate_missing_identity() -> None:
    chain = FakeChain({"variants": [{"gene": "RPE65"}]})  # no transcript_hgvs
    validator = FakeValidator({"RPE65": _resolved("x")})
    service = PaperVariantsService(_gateway_settings(), chain=chain, validator=validator)

    result = service.extract("paper")

    assert result.variants[0].validated is False
    assert result.variants[0].validation_status == "missing"
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
    assert report["source_metadata"] is None
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
    assert report["source_metadata"] is None


# --- API front door -------------------------------------------------------


def test_api_extract_requires_authentication(client) -> None:
    response = client.post(
        "/api/v1/paper-variants/extract",
        json={"text": "RPE65 c.260A>G was identified in a patient."},
    )

    assert response.status_code == 401


def test_api_extract_json_returns_sanitized_cli_style_result(auth_client) -> None:
    text = "RPE65 c.260A>G was identified in a patient."
    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        json={"text": text},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "paper_variants_extract"
    assert body["llm_provider"] == "mock"
    assert body["pdf"] is None
    assert body["source_metadata"] is None
    assert body["guardrails"] == {
        "patient_data": "not_used",
        "raw_paper_text_in_output": "blocked",
        "secrets_in_output": "blocked",
    }
    assert body["candidate_count"] == len(body["variants"])
    assert body["validated_count"] == 1
    assert body["variants"][0]["validated"] is True
    assert body["variants"][0]["resolved_candidate_id"] == "clinvar:VCV001421454"
    assert "mock_paper_variants_extractor" in body["provenance"]
    assert text not in response.text


def test_api_extract_pdf_upload_returns_pdf_meta(auth_client, pdf_bytes: bytes) -> None:
    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        files={"file": ("paper.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pdf"]["engine"] == "pypdf"
    assert body["pdf"]["page_count"] >= 1
    assert body["source_metadata"] is None
    assert body["guardrails"]["raw_paper_text_in_output"] == "blocked"
    assert body["candidate_count"] >= 1
