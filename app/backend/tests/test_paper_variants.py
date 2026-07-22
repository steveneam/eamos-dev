from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

from app.api.routes import paper_variants as paper_routes
from app.cli import eamos_paper_variants as cli
from app.core.config import Settings
from app.schemas.lookup import SearchInputCandidate
from app.schemas.paper_variants import PaperVariantsResult
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
        self.calls = 0

    def invoke(self, _payload: dict) -> dict:
        self.calls += 1
        return self.payload


class BoomChain:
    def invoke(self, _payload: dict) -> dict:
        raise RuntimeError("provider down")


class SourceBackedCandidateResolver:
    records: tuple[object, ...] = ()

    @staticmethod
    def _candidate() -> SearchInputCandidate:
        return SearchInputCandidate(
            candidate_id="clinvar-live-1421454",
            display_label="RPE65 NM_000329.3:c.260A>G",
            gene="RPE65",
            cdna="c.260A>G",
            transcript="NM_000329.3",
            protein_change="p.Asp87Gly",
            genomic_hg38="1-68444869-T-C",
            genomic_hgvs="NC_000001.11:g.68444869T>C",
            match_reason="Exact source-backed cDNA match.",
            source_support=["ClinVar release 2026-07 VCV001421454"],
            source_count=1,
            confidence="high",
        )

    def exact_candidate(self, resolution):
        return self._candidate() if resolution.hgvs == "c.260A>G" else None

    def resolve_candidates(self, resolution):
        candidate = self.exact_candidate(resolution)
        return [candidate] if candidate is not None else []


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


def test_deterministic_extract_blocks_fixture_resolution_and_unknown() -> None:
    text = (
        "We identified RPE65 c.260A>G (p.Asp87Gly) in two probands. "
        "A separate ABCA4 c.9999A>T mention was a typo."
    )
    result = PaperVariantsService(_settings()).extract(text)

    by_hgvs = {v.transcript_hgvs: v for v in result.variants if v.transcript_hgvs}
    assert by_hgvs["c.260A>G"].validated is False
    assert by_hgvs["c.260A>G"].validation_status == "fixture_source_unavailable"
    assert by_hgvs["c.260A>G"].variant_id is None
    assert by_hgvs["c.260A>G"].candidates == []
    assert "fixture_candidate_blocked" in by_hgvs["c.260A>G"].resolver_provenance
    assert by_hgvs["c.9999A>T"].validated is False


def test_mock_extract_pairs_gene_cdna_and_protein() -> None:
    result = PaperVariantsService(_settings()).extract("RPE65 c.260A>G (p.Asp87Gly)")
    assert len(result.variants) == 2
    v = next(item for item in result.variants if item.level == "cdna")
    assert v.gene == "RPE65"
    assert v.transcript_hgvs == "c.260A>G"
    assert v.level == "cdna"
    protein = next(item for item in result.variants if item.level == "protein")
    assert protein.protein_hgvs == "p.Asp87Gly"
    assert result.provenance == ["eamos_paper_extract_l1_l3"]


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
    assert hit.level == "legacy"
    assert hit.gene == "FAKEGENE"  # gene-agnostic: not limited to the 8 curated symbols
    assert hit.context == "experimental_construct"  # "site-directed mutagenesis"
    assert hit.validated is False
    assert hit.validation_status == "experimental_construct_non_actionable"
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
    assert hit.validation_status == "experimental_construct_fixture_source_unavailable"
    assert hit.candidates == []
    assert by_protein["p.His527Ala"].validation_status == "experimental_construct_non_actionable"


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
    assert variant.validation_status == "experimental_construct_non_actionable"
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


# --- deterministic extraction remains canonical under gateway config -------


def _gateway_settings() -> SimpleNamespace:
    return SimpleNamespace(llm_provider="gateway", ai_gateway_api_key="vck_test")


