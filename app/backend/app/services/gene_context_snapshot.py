from __future__ import annotations

from urllib.parse import urlencode

from app.core.config import Settings
from app.schemas.gene_viewer import (
    GeneViewerRequest,
    GeneViewerResponse,
    ViewerProvenanceSource,
    ViewerWindowRequest,
)
from app.schemas.run import (
    GeneContextRenderHints,
    GeneContextSnapshot,
    GeneContextTranscriptExon,
    GeneContextTranscriptIntron,
    GeneContextVariantProjection,
    GeneContextWorkbenchLink,
    SourceProvenance,
)
from app.services.gene_viewer import (
    GeneViewerError,
    GeneViewerFixtureProvider,
    SourceBackedGeneViewerProvider,
    SourceBackedViewerBundle,
    SourceTranscriptModel,
)
from app.services.report_provenance import provenance_for_source
from app.services.sequence_context import normalize_sequence_query, unsupported_input_warning

RPE65_FIXTURE_EXONS: tuple[tuple[int, int, int, int], ...] = (
    (1, 1, 24, 113),
    (2, 25, 88, 64),
    (3, 89, 231, 143),
    (4, 232, 324, 93),
    (5, 325, 432, 108),
    (6, 433, 533, 101),
    (7, 534, 660, 127),
    (8, 661, 770, 110),
    (9, 771, 884, 114),
    (10, 885, 988, 104),
    (11, 989, 1130, 142),
    (12, 1131, 1276, 146),
    (13, 1277, 1452, 176),
    (14, 1453, 1602, 1366),
)
RPE65_FIXTURE_INTRONS: tuple[tuple[int, int], ...] = (
    (1, 1812),
    (2, 661),
    (3, 1240),
    (4, 982),
    (5, 753),
    (6, 1504),
    (7, 921),
    (8, 1082),
    (9, 787),
    (10, 1342),
    (11, 1155),
    (12, 984),
    (13, 823),
)


class GeneContextSnapshotService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        fixture_provider: GeneViewerFixtureProvider | None = None,
        source_provider: SourceBackedGeneViewerProvider | None = None,
    ) -> None:
        self.settings = settings
        self.fixture_provider = fixture_provider or GeneViewerFixtureProvider()
        self.source_provider = source_provider or SourceBackedGeneViewerProvider(settings=settings)
        self._explicit_source_provider = source_provider is not None

    def build(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str | None = None,
        species: str = "human",
    ) -> GeneContextSnapshot:
        query = normalize_sequence_query(gene, cdna, transcript)
        normalized_species = species.strip().lower() or "human"
        if normalized_species != "human":
            return _unavailable_snapshot(
                gene=query.gene,
                cdna=query.hgvs,
                transcript=query.resolver_transcript,
                warnings=[unsupported_input_warning("species")],
            )
        if query.kind != "cdna":
            return _unavailable_snapshot(
                gene=query.gene,
                cdna=query.hgvs,
                transcript=query.resolver_transcript,
                warnings=[unsupported_input_warning(query.kind)],
            )

        payload = GeneViewerRequest(
            gene=query.gene,
            cdna=query.hgvs,
            transcript=query.resolver_transcript or query.transcript,
            species=normalized_species,
            genome_build="GRCh38",
            allele_mode="reference",
            window=ViewerWindowRequest(
                kind="around_variant",
                cds_flank_bp=120,
                intron_flank_bp=30,
            ),
        )
        if self._use_source_backed_path:
            try:
                bundle = self.source_provider.viewer_bundle(payload)
            except GeneViewerError as exc:
                return _unavailable_snapshot(
                    gene=query.gene,
                    cdna=query.hgvs,
                    transcript=query.resolver_transcript,
                    warnings=[exc.code],
                )
            return _snapshot_from_source_bundle(bundle, source_status="live")

        try:
            if query.gene == "RPE65" and query.hgvs == "c.260A>G":
                response = self.fixture_provider.viewer(payload)
                return _snapshot_from_rpe65_fixture(response)
            bundle = self.fixture_provider.viewer_bundle(payload)
        except GeneViewerError as exc:
            return _unavailable_snapshot(
                gene=query.gene,
                cdna=query.hgvs,
                transcript=query.resolver_transcript,
                warnings=[exc.code, "gene_context_snapshot_fixture_unavailable"],
            )
        return _snapshot_from_source_bundle(bundle, source_status="fixture")

    @property
    def _use_source_backed_path(self) -> bool:
        return self._explicit_source_provider or bool(
            self.settings is not None and self.settings.use_real_apis
        )


