from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

from app.core.config import Settings
from app.schemas.workbench import PrimerRequest
from app.services.dbsnp_local import DbSnpLocalError, DbSnpLocalStore
from app.services.sequence_context import SequenceContext
from app.services.workbench_design_common import _settings_path

PRIMER_SNP_MASK_MAX_INTERVAL_BASES = 20_000
PRIMER_SNP_MASK_MAX_RECORDS = 10_000


@dataclass(frozen=True)
class PrimerSnpMaskingVariant:
    rsid: str
    chrom: str
    position: int
    template_offset: int
    ref: str
    alts: tuple[str, ...]


@dataclass(frozen=True)
class PrimerSnpMaskingResult:
    requested: bool
    provider: str
    active: bool
    source_version: str | None = None
    queried_interval: str | None = None
    variants: tuple[PrimerSnpMaskingVariant, ...] = ()
    excluded_regions: tuple[tuple[int, int], ...] = ()
    warnings: tuple[str, ...] = ()

    def seq_args(self) -> dict[str, object]:
        if not self.active or not self.excluded_regions:
            return {}
        return {
            "SEQUENCE_EXCLUDED_REGION": [[start, length] for start, length in self.excluded_regions]
        }

    def risk_offsets(self) -> set[int]:
        offsets: set[int] = set()
        for start, length in self.excluded_regions:
            offsets.update(range(start, start + max(1, length)))
        return offsets

    def note(self, *, rejected_pair_count: int = 0) -> str | None:
        if not self.requested:
            return None
        if not self.active:
            warning = self.warnings[0] if self.warnings else "primer_snp_masking_unavailable"
            return f"{warning}: SNP masking was requested but no source-backed mask was applied."
        interval = self.queried_interval or "unknown interval"
        source = f"; source={self.source_version}" if self.source_version else ""
        return (
            "dbSNP local SNP masking active"
            f"{source}; queried={interval}; snp_count={len(self.variants)}; "
            f"excluded_regions={len(self.excluded_regions)}; "
            f"rejected_3prime_pairs={rejected_pair_count}."
        )


class PrimerSnpMaskingProvider(Protocol):
    def prepare(
        self,
        *,
        payload: PrimerRequest,
        context: SequenceContext,
        template: str,
    ) -> PrimerSnpMaskingResult: ...


class NoopPrimerSnpMaskingProvider:
    def prepare(
        self,
        *,
        payload: PrimerRequest,
        context: SequenceContext,
        template: str,
    ) -> PrimerSnpMaskingResult:
        del context, template
        return PrimerSnpMaskingResult(
            requested=bool(payload.avoid_snps),
            provider="none",
            active=False,
            warnings=("primer_snp_masking_not_configured",) if payload.avoid_snps else (),
        )


class LocalDbSnpPrimerSnpMaskingProvider:
    """Fixture/local dbSNP SNP mask for Primer3 design windows."""

    def __init__(self, store: DbSnpLocalStore | None = None) -> None:
        self.store = store or DbSnpLocalStore()

    def prepare(
        self,
        *,
        payload: PrimerRequest,
        context: SequenceContext,
        template: str,
    ) -> PrimerSnpMaskingResult:
        if not payload.avoid_snps:
            return PrimerSnpMaskingResult(
                requested=False,
                provider="dbsnp_local",
                active=False,
            )
        chrom, target_pos = target_genomic_locus(context)
        if chrom is None or target_pos is None:
            return PrimerSnpMaskingResult(
                requested=True,
                provider="dbsnp_local",
                active=False,
                warnings=("primer_snp_masking_locus_unavailable",),
            )
        template_interval = template_genomic_interval(context, len(template))
        if template_interval is None:
            return PrimerSnpMaskingResult(
                requested=True,
                provider="dbsnp_local",
                active=False,
                warnings=("primer_snp_masking_interval_invalid",),
            )
        template_start, template_end = template_interval

        variants: dict[tuple[str, int, str], PrimerSnpMaskingVariant] = {}
        try:
            for position in range(template_start, template_end + 1):
                for record in self.store.records_at(chrom, position):
                    offset = template_offset_for_genomic(context, record.position)
                    if offset is None or offset < 0 or offset >= len(template):
                        continue
                    variants[(record.chrom, record.position, record.rsid)] = (
                        PrimerSnpMaskingVariant(
                            rsid=record.rsid,
                            chrom=record.chrom,
                            position=record.position,
                            template_offset=offset,
                            ref=record.ref,
                            alts=record.alts,
                        )
                    )
        except DbSnpLocalError as exc:
            return PrimerSnpMaskingResult(
                requested=True,
                provider="dbsnp_local",
                active=False,
                warnings=(f"primer_snp_masking_{exc.code}",),
            )

        ordered_variants = tuple(
            sorted(variants.values(), key=lambda variant: (variant.template_offset, variant.rsid))
        )
        excluded_regions = tuple(
            (variant.template_offset, max(1, len(variant.ref))) for variant in ordered_variants
        )
        return PrimerSnpMaskingResult(
            requested=True,
            provider="dbsnp_local",
            active=True,
            source_version=self.store.provenance().source_version,
            queried_interval=f"{chrom}:{template_start}-{template_end}",
            variants=ordered_variants,
            excluded_regions=excluded_regions,
        )


