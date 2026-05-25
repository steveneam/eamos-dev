from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

from fastapi import status
import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.gene_viewer import (
    AppliedVariant,
    ClinvarVariant,
    ExonVariantDensity,
    GeneViewerRequest,
    GeneViewerResponse,
    ProteinDomain,
    ProteinFeatures,
    QueriedVariant,
    ViewerIdentity,
    ViewerLocus,
    ViewerProvenance,
    ViewerProvenanceSource,
    ViewerSegment,
    ViewerSequences,
    ViewerSummary,
    ViewerTracks,
    ViewerWindow,
    ViewerWindowRequest,
)
from app.services.sequence_context import (
    NormalizedVariantQuery,
    normalize_sequence_query,
    unsupported_input_warning,
)
from app.services.workbench_design import (
    WORKBENCH_PROVIDER_FAILED_PREFIX,
    WORKBENCH_PROVIDER_MALFORMED,
    WORKBENCH_PROVIDER_UNAVAILABLE,
)
from app.services.variant_applied_model import build_protein_product_effect

GENE_VIEWER_PROVIDER_UNAVAILABLE = WORKBENCH_PROVIDER_UNAVAILABLE
GENE_VIEWER_PROVIDER_MALFORMED = WORKBENCH_PROVIDER_MALFORMED
GENE_VIEWER_PROVIDER_FAILED_PREFIX = WORKBENCH_PROVIDER_FAILED_PREFIX
GENE_VIEWER_SERVICE_UNAVAILABLE = "workbench_viewer_service_unavailable"
GENE_VIEWER_LIVE_UNAVAILABLE = "workbench_viewer_live_unavailable"
GENE_VIEWER_REFERENCE_MISMATCH = unsupported_input_warning("reference_mismatch")
GENE_VIEWER_UNSUPPORTED_VARIANT = unsupported_input_warning("variant_type")
HTTP_UNPROCESSABLE_ENTITY = 422
AA3_TO_AA1 = {
    "Ala": "A",
    "Arg": "R",
    "Asn": "N",
    "Asp": "D",
    "Cys": "C",
    "Gln": "Q",
    "Glu": "E",
    "Gly": "G",
    "His": "H",
    "Ile": "I",
    "Leu": "L",
    "Lys": "K",
    "Met": "M",
    "Phe": "F",
    "Pro": "P",
    "Ser": "S",
    "Thr": "T",
    "Trp": "W",
    "Tyr": "Y",
    "Val": "V",
    "Ter": "*",
}


class GeneViewerError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
        warnings: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.warnings = warnings if warnings is not None else [code]

    def to_http_detail(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "warnings": self.warnings,
        }


class GeneViewerFixtureProvider:
    curated_fixture_name = "gene_viewer_transcript_models.json"

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self.fixtures_dir = fixtures_dir or (
            Path(__file__).resolve().parents[1] / "fixtures" / "workbench"
        )

    def viewer(self, payload: GeneViewerRequest) -> GeneViewerResponse:
        query = normalize_sequence_query(payload.gene, payload.cdna, payload.transcript)
        if query.gene != "RPE65" or query.hgvs != "c.260A>G":
            return self.viewer_bundle(payload, query=query).response
        try:
            response = GeneViewerResponse(**self._load("viewer_rpe65.json"))
        except ValidationError as exc:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message="Gene viewer fixture is malformed: viewer_rpe65.json",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc
        return _viewer_response_for_allele_mode(response, payload.allele_mode)

    def viewer_bundle(
        self,
        payload: GeneViewerRequest,
        *,
        query: NormalizedVariantQuery | None = None,
    ) -> SourceBackedViewerBundle:
        query = query or normalize_sequence_query(payload.gene, payload.cdna, payload.transcript)
        fixture = self._load(self.curated_fixture_name)
        return _curated_fixture_viewer_bundle(payload=payload, query=query, fixture=fixture)

    def _load(self, name: str) -> dict[str, Any]:
        try:
            return json.loads((self.fixtures_dir / name).read_text(encoding="utf-8"))
        except OSError as exc:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_UNAVAILABLE,
                message=f"Gene viewer fixture is unavailable: {name}",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        except ValueError as exc:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message=f"Gene viewer fixture is malformed: {name}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc


class GeneViewerService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        fixture_provider: GeneViewerFixtureProvider | None = None,
        live_provider: GeneViewerProvider | None = None,
    ) -> None:
        self.settings = settings
        self.fixture_provider = fixture_provider or GeneViewerFixtureProvider()
        self.live_provider = live_provider or SourceBackedGeneViewerProvider(settings=settings)

    def build_viewer(self, payload: GeneViewerRequest) -> GeneViewerResponse:
        if self.settings is not None and self.settings.use_real_apis:
            return self.live_provider.viewer(payload)
        return self.fixture_provider.viewer(payload)


class GeneViewerProvider(Protocol):
    def viewer(self, payload: GeneViewerRequest) -> GeneViewerResponse: ...


@dataclass(frozen=True)
class SourceTranscriptExon:
    number: int
    cds_start: int
    cds_end: int
    genomic_start: int
    genomic_end: int


@dataclass(frozen=True)
class SourceTranscriptIntron:
    number: int
    genomic_start: int
    genomic_end: int

    @property
    def total_len(self) -> int:
        return abs(self.genomic_end - self.genomic_start) + 1


@dataclass(frozen=True)
class SourceTranscriptModel:
    gene: str
    transcript: str
    chrom: str
    strand: str
    exons: tuple[SourceTranscriptExon, ...]
    introns: tuple[SourceTranscriptIntron, ...] = ()
    ensembl_gene_id: str | None = None
    transcript_aliases: tuple[str, ...] = ()
    species: str = "human"
    genome_build: str = "GRCh38"
    gene_start: int | None = None
    gene_end: int | None = None
    gene_length: int | None = None
    cds_length: int | None = None
    protein_length: int | None = None
    utr5_length: int | None = None
    utr3_length: int | None = None
    mrna_length: int | None = None
    translation_id: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceBackedViewerBundle:
    query: NormalizedVariantQuery
    variant: VariantProjection
    transcript_source: SourceTranscriptModel
    response: GeneViewerResponse


class GeneViewerSourceClient(Protocol):
    def resolve_variant(
        self,
        *,
        query: NormalizedVariantQuery,
        genome_build: str,
    ) -> VariantProjection: ...

    def fetch_transcript(
        self,
        *,
        query: NormalizedVariantQuery,
        variant: VariantProjection,
        genome_build: str,
    ) -> SourceTranscriptModel: ...

    def fetch_sequence(
        self,
        *,
        chrom: str,
        start: int,
        end: int,
        strand: str,
    ) -> str: ...

    def fetch_protein_features(
        self,
        *,
        transcript: SourceTranscriptModel,
    ) -> ProteinFeatures | None: ...

    def provenance_sources(
        self,
        *,
        query: NormalizedVariantQuery,
        transcript: SourceTranscriptModel,
        variant: VariantProjection,
    ) -> list[ViewerProvenanceSource]: ...