def _snapshot_from_source_bundle(
    bundle: SourceBackedViewerBundle,
    *,
    source_status: str,
) -> GeneContextSnapshot:
    response = bundle.response
    exons, introns = _rows_from_source_transcript(bundle.transcript_source)
    variant = _variant_projection_from_response(response, exons=exons, introns=introns)
    status_warning = (
        "gene_context_snapshot_source_backed"
        if source_status == "live"
        else "gene_context_snapshot_fixture"
    )
    warnings = _dedupe([*response.provenance.warnings, status_warning])
    return GeneContextSnapshot(
        source_status=source_status,
        gene=response.identity.gene,
        transcript=response.identity.resolved_transcript,
        genome_build=response.identity.genome_build,
        chromosome=response.locus.chrom,
        strand=response.locus.strand,
        ensembl_gene_id=response.identity.ensembl_gene_id,
        gene_start=response.locus.gene_start,
        gene_end=response.locus.gene_end,
        gene_length=response.summary.gene_length,
        cds_length=response.summary.cds_length,
        protein_length=response.summary.protein_length,
        exons=exons,
        introns=introns,
        variant=variant,
        zoom_window=response.window,
        zoom_segments=response.segments,
        zoom_sequences=response.sequences,
        protein_domain_track=response.tracks.protein_features.domain_track,
        render_hints=_render_hints(exons=exons, introns=introns, zoom_flank_bp=120),
        workbench_link=_workbench_link(
            gene=response.identity.gene,
            cdna=response.queried_variant.hgvs_c,
            transcript=response.identity.resolved_transcript,
        ),
        provenance=_provenance_from_viewer_sources(
            response.provenance.sources,
            status=source_status,
        ),
        warnings=warnings,
    )


def _snapshot_from_rpe65_fixture(response: GeneViewerResponse) -> GeneContextSnapshot:
    exons, introns = _rows_from_fixture()
    variant = _variant_projection_from_response(response, exons=exons, introns=introns)
    warnings = _dedupe(
        [
            *response.provenance.warnings,
            "gene_context_snapshot_fixture",
            "transcript_model_from_rpe65_fixture_scaffold",
        ]
    )
    return GeneContextSnapshot(
        source_status="fixture",
        gene=response.identity.gene,
        transcript=response.identity.resolved_transcript,
        genome_build=response.identity.genome_build,
        chromosome=response.locus.chrom,
        strand=response.locus.strand,
        ensembl_gene_id=response.identity.ensembl_gene_id,
        gene_start=response.locus.gene_start,
        gene_end=response.locus.gene_end,
        gene_length=response.summary.gene_length,
        cds_length=response.summary.cds_length,
        protein_length=response.summary.protein_length,
        exons=exons,
        introns=introns,
        variant=variant,
        zoom_window=response.window,
        zoom_segments=response.segments,
        zoom_sequences=response.sequences,
        protein_domain_track=response.tracks.protein_features.domain_track,
        render_hints=_render_hints(exons=exons, introns=introns, zoom_flank_bp=120),
        workbench_link=_workbench_link(
            gene=response.identity.gene,
            cdna=response.queried_variant.hgvs_c,
            transcript=response.identity.resolved_transcript,
        ),
        provenance=[
            provenance_for_source(
                "workbench_rpe65_fixture",
                status="fixture",
                query={
                    "gene": response.identity.gene,
                    "cdna": response.queried_variant.hgvs_c,
                    "transcript": response.identity.resolved_transcript,
                },
                version="RPE65_V2",
            )
        ],
        warnings=warnings,
    )


def _unavailable_snapshot(
    *,
    gene: str,
    cdna: str,
    transcript: str | None,
    warnings: list[str],
) -> GeneContextSnapshot:
    return GeneContextSnapshot(
        source_status="missing",
        gene=gene,
        transcript=transcript,
        variant=GeneContextVariantProjection(
            hgvs_c=cdna,
            membership="unknown",
            warnings=list(warnings),
        ),
        workbench_link=_workbench_link(gene=gene, cdna=cdna, transcript=transcript),
        warnings=_dedupe(["gene_context_snapshot_unavailable", *warnings]),
    )


def _rows_from_source_transcript(
    transcript: SourceTranscriptModel,
) -> tuple[list[GeneContextTranscriptExon], list[GeneContextTranscriptIntron]]:
    introns_by_number = {intron.number: intron for intron in transcript.introns}
    exons: list[GeneContextTranscriptExon] = []
    introns: list[GeneContextTranscriptIntron] = []
    cursor = 1
    for exon in sorted(transcript.exons, key=lambda item: item.number):
        genomic_length = abs(exon.genomic_end - exon.genomic_start) + 1
        transcript_start = cursor
        transcript_end = cursor + genomic_length - 1
        exons.append(
            GeneContextTranscriptExon(
                number=exon.number,
                cds_start=exon.cds_start,
                cds_end=exon.cds_end,
                genomic_start=exon.genomic_start,
                genomic_end=exon.genomic_end,
                genomic_length=genomic_length,
                transcript_start=transcript_start,
                transcript_end=transcript_end,
            )
        )
        cursor = transcript_end + 1
        intron = introns_by_number.get(exon.number)
        if intron is None:
            continue
        length_bp = abs(intron.genomic_end - intron.genomic_start) + 1
        transcript_start = cursor
        transcript_end = cursor + length_bp - 1
        introns.append(
            GeneContextTranscriptIntron(
                number=intron.number,
                genomic_start=intron.genomic_start,
                genomic_end=intron.genomic_end,
                length_bp=length_bp,
                transcript_start=transcript_start,
                transcript_end=transcript_end,
            )
        )
        cursor = transcript_end + 1
    return exons, introns