def test_gateway_chain_cannot_replace_deterministic_mentions() -> None:
    chain = FakeChain(
        {
            "variants": [
                {"gene": "MADEUP", "transcript_hgvs": "c.1A>T"},
            ]
        }
    )
    service = PaperVariantsService(_gateway_settings(), chain=chain)

    result = service.extract("The RPE65 proband carried NM_000329.3:c.260A>G.")

    assert chain.calls == 0
    assert all(variant.gene != "MADEUP" for variant in result.variants)
    variant = result.variants[0]
    assert variant.gene == "RPE65"
    assert variant.validated is False
    assert variant.validation_status == "fixture_source_unavailable"
    assert result.provenance == ["eamos_paper_extract_l1_l3"]


def test_source_backed_candidate_resolves_and_enables_action() -> None:
    service = PaperVariantsService(
        _settings(),
        candidate_resolver=SourceBackedCandidateResolver(),
    )

    result = service.extract("The RPE65 proband carried NM_000329.3:c.260A>G.")

    variant = result.variants[0]
    assert variant.validated is True
    assert variant.validation_status == "resolved"
    assert variant.resolved_candidate_id == "clinvar-live-1421454"
    assert variant.source_support == ["ClinVar release 2026-07 VCV001421454"]


def test_deterministic_protein_fixture_cannot_auto_resolve() -> None:
    service = PaperVariantsService(_gateway_settings())

    result = service.extract("The CFTR patient carried p.Leu441del.")

    variant = result.variants[0]
    assert variant.validated is False
    assert variant.validation_status == "fixture_source_unavailable"
    assert variant.variant_id is None
    assert variant.candidates == []
    assert "search_candidate_resolver" in variant.resolver_provenance


def test_deterministic_experimental_protein_match_stays_non_actionable() -> None:
    service = PaperVariantsService(_gateway_settings())

    result = service.extract("A CFTR p.Leu441del experimental construct was engineered.")

    variant = result.variants[0]
    assert variant.validated is False
    assert variant.validation_status == "experimental_construct_fixture_source_unavailable"
    assert variant.variant_id is None
    assert variant.candidates == []


def test_deterministic_protein_candidate_suggestion_stays_fail_closed() -> None:
    service = PaperVariantsService(_gateway_settings())

    result = service.extract("The CFTR patient carried p.Leu441fs.")

    variant = result.variants[0]
    assert variant.validated is False
    assert variant.validation_status == "fixture_source_unavailable"
    assert variant.variant_id is None
    assert variant.candidates == []


def test_no_validate_flag_skips_the_gate() -> None:
    service = PaperVariantsService(_gateway_settings())

    result = service.extract("RPE65 c.260A>G", validate=False)

    assert result.variants[0].validated is False
    assert result.variants[0].validation_status == "not_validated"


def test_provider_failure_is_irrelevant_to_deterministic_path() -> None:
    service = PaperVariantsService(_gateway_settings(), chain=BoomChain())
    result = service.extract("RPE65 c.260A>G")
    assert result.variants[0].validated is False
    assert result.variants[0].validation_status == "fixture_source_unavailable"
    assert result.warnings == []


def test_gateway_unavailable_does_not_disable_local_extraction() -> None:
    service = PaperVariantsService(SimpleNamespace(llm_provider="gateway", ai_gateway_api_key=None))
    result = service.extract("RPE65 c.260A>G")
    assert result.variants[0].validated is False
    assert result.variants[0].validation_status == "fixture_source_unavailable"
    assert result.provenance == ["eamos_paper_extract_l1_l3"]


# --- CLI ------------------------------------------------------------------


def test_cli_require_validated_fails_closed_for_fixture_resolution(capsys) -> None:
    code = cli.main(["--text", "RPE65 c.260A>G was identified", "--require-validated"])
    assert code == 2
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "paper_variants_extract"
    assert report["llm_provider"] == "eamos_deterministic"
    assert report["source_metadata"] is None
    assert report["validated_count"] == 0
    assert report["variants"][0]["validation_status"] == "fixture_source_unavailable"
    assert report["document_extraction"]["resolutions"][0]["status"] == "unresolved"


