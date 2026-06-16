from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Iterable, Protocol
from uuid import uuid4
from urllib.parse import unquote

from app.schemas.batch import (
    BATCH_MAX_VARIANTS,
    BatchCreateRequest,
    BatchCreateResponse,
    BatchFilters,
    BatchJob,
    BatchPage,
    BatchResult,
    ParsedVariant,
)
from app.services.panels import PanelService
from app.services.vcf_ingest import DEFAULT_MAX_DECOMPRESSED_BYTES, parse_vcf_upload_bytes

BATCH_EST_SECONDS_PER_LOOKUP = 0.25
BATCH_DEFAULT_UPLOAD_REGISTRY_MAX_ENTRIES = 128
BATCH_DEFAULT_JOB_REGISTRY_MAX_ENTRIES = 256
BATCH_DEFAULT_REGISTRY_TTL_SECONDS = 60 * 60


class BatchCoordinateResolver(Protocol):
    def resolve(self, **kwargs): ...


@dataclass
class StoredUpload:
    upload_ref: str
    filename: str | None
    variants: list[ParsedVariant]
    created_at_monotonic: float
    warnings: list[str] = field(default_factory=list)
    skipped_rows: int = 0


@dataclass
class StoredBatchJob:
    job_id: str
    status: str
    created_at_monotonic: float
    n_input: int
    n_to_lookup: int
    n_after_filters: int | None
    est_seconds: float
    done: int
    total: int
    results: list[BatchResult]
    warnings: list[str] = field(default_factory=list)


