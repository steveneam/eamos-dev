from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Callable, Iterable, Iterator

from app.schemas.batch import (
    BatchFilterDispositionV2,
    BatchFilterPlanV2,
    BatchFilters,
    BatchResult,
)
from app.services.batch_engine.intake import StreamedVariant


@dataclass(frozen=True)
class GenomicInterval:
    chromosome: str
    start: int
    end: int


@dataclass(frozen=True)
class BatchPreFilterResult:
    candidates: tuple[StreamedVariant, ...]
    dispositions: tuple[BatchFilterDispositionV2, ...]
    allele_count: int
    excluded_count: int
    duplicate_count: int
    over_cap_count: int


@dataclass
class BatchPreFilterStats:
    allele_count: int = 0
    retained_count: int = 0
    counts: dict[str, int] = field(default_factory=dict)

    def exclude(self, reason: str) -> None:
        self.counts[reason] = self.counts.get(reason, 0) + 1

    def dispositions(
        self,
        *,
        source_snapshot_id: str,
        normalized_retained_count: int,
        normalized_duplicate_count: int,
        annotation_cap_count: int,
    ) -> tuple[BatchFilterDispositionV2, ...]:
        counts = dict(self.counts)
        if normalized_duplicate_count:
            counts["duplicate"] = normalized_duplicate_count
        if annotation_cap_count:
            counts["annotation_cap"] = annotation_cap_count
        dispositions = [
            BatchFilterDispositionV2(
                stage="pre_annotation",
                outcome="excluded",
                reason=reason,
                detail=f"{count} allele(s) excluded by {reason}",
                source_snapshot_id=source_snapshot_id,
            )
            for reason, count in sorted(counts.items())
        ]
        if normalized_retained_count:
            dispositions.append(
                BatchFilterDispositionV2(
                    stage="pre_annotation",
                    outcome="included",
                    reason="pass_filter",
                    detail=(
                        f"{normalized_retained_count} unique normalized allele(s) retained "
                        "for annotation"
                    ),
                    source_snapshot_id=source_snapshot_id,
                )
            )
        return tuple(dispositions)


class BatchFilterUnavailable(RuntimeError):
    def __init__(self, requirement: str) -> None:
        super().__init__("Batch pre-annotation filtering is unavailable.")
        self.requirement = requirement


class BatchResourceLimitExceeded(RuntimeError):
    pass


def filter_pre_annotation(
    variants: Iterable[StreamedVariant],
    *,
    legacy_filters: BatchFilters,
    filter_plan: BatchFilterPlanV2 | None,
    panel_intervals: tuple[GenomicInterval, ...] | None,
    source_snapshot_id: str,
    post_filter_cap: int,
) -> BatchPreFilterResult:
    """Filter a raw stream while retaining at most the annotation cap."""

    cap = max(1, int(post_filter_cap))
    stats = BatchPreFilterStats()
    stream = iter_pre_annotation(
        variants,
        legacy_filters=legacy_filters,
        filter_plan=filter_plan,
        panel_intervals=panel_intervals,
        stats=stats,
    )
    candidates: dict[str, StreamedVariant] = {}
    duplicate_count = 0
    over_cap_count = 0
    for streamed in stream:
        key = _original_key(streamed)
        if key in candidates:
            duplicate_count += 1
            candidates[key] = _merge_streamed_variant(candidates[key], streamed)
            continue
        if len(candidates) >= cap:
            over_cap_count += 1
            continue
        candidates[key] = streamed
    dispositions = stats.dispositions(
        source_snapshot_id=source_snapshot_id,
        normalized_retained_count=len(candidates),
        normalized_duplicate_count=duplicate_count,
        annotation_cap_count=over_cap_count,
    )
    return BatchPreFilterResult(
        candidates=tuple(candidates.values()),
        dispositions=dispositions,
        allele_count=stats.allele_count,
        excluded_count=sum(stats.counts.values()) + duplicate_count + over_cap_count,
        duplicate_count=duplicate_count,
        over_cap_count=over_cap_count,
    )


def iter_pre_annotation(
    variants: Iterable[StreamedVariant],
    *,
    legacy_filters: BatchFilters,
    filter_plan: BatchFilterPlanV2 | None,
    panel_intervals: tuple[GenomicInterval, ...] | None,
    stats: BatchPreFilterStats,
    deadline_monotonic: float | None = None,
    clock: Callable[[], float] = monotonic,
) -> Iterator[StreamedVariant]:
    """Yield cheap-filter survivors without materializing the candidate cohort."""

    pass_only = filter_plan.pass_only if filter_plan is not None else legacy_filters.pass_only
    minimum_quality = filter_plan.minimum_quality if filter_plan is not None else None
    regions = list(filter_plan.regions if filter_plan is not None else legacy_filters.regions)
    needs_panel_intervals = bool(legacy_filters.panel_slug) or filter_plan is not None
    if needs_panel_intervals and not panel_intervals:
        raise BatchFilterUnavailable(
            "mount a checksum-verified coordinate interval artifact for the selected panel scope"
        )

    for streamed in variants:
        stats.allele_count += 1
        if deadline_monotonic is not None and clock() > deadline_monotonic:
            raise BatchResourceLimitExceeded(
                "Batch preparation exceeded the configured wall-time limit."
            )
        variant = streamed.variant
        if pass_only and variant.filter not in {None, "", ".", "PASS"}:
            stats.exclude("pass_filter")
            continue
        if minimum_quality is not None and (
            streamed.quality is None or streamed.quality < minimum_quality
        ):
            stats.exclude("quality")
            continue
        if regions and not _matches_regions(streamed, regions):
            stats.exclude("region")
            continue
        if needs_panel_intervals and panel_intervals is not None:
            if not _matches_intervals(streamed, panel_intervals):
                reason = (
                    "capture_scope"
                    if filter_plan is not None and filter_plan.interval_scope == "capture_bed"
                    else "gene_scope"
                )
                stats.exclude(reason)
                continue
        if streamed.samples and not any(
            _has_non_reference_genotype(item.genotype) for item in streamed.samples
        ):
            stats.exclude("genotype")
            continue
        stats.retained_count += 1
        yield streamed