def test_cli_pdf_ingest(capsys) -> None:
    from app.core.config import Settings

    pdf = (
        Settings(jwt_secret="x").fixtures_root / "reports" / "backend_report_recommendations_v2.pdf"
    )
    code = cli.main(["--pdf", str(pdf)])
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["pdf"]["engine"] == "pdfium"
    assert report["pdf"]["page_count"] >= 1
    assert report["source_metadata"] is None or report["source_metadata"]["title"]
    assert str(pdf) not in json.dumps(report)


def test_cli_rejects_oversized_and_non_utf8_text_files_without_echoing_paths(
    capsys,
    tmp_path: Path,
) -> None:
    private_path = tmp_path / "PRIVATE_INPUT_NAME.txt"
    private_path.write_bytes(b"x" * 1_000_001)

    assert cli.main(["--text-file", str(private_path)]) == 3
    oversized = capsys.readouterr().out
    assert json.loads(oversized)["error"] == "text_size_limit"
    assert "PRIVATE_INPUT_NAME" not in oversized

    private_path.write_bytes(b"\xff\xfe")
    assert cli.main(["--text-file", str(private_path)]) == 3
    invalid = capsys.readouterr().out
    assert json.loads(invalid)["error"] == "text_encoding_invalid"
    assert "PRIVATE_INPUT_NAME" not in invalid


def test_cli_fails_honestly_for_garbled_text_and_blank_pdf(capsys, tmp_path: Path) -> None:
    assert cli.main(["--text", "marker" + ("\ufffd" * 200)]) == 3
    garbled = json.loads(capsys.readouterr().out)
    assert garbled["error"] == "paper_text_ambiguous"

    from pypdf import PdfWriter

    path = tmp_path / "PRIVATE_BLANK.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with path.open("wb") as handle:
        writer.write(handle)

    assert cli.main(["--pdf", str(path)]) == 3
    blank = capsys.readouterr().out
    assert json.loads(blank)["error"] == "ocr_required"
    assert "PRIVATE_BLANK" not in blank


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
    assert body["llm_provider"] == "eamos_deterministic"
    assert body["pdf"] is None
    assert body["source_metadata"] is None
    assert body["guardrails"] == {
        "patient_data": "not_used",
        "raw_paper_text_in_output": "blocked",
        "secrets_in_output": "blocked",
    }
    assert body["candidate_count"] == len(body["variants"])
    assert body["validated_count"] == 0
    assert body["variants"][0]["validated"] is False
    assert body["variants"][0]["validation_status"] == "fixture_source_unavailable"
    assert body["provenance"] == ["eamos_paper_extract_l1_l3"]
    assert body["document_extraction"]["schema_version"] == "paper_document_extraction.v2"
    assert body["execution_disclosure"]["algorithm_id"] == "eamos_paper_extract"
    resolution = body["document_extraction"]["resolutions"][0]
    assert resolution["status"] == "unresolved"
    assert resolution["execution_disclosure"]["execution"] == "unavailable"
    assert text not in response.text