class IndexedDbSnpPrimerSnpMaskingProvider:
    """Bounded tabix query against the mounted dbSNP GRCh38 VCF."""

    def __init__(
        self,
        vcf_path: Path,
        index_path: Path,
        *,
        pysam_module: ModuleType | None = None,
    ) -> None:
        self.vcf_path = vcf_path
        self.index_path = index_path
        self._pysam_module = pysam_module

    def prepare(
        self,
        *,
        payload: PrimerRequest,
        context: SequenceContext,
        template: str,
    ) -> PrimerSnpMaskingResult:
        if not payload.avoid_snps:
            return PrimerSnpMaskingResult(
                requested=False,
                provider="dbsnp_indexed_vcf",
                active=False,
            )
        interval = template_genomic_interval(context, len(template))
        chrom, _target_pos = target_genomic_locus(context)
        if interval is None or chrom is None:
            return PrimerSnpMaskingResult(
                requested=True,
                provider="dbsnp_indexed_vcf",
                active=False,
                warnings=("primer_snp_masking_locus_unavailable",),
            )
        if not self.vcf_path.is_file() or not self.index_path.is_file():
            return PrimerSnpMaskingResult(
                requested=True,
                provider="dbsnp_indexed_vcf",
                active=False,
                warnings=("primer_snp_masking_assets_unavailable",),
            )

        start, end = interval
        if end - start + 1 > PRIMER_SNP_MASK_MAX_INTERVAL_BASES:
            return PrimerSnpMaskingResult(
                requested=True,
                provider="dbsnp_indexed_vcf",
                active=False,
                warnings=("primer_snp_masking_interval_too_large",),
            )
        try:
            pysam = self._pysam_module or import_module("pysam")
            with pysam.VariantFile(
                str(self.vcf_path),
                index_filename=str(self.index_path),
            ) as variants_file:
                contig = _dbsnp_contig(variants_file.header.contigs, chrom)
                if contig is None:
                    return PrimerSnpMaskingResult(
                        requested=True,
                        provider="dbsnp_indexed_vcf",
                        active=False,
                        warnings=("primer_snp_masking_contig_unavailable",),
                    )
                records: list[tuple[int, str, tuple[str, ...], str | None]] = []
                for index, record in enumerate(variants_file.fetch(contig, start - 1, end)):
                    if index >= PRIMER_SNP_MASK_MAX_RECORDS:
                        return PrimerSnpMaskingResult(
                            requested=True,
                            provider="dbsnp_indexed_vcf",
                            active=False,
                            warnings=("primer_snp_masking_result_limit_exceeded",),
                        )
                    records.append(
                        (
                            int(record.pos),
                            str(record.ref or "").upper(),
                            tuple(str(alt).upper() for alt in (record.alts or ())),
                            str(record.id) if record.id is not None else None,
                        )
                    )
                source_version = _dbsnp_source_version(variants_file.header)
        except (ImportError, OSError, ValueError):
            return PrimerSnpMaskingResult(
                requested=True,
                provider="dbsnp_indexed_vcf",
                active=False,
                warnings=("primer_snp_masking_provider_unavailable",),
            )

        masked: dict[tuple[int, str], PrimerSnpMaskingVariant] = {}
        for position, reference, alternates, record_id in records:
            offset = template_offset_for_genomic(context, position)
            if (
                offset is None
                or not reference
                or not alternates
                or offset < 0
                or offset >= len(template)
            ):
                continue
            rsid = record_id or f"dbsnp-{position}"
            masked[(position, rsid)] = PrimerSnpMaskingVariant(
                rsid=rsid,
                chrom=chrom,
                position=position,
                template_offset=offset,
                ref=reference,
                alts=alternates,
            )

        ordered = tuple(sorted(masked.values(), key=lambda row: (row.template_offset, row.rsid)))
        return PrimerSnpMaskingResult(
            requested=True,
            provider="dbsnp_indexed_vcf",
            active=True,
            source_version=source_version,
            queried_interval=f"{chrom}:{start}-{end}",
            variants=ordered,
            excluded_regions=tuple((row.template_offset, max(1, len(row.ref))) for row in ordered),
        )