def _rows_from_fixture() -> (
    tuple[list[GeneContextTranscriptExon], list[GeneContextTranscriptIntron]]
):
    intron_lengths = dict(RPE65_FIXTURE_INTRONS)
    exons: list[GeneContextTranscriptExon] = []
    introns: list[GeneContextTranscriptIntron] = []
    cursor = 1
    for number, cds_start, cds_end, genomic_length in RPE65_FIXTURE_EXONS:
        transcript_start = cursor
        transcript_end = cursor + genomic_length - 1
        exons.append(
            GeneContextTranscriptExon(
                number=number,
                cds_start=cds_start,
                cds_end=cds_end,
                genomic_length=genomic_length,
                transcript_start=transcript_start,
                transcript_end=transcript_end,
            )
        )
        cursor = transcript_end + 1
        length_bp = intron_lengths.get(number)
        if length_bp is None:
            continue
        transcript_start = cursor
        transcript_end = cursor + length_bp - 1
        introns.append(
            GeneContextTranscriptIntron(
                number=number,
                length_bp=length_bp,
                transcript_start=transcript_start,
                transcript_end=transcript_end,
            )
        )
        cursor = transcript_end + 1
    return exons, introns


def _variant_projection_from_response(
    response: GeneViewerResponse,
    *,
    exons: list[GeneContextTranscriptExon],
    introns: list[GeneContextTranscriptIntron],
) -> GeneContextVariantProjection:
    queried = response.queried_variant
    exon = next(
        (
            item
            for item in exons
            if item.cds_start is not None
            and item.cds_end is not None
            and item.cds_start <= queried.cds_pos <= item.cds_end
        ),
        None,
    )
    transcript_offset = None
    membership = "unknown"
    if exon is not None:
        membership = "exon"
        if exon.transcript_start is not None and exon.cds_start is not None:
            transcript_offset = exon.transcript_start + (queried.cds_pos - exon.cds_start)
    elif introns:
        membership = "outside_transcript"
    return GeneContextVariantProjection(
        hgvs_c=queried.hgvs_c,
        hgvs_p=queried.hgvs_p,
        cds_pos=queried.cds_pos,
        genomic_hg38=queried.genomic_hg38,
        ref=queried.ref,
        alt=queried.alt,
        exon_number=exon.number if exon is not None else None,
        membership=membership,
        transcript_offset=transcript_offset,
        codon_number=queried.codon_number,
        codon_offset=queried.codon_offset,
        aa_ref=queried.aa_ref,
        aa_alt=queried.aa_alt,
    )


def _render_hints(
    *,
    exons: list[GeneContextTranscriptExon],
    introns: list[GeneContextTranscriptIntron],
    zoom_flank_bp: int,
) -> GeneContextRenderHints:
    span = sum((item.genomic_length or 0) for item in exons) + sum(
        (item.length_bp or 0) for item in introns
    )
    large_gene = span > 5000 or len(exons) > 10
    return GeneContextRenderHints(
        overview_mode="compressed_introns" if introns else "linear",
        min_exon_width_px=8,
        max_intron_width_px=72 if large_gene else 120,
        zoom_flank_bp=zoom_flank_bp,
        large_gene_compression_applied=large_gene,
        warnings=["compressed_intron_rendering"] if large_gene else [],
    )


def _workbench_link(
    *,
    gene: str,
    cdna: str,
    transcript: str | None,
) -> GeneContextWorkbenchLink:
    query = {"gene": gene, "cdna": cdna}
    if transcript:
        query["transcript"] = transcript
    return GeneContextWorkbenchLink(
        url=f"/workbench?{urlencode(query)}",
        gene=gene,
        cdna=cdna,
        transcript=transcript,
    )


def _provenance_from_viewer_sources(
    sources: list[ViewerProvenanceSource],
    *,
    status: str,
) -> list[SourceProvenance]:
    return [
        provenance_for_source(
            source.name,
            status=status,
            query={"identifier": source.identifier or ""},
            source_url=source.url,
            version=source.version,
        )
        for source in sources
    ]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
