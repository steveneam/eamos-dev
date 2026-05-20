from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import status

from app.core.config import Settings
from app.schemas.gene_viewer import (
    GeneViewerRequest,
    ProteinDomain,
    ProteinFeatures,
    ViewerProvenanceSource,
    ViewerWindowRequest,
)
from app.services.sequence_context import normalize_sequence_query, unsupported_input_warning
from app.services.gene_viewer import (
    GENE_VIEWER_PROVIDER_FAILED_PREFIX,
    GENE_VIEWER_REFERENCE_MISMATCH,
    GeneViewerError,
    GeneViewerFixtureProvider,
    GeneViewerService,
    HttpGeneViewerSourceClient,
    SourceBackedGeneViewerProvider,
    SourceTranscriptExon,
    SourceTranscriptIntron,
    SourceTranscriptModel,
    TranscriptExon,
    TranscriptIntron,
    TranscriptModel,
    TranscriptWindowBuilder,
    VariantProjection,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "workbench"


def _request(
    *,
    allele_mode: str = "reference",
    cds_start: int = 1,
    cds_end: int = 18,
) -> GeneViewerRequest:
    return GeneViewerRequest(
        gene="TEST",
        cdna="c.11T>G",
        transcript="NM_TEST.1",
        allele_mode=allele_mode,
        window=ViewerWindowRequest(
            kind="cds_range",
            cds_start=cds_start,
            cds_end=cds_end,
            intron_flank_bp=2,
        ),
    )


class FailingGeneViewerService:
    def __init__(self, error: GeneViewerError) -> None:
        self.error = error

    def build_viewer(self, _payload):
        raise self.error


class MockOfficialGeneViewerSourceClient:
    def __init__(self) -> None:
        fixture_response = GeneViewerFixtureProvider().viewer(
            GeneViewerRequest(
                gene="RPE65",
                cdna="c.260A>G",
                transcript="NM_000329.3",
            )
        )
        self.fixture_response = fixture_response
        self.sequence_calls: list[dict] = []
        self.sequences = {
            ("chr1", 1000, 1014, "-"): fixture_response.segments[0].sequence,
            ("chr1", 970, 999, "-"): fixture_response.segments[1].five_prime_sequence,
            ("chr1", 900, 929, "-"): fixture_response.segments[1].three_prime_sequence,
            ("chr1", 800, 892, "-"): fixture_response.segments[2].sequence,
            ("chr1", 770, 799, "-"): fixture_response.segments[3].five_prime_sequence,
            ("chr1", 700, 729, "-"): fixture_response.segments[3].three_prime_sequence,
            ("chr1", 685, 699, "-"): fixture_response.segments[4].sequence,
        }

    def resolve_variant(self, *, query, genome_build: str) -> VariantProjection:
        variant = self.fixture_response.queried_variant
        return VariantProjection(
            hgvs_c=query.hgvs,
            cds_pos=variant.cds_pos,
            ref=variant.ref,
            alt=variant.alt,
            hgvs_p=variant.hgvs_p,
            genomic_hg38=variant.genomic_hg38,
            codon_number=variant.codon_number,
            codon_offset=variant.codon_offset,
            aa_ref=variant.aa_ref,
            aa_alt=variant.aa_alt,
            classification=variant.classification,
        )

    def fetch_transcript(self, *, query, variant, genome_build: str) -> SourceTranscriptModel:
        return SourceTranscriptModel(
            gene=query.gene,
            transcript=query.resolver_transcript or "NM_000329.3",
            chrom="chr1",
            strand="-",
            exons=(
                SourceTranscriptExon(
                    number=3,
                    cds_start=217,
                    cds_end=231,
                    genomic_start=1000,
                    genomic_end=1014,
                ),
                SourceTranscriptExon(
                    number=4,
                    cds_start=232,
                    cds_end=324,
                    genomic_start=800,
                    genomic_end=892,
                ),
                SourceTranscriptExon(
                    number=5,
                    cds_start=325,
                    cds_end=339,
                    genomic_start=685,
                    genomic_end=699,
                ),
            ),
            introns=(
                SourceTranscriptIntron(number=3, genomic_start=900, genomic_end=999),
                SourceTranscriptIntron(number=4, genomic_start=700, genomic_end=799),
            ),
            ensembl_gene_id="ENSG00000116745",
            transcript_aliases=("ENST00000262340", "MANE Select"),
            gene_start=68428820,
            gene_end=68449958,
            gene_length=21138,
            cds_length=1602,
            protein_length=533,
            utr5_length=89,
            utr3_length=1216,
            mrna_length=2907,
            translation_id="ENSP00000262340",
            warnings=("mocked_source_responses",),
        )

    def fetch_sequence(self, *, chrom: str, start: int, end: int, strand: str) -> str:
        call = {"chrom": chrom, "start": start, "end": end, "strand": strand}
        self.sequence_calls.append(call)
        return self.sequences[(chrom, start, end, strand)]

    def fetch_protein_features(self, *, transcript: SourceTranscriptModel) -> ProteinFeatures:
        return ProteinFeatures(
            domains=[
                ProteinDomain(
                    aa_start=51,
                    aa_end=468,
                    label="Carotenoid oxygenase (source-backed)",
                    short_label="Carotenoid oxygenase",
                )
            ]
        )

    def provenance_sources(self, *, query, transcript, variant) -> list[ViewerProvenanceSource]:
        return [
            ViewerProvenanceSource(
                name="variant_validator",
                identifier=query.resolver_transcript_hgvs,
                url="https://rest.variantvalidator.org/example",
            ),
            ViewerProvenanceSource(
                name="ensembl_rest",
                identifier=transcript.transcript,
                url="https://rest.ensembl.org/example",
            ),
        ]


class ExplodingGeneViewerSourceClient(MockOfficialGeneViewerSourceClient):
    def resolve_variant(self, *, query, genome_build: str) -> VariantProjection:
        raise RuntimeError("boom")


class StaticHttpGeneViewerSourceClient(HttpGeneViewerSourceClient):
    def __init__(self, payloads: dict[str, object]) -> None:
        super().__init__(Settings(jwt_secret="test-secret"))
        self.payloads = payloads
        self.requested_urls: list[str] = []

    def _get_json(self, url: str):
        self.requested_urls.append(url)
        for key, payload in self.payloads.items():
            if key in url:
                return payload
        raise AssertionError(f"Unexpected URL: {url}")


def _ensembl_rpe65_lookup_payload() -> dict:
    return {
        "id": "ENSG00000116745",
        "display_name": "RPE65",
        "seq_region_name": "1",
        "start": 100,
        "end": 500,
        "strand": -1,
        "canonical_transcript": "ENST00000262340.6",
        "Transcript": [
            {
                "id": "ENST00000262340",
                "version": 6,
                "display_name": "RPE65-201",
                "biotype": "protein_coding",
                "is_canonical": 1,
                "seq_region_name": "1",
                "start": 100,
                "end": 500,
                "strand": -1,
                "length": 210,
                "MANE": [{"type": "MANE_Select", "refseq_match": "NM_000329.3"}],
                "Translation": {
                    "id": "ENSP00000262340",
                    "start": 130,
                    "end": 470,
                    "length": 24,
                },
                "UTR": [
                    {"type": "five_prime_utr", "start": 471, "end": 500},
                    {"type": "three_prime_utr", "start": 100, "end": 129},
                ],
                "Exon": [
                    {"start": 460, "end": 500, "strand": -1},
                    {"start": 300, "end": 350, "strand": -1},
                    {"start": 100, "end": 140, "strand": -1},
                ],
            }
        ],
    }


def _ensembl_protein_feature_payload() -> list[dict]:
    return [
        {
            "type": "alphafold",
            "start": 1,
            "end": 533,
            "description": "AlphaFold model",
        },
        {
            "type": "Pfam",
            "start": 16,
            "end": 531,
            "description": "Carotenoid oxygenase",
            "id": "PF03055",
        },
        {
            "type": "Seg",
            "start": 294,
            "end": 305,
            "description": "",
        },
    ]


def _plus_transcript() -> TranscriptModel:
    return TranscriptModel(
        gene="TEST",
        transcript="NM_TEST.1",
        chrom="chr1",
        strand="+",
        exons=(
            TranscriptExon(number=1, cds_start=1, cds_end=9, sequence="AAACCCGGG"),
            TranscriptExon(number=2, cds_start=10, cds_end=18, sequence="TTTAAACCC"),
        ),
        introns=(
            TranscriptIntron(
                number=1,
                total_len=10,
                five_prime_sequence="gt",
                three_prime_sequence="ag",
            ),
        ),
    )


def test_fixture_provider_returns_valid_rpe65_reference_viewer_response() -> None:
    response = GeneViewerFixtureProvider().viewer(
        GeneViewerRequest(gene="RPE65", cdna="c.260A>G", transcript="NM_000329.3")
    )

    assert response.identity.gene == "RPE65"
    assert response.identity.resolved_transcript == "NM_000329.3"
    assert response.locus.strand == "-"
    assert response.queried_variant.hgvs_c == "c.260A>G"
    assert response.queried_variant.ref == "A"
    assert response.queried_variant.alt == "G"
    assert response.sequences.allele_mode == "reference"
    assert (
        response.sequences.reference_window_sequence == response.sequences.display_window_sequence
    )
    assert response.sequences.reference_window_sequence[103] == "A"
    assert response.segments[2].exon_number == 4
    assert response.tracks.protein_features.domains[0].label.startswith("Carotenoid oxygenase")


def test_fixture_provider_applies_variant_mode_to_offline_rpe65_fixture() -> None:
    response = GeneViewerFixtureProvider().viewer(
        GeneViewerRequest(
            gene="RPE65",
            cdna="c.260A>G",
            transcript="NM_000329.3",
            allele_mode="variant",
        )
    )

    assert response.sequences.allele_mode == "variant"
    assert response.sequences.reference_window_sequence[103] == "A"
    assert response.sequences.display_window_sequence[103] == "G"
    assert response.sequences.applied_variant is not None
    assert response.sequences.applied_variant.sequence_offset == 103


def test_http_source_client_builds_transcript_model_from_ensembl_symbol_lookup() -> None:
    source_client = StaticHttpGeneViewerSourceClient(
        {"lookup/symbol": _ensembl_rpe65_lookup_payload()}
    )

    transcript = source_client.fetch_transcript(
        query=normalize_sequence_query("RPE65", "c.260A>G", "NM_000329.3"),
        variant=VariantProjection.from_hgvs_c("c.260A>G"),
        genome_build="GRCh38",
    )

    assert transcript.transcript == "NM_000329.3"
    assert transcript.ensembl_gene_id == "ENSG00000116745"
    assert transcript.chrom == "1"
    assert transcript.strand == "-"
    assert transcript.translation_id == "ENSP00000262340"
    assert transcript.cds_length == 73
    assert transcript.protein_length == 24
    assert transcript.utr5_length == 30
    assert transcript.utr3_length == 30
    assert transcript.transcript_aliases == (
        "NM_000329.3",
        "ENST00000262340.6",
        "RPE65-201",
        "MANE Select",
    )
    assert transcript.exons == (
        SourceTranscriptExon(
            number=1,
            cds_start=1,
            cds_end=11,
            genomic_start=460,
            genomic_end=470,
        ),
        SourceTranscriptExon(
            number=2,
            cds_start=12,
            cds_end=62,
            genomic_start=300,
            genomic_end=350,
        ),
        SourceTranscriptExon(
            number=3,
            cds_start=63,
            cds_end=73,
            genomic_start=130,
            genomic_end=140,
        ),
    )
    assert transcript.introns == (
        SourceTranscriptIntron(number=1, genomic_start=351, genomic_end=459),
        SourceTranscriptIntron(number=2, genomic_start=141, genomic_end=299),
    )
    assert "live_source_transcript_from_ensembl" in transcript.warnings


def test_http_source_client_maps_ensembl_translation_overlap_to_domains() -> None:
    source_client = StaticHttpGeneViewerSourceClient(
        {"overlap/translation": _ensembl_protein_feature_payload()}
    )

    features = source_client.fetch_protein_features(
        transcript=SourceTranscriptModel(
            gene="RPE65",
            transcript="NM_000329.3",
            chrom="1",
            strand="-",
            exons=(),
            translation_id="ENSP00000262340",
        )
    )

    assert features is not None
    assert features.domains == [
        ProteinDomain(
            aa_start=16,
            aa_end=531,
            label="Carotenoid oxygenase",
            short_label="Carotenoid oxygenase",
        )
    ]


def test_source_backed_provider_builds_rpe65_viewer_from_mocked_official_sources() -> None:
    source_client = MockOfficialGeneViewerSourceClient()
    provider = SourceBackedGeneViewerProvider(source_client=source_client)

    response = provider.viewer(
        GeneViewerRequest(
            gene="RPE65",
            cdna="c.260A>G",
            transcript="NM_000329.3",
            allele_mode="variant",
            window=ViewerWindowRequest(
                kind="cds_range",
                cds_start=217,
                cds_end=339,
                intron_flank_bp=30,
            ),
        )
    )

    assert response.identity.gene == "RPE65"
    assert response.identity.resolved_transcript == "NM_000329.3"
    assert response.locus.strand == "-"
    assert response.queried_variant.genomic_hg38 == "1-68444869-T-C"
    assert response.sequences.reference_window_sequence[103] == "A"
    assert response.sequences.display_window_sequence[103] == "G"
    assert response.sequences.applied_variant is not None
    assert response.sequences.applied_variant.segment_id == "exon-4:232-324"
    assert response.tracks.protein_features.domains[0].label == (
        "Carotenoid oxygenase (source-backed)"
    )
    assert [source.name for source in response.provenance.sources] == [
        "variant_validator",
        "ensembl_rest",
    ]
    assert response.provenance.warnings == ["mocked_source_responses"]
    assert {"chrom": "chr1", "start": 970, "end": 999, "strand": "-"} in (
        source_client.sequence_calls
    )


@pytest.mark.parametrize(
    "payload,expected_code",
    [
        (
            GeneViewerRequest(gene="RPE65", cdna="c.260A>G", species="mouse"),
            unsupported_input_warning("species"),
        ),
        (
            GeneViewerRequest(gene="RPE65", cdna="c.260A>G", genome_build="GRCh37"),
            unsupported_input_warning("genome_build"),
        ),
        (
            GeneViewerRequest(gene="RPE65", cdna="rs1645931040"),
            unsupported_input_warning("rsid"),
        ),
    ],
)
def test_source_backed_provider_rejects_unsupported_inputs(
    payload: GeneViewerRequest,
    expected_code: str,
) -> None:
    provider = SourceBackedGeneViewerProvider(source_client=MockOfficialGeneViewerSourceClient())

    with pytest.raises(GeneViewerError) as error:
        provider.viewer(payload)

    assert error.value.code == expected_code
    assert error.value.status_code == 422


def test_source_backed_provider_failures_map_to_workbench_style_503() -> None:
    provider = SourceBackedGeneViewerProvider(source_client=ExplodingGeneViewerSourceClient())

    with pytest.raises(GeneViewerError) as error:
        provider.viewer(
            GeneViewerRequest(
                gene="RPE65",
                cdna="c.260A>G",
                transcript="NM_000329.3",
            )
        )

    assert error.value.code == f"{GENE_VIEWER_PROVIDER_FAILED_PREFIX}:RuntimeError"
    assert error.value.status_code == 503


def test_create_app_wires_gene_viewer_service(app) -> None:
    assert isinstance(app.state.gene_viewer_service, GeneViewerService)


def test_viewer_endpoint_returns_rpe65_fixture_response(client) -> None:
    response = client.post(
        "/api/v1/viewer",
        json={"gene": "RPE65", "cdna": "c.260A>G", "transcript": "NM_000329.3"},
    )

    fixture = json.loads((FIXTURES_DIR / "viewer_rpe65.json").read_text(encoding="utf-8"))
    assert response.status_code == 200
    body = response.json()
    assert body["identity"] == fixture["identity"]
    assert body["queried_variant"] == fixture["queried_variant"]
    assert body["sequences"] == fixture["sequences"]
    assert body["tracks"]["protein_features"] == fixture["tracks"]["protein_features"]


def test_viewer_endpoint_applies_variant_mode_to_fixture_response(client) -> None:
    response = client.post(
        "/api/v1/viewer",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "transcript": "NM_000329.3",
            "allele_mode": "variant",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sequences"]["allele_mode"] == "variant"
    assert body["sequences"]["reference_window_sequence"][103] == "A"
    assert body["sequences"]["display_window_sequence"][103] == "G"
    assert body["sequences"]["applied_variant"]["sequence_offset"] == 103


def test_viewer_endpoint_service_failures_map_to_structured_http_errors(client) -> None:
    client.app.state.gene_viewer_service = FailingGeneViewerService(
        GeneViewerError(
            code="workbench_provider_malformed",
            message="Provider returned an invalid viewer payload.",
            status_code=status.HTTP_502_BAD_GATEWAY,
            warnings=["workbench_provider_malformed", "missing_segments"],
        )
    )

    response = client.post(
        "/api/v1/viewer",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": "workbench_provider_malformed",
        "message": "Provider returned an invalid viewer payload.",
        "warnings": ["workbench_provider_malformed", "missing_segments"],
    }


def test_viewer_endpoint_uses_injected_live_provider_when_real_mode_is_enabled(client) -> None:
    source_client = MockOfficialGeneViewerSourceClient()
    client.app.state.gene_viewer_service = GeneViewerService(
        settings=Settings(jwt_secret="test-secret", use_real_apis=True),
        live_provider=SourceBackedGeneViewerProvider(source_client=source_client),
    )

    response = client.post(
        "/api/v1/viewer",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "transcript": "NM_000329.3",
            "allele_mode": "variant",
            "window": {
                "kind": "cds_range",
                "cds_start": 217,
                "cds_end": 339,
                "intron_flank_bp": 30,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provenance"]["sources"][0]["name"] == "variant_validator"
    assert body["sequences"]["display_window_sequence"][103] == "G"
    assert {"chrom": "chr1", "start": 970, "end": 999, "strand": "-"} in (
        source_client.sequence_calls
    )


def test_window_builder_reference_mode_preserves_reference_sequence() -> None:
    response = TranscriptWindowBuilder().build(
        request=_request(cds_start=8, cds_end=12),
        transcript=_plus_transcript(),
        variant=VariantProjection.from_hgvs_c("c.11T>G"),
    )

    assert [segment.kind for segment in response.segments] == ["exon", "intron", "exon"]
    assert response.sequences.reference_window_sequence == "GGgtagTTT"
    assert response.sequences.display_window_sequence == "GGgtagTTT"
    assert response.sequences.applied_variant is None
    assert response.sequences.reference_window_sequence[7] == "T"


def test_window_builder_variant_mode_applies_only_requested_snv() -> None:
    response = TranscriptWindowBuilder().build(
        request=_request(allele_mode="variant", cds_start=8, cds_end=12),
        transcript=_plus_transcript(),
        variant=VariantProjection.from_hgvs_c("c.11T>G"),
    )

    assert response.sequences.reference_window_sequence == "GGgtagTTT"
    assert response.sequences.display_window_sequence == "GGgtagTGT"
    assert response.sequences.applied_variant is not None
    assert response.sequences.applied_variant.segment_id == "exon-2:10-12"
    assert response.sequences.applied_variant.sequence_offset == 7


def test_window_builder_renders_reverse_strand_in_transcript_order() -> None:
    transcript = TranscriptModel(
        gene="REV",
        transcript="NM_REV.1",
        chrom="chr2",
        strand="-",
        exons=(
            TranscriptExon(
                number=2,
                cds_start=4,
                cds_end=6,
                sequence="CCC",
                genomic_start=200,
                genomic_end=202,
            ),
            TranscriptExon(
                number=1,
                cds_start=1,
                cds_end=3,
                sequence="AAA",
                genomic_start=300,
                genomic_end=302,
            ),
        ),
        introns=(
            TranscriptIntron(
                number=1,
                total_len=8,
                five_prime_sequence="gc",
                three_prime_sequence="ag",
            ),
        ),
    )

    response = TranscriptWindowBuilder().build(
        request=GeneViewerRequest(
            gene="REV",
            cdna="c.5C>T",
            transcript="NM_REV.1",
            allele_mode="variant",
            window=ViewerWindowRequest(kind="cds_range", cds_start=1, cds_end=6),
        ),
        transcript=transcript,
        variant=VariantProjection.from_hgvs_c("c.5C>T"),
    )

    assert [segment.id for segment in response.segments] == [
        "exon-1:1-3",
        "intron-1",
        "exon-2:4-6",
    ]
    assert response.locus.strand == "-"
    assert response.sequences.reference_window_sequence == "AAAgcagCCC"
    assert response.sequences.display_window_sequence == "AAAgcagCTC"


def test_window_builder_reference_mismatch_fails_closed() -> None:
    with pytest.raises(GeneViewerError) as error:
        TranscriptWindowBuilder().build(
            request=_request(cds_start=1, cds_end=9),
            transcript=_plus_transcript(),
            variant=VariantProjection.from_hgvs_c("c.2G>T"),
        )

    assert error.value.code == GENE_VIEWER_REFERENCE_MISMATCH
    assert error.value.status_code == 422
