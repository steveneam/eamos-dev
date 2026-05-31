from __future__ import annotations

from app.schemas.run import (
    PopulationAgeBin,
    PopulationAgeDistribution,
    PopulationAgeHistogram,
    PopulationAgeHistogramView,
    PopulationFrequencyAncestryGroup,
    PopulationFrequencyDatasetCell,
    PopulationFrequencyDetail,
    PopulationFrequencyOverall,
    PopulationFrequencyOverallTotalCell,
    PopulationFrequencyReportSection,
    PopulationFrequencySexCell,
    PopulationFrequencySourceRow,
    PopulationFrequencyVisualGroup,
    PopulationFrequencyVisualScale,
    PopulationSequencingAgeDistribution,
)
from app.services.report_provenance import provenance_for_source

SECTION_ID = "section-3-population-frequency"
PANEL_ID = "gnomad-expansion"

_GROUP_LABELS = {
    "afr": "African/African American genetic ancestry",
    "ami": "Amish genetic ancestry",
    "amr": "Admixed American genetic ancestry",
    "asj": "Ashkenazi Jewish genetic ancestry",
    "eas": "East Asian genetic ancestry",
    "fin": "Finnish genetic ancestry",
    "mid": "Middle Eastern genetic ancestry",
    "nfe": "Non-Finnish European genetic ancestry",
    "remaining": "Remaining genetic ancestry",
    "sas": "South Asian genetic ancestry",
}

GNOMAD_V4_ALL_INDIVIDUAL_AGE_DISTRIBUTIONS = {
    "exome": PopulationAgeHistogram(
        bin_edges=[30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80],
        bin_freq=[3337, 3806, 46374, 60862, 71023, 83028, 108358, 83329, 6292, 2814],
        n_smaller=5892,
        n_larger=1950,
    ),
    "genome": PopulationAgeHistogram(
        bin_edges=[30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80],
        bin_freq=[1332, 1401, 1642, 2949, 4283, 3601, 3282, 2909, 1955, 1202],
        n_smaller=3760,
        n_larger=438,
    ),
}


def build_population_frequency_section(
    detail: PopulationFrequencyDetail | None,
    *,
    source_status: str = "missing",
    gnomad_summary: dict | None = None,
) -> PopulationFrequencyReportSection:
    """Project canonical gnomAD detail into the Section 3 render model."""

    if detail is None:
        return PopulationFrequencyReportSection(
            source_status=source_status or "missing",
            warnings=["population_frequency_detail_unavailable"],
            provenance=[
                provenance_for_source(
                    "gnomAD",
                    status=source_status or "missing",
                    warnings=["population_frequency_detail_unavailable"],
                )
            ],
        )

    groups = _visual_groups(detail, gnomad_summary=gnomad_summary)
    warnings = _section_warnings(detail, groups)
    return PopulationFrequencyReportSection(
        source_status=source_status or "missing",
        dataset=detail.dataset,
        variant_id=detail.variant_id,
        sequencing_type=detail.sequencing_type,
        visual_scale=_visual_scale(detail, groups),
        visual_groups=groups,
        overall=_overall_frequency(detail, gnomad_summary=gnomad_summary),
        age_histograms=_age_histograms(detail),
        source_rows=_source_rows(groups),
        source_url=detail.source_url,
        warnings=warnings,
        provenance=[
            provenance_for_source(
                detail.source,
                status=source_status or "missing",
                query={
                    "variant_id": detail.variant_id,
                    "dataset": detail.dataset,
                    "sequencing_type": detail.sequencing_type,
                },
                source_url=detail.source_url,
                warnings=warnings,
            )
        ],
    )


