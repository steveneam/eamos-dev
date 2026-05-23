from __future__ import annotations

from app.schemas.run import (
    PopulationAgeBin,
    PopulationAgeHistogram,
    PopulationAgeHistogramView,
    PopulationFrequencyAncestryGroup,
    PopulationFrequencyDetail,
    PopulationFrequencyReportSection,
    PopulationFrequencySourceRow,
    PopulationFrequencyVisualGroup,
    PopulationFrequencyVisualScale,
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


def build_population_frequency_section(
    detail: PopulationFrequencyDetail | None,
    *,
    source_status: str = "missing",
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

    groups = _visual_groups(detail)
    warnings = _section_warnings(detail, groups)
    return PopulationFrequencyReportSection(
        source_status=source_status or "missing",
        dataset=detail.dataset,
        variant_id=detail.variant_id,
        sequencing_type=detail.sequencing_type,
        visual_scale=_visual_scale(detail, groups),
        visual_groups=groups,
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


def _visual_groups(detail: PopulationFrequencyDetail) -> list[PopulationFrequencyVisualGroup]:
    popmax_id = (detail.popmax_population or "").strip().lower()
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
            warnings=_group_warnings(group),
        )
        for index, group in enumerate(sorted_groups)
    ]


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
    if detail.age_distribution is None:
        return []
    histograms: list[PopulationAgeHistogramView] = []
    if detail.age_distribution.het is not None:
        histograms.append(
            _age_histogram_view(
                detail.age_distribution.het,
                genotype="heterozygous_alternate",
            )
        )
    if detail.age_distribution.hom is not None:
        histograms.append(
            _age_histogram_view(
                detail.age_distribution.hom,
                genotype="homozygous_alternate",
            )
        )
    return histograms


def _age_histogram_view(
    histogram: PopulationAgeHistogram,
    *,
    genotype: str,
) -> PopulationAgeHistogramView:
    return PopulationAgeHistogramView(
        genotype=genotype,  # type: ignore[arg-type]
        scope="overall_release_samples",
        bins=_age_bins(histogram),
        n_smaller=histogram.n_smaller,
        n_larger=histogram.n_larger,
        warnings=[
            "age_distribution_scope:overall_release_samples",
            "per_genetic_ancestry_age_distribution_not_available",
        ],
    )


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
    if detail.age_distribution is None:
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