def test_api_extract_pdf_upload_returns_pdf_meta(auth_client, pdf_bytes: bytes) -> None:
    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        files={"file": ("paper.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pdf"]["engine"] == "pdfium"
    assert body["pdf"]["page_count"] >= 1
    assert body["source_metadata"] == {
        "title": "HSIL demo PDF fixture",
        "authors": [],
        "year": None,
        "journal": None,
        "doi": None,
        "pmid": None,
    }
    assert body["guardrails"]["raw_paper_text_in_output"] == "blocked"
    assert body["candidate_count"] >= 1


def test_api_pdf_ignores_hostile_filename_and_cleans_request_tempfile(
    auth_client,
    pdf_bytes: bytes,
) -> None:
    upload_dir = Path(auth_client.app.state.settings.upload_dir)
    before = set(upload_dir.glob("*.pdf"))

    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        files={"file": ("../../PRIVATE_PAPER.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_extraction"]["bundle"]["documents"][0]["filename"] == "main-pdf.pdf"
    assert "PRIVATE_PAPER" not in response.text
    assert set(upload_dir.glob("*.pdf")) == before


def test_api_blank_pdf_returns_typed_ocr_requirement(auth_client, tmp_path: Path) -> None:
    from pypdf import PdfWriter

    path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with path.open("wb") as handle:
        writer.write(handle)

    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        files={"file": ("blank.pdf", path.read_bytes(), "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "ocr_required",
        "requirement": "local_ocr_or_selectable_text",
    }


def test_api_pdf_page_parse_failure_rejects_partial_text(auth_client, monkeypatch) -> None:
    def partial_pdf_result(*_args, **_kwargs):
        return {
            "text": "Selectable text from the first page.",
            "pages": [
                {"page_number": 1, "text": "Selectable text.", "quality": "good"},
                {"page_number": 2, "text": "", "quality": "empty"},
            ],
            "page_count": 2,
            "engine": "pypdf",
            "engine_version": "test",
            "metadata": {},
            "warnings": ["pdf_page_parse_failed:2:PdfReadError"],
        }

    monkeypatch.setattr(paper_routes, "extract_pdf_text", partial_pdf_result)

    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        files={"file": ("paper.pdf", b"%PDF-partial", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "paper_pdf_unavailable",
        "requirement": "pdf_page_parse_failed:2:PdfReadError",
    }


def test_api_rejects_garbled_text_without_false_zero_success(auth_client) -> None:
    marker = "PRIVATE_GARBLED_MARKER"
    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        json={"text": marker + ("\ufffd" * 200)},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "paper_text_ambiguous"
    assert marker not in response.text


def test_api_json_body_limit_fails_before_parsing_and_does_not_echo_input(
    auth_client,
    monkeypatch,
) -> None:
    marker = "PRIVATE_OVERSIZED_JSON_MARKER"
    monkeypatch.setattr(paper_routes, "_MAX_JSON_BODY_BYTES", 128)

    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        content=json.dumps({"text": marker + ("x" * 256)}),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "JSON body exceeds configured size limit."
    assert marker not in response.text


def test_api_streaming_upload_limit_fails_before_parser(auth_client) -> None:
    auth_client.app.state.settings.max_upload_mb = 0.00001
    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        files={"file": ("paper.pdf", b"%PDF-" + (b"x" * 256), "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Uploaded file exceeds configured size limit."


def test_api_rejects_multiple_file_parts_with_sanitized_error(auth_client) -> None:
    marker = "PRIVATE_SECOND_FILENAME"

    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        files=[
            ("file", ("first.pdf", b"%PDF-one", "application/pdf")),
            ("pdf", (f"{marker}.pdf", b"%PDF-two", "application/pdf")),
        ],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Malformed multipart upload."
    assert marker not in response.text


def test_api_extract_times_out_slow_extraction(auth_client, monkeypatch) -> None:
    auth_client.app.state.settings.paper_variants_extract_timeout_seconds = 0.01

    def slow_extract(self, paper_text: str, *, validate: bool = True):  # noqa: ARG001
        time.sleep(0.05)
        return PaperVariantsResult()

    monkeypatch.setattr(PaperVariantsService, "extract", slow_extract)

    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        json={"text": "RPE65 c.260A>G was identified in a patient."},
    )

    assert response.status_code == 504
    assert response.json()["detail"] == "Paper variant extraction timed out."


def test_api_pdf_parser_timeout_is_bounded_and_cleans_tempfile(
    auth_client,
    monkeypatch,
) -> None:
    auth_client.app.state.settings.paper_variants_pdf_timeout_seconds = 0.01
    upload_dir = Path(auth_client.app.state.settings.upload_dir)
    before = set(upload_dir.glob("*.pdf"))

    def slow_pdf_parser(*_args, **_kwargs):
        time.sleep(0.05)
        return {}

    monkeypatch.setattr(paper_routes, "extract_pdf_text", slow_pdf_parser)

    response = auth_client.post(
        "/api/v1/paper-variants/extract",
        files={"file": ("paper.pdf", b"%PDF-slow", "application/pdf")},
    )

    assert response.status_code == 504
    assert response.json()["detail"] == "PDF text extraction timed out."
    assert set(upload_dir.glob("*.pdf")) == before
