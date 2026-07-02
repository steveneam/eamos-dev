from __future__ import annotations

import threading
from typing import Any, Callable
from urllib.parse import quote

from fastapi import status
import httpx

from app.core.config import Settings
from app.data_sources.runtime_assets import (
    ResolvedRuntimeAsset,
    SourceAssetMaterializationError,
    SourceAssetMaterializationStore,
    resolve_hg38_materialized_runtime_asset,
)
from app.schemas.gene_viewer import ProteinDomain, ProteinFeatures, ViewerProvenanceSource
from app.services.compact_coordinate_index import (
    CompactCoordinateIndex,
    CompactCoordinateTranscript,
    compact_coordinate_index_from_settings,
)
from app.services.gene_viewer_errors import (
    GENE_VIEWER_PROVIDER_FAILED_PREFIX,
    GENE_VIEWER_PROVIDER_MALFORMED,
    GENE_VIEWER_PROVIDER_UNAVAILABLE,
    HTTP_UNPROCESSABLE_ENTITY,
    GeneViewerError,
    raise_unsupported_gene_viewer_input as _raise_unsupported,
)
from app.services.gene_viewer_models import (
    GeneViewerReferenceReader,
    SourceTranscriptExon,
    SourceTranscriptIntron,
    SourceTranscriptModel,
)
from app.services.gene_viewer_utils import (
    as_list as _as_list,
    clean_dna as _clean_dna,
    int_or_none as _int_or_none,
    protein_change_parts as _protein_change_parts,
    protein_hgvs_from_variant_validator as _protein_hgvs_from_variant_validator,
    reverse_complement as _reverse_complement,
    transcript_aliases as _transcript_aliases,
    utr_length as _utr_length,
    versioned_id as _versioned_id,
    versionless as _versionless,
)
from app.services.gene_viewer_variants import VariantProjection
from app.services.reference_genome import (
    ReferenceGenomeStoreError,
    TwoBitReferenceGenomeStore,
)
from app.services.sequence_context import NormalizedVariantQuery, unsupported_input_warning


def _materialized_hg38_gene_viewer_store(
    resolved: ResolvedRuntimeAsset,
) -> TwoBitReferenceGenomeStore:
    return TwoBitReferenceGenomeStore(
        resolved.path,
        source_id=resolved.source_id,
        expected_size_bytes=resolved.byte_size,
        expected_md5=resolved.checksum_value,
        verify_checksum=False,
    )


def _resolved_asset_store_key(
    resolved: ResolvedRuntimeAsset,
) -> tuple[str, str, int | None, str | None]:
    return (
        str(getattr(resolved, "path", "")),
        str(getattr(resolved, "source_id", "")),
        getattr(resolved, "byte_size", None),
        getattr(resolved, "checksum_value", None),
    )