class BatchService:
    def __init__(
        self,
        *,
        upload_dir: Path,
        panel_service: PanelService,
        coordinate_resolver: BatchCoordinateResolver | None = None,
        max_upload_entries: int = BATCH_DEFAULT_UPLOAD_REGISTRY_MAX_ENTRIES,
        max_job_entries: int = BATCH_DEFAULT_JOB_REGISTRY_MAX_ENTRIES,
        entry_ttl_seconds: int = BATCH_DEFAULT_REGISTRY_TTL_SECONDS,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.upload_dir = upload_dir / "batch"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.panel_service = panel_service
        self.coordinate_resolver = coordinate_resolver
        self._max_upload_entries = _positive_int_or_default(
            max_upload_entries,
            BATCH_DEFAULT_UPLOAD_REGISTRY_MAX_ENTRIES,
        )
        self._max_job_entries = _positive_int_or_default(
            max_job_entries,
            BATCH_DEFAULT_JOB_REGISTRY_MAX_ENTRIES,
        )
        self._entry_ttl_seconds = max(0, int(entry_ttl_seconds))
        self._clock = clock or monotonic
        self._uploads: OrderedDict[str, StoredUpload] = OrderedDict()
        self._jobs: OrderedDict[str, StoredBatchJob] = OrderedDict()

    def store_upload(
        self,
        payload: bytes,
        *,
        filename: str | None = None,
        max_decompressed_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES,
        max_variants: int = BATCH_MAX_VARIANTS,
    ) -> str:
        self._prune_registries()
        upload_ref = f"batch-upload-{uuid4().hex[:12]}"
        parsed = parse_vcf_upload_bytes(
            payload,
            filename=filename,
            max_decompressed_bytes=max_decompressed_bytes,
            max_variants=max_variants,
        )
        stored = StoredUpload(
            upload_ref=upload_ref,
            filename=filename,
            variants=parsed.variants,
            created_at_monotonic=self._clock(),
            warnings=parsed.warnings,
            skipped_rows=parsed.skipped_rows,
        )
        self._uploads[upload_ref] = stored
        self._trim_registry(self._uploads, max_entries=self._max_upload_entries)
        self._write_upload_snapshot(stored)
        return upload_ref

    def create_job(self, request: BatchCreateRequest) -> BatchCreateResponse:
        self._prune_registries()
        variants, warnings = self._request_variants(request)
        filtered, filter_warnings = self._apply_prelookup_filters(variants, request.filters)
        warnings.extend(filter_warnings)
        deduped, dedupe_warnings = _dedupe_variants(filtered)
        warnings.extend(dedupe_warnings)

        results = [self._result_from_variant(variant) for variant in deduped]
        job_id = f"batch-{uuid4().hex[:12]}"
        est_seconds = round(len(deduped) * BATCH_EST_SECONDS_PER_LOOKUP, 2)
        job = StoredBatchJob(
            job_id=job_id,
            status="completed",
            created_at_monotonic=self._clock(),
            n_input=len(variants),
            n_to_lookup=len(deduped),
            n_after_filters=len(results),
            est_seconds=est_seconds,
            done=len(results),
            total=len(results),
            results=results,
            warnings=warnings,
        )
        self._jobs[job_id] = job
        self._trim_registry(self._jobs, max_entries=self._max_job_entries)
        return BatchCreateResponse(
            job_id=job_id,
            n_input=job.n_input,
            n_to_lookup=job.n_to_lookup,
            est_seconds=job.est_seconds,
        )

    def get_job(self, job_id: str, *, limit: int, cursor: str | None = None) -> BatchJob | None:
        self._prune_registries()
        job = self._jobs.get(job_id)
        if job is None:
            return None
        self._jobs.move_to_end(job_id)
        offset = _cursor_offset(cursor)
        page_results = job.results[offset : offset + limit]
        next_offset = offset + len(page_results)
        next_cursor = str(next_offset) if next_offset < len(job.results) else None
        return BatchJob(
            job_id=job.job_id,
            status=job.status,
            n_input=job.n_input,
            n_to_lookup=job.n_to_lookup,
            n_after_filters=job.n_after_filters,
            est_seconds=job.est_seconds,
            done=job.done,
            total=job.total,
            results=page_results,
            page=BatchPage(limit=limit, next_cursor=next_cursor, total=len(job.results)),
            warnings=list(job.warnings),
        )

    def _request_variants(
        self, request: BatchCreateRequest
    ) -> tuple[list[ParsedVariant], list[str]]:
        if request.variants is not None:
            return list(request.variants), []
        upload = self._uploads.get(request.upload_ref or "")
        if upload is None:
            raise KeyError(request.upload_ref or "")
        self._uploads.move_to_end(request.upload_ref or "")
        warnings = list(upload.warnings)
        if upload.skipped_rows:
            warnings.append(f"upload_skipped_rows:{upload.skipped_rows}")
        return list(upload.variants), warnings

    def _apply_prelookup_filters(
        self,
        variants: list[ParsedVariant],
        filters: BatchFilters,
    ) -> tuple[list[ParsedVariant], list[str]]:
        panel_genes: set[str] | None = None
        warnings: list[str] = []
        if filters.panel_slug:
            panel = self.panel_service.get_panel(filters.panel_slug)
            if panel is None:
                warnings.append(f"panel_filter_unknown:{filters.panel_slug}")
                panel_genes = set()
            else:
                panel_genes = {gene.symbol for gene in panel.genes}

        kept: list[ParsedVariant] = []
        for variant in variants:
            variant_warnings = list(variant.warnings)
            if filters.pass_only and variant.filter not in {None, "", ".", "PASS"}:
                continue
            if filters.max_af is not None and variant.info_af is not None:
                if variant.info_af > filters.max_af:
                    continue
            if filters.regions and not _in_regions(variant, filters.regions):
                continue
            if panel_genes is not None:
                if variant.gene and variant.gene not in panel_genes:
                    continue
                if not variant.gene:
                    variant_warnings.append("panel_filter_gene_missing_kept_for_lookup")
            kept.append(variant.model_copy(update={"warnings": variant_warnings}))
        return kept, warnings

    def _write_upload_snapshot(self, upload: StoredUpload) -> None:
        snapshot = self.upload_dir / f"{upload.upload_ref}.json"
        with snapshot.open("w", encoding="utf-8") as handle:
            for variant in upload.variants:
                handle.write(variant.model_dump_json())
                handle.write("\n")

    def _prune_registries(self) -> None:
        if self._entry_ttl_seconds <= 0:
            return
        expires_before = self._clock() - self._entry_ttl_seconds
        self._prune_expired(self._uploads, expires_before=expires_before)
        self._prune_expired(self._jobs, expires_before=expires_before)

    @staticmethod
    def _prune_expired(
        registry: OrderedDict[str, StoredUpload] | OrderedDict[str, StoredBatchJob],
        *,
        expires_before: float,
    ) -> None:
        expired = [
            key for key, value in registry.items() if value.created_at_monotonic < expires_before
        ]
        for key in expired:
            registry.pop(key, None)

    @staticmethod
    def _trim_registry(
        registry: OrderedDict[str, StoredUpload] | OrderedDict[str, StoredBatchJob],
        *,
        max_entries: int,
    ) -> None:
        while len(registry) > max_entries:
            registry.popitem(last=False)

    def _result_from_variant(self, variant: ParsedVariant) -> BatchResult:
        resolved_variant_key: str | None = None
        warnings = list(variant.warnings)
        if (
            self.coordinate_resolver is not None
            and not (variant.chrom and variant.pos and variant.ref and variant.alt)
            and variant.gene
            and variant.variant
            and variant.variant.startswith("c.")
        ):
            try:
                resolved = self.coordinate_resolver.resolve(
                    gene=variant.gene,
                    cdna=variant.variant,
                )
            except Exception:
                resolved = None
                warnings.append("compact_coordinate_index_batch_resolution_failed")
            if resolved is not None:
                resolved_variant_key = resolved.genomic_hg38
                warnings.extend(
                    warning
                    for warning in (
                        "compact_coordinate_index_batch_resolution",
                        *getattr(resolved, "warnings", ()),
                    )
                    if warning
                )
            else:
                warnings.append("compact_coordinate_index_batch_resolution_unavailable")

        variant_key = resolved_variant_key or _variant_key(variant)
        hgvs_c = variant.variant if (variant.variant or "").startswith("c.") else None
        hgvs_p = _raw_info_value(variant.raw, "HGVS_P")
        clinvar_verdict = _raw_info_value(variant.raw, "CLNSIG")
        return BatchResult(
            variant_key=variant_key,
            state="completed",
            gene=variant.gene,
            hgvs_c=hgvs_c,
            hgvs_p=hgvs_p,
            clinvar_verdict=clinvar_verdict,
            gnomad_af=variant.info_af,
            predictor_ensemble={},
            acmg_classification=None,
            report_href=f"/lookup?query={variant.query}",
            warnings=list(dict.fromkeys(warnings)),
        )


def _dedupe_variants(variants: Iterable[ParsedVariant]) -> tuple[list[ParsedVariant], list[str]]:
    seen: set[str] = set()
    deduped: list[ParsedVariant] = []
    duplicate_count = 0
    for variant in variants:
        key = _variant_key(variant)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        deduped.append(variant)
    warnings = [f"deduplicated_variants:{duplicate_count}"] if duplicate_count else []
    return deduped, warnings


def _variant_key(variant: ParsedVariant) -> str:
    if variant.chrom and variant.pos and variant.ref and variant.alt:
        return f"{variant.chrom}-{variant.pos}-{variant.ref}-{variant.alt}"
    return variant.query


def _raw_info_value(raw: str | None, key: str) -> str | None:
    if not raw:
        return None
    columns = raw.split("\t")
    if len(columns) < 8:
        columns = raw.split()
    if len(columns) < 8:
        return None
    prefix = f"{key.upper()}="
    for item in columns[7].split(";"):
        if item.upper().startswith(prefix):
            return unquote(item.split("=", 1)[1])
    return None


def _in_regions(variant: ParsedVariant, regions: list[str]) -> bool:
    if not variant.chrom or not variant.pos:
        return False
    chrom = variant.chrom.removeprefix("chr")
    for region in regions:
        region_chrom, start, end = _parse_region(region)
        if region_chrom != chrom:
            continue
        if start is None or end is None or start <= variant.pos <= end:
            return True
    return False


def _parse_region(region: str) -> tuple[str, int | None, int | None]:
    chrom, _, span = region.partition(":")
    chrom = chrom.strip().removeprefix("chr")
    if not span:
        return chrom, None, None
    start_text, _, end_text = span.replace(",", "").partition("-")
    try:
        start = int(start_text)
        end = int(end_text)
    except ValueError:
        return chrom, None, None
    return chrom, start, end


def _cursor_offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        offset = int(cursor)
    except ValueError:
        return 0
    return max(0, offset)


def _positive_int_or_default(value: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
