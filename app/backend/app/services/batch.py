from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock, RLock
from time import monotonic
from typing import Any, BinaryIO, Iterable, Protocol
from urllib.parse import urlencode
from uuid import uuid4

from app.schemas.lookup import LookupRequest
from app.schemas.batch import (
    BATCH_MAX_VARIANTS,
    BatchAlleleIdentityV2,
    BatchCreateRequest,
    BatchCreateResponse,
    BatchFieldExecutionV2,
    BatchFilterDispositionV2,
    BatchFilterPlanV2,
    BatchFilters,
    BatchInputEnvelopeV2,
    BatchJob,
    BatchPage,
    BatchPagingV2,
    BatchResult,
    BatchSampleProvenanceV2,
    BatchSourceSnapshotV2,
    ParsedVariant,
)
from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.services.compact_coordinate_index import CompactCoordinateIndex
from app.services.batch_engine import (
    BatchAlleleNormalizer,
    BatchFilterUnavailable,
    BatchLease,
    BatchLeaseStore,
    BatchPreFilterStats,
    BatchResourceLimitExceeded,
    DEFAULT_MAX_RAW_RECORDS,
    BatchNormalizationFailed,
    BatchNormalizationUnavailable,
    GenomicInterval,
    SnapshotCursorCodec,
    StagedVcf,
    UnavailableBatchNormalizer,
    build_source_snapshot,
    cleanup_expired_staged_vcfs,
    filter_post_annotation,
    iter_pre_annotation,
    iter_staged_variants,
    mounted_interval_capability,
    remove_staged_vcf,
    stage_vcf_file,
    unavailable_interval_capability,
)
from app.services.panels import PanelService
from app.services.vcf_ingest import (
    DEFAULT_MAX_DECOMPRESSED_BYTES,
    VcfIngestLimitError,
    parse_vcf_upload_bytes,
)

BATCH_EST_SECONDS_PER_LOOKUP = 0.25
BATCH_DEFAULT_UPLOAD_REGISTRY_MAX_ENTRIES = 128
BATCH_DEFAULT_JOB_REGISTRY_MAX_ENTRIES = 256
BATCH_DEFAULT_REGISTRY_TTL_SECONDS = 60 * 60
BATCH_DEFAULT_LOOKUP_WORKERS = 2
BATCH_LOOKUP_CACHE_MAX_ENTRIES = 4096
BATCH_PANEL_SPLICE_FLANK_BP = 20
BATCH_DEFAULT_PREPARE_TIMEOUT_SECONDS = 120.0


class BatchCoordinateResolver(Protocol):
    def resolve(self, **kwargs): ...


class BatchLookupService(Protocol):
    def lookup(self, request: LookupRequest, refresh: bool = False): ...


class BatchQueueUnavailable(RuntimeError):
    pass


@dataclass
class StoredUpload:
    upload_ref: str
    variants: list[ParsedVariant] | None
    staged_vcf: StagedVcf | None
    created_at_monotonic: float
    expires_at: datetime
    owner_user_id: str | None = None
    owner_provider: str | None = None
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
    owner_user_id: str | None = None
    owner_provider: str | None = None
    warnings: list[str] = field(default_factory=list)
    input_envelope_v2: BatchInputEnvelopeV2 | None = None
    source_snapshot_v2: BatchSourceSnapshotV2 | None = None
    filter_plan_v2: BatchFilterPlanV2 | None = None
    filter_dispositions_v2: list[BatchFilterDispositionV2] = field(default_factory=list)
    v2_contexts: list["_V2RowContext | None"] = field(default_factory=list)
    direct_report_source_snapshot_id: str | None = None


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


@dataclass(frozen=True)
class _V2RowContext:
    allele_identity: BatchAlleleIdentityV2 | None
    samples: tuple[BatchSampleProvenanceV2, ...]
    filter_dispositions: tuple[BatchFilterDispositionV2, ...] = ()


@dataclass(frozen=True)
class _LookupTask:
    result_index: int
    variant: ParsedVariant
    v2_context: _V2RowContext | None = None