class HttpGeneViewerSourceClient:
    """HTTP source client boundary for live viewer hydration."""

    def __init__(
        self,
        settings: Settings | None,
        *,
        materialization_store: SourceAssetMaterializationStore | None = None,
        compact_index: CompactCoordinateIndex | None = None,
        reference_store_factory: (
            Callable[[ResolvedRuntimeAsset], GeneViewerReferenceReader] | None
        ) = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.settings = settings
        self.materialization_store = materialization_store
        self.compact_index = compact_index or (
            compact_coordinate_index_from_settings(settings) if settings is not None else None
        )
        self.reference_store_factory = (
            reference_store_factory or _materialized_hg38_gene_viewer_store
        )
        self.timeout_seconds = timeout_seconds
        self._reference_store_lock = threading.RLock()
        self._reference_store_key: tuple[str, str, int | None, str | None] | None = None
        self._reference_store: GeneViewerReferenceReader | None = None

    def close(self) -> None:
        with self._reference_store_lock:
            self._close_reference_store_unlocked()

    def _reference_store_for_resolved(
        self,
        resolved: ResolvedRuntimeAsset,
    ) -> GeneViewerReferenceReader:
        key = _resolved_asset_store_key(resolved)
        if self._reference_store is None or self._reference_store_key != key:
            self._close_reference_store_unlocked()
            self._reference_store = self.reference_store_factory(resolved)
            self._reference_store_key = key
        return self._reference_store

    def _close_reference_store_unlocked(self) -> None:
        store = self._reference_store
        self._reference_store = None
        self._reference_store_key = None
        close = getattr(store, "close", None)
        if callable(close):
            close()

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
        compact_variant = (
            self.compact_index.resolve_variant(
                gene=query.gene,
                cdna=query.hgvs,
                transcript=query.resolver_transcript,
            )
            if self.compact_index is not None
            else None
        )
        if compact_variant is not None:
            hgvs_p = compact_variant.protein_change
            codon_number, aa_ref, aa_alt = _protein_change_parts(hgvs_p)
            return VariantProjection(
                hgvs_c=variant.hgvs_c,
                cds_pos=variant.cds_pos,
                cds_end=variant.cds_end,
                variant_type=variant.variant_type,
                ref=variant.ref,
                alt=variant.alt,
                hgvs_p=hgvs_p,
                genomic_hg38=compact_variant.genomic_hg38,
                codon_number=codon_number,
                codon_offset=(variant.cds_pos - 1) % 3,
                aa_ref=aa_ref,
                aa_alt=aa_alt,
            )
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
        compact_transcript = (
            self.compact_index.transcript(gene=query.gene, transcript=query.resolver_transcript)
            if self.compact_index is not None
            else None
        )
        if compact_transcript is not None:
            return _source_transcript_from_compact_index(compact_transcript)
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
        if self.materialization_store is not None:
            return self._fetch_materialized_hg38_sequence(
                chrom=chrom,
                start=start,
                end=end,
                strand=strand,
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

    def _fetch_materialized_hg38_sequence(
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
        try:
            resolved = resolve_hg38_materialized_runtime_asset(
                self.settings,
                self.materialization_store,
                verify_checksum=False,
            )
            with self._reference_store_lock:
                reference_store = self._reference_store_for_resolved(resolved)
                sequence = reference_store.get_sequence(
                    chrom,
                    start,
                    end,
                    build="GRCh38",
                ).sequence
        except SourceAssetMaterializationError as exc:
            code = f"{GENE_VIEWER_PROVIDER_UNAVAILABLE}:{exc.code}"
            raise GeneViewerError(
                code=code,
                message="Materialized hg38 source asset is not ready for gene viewer hydration.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                warnings=[code],
            ) from exc
        except (ReferenceGenomeStoreError, OSError) as exc:
            detail = getattr(exc, "code", type(exc).__name__)
            code = f"{GENE_VIEWER_PROVIDER_FAILED_PREFIX}:{detail}"
            raise GeneViewerError(
                code=code,
                message="Materialized hg38 reader failed while hydrating the gene viewer.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                warnings=[code],
            ) from exc

        cleaned = _clean_dna(sequence)
        return _reverse_complement(cleaned) if strand == "-" else cleaned

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
        if "compact_coordinate_index_transcript" in transcript.warnings:
            sources = [
                ViewerProvenanceSource(
                    name="eamos_compact_coordinate_index",
                    identifier=transcript.transcript,
                    url=None,
                )
            ]
            if self.materialization_store is not None:
                sources.append(
                    ViewerProvenanceSource(
                        name="ucsc_hg38_2bit_materialized",
                        identifier=transcript.genome_build,
                        url=None,
                    )
                )
            return sources
        sources = [
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
        if self.materialization_store is not None:
            sources.append(
                ViewerProvenanceSource(
                    name="ucsc_hg38_2bit_materialized",
                    identifier=transcript.genome_build,
                    url=None,
                )
            )
        return sources

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
            total_exons=len(ordered_exons),
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


def _required_int(value: Any, field_name: str) -> int:
    parsed = _int_or_none(value)
    if parsed is None:
        raise GeneViewerError(
            code=GENE_VIEWER_PROVIDER_MALFORMED,
            message=f"Ensembl transcript response did not include {field_name}.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    return parsed


def _strand_from_ensembl(value: Any) -> str:
    if value in {1, "1", "+", "+1"}:
        return "+"
    if value in {-1, "-1", "-"}:
        return "-"
    return "unknown"


def _source_transcript_from_compact_index(
    transcript: CompactCoordinateTranscript,
) -> SourceTranscriptModel:
    exons = tuple(
        SourceTranscriptExon(
            number=exon.number,
            cds_start=exon.cds_start,
            cds_end=exon.cds_end,
            genomic_start=exon.genomic_start,
            genomic_end=exon.genomic_end,
        )
        for exon in transcript.exons
    )
    aliases = tuple(
        dict.fromkeys(
            alias
            for alias in (
                transcript.refseq_transcript,
                transcript.ensembl_transcript,
                *transcript.transcript_aliases,
            )
            if alias
        )
    )
    return SourceTranscriptModel(
        gene=transcript.gene,
        transcript=transcript.refseq_transcript,
        chrom=transcript.chrom,
        strand=transcript.strand,
        exons=exons,
        introns=_introns_from_compact_exons(exons),
        ensembl_gene_id=transcript.ensembl_gene_id,
        transcript_aliases=aliases,
        genome_build=transcript.genome_build,
        gene_start=transcript.gene_start,
        gene_end=transcript.gene_end,
        gene_length=(
            transcript.gene_end - transcript.gene_start + 1
            if transcript.gene_start is not None and transcript.gene_end is not None
            else None
        ),
        cds_length=transcript.cds_length,
        protein_length=transcript.protein_length,
        utr5_length=transcript.utr5_length,
        utr3_length=transcript.utr3_length,
        mrna_length=transcript.mrna_length,
        translation_id=transcript.translation_id,
        warnings=(
            "compact_coordinate_index_transcript",
            "raw_gff_runtime_scan_disabled",
        ),
    )


def _introns_from_compact_exons(
    exons: tuple[SourceTranscriptExon, ...],
) -> tuple[SourceTranscriptIntron, ...]:
    introns: list[SourceTranscriptIntron] = []
    for left, right in zip(exons, exons[1:], strict=False):
        left_interval = tuple(sorted((left.genomic_start, left.genomic_end)))
        right_interval = tuple(sorted((right.genomic_start, right.genomic_end)))
        lower_exon, higher_exon = sorted(
            (left_interval, right_interval),
            key=lambda interval: interval[0],
        )
        start = lower_exon[1] + 1
        end = higher_exon[0] - 1
        if start > end:
            continue
        introns.append(
            SourceTranscriptIntron(
                number=left.number,
                genomic_start=start,
                genomic_end=end,
            )
        )
    return tuple(introns)