def _visual_groups(
    detail: PopulationFrequencyDetail,
    *,
    gnomad_summary: dict | None = None,
) -> list[PopulationFrequencyVisualGroup]:
    popmax_id = (detail.popmax_population or "").strip().lower()
    sex_splits = _sex_splits_by_group(gnomad_summary)
    dataset_splits = _dataset_splits_by_group(gnomad_summary)
    sorted_groups = sorted(
        detail.genetic_ancestry_groups,
        key=lambda group: (
            -1 if group.allele_frequency is None else -group.allele_frequency,
            group.id,
        ),
    )
    return [
        PopulationFrequencyVisualGroup(
            id=group.id,
            label=_group_label(group.id),
            allele_frequency=group.allele_frequency,
            allele_count=group.allele_count,
            allele_number=group.allele_number,
            homozygote_count=group.homozygote_count,
            is_popmax=group.id.lower() == popmax_id,
            data_state=_data_state(group),
            sort_order=index + 1,
            xx=sex_splits.get(group.id, {}).get("xx"),
            xy=sex_splits.get(group.id, {}).get("xy"),
            exome=dataset_splits.get(group.id, {}).get("exome"),
            genome=dataset_splits.get(group.id, {}).get("genome"),
            warnings=_group_warnings(group),
        )
        for index, group in enumerate(sorted_groups)
    ]


def _overall_frequency(
    detail: PopulationFrequencyDetail,
    *,
    gnomad_summary: dict | None = None,
) -> PopulationFrequencyOverall | None:
    raw_overall = _dict_or_empty((gnomad_summary or {}).get("overall"))
    total = _total_cell(raw_overall.get("total")) or _detail_total_cell(detail)
    overall = PopulationFrequencyOverall(
        total=total,
        xx=_sex_cell(raw_overall.get("xx")),
        xy=_sex_cell(raw_overall.get("xy")),
    )
    if overall.total is None and overall.xx is None and overall.xy is None:
        return None
    return overall