class HttpGeneViewerSourceClient:
    """HTTP source client boundary for future live viewer hydration.

    The provider below is fully exercised with mocked source records in tests.
    The default HTTP client already resolves VariantValidator and Ensembl
    sequence windows, while full transcript-structure parsing is intentionally
    kept behind this seam until GV-008 live smoke hardens source discrepancies.
    """

    def __init__(
        self,
        settings: Settings | None,
        *,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def resolve_variant(
        self,
        *,
        query: NormalizedVariantQuery,
        genome_build: str,
    ) -> VariantProjection:
        if self.settings is None:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_UNAVAILABLE,
                message="Gene viewer live source client is not configured.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        variant = VariantProjection.from_hgvs_c(query.hgvs)
        response = httpx.get(
            self._variant_validator_url(query=query, genome_build=genome_build),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        variant_payload = next(
            (
                value
                for key, value in payload.items()
                if key not in {"flag", "metadata"} and isinstance(value, dict)
            ),
            {},
        )
        loci = variant_payload.get("primary_assembly_loci", {})
        grch38 = loci.get("grch38", {}) if isinstance(loci, dict) else {}
        vcf = grch38.get("vcf") or {} if isinstance(grch38, dict) else {}
        chrom = str(vcf.get("chr") or "").removeprefix("chr")
        pos = str(vcf.get("pos") or "")
        ref = str(vcf.get("ref") or "").upper()
        alt = str(vcf.get("alt") or "").upper()
        if not chrom or not pos.isdigit() or not ref or not alt:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message="VariantValidator response did not include a GRCh38 VCF locus.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        hgvs_p = _protein_hgvs_from_variant_validator(variant_payload)
        codon_number, aa_ref, aa_alt = _protein_change_parts(hgvs_p)
        return VariantProjection(
            hgvs_c=variant.hgvs_c,
            cds_pos=variant.cds_pos,
            cds_end=variant.cds_end,
            variant_type=variant.variant_type,
            ref=variant.ref,
            alt=variant.alt,
            hgvs_p=hgvs_p,
            genomic_hg38=f"{chrom}-{pos}-{ref}-{alt}",
            codon_number=codon_number,
            codon_offset=(variant.cds_pos - 1) % 3,
            aa_ref=aa_ref,
            aa_alt=aa_alt,
        )

    def fetch_transcript(
        self,
        *,
        query: NormalizedVariantQuery,
        variant: VariantProjection,
        genome_build: str,
    ) -> SourceTranscriptModel:
        if self.settings is None:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_UNAVAILABLE,
                message="Gene viewer live source client is not configured.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        payload = self._get_json(self._ensembl_lookup_symbol_url(query=query))
        if not isinstance(payload, dict):
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message="Ensembl symbol lookup response was not an object.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        transcript_payload = self._select_transcript(payload=payload, query=query)
        return self._source_transcript_from_ensembl(
            gene_payload=payload,
            transcript_payload=transcript_payload,
            query=query,
            genome_build=genome_build,
        )

    def fetch_sequence(
        self,
        *,
        chrom: str,
        start: int,
        end: int,
        strand: str,
    ) -> str:
        if self.settings is None:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_UNAVAILABLE,
                message="Gene viewer live source client is not configured.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        strand_value = "-1" if strand == "-" else "1"
        region = f"{chrom.removeprefix('chr')}:{start}..{end}:{strand_value}"
        url = f"{self.settings.vep_base_url}/sequence/region/human/{region}"
        response = httpx.get(
            url,
            headers={"Content-Type": "text/plain", "Accept": "text/plain"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return _clean_dna(response.text)

    def fetch_protein_features(
        self,
        *,
        transcript: SourceTranscriptModel,
    ) -> ProteinFeatures | None:
        if self.settings is None or not transcript.translation_id:
            return None
        payload = self._get_json(
            self._ensembl_protein_features_url(translation_id=transcript.translation_id)
        )
        features = (
            _as_list(payload.get("value")) if isinstance(payload, dict) else _as_list(payload)
        )
        domains: list[ProteinDomain] = []
        seen: set[tuple[int, int, str]] = set()
        for feature in features:
            if not isinstance(feature, dict):
                continue
            feature_type = str(feature.get("type") or "")
            if feature_type not in {"CDD", "PANTHER", "Pfam", "SMART", "Superfamily"}:
                continue
            aa_start = _int_or_none(feature.get("start"))
            aa_end = _int_or_none(feature.get("end"))
            label = str(feature.get("description") or feature.get("id") or feature_type).strip()
            if aa_start is None or aa_end is None or not label:
                continue
            key = (min(aa_start, aa_end), max(aa_start, aa_end), label)
            if key in seen:
                continue
            seen.add(key)
            domains.append(
                ProteinDomain(
                    aa_start=key[0],
                    aa_end=key[1],
                    label=label,
                    short_label=label,
                )
            )
        if not domains:
            return None
        domains.sort(key=lambda domain: (domain.aa_start, domain.aa_end, domain.label))
        return ProteinFeatures(domains=domains)

    def provenance_sources(
        self,
        *,
        query: NormalizedVariantQuery,
        transcript: SourceTranscriptModel,
        variant: VariantProjection,
    ) -> list[ViewerProvenanceSource]:
        return [
            ViewerProvenanceSource(
                name="variant_validator",
                identifier=query.resolver_transcript_hgvs,
                url=(
                    self._variant_validator_url(query=query, genome_build=transcript.genome_build)
                    if self.settings is not None
                    else None
                ),
            ),
            ViewerProvenanceSource(
                name="ensembl_rest",
                identifier=transcript.transcript,
                url=self.settings.vep_base_url if self.settings is not None else None,
            ),
        ]

    def _variant_validator_url(
        self,
        *,
        query: NormalizedVariantQuery,
        genome_build: str,
    ) -> str:
        if self.settings is None:
            return ""
        encoded_query = quote(query.resolver_transcript_hgvs, safe="")
        return (
            f"{self.settings.variant_validator_base_url}"
            f"/VariantValidator/variantvalidator/{genome_build}/{encoded_query}/all"
        )

    def _ensembl_lookup_symbol_url(self, *, query: NormalizedVariantQuery) -> str:
        if self.settings is None:
            return ""
        encoded_gene = quote(query.gene, safe="")
        return (
            f"{self.settings.vep_base_url}"
            f"/lookup/symbol/homo_sapiens/{encoded_gene}?expand=1;mane=1;utr=1"
        )

    def _ensembl_protein_features_url(self, *, translation_id: str) -> str:
        if self.settings is None:
            return ""
        encoded_translation = quote(translation_id, safe="")
        return (
            f"{self.settings.vep_base_url}"
            f"/overlap/translation/{encoded_translation}?feature=protein_feature"
        )

    def _get_json(self, url: str) -> Any:
        response = httpx.get(
            url,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _select_transcript(
        self,
        *,
        payload: dict[str, Any],
        query: NormalizedVariantQuery,
    ) -> dict[str, Any]:
        transcripts = [
            transcript
            for transcript in _as_list(payload.get("Transcript"))
            if isinstance(transcript, dict)
        ]
        if not transcripts:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message="Ensembl symbol lookup did not include transcripts.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        requested = query.resolver_transcript
        if requested:
            for transcript in transcripts:
                if self._transcript_matches(transcript=transcript, requested=requested):
                    return transcript
            raise GeneViewerError(
                code=unsupported_input_warning("transcript"),
                message=(
                    "Requested transcript was not present in the Ensembl symbol "
                    f"lookup for {query.gene}."
                ),
                status_code=HTTP_UNPROCESSABLE_ENTITY,
            )

        canonical = _versionless(str(payload.get("canonical_transcript") or ""))
        for transcript in transcripts:
            if canonical and _versionless(str(transcript.get("id") or "")) == canonical:
                return transcript
        for transcript in transcripts:
            if (
                transcript.get("is_canonical") == 1
                and transcript.get("biotype") == "protein_coding"
            ):
                return transcript
        _raise_unsupported(
            "ambiguous_transcript",
            f"Could not choose a canonical protein-coding transcript for {query.gene}.",
        )

    def _transcript_matches(
        self,
        *,
        transcript: dict[str, Any],
        requested: str,
    ) -> bool:
        transcript_id = str(transcript.get("id") or "")
        transcript_version = transcript.get("version")
        transcript_versioned = (
            f"{transcript_id}.{transcript_version}" if transcript_id and transcript_version else ""
        )
        requested_versionless = _versionless(requested)
        if requested.startswith("ENST") and requested_versionless == _versionless(transcript_id):
            return True
        if transcript_versioned and requested == transcript_versioned:
            return True
        for mane in _as_list(transcript.get("MANE")):
            if not isinstance(mane, dict):
                continue
            refseq_match = str(mane.get("refseq_match") or "")
            if requested == refseq_match or requested_versionless == _versionless(refseq_match):
                return True
        return False

    def _source_transcript_from_ensembl(
        self,
        *,
        gene_payload: dict[str, Any],
        transcript_payload: dict[str, Any],
        query: NormalizedVariantQuery,
        genome_build: str,
    ) -> SourceTranscriptModel:
        translation = transcript_payload.get("Translation")
        if not isinstance(translation, dict):
            _raise_unsupported(
                "transcript",
                "Gene viewer live mode requires a protein-coding transcript.",
            )

        strand = _strand_from_ensembl(transcript_payload.get("strand"))
        if strand == "unknown":
            strand = _strand_from_ensembl(gene_payload.get("strand"))
        translation_start = _required_int(translation.get("start"), "translation.start")
        translation_end = _required_int(translation.get("end"), "translation.end")
        coding_min = min(translation_start, translation_end)
        coding_max = max(translation_start, translation_end)

        raw_exons = [
            exon for exon in _as_list(transcript_payload.get("Exon")) if isinstance(exon, dict)
        ]
        if not raw_exons:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message="Ensembl transcript did not include exon records.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        ordered_exons = sorted(
            raw_exons,
            key=lambda exon: _required_int(exon.get("start"), "exon.start"),
            reverse=strand == "-",
        )

        coding_exons: list[SourceTranscriptExon] = []
        coding_records: list[tuple[int, int, int]] = []
        next_cds = 1
        for exon_number, exon in enumerate(ordered_exons, start=1):
            exon_start = _required_int(exon.get("start"), "exon.start")
            exon_end = _required_int(exon.get("end"), "exon.end")
            exon_low = min(exon_start, exon_end)
            exon_high = max(exon_start, exon_end)
            coding_start = max(exon_low, coding_min)
            coding_end = min(exon_high, coding_max)
            if coding_start > coding_end:
                continue
            coding_len = coding_end - coding_start + 1
            cds_start = next_cds
            cds_end = next_cds + coding_len - 1
            next_cds = cds_end + 1
            coding_exons.append(
                SourceTranscriptExon(
                    number=exon_number,
                    cds_start=cds_start,
                    cds_end=cds_end,
                    genomic_start=coding_start,
                    genomic_end=coding_end,
                )
            )
            coding_records.append((exon_number, exon_low, exon_high))

        if not coding_exons:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message="Ensembl transcript did not include coding exon sequence.",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        introns: list[SourceTranscriptIntron] = []
        for (exon_number, previous_low, previous_high), (_, next_low, next_high) in zip(
            coding_records, coding_records[1:]
        ):
            intron_start = min(previous_high, next_high) + 1
            intron_end = max(previous_low, next_low) - 1
            if intron_start <= intron_end:
                introns.append(
                    SourceTranscriptIntron(
                        number=exon_number,
                        genomic_start=intron_start,
                        genomic_end=intron_end,
                    )
                )

        gene_start = _int_or_none(gene_payload.get("start"))
        gene_end = _int_or_none(gene_payload.get("end"))
        gene_length = (
            abs(gene_end - gene_start) + 1
            if gene_start is not None and gene_end is not None
            else None
        )
        transcript_id = str(transcript_payload.get("id") or "")
        translation_id = str(translation.get("id") or "") or None
        return SourceTranscriptModel(
            gene=query.gene,
            transcript=query.resolver_transcript or _versioned_id(transcript_payload),
            chrom=str(
                transcript_payload.get("seq_region_name") or gene_payload.get("seq_region_name")
            ),
            strand=strand,
            exons=tuple(coding_exons),
            introns=tuple(introns),
            ensembl_gene_id=str(gene_payload.get("id") or "") or None,
            transcript_aliases=tuple(
                _transcript_aliases(
                    transcript=transcript_payload,
                    requested=query.resolver_transcript,
                )
            ),
            species="human",
            genome_build=genome_build,
            gene_start=gene_start,
            gene_end=gene_end,
            gene_length=gene_length,
            cds_length=next_cds - 1,
            protein_length=_int_or_none(translation.get("length")),
            utr5_length=_utr_length(transcript_payload, "five_prime_utr"),
            utr3_length=_utr_length(transcript_payload, "three_prime_utr"),
            mrna_length=_int_or_none(transcript_payload.get("length")),
            translation_id=translation_id,
            warnings=(
                "live_source_transcript_from_ensembl",
                "clinvar_track_not_live_hydrated",
                "protein_features_from_ensembl_overlap",
                f"ensembl_transcript:{transcript_id}",
            ),
        )


class SourceBackedGeneViewerProvider:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        source_client: GeneViewerSourceClient | None = None,
        builder: TranscriptWindowBuilder | None = None,
    ) -> None:
        self.settings = settings
        self.source_client = source_client or HttpGeneViewerSourceClient(settings)
        self.builder = builder or TranscriptWindowBuilder()

    def viewer(self, payload: GeneViewerRequest) -> GeneViewerResponse:
        return self.viewer_bundle(payload).response

    def viewer_bundle(self, payload: GeneViewerRequest) -> SourceBackedViewerBundle:
        query = normalize_sequence_query(payload.gene, payload.cdna, payload.transcript)
        self._validate_query(payload=payload, query=query)
        try:
            variant_seed = VariantProjection.from_hgvs_c(query.hgvs)
            if query.resolver_transcript:
                variant = self.source_client.resolve_variant(
                    query=query,
                    genome_build=payload.genome_build,
                )
                transcript_source = self.source_client.fetch_transcript(
                    query=query,
                    variant=variant,
                    genome_build=payload.genome_build,
                )
            else:
                transcript_source = self.source_client.fetch_transcript(
                    query=query,
                    variant=variant_seed,
                    genome_build=payload.genome_build,
                )
                query = _query_with_source_transcript(query, transcript_source)
                variant = self.source_client.resolve_variant(
                    query=query,
                    genome_build=payload.genome_build,
                )
            transcript = self._transcript_model(
                source=transcript_source,
                window=payload.window,
                variant=variant,
                intron_flank_bp=payload.window.intron_flank_bp,
            )
            response = self.builder.build(
                request=payload,
                transcript=transcript,
                variant=variant,
            )
            protein_features = self.source_client.fetch_protein_features(
                transcript=transcript_source
            )
        except GeneViewerError:
            raise
        except Exception as exc:
            raise GeneViewerError(
                code=f"{GENE_VIEWER_PROVIDER_FAILED_PREFIX}:{type(exc).__name__}",
                message="Gene viewer source provider failed while building the viewer.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        if protein_features is not None:
            response.tracks.protein_features = protein_features
        response.tracks.protein_product = build_protein_product_effect(
            variant=variant,
            allele_mode=payload.allele_mode,
            reference_protein_length=transcript_source.protein_length,
            exons=transcript_source.exons,
        )
        response.provenance = ViewerProvenance(
            sources=self.source_client.provenance_sources(
                query=query,
                transcript=transcript_source,
                variant=variant,
            ),
            warnings=list(transcript_source.warnings),
        )
        return SourceBackedViewerBundle(
            query=query,
            variant=variant,
            transcript_source=transcript_source,
            response=response,
        )

    def _validate_query(
        self,
        *,
        payload: GeneViewerRequest,
        query: NormalizedVariantQuery,
    ) -> None:
        if payload.species.strip().lower() != "human":
            _raise_unsupported("species", "Gene viewer currently supports human transcripts only.")
        if payload.genome_build not in {"GRCh38", "hg38"}:
            _raise_unsupported(
                "genome_build",
                "Gene viewer currently supports GRCh38/hg38 only.",
            )
        if query.kind != "cdna":
            _raise_unsupported(
                query.kind,
                "Gene viewer source-backed mode currently supports coding cDNA HGVS only.",
            )

    def _transcript_model(
        self,
        *,
        source: SourceTranscriptModel,
        window: ViewerWindowRequest,
        variant: VariantProjection,
        intron_flank_bp: int,
    ) -> TranscriptModel:
        display_start, display_end = _source_window_bounds(
            window=window,
            variant=variant,
            source=source,
        )
        source_exons = tuple(
            exon
            for exon in source.exons
            if exon.cds_end >= display_start and exon.cds_start <= display_end
        )
        if not source_exons:
            raise GeneViewerError(
                code=unsupported_input_warning("window"),
                message="Viewer window does not overlap the transcript CDS.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
            )

        exons: list[TranscriptExon] = []
        for exon in source_exons:
            sequence = self._sequence(
                chrom=source.chrom,
                start=exon.genomic_start,
                end=exon.genomic_end,
                strand=source.strand,
                expected_len=exon.cds_end - exon.cds_start + 1,
            )
            exons.append(
                TranscriptExon(
                    number=exon.number,
                    cds_start=exon.cds_start,
                    cds_end=exon.cds_end,
                    sequence=sequence,
                    genomic_start=exon.genomic_start,
                    genomic_end=exon.genomic_end,
                )
            )

        selected_exon_numbers = {exon.number for exon in source_exons}
        introns = tuple(
            self._intron_model(
                source=source,
                intron=intron,
                intron_flank_bp=intron_flank_bp,
            )
            for intron in source.introns
            if intron.number in selected_exon_numbers
            and (intron.number + 1) in selected_exon_numbers
        )
        return TranscriptModel(
            gene=source.gene,
            transcript=source.transcript,
            chrom=source.chrom,
            strand=source.strand,
            exons=tuple(exons),
            introns=introns,
            ensembl_gene_id=source.ensembl_gene_id,
            transcript_aliases=source.transcript_aliases,
            species=source.species,
            genome_build=source.genome_build,
            gene_start=source.gene_start,
            gene_end=source.gene_end,
            gene_length=source.gene_length,
            cds_length=source.cds_length,
            protein_length=source.protein_length,
            utr5_length=source.utr5_length,
            utr3_length=source.utr3_length,
            mrna_length=source.mrna_length,
            total_exons=len(source.exons),
        )

    def _intron_model(
        self,
        *,
        source: SourceTranscriptModel,
        intron: SourceTranscriptIntron,
        intron_flank_bp: int,
    ) -> TranscriptIntron:
        start = min(intron.genomic_start, intron.genomic_end)
        end = max(intron.genomic_start, intron.genomic_end)
        total_len = end - start + 1
        flank = max(0, intron_flank_bp)
        five_len = min(flank, total_len)
        three_len = min(flank, max(0, total_len - five_len))
        five_prime = ""
        three_prime = ""
        if five_len:
            if source.strand == "-":
                five_prime = self._sequence(
                    chrom=source.chrom,
                    start=end - five_len + 1,
                    end=end,
                    strand=source.strand,
                    expected_len=five_len,
                ).lower()
            else:
                five_prime = self._sequence(
                    chrom=source.chrom,
                    start=start,
                    end=start + five_len - 1,
                    strand=source.strand,
                    expected_len=five_len,
                ).lower()
        if three_len:
            if source.strand == "-":
                three_prime = self._sequence(
                    chrom=source.chrom,
                    start=start,
                    end=start + three_len - 1,
                    strand=source.strand,
                    expected_len=three_len,
                ).lower()
            else:
                three_prime = self._sequence(
                    chrom=source.chrom,
                    start=end - three_len + 1,
                    end=end,
                    strand=source.strand,
                    expected_len=three_len,
                ).lower()
        return TranscriptIntron(
            number=intron.number,
            total_len=total_len,
            five_prime_sequence=five_prime,
            three_prime_sequence=three_prime,
            genomic_start=intron.genomic_start,
            genomic_end=intron.genomic_end,
        )

    def _sequence(
        self,
        *,
        chrom: str,
        start: int,
        end: int,
        strand: str,
        expected_len: int,
    ) -> str:
        if start > end:
            start, end = end, start
        sequence = _clean_dna(
            self.source_client.fetch_sequence(
                chrom=chrom,
                start=start,
                end=end,
                strand=strand,
            )
        )
        if len(sequence) != expected_len:
            raise GeneViewerError(
                code=GENE_VIEWER_PROVIDER_MALFORMED,
                message=(
                    "Gene viewer source sequence length did not match the "
                    f"requested interval ({len(sequence)} != {expected_len})."
                ),
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        return sequence


def _query_with_source_transcript(
    query: NormalizedVariantQuery,
    source: SourceTranscriptModel,
) -> NormalizedVariantQuery:
    resolver_transcript = _source_resolver_transcript(source)
    return query.model_copy(
        update={
            "resolver_transcript": resolver_transcript,
            "resolver_transcript_hgvs": f"{resolver_transcript}:{query.hgvs}",
        }
    )


def _source_resolver_transcript(source: SourceTranscriptModel) -> str:
    candidates = [*source.transcript_aliases, source.transcript]
    for candidate in candidates:
        if candidate.startswith(("NM_", "NR_")):
            return candidate
    for candidate in candidates:
        if candidate.startswith("ENST"):
            return candidate
    if source.transcript:
        return source.transcript
    _raise_unsupported(
        "transcript",
        f"Could not choose a source-backed transcript for {source.gene}.",
    )


def _curated_fixture_viewer_bundle(
    *,
    payload: GeneViewerRequest,
    query: NormalizedVariantQuery,
    fixture: dict[str, Any],
) -> SourceBackedViewerBundle:
    record = _curated_fixture_record(fixture=fixture, query=query)
    if record is None:
        code = unsupported_input_warning("fixture")
        raise GeneViewerError(
            code=code,
            message=(
                "Offline gene viewer fixture is available for RPE65 c.260A>G "
                "and curated ClinVar-stack transcript-model cases."
            ),
            status_code=HTTP_UNPROCESSABLE_ENTITY,
            warnings=[code],
        )
    _validate_curated_fixture_window(payload=payload, record=record)
    variant = _variant_from_curated_fixture(record)
    source = _source_transcript_from_curated_fixture(record)
    response = TranscriptWindowBuilder().build(
        request=payload,
        transcript=_transcript_model_from_curated_fixture(record),
        variant=variant,
    )
    query = _query_with_source_transcript(query, source)
    response.provenance = ViewerProvenance(
        sources=_curated_fixture_provenance_sources(
            record=record,
            fixture_version=str(fixture.get("version") or ""),
        ),
        warnings=list(record.get("warnings") or []),
    )
    response.tracks.clinvar_variants = [
        ClinvarVariant(
            cds_pos=variant.cds_pos,
            hgvs_c=variant.hgvs_c,
            hgvs_p=variant.hgvs_p,
            classification=variant.classification,
            clinvar_id=str(record.get("accession") or record.get("clinvar_variation_id") or ""),
            queried=True,
        )
    ]
    response.tracks.protein_product = build_protein_product_effect(
        variant=variant,
        allele_mode=payload.allele_mode,
        reference_protein_length=source.protein_length,
        exons=source.exons,
    )
    exon_number = next(
        (exon.number for exon in source.exons if exon.cds_start <= variant.cds_pos <= exon.cds_end),
        None,
    )
    if exon_number is not None:
        response.tracks.exon_density = [
            ExonVariantDensity(exon_number=exon_number, variant_count=1)
        ]
    return SourceBackedViewerBundle(
        query=query,
        variant=variant,
        transcript_source=source,
        response=response,
    )


def _curated_fixture_record(
    *,
    fixture: dict[str, Any],
    query: NormalizedVariantQuery,
) -> dict[str, Any] | None:
    requested_transcript = _versionless(query.resolver_transcript or query.transcript or "")
    for record in fixture.get("records") or []:
        if not isinstance(record, dict):
            continue
        if str(record.get("gene") or "").upper() != query.gene:
            continue
        if str(record.get("cdna") or "") != query.hgvs:
            continue
        if not requested_transcript:
            return record
        aliases = [
            str(record.get("transcript") or ""),
            str(record.get("requested_transcript") or ""),
            *(str(alias) for alias in record.get("transcript_aliases") or []),
        ]
        if any(_versionless(alias) == requested_transcript for alias in aliases):
            return record
    return None


def _validate_curated_fixture_window(
    *,
    payload: GeneViewerRequest,
    record: dict[str, Any],
) -> None:
    default_window = record.get("default_window") or {
        "kind": "around_variant",
        "cds_flank_bp": 120,
        "intron_flank_bp": 30,
    }
    if (
        payload.window.kind == default_window.get("kind")
        and payload.window.cds_start is None
        and payload.window.cds_end is None
        and payload.window.cds_flank_bp == default_window.get("cds_flank_bp")
        and payload.window.intron_flank_bp == default_window.get("intron_flank_bp")
    ):
        return
    code = unsupported_input_warning("fixture_window")
    raise GeneViewerError(
        code=code,
        message=(
            "Curated non-RPE65 gene viewer fixtures support the default "
            "around-variant window only."
        ),
        status_code=HTTP_UNPROCESSABLE_ENTITY,
        warnings=[code],
    )


def _source_transcript_from_curated_fixture(record: dict[str, Any]) -> SourceTranscriptModel:
    return SourceTranscriptModel(
        gene=str(record["gene"]),
        transcript=str(record["transcript"]),
        chrom=str(record["chrom"]),
        strand=str(record.get("strand") or "unknown"),
        exons=tuple(
            SourceTranscriptExon(
                number=int(exon["number"]),
                cds_start=int(exon["cds_start"]),
                cds_end=int(exon["cds_end"]),
                genomic_start=int(exon["genomic_start"]),
                genomic_end=int(exon["genomic_end"]),
            )
            for exon in record.get("exons") or []
        ),
        introns=tuple(
            SourceTranscriptIntron(
                number=int(intron["number"]),
                genomic_start=int(intron["genomic_start"]),
                genomic_end=int(intron["genomic_end"]),
            )
            for intron in record.get("introns") or []
        ),
        ensembl_gene_id=_optional_fixture_text(record.get("ensembl_gene_id")),
        transcript_aliases=tuple(str(alias) for alias in record.get("transcript_aliases") or []),
        species=str(record.get("species") or "human"),
        genome_build=str(record.get("genome_build") or "GRCh38"),
        gene_start=_fixture_int_or_none(record.get("gene_start")),
        gene_end=_fixture_int_or_none(record.get("gene_end")),
        gene_length=_fixture_int_or_none(record.get("gene_length")),
        cds_length=_fixture_int_or_none(record.get("cds_length")),
        protein_length=_fixture_int_or_none(record.get("protein_length")),
        utr5_length=_fixture_int_or_none(record.get("utr5_length")),
        utr3_length=_fixture_int_or_none(record.get("utr3_length")),
        mrna_length=_fixture_int_or_none(record.get("mrna_length")),
        translation_id=_optional_fixture_text(record.get("translation_id")),
        warnings=tuple(str(warning) for warning in record.get("warnings") or []),
    )


def _transcript_model_from_curated_fixture(record: dict[str, Any]) -> TranscriptModel:
    return TranscriptModel(
        gene=str(record["gene"]),
        transcript=str(record["transcript"]),
        chrom=str(record["chrom"]),
        strand=str(record.get("strand") or "unknown"),
        exons=tuple(
            TranscriptExon(
                number=int(exon["number"]),
                cds_start=int(exon["cds_start"]),
                cds_end=int(exon["cds_end"]),
                sequence=str(exon.get("sequence") or _placeholder_sequence(exon)),
                genomic_start=int(exon["genomic_start"]),
                genomic_end=int(exon["genomic_end"]),
            )
            for exon in record.get("exons") or []
        ),
        introns=tuple(
            TranscriptIntron(
                number=int(intron["number"]),
                total_len=int(intron.get("total_len") or _fixture_intron_length(intron)),
                five_prime_sequence=str(intron.get("five_prime_sequence") or ""),
                three_prime_sequence=str(intron.get("three_prime_sequence") or ""),
                genomic_start=int(intron["genomic_start"]),
                genomic_end=int(intron["genomic_end"]),
            )
            for intron in record.get("introns") or []
        ),
        ensembl_gene_id=_optional_fixture_text(record.get("ensembl_gene_id")),
        transcript_aliases=tuple(str(alias) for alias in record.get("transcript_aliases") or []),
        species=str(record.get("species") or "human"),
        genome_build=str(record.get("genome_build") or "GRCh38"),
        gene_start=_fixture_int_or_none(record.get("gene_start")),
        gene_end=_fixture_int_or_none(record.get("gene_end")),
        gene_length=_fixture_int_or_none(record.get("gene_length")),
        total_exons=len(record.get("exons") or []),
        cds_length=_fixture_int_or_none(record.get("cds_length")),
        protein_length=_fixture_int_or_none(record.get("protein_length")),
        utr5_length=_fixture_int_or_none(record.get("utr5_length")),
        utr3_length=_fixture_int_or_none(record.get("utr3_length")),
        mrna_length=_fixture_int_or_none(record.get("mrna_length")),
    )


def _variant_from_curated_fixture(record: dict[str, Any]) -> VariantProjection:
    variant = record.get("variant") or {}
    return VariantProjection(
        hgvs_c=str(variant["hgvs_c"]),
        cds_pos=int(variant["cds_pos"]),
        ref=str(variant["ref"]),
        alt=str(variant["alt"]),
        hgvs_p=_optional_fixture_text(variant.get("hgvs_p")),
        genomic_hg38=_optional_fixture_text(variant.get("genomic_hg38")),
        codon_number=_fixture_int_or_none(variant.get("codon_number")),
        codon_offset=_fixture_int_or_none(variant.get("codon_offset")),
        aa_ref=_optional_fixture_text(variant.get("aa_ref")),
        aa_alt=_optional_fixture_text(variant.get("aa_alt")),
        classification=str(variant.get("classification") or "unknown"),
    )


def _curated_fixture_provenance_sources(
    *,
    record: dict[str, Any],
    fixture_version: str,
) -> list[ViewerProvenanceSource]:
    return [
        ViewerProvenanceSource(
            name="ensembl_rest_fixture",
            identifier=str(record.get("transcript") or ""),
            url="https://rest.ensembl.org",
            version=fixture_version or None,
        ),
        ViewerProvenanceSource(
            name="clinvar_gene_agnostic_stack",
            identifier=str(record.get("accession") or record.get("clinvar_variation_id") or ""),
            url=_optional_fixture_text(record.get("source_url")),
            version=fixture_version or None,
        ),
    ]


def _placeholder_sequence(exon: dict[str, Any]) -> str:
    return "N" * (int(exon["cds_end"]) - int(exon["cds_start"]) + 1)


def _fixture_intron_length(intron: dict[str, Any]) -> int:
    return abs(int(intron["genomic_end"]) - int(intron["genomic_start"])) + 1


def _fixture_int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_fixture_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


@dataclass(frozen=True)
class TranscriptExon:
    number: int
    cds_start: int
    cds_end: int
    sequence: str
    genomic_start: int | None = None
    genomic_end: int | None = None

    def sequence_for(self, cds_start: int, cds_end: int) -> str:
        start_offset = cds_start - self.cds_start
        end_offset = cds_end - self.cds_start + 1
        return self.sequence[start_offset:end_offset]


@dataclass(frozen=True)
class TranscriptIntron:
    number: int
    total_len: int
    five_prime_sequence: str = ""
    three_prime_sequence: str = ""
    genomic_start: int | None = None
    genomic_end: int | None = None

    @property
    def omitted_bp(self) -> int:
        return max(
            0, self.total_len - len(self.five_prime_sequence) - len(self.three_prime_sequence)
        )


@dataclass(frozen=True)
class TranscriptModel:
    gene: str
    transcript: str
    chrom: str
    strand: str
    exons: tuple[TranscriptExon, ...]
    introns: tuple[TranscriptIntron, ...] = ()
    ensembl_gene_id: str | None = None
    transcript_aliases: tuple[str, ...] = ()
    species: str = "human"
    genome_build: str = "GRCh38"
    gene_start: int | None = None
    gene_end: int | None = None
    gene_length: int | None = None
    total_exons: int | None = None
    cds_length: int | None = None
    protein_length: int | None = None
    utr5_length: int | None = None
    utr3_length: int | None = None
    mrna_length: int | None = None


@dataclass(frozen=True)
class VariantProjection:
    hgvs_c: str
    cds_pos: int
    ref: str
    alt: str
    cds_end: int | None = None
    variant_type: str = "substitution"
    hgvs_p: str | None = None
    genomic_hg38: str | None = None
    codon_number: int | None = None
    codon_offset: int | None = None
    aa_ref: str | None = None
    aa_alt: str | None = None
    classification: str = "unknown"

    @classmethod
    def from_hgvs_c(cls, hgvs_c: str) -> VariantProjection:
        substitution = re.fullmatch(
            r"c\.(?P<pos>\d+)(?P<ref>[ACGT]+)>(?P<alt>[ACGT]+)",
            hgvs_c,
            flags=re.IGNORECASE,
        )
        if substitution is not None:
            return cls(
                hgvs_c=hgvs_c,
                cds_pos=int(substitution.group("pos")),
                cds_end=int(substitution.group("pos")) + len(substitution.group("ref")) - 1,
                ref=substitution.group("ref").upper(),
                alt=substitution.group("alt").upper(),
                variant_type="substitution",
            )

        deletion = re.fullmatch(
            r"c\.(?P<start>\d+)(?:_(?P<end>\d+))?del(?P<ref>[ACGT]+)?",
            hgvs_c,
            flags=re.IGNORECASE,
        )
        if deletion is not None:
            start = int(deletion.group("start"))
            end = int(deletion.group("end") or start)
            return cls(
                hgvs_c=hgvs_c,
                cds_pos=start,
                cds_end=end,
                ref=(deletion.group("ref") or "").upper(),
                alt="",
                variant_type="deletion",
            )

        duplication = re.fullmatch(
            r"c\.(?P<start>\d+)(?:_(?P<end>\d+))?dup(?P<alt>[ACGT]+)?",
            hgvs_c,
            flags=re.IGNORECASE,
        )
        if duplication is not None:
            start = int(duplication.group("start"))
            end = int(duplication.group("end") or start)
            return cls(
                hgvs_c=hgvs_c,
                cds_pos=start,
                cds_end=end,
                ref="",
                alt=(duplication.group("alt") or "").upper(),
                variant_type="duplication",
            )

        insertion = re.fullmatch(
            r"c\.(?P<left>\d+)_(?P<right>\d+)ins(?P<alt>[ACGT]+)",
            hgvs_c,
            flags=re.IGNORECASE,
        )
        if insertion is not None:
            return cls(
                hgvs_c=hgvs_c,
                cds_pos=int(insertion.group("left")),
                cds_end=int(insertion.group("right")),
                ref="",
                alt=insertion.group("alt").upper(),
                variant_type="insertion",
            )

        delins = re.fullmatch(
            r"c\.(?P<start>\d+)(?:_(?P<end>\d+))?delins(?P<alt>[ACGT]+)",
            hgvs_c,
            flags=re.IGNORECASE,
        )
        if delins is not None:
            start = int(delins.group("start"))
            end = int(delins.group("end") or start)
            return cls(
                hgvs_c=hgvs_c,
                cds_pos=start,
                cds_end=end,
                ref="",
                alt=delins.group("alt").upper(),
                variant_type="delins",
            )

        raise GeneViewerError(
            code=GENE_VIEWER_UNSUPPORTED_VARIANT,
            message="Only simple coding substitution, deletion, duplication, insertion, and delins viewer overlays are supported.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
        )


@dataclass(frozen=True)
class VariantDisplayOperation:
    segment_id: str
    sequence_offset: int
    ref: str
    alt: str
    replace_length: int


class TranscriptWindowBuilder:
    def build(
        self,
        *,
        request: GeneViewerRequest,
        transcript: TranscriptModel,
        variant: VariantProjection,
    ) -> GeneViewerResponse:
        display_start, display_end = self._window_bounds(
            window=request.window,
            variant=variant,
            transcript=transcript,
        )
        segments = self._segments(
            transcript=transcript,
            display_start=display_start,
            display_end=display_end,
        )
        reference_sequence = "".join(_segment_display_sequence(segment) for segment in segments)
        applied_variant, display_sequence = self._apply_variant(
            allele_mode=request.allele_mode,
            reference_sequence=reference_sequence,
            segments=segments,
            variant=variant,
        )

        return GeneViewerResponse(
            identity=ViewerIdentity(
                gene=transcript.gene,
                ensembl_gene_id=transcript.ensembl_gene_id,
                requested_transcript=request.transcript,
                resolved_transcript=transcript.transcript,
                transcript_aliases=list(transcript.transcript_aliases),
                species=transcript.species,
                genome_build=transcript.genome_build,
            ),
            locus=ViewerLocus(
                chrom=transcript.chrom,
                gene_start=transcript.gene_start,
                gene_end=transcript.gene_end,
                strand=_schema_strand(transcript.strand),
            ),
            summary=ViewerSummary(
                gene_length=transcript.gene_length,
                total_exons=transcript.total_exons or len(transcript.exons),
                cds_length=transcript.cds_length,
                protein_length=transcript.protein_length,
                utr5_length=transcript.utr5_length,
                utr3_length=transcript.utr3_length,
                mrna_length=transcript.mrna_length,
            ),
            window=ViewerWindow(
                kind=request.window.kind,
                cds_start=request.window.cds_start,
                cds_end=request.window.cds_end,
                cds_flank_bp=request.window.cds_flank_bp,
                intron_flank_bp=request.window.intron_flank_bp,
                display_cds_start=display_start,
                display_cds_end=display_end,
                total_display_bases=len(reference_sequence),
            ),
            segments=segments,
            queried_variant=QueriedVariant(
                hgvs_c=variant.hgvs_c,
                hgvs_p=variant.hgvs_p,
                cds_pos=variant.cds_pos,
                genomic_hg38=variant.genomic_hg38,
                ref=variant.ref,
                alt=variant.alt,
                codon_number=variant.codon_number,
                codon_offset=variant.codon_offset,
                aa_ref=variant.aa_ref,
                aa_alt=variant.aa_alt,
                classification=variant.classification,
            ),
            sequences=ViewerSequences(
                allele_mode=request.allele_mode,
                reference_window_sequence=reference_sequence,
                display_window_sequence=display_sequence,
                applied_variant=applied_variant,
            ),
            tracks=ViewerTracks(
                protein_product=build_protein_product_effect(
                    variant=variant,
                    allele_mode=request.allele_mode,
                    reference_protein_length=transcript.protein_length,
                    exons=transcript.exons,
                )
            ),
            provenance=ViewerProvenance(
                sources=[
                    ViewerProvenanceSource(
                        name="synthetic_transcript_model",
                        identifier=transcript.transcript,
                    )
                ]
            ),
        )

    def _window_bounds(
        self,
        *,
        window: ViewerWindowRequest,
        variant: VariantProjection,
        transcript: TranscriptModel,
    ) -> tuple[int, int]:
        min_cds = min(exon.cds_start for exon in transcript.exons)
        max_cds = max(exon.cds_end for exon in transcript.exons)
        if window.kind == "cds_range":
            start = window.cds_start if window.cds_start is not None else min_cds
            end = window.cds_end if window.cds_end is not None else max_cds
        else:
            start = variant.cds_pos - window.cds_flank_bp
            end = variant.cds_pos + window.cds_flank_bp
        start = max(min_cds, start)
        end = min(max_cds, end)
        if start > end:
            raise GeneViewerError(
                code=unsupported_input_warning("window"),
                message="Viewer window does not overlap the transcript CDS.",
                status_code=HTTP_UNPROCESSABLE_ENTITY,
            )
        return start, end

    def _segments(
        self,
        *,
        transcript: TranscriptModel,
        display_start: int,
        display_end: int,
    ) -> list[ViewerSegment]:
        ordered_exons = sorted(transcript.exons, key=lambda exon: exon.cds_start)
        introns = {intron.number: intron for intron in transcript.introns}
        selected: list[tuple[TranscriptExon, int, int]] = []
        for exon in ordered_exons:
            if exon.cds_end < display_start or exon.cds_start > display_end:
                continue
            start = max(display_start, exon.cds_start)
            end = min(display_end, exon.cds_end)
            selected.append((exon, start, end))

        segments: list[ViewerSegment] = []
        for index, (exon, start, end) in enumerate(selected):
            segment_id = f"exon-{exon.number}:{start}-{end}"
            segments.append(
                ViewerSegment(
                    id=segment_id,
                    kind="exon",
                    label=f"Exon {exon.number}",
                    exon_number=exon.number,
                    cds_start=start,
                    cds_end=end,
                    genomic_start=exon.genomic_start,
                    genomic_end=exon.genomic_end,
                    strand=_schema_strand(transcript.strand),
                    sequence=exon.sequence_for(start, end),
                )
            )
            next_exon = selected[index + 1][0] if index + 1 < len(selected) else None
            if next_exon is None or next_exon.number != exon.number + 1:
                continue
            intron = introns.get(exon.number)
            if intron is None:
                continue
            segments.append(
                ViewerSegment(
                    id=f"intron-{intron.number}",
                    kind="intron",
                    label=f"Intron {intron.number}",
                    intron_number=intron.number,
                    genomic_start=intron.genomic_start,
                    genomic_end=intron.genomic_end,
                    strand=_schema_strand(transcript.strand),
                    five_prime_sequence=intron.five_prime_sequence,
                    three_prime_sequence=intron.three_prime_sequence,
                    omitted_bp=intron.omitted_bp,
                )
            )

        return segments

    def _apply_variant(
        self,
        *,
        allele_mode: str,
        reference_sequence: str,
        segments: list[ViewerSegment],
        variant: VariantProjection,
    ) -> tuple[AppliedVariant | None, str]:
        operation = _variant_display_operation(
            segments=segments,
            reference_sequence=reference_sequence,
            variant=variant,
        )
        if allele_mode == "reference":
            return None, reference_sequence

        applied = AppliedVariant(
            hgvs_c=variant.hgvs_c,
            cds_pos=variant.cds_pos,
            segment_id=operation.segment_id,
            sequence_offset=operation.sequence_offset,
            ref=operation.ref,
            alt=operation.alt,
        )
        display_sequence = (
            reference_sequence[: operation.sequence_offset]
            + operation.alt
            + reference_sequence[operation.sequence_offset + operation.replace_length :]
        )
        return applied, display_sequence


def _segment_display_sequence(segment: ViewerSegment) -> str:
    if segment.kind == "intron":
        return f"{segment.five_prime_sequence}{segment.three_prime_sequence}"
    return segment.sequence


def _replace_at(sequence: str, index: int, value: str) -> str:
    return f"{sequence[:index]}{value}{sequence[index + 1:]}"


def _variant_display_operation(
    *,
    segments: list[ViewerSegment],
    reference_sequence: str,
    variant: VariantProjection,
) -> VariantDisplayOperation:
    coord_map = _exon_display_coordinate_map(segments)
    end = variant.cds_end or variant.cds_pos

    if variant.variant_type == "insertion":
        left = variant.cds_pos
        right = end
        if right != left + 1:
            _raise_unsupported(
                "variant_insert_coordinates",
                "Viewer insertion overlays require adjacent coding coordinates.",
            )
        if left not in coord_map or right not in coord_map:
            _raise_variant_outside_window(variant)
        segment_id, left_offset = coord_map[left]
        return VariantDisplayOperation(
            segment_id=segment_id,
            sequence_offset=left_offset + 1,
            ref="",
            alt=variant.alt,
            replace_length=0,
        )

    positions = list(range(variant.cds_pos, end + 1))
    if not positions or any(position not in coord_map for position in positions):
        _raise_variant_outside_window(variant)

    mapped = [coord_map[position] for position in positions]
    segment_ids = {segment_id for segment_id, _offset in mapped}
    offsets = [offset for _segment_id, offset in mapped]
    if len(segment_ids) != 1 or offsets != list(range(offsets[0], offsets[0] + len(offsets))):
        _raise_unsupported(
            "variant_spans_segments",
            "Viewer overlays currently require the affected coding bases to be contiguous in the displayed segment.",
        )

    segment_id = mapped[0][0]
    sequence_offset = offsets[0]
    observed_ref = reference_sequence[sequence_offset : offsets[-1] + 1].upper()

    if variant.variant_type == "duplication":
        duplicated = variant.alt or observed_ref
        if variant.alt and duplicated != observed_ref:
            _raise_reference_mismatch(variant)
        return VariantDisplayOperation(
            segment_id=segment_id,
            sequence_offset=offsets[-1] + 1,
            ref="",
            alt=duplicated,
            replace_length=0,
        )

    if variant.ref and observed_ref != variant.ref.upper():
        _raise_reference_mismatch(variant)

    if variant.variant_type in {"substitution", "deletion", "delins"}:
        return VariantDisplayOperation(
            segment_id=segment_id,
            sequence_offset=sequence_offset,
            ref=variant.ref.upper() or observed_ref,
            alt=variant.alt,
            replace_length=len(observed_ref),
        )

    _raise_unsupported(
        "variant_type",
        f"Viewer overlays do not support variant type {variant.variant_type}.",
    )


def _exon_display_coordinate_map(
    segments: list[ViewerSegment],
) -> dict[int, tuple[str, int]]:
    coord_map: dict[int, tuple[str, int]] = {}
    cumulative = 0
    for segment in segments:
        segment_sequence = _segment_display_sequence(segment)
        if segment.kind == "exon" and segment.cds_start is not None and segment.cds_end is not None:
            for local_offset, cds_pos in enumerate(range(segment.cds_start, segment.cds_end + 1)):
                coord_map[cds_pos] = (segment.id, cumulative + local_offset)
        cumulative += len(segment_sequence)
    return coord_map


def _raise_reference_mismatch(variant: VariantProjection) -> None:
    raise GeneViewerError(
        code=GENE_VIEWER_REFERENCE_MISMATCH,
        message=(
            "Viewer reference sequence does not match the requested "
            f"variant at {variant.hgvs_c}."
        ),
        status_code=HTTP_UNPROCESSABLE_ENTITY,
        warnings=[GENE_VIEWER_REFERENCE_MISMATCH],
    )


def _raise_variant_outside_window(variant: VariantProjection) -> None:
    raise GeneViewerError(
        code=unsupported_input_warning("variant_outside_window"),
        message=f"Queried variant {variant.hgvs_c} is outside the active viewer window.",
        status_code=HTTP_UNPROCESSABLE_ENTITY,
    )


def _schema_strand(strand: str) -> str:
    return strand if strand in {"+", "-"} else "unknown"


def _source_window_bounds(
    *,
    window: ViewerWindowRequest,
    variant: VariantProjection,
    source: SourceTranscriptModel,
) -> tuple[int, int]:
    min_cds = min(exon.cds_start for exon in source.exons)
    max_cds = max(exon.cds_end for exon in source.exons)
    if window.kind == "cds_range":
        start = window.cds_start if window.cds_start is not None else min_cds
        end = window.cds_end if window.cds_end is not None else max_cds
    else:
        start = variant.cds_pos - window.cds_flank_bp
        end = variant.cds_pos + window.cds_flank_bp
    start = max(min_cds, start)
    end = min(max_cds, end)
    if start > end:
        raise GeneViewerError(
            code=unsupported_input_warning("window"),
            message="Viewer window does not overlap the transcript CDS.",
            status_code=HTTP_UNPROCESSABLE_ENTITY,
        )
    return start, end


def _strand_from_ensembl(value: Any) -> str:
    if value in {1, "1", "+", "+1"}:
        return "+"
    if value in {-1, "-1", "-"}:
        return "-"
    return "unknown"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _required_int(value: Any, field_name: str) -> int:
    parsed = _int_or_none(value)
    if parsed is None:
        raise GeneViewerError(
            code=GENE_VIEWER_PROVIDER_MALFORMED,
            message=f"Ensembl transcript response did not include {field_name}.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    return parsed


def _versionless(identifier: str) -> str:
    return identifier.split(".", 1)[0] if identifier else ""


def _versioned_id(transcript: dict[str, Any]) -> str:
    transcript_id = str(transcript.get("id") or "")
    version = transcript.get("version")
    if transcript_id and version:
        return f"{transcript_id}.{version}"
    return transcript_id


def _transcript_aliases(
    *,
    transcript: dict[str, Any],
    requested: str | None,
) -> list[str]:
    aliases: list[str] = []
    for alias in [requested, _versioned_id(transcript), str(transcript.get("display_name") or "")]:
        if alias and alias not in aliases:
            aliases.append(alias)
    for mane in _as_list(transcript.get("MANE")):
        if not isinstance(mane, dict):
            continue
        refseq_match = str(mane.get("refseq_match") or "")
        if refseq_match and refseq_match not in aliases:
            aliases.append(refseq_match)
        mane_type = str(mane.get("type") or "")
        if mane_type == "MANE_Select" and "MANE Select" not in aliases:
            aliases.append("MANE Select")
    return aliases


def _utr_length(transcript: dict[str, Any], utr_type: str) -> int | None:
    total = 0
    found = False
    for utr in _as_list(transcript.get("UTR")):
        if not isinstance(utr, dict) or utr.get("type") != utr_type:
            continue
        start = _int_or_none(utr.get("start"))
        end = _int_or_none(utr.get("end"))
        if start is None or end is None:
            continue
        found = True
        total += abs(end - start) + 1
    return total if found else None


def _protein_hgvs_from_variant_validator(variant_payload: dict[str, Any]) -> str | None:
    consequences = variant_payload.get("hgvs_predicted_protein_consequence")
    if not isinstance(consequences, dict):
        return None
    raw = str(consequences.get("tlr") or consequences.get("slr") or "")
    if not raw:
        return None
    hgvs_p = raw.split(":", 1)[1] if ":" in raw else raw
    return hgvs_p.replace("p.(", "p.").removesuffix(")")


def _protein_change_parts(hgvs_p: str | None) -> tuple[int | None, str | None, str | None]:
    if hgvs_p is None:
        return None, None, None
    match = re.fullmatch(
        r"p\.(?P<ref>[A-Z][a-z]{2}|[A-Z*])(?P<pos>\d+)(?P<alt>[A-Z][a-z]{2}|[A-Z*])",
        hgvs_p,
    )
    if match is None:
        return None, None, None
    return (
        int(match.group("pos")),
        _aa_to_one_letter(match.group("ref")),
        _aa_to_one_letter(match.group("alt")),
    )


def _aa_to_one_letter(value: str) -> str:
    return AA3_TO_AA1.get(value, value)


def _clean_dna(sequence: str) -> str:
    return re.sub(r"[^ACGTNacgtn]", "", sequence).upper()


def _raise_unsupported(kind: str, message: str) -> None:
    code = unsupported_input_warning(kind)
    raise GeneViewerError(
        code=code,
        message=message,
        status_code=HTTP_UNPROCESSABLE_ENTITY,
        warnings=[code],
    )


def _viewer_response_for_allele_mode(
    response: GeneViewerResponse,
    allele_mode: str,
) -> GeneViewerResponse:
    if allele_mode == response.sequences.allele_mode:
        updated = response.model_copy(deep=True)
        _set_windowed_protein_product(updated, allele_mode=allele_mode)
        return updated
    if allele_mode == "reference":
        updated = response.model_copy(deep=True)
        updated.sequences.allele_mode = "reference"
        updated.sequences.display_window_sequence = updated.sequences.reference_window_sequence
        updated.sequences.applied_variant = None
        _set_windowed_protein_product(updated, allele_mode="reference")
        return updated

    updated = response.model_copy(deep=True)
    variant = updated.queried_variant
    cumulative = 0
    for segment in updated.segments:
        segment_sequence = _segment_display_sequence(segment)
        if (
            segment.kind == "exon"
            and segment.cds_start is not None
            and segment.cds_end is not None
            and segment.cds_start <= variant.cds_pos <= segment.cds_end
        ):
            local_offset = variant.cds_pos - segment.cds_start
            global_offset = cumulative + local_offset
            observed_ref = updated.sequences.reference_window_sequence[global_offset]
            if observed_ref.upper() != variant.ref.upper():
                raise GeneViewerError(
                    code=GENE_VIEWER_REFERENCE_MISMATCH,
                    message=(
                        "Viewer fixture reference base does not match the requested "
                        f"variant at {variant.hgvs_c}."
                    ),
                    status_code=HTTP_UNPROCESSABLE_ENTITY,
                    warnings=[GENE_VIEWER_REFERENCE_MISMATCH],
                )
            updated.sequences.allele_mode = "variant"
            updated.sequences.display_window_sequence = _replace_at(
                updated.sequences.reference_window_sequence,
                global_offset,
                variant.alt,
            )
            updated.sequences.applied_variant = AppliedVariant(
                hgvs_c=variant.hgvs_c,
                cds_pos=variant.cds_pos,
                segment_id=segment.id,
                sequence_offset=global_offset,
                ref=variant.ref,
                alt=variant.alt,
            )
            _set_windowed_protein_product(updated, allele_mode="variant")
            return updated
        cumulative += len(segment_sequence)

    raise GeneViewerError(
        code=unsupported_input_warning("variant_outside_window"),
        message="Queried variant is outside the active viewer fixture window.",
        status_code=HTTP_UNPROCESSABLE_ENTITY,
    )


def _set_windowed_protein_product(response: GeneViewerResponse, *, allele_mode: str) -> None:
    response.tracks.protein_product = build_protein_product_effect(
        variant=response.queried_variant,
        allele_mode=allele_mode,
        reference_protein_length=response.summary.protein_length,
        exons=[
            SourceTranscriptExon(
                number=segment.exon_number,
                cds_start=segment.cds_start,
                cds_end=segment.cds_end,
                genomic_start=segment.genomic_start or 0,
                genomic_end=segment.genomic_end or 0,
            )
            for segment in response.segments
            if (
                segment.kind == "exon"
                and segment.exon_number is not None
                and segment.cds_start is not None
                and segment.cds_end is not None
            )
        ],
    )
