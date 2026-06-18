from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock, Thread
from time import monotonic
from typing import Any, Iterable, Protocol
from urllib.parse import quote_plus, unquote
from uuid import uuid4

from app.schemas.lookup import LookupRequest
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
from app.services.compact_coordinate_index import CompactCoordinateIndex
from app.services.panels import PanelService
from app.services.vcf_ingest import DEFAULT_MAX_DECOMPRESSED_BYTES, parse_vcf_upload_bytes

BATCH_EST_SECONDS_PER_LOOKUP = 0.25
BATCH_DEFAULT_UPLOAD_REGISTRY_MAX_ENTRIES = 128
BATCH_DEFAULT_JOB_REGISTRY_MAX_ENTRIES = 256
BATCH_DEFAULT_REGISTRY_TTL_SECONDS = 60 * 60
BATCH_DEFAULT_LOOKUP_WORKERS = 2
BATCH_LOOKUP_CACHE_MAX_ENTRIES = 4096
BATCH_PANEL_SPLICE_FLANK_BP = 20


class BatchCoordinateResolver(Protocol):
    def resolve(self, **kwargs): ...


class BatchLookupService(Protocol):
    def lookup(self, request: LookupRequest, refresh: bool = False): ...


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


@dataclass(frozen=True)
class _VariantIdentity:
    variant_key: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _PanelInterval:
    gene: str
    chrom: str
    start: int
    end: int