def target_genomic_locus(context: SequenceContext) -> tuple[str | None, int | None]:
    if not context.genomic_hg38:
        return None, None
    parts = context.genomic_hg38.split("-")
    if len(parts) < 2 or not parts[1].isdigit():
        return None, None
    chrom = parts[0]
    if not chrom.startswith("chr"):
        chrom = f"chr{chrom}"
    return chrom, int(parts[1])


def template_is_genomically_reversed(context: SequenceContext) -> bool:
    coordinates = context.genomic_coordinates
    if coordinates is not None:
        concrete = [coordinate for coordinate in coordinates if coordinate is not None]
        return len(concrete) > 1 and concrete[0] > concrete[-1]
    orientation = context.source_metadata.get("selection_orientation")
    return orientation == "genomic_reverse" or (
        orientation == "transcript" and context.strand == "-"
    )


def template_genomic_coordinate(context: SequenceContext, offset: int) -> int | None:
    coordinates = context.genomic_coordinates
    if coordinates is not None:
        if offset < 0 or offset >= len(coordinates):
            return None
        return coordinates[offset]
    start_text = context.source_metadata.get("selection_genomic_start")
    end_text = context.source_metadata.get("selection_genomic_end")
    if start_text and end_text and start_text.isdigit() and end_text.isdigit():
        start = int(start_text)
        end = int(end_text)
        coordinate = end - offset if template_is_genomically_reversed(context) else start + offset
        return coordinate if start <= coordinate <= end else None
    _chrom, target_pos = target_genomic_locus(context)
    if target_pos is None:
        return None
    return target_pos - context.target_offset + offset


def template_offset_for_genomic(context: SequenceContext, coordinate: int) -> int | None:
    coordinates = context.genomic_coordinates
    if coordinates is not None:
        try:
            return coordinates.index(coordinate)
        except ValueError:
            return None
    start_text = context.source_metadata.get("selection_genomic_start")
    end_text = context.source_metadata.get("selection_genomic_end")
    if start_text and end_text and start_text.isdigit() and end_text.isdigit():
        start = int(start_text)
        end = int(end_text)
        if not start <= coordinate <= end:
            return None
        return end - coordinate if template_is_genomically_reversed(context) else coordinate - start
    _chrom, target_pos = target_genomic_locus(context)
    if target_pos is None:
        return None
    return coordinate - (target_pos - context.target_offset)


def template_genomic_interval(
    context: SequenceContext,
    template_length: int,
) -> tuple[int, int] | None:
    if context.genomic_coordinates is not None:
        concrete = [
            coordinate
            for coordinate in context.genomic_coordinates[:template_length]
            if coordinate is not None
        ]
        if not concrete:
            return None
        return min(concrete), max(concrete)
    first = template_genomic_coordinate(context, 0)
    last = template_genomic_coordinate(context, template_length - 1)
    if first is None or last is None:
        return None
    return min(first, last), max(first, last)


def default_snp_masking_provider(settings: Settings | None) -> PrimerSnpMaskingProvider:
    if settings is None:
        return NoopPrimerSnpMaskingProvider()
    vcf_path = _settings_path(settings, settings.dbsnp_runtime_vcf_path)
    index_path = _settings_path(settings, settings.dbsnp_runtime_index_path)
    if vcf_path.is_file() and index_path.is_file():
        return IndexedDbSnpPrimerSnpMaskingProvider(vcf_path, index_path)
    return NoopPrimerSnpMaskingProvider()


def _dbsnp_contig(contigs: Any, chromosome: str) -> str | None:
    requested = _contig_alias(chromosome)
    return next(
        (str(contig) for contig in contigs if _contig_alias(str(contig)) == requested), None
    )


def _contig_alias(contig: str) -> str:
    raw = contig.strip().upper().removeprefix("CHR")
    accession = re.fullmatch(r"NC_0*(?P<number>\d+)\.\d+", raw)
    if accession is not None:
        number = int(accession.group("number"))
        if number == 23:
            return "X"
        if number == 24:
            return "Y"
        if number == 12920:
            return "M"
        return str(number)
    return "M" if raw == "MT" else raw.lstrip("0") or "0"


def _dbsnp_source_version(header: Any) -> str:
    for record in getattr(header, "records", ()):
        key = str(getattr(record, "key", "")).lower()
        if key in {"filedate", "dbsnp_build_id"}:
            value = str(getattr(record, "value", "") or "").strip()
            if value:
                return value[:128]
    return "dbsnp_grch38_indexed_vcf"