def filter_post_annotation(
    result: BatchResult,
    *,
    filter_plan: BatchFilterPlanV2 | None,
    source_snapshot_id: str,
) -> tuple[BatchResult, tuple[BatchFilterDispositionV2, ...]]:
    if filter_plan is None:
        return result, ()
    dispositions: list[BatchFilterDispositionV2] = []
    excluded_reason: str | None = None
    deferred: list[str] = []
    if filter_plan.max_population_af is not None:
        if result.gnomad_af is None:
            deferred.append("population frequency execution is unavailable")
        elif result.gnomad_af > filter_plan.max_population_af:
            excluded_reason = "population_frequency"
    if excluded_reason is None and filter_plan.classifications:
        if result.acmg_classification is None:
            deferred.append("classification execution is unavailable")
        elif result.acmg_classification not in filter_plan.classifications:
            excluded_reason = "classification"
    if excluded_reason is None and filter_plan.consequence_terms:
        deferred.append("consequence filtering requires a canonical Report consequence field")
    if excluded_reason is None and filter_plan.require_evidence_sources:
        executed_ids = {
            field.execution_disclosure.capability_id
            for field in result.field_executions_v2
            if field.value_status == "executed"
        }
        missing = sorted(set(filter_plan.require_evidence_sources) - executed_ids)
        if missing:
            deferred.append("required evidence source execution is unavailable")
    if excluded_reason is not None:
        dispositions.append(
            BatchFilterDispositionV2(
                stage="post_annotation",
                outcome="excluded",
                reason=excluded_reason,
                detail=f"row excluded by {excluded_reason}",
                source_snapshot_id=source_snapshot_id,
            )
        )
        result = result.model_copy(update={"state": "filtered_post_lookup"}, deep=True)
    for detail in dict.fromkeys(deferred):
        dispositions.append(
            BatchFilterDispositionV2(
                stage="post_annotation",
                outcome="deferred",
                reason="source_unavailable",
                detail=detail,
                source_snapshot_id=source_snapshot_id,
            )
        )
    if excluded_reason is None and not deferred:
        dispositions.append(
            BatchFilterDispositionV2(
                stage="post_annotation",
                outcome="included",
                reason="evidence_state",
                detail="row satisfied every configured post-annotation filter",
                source_snapshot_id=source_snapshot_id,
            )
        )
    return result, tuple(dispositions)


def _original_key(streamed: StreamedVariant) -> str:
    allele = streamed.original_allele
    return f"{allele.chromosome}-{allele.position}-{allele.reference}-{allele.alternate}"


def _merge_streamed_variant(
    primary: StreamedVariant, duplicate: StreamedVariant
) -> StreamedVariant:
    by_index = {item.source_sample_index: item for item in primary.samples}
    for item in duplicate.samples:
        by_index.setdefault(item.source_sample_index, item)
    warnings = list(dict.fromkeys([*primary.variant.warnings, *duplicate.variant.warnings]))
    variant = primary.variant.model_copy(update={"warnings": warnings})
    return StreamedVariant(
        variant=variant,
        original_allele=primary.original_allele,
        source_record_index=primary.source_record_index,
        quality=primary.quality,
        samples=tuple(by_index[index] for index in sorted(by_index)),
    )


def _has_non_reference_genotype(genotype: str) -> bool:
    alleles = genotype.replace("|", "/").split("/")
    return any(allele not in {"0", ".", ""} for allele in alleles)


def _matches_intervals(
    streamed: StreamedVariant,
    intervals: tuple[GenomicInterval, ...],
) -> bool:
    allele = streamed.original_allele
    chromosome = allele.chromosome.removeprefix("chr").upper()
    end = allele.position + len(allele.reference) - 1
    return any(
        interval.chromosome.removeprefix("chr").upper() == chromosome
        and end >= interval.start
        and allele.position <= interval.end
        for interval in intervals
    )


def _matches_regions(streamed: StreamedVariant, regions: list[str]) -> bool:
    allele = streamed.original_allele
    chromosome = allele.chromosome.removeprefix("chr").upper()
    for region in regions:
        region_chromosome, start, end = _parse_region(region)
        if region_chromosome != chromosome:
            continue
        if start is None or end is None or start <= allele.position <= end:
            return True
    return False


def _parse_region(region: str) -> tuple[str, int | None, int | None]:
    chromosome, _, span = region.partition(":")
    chromosome = chromosome.strip().removeprefix("chr").upper()
    if not span:
        return chromosome, None, None
    start_text, separator, end_text = span.replace(",", "").partition("-")
    if not separator:
        return chromosome, None, None
    try:
        start = int(start_text)
        end = int(end_text)
    except ValueError:
        return chromosome, None, None
    return chromosome, min(start, end), max(start, end)
