from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.core.config import Settings
from app.schemas.lookup import SearchInputCandidate
from app.services.paper_extract.document import text_document
from app.services.paper_extract.grammar import extract_page_mentions
from app.services.paper_extract.pipeline import MAX_BUNDLE_MENTIONS, build_extraction_draft
from app.services.paper_variants import PaperVariantsService
from app.services.search_candidate_resolver import CandidateRecord, SearchCandidateResolver


def _settings() -> Settings:
    return Settings(
        jwt_secret="paper-pipeline-test-secret-that-is-long-enough",
        llm_provider="mock",
        clingen_local_enabled=False,
    )


class SourceBackedCandidateResolver:
    records: tuple[object, ...] = ()

    def exact_candidate(self, resolution):
        if resolution.hgvs != "c.260A>G":
            return None
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

    def resolve_candidates(self, resolution):
        candidate = self.exact_candidate(resolution)
        return [candidate] if candidate is not None else []


class SourcelessCandidateResolver(SourceBackedCandidateResolver):
    def exact_candidate(self, resolution):
        candidate = super().exact_candidate(resolution)
        if candidate is None:
            return None
        return candidate.model_copy(update={"source_support": [], "source_count": 0})


def test_deterministic_pipeline_emits_v2_bundle_spans_and_resolution_separately() -> None:
    text = (
        "Results\nThe RPE65 proband carried NM_000329.3:c.260A>G.\n"
        "References\nA review discussed ABCA4 c.5882G>A."
    )
    document = text_document(text, document_id="main-text")

    result = PaperVariantsService(_settings()).extract_document(document)
    extraction = result.document_extraction

    assert extraction.bundle.schema_version == "paper_document_bundle.v2"
    assert extraction.bundle.input_digest
    assert extraction.deterministic_digest
    assert extraction.execution_disclosure.execution == "eamos_local"
    assert extraction.execution_disclosure.algorithm_id == "eamos_paper_extract"
    assert extraction.execution_disclosure.validation_matrix_id == "paper-synthetic-v2"
    assert len(extraction.mentions) == len(extraction.resolutions) == len(result.result.variants)
    by_surface = {mention.span.exact_text: mention for mention in extraction.mentions}
    by_resolution = {resolution.mention_id: resolution for resolution in extraction.resolutions}
    clinical = by_surface["NM_000329.3:c.260A>G"]
    reference = by_surface["c.5882G>A"]
    assert by_resolution[clinical.mention_id].status == "unresolved"
    assert by_resolution[clinical.mention_id].execution_disclosure.execution == "unavailable"
    assert by_resolution[reference.mention_id].status == "excluded"
    assert by_resolution[reference.mention_id].canonical_variant is None
    assert "bibliography" in " ".join(by_resolution[reference.mention_id].warnings).lower()

    payload = extraction.model_dump_json()
    assert text not in payload
    assert "upload_ref" not in payload
    assert "/" not in extraction.bundle.documents[0].filename


def test_source_backed_resolution_is_the_only_action_enabling_path() -> None:
    document = text_document(
        "Results\nThe RPE65 proband carried NM_000329.3:c.260A>G.",
        document_id="main-text",
    )

    result = PaperVariantsService(
        _settings(),
        candidate_resolver=SourceBackedCandidateResolver(),
    ).extract_document(document)
    resolution = result.document_extraction.resolutions[0]

    assert resolution.status == "resolved"
    assert resolution.canonical_variant is not None
    assert resolution.execution_disclosure.source_status == "source_backed"
    assert resolution.execution_disclosure.source_record_ids


def test_injected_source_records_are_not_misclassified_as_bundled_fixtures() -> None:
    resolver = SearchCandidateResolver(
        records=(
            CandidateRecord(
                candidate_id="mounted-source-gene7-777",
                display_label="GENE7 NM_123456.1:c.777A>G",
                gene="GENE7",
                cdna="c.777A>G",
                transcript="NM_123456.1",
                genomic_hg38="1-777-A-G",
                genomic_hgvs="NC_000001.11:g.777A>G",
                source_support=("Mounted allele release 2026-07 record 777",),
            ),
        ),
        settings=_settings(),
    )
    document = text_document(
        "Results\nThe GENE7 proband carried NM_123456.1:c.777A>G.",
        document_id="main-text",
    )

    result = PaperVariantsService(
        _settings(),
        candidate_resolver=resolver,
    ).extract_document(document)

    assert result.result.variants[0].validation_status == "resolved"
    assert result.document_extraction.resolutions[0].status == "resolved"