@dataclass(frozen=True)
class _PreparedV2Job:
    envelope: BatchInputEnvelopeV2
    snapshot: BatchSourceSnapshotV2
    tasks: tuple[_LookupTask, ...]
    results: tuple[BatchResult, ...]
    contexts: tuple[_V2RowContext | None, ...]
    filter_dispositions: tuple[BatchFilterDispositionV2, ...]
    warnings: tuple[str, ...]
    n_to_lookup: int
    status: str
    done: int


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
        workflow_service: Any | None = None,
        normalizer: BatchAlleleNormalizer | None = None,
        cursor_secret: bytes | None = None,
        lease_store: BatchLeaseStore | None = None,
        lease_seconds: int = 120,
        max_prepare_seconds: float = BATCH_DEFAULT_PREPARE_TIMEOUT_SECONDS,
    ) -> None:
        self.upload_dir = upload_dir / "batch"
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
        cleanup_expired_staged_vcfs(
            self.upload_dir / "uploads",
            older_than_seconds=max(
                1,
                self._entry_ttl_seconds or BATCH_DEFAULT_REGISTRY_TTL_SECONDS,
            ),
        )
        self._max_lookup_workers = max(
            1,
            min(3, _positive_int_or_default(max_lookup_workers, BATCH_DEFAULT_LOOKUP_WORKERS)),
        )
        self._panel_splice_flank_bp = max(0, int(panel_splice_flank_bp))
        self._clock = clock or monotonic
        self._max_prepare_seconds = max(1.0, min(float(max_prepare_seconds), 600.0))
        self.workflow_service = workflow_service
        self.normalizer = normalizer or UnavailableBatchNormalizer()
        self._cursor_codec = SnapshotCursorCodec(cursor_secret)
        self._lease_store_path = (
            self.upload_dir / "leases.sqlite3" if workflow_service is not None else None
        )
        self._lease_seconds = lease_seconds
        self._lease_store = lease_store
        if (
            self._lease_store is None
            and self._lease_store_path is not None
            and self._lease_store_path.is_file()
        ):
            self._lease_store = BatchLeaseStore(
                self._lease_store_path,
                lease_seconds=self._lease_seconds,
            )
        self._uploads: OrderedDict[str, StoredUpload] = OrderedDict()
        self._jobs: OrderedDict[str, StoredBatchJob] = OrderedDict()
        self._lookup_cache: OrderedDict[str, BatchResult] = OrderedDict()
        self._lock = RLock()
        self._recovery_lock = Lock()
        self._job_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="eamos-batch-job",
        )
        if self.lookup_service is not None:
            self._recover_orphaned_jobs()

    def bind_lookup_service(self, lookup_service: BatchLookupService | None) -> None:
        if lookup_service is None:
            return
        with self._lock:
            if self.lookup_service is None:
                self.lookup_service = lookup_service
        self._recover_orphaned_jobs()

    def _ensure_lease_store(self) -> BatchLeaseStore | None:
        if self._lease_store_path is None:
            return self._lease_store
        with self._lock:
            if self._lease_store is None:
                self._lease_store = BatchLeaseStore(
                    self._lease_store_path,
                    lease_seconds=self._lease_seconds,
                )
            return self._lease_store

    def store_upload(
        self,
        payload: bytes,
        *,
        filename: str | None = None,
        owner_user_id: str | None = None,
        owner_provider: str | None = None,
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
            variants=parsed.variants,
            staged_vcf=None,
            created_at_monotonic=self._clock(),
            expires_at=self._upload_expires_at(),
            owner_user_id=owner_user_id,
            owner_provider=owner_provider,
            warnings=parsed.warnings,
            skipped_rows=parsed.skipped_rows,
        )
        with self._lock:
            self._uploads[upload_ref] = stored
            self._trim_registry(self._uploads, max_entries=self._max_upload_entries)
        return upload_ref

    def store_upload_file(
        self,
        handle: BinaryIO,
        *,
        filename: str | None = None,
        owner_user_id: str | None = None,
        owner_provider: str | None = None,
        max_compressed_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES,
        max_decompressed_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES * 20,
        max_raw_records: int = DEFAULT_MAX_RAW_RECORDS,
        post_filter_variant_cap: int = BATCH_MAX_VARIANTS,
    ) -> str:
        """Stage a single-use V2 upload while retaining no parsed raw rows."""

        with self._lock:
            self._prune_registries()
        upload_ref = f"batch-upload-{uuid4().hex[:12]}"
        try:
            staged = stage_vcf_file(
                handle,
                staging_dir=self.upload_dir / "uploads",
                filename=filename,
                max_compressed_bytes=max_compressed_bytes,
                max_decompressed_bytes=max_decompressed_bytes,
                max_raw_records=max_raw_records,
                post_filter_variant_cap=post_filter_variant_cap,
            )
        except VcfIngestLimitError as exc:
            if exc.code not in {"vcf_invalid_header", "vcf_sample_columns_required"}:
                raise
            try:
                handle.seek(0)
            except (AttributeError, OSError) as seek_exc:
                raise exc from seek_exc
            payload = handle.read(max_compressed_bytes + 1)
            if len(payload) > max_compressed_bytes:
                raise VcfIngestLimitError(
                    "Uploaded VCF exceeds the configured compressed size limit.",
                    code="vcf_compressed_size_limit_exceeded",
                ) from exc
            return self.store_upload(
                payload,
                filename=filename,
                owner_user_id=owner_user_id,
                owner_provider=owner_provider,
                max_decompressed_bytes=max_decompressed_bytes,
                max_variants=post_filter_variant_cap,
            )
        stored = StoredUpload(
            upload_ref=upload_ref,
            variants=None,
            staged_vcf=staged,
            created_at_monotonic=self._clock(),
            expires_at=self._upload_expires_at(),
            owner_user_id=owner_user_id,
            owner_provider=owner_provider,
            warnings=list(staged.envelope.warnings),
            skipped_rows=0,
        )
        try:
            with self._lock:
                self._uploads[upload_ref] = stored
                self._trim_registry(self._uploads, max_entries=self._max_upload_entries)
        except Exception:
            remove_staged_vcf(staged)
            raise
        return upload_ref

    def upload_response(
        self,
        upload_ref: str,
        *,
        owner_user_id: str | None,
        owner_provider: str | None,
    ):
        with self._lock:
            self._prune_registries()
            upload = self._uploads.get(upload_ref)
            if upload is None or not _owner_matches(
                upload,
                owner_user_id=owner_user_id,
                owner_provider=owner_provider,
            ):
                raise KeyError(upload_ref)
            if upload.staged_vcf is None:
                from app.schemas.batch import BatchUploadResponse

                return BatchUploadResponse(upload_ref=upload_ref)
            from app.schemas.batch import BatchUploadResponse

            return BatchUploadResponse(
                upload_ref=upload_ref,
                expires_at=upload.expires_at,
                single_use=True,
                input_envelope_v2=upload.staged_vcf.envelope,
            )

    def _upload_expires_at(self) -> datetime:
        ttl_seconds = max(1, self._entry_ttl_seconds or BATCH_DEFAULT_REGISTRY_TTL_SECONDS)
        return datetime.now(UTC) + timedelta(seconds=ttl_seconds)

    def create_job(
        self,
        request: BatchCreateRequest,
        *,
        owner_user_id: str | None = None,
        owner_provider: str | None = None,
    ) -> BatchCreateResponse:
        with self._lock:
            self._prune_registries()
            variants, upload, warnings = self._consume_request_source(
                request,
                owner_user_id=owner_user_id,
                owner_provider=owner_provider,
            )
        job_id = f"batch-{uuid4().hex[:12]}"
        input_envelope_v2: BatchInputEnvelopeV2 | None = None
        source_snapshot_v2: BatchSourceSnapshotV2 | None = None
        filter_dispositions_v2: list[BatchFilterDispositionV2] = []
        contexts: list[_V2RowContext | None] = []
        tasks: tuple[_LookupTask, ...] = ()
        if upload is not None and upload.staged_vcf is not None:
            try:
                prepared = self._prepare_v2_job(
                    upload,
                    request=request,
                    upload_ref=upload.upload_ref,
                )
            finally:
                remove_staged_vcf(upload.staged_vcf)
            input_envelope_v2 = prepared.envelope
            source_snapshot_v2 = prepared.snapshot
            filter_dispositions_v2 = list(prepared.filter_dispositions)
            contexts = list(prepared.contexts)
            warnings.extend(prepared.warnings)
            results = list(prepared.results)
            tasks = prepared.tasks
            n_input = prepared.envelope.raw_record_count
            n_to_lookup = prepared.n_to_lookup
            status = prepared.status
            done = prepared.done
            n_after_filters = (
                None if tasks else sum(result.state == "completed" for result in results)
            )
        else:
            legacy_variants = variants or []
            filtered, filter_warnings = self._apply_prelookup_filters(
                legacy_variants, request.filters
            )
            warnings.extend(filter_warnings)
            deduped, dedupe_warnings = _dedupe_variants(
                filtered,
                key_fn=lambda variant: self._variant_identity(variant).variant_key,
            )
            warnings.extend(dedupe_warnings)
            n_input = len(legacy_variants)
            n_to_lookup = len(deduped)
            n_after_filters = len(deduped)
            if self.lookup_service is None:
                results = [
                    self._failed_result_from_variant(
                        variant,
                        "batch_direct_report_lookup_unavailable",
                    )
                    for variant in deduped
                ]
                status = "failed"
                done = len(results)
            else:
                results = [self._queued_result_from_variant(variant) for variant in deduped]
                status = "queued" if results else "completed"
                done = 0
                tasks = tuple(
                    _LookupTask(result_index=index, variant=variant)
                    for index, variant in enumerate(deduped)
                )
            contexts = [None] * len(results)

        est_seconds = round(n_to_lookup * BATCH_EST_SECONDS_PER_LOOKUP, 2)
        job = StoredBatchJob(
            job_id=job_id,
            status=status,
            created_at_monotonic=self._clock(),
            n_input=n_input,
            n_to_lookup=n_to_lookup,
            n_after_filters=n_after_filters,
            est_seconds=est_seconds,
            done=done,
            total=len(results),
            results=results,
            owner_user_id=owner_user_id,
            owner_provider=owner_provider,
            warnings=warnings,
            input_envelope_v2=input_envelope_v2,
            source_snapshot_v2=source_snapshot_v2,
            filter_plan_v2=request.filter_plan_v2,
            filter_dispositions_v2=filter_dispositions_v2,
            v2_contexts=contexts,
        )
        with self._lock:
            self._jobs[job_id] = job
            self._trim_registry(self._jobs, max_entries=self._max_job_entries)
        lease_registered = False
        try:
            if (
                tasks
                and self.workflow_service is not None
                and job.owner_user_id is not None
                and job.owner_provider is not None
            ):
                lease_store = self._ensure_lease_store()
                if lease_store is None:  # pragma: no cover - workflow path guarantees one
                    raise RuntimeError("Batch lease store is unavailable.")
                lease_store.enqueue(
                    job_id=job.job_id,
                    owner_user_id=job.owner_user_id,
                    owner_provider=job.owner_provider,
                )
                lease_registered = True
            self._create_durable_job(job)
        except Exception as exc:
            if lease_registered and self._lease_store is not None:
                self._lease_store.delete(job.job_id)
            with self._lock:
                self._jobs.pop(job_id, None)
            raise BatchQueueUnavailable("Durable Batch job registration is unavailable.") from exc
        if tasks:
            try:
                self._start_background_job(job_id, tasks)
            except Exception as exc:
                with self._lock:
                    job.status = "failed"
                    job.warnings.append("batch_queue_reservation_unavailable")
                    self._persist_job(job)
                if self._lease_store is not None:
                    self._lease_store.finish(job_id, state="failed")
                raise BatchQueueUnavailable(
                    "Durable Batch worker reservation is unavailable."
                ) from exc
        return BatchCreateResponse(
            job_id=job_id,
            n_input=job.n_input,
            n_to_lookup=job.n_to_lookup,
            est_seconds=job.est_seconds,
            input_envelope_v2=job.input_envelope_v2,
            source_snapshot_v2=job.source_snapshot_v2,
        )

    def get_job(
        self,
        job_id: str,
        *,
        limit: int,
        cursor: str | None = None,
        source_snapshot_id: str | None = None,
        owner_user_id: str | None = None,
        owner_provider: str | None = None,
    ) -> BatchJob | None:
        with self._lock:
            self._prune_registries()
            job = self._jobs.get(job_id)
            if job is None:
                return self._durable_job(
                    job_id,
                    limit=limit,
                    cursor=cursor,
                    source_snapshot_id=source_snapshot_id,
                    owner_user_id=owner_user_id,
                    owner_provider=owner_provider,
                )
            if not _owner_matches(
                job,
                owner_user_id=owner_user_id,
                owner_provider=owner_provider,
            ):
                return None
            self._jobs.move_to_end(job_id)
            snapshot = job.source_snapshot_v2
            if snapshot is not None:
                if source_snapshot_id is not None and source_snapshot_id != snapshot.snapshot_id:
                    raise ValueError("requested source snapshot does not match the batch job")
                offset = self._cursor_codec.decode(cursor, snapshot_id=snapshot.snapshot_id)
            else:
                offset = _cursor_offset(cursor)
            page_results = job.results[offset : offset + limit]
            next_offset = offset + len(page_results)
            has_more = next_offset < len(job.results)
            if has_more and snapshot is not None:
                next_cursor = self._cursor_codec.encode(
                    snapshot_id=snapshot.snapshot_id,
                    offset=next_offset,
                )
            else:
                next_cursor = str(next_offset) if has_more else None
            paging_v2 = (
                BatchPagingV2(
                    snapshot_id=snapshot.snapshot_id,
                    limit=limit,
                    next_cursor=next_cursor,
                    total=len(job.results),
                    has_more=has_more,
                )
                if snapshot is not None
                else None
            )
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
                page=BatchPage(
                    limit=limit,
                    next_cursor=next_cursor,
                    total=len(job.results),
                    paging_v2=paging_v2,
                ),
                warnings=list(job.warnings),
                input_envelope_v2=job.input_envelope_v2,
                source_snapshot_v2=job.source_snapshot_v2,
                filter_dispositions_v2=list(job.filter_dispositions_v2),
            )

    def _consume_request_source(
        self,
        request: BatchCreateRequest,
        *,
        owner_user_id: str | None = None,
        owner_provider: str | None = None,
    ) -> tuple[list[ParsedVariant] | None, StoredUpload | None, list[str]]:
        if request.variants is not None:
            return list(request.variants), None, []
        upload = self._uploads.get(request.upload_ref or "")
        if upload is None or not _owner_matches(
            upload,
            owner_user_id=owner_user_id,
            owner_provider=owner_provider,
        ):
            raise KeyError(request.upload_ref or "")
        self._uploads.pop(request.upload_ref or "", None)
        warnings = list(upload.warnings)
        if upload.skipped_rows:
            warnings.append(f"upload_skipped_rows:{upload.skipped_rows}")
        if upload.staged_vcf is not None:
            return None, upload, warnings
        return list(upload.variants or []), upload, warnings

    def _prepare_v2_job(
        self,
        upload: StoredUpload,
        *,
        request: BatchCreateRequest,
        upload_ref: str,
    ) -> _PreparedV2Job:
        staged = upload.staged_vcf
        if staged is None:
            raise ValueError("V2 preparation requires a staged upload")
        intervals, interval_capability, interval_requirement = self._v2_interval_setup(request)
        snapshot = build_source_snapshot(
            envelope=staged.envelope,
            normalizer=self.normalizer,
            lookup_ready=self.lookup_service is not None,
            interval_capability=interval_capability,
        )
        normalizer_disclosure = self.normalizer.disclosure()
        if normalizer_disclosure.execution == "unavailable":
            requirement = "; ".join(normalizer_disclosure.requirements)
            disposition = BatchFilterDispositionV2(
                stage="pre_annotation",
                outcome="deferred",
                reason="source_unavailable",
                detail=requirement,
                source_snapshot_id=snapshot.snapshot_id,
            )
            return _PreparedV2Job(
                envelope=staged.envelope,
                snapshot=snapshot,
                tasks=(),
                results=(),
                contexts=(),
                filter_dispositions=(disposition,),
                warnings=(f"batch_normalization_unavailable:{requirement}",),
                n_to_lookup=0,
                status="failed",
                done=0,
            )

        cap = staged.envelope.post_filter_variant_cap
        stats = BatchPreFilterStats()
        normalized: OrderedDict[
            str,
            tuple[ParsedVariant, BatchAlleleIdentityV2, tuple[BatchSampleProvenanceV2, ...]],
        ] = OrderedDict()
        failed_rows: list[
            tuple[
                ParsedVariant,
                BatchAlleleIdentityV2 | None,
                tuple[BatchSampleProvenanceV2, ...],
                str,
            ]
        ] = []
        normalized_duplicate_count = 0
        annotation_cap_count = 0
        normalization_failed_count = 0
        try:
            stream = iter_pre_annotation(
                iter_staged_variants(staged, upload_ref=upload_ref),
                legacy_filters=request.filters,
                filter_plan=request.filter_plan_v2,
                panel_intervals=intervals,
                stats=stats,
                deadline_monotonic=self._clock() + self._max_prepare_seconds,
                clock=self._clock,
            )
            for streamed in stream:
                try:
                    identity = self.normalizer.normalize(
                        streamed.original_allele,
                        source_record_index=streamed.source_record_index,
                    )
                except BatchNormalizationUnavailable as exc:
                    requirement = "; ".join(exc.requirements)
                    raise BatchFilterUnavailable(requirement) from exc
                except BatchNormalizationFailed:
                    identity = None
                    warning = "batch_normalization_failed"
                else:
                    warning = (
                        f"batch_normalization_{identity.status}"
                        if identity.status != "normalized" or identity.normalized is None
                        else ""
                    )
                if warning:
                    normalization_failed_count += 1
                    if len(failed_rows) < cap:
                        failed_rows.append((streamed.variant, identity, streamed.samples, warning))
                    continue
                allele = identity.normalized
                if allele is None:  # guarded by the status check above
                    raise ValueError("normalized Batch allele is missing")
                variant = streamed.variant.model_copy(
                    update={
                        "query": _allele_key(allele),
                        "chrom": allele.chromosome,
                        "pos": allele.position,
                        "ref": allele.reference,
                        "alt": allele.alternate,
                    }
                )
                key = variant.query
                if key in normalized:
                    prior_variant, prior_identity, prior_samples = normalized[key]
                    samples = {item.source_sample_index: item for item in prior_samples}
                    for item in streamed.samples:
                        samples.setdefault(item.source_sample_index, item)
                    normalized[key] = (
                        _merge_variant_metadata(prior_variant, variant),
                        prior_identity,
                        tuple(samples[index] for index in sorted(samples)),
                    )
                    normalized_duplicate_count += 1
                    continue
                if len(normalized) >= cap:
                    annotation_cap_count += 1
                    continue
                normalized[key] = (variant, identity, streamed.samples)
        except BatchFilterUnavailable as exc:
            requirement = interval_requirement or exc.requirement
            disposition = BatchFilterDispositionV2(
                stage="pre_annotation",
                outcome="deferred",
                reason="source_unavailable",
                detail=requirement,
                source_snapshot_id=snapshot.snapshot_id,
            )
            return _PreparedV2Job(
                envelope=staged.envelope,
                snapshot=snapshot,
                tasks=(),
                results=(),
                contexts=(),
                filter_dispositions=(disposition,),
                warnings=(f"batch_filter_unavailable:{requirement}",),
                n_to_lookup=0,
                status="failed",
                done=0,
            )
        except BatchResourceLimitExceeded:
            return _PreparedV2Job(
                envelope=staged.envelope,
                snapshot=snapshot,
                tasks=(),
                results=(),
                contexts=(),
                filter_dispositions=(),
                warnings=(f"batch_processing_time_limit_exceeded:{self._max_prepare_seconds:g}s",),
                n_to_lookup=0,
                status="failed",
                done=0,
            )

        dispositions = stats.dispositions(
            source_snapshot_id=snapshot.snapshot_id,
            normalized_retained_count=len(normalized),
            normalized_duplicate_count=normalized_duplicate_count,
            annotation_cap_count=annotation_cap_count,
        )
        included_dispositions = tuple(item for item in dispositions if item.outcome == "included")
        warnings = [
            f"raw_records_scanned:{staged.envelope.raw_record_count}",
            f"split_alleles_scanned:{stats.allele_count}",
            f"pre_annotation_excluded:{sum(stats.counts.values())}",
        ]
        if normalized_duplicate_count:
            warnings.extend(
                [
                    "normalized_duplicate_collapsed",
                    f"normalized_duplicates:{normalized_duplicate_count}",
                ]
            )
        if annotation_cap_count:
            warnings.append(f"post_filter_annotation_cap_excluded:{annotation_cap_count}")
        if normalization_failed_count:
            warnings.append(f"normalization_failed_rows:{normalization_failed_count}")

        results: list[BatchResult] = []
        contexts: list[_V2RowContext | None] = []
        tasks: list[_LookupTask] = []
        for variant, identity, samples in normalized.values():
            context = _V2RowContext(
                allele_identity=identity,
                samples=samples,
                filter_dispositions=included_dispositions,
            )
            result_index = len(results)
            if self.lookup_service is None:
                result = self._failed_v2_result(
                    variant,
                    snapshot=snapshot,
                    context=context,
                    warning="batch_direct_report_lookup_unavailable",
                )
            else:
                result = self._queued_v2_result(
                    variant,
                    snapshot=snapshot,
                    context=context,
                )
                tasks.append(
                    _LookupTask(
                        result_index=result_index,
                        variant=variant,
                        v2_context=context,
                    )
                )
            results.append(result)
            contexts.append(context)
        remaining_failure_slots = max(0, cap - len(results))
        for variant, identity, samples, warning in failed_rows[:remaining_failure_slots]:
            context = _V2RowContext(
                allele_identity=identity,
                samples=samples,
                filter_dispositions=included_dispositions,
            )
            result = self._failed_v2_result(
                variant,
                snapshot=snapshot,
                context=context,
                warning=warning,
            )
            results.append(result)
            contexts.append(context)
        if tasks:
            status = "queued"
        elif results and any(result.state == "failed" for result in results):
            status = "failed"
        else:
            status = "completed"
        done = sum(result.state != "lookup_pending" for result in results)
        return _PreparedV2Job(
            envelope=staged.envelope,
            snapshot=snapshot,
            tasks=tuple(tasks),
            results=tuple(results),
            contexts=tuple(contexts),
            filter_dispositions=dispositions,
            warnings=tuple(dict.fromkeys(warnings)),
            n_to_lookup=len(tasks),
            status=status,
            done=done,
        )

    def _v2_interval_setup(
        self,
        request: BatchCreateRequest,
    ) -> tuple[
        tuple[GenomicInterval, ...] | None,
        CapabilityExecutionDisclosureV2 | None,
        str | None,
    ]:
        filter_plan = request.filter_plan_v2
        needs_intervals = bool(request.filters.panel_slug) or (
            filter_plan is not None and filter_plan.interval_scope != "capture_bed"
        )
        if filter_plan is not None and filter_plan.interval_scope == "capture_bed":
            requirement = "resolve interval_snapshot_id through the server-side validated capture-BED registry"
            return None, unavailable_interval_capability(requirement), requirement
        if not needs_intervals:
            return None, None, None
        panel = self.panel_service.get_panel(request.filters.panel_slug or "")
        if panel is None:
            requirement = "select a source-backed panel snapshot available to this deployment"
            return None, unavailable_interval_capability(requirement), requirement
        panel_snapshot = panel.source_snapshot_v2
        requested_panel_snapshot = (
            filter_plan.panel_snapshot_id if filter_plan is not None else None
        )
        if (
            panel_snapshot is None
            or panel_snapshot.launch_posture != "ready"
            or requested_panel_snapshot != panel_snapshot.snapshot_id
        ):
            requirement = (
                "select the exact ready source-backed panel snapshot from the server catalog"
            )
            return None, unavailable_interval_capability(requirement), requirement
        if self.panel_interval_index is None:
            requirement = "mount the checksum-verified MANE coordinate interval artifact"
            return None, unavailable_interval_capability(requirement), requirement
        try:
            inspection = self.panel_interval_index.inspection(verify_checksum=True)
        except Exception:
            inspection = None
        if (
            inspection is None
            or not inspection.ready
            or not inspection.checksum_verified
            or not inspection.actual_sha256
        ):
            requirement = "pass the MANE interval artifact checksum and functional preflight"
            return None, unavailable_interval_capability(requirement), requirement
        intervals: list[GenomicInterval] = []
        interval_scope = filter_plan.interval_scope if filter_plan is not None else "whole_gene"
        for gene in panel.genes:
            transcript = self.panel_interval_index.transcript(gene=gene.symbol)
            if transcript is None:
                continue
            if interval_scope == "mane_exon_splice":
                for exon in transcript.exons:
                    start = min(exon.genomic_start, exon.genomic_end)
                    end = max(exon.genomic_start, exon.genomic_end)
                    intervals.append(
                        GenomicInterval(
                            chromosome=transcript.chrom,
                            start=max(1, start - self._panel_splice_flank_bp),
                            end=end + self._panel_splice_flank_bp,
                        )
                    )
                continue
            bounds = [
                coordinate
                for exon in transcript.exons
                for coordinate in (exon.genomic_start, exon.genomic_end)
            ]
            start = transcript.gene_start or (min(bounds) if bounds else None)
            end = transcript.gene_end or (max(bounds) if bounds else None)
            if start is not None and end is not None:
                intervals.append(
                    GenomicInterval(
                        chromosome=transcript.chrom,
                        start=min(start, end),
                        end=max(start, end),
                    )
                )
        if not intervals:
            requirement = "materialize intervals for every selected panel gene"
            return None, unavailable_interval_capability(requirement), requirement
        return (
            tuple(intervals),
            mounted_interval_capability(
                manifest_id=inspection.artifact_version or "eamos-coordinate-index",
                artifact_sha256=inspection.actual_sha256,
                source_release=inspection.artifact_version or "unknown",
                validation_matrix_id="batch-panel-intervals-v1",
            ),
            None,
        )

    def _queued_v2_result(
        self,
        variant: ParsedVariant,
        *,
        snapshot: BatchSourceSnapshotV2,
        context: _V2RowContext,
    ) -> BatchResult:
        return BatchResult(
            variant_key=variant.query,
            state="lookup_pending",
            gene=variant.gene,
            hgvs_c=variant.variant if (variant.variant or "").startswith("c.") else None,
            predictor_ensemble={},
            warnings=list(variant.warnings),
            allele_identity_v2=context.allele_identity,
            source_snapshot_id=snapshot.snapshot_id,
            filter_dispositions_v2=list(context.filter_dispositions),
            sample_provenance_v2=list(context.samples),
        )

    def _failed_v2_result(
        self,
        variant: ParsedVariant,
        *,
        snapshot: BatchSourceSnapshotV2,
        context: _V2RowContext,
        warning: str,
    ) -> BatchResult:
        return BatchResult(
            variant_key=variant.query,
            state="failed",
            gene=variant.gene,
            hgvs_c=variant.variant if (variant.variant or "").startswith("c.") else None,
            predictor_ensemble={},
            warnings=list(dict.fromkeys([*variant.warnings, warning])),
            allele_identity_v2=context.allele_identity,
            source_snapshot_id=snapshot.snapshot_id,
            filter_dispositions_v2=list(context.filter_dispositions),
            sample_provenance_v2=list(context.samples),
        )

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
            candidate = registry.get(key)
            if isinstance(candidate, StoredBatchJob) and candidate.status in {"queued", "running"}:
                continue
            removed = registry.pop(key, None)
            if isinstance(removed, StoredUpload):
                remove_staged_vcf(removed.staged_vcf)

    @staticmethod
    def _trim_registry(
        registry: OrderedDict[str, StoredUpload] | OrderedDict[str, StoredBatchJob],
        *,
        max_entries: int,
    ) -> None:
        while len(registry) > max_entries:
            removable_key = next(
                (
                    key
                    for key, value in registry.items()
                    if not isinstance(value, StoredBatchJob)
                    or value.status not in {"queued", "running"}
                ),
                None,
            )
            if removable_key is None:
                return
            removed = registry.pop(removable_key)
            if isinstance(removed, StoredUpload):
                remove_staged_vcf(removed.staged_vcf)

    def _queued_result_from_variant(self, variant: ParsedVariant) -> BatchResult:
        identity = self._variant_identity(variant)
        return BatchResult(
            variant_key=identity.variant_key,
            state="lookup_pending",
            gene=variant.gene,
            hgvs_c=variant.variant if (variant.variant or "").startswith("c.") else None,
            hgvs_p=None,
            clinvar_verdict=None,
            gnomad_af=None,
            predictor_ensemble={},
            acmg_classification=None,
            report_href=_report_href(
                variant.gene,
                variant.variant if (variant.variant or "").startswith("c.") else None,
            ),
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

    def _start_background_job(
        self,
        job_id: str,
        tasks: tuple[_LookupTask, ...],
        *,
        reserve_lease: bool = True,
    ) -> None:
        if self._lease_store is not None and reserve_lease:
            if not self._lease_store.reserve(job_id):
                raise RuntimeError("Batch job could not reserve its durable worker lease.")
        self._job_executor.submit(self._run_lookup_job, job_id, tasks)

    def _run_lookup_job(self, job_id: str, tasks: tuple[_LookupTask, ...]) -> None:
        lease_managed = self._lease_store is not None and self._lease_store.get(job_id) is not None
        if lease_managed:
            if self._lease_store.claim(job_id) is None:
                return
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                if self._lease_store is not None:
                    self._lease_store.finish(job_id, state="failed")
                return
            if job.status == "cancelled":
                return
            job.status = "running"
            self._persist_job(job)

        try:
            executor = ThreadPoolExecutor(max_workers=self._max_lookup_workers)
            cancelled = False
            next_lease_renewal = monotonic() + (
                max(1.0, self._lease_store.lease_seconds / 3) if lease_managed else 3600.0
            )
            try:
                pending = {
                    executor.submit(self._lookup_result_for_task, job_id, task): task
                    for task in tasks
                }
                while pending:
                    if lease_managed and monotonic() >= next_lease_renewal:
                        if not self._lease_store.renew(job_id):
                            raise RuntimeError("Batch worker lost its durable lease.")
                        next_lease_renewal = monotonic() + max(
                            1.0,
                            self._lease_store.lease_seconds / 3,
                        )
                    if self._job_is_cancelled(job_id):
                        cancelled = True
                        for future in pending:
                            future.cancel()
                        break
                    completed, _waiting = wait(
                        tuple(pending),
                        timeout=0.05,
                        return_when=FIRST_COMPLETED,
                    )
                    for future in completed:
                        task = pending.pop(future)
                        try:
                            result = future.result()
                        except Exception as exc:
                            result = self._failed_result_for_task(
                                job_id,
                                task,
                                f"batch_lookup_failed:{type(exc).__name__}",
                            )
                        self._record_lookup_result(job_id, task.result_index, result)
                        if lease_managed and not self._lease_store.renew(job_id):
                            raise RuntimeError("Batch worker lost its durable lease.")
                        if lease_managed:
                            next_lease_renewal = monotonic() + max(
                                1.0,
                                self._lease_store.lease_seconds / 3,
                            )
            finally:
                executor.shutdown(wait=not cancelled, cancel_futures=cancelled)
            if cancelled:
                return
            self._finish_lookup_job(job_id)
        except Exception as exc:
            with self._lock:
                job = self._jobs.get(job_id)
                if job is not None:
                    job.status = "failed"
                    job.warnings.append(f"batch_job_failed:{type(exc).__name__}")
                    self._persist_job(job)
            if self._lease_store is not None:
                self._lease_store.finish(job_id, state="failed")

    def _lookup_result_for_task(self, job_id: str, task: _LookupTask) -> BatchResult:
        if task.v2_context is None:
            return self._lookup_result_for_variant(task.variant)
        with self._lock:
            job = self._jobs.get(job_id)
            snapshot = job.source_snapshot_v2 if job is not None else None
            filter_plan = job.filter_plan_v2 if job is not None else None
        if snapshot is None:
            raise ValueError("V2 lookup task lost its source snapshot")
        return self._lookup_v2_result(
            job_id,
            task.variant,
            context=task.v2_context,
            snapshot=snapshot,
            filter_plan=filter_plan,
        )

    def _failed_result_for_task(
        self,
        job_id: str,
        task: _LookupTask,
        warning: str,
    ) -> BatchResult:
        if task.v2_context is None:
            return self._failed_result_from_variant(task.variant, warning)
        with self._lock:
            job = self._jobs.get(job_id)
            snapshot = job.source_snapshot_v2 if job is not None else None
        if snapshot is None:
            return self._failed_result_from_variant(task.variant, warning)
        return self._failed_v2_result(
            task.variant,
            snapshot=snapshot,
            context=task.v2_context,
            warning=warning,
        )

    def _job_is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return job is None or job.status == "cancelled"

    def _lookup_result_for_variant(self, variant: ParsedVariant) -> BatchResult:
        identity = self._variant_identity(variant)
        with self._lock:
            cached = self._lookup_cache.get(identity.variant_key)
            if cached is not None:
                self._lookup_cache.move_to_end(identity.variant_key)
                return cached.model_copy(deep=True)

        lookup_service = self.lookup_service
        if lookup_service is None:
            return self._failed_result_from_variant(
                variant,
                "batch_direct_report_lookup_unavailable",
            )

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
        if result.state == "completed":
            with self._lock:
                self._lookup_cache[identity.variant_key] = result.model_copy(deep=True)
                self._trim_registry(
                    self._lookup_cache,
                    max_entries=BATCH_LOOKUP_CACHE_MAX_ENTRIES,
                )
        return result

    def _lookup_v2_result(
        self,
        job_id: str,
        variant: ParsedVariant,
        *,
        context: _V2RowContext,
        snapshot: BatchSourceSnapshotV2,
        filter_plan: BatchFilterPlanV2 | None,
    ) -> BatchResult:
        lookup_service = self.lookup_service
        if lookup_service is None:
            return self._failed_v2_result(
                variant,
                snapshot=snapshot,
                context=context,
                warning="batch_direct_report_lookup_unavailable",
            )
        try:
            response = lookup_service.lookup(_lookup_request_from_variant(variant), refresh=False)
        except Exception as exc:
            return self._failed_v2_result(
                variant,
                snapshot=snapshot,
                context=context,
                warning=f"batch_lookup_failed:{type(exc).__name__}",
            )
        try:
            report_snapshot_id = self._bind_direct_report_snapshot(job_id, response)
            result = _batch_v2_result_from_lookup_response(
                variant=variant,
                response=response,
                context=context,
                source_snapshot_id=snapshot.snapshot_id,
            )
            result = result.model_copy(
                update={
                    "warnings": list(
                        dict.fromkeys(
                            [
                                *result.warnings,
                                f"direct_report_source_snapshot:{report_snapshot_id}",
                            ]
                        )
                    )
                },
                deep=True,
            )
            result, post_dispositions = filter_post_annotation(
                result,
                filter_plan=filter_plan,
                source_snapshot_id=snapshot.snapshot_id,
            )
            if post_dispositions:
                result = result.model_copy(
                    update={
                        "filter_dispositions_v2": [
                            *result.filter_dispositions_v2,
                            *post_dispositions,
                        ]
                    },
                    deep=True,
                )
            return result
        except Exception:
            return self._failed_v2_result(
                variant,
                snapshot=snapshot,
                context=context,
                warning="batch_report_v2_contract_mismatch",
            )

    def _bind_direct_report_snapshot(self, job_id: str, response) -> str:
        execution_state = getattr(response, "execution_state_v2", None)
        report_snapshot_id = getattr(execution_state, "source_snapshot_id", None)
        if not report_snapshot_id:
            raise ValueError("direct Report lookup omitted its source snapshot")
        section_snapshot_ids = {section.source_snapshot_id for section in execution_state.sections}
        if section_snapshot_ids != {report_snapshot_id}:
            raise ValueError("direct Report sections do not share one source snapshot")
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ValueError("Batch job is unavailable while binding Report snapshot")
            expected = job.direct_report_source_snapshot_id
            if expected is None:
                job.direct_report_source_snapshot_id = report_snapshot_id
            elif expected != report_snapshot_id:
                raise ValueError("direct Report source snapshot changed within the Batch job")
        return report_snapshot_id

    def _failed_result_from_variant(self, variant: ParsedVariant, warning: str) -> BatchResult:
        identity = self._variant_identity(variant)
        return BatchResult(
            variant_key=identity.variant_key,
            state="failed",
            gene=variant.gene,
            hgvs_c=variant.variant if (variant.variant or "").startswith("c.") else None,
            hgvs_p=None,
            clinvar_verdict=None,
            gnomad_af=None,
            predictor_ensemble={},
            acmg_classification=None,
            report_href=_report_href(
                variant.gene,
                variant.variant if (variant.variant or "").startswith("c.") else None,
            ),
            warnings=list(dict.fromkeys([*identity.warnings, warning])),
        )

    def _record_lookup_result(self, job_id: str, index: int, result: BatchResult) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status == "cancelled" or index >= len(job.results):
                return
            job.results[index] = result
            job.done = min(job.total, job.done + 1)
            self._persist_job(job)

    def _finish_lookup_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if job.status == "cancelled":
                self._persist_job(job)
                return
            any_success = any(
                result.state in {"completed", "filtered_post_lookup"} for result in job.results
            )
            job.n_after_filters = sum(result.state == "completed" for result in job.results)
            job.status = "completed" if any_success or job.total == 0 else "failed"
            self._persist_job(job)
            if self._lease_store is not None:
                self._lease_store.finish(
                    job_id,
                    state="completed" if job.status == "completed" else "failed",
                )

    def _recover_orphaned_jobs(self) -> None:
        if (
            self._lease_store is None
            or self.workflow_service is None
            or self.lookup_service is None
            or not self._recovery_lock.acquire(blocking=False)
        ):
            return
        try:
            for lease in self._lease_store.orphaned():
                try:
                    self._restore_orphaned_job(lease)
                except Exception:
                    self._mark_recovery_failed(lease, "batch_restart_recovery_state_invalid")
        finally:
            self._recovery_lock.release()

    def _restore_orphaned_job(self, lease: BatchLease) -> None:
        workflow = self.workflow_service
        if workflow is None:
            return
        record = workflow.get_record(
            run_id=lease.job_id,
            user_id=lease.owner_user_id,
            owner_provider=lease.owner_provider,
        )
        if record is None or record.kind != "batch":
            self._lease_store.delete(lease.job_id)
            return
        if record.status in {"completed", "failed", "cancelled", "expired"}:
            terminal = (
                "cancelled"
                if record.status == "cancelled"
                else ("completed" if record.status == "completed" else "failed")
            )
            self._lease_store.finish(lease.job_id, state=terminal)
            return

        results = self._load_durable_results(lease)
        payload = record.result_payload or {}
        envelope_payload = payload.get("input_envelope_v2")
        snapshot_payload = payload.get("source_snapshot_v2")
        filter_plan_payload = payload.get("filter_plan_v2")
        dispositions_payload = payload.get("filter_dispositions_v2") or []
        envelope = (
            BatchInputEnvelopeV2.model_validate(envelope_payload)
            if envelope_payload is not None
            else None
        )
        snapshot = (
            BatchSourceSnapshotV2.model_validate(snapshot_payload)
            if snapshot_payload is not None
            else None
        )
        if (envelope is None) != (snapshot is None):
            raise ValueError("Batch restart state has an incomplete V2 snapshot.")
        filter_plan = (
            BatchFilterPlanV2.model_validate(filter_plan_payload)
            if filter_plan_payload is not None
            else None
        )
        dispositions = [
            BatchFilterDispositionV2.model_validate(item) for item in dispositions_payload
        ]

        tasks: list[_LookupTask] = []
        contexts: list[_V2RowContext | None] = []
        restored_results: list[BatchResult] = []
        for index, result in enumerate(results):
            context = (
                _V2RowContext(
                    allele_identity=result.allele_identity_v2,
                    samples=tuple(result.sample_provenance_v2),
                    filter_dispositions=tuple(result.filter_dispositions_v2),
                )
                if snapshot is not None
                else None
            )
            if result.state in {"queued", "lookup_pending", "running"}:
                variant = self._restart_variant(result, snapshot=snapshot)
                result = result.model_copy(update={"state": "lookup_pending"}, deep=True)
                tasks.append(
                    _LookupTask(
                        result_index=index,
                        variant=variant,
                        v2_context=context,
                    )
                )
            restored_results.append(result)
            contexts.append(context)

        warnings = list(dict.fromkeys([*record.warnings, "batch_job_recovered_after_restart"]))
        done = sum(
            result.state not in {"queued", "lookup_pending", "running"}
            for result in restored_results
        )
        job = StoredBatchJob(
            job_id=record.run_id,
            status="queued" if tasks else record.status,
            created_at_monotonic=self._clock(),
            n_input=record.n_input or len(restored_results),
            n_to_lookup=record.n_to_lookup or len(tasks),
            n_after_filters=payload.get("n_after_filters", record.n_after_filters),
            est_seconds=record.est_seconds or 0.0,
            done=done,
            total=len(restored_results),
            results=restored_results,
            owner_user_id=lease.owner_user_id,
            owner_provider=lease.owner_provider,
            warnings=warnings,
            input_envelope_v2=envelope,
            source_snapshot_v2=snapshot,
            filter_plan_v2=filter_plan,
            filter_dispositions_v2=dispositions,
            v2_contexts=contexts,
            direct_report_source_snapshot_id=payload.get("direct_report_source_snapshot_id"),
        )
        with self._lock:
            self._jobs[job.job_id] = job
            self._trim_registry(self._jobs, max_entries=self._max_job_entries)
        if not tasks:
            self._finish_lookup_job(job.job_id)
            return
        self._persist_job(job)
        self._start_background_job(job.job_id, tuple(tasks), reserve_lease=False)

    def _load_durable_results(self, lease: BatchLease) -> list[BatchResult]:
        workflow = self.workflow_service
        if workflow is None:
            return []
        cursor: str | None = None
        results: list[BatchResult] = []
        while len(results) <= BATCH_MAX_VARIANTS:
            page = workflow.page_items(
                run_id=lease.job_id,
                user_id=lease.owner_user_id,
                owner_provider=lease.owner_provider,
                limit=min(500, BATCH_MAX_VARIANTS + 1 - len(results)),
                cursor=cursor,
            )
            if page is None:
                raise ValueError("Batch restart state lost its durable result rows.")
            items, cursor, total = page
            results.extend(BatchResult.model_validate(item) for item in items)
            if not cursor:
                if total != len(results):
                    raise ValueError("Batch restart result count is inconsistent.")
                return results
        raise ValueError("Batch restart state exceeds the post-filter result cap.")

    @staticmethod
    def _restart_variant(
        result: BatchResult,
        *,
        snapshot: BatchSourceSnapshotV2 | None,
    ) -> ParsedVariant:
        if snapshot is not None:
            identity = result.allele_identity_v2
            if identity is None or identity.status != "normalized" or identity.normalized is None:
                raise ValueError("Batch V2 restart requires a normalized pending allele.")
            allele = identity.normalized
            if result.source_snapshot_id != snapshot.snapshot_id:
                raise ValueError("Batch V2 restart row has a mismatched source snapshot.")
            return ParsedVariant(
                raw=None,
                query=_allele_key(allele),
                gene=result.gene,
                variant=result.hgvs_c,
                chrom=allele.chromosome,
                pos=allele.position,
                ref=allele.reference,
                alt=allele.alternate,
                warnings=list(result.warnings),
            )
        coordinate = result.variant_key.split("-", 3)
        coordinate_fields: dict[str, Any] = {}
        if len(coordinate) == 4:
            try:
                coordinate_fields = {
                    "chrom": coordinate[0],
                    "pos": int(coordinate[1]),
                    "ref": coordinate[2],
                    "alt": coordinate[3],
                }
            except ValueError:
                coordinate_fields = {}
        return ParsedVariant(
            query=result.variant_key,
            gene=result.gene,
            variant=result.hgvs_c,
            warnings=list(result.warnings),
            **coordinate_fields,
        )

    def _mark_recovery_failed(self, lease: BatchLease, warning: str) -> None:
        workflow = self.workflow_service
        if workflow is not None:
            record = workflow.get_record(
                run_id=lease.job_id,
                user_id=lease.owner_user_id,
                owner_provider=lease.owner_provider,
            )
            if record is not None and record.kind == "batch":
                workflow.update_run(
                    run_id=lease.job_id,
                    user_id=lease.owner_user_id,
                    owner_provider=lease.owner_provider,
                    status="failed",
                    warnings=list(dict.fromkeys([*record.warnings, warning])),
                )
        if self._lease_store is not None:
            self._lease_store.finish(lease.job_id, state="failed")

    def cancel_job(
        self,
        job_id: str,
        *,
        owner_user_id: str,
        owner_provider: str,
    ):
        workflow = self.workflow_service
        if workflow is None:
            return None
        with self._lock:
            record = workflow.get_record(
                run_id=job_id,
                user_id=owner_user_id,
                owner_provider=owner_provider,
            )
            if record is None or record.kind != "batch":
                return None
            run = workflow.cancel_run(
                run_id=job_id,
                user_id=owner_user_id,
                owner_provider=owner_provider,
            )
            if run is None:
                return None
            job = self._jobs.get(job_id)
            if job is not None and _owner_matches(
                job,
                owner_user_id=owner_user_id,
                owner_provider=owner_provider,
            ):
                job.status = "cancelled"
        if self._lease_store is not None:
            self._lease_store.finish(job_id, state="cancelled")
        return run

    def delete_job(
        self,
        job_id: str,
        *,
        owner_user_id: str,
        owner_provider: str,
    ) -> bool:
        workflow = self.workflow_service
        if workflow is None:
            return False
        record = workflow.get_record(
            run_id=job_id,
            user_id=owner_user_id,
            owner_provider=owner_provider,
        )
        if record is None or record.kind != "batch":
            return False
        deleted = workflow.delete_run(
            run_id=job_id,
            user_id=owner_user_id,
            owner_provider=owner_provider,
        )
        if deleted:
            with self._lock:
                self._jobs.pop(job_id, None)
            if self._lease_store is not None:
                self._lease_store.delete(job_id)
        return deleted

    def _create_durable_job(self, job: StoredBatchJob) -> None:
        if self.workflow_service is None or job.owner_user_id is None or job.owner_provider is None:
            return
        self.workflow_service.create_run(
            kind="batch",
            run_id=job.job_id,
            user_id=job.owner_user_id,
            owner_provider=job.owner_provider,
            status=job.status,
            done=job.done,
            total=job.total,
            warnings=job.warnings,
            processing_disclosure={
                "execution": "eamos_backend",
                "provider_id": "eamos_batch",
                "provider_label": "Eamos batch processor",
                "input_classes": ["vcf" if job.input_envelope_v2 is not None else "variant_id"],
                "raw_input_persisted": False,
                "retention": "account_saved",
                "expires_at": None,
                "user_deletable": True,
                "consent_required": False,
                "warnings": [
                    "Normalized result rows are retained in the owner account until deletion."
                ],
            },
            result_payload=self._durable_runtime_payload(job),
            items=[result.model_dump(mode="json") for result in job.results],
            n_input=job.n_input,
            n_to_lookup=job.n_to_lookup,
            n_after_filters=job.n_after_filters,
            est_seconds=job.est_seconds,
        )

    def _persist_job(self, job: StoredBatchJob) -> None:
        if self.workflow_service is None or job.owner_user_id is None or job.owner_provider is None:
            return
        self.workflow_service.update_run(
            run_id=job.job_id,
            user_id=job.owner_user_id,
            owner_provider=job.owner_provider,
            status=job.status,
            done=job.done,
            total=job.total,
            warnings=list(job.warnings),
            result_payload=self._durable_runtime_payload(job),
            items=[result.model_dump(mode="json") for result in job.results],
        )

    @staticmethod
    def _durable_runtime_payload(job: StoredBatchJob) -> dict[str, Any]:
        return {
            "schema_version": "batch_runtime_state.v2",
            "input_envelope_v2": (
                job.input_envelope_v2.model_dump(mode="json")
                if job.input_envelope_v2 is not None
                else None
            ),
            "source_snapshot_v2": (
                job.source_snapshot_v2.model_dump(mode="json")
                if job.source_snapshot_v2 is not None
                else None
            ),
            "filter_plan_v2": (
                job.filter_plan_v2.model_dump(mode="json")
                if job.filter_plan_v2 is not None
                else None
            ),
            "filter_dispositions_v2": [
                item.model_dump(mode="json") for item in job.filter_dispositions_v2
            ],
            "n_after_filters": job.n_after_filters,
            "direct_report_source_snapshot_id": job.direct_report_source_snapshot_id,
        }

    def _durable_job(
        self,
        job_id: str,
        *,
        limit: int,
        cursor: str | None,
        source_snapshot_id: str | None,
        owner_user_id: str | None,
        owner_provider: str | None,
    ) -> BatchJob | None:
        workflow = self.workflow_service
        if workflow is None or owner_user_id is None or owner_provider is None:
            return None
        record = workflow.get_record(
            run_id=job_id,
            user_id=owner_user_id,
            owner_provider=owner_provider,
        )
        if record is None or record.kind != "batch":
            return None
        payload = record.result_payload or {}
        snapshot_payload = payload.get("source_snapshot_v2")
        envelope_payload = payload.get("input_envelope_v2")
        if snapshot_payload is not None:
            snapshot = BatchSourceSnapshotV2.model_validate(snapshot_payload)
            envelope = BatchInputEnvelopeV2.model_validate(envelope_payload)
            if source_snapshot_id is not None and source_snapshot_id != snapshot.snapshot_id:
                raise ValueError("requested source snapshot does not match the batch job")
            offset = self._cursor_codec.decode(cursor, snapshot_id=snapshot.snapshot_id)
            items, total = self._durable_items_at_offset(
                job_id=job_id,
                owner_user_id=owner_user_id,
                owner_provider=owner_provider,
                offset=offset,
                limit=limit,
            )
            next_offset = offset + len(items)
            has_more = next_offset < total
            next_cursor = (
                self._cursor_codec.encode(
                    snapshot_id=snapshot.snapshot_id,
                    offset=next_offset,
                )
                if has_more
                else None
            )
            paging_v2 = BatchPagingV2(
                snapshot_id=snapshot.snapshot_id,
                limit=limit,
                next_cursor=next_cursor,
                total=total,
                has_more=has_more,
            )
            dispositions = [
                BatchFilterDispositionV2.model_validate(item)
                for item in payload.get("filter_dispositions_v2") or []
            ]
        else:
            if source_snapshot_id is not None:
                raise ValueError("source-bound paging metadata is unavailable for this legacy job")
            page = workflow.page_items(
                run_id=job_id,
                user_id=owner_user_id,
                owner_provider=owner_provider,
                limit=limit,
                cursor=cursor,
            )
            if page is None:
                return None
            items, next_cursor, total = page
            snapshot = None
            envelope = None
            paging_v2 = None
            dispositions = []
        return BatchJob(
            job_id=record.run_id,
            status=record.status,
            n_input=record.n_input or 0,
            n_to_lookup=record.n_to_lookup or record.total,
            n_after_filters=payload.get("n_after_filters", record.n_after_filters),
            est_seconds=record.est_seconds or 0.0,
            done=record.done,
            total=record.total,
            results=[BatchResult.model_validate(item) for item in items],
            page=BatchPage(
                limit=limit,
                next_cursor=next_cursor,
                total=total,
                paging_v2=paging_v2,
            ),
            warnings=record.warnings,
            input_envelope_v2=envelope,
            source_snapshot_v2=snapshot,
            filter_dispositions_v2=dispositions,
        )

    def _durable_items_at_offset(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        owner_provider: str,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        workflow = self.workflow_service
        if workflow is None:
            return [], 0
        internal_cursor: str | None = None
        position = 0
        selected: list[dict[str, Any]] = []
        total = 0
        while len(selected) < limit:
            page = workflow.page_items(
                run_id=job_id,
                user_id=owner_user_id,
                owner_provider=owner_provider,
                limit=500,
                cursor=internal_cursor,
            )
            if page is None:
                raise ValueError("durable Batch result page is unavailable")
            items, internal_cursor, total = page
            for item in items:
                if position >= offset and len(selected) < limit:
                    selected.append(item)
                position += 1
            if not internal_cursor or not items or position >= offset + limit:
                break
        if offset > total:
            raise ValueError("batch result cursor exceeds the result set")
        return selected, total


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


def _owner_matches(
    record: StoredUpload | StoredBatchJob,
    *,
    owner_user_id: str | None,
    owner_provider: str | None,
) -> bool:
    if owner_user_id is None and owner_provider is None:
        return True
    return record.owner_user_id == owner_user_id and record.owner_provider == owner_provider


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
    hgvs_p = getattr(header, "protein_change", None) or getattr(row, "protein_change", None)
    clinvar_verdict = (
        getattr(header, "classification", None)
        or getattr(acmg_worksheet, "classification", None)
        or _evidence_summary_text(response, "clinvar", "classification")
    )
    gnomad_af = getattr(population, "allele_frequency", None) if population is not None else None
    if gnomad_af is None:
        gnomad_af = _evidence_summary_float(response, "gnomad", "allele_frequency")
    acmg_classification = getattr(computed, "tier", None) or getattr(
        acmg_worksheet, "classification", None
    )
    genomic_hg38 = getattr(header, "genomic_hg38", None) or getattr(row, "genomic_hg38", None)
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
        report_href=_report_href(
            gene,
            hgvs_c,
            transcript=getattr(header, "transcript", None),
        ),
        warnings=list(dict.fromkeys(warnings)),
    )


def _batch_v2_result_from_lookup_response(
    *,
    variant: ParsedVariant,
    response,
    context: _V2RowContext,
    source_snapshot_id: str,
) -> BatchResult:
    execution_state = getattr(response, "execution_state_v2", None)
    identity = context.allele_identity
    if execution_state is None:
        raise ValueError("direct lookup omitted Report V2 execution state")
    if identity is None or identity.status != "normalized" or identity.normalized is None:
        raise ValueError("direct lookup requires a normalized V2 allele")
    normalized_key = _allele_key(identity.normalized)
    canonical = execution_state.canonical_variant
    canonical_keys = {
        _normalize_variant_key(value)
        for value in (canonical.variant_key, canonical.genomic_hg38)
        if value
    }
    if _normalize_variant_key(normalized_key) not in canonical_keys:
        raise ValueError("Report canonical variant does not match the normalized Batch allele")

    legacy = _batch_result_from_lookup_response(
        variant=variant.model_copy(update={"info_af": None, "raw": None}),
        identity=_VariantIdentity(variant_key=normalized_key),
        response=response,
    )
    gene = canonical.gene
    hgvs_c = canonical.cdna
    hgvs_p = canonical.protein_hgvs or legacy.hgvs_p
    values = {
        "gene": gene,
        "hgvs_c": hgvs_c,
        "hgvs_p": hgvs_p,
        "clinvar_verdict": legacy.clinvar_verdict,
        "gnomad_af": legacy.gnomad_af,
        "predictor_ensemble": legacy.predictor_ensemble or None,
        "acmg_classification": legacy.acmg_classification,
    }
    section_ids = {
        "gene": "header",
        "hgvs_c": "header",
        "hgvs_p": "header",
        "clinvar_verdict": "interpretation_summary",
        "gnomad_af": "population_frequency",
        "predictor_ensemble": "computational_deep_dive",
        "acmg_classification": "acmg_worksheet",
    }
    sections = {section.section_id: section for section in execution_state.sections}
    field_executions = [
        _batch_field_execution(
            field_name=field_name,
            value_present=value is not None,
            section=sections.get(section_ids[field_name]),
        )
        for field_name, value in values.items()
    ]
    warnings = list(dict.fromkeys([*legacy.warnings, *getattr(response, "warnings", [])]))
    return BatchResult(
        variant_key=normalized_key,
        state="completed",
        gene=gene,
        hgvs_c=hgvs_c,
        hgvs_p=hgvs_p,
        clinvar_verdict=legacy.clinvar_verdict,
        gnomad_af=legacy.gnomad_af,
        predictor_ensemble=legacy.predictor_ensemble,
        acmg_classification=legacy.acmg_classification,
        report_href=_report_href(gene, hgvs_c, transcript=canonical.transcript),
        warnings=warnings,
        allele_identity_v2=identity,
        source_snapshot_id=source_snapshot_id,
        filter_dispositions_v2=list(context.filter_dispositions),
        sample_provenance_v2=list(context.samples),
        field_executions_v2=field_executions,
    )


def _batch_field_execution(*, field_name: str, value_present: bool, section):
    if value_present:
        if section is None or section.state not in {"ready", "partial"}:
            raise ValueError(f"{field_name} value lacks a ready Report V2 section")
        disclosure = next(
            (
                item
                for item in section.execution_disclosures
                if item.execution in {"eamos_local", "mounted_artifact", "external_provider"}
            ),
            None,
        )
        if disclosure is None:
            raise ValueError(f"{field_name} value lacks executed Report evidence")
        return BatchFieldExecutionV2(
            field_name=field_name,
            value_status="executed",
            execution_disclosure=disclosure,
        )
    if section is not None and section.state == "not_applicable":
        disclosure = next(
            (
                item
                for item in section.execution_disclosures
                if item.execution == "unavailable" and item.applicability == "not_applicable"
            ),
            None,
        )
        if disclosure is None:
            raise ValueError(f"{field_name} not-applicable state lacks exact disclosure")
        return BatchFieldExecutionV2(
            field_name=field_name,
            value_status="not_applicable",
            execution_disclosure=disclosure,
        )
    disclosure = None
    if section is not None and section.state in {"unavailable", "failed", "partial"}:
        disclosure = next(
            (item for item in section.execution_disclosures if item.execution == "unavailable"),
            None,
        )
    if section is not None and section.state == "stale":
        raise ValueError(f"{field_name} source is stale")
    if disclosure is None:
        disclosure = CapabilityExecutionDisclosureV2(
            capability_id=f"batch.field.{field_name}",
            claim=f"Direct Report lookup value for {field_name}",
            execution="unavailable",
            input_scope="normalized_grch38_allele",
            source_status="not_found" if section is not None else "unavailable",
            applicability="applicable",
            validation_status="unvalidated",
            retention="none",
            consent_required=False,
            warnings=[],
            requirements=[
                (
                    "no exact source-backed value was returned"
                    if section is not None
                    else "Report V2 section execution state is required"
                )
            ],
        )
    return BatchFieldExecutionV2(
        field_name=field_name,
        value_status="unavailable",
        execution_disclosure=disclosure,
    )


def _allele_key(allele) -> str:
    return (
        f"{allele.chromosome.removeprefix('chr')}-{allele.position}-"
        f"{allele.reference}-{allele.alternate}"
    )


def _normalize_variant_key(value: str) -> str:
    return value.strip().removeprefix("chr").upper()


def _is_cdna_hgvs(value: str | None) -> bool:
    return bool(value and value.startswith("c."))


def _report_href(
    gene: str | None,
    cdna: str | None,
    *,
    transcript: str | None = None,
) -> str | None:
    if not gene or not _is_cdna_hgvs(cdna):
        return None
    params: list[tuple[str, str]] = [("gene", gene.upper()), ("cdna", cdna)]
    if transcript:
        params.append(("transcript", transcript))
    params.append(("from", "batch"))
    return f"/report?{urlencode(params)}"


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
    except ValueError as exc:
        raise ValueError("batch result cursor is invalid") from exc
    if offset < 0:
        raise ValueError("batch result cursor is invalid")
    return offset


def _positive_int_or_default(value: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