class BatchService:
    def __init__(
        self,
        *,
        upload_dir: Path,
        panel_service: PanelService,
        coordinate_resolver: BatchCoordinateResolver | None = None,
        lookup_service: BatchLookupService | None = None,
        panel_interval_index: CompactCoordinateIndex | None = None,
        max_upload_entries: int = BATCH_DEFAULT_UPLOAD_REGISTRY_MAX_ENTRIES,
        max_job_entries: int = BATCH_DEFAULT_JOB_REGISTRY_MAX_ENTRIES,
        entry_ttl_seconds: int = BATCH_DEFAULT_REGISTRY_TTL_SECONDS,
        max_lookup_workers: int = BATCH_DEFAULT_LOOKUP_WORKERS,
        panel_splice_flank_bp: int = BATCH_PANEL_SPLICE_FLANK_BP,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.upload_dir = upload_dir / "batch"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.panel_service = panel_service
        self.coordinate_resolver = coordinate_resolver
        self.lookup_service = lookup_service
        self.panel_interval_index = panel_interval_index or getattr(
            coordinate_resolver,
            "compact_index",
            None,
        )
        self._max_upload_entries = _positive_int_or_default(
            max_upload_entries,
            BATCH_DEFAULT_UPLOAD_REGISTRY_MAX_ENTRIES,
        )
        self._max_job_entries = _positive_int_or_default(
            max_job_entries,
            BATCH_DEFAULT_JOB_REGISTRY_MAX_ENTRIES,
        )
        self._entry_ttl_seconds = max(0, int(entry_ttl_seconds))
        self._max_lookup_workers = max(
            1,
            min(3, _positive_int_or_default(max_lookup_workers, BATCH_DEFAULT_LOOKUP_WORKERS)),
        )
        self._panel_splice_flank_bp = max(0, int(panel_splice_flank_bp))
        self._clock = clock or monotonic
        self._uploads: OrderedDict[str, StoredUpload] = OrderedDict()
        self._jobs: OrderedDict[str, StoredBatchJob] = OrderedDict()
        self._lookup_cache: OrderedDict[str, BatchResult] = OrderedDict()
        self._lock = RLock()

    def bind_lookup_service(self, lookup_service: BatchLookupService | None) -> None:
        if lookup_service is None:
            return
        with self._lock:
            if self.lookup_service is None:
                self.lookup_service = lookup_service

    def store_upload(
        self,
        payload: bytes,
        *,
        filename: str | None = None,
        max_decompressed_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES,
        max_variants: int = BATCH_MAX_VARIANTS,
    ) -> str:
        with self._lock:
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
        with self._lock:
            self._uploads[upload_ref] = stored
            self._trim_registry(self._uploads, max_entries=self._max_upload_entries)
        self._write_upload_snapshot(stored)
        return upload_ref

    def create_job(self, request: BatchCreateRequest) -> BatchCreateResponse:
        with self._lock:
            self._prune_registries()
            variants, warnings = self._request_variants(request)
        filtered, filter_warnings = self._apply_prelookup_filters(variants, request.filters)
        warnings.extend(filter_warnings)
        deduped, dedupe_warnings = _dedupe_variants(
            filtered,
            key_fn=lambda variant: self._variant_identity(variant).variant_key,
        )
        warnings.extend(dedupe_warnings)

        job_id = f"batch-{uuid4().hex[:12]}"
        est_seconds = round(len(deduped) * BATCH_EST_SECONDS_PER_LOOKUP, 2)
        if self.lookup_service is None:
            results = [self._result_from_variant(variant) for variant in deduped]
            status = "completed"
            done = len(results)
        else:
            results = [self._queued_result_from_variant(variant) for variant in deduped]
            status = "queued" if results else "completed"
            done = 0
        job = StoredBatchJob(
            job_id=job_id,
            status=status,
            created_at_monotonic=self._clock(),
            n_input=len(variants),
            n_to_lookup=len(deduped),
            n_after_filters=len(deduped),
            est_seconds=est_seconds,
            done=done,
            total=len(results),
            results=results,
            warnings=warnings,
        )
        with self._lock:
            self._jobs[job_id] = job
            self._trim_registry(self._jobs, max_entries=self._max_job_entries)
        if self.lookup_service is not None and deduped:
            self._start_background_job(job_id, tuple(deduped))
        return BatchCreateResponse(
            job_id=job_id,
            n_input=job.n_input,
            n_to_lookup=job.n_to_lookup,
            est_seconds=job.est_seconds,
        )

    def get_job(self, job_id: str, *, limit: int, cursor: str | None = None) -> BatchJob | None:
        with self._lock:
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
        panel_intervals: tuple[_PanelInterval, ...] = ()
        if panel_genes is not None:
            panel_intervals, interval_warnings = self._panel_intervals(panel_genes)
            warnings.extend(interval_warnings)

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
                gene_matches = bool(variant.gene and variant.gene in panel_genes)
                interval_matches = (
                    bool(panel_intervals)
                    and variant.chrom is not None
                    and variant.pos is not None
                    and _variant_intersects_intervals(variant, panel_intervals)
                )
                if not gene_matches and not interval_matches:
                    if not variant.gene and not panel_intervals:
                        variant_warnings.append("panel_filter_interval_unavailable_kept_for_lookup")
                    else:
                        continue
                elif interval_matches and not gene_matches:
                    variant_warnings.append("panel_filter_interval_match")
                if not variant.gene and not panel_intervals:
                    variant_warnings.append("panel_filter_gene_missing_kept_for_lookup")
            kept.append(variant.model_copy(update={"warnings": variant_warnings}))
        return kept, warnings

    def _panel_intervals(
        self, panel_genes: set[str]
    ) -> tuple[tuple[_PanelInterval, ...], list[str]]:
        if not panel_genes:
            return (), []
        if self.panel_interval_index is None:
            return (), ["panel_filter_interval_index_unavailable"]
        intervals: list[_PanelInterval] = []
        missing_genes = 0
        for gene in sorted(panel_genes):
            try:
                transcript = self.panel_interval_index.transcript(gene=gene)
            except Exception:
                missing_genes += 1
                continue
            if transcript is None:
                missing_genes += 1
                continue
            bounds = [
                coordinate
                for exon in transcript.exons
                for coordinate in (exon.genomic_start, exon.genomic_end)
            ]
            start = transcript.gene_start or (min(bounds) if bounds else None)
            end = transcript.gene_end or (max(bounds) if bounds else None)
            if start is None or end is None:
                missing_genes += 1
                continue
            intervals.append(
                _PanelInterval(
                    gene=gene,
                    chrom=transcript.chrom.removeprefix("chr").upper(),
                    start=max(1, min(start, end) - self._panel_splice_flank_bp),
                    end=max(start, end) + self._panel_splice_flank_bp,
                )
            )
        warnings = []
        if not intervals:
            warnings.append("panel_filter_interval_index_unavailable")
        elif missing_genes:
            warnings.append(f"panel_filter_interval_genes_missing:{missing_genes}")
        return tuple(intervals), warnings

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
        identity = self._variant_identity(variant)
        hgvs_c = variant.variant if (variant.variant or "").startswith("c.") else None
        hgvs_p = _raw_info_value(variant.raw, "HGVS_P")
        clinvar_verdict = _raw_info_value(variant.raw, "CLNSIG")
        return BatchResult(
            variant_key=identity.variant_key,
            state="completed",
            gene=variant.gene,
            hgvs_c=hgvs_c,
            hgvs_p=hgvs_p,
            clinvar_verdict=clinvar_verdict,
            gnomad_af=variant.info_af,
            predictor_ensemble={},
            acmg_classification=None,
            report_href=f"/lookup?query={variant.query}",
            warnings=list(dict.fromkeys(identity.warnings)),
        )

    def _queued_result_from_variant(self, variant: ParsedVariant) -> BatchResult:
        identity = self._variant_identity(variant)
        return BatchResult(
            variant_key=identity.variant_key,
            state="lookup_pending",
            gene=variant.gene,
            hgvs_c=variant.variant if (variant.variant or "").startswith("c.") else None,
            hgvs_p=_raw_info_value(variant.raw, "HGVS_P"),
            clinvar_verdict=None,
            gnomad_af=variant.info_af,
            predictor_ensemble={},
            acmg_classification=None,
            report_href=f"/lookup?query={quote_plus(variant.query)}",
            warnings=list(dict.fromkeys(identity.warnings)),
        )

    def _variant_identity(self, variant: ParsedVariant) -> _VariantIdentity:
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
        return _VariantIdentity(
            variant_key=resolved_variant_key or _variant_key(variant),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def _start_background_job(self, job_id: str, variants: tuple[ParsedVariant, ...]) -> None:
        thread = Thread(
            target=self._run_lookup_job,
            args=(job_id, variants),
            name=f"eamos-batch-{job_id}",
            daemon=True,
        )
        thread.start()

    def _run_lookup_job(self, job_id: str, variants: tuple[ParsedVariant, ...]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "running"

        try:
            with ThreadPoolExecutor(max_workers=self._max_lookup_workers) as executor:
                futures = {
                    executor.submit(self._lookup_result_for_variant, variant): index
                    for index, variant in enumerate(variants)
                }
                for future in as_completed(futures):
                    index = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = self._failed_result_from_variant(
                            variants[index],
                            f"batch_lookup_failed:{type(exc).__name__}",
                        )
                    self._record_lookup_result(job_id, index, result)
            self._finish_lookup_job(job_id)
        except Exception as exc:
            with self._lock:
                job = self._jobs.get(job_id)
                if job is not None:
                    job.status = "failed"
                    job.warnings.append(f"batch_job_failed:{type(exc).__name__}")

    def _lookup_result_for_variant(self, variant: ParsedVariant) -> BatchResult:
        identity = self._variant_identity(variant)
        with self._lock:
            cached = self._lookup_cache.get(identity.variant_key)
            if cached is not None:
                self._lookup_cache.move_to_end(identity.variant_key)
                result = _enrich_batch_result_from_variant(cached, variant)
                self._lookup_cache[identity.variant_key] = result.model_copy(deep=True)
                return result

        lookup_service = self.lookup_service
        if lookup_service is None:
            return self._result_from_variant(variant)

        try:
            request = _lookup_request_from_variant(variant)
            response = lookup_service.lookup(request, refresh=False)
        except Exception as exc:
            return self._failed_result_from_variant(
                variant,
                f"batch_lookup_failed:{type(exc).__name__}",
            )

        result = _batch_result_from_lookup_response(
            variant=variant,
            identity=identity,
            response=response,
        )
        result = _enrich_batch_result_from_variant(result, variant)
        if result.state == "completed":
            with self._lock:
                self._lookup_cache[identity.variant_key] = result.model_copy(deep=True)
                self._trim_registry(
                    self._lookup_cache,
                    max_entries=BATCH_LOOKUP_CACHE_MAX_ENTRIES,
                )
        return result

    def _failed_result_from_variant(self, variant: ParsedVariant, warning: str) -> BatchResult:
        identity = self._variant_identity(variant)
        return BatchResult(
            variant_key=identity.variant_key,
            state="failed",
            gene=variant.gene,
            hgvs_c=variant.variant if (variant.variant or "").startswith("c.") else None,
            hgvs_p=_raw_info_value(variant.raw, "HGVS_P"),
            clinvar_verdict=_raw_info_value(variant.raw, "CLNSIG"),
            gnomad_af=variant.info_af,
            predictor_ensemble={},
            acmg_classification=None,
            report_href=f"/lookup?query={quote_plus(variant.query)}",
            warnings=list(dict.fromkeys([*identity.warnings, warning])),
        )

    def _record_lookup_result(self, job_id: str, index: int, result: BatchResult) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or index >= len(job.results):
                return
            job.results[index] = result
            job.done = min(job.total, job.done + 1)

    def _finish_lookup_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            any_completed = any(result.state == "completed" for result in job.results)
            job.status = "completed" if any_completed or job.total == 0 else "failed"


def _dedupe_variants(
    variants: Iterable[ParsedVariant],
    *,
    key_fn: Callable[[ParsedVariant], str] | None = None,
) -> tuple[list[ParsedVariant], list[str]]:
    seen: set[str] = set()
    key_to_index: dict[str, int] = {}
    deduped: list[ParsedVariant] = []
    duplicate_count = 0
    for variant in variants:
        key = key_fn(variant) if key_fn is not None else _variant_key(variant)
        if key in seen:
            duplicate_count += 1
            deduped[key_to_index[key]] = _merge_variant_metadata(
                deduped[key_to_index[key]], variant
            )
            continue
        seen.add(key)
        key_to_index[key] = len(deduped)
        deduped.append(variant)
    warnings = [f"deduplicated_variants:{duplicate_count}"] if duplicate_count else []
    return deduped, warnings


def _merge_variant_metadata(primary: ParsedVariant, duplicate: ParsedVariant) -> ParsedVariant:
    updates: dict[str, Any] = {}
    for field_name in (
        "raw",
        "gene",
        "variant",
        "chrom",
        "pos",
        "ref",
        "alt",
        "filter",
        "info_af",
        "source_index",
        "sample_id",
        "genotype",
    ):
        if _has_value(getattr(primary, field_name)) or not _has_value(
            getattr(duplicate, field_name)
        ):
            continue
        updates[field_name] = getattr(duplicate, field_name)
    warnings = list(dict.fromkeys([*primary.warnings, *duplicate.warnings]))
    if warnings != primary.warnings:
        updates["warnings"] = warnings
    if not updates:
        return primary
    return primary.model_copy(update=updates)


def _has_value(value: Any) -> bool:
    return value is not None and value != ""


def _variant_key(variant: ParsedVariant) -> str:
    if variant.chrom and variant.pos and variant.ref and variant.alt:
        return f"{variant.chrom}-{variant.pos}-{variant.ref}-{variant.alt}"
    return variant.query


def _lookup_request_from_variant(variant: ParsedVariant) -> LookupRequest:
    if variant.gene and variant.variant:
        return LookupRequest(gene=variant.gene, cdna=variant.variant)
    return LookupRequest(search_text=variant.query)


def _batch_result_from_lookup_response(
    *,
    variant: ParsedVariant,
    identity: _VariantIdentity,
    response,
) -> BatchResult:
    payload = response.report_payload
    profile = getattr(payload, "report_profile", None)
    header = getattr(profile, "header", None) if profile is not None else None
    acmg_worksheet = getattr(profile, "acmg_worksheet", None) if profile is not None else None
    row = payload.variant_summary_rows[0] if payload.variant_summary_rows else None
    computed = getattr(payload, "eamos_computed_classification", None)
    population = getattr(payload, "population_frequency_detail", None)

    gene = getattr(header, "gene", None) or getattr(row, "gene", None) or variant.gene
    hgvs_c = getattr(header, "cdna", None) or (
        variant.variant if (variant.variant or "").startswith("c.") else None
    )
    hgvs_p = (
        getattr(header, "protein_change", None)
        or getattr(row, "protein_change", None)
        or _raw_info_value(variant.raw, "HGVS_P")
    )
    clinvar_verdict = (
        getattr(header, "classification", None)
        or getattr(acmg_worksheet, "classification", None)
        or _evidence_summary_text(response, "clinvar", "classification")
        or _raw_info_value(variant.raw, "CLNSIG")
    )
    gnomad_af = getattr(population, "allele_frequency", None) if population is not None else None
    if gnomad_af is None:
        gnomad_af = _evidence_summary_float(response, "gnomad", "allele_frequency")
    acmg_classification = getattr(computed, "tier", None) or getattr(
        acmg_worksheet, "classification", None
    )
    genomic_hg38 = getattr(header, "genomic_hg38", None) or getattr(row, "genomic_hg38", None)
    query = str(getattr(response, "query", None) or variant.query)
    warnings = list(identity.warnings)
    warnings.extend(getattr(response, "warnings", []) or [])
    return BatchResult(
        variant_key=genomic_hg38 or identity.variant_key,
        state="completed",
        gene=gene,
        hgvs_c=hgvs_c,
        hgvs_p=hgvs_p,
        clinvar_verdict=clinvar_verdict,
        gnomad_af=gnomad_af,
        predictor_ensemble=_predictor_ensemble(payload),
        acmg_classification=acmg_classification,
        report_href=f"/lookup?query={quote_plus(query)}",
        warnings=list(dict.fromkeys(warnings)),
    )


def _enrich_batch_result_from_variant(result: BatchResult, variant: ParsedVariant) -> BatchResult:
    updates: dict[str, Any] = {}
    variant_cdna = variant.variant if _is_cdna_hgvs(variant.variant) else None

    gene = result.gene or variant.gene
    hgvs_c = result.hgvs_c
    if variant_cdna and not _is_cdna_hgvs(hgvs_c):
        hgvs_c = variant_cdna

    if not result.gene and variant.gene:
        updates["gene"] = variant.gene
    if hgvs_c != result.hgvs_c:
        updates["hgvs_c"] = hgvs_c
    if not result.hgvs_p:
        hgvs_p = _raw_info_value(variant.raw, "HGVS_P")
        if hgvs_p:
            updates["hgvs_p"] = hgvs_p
    if result.gnomad_af is None and variant.info_af is not None:
        updates["gnomad_af"] = variant.info_af
    if updates and gene and hgvs_c:
        updates["report_href"] = f"/lookup?query={quote_plus(f'{gene}:{hgvs_c}')}"
    if not updates:
        return result.model_copy(deep=True)
    return result.model_copy(update=updates, deep=True)


def _is_cdna_hgvs(value: str | None) -> bool:
    return bool(value and value.startswith("c."))


def _predictor_ensemble(payload) -> dict[str, Any]:
    profile = getattr(payload, "report_profile", None)
    deep_dive = getattr(profile, "computational_deep_dive", None) if profile is not None else None
    rows: dict[str, Any] = {}
    if deep_dive is not None:
        for predictor in [*deep_dive.predictors, *deep_dive.conservation]:
            rows[predictor.name] = {
                key: value
                for key, value in {
                    "score": predictor.score,
                    "threshold": predictor.threshold,
                    "interpretation": predictor.interpretation,
                    "calibrated_label": predictor.calibrated_label,
                    "calibration_bucket": predictor.calibration_bucket,
                    "source": predictor.source,
                    "version": predictor.version,
                    "launch_gate": predictor.launch_gate,
                }.items()
                if value is not None
            }
        if deep_dive.spliceai_max_delta is not None:
            rows.setdefault("SpliceAI", {})["score"] = deep_dive.spliceai_max_delta
            if deep_dive.spliceai_consequence:
                rows["SpliceAI"]["interpretation"] = deep_dive.spliceai_consequence

    if not rows and getattr(payload, "in_silico_predictions", None) is not None:
        for card in payload.in_silico_predictions.cards:
            rows[card.name] = {
                "score": card.score,
                "threshold": card.threshold,
                "interpretation": card.verdict_label or card.verdict,
            }
    return rows


def _evidence_summary_text(response, source: str, key: str) -> str | None:
    summary = _evidence_summary(response, source)
    value = summary.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _evidence_summary_float(response, source: str, key: str) -> float | None:
    summary = _evidence_summary(response, source)
    try:
        return float(summary.get(key))
    except (TypeError, ValueError):
        return None


def _evidence_summary(response, source: str) -> dict[str, Any]:
    for item in getattr(response, "evidence", []) or []:
        if item.source == source:
            return item.summary or {}
    return {}


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


def _variant_intersects_intervals(
    variant: ParsedVariant,
    intervals: tuple[_PanelInterval, ...],
) -> bool:
    if not variant.chrom or variant.pos is None:
        return False
    chrom = variant.chrom.removeprefix("chr").upper()
    variant_end = variant.pos + max(1, len(variant.ref or "")) - 1
    for interval in intervals:
        if interval.chrom != chrom:
            continue
        if variant_end >= interval.start and variant.pos <= interval.end:
            return True
    return False


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
