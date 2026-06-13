from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import status

from app.core.config import Settings
from app.schemas.gene_viewer import (
    GeneViewerResponse,
    GeneViewerRequest,
    ProteinDomain,
    ProteinFeatures,
    ViewerProvenanceSource,
    ViewerWindow,
    ViewerWindowRequest,
)
from app.services.reference_genome import ReferenceWindow
from app.services.sequence_context import normalize_sequence_query, unsupported_input_warning
from app.services.compact_coordinate_index import CompactCoordinateIndex
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
from app.services.gene_context_snapshot import GeneContextSnapshotService

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "workbench"
COMPACT_INDEX_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "fixtures"
    / "coordinate_index"
    / "eamos_coordinate_index_tiny.jsonl"
)


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
            gene_length=21139,
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


class MockGenericGeneViewerSourceClient:
    def __init__(self) -> None:
        self.transcript_queries: list[object] = []
        self.variant_queries: list[object] = []

    def resolve_variant(self, *, query, genome_build: str) -> VariantProjection:
        self.variant_queries.append(query)
        assert query.resolver_transcript == "NM_GENERIC.1"
        variant = VariantProjection.from_hgvs_c(query.hgvs)
        return VariantProjection(
            hgvs_c=variant.hgvs_c,
            cds_pos=variant.cds_pos,
            ref=variant.ref,
            alt=variant.alt,
            genomic_hg38="7-200-G-A",
            codon_number=3,
            codon_offset=1,
        )

    def fetch_transcript(self, *, query, variant, genome_build: str) -> SourceTranscriptModel:
        self.transcript_queries.append(query)
        assert query.resolver_transcript is None
        return SourceTranscriptModel(
            gene=query.gene,
            transcript="ENSTGENERIC.1",
            chrom="7",
            strand="+",
            exons=(
                SourceTranscriptExon(
                    number=1,
                    cds_start=1,
                    cds_end=6,
                    genomic_start=100,
                    genomic_end=105,
                ),
                SourceTranscriptExon(
                    number=2,
                    cds_start=7,
                    cds_end=12,
                    genomic_start=200,
                    genomic_end=205,
                ),
            ),
            introns=(SourceTranscriptIntron(number=1, genomic_start=106, genomic_end=199),),
            ensembl_gene_id="ENSGGENERIC",
            transcript_aliases=("ENSTGENERIC.1", "NM_GENERIC.1", "MANE Select"),
            gene_start=90,
            gene_end=210,
            gene_length=121,
            cds_length=12,
            protein_length=4,
            mrna_length=12,
            translation_id="ENSPGENERIC",
            warnings=("mocked_generic_source",),
        )

    def fetch_sequence(self, *, chrom: str, start: int, end: int, strand: str) -> str:
        sequences = {
            ("7", 100, 105, "+"): "AAACCC",
            ("7", 106, 135, "+"): "gtacgtacgtacgtacgtacgtacgtacgt",
            ("7", 170, 199, "+"): "agctagctagctagctagctagctagctag",
            ("7", 200, 205, "+"): "GGGTTT",
        }
        return sequences[(chrom, start, end, strand)]

    def fetch_protein_features(self, *, transcript: SourceTranscriptModel) -> ProteinFeatures:
        return ProteinFeatures()

    def provenance_sources(self, *, query, transcript, variant) -> list[ViewerProvenanceSource]:
        return [
            ViewerProvenanceSource(
                name="variant_validator",
                identifier=query.resolver_transcript_hgvs,
                url="https://rest.variantvalidator.org/generic",
            ),
            ViewerProvenanceSource(
                name="ensembl_rest",
                identifier=transcript.transcript,
                url="https://rest.ensembl.org/generic",
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


def test_http_gene_viewer_source_client_reads_materialized_hg38_sequence(monkeypatch) -> None:
    class ReferenceStore:
        def __init__(self) -> None:
            self.closed = False

        def get_sequence(self, chrom: str, start: int, end: int, build: str | None = None):
            assert (chrom, start, end, build) == ("chr7", 10, 13, "GRCh38")
            return ReferenceWindow(
                requested_chrom=chrom,
                chrom="7",
                start=start,
                end=end,
                zero_based_start=9,
                zero_based_end_exclusive=13,
                sequence="AAGC",
                genome_build="GRCh38",
                source_id="ucsc_hg38_2bit",
            )

        def close(self) -> None:
            self.closed = True

    resolved = SimpleNamespace(
        source_id="ucsc_hg38_2bit",
        byte_size=835393456,
        checksum_value="dcc3ea27079aa6dc3f9deccd7275e0f8",
    )
    store = ReferenceStore()
    monkeypatch.setattr(
        "app.services.gene_viewer.resolve_hg38_materialized_runtime_asset",
        lambda *_args, **_kwargs: resolved,
    )
    client = HttpGeneViewerSourceClient(
        Settings(jwt_secret="test-secret"),
        materialization_store=object(),
        reference_store_factory=lambda _resolved: store,
    )

    sequence = client.fetch_sequence(chrom="chr7", start=10, end=13, strand="-")

    assert sequence == "GCTT"
    assert store.closed is True


def test_http_source_client_uses_compact_coordinate_index_before_http(
    monkeypatch,
) -> None:
    def fail_http(url: str, **_kwargs):
        raise AssertionError(f"compact coordinate index should avoid HTTP, got {url}")

    monkeypatch.setattr("app.services.gene_viewer.httpx.get", fail_http)
    query = normalize_sequence_query("RPE65", "c.260A>G", "NM_000329.3")
    client = HttpGeneViewerSourceClient(
        Settings(jwt_secret="test-secret"),
        compact_index=CompactCoordinateIndex(COMPACT_INDEX_FIXTURE),
    )

    variant = client.resolve_variant(query=query, genome_build="GRCh38")
    transcript = client.fetch_transcript(
        query=query,
        variant=variant,
        genome_build="GRCh38",
    )
    sources = client.provenance_sources(
        query=query,
        transcript=transcript,
        variant=variant,
    )

    assert variant.genomic_hg38 == "1-68444869-T-C"
    assert variant.hgvs_p == "p.Asp87Gly"
    assert transcript.transcript == "NM_000329.3"
    assert transcript.exons[1].genomic_start == 68444805
    assert "compact_coordinate_index_transcript" in transcript.warnings
    assert [source.name for source in sources] == ["eamos_compact_coordinate_index"]
    assert sources[0].identifier == "NM_000329.3"
    assert sources[0].url is None
    encoded_sources = json.dumps([source.model_dump() for source in sources]).lower()
    assert str(COMPACT_INDEX_FIXTURE).lower() not in encoded_sources


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


def _full_locus_response(
    *,
    gene: str,
    chrom: str,
    start: int,
    end: int,
    strand: str,
    transcript: str,
    cds_pos: int,
    genomic_variant_pos: int,
) -> GeneViewerResponse:
    length = end - start + 1
    return GeneViewerResponse(
        identity={
            "gene": gene,
            "requested_transcript": transcript,
            "resolved_transcript": transcript,
            "species": "human",
            "genome_build": "GRCh38",
        },
        locus={"chrom": chrom, "gene_start": start, "gene_end": end, "strand": strand},
        summary={
            "gene_length": length,
            "total_exons": 2,
            "cds_length": 600,
            "protein_length": 200,
            "utr5_length": 75,
            "utr3_length": 125,
            "mrna_length": 800,
        },
        window=ViewerWindow(
            kind="full_gene",
            basis="genomic_locus",
            cds_start=1,
            cds_end=600,
            cds_flank_bp=0,
            intron_flank_bp=0,
            display_cds_start=1,
            display_cds_end=600,
            total_display_bases=length,
            display_genomic_start=start,
            display_genomic_end=end,
            total_locus_bases=length,
        ),
        segments=[],
        queried_variant={
            "hgvs_c": f"c.{cds_pos}A>G",
            "cds_pos": cds_pos,
            "genomic_hg38": f"{chrom}-{genomic_variant_pos}-A-G",
            "ref": "A",
            "alt": "G",
            "codon_number": (cds_pos + 2) // 3,
            "codon_offset": (cds_pos - 1) % 3,
            "classification": "vus",
        },
        sequences={
            "allele_mode": "reference",
            "reference_window_sequence": "",
            "display_window_sequence": "",
        },
        full_locus={
            "locus": {
                "chrom": chrom,
                "start": start,
                "end": end,
                "strand": strand,
                "genome_build": "GRCh38",
                "sequence": "N" * length,
            },
            "transcript_projection": {
                "transcript": transcript,
                "strand": strand,
                "intervals": [
                    {
                        "id": f"{gene.lower()}-utr5",
                        "kind": "utr5",
                        "label": "5' UTR",
                        "genomic_start": start,
                        "genomic_end": start + 74,
                        "strand": strand,
                        "cdna_start": 1,
                        "cdna_end": 75,
                    },
                    {
                        "id": f"{gene.lower()}-exon-1",
                        "kind": "exon",
                        "label": "Exon 1",
                        "genomic_start": start + 75,
                        "genomic_end": start + 374,
                        "strand": strand,
                        "exon_number": 1,
                        "cdna_start": 76,
                        "cdna_end": 375,
                        "cds_start": 1,
                        "cds_end": 300,
                        "protein_start": 1,
                        "protein_end": 100,
                    },
                    {
                        "id": f"{gene.lower()}-intron-1",
                        "kind": "intron",
                        "label": "Intron 1",
                        "genomic_start": start + 375,
                        "genomic_end": end - 300,
                        "strand": strand,
                        "intron_number": 1,
                    },
                ],
                "coordinate_map": [
                    {
                        "genomic_start": start + 75,
                        "genomic_end": start + 374,
                        "cdna_start": 76,
                        "cdna_end": 375,
                        "cds_start": 1,
                        "cds_end": 300,
                        "protein_start": 1,
                        "protein_end": 100,
                    }
                ],
                "codon_starts": [
                    {
                        "codon_number": (cds_pos + 2) // 3,
                        "cds_start": cds_pos - ((cds_pos - 1) % 3),
                        "protein_position": (cds_pos + 2) // 3,
                        "genomic_start": genomic_variant_pos,
                        "genomic_positions": [
                            genomic_variant_pos,
                            genomic_variant_pos + 1,
                            genomic_variant_pos + 2,
                        ],
                    }
                ],
            },
            "feature_intervals": [
                {
                    "id": f"{gene.lower()}-queried-variant",
                    "kind": "queried_variant",
                    "label": f"{gene} queried variant",
                    "coordinate_system": "genomic",
                    "start": genomic_variant_pos,
                    "end": genomic_variant_pos,
                    "strand": strand,
                    "source": "contract_test",
                    "classification": "vus",
                    "metadata": {"cds_pos": cds_pos},
                }
            ],
            "rendering_hints": {
                "orientation": "genomic_forward",
                "row_coordinate_policy": "genomic",
                "bases_per_row_min": 80,
                "bases_per_row_max": 140,
                "max_visual_density": 250000,
                "base_color_scheme": "none",
                "amino_acid_color_scheme": "biochemical",
            },
        },
    )


@pytest.mark.parametrize(
    "gene,chrom,start,end,strand,transcript,cds_pos,genomic_variant_pos",
    [
        ("RPE65", "1", 68428821, 68449958, "-", "NM_000329.3", 260, 68444869),
        ("ABCA4", "1", 93992834, 94121148, "-", "NM_000350.3", 5435, 94014568),
    ],
)
def test_full_locus_contract_represents_complete_gene_loci(
    gene: str,
    chrom: str,
    start: int,
    end: int,
    strand: str,
    transcript: str,
    cds_pos: int,
    genomic_variant_pos: int,
) -> None:
    response = _full_locus_response(
        gene=gene,
        chrom=chrom,
        start=start,
        end=end,
        strand=strand,
        transcript=transcript,
        cds_pos=cds_pos,
        genomic_variant_pos=genomic_variant_pos,
    )

    full_locus = response.full_locus
    assert full_locus is not None
    assert response.window.kind == "full_gene"
    assert response.window.basis == "genomic_locus"
    assert response.window.total_locus_bases == end - start + 1
    assert len(full_locus.locus.sequence) == response.window.total_locus_bases
    assert full_locus.locus.coordinate_system == "genomic"
    assert full_locus.transcript_projection.coordinate_map[0].cds_start == 1
    assert full_locus.transcript_projection.codon_starts[0].protein_position == (cds_pos + 2) // 3
    assert full_locus.feature_intervals[0].coordinate_system == "genomic"
    assert full_locus.rendering_hints.base_color_scheme == "none"
    assert full_locus.rendering_hints.amino_acid_color_scheme == "biochemical"


@pytest.mark.parametrize(
    "gene,cdna,transcript,expected_length,expected_exons,variant_position",
    [
        ("RPE65", "c.260A>G", "NM_000329.3", 21139, 14, 68444869),
        ("ABCA4", "c.5435T>A", "NM_000350.3", 128315, 50, 94014568),
    ],
)
def test_fixture_provider_hydrates_full_gene_locus_payloads(
    gene: str,
    cdna: str,
    transcript: str,
    expected_length: int,
    expected_exons: int,
    variant_position: int,
) -> None:
    response = GeneViewerFixtureProvider().viewer(
        GeneViewerRequest(
            gene=gene,
            cdna=cdna,
            transcript=transcript,
            window=ViewerWindowRequest(kind="full_gene"),
        )
    )

    full_locus = response.full_locus
    assert full_locus is not None
    assert response.window.kind == "full_gene"
    assert response.window.basis == "genomic_locus"
    assert response.window.total_locus_bases == expected_length
    assert response.window.total_display_bases == expected_length
    assert response.summary.gene_length == expected_length
    assert response.summary.total_exons == expected_exons
    assert len(full_locus.locus.sequence) == expected_length
    assert full_locus.locus.sequence != response.sequences.reference_window_sequence
    assert response.sequences.reference_window_sequence == ""
    assert full_locus.locus.coordinate_system == "genomic"
    assert full_locus.rendering_hints.base_color_scheme == "none"
    assert full_locus.rendering_hints.amino_acid_color_scheme == "biochemical"
    assert full_locus.rendering_hints.orientation == "genomic_reverse"
    assert full_locus.rendering_hints.max_visual_density == expected_length
    assert len(full_locus.transcript_projection.coordinate_map) == expected_exons
    assert full_locus.transcript_projection.codon_starts
    assert any(
        feature.kind == "queried_variant"
        and feature.coordinate_system == "genomic"
        and feature.start == variant_position
        for feature in full_locus.feature_intervals
    )
    assert "full_gene_fixture_hydrated" in response.provenance.warnings


def test_abca4_full_gene_fixture_is_not_clipped_to_variant_window() -> None:
    response = GeneViewerFixtureProvider().viewer(
        GeneViewerRequest(
            gene="ABCA4",
            cdna="c.5435T>A",
            transcript="NM_000350.3",
            window=ViewerWindowRequest(kind="full_gene"),
        )
    )

    assert response.full_locus is not None
    assert response.locus.gene_start == 93992834
    assert response.locus.gene_end == 94121148
    assert response.window.total_locus_bases == 128315
    assert response.window.total_display_bases > 5000
    assert response.window.display_genomic_start == 93992834
    assert response.window.display_genomic_end == 94121148
    assert response.full_locus.transcript_projection.coordinate_map[0].cds_start == 1
    assert response.full_locus.transcript_projection.coordinate_map[-1].cds_end == 6822


def test_full_gene_fixture_missing_transcript_fails_closed() -> None:
    with pytest.raises(GeneViewerError) as error:
        GeneViewerFixtureProvider().viewer(
            GeneViewerRequest(
                gene="ABCA4",
                cdna="c.5435T>A",
                transcript="NM_MISSING.1",
                window=ViewerWindowRequest(kind="full_gene"),
            )
        )

    assert error.value.status_code == 422
    assert error.value.code == unsupported_input_warning("fixture")


def test_full_gene_fixture_reference_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture_path = tmp_path / "gene_viewer_transcript_models.json"
    fixture_path.write_text(
        json.dumps(
            {
                "version": "test",
                "records": [
                    {
                        "gene": "TEST",
                        "cdna": "c.2A>G",
                        "transcript": "NM_TEST.1",
                        "requested_transcript": "NM_TEST.1",
                        "transcript_aliases": ["NM_TEST.1"],
                        "chrom": "1",
                        "strand": "+",
                        "species": "human",
                        "genome_build": "GRCh38",
                        "gene_start": 100,
                        "gene_end": 110,
                        "gene_length": 11,
                        "cds_length": 3,
                        "protein_length": 1,
                        "variant": {
                            "hgvs_c": "c.2A>G",
                            "cds_pos": 2,
                            "ref": "A",
                            "alt": "G",
                            "genomic_hg38": "1-101-A-G",
                        },
                        "exons": [
                            {
                                "number": 1,
                                "cds_start": 1,
                                "cds_end": 3,
                                "genomic_start": 100,
                                "genomic_end": 102,
                                "sequence": "CCC",
                            }
                        ],
                        "introns": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(GeneViewerError) as error:
        GeneViewerFixtureProvider(fixtures_dir=tmp_path).viewer(
            GeneViewerRequest(
                gene="TEST",
                cdna="c.2A>G",
                transcript="NM_TEST.1",
                window=ViewerWindowRequest(kind="full_gene"),
            )
        )

    assert error.value.status_code == 422
    assert error.value.code == GENE_VIEWER_REFERENCE_MISMATCH


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
    assert response.queried_variant.classification == "vus"
    assert response.sequences.allele_mode == "reference"
    assert (
        response.sequences.reference_window_sequence == response.sequences.display_window_sequence
    )
    assert response.sequences.reference_window_sequence[103] == "A"
    assert response.segments[2].exon_number == 4
    query_track_variant = next(item for item in response.tracks.clinvar_variants if item.queried)
    assert query_track_variant.clinvar_id == "VCV001421454"
    assert query_track_variant.classification == "vus"
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


def test_fixture_provider_returns_curated_non_rpe65_transcript_viewer_response() -> None:
    response = GeneViewerFixtureProvider().viewer(
        GeneViewerRequest(
            gene="CFTR",
            cdna="c.199C>T",
            transcript="NM_000492.4",
            allele_mode="variant",
        )
    )

    assert response.identity.gene == "CFTR"
    assert response.identity.resolved_transcript == "NM_000492.4"
    assert response.summary.total_exons == 27
    assert response.locus.chrom == "7"
    assert response.queried_variant.hgvs_p == "p.Pro67Ser"
    assert response.queried_variant.genomic_hg38 == "7-117509068-C-T"
    assert response.sequences.applied_variant is not None
    assert response.sequences.applied_variant.ref == "C"
    assert response.sequences.applied_variant.alt == "T"
    assert {segment.exon_number for segment in response.segments if segment.exon_number} == {
        2,
        3,
        4,
    }
    assert response.tracks.clinvar_variants[0].clinvar_id.startswith("VCV")
    assert "transcript_model_from_ensembl_rest_fixture" in response.provenance.warnings


def test_gene_context_snapshot_fixture_returns_static_report_contract() -> None:
    snapshot = GeneContextSnapshotService().build(
        gene="RPE65",
        cdna="c.260A>G",
        transcript="NM_000329.3",
    )

    assert snapshot.source_status == "fixture"
    assert snapshot.section_id == "section-2-gene-context"
    assert snapshot.gene == "RPE65"
    assert snapshot.transcript == "NM_000329.3"
    assert len(snapshot.exons) == 14
    assert len(snapshot.introns) == 13
    assert snapshot.exons[3].number == 4
    assert snapshot.exons[3].cds_start == 232
    assert snapshot.exons[3].cds_end == 324
    assert snapshot.variant is not None
    assert snapshot.variant.membership == "exon"
    assert snapshot.variant.exon_number == 4
    assert snapshot.variant.transcript_offset == 4062
    assert snapshot.zoom_window is not None
    assert snapshot.zoom_window.display_cds_start == 217
    assert snapshot.zoom_segments[2].exon_number == 4
    assert snapshot.workbench_link is not None
    assert snapshot.workbench_link.url == (
        "/workbench?gene=RPE65&cdna=c.260A%3EG&transcript=NM_000329.3"
    )
    assert "transcript_model_from_rpe65_fixture_scaffold" in snapshot.warnings


def test_gene_context_snapshot_fixture_populates_curated_non_rpe65_transcript() -> None:
    snapshot = GeneContextSnapshotService().build(
        gene="CFTR",
        cdna="c.199C>T",
        transcript="NM_000492.4",
    )

    assert snapshot.source_status == "fixture"
    assert snapshot.gene == "CFTR"
    assert snapshot.transcript == "NM_000492.4"
    assert snapshot.chromosome == "7"
    assert len(snapshot.exons) == 27
    assert len(snapshot.introns) == 26
    assert snapshot.variant is not None
    assert snapshot.variant.membership == "exon"
    assert snapshot.variant.exon_number == 3
    assert snapshot.variant.genomic_hg38 == "7-117509068-C-T"
    assert snapshot.zoom_window is not None
    assert snapshot.zoom_window.display_cds_start == 79
    assert {segment.exon_number for segment in snapshot.zoom_segments if segment.exon_number} == {
        2,
        3,
        4,
    }
    assert snapshot.workbench_link is not None
    assert snapshot.workbench_link.url == (
        "/workbench?gene=CFTR&cdna=c.199C%3ET&transcript=NM_000492.4"
    )
    assert "transcript_model_from_ensembl_rest_fixture" in snapshot.warnings
    assert "transcript_model_from_rpe65_fixture_scaffold" not in snapshot.warnings


def test_gene_context_snapshot_source_backed_generic_gene_uses_source_transcript() -> None:
    service = GeneContextSnapshotService(
        source_provider=SourceBackedGeneViewerProvider(
            source_client=MockGenericGeneViewerSourceClient()
        )
    )

    snapshot = service.build(gene="GENE", cdna="c.8G>A")

    assert snapshot.source_status == "live"
    assert snapshot.gene == "GENE"
    assert snapshot.transcript == "ENSTGENERIC.1"
    assert snapshot.ensembl_gene_id == "ENSGGENERIC"
    assert [(exon.number, exon.genomic_start, exon.genomic_end) for exon in snapshot.exons] == [
        (1, 100, 105),
        (2, 200, 205),
    ]
    assert [(intron.number, intron.length_bp) for intron in snapshot.introns] == [(1, 94)]
    assert snapshot.variant is not None
    assert snapshot.variant.exon_number == 2
    assert snapshot.variant.transcript_offset == 102
    assert snapshot.zoom_segments[1].intron_number == 1
    assert "transcript_model_from_rpe65_fixture_scaffold" not in snapshot.warnings


def test_gene_context_snapshot_fixture_missing_does_not_import_rpe65_scaffold() -> None:
    snapshot = GeneContextSnapshotService().build(gene="CFTR", cdna="c.1521_1523delCTT")

    assert snapshot.source_status == "missing"
    assert snapshot.gene == "CFTR"
    assert snapshot.exons == []
    assert snapshot.introns == []
    assert snapshot.variant is not None
    assert snapshot.variant.hgvs_c == "c.1521_1523delCTT"
    assert snapshot.variant.membership == "unknown"
    assert "gene_context_snapshot_fixture_unavailable" in snapshot.warnings


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


def test_source_backed_provider_uses_curated_fixture_for_full_gene_until_live_hydration() -> None:
    provider = SourceBackedGeneViewerProvider(source_client=ExplodingGeneViewerSourceClient())

    response = provider.viewer(
        GeneViewerRequest(
            gene="ABCA4",
            cdna="c.5435T>A",
            transcript="NM_000350.3",
            window=ViewerWindowRequest(kind="full_gene"),
        )
    )

    assert response.identity.gene == "ABCA4"
    assert response.window.kind == "full_gene"
    assert response.window.basis == "genomic_locus"
    assert response.full_locus is not None
    assert response.window.total_locus_bases == 128315
    assert "full_gene_fixture_hydrated" in response.provenance.warnings


def test_source_backed_provider_uses_ensembl_transcript_for_non_rpe65_request() -> None:
    source_client = MockGenericGeneViewerSourceClient()
    provider = SourceBackedGeneViewerProvider(source_client=source_client)

    response = provider.viewer(
        GeneViewerRequest(
            gene="CFTR",
            cdna="c.8G>A",
            allele_mode="variant",
            window=ViewerWindowRequest(
                kind="cds_range",
                cds_start=1,
                cds_end=12,
                intron_flank_bp=0,
            ),
        )
    )

    assert response.identity.gene == "CFTR"
    assert response.identity.resolved_transcript == "ENSTGENERIC.1"
    assert "NM_GENERIC.1" in response.identity.transcript_aliases
    assert response.sequences.reference_window_sequence == "AAACCCGGGTTT"
    assert response.sequences.display_window_sequence == "AAACCCGAGTTT"
    assert response.sequences.applied_variant is not None
    assert response.sequences.applied_variant.sequence_offset == 7
    assert source_client.transcript_queries[0].resolver_transcript is None
    assert source_client.variant_queries[0].resolver_transcript == "NM_GENERIC.1"
    assert response.provenance.sources[0].identifier == "NM_GENERIC.1:c.8G>A"
    assert response.provenance.warnings == ["mocked_generic_source"]


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
    assert body["tracks"]["protein_product"]["allele_mode"] == "variant"
    assert body["tracks"]["protein_product"]["consequence"] == "missense"


def test_viewer_endpoint_returns_curated_non_rpe65_fixture_response(client) -> None:
    response = client.post(
        "/api/v1/viewer",
        json={
            "gene": "CFTR",
            "cdna": "c.199C>T",
            "transcript": "NM_000492.4",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["identity"]["gene"] == "CFTR"
    assert body["identity"]["resolved_transcript"] == "NM_000492.4"
    assert body["summary"]["total_exons"] == 27
    assert body["queried_variant"]["genomic_hg38"] == "7-117509068-C-T"
    assert body["segments"][2]["exon_number"] == 3
    assert "transcript_model_from_ensembl_rest_fixture" in body["provenance"]["warnings"]
    assert "transcript_model_from_rpe65_fixture_scaffold" not in body["provenance"]["warnings"]


def test_viewer_endpoint_rejects_oversized_schema_inputs(client) -> None:
    overlong_gene = client.post(
        "/api/v1/viewer",
        json={"gene": "G" * 33, "cdna": "c.260A>G"},
    )
    too_many_tracks = client.post(
        "/api/v1/viewer",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "tracks": ["sequence"] * 9,
        },
    )

    assert overlong_gene.status_code == 422
    assert too_many_tracks.status_code == 422


def test_viewer_endpoint_rejects_non_overlapping_window(client) -> None:
    response = client.post(
        "/api/v1/viewer",
        json={
            "gene": "CFTR",
            "cdna": "c.199C>T",
            "transcript": "NM_000492.4",
            "window": {
                "kind": "cds_range",
                "cds_start": 50000,
                "cds_end": 1,
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == unsupported_input_warning("fixture_window")


def test_viewer_endpoint_returns_full_gene_fixture_response(client) -> None:
    response = client.post(
        "/api/v1/viewer",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "transcript": "NM_000329.3",
            "window": {"kind": "full_gene"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["window"]["kind"] == "full_gene"
    assert body["window"]["basis"] == "genomic_locus"
    assert body["full_locus"]["basis"] == "genomic_locus"
    assert len(body["full_locus"]["locus"]["sequence"]) == body["window"]["total_locus_bases"]
    assert body["full_locus"]["feature_intervals"][2]["kind"] == "queried_variant"


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


def test_viewer_endpoint_full_gene_uses_fixture_fallback_in_real_mode(client) -> None:
    client.app.state.gene_viewer_service = GeneViewerService(
        settings=Settings(jwt_secret="test-secret", use_real_apis=True),
        live_provider=SourceBackedGeneViewerProvider(
            source_client=ExplodingGeneViewerSourceClient()
        ),
    )

    response = client.post(
        "/api/v1/viewer",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "transcript": "NM_000329.3",
            "window": {"kind": "full_gene"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["window"]["kind"] == "full_gene"
    assert body["window"]["basis"] == "genomic_locus"
    assert body["full_locus"]["basis"] == "genomic_locus"
    assert "full_gene_fixture_hydrated" in body["provenance"]["warnings"]


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


@pytest.mark.parametrize(
    "hgvs_c,expected,ref,alt,offset",
    [
        ("c.4_6delGAA", "ATG", "GAA", "", 3),
        ("c.3_4insTT", "ATGTTGAA", "", "TT", 3),
        ("c.4_6dupGAA", "ATGGAAGAA", "", "GAA", 6),
        ("c.4_6delinsTT", "ATGTT", "GAA", "TT", 3),
    ],
)
def test_window_builder_applies_simple_indel_dup_and_delins_variants(
    hgvs_c: str,
    expected: str,
    ref: str,
    alt: str,
    offset: int,
) -> None:
    transcript = TranscriptModel(
        gene="EDIT",
        transcript="NM_EDIT.1",
        chrom="chr1",
        strand="+",
        exons=(TranscriptExon(number=1, cds_start=1, cds_end=6, sequence="ATGGAA"),),
    )

    response = TranscriptWindowBuilder().build(
        request=GeneViewerRequest(
            gene="EDIT",
            cdna=hgvs_c,
            transcript="NM_EDIT.1",
            allele_mode="variant",
            window=ViewerWindowRequest(kind="cds_range", cds_start=1, cds_end=6),
        ),
        transcript=transcript,
        variant=VariantProjection.from_hgvs_c(hgvs_c),
    )

    assert response.sequences.reference_window_sequence == "ATGGAA"
    assert response.sequences.display_window_sequence == expected
    assert response.sequences.applied_variant is not None
    assert response.sequences.applied_variant.ref == ref
    assert response.sequences.applied_variant.alt == alt
    assert response.sequences.applied_variant.sequence_offset == offset


def test_window_builder_variant_mode_models_stop_gained_product_truncation() -> None:
    transcript = TranscriptModel(
        gene="STOP",
        transcript="NM_STOP.1",
        chrom="chr1",
        strand="+",
        exons=(
            TranscriptExon(number=1, cds_start=1, cds_end=6, sequence="ATGGAA"),
            TranscriptExon(number=2, cds_start=7, cds_end=12, sequence="TTTTAA"),
        ),
        cds_length=12,
        protein_length=4,
    )
    variant = VariantProjection(
        hgvs_c="c.4G>T",
        cds_pos=4,
        ref="G",
        alt="T",
        hgvs_p="p.Glu2Ter",
        codon_number=2,
        codon_offset=0,
        aa_ref="E",
        aa_alt="*",
    )

    response = TranscriptWindowBuilder().build(
        request=GeneViewerRequest(
            gene="STOP",
            cdna="c.4G>T",
            transcript="NM_STOP.1",
            allele_mode="variant",
            window=ViewerWindowRequest(kind="cds_range", cds_start=1, cds_end=12),
        ),
        transcript=transcript,
        variant=variant,
    )

    product = response.tracks.protein_product
    assert product is not None
    assert product.consequence == "stop_gained"
    assert product.truncates_protein is True
    assert product.stop_codon == 2
    assert product.effective_protein_length == 1
    assert product.lost_aa_count == 3
    assert [(item.exon_number, item.state) for item in product.exon_effects] == [
        (1, "contains_variant"),
        (2, "downstream_truncated"),
    ]


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