def _sex_splits_by_group(
    gnomad_summary: dict | None,
) -> dict[str, dict[str, PopulationFrequencySexCell]]:
    groups = (gnomad_summary or {}).get("genetic_ancestry_groups")
    if not isinstance(groups, list):
        return {}
    splits: dict[str, dict[str, PopulationFrequencySexCell]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id") or "").strip()
        if not group_id:
            continue
        xx = _sex_cell(group.get("xx"))
        xy = _sex_cell(group.get("xy"))
        if xx is not None:
            splits.setdefault(group_id, {})["xx"] = xx
        if xy is not None:
            splits.setdefault(group_id, {})["xy"] = xy
    return splits


def _dataset_splits_by_group(
    gnomad_summary: dict | None,
) -> dict[str, dict[str, PopulationFrequencyDatasetCell]]:
    groups = (gnomad_summary or {}).get("genetic_ancestry_groups")
    if not isinstance(groups, list):
        return {}
    splits: dict[str, dict[str, PopulationFrequencyDatasetCell]] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id") or "").strip()
        if not group_id:
            continue
        exome = _dataset_cell(group.get("exome"))
        genome = _dataset_cell(group.get("genome"))
        if exome is not None:
            splits.setdefault(group_id, {})["exome"] = exome
        if genome is not None:
            splits.setdefault(group_id, {})["genome"] = genome
    return splits


def _sex_cell(value: object) -> PopulationFrequencySexCell | None:
    if not isinstance(value, dict):
        return None
    cell = PopulationFrequencySexCell(
        allele_frequency=_optional_float(value.get("allele_frequency")),
        allele_count=_optional_int(value.get("allele_count")),
        allele_number=_optional_int(value.get("allele_number")),
        homozygote_count=_optional_int(value.get("homozygote_count")),
    )
    if (
        cell.allele_frequency is None
        and cell.allele_count is None
        and cell.allele_number is None
        and cell.homozygote_count is None
    ):
        return None
    return cell


def _dataset_cell(value: object) -> PopulationFrequencyDatasetCell | None:
    if not isinstance(value, dict):
        return None
    cell = PopulationFrequencyDatasetCell(
        allele_frequency=_optional_float(value.get("allele_frequency")),
        allele_count=_optional_int(value.get("allele_count")),
        allele_number=_optional_int(value.get("allele_number")),
        homozygote_count=_optional_int(value.get("homozygote_count")),
    )
    if (
        cell.allele_frequency is None
        and cell.allele_count is None
        and cell.allele_number is None
        and cell.homozygote_count is None
    ):
        return None
    return cell


def _total_cell(value: object) -> PopulationFrequencyOverallTotalCell | None:
    if not isinstance(value, dict):
        return None
    cell = PopulationFrequencyOverallTotalCell(
        allele_frequency=_optional_float(value.get("allele_frequency")),
        allele_count=_optional_int(value.get("allele_count")),
        allele_number=_optional_int(value.get("allele_number")),
        homozygote_count=_optional_int(value.get("homozygote_count")),
        exome=_dataset_cell(value.get("exome")),
        genome=_dataset_cell(value.get("genome")),
    )
    if (
        cell.allele_frequency is None
        and cell.allele_count is None
        and cell.allele_number is None
        and cell.homozygote_count is None
        and cell.exome is None
        and cell.genome is None
    ):
        return None
    return cell


def _detail_total_cell(
    detail: PopulationFrequencyDetail,
) -> PopulationFrequencyOverallTotalCell | None:
    return _nonempty_total_cell(
        PopulationFrequencyOverallTotalCell(
            allele_frequency=detail.allele_frequency,
            allele_count=detail.allele_count,
            allele_number=detail.allele_number,
            homozygote_count=detail.homozygote_count,
        )
    )


def _nonempty_total_cell(
    cell: PopulationFrequencyOverallTotalCell,
) -> PopulationFrequencyOverallTotalCell | None:
    if (
        cell.allele_frequency is None
        and cell.allele_count is None
        and cell.allele_number is None
        and cell.homozygote_count is None
        and cell.exome is None
        and cell.genome is None
    ):
        return None
    return cell


def _visual_scale(
    detail: PopulationFrequencyDetail,
    groups: list[PopulationFrequencyVisualGroup],
) -> PopulationFrequencyVisualScale | None:
    basis = "popmax_frequency" if detail.popmax_frequency is not None else "allele_frequency"
    candidates = [group.allele_frequency for group in groups if group.allele_frequency is not None]
    candidates.extend(
        value for value in (detail.popmax_frequency, detail.allele_frequency) if value is not None
    )
    if not candidates:
        return None
    max_value = max(candidates)
    max_group_id = next((group.id for group in groups if group.is_popmax), None)
    if max_group_id is None:
        max_group_id = next(
            (group.id for group in groups if group.allele_frequency == max_value),
            None,
        )
    return PopulationFrequencyVisualScale(
        basis=basis,
        max_value=max_value,
        max_group_id=max_group_id,
        warnings=[],
    )


def _age_histograms(detail: PopulationFrequencyDetail) -> list[PopulationAgeHistogramView]:
    histograms: list[PopulationAgeHistogramView] = []
    age_distributions = list(detail.age_distributions)
    if not age_distributions and detail.age_distribution is not None:
        age_distributions = [
            PopulationSequencingAgeDistribution(
                sequencing_type=detail.sequencing_type,
                age_distribution=detail.age_distribution,
            )
        ]
    for item in age_distributions:
        carrier_histogram = _carrier_age_histogram(item.age_distribution)
        if carrier_histogram is None:
            continue
        histograms.append(
            _age_histogram_view(
                carrier_histogram,
                sequencing_type=item.sequencing_type,
                series_kind="variant_carriers",
                genotype="combined",
            )
        )
    for sequencing_type, histogram in GNOMAD_V4_ALL_INDIVIDUAL_AGE_DISTRIBUTIONS.items():
        histograms.append(
            _age_histogram_view(
                histogram,
                sequencing_type=sequencing_type,
                series_kind="all_individuals",
                genotype="not_applicable",
                warnings=["age_distribution_source:gnomad_v4_age_distribution_metadata"],
            )
        )
    return histograms


def _age_histogram_view(
    histogram: PopulationAgeHistogram,
    *,
    sequencing_type: str,
    series_kind: str,
    genotype: str,
    warnings: list[str] | None = None,
) -> PopulationAgeHistogramView:
    return PopulationAgeHistogramView(
        sequencing_type=sequencing_type,  # type: ignore[arg-type]
        series_kind=series_kind,  # type: ignore[arg-type]
        genotype=genotype,  # type: ignore[arg-type]
        scope="overall_release_samples",
        bins=_age_bins(histogram),
        n_smaller=histogram.n_smaller,
        n_larger=histogram.n_larger,
        warnings=warnings
        or [
            "age_distribution_scope:overall_release_samples",
            "per_genetic_ancestry_age_distribution_not_available",
        ],
    )


def _carrier_age_histogram(
    distribution: PopulationAgeDistribution,
) -> PopulationAgeHistogram | None:
    histograms = [item for item in (distribution.het, distribution.hom) if item is not None]
    if not histograms:
        return None
    max_bins = max(len(item.bin_freq) for item in histograms)
    first = histograms[0]
    return PopulationAgeHistogram(
        bin_edges=first.bin_edges,
        bin_freq=[
            sum(item.bin_freq[index] if index < len(item.bin_freq) else 0 for item in histograms)
            for index in range(max_bins)
        ],
        n_smaller=_sum_optional_counts([item.n_smaller for item in histograms]),
        n_larger=_sum_optional_counts([item.n_larger for item in histograms]),
    )


def _sum_optional_counts(values: list[int | None]) -> int | None:
    reported = [value for value in values if value is not None]
    if not reported:
        return None
    return sum(reported)


def _age_bins(histogram: PopulationAgeHistogram) -> list[PopulationAgeBin]:
    bins: list[PopulationAgeBin] = []
    for index, count in enumerate(histogram.bin_freq):
        lower = histogram.bin_edges[index] if index < len(histogram.bin_edges) else None
        upper = histogram.bin_edges[index + 1] if index + 1 < len(histogram.bin_edges) else None
        if lower is not None and upper is not None:
            label = f"{lower:g}-{upper:g}"
        elif lower is not None:
            label = f"{lower:g}+"
        else:
            label = f"bin {index + 1}"
        bins.append(
            PopulationAgeBin(
                label=label,
                lower_bound=lower,
                upper_bound=upper,
                count=count,
            )
        )
    return bins


def _source_rows(
    groups: list[PopulationFrequencyVisualGroup],
) -> list[PopulationFrequencySourceRow]:
    return [
        PopulationFrequencySourceRow(
            group_id=group.id,
            label=group.label,
            allele_frequency=group.allele_frequency,
            allele_count=group.allele_count,
            allele_number=group.allele_number,
            homozygote_count=group.homozygote_count,
            is_popmax=group.is_popmax,
            warnings=group.warnings,
        )
        for group in groups
    ]


def _section_warnings(
    detail: PopulationFrequencyDetail,
    groups: list[PopulationFrequencyVisualGroup],
) -> list[str]:
    warnings = list(detail.warnings)
    if not groups:
        warnings.append("genetic_ancestry_groups_unavailable")
    if detail.age_distribution is None and not detail.age_distributions:
        warnings.append("age_distribution_unavailable")
    else:
        warnings.append("age_distribution_scope:overall_release_samples")
        warnings.append("per_genetic_ancestry_age_distribution_not_available")
    if detail.allele_frequency is None:
        warnings.append("allele_frequency_unavailable")
    return _dedupe(warnings)


def _data_state(group: PopulationFrequencyAncestryGroup) -> str:
    if group.allele_count == 0:
        return "zero_observed"
    if group.allele_frequency is None and group.allele_count is None:
        return "not_reported"
    return "observed"


def _group_warnings(group: PopulationFrequencyAncestryGroup) -> list[str]:
    if group.allele_number in (None, 0):
        return ["allele_number_unavailable"]
    return []


def _group_label(group_id: str) -> str:
    return _GROUP_LABELS.get(group_id.lower(), f"{group_id.upper()} genetic ancestry")


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


def _dict_or_empty(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