def test_candidate_without_source_support_cannot_enable_action() -> None:
    document = text_document(
        "Results\nThe RPE65 proband carried NM_000329.3:c.260A>G.",
        document_id="main-text",
    )

    result = PaperVariantsService(
        _settings(),
        candidate_resolver=SourcelessCandidateResolver(),
    ).extract_document(document)
    variant = result.result.variants[0]
    resolution = result.document_extraction.resolutions[0]

    assert variant.validated is False
    assert variant.validation_status == "source_verification_required"
    assert variant.variant_id is None
    assert resolution.status == "unresolved"
    assert resolution.canonical_variant is None
    assert resolution.execution_disclosure.execution == "unavailable"


def test_submitted_genomic_identifier_requires_independent_source_verification() -> None:
    document = text_document(
        "Results\nThe FAKEGENE proband carried NC_000001.11:g.101A>G.",
        document_id="main-text",
    )

    result = PaperVariantsService(_settings()).extract_document(document)
    variant = result.result.variants[0]
    resolution = result.document_extraction.resolutions[0]

    assert variant.validation_status == "source_verification_required"
    assert variant.validated is False
    assert "submitted_genomic_variant_id" in variant.resolver_provenance
    assert resolution.status == "unresolved"
    assert resolution.execution_disclosure.requirements == [
        "source_backed_allele_resolver_or_mounted_artifact"
    ]


def test_deterministic_output_is_stable_and_gateway_chain_cannot_replace_it() -> None:
    class FailIfCalled:
        def invoke(self, _payload):
            raise AssertionError("optional L4 provider must not replace deterministic extraction")

    text = "Results\nThe RPE65 proband carried c.260A>G."
    service = PaperVariantsService(_settings(), chain=FailIfCalled())

    first = service.extract_document(text_document(text))
    second = service.extract_document(text_document(text))

    assert (
        first.document_extraction.deterministic_digest
        == second.document_extraction.deterministic_digest
    )
    assert first.result.provenance == ["eamos_paper_extract_l1_l3"]


def test_default_paper_resolver_stays_offline_even_when_generic_live_apis_are_enabled(
    monkeypatch,
) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Paper resolution must not call a network provider")

    monkeypatch.setattr("app.services.search_input_resolver.httpx.get", fail_if_called)
    settings = _settings().model_copy(update={"use_real_apis": True})
    service = PaperVariantsService(settings)

    resolver = service._search_input_resolver()
    result = service.extract("The FAKEGENE proband carried c.123A>G and rs121918127.")

    assert resolver.resolve_coordinates is False
    assert resolver.settings is None
    assert result.variants


def test_main_and_csv_supplement_share_one_bound_evidence_graph() -> None:
    main = text_document(
        "Results\nThe RPE65 proband carried c.260A>G.",
        document_id="main-text",
    )
    supplement = text_document(
        "gene,variant\nABCA4,c.5882G>A\n",
        document_id="supp-table",
        role="supplement",
        kind="csv",
    )

    result = PaperVariantsService(_settings()).extract_document(
        main,
        supplements=(supplement,),
    )

    documents = result.document_extraction.bundle.documents
    assert [(item.document_id, item.role, item.kind) for item in documents] == [
        ("main-text", "main", "text"),
        ("supp-table", "supplement", "csv"),
    ]
    assert {mention.span.document_id for mention in result.document_extraction.mentions} == {
        "main-text",
        "supp-table",
    }


def test_synthetic_corpus_manifest_hashes_and_expectations_are_self_owned() -> None:
    root = Path(__file__).parents[1] / "app" / "fixtures" / "paper_variants"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["corpus_id"] == "eamos-paper-synthetic-v2"
    assert manifest["license"] == "Eamos-owned synthetic test data"
    for item in manifest["documents"]:
        payload = (root / item["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
        assert item["expected_mentions"]
        assert "expected_exclusions" in item
        mentions = extract_page_mentions(
            document_id=Path(item["path"]).stem,
            page_number=1,
            text=payload.decode("utf-8"),
        )
        by_surface: dict[str, list] = {}
        for mention in mentions:
            by_surface.setdefault(mention.span.exact_text, []).append(mention)
        assert set(item["expected_mentions"]) <= set(by_surface)
        for surface in item["expected_exclusions"]:
            assert all(
                mention.biological_context == "bibliography_only" for mention in by_surface[surface]
            )


def test_mention_flood_is_bounded_before_resolution_or_schema_construction() -> None:
    text = "Results\n" + " ".join(
        f"GENE1 c.{index}A>G." for index in range(1, MAX_BUNDLE_MENTIONS + 50)
    )

    draft = build_extraction_draft((text_document(text),))

    assert len(draft.records) == MAX_BUNDLE_MENTIONS
    assert draft.warnings == (f"paper_mention_limit_exceeded:{MAX_BUNDLE_MENTIONS}",)
