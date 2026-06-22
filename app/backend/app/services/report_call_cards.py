from __future__ import annotations

from typing import Any

from app.schemas.run import (
    PopulationAgeDistribution,
    PopulationAgeHistogram,
    PopulationFrequencyAncestryGroup,
    PopulationFrequencyDetail,
    PopulationSequencingAgeDistribution,
    ReportCallBadge,
    ReportCallCard,
    ReportCallInteraction,
    ReportPayload,
    VariantReportCallCards,
)
from app.services.population_frequency_section import PANEL_ID, SECTION_ID

FREQUENCY_PM2_AF_THRESHOLD = 0.0001
FREQUENCY_BS1_AF_THRESHOLD = 0.01
FREQUENCY_BA1_AF_THRESHOLD = 0.05

CORE_GNOMAD_GROUPS = {
    "afr",
    "ami",
    "amr",
    "asj",
    "eas",
    "fin",
    "mid",
    "nfe",
    "remaining",
    "sas",
}

POPULATION_FREQUENCY_INTERACTION = ReportCallInteraction(
    action="scroll_and_expand",
    target_section_id=SECTION_ID,
    target_panel_id=PANEL_ID,
)


def build_population_frequency_detail(
    gnomad_summary: dict[str, Any],
    *,
    source_status: str = "",
    source_url: str | None = None,
    source_warnings: list[str] | None = None,
) -> PopulationFrequencyDetail | None:
    if not gnomad_summary:
        return None

    ancestry_groups = [
        _population_group_from_summary(item)
        for item in gnomad_summary.get("genetic_ancestry_groups", [])
        if isinstance(item, dict)
    ]
    ancestry_groups = [item for item in ancestry_groups if item is not None]

    age_distribution = _age_distribution_from_summary(gnomad_summary.get("age_distribution"))
    age_distributions = _age_distributions_from_summary(gnomad_summary.get("age_distributions"))
    warnings = list(source_warnings or [])
    if source_status in {"fallback", "degraded", "error", "failed"}:
        warnings.append(f"gnomad_source_status:{source_status}")
    unavailable_reason = _population_unavailable_reason(
        gnomad_summary,
        source_status=source_status,
        warnings=warnings,
    )

    return PopulationFrequencyDetail(
        dataset=str(gnomad_summary.get("dataset") or ""),
        variant_id=str(gnomad_summary.get("variant_id") or ""),
        unavailable_reason=unavailable_reason,
        sequencing_type=gnomad_summary.get("sequencing_type") or "unknown",
        allele_frequency=_as_float(gnomad_summary.get("allele_frequency")),
        allele_count=_as_int(gnomad_summary.get("allele_count")),
        allele_number=_as_int(gnomad_summary.get("allele_number")),
        homozygote_count=_as_int(gnomad_summary.get("homozygote_count")),
        popmax_frequency=_as_float(gnomad_summary.get("popmax_frequency")),
        popmax_population=_as_optional_str(gnomad_summary.get("popmax_population")),
        genetic_ancestry_groups=ancestry_groups,
        age_distribution=age_distribution,
        age_distributions=age_distributions,
        flags=[
            str(item) for item in gnomad_summary.get("flags", []) if isinstance(item, str) and item
        ],
        warnings=warnings,
        source_url=_as_optional_str(gnomad_summary.get("url")) or source_url,
    )


def build_variant_report_call_cards(
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> VariantReportCallCards:
    return VariantReportCallCards(
        cards=[
            _population_frequency_card(payload, evidence_map, evidence_statuses),
            _computational_card(payload, evidence_map, evidence_statuses),
            _lab_functional_card(payload, evidence_statuses),
            _clinical_consensus_card(payload, evidence_map, evidence_statuses),
        ]
    )


def _population_frequency_card(
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> ReportCallCard:
    detail = payload.population_frequency_detail
    status = evidence_statuses.get("gnomad", "missing")
    if detail is None or detail.allele_frequency is None:
        return ReportCallCard(
            card_id="population_frequency",
            title="Population Frequency",
            primary_label="No Population Data",
            support_badges=[ReportCallBadge(text="gnomAD unavailable", kind="warning")],
            ui_color_theme="neutral_slate_state",
            source_status=status,
            provenance=[_gnomad_provenance_label(status)],
            warnings=[] if detail is None else detail.warnings,
            interaction=POPULATION_FREQUENCY_INTERACTION,
        )

    ac = detail.allele_count
    af = detail.allele_frequency
    popmax_af = detail.popmax_frequency
    max_af = max(value for value in (af, popmax_af) if value is not None)

    if ac == 0:
        primary_label = "Absent"
        theme = "support_green_state"
    elif max_af >= FREQUENCY_BA1_AF_THRESHOLD:
        primary_label = f"Very Common ({_format_percent(max_af)} max AF)"
        theme = "benign_green_state"
    elif max_af >= FREQUENCY_BS1_AF_THRESHOLD:
        primary_label = f"Common ({_format_percent(max_af)} max AF)"
        theme = "benign_green_state"
    elif max_af < FREQUENCY_PM2_AF_THRESHOLD:
        primary_label = f"Rare ({_format_percent(af)} AF)"
        theme = "support_green_state"
    else:
        primary_label = f"Low Frequency ({_format_percent(max_af)} max AF)"
        theme = "neutral_slate_state"

    support_badges = [_frequency_code_badge(detail, payload, evidence_map)]
    if detail.popmax_frequency is not None and detail.popmax_population:
        support_badges.append(
            ReportCallBadge(
                text=(
                    f"Max {detail.popmax_population.upper()}: "
                    f"{_format_percent(detail.popmax_frequency)}"
                ),
                kind="metric",
            )
        )
    if detail.allele_count is not None:
        support_badges.append(ReportCallBadge(text=f"AC {detail.allele_count}", kind="metric"))

    provenance = [
        f"gnomAD {detail.dataset or 'dataset unknown'} {detail.sequencing_type}",
    ]
    if detail.source_url:
        provenance.append(detail.source_url)

    return ReportCallCard(
        card_id="population_frequency",
        title="Population Frequency",
        primary_label=primary_label,
        support_badges=support_badges,
        ui_color_theme=theme,
        source_status=status,
        provenance=provenance,
        warnings=detail.warnings,
        interaction=POPULATION_FREQUENCY_INTERACTION,
    )


def _computational_card(
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> ReportCallCard:
    annotations = evidence_map.get("computational_annotations", {})
    annotation_card = _computational_card_from_annotations(
        annotations,
        payload,
        evidence_map,
        evidence_statuses,
    )
    if annotation_card is not None:
        return annotation_card

    predictions = payload.in_silico_predictions
    if predictions is None or not predictions.cards:
        return ReportCallCard(
            card_id="computational",
            title="Computational",
            primary_label="No Computational Data",
            support_badges=[ReportCallBadge(text="None", kind="neutral")],
            ui_color_theme="neutral_slate_state",
            source_status=_combined_status(evidence_statuses, ("spliceai",)),
            provenance=["SpliceAI / predictor sources unavailable"],
        )

    spliceai = next((card for card in predictions.cards if card.name == "SpliceAI"), None)
    damaging_cards = [card for card in predictions.cards if card.verdict == "damaging"]
    tolerated_cards = [card for card in predictions.cards if card.verdict == "tolerated"]

    if spliceai is not None and spliceai.verdict == "damaging":
        primary_label = "Splicing Defect"
        theme = "risk_red_state"
    elif damaging_cards:
        primary_label = "Damaging"
        theme = "risk_red_state"
    elif len(tolerated_cards) == len(predictions.cards):
        primary_label = "Benign Predicted"
        theme = "benign_green_state"
    else:
        primary_label = "Uncertain"
        theme = "caution_orange_state"

    support_badges: list[ReportCallBadge] = []
    top_cards = sorted(
        predictions.cards,
        key=lambda card: (card.verdict != "damaging", -card.score),
    )[:2]
    for card in top_cards:
        support_badges.append(ReportCallBadge(text=f"{card.name}: {card.score:.2f}", kind="metric"))

    acmg_badge = _first_met_acmg_badge(payload, ("PP3", "BP4"))
    if acmg_badge is not None:
        support_badges.append(acmg_badge)

    return ReportCallCard(
        card_id="computational",
        title="Computational",
        primary_label=primary_label,
        support_badges=support_badges or [ReportCallBadge(text="None", kind="neutral")],
        ui_color_theme=theme,
        source_status=_combined_status(evidence_statuses, ("spliceai", "vep")),
        provenance=["SpliceAI and in-silico predictor payload"],
    )


def _lab_functional_card(
    payload: ReportPayload,
    evidence_statuses: dict[str, str],
) -> ReportCallCard:
    functional = payload.functional_evidence
    if functional is None:
        return ReportCallCard(
            card_id="lab_functional",
            title="Lab & Functional",
            primary_label="No Functional Data Available",
            support_badges=[ReportCallBadge(text="0 Unique", kind="metric")],
            ui_color_theme="neutral_slate_state",
            source_status="missing",
            provenance=["ClinGen / ClinVar / PubMed functional evidence"],
        )

    metrics = functional.display_metrics
    acmg_badge_kind: str = "acmg"
    if metrics.acmg_badge_text == "Review Required":
        acmg_badge_kind = "warning"
    elif metrics.acmg_badge_text in {"None", "No code asserted"}:
        acmg_badge_kind = "neutral"
    badges = [
        ReportCallBadge(
            text=metrics.acmg_badge_text,
            kind=acmg_badge_kind,  # type: ignore[arg-type]
        ),
        ReportCallBadge(text=metrics.study_count_badge_text, kind="metric"),
    ]

    return ReportCallCard(
        card_id="lab_functional",
        title="Lab & Functional",
        primary_label=metrics.primary_label,
        support_badges=badges,
        ui_color_theme=metrics.ui_color_theme,
        source_status=_combined_status(evidence_statuses, ("clingen", "clinvar", "pubmed")),
        provenance=["ClinGen Evidence Repository", "ClinVar VCV", "PubMed"],
        warnings=functional.warnings,
    )


def _computational_card_from_annotations(
    annotations: dict[str, Any],
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> ReportCallCard | None:
    if not annotations:
        return None

    excluded = {str(item) for item in annotations.get("excluded_predictors", [])}
    excluded.discard("AlphaMissense")
    rows = [
        row
        for row in (
            _annotation_predictor_row(item)
            for item in annotations.get("predictors", [])
            if isinstance(item, dict)
        )
        if row is not None and row["name"] not in excluded
    ]
    spliceai = annotations.get("spliceai") if isinstance(annotations.get("spliceai"), dict) else {}
    spliceai_score = _as_float(spliceai.get("max_delta")) if spliceai else None
    if spliceai_score is not None and "SpliceAI" not in {row["name"] for row in rows}:
        rows.append(
            {
                "name": "SpliceAI",
                "score": spliceai_score,
                "threshold": _as_float(spliceai.get("threshold")),
            }
        )

    if not rows and spliceai_score is None:
        return None

    damaging_rows = [
        row
        for row in rows
        if row["score"] is not None
        and row["threshold"] is not None
        and row["score"] >= row["threshold"]
    ]
    if any(row["name"] == "SpliceAI" for row in damaging_rows):
        primary_label = "Splicing Defect"
        theme = "risk_red_state"
    elif damaging_rows:
        primary_label = "Damaging"
        theme = "risk_red_state"
    else:
        primary_label = "Uncertain"
        theme = "caution_orange_state"

    preferred_names = (
        "REVEL",
        "CADD PHRED",
        "AlphaMissense",
        "ESM1b",
        "PrimateAI-3D",
        "MetaLR",
        "SpliceAI",
    )
    ranked_rows = sorted(
        rows,
        key=lambda row: (
            (
                preferred_names.index(row["name"])
                if row["name"] in preferred_names
                else len(preferred_names)
            ),
            row["name"],
        ),
    )
    support_badges = [
        ReportCallBadge(text=f"{row['name']}: {_format_score(row['score'])}", kind="metric")
        for row in (row for row in ranked_rows if row["score"] is not None)
    ][:2]

    acmg_badge = _first_acmg_badge_from_consensus(evidence_map, ("PP3", "BP4"))
    if acmg_badge is None:
        acmg_badge = _first_met_acmg_badge(payload, ("PP3", "BP4"))
    if acmg_badge is not None:
        support_badges.append(acmg_badge)

    provenance = ["Computational annotation payload"]
    source_urls = [
        str(row.get("source_url"))
        for row in annotations.get("predictors", [])
        if isinstance(row, dict) and row.get("source_url")
    ]
    if spliceai and spliceai.get("source_url"):
        source_urls.append(str(spliceai["source_url"]))
    provenance.extend(_dedupe_strings(source_urls))

    return ReportCallCard(
        card_id="computational",
        title="Computational",
        primary_label=primary_label,
        support_badges=support_badges or [ReportCallBadge(text="None", kind="neutral")],
        ui_color_theme=theme,
        source_status=_displayed_annotation_status(evidence_statuses),
        provenance=provenance,
        warnings=[str(item) for item in annotations.get("warnings", []) if isinstance(item, str)],
    )


def _displayed_annotation_status(evidence_statuses: dict[str, str]) -> str:
    status = evidence_statuses.get("computational_annotations")
    if status:
        return status
    return _combined_status(evidence_statuses, ("spliceai", "vep"))


def _gnomad_provenance_label(status: str) -> str:
    if status in {"live", "cache"}:
        return "gnomAD GraphQL"
    if status == "fixture":
        return "gnomAD fixture"
    if status in {"fallback", "degraded"}:
        return "gnomAD fallback"
    if status in {"error", "failed"}:
        return "gnomAD source error"
    return "gnomAD unavailable"


def _population_unavailable_reason(
    summary: dict[str, Any],
    *,
    source_status: str,
    warnings: list[str],
) -> str | None:
    has_frequency = _as_float(summary.get("allele_frequency")) is not None
    groups = summary.get("genetic_ancestry_groups", [])
    if not isinstance(groups, list):
        groups = []
    has_groups = any(
        isinstance(item, dict)
        and (
            _as_float(item.get("allele_frequency", item.get("af"))) is not None
            or _as_int(item.get("allele_count", item.get("ac"))) is not None
        )
        for item in groups
    )
    if has_frequency or has_groups:
        return None
    if "gnomad_variant_not_found" in warnings:
        return "variant_not_found"
    if source_status in {"fallback", "degraded", "error", "failed"}:
        return "source_unavailable"
    if not summary:
        return "detail_unavailable"
    return "frequency_metrics_unavailable"


def _annotation_predictor_row(item: dict[str, Any]) -> dict[str, Any] | None:
    name = _as_optional_str(item.get("name"))
    if not name:
        return None
    return {
        "name": name,
        "score": _as_float(item.get("score")),
        "threshold": _as_float(item.get("threshold")),
    }


def _clinical_consensus_card(
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
) -> ReportCallCard:
    consensus = evidence_map.get("clinical_consensus", {})
    clinvar = evidence_map.get("clinvar", {})
    classification = str(
        consensus.get("classification") or clinvar.get("classification") or "Unavailable"
    )
    classification_source = str(consensus.get("classification_source") or "ClinVar")
    review_status = str(
        consensus.get("review_status")
        or clinvar.get("review_status")
        or "review status unavailable"
    )
    accession = str(consensus.get("accession") or clinvar.get("accession") or "")
    primary_label = _title_classification(classification)

    source_label = "ClinGen/VCEP" if classification_source == "ClinGen" else "ClinVar"
    badges = [ReportCallBadge(text=f"{source_label}: {review_status}", kind="source")]
    if accession:
        badges.append(ReportCallBadge(text=accession, kind="source"))

    provenance = (
        ["ClinGen Evidence Repository"]
        if classification_source == "ClinGen"
        else ["ClinVar aggregate classification"]
    )
    source_url = consensus.get("source_url")
    if source_url:
        provenance.append(str(source_url))

    return ReportCallCard(
        card_id="clinical_consensus",
        title="Clinical Consensus",
        primary_label=primary_label,
        support_badges=badges,
        ui_color_theme=_classification_theme(primary_label),
        source_status=evidence_statuses.get("clinical_consensus")
        or evidence_statuses.get("clingen")
        or evidence_statuses.get("clinvar", "missing"),
        provenance=provenance,
        warnings=[str(item) for item in consensus.get("warnings", [])],
    )


def _frequency_code_badge(
    detail: PopulationFrequencyDetail,
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
) -> ReportCallBadge:
    consensus_badge = _first_acmg_badge_from_consensus(evidence_map, ("PM2", "BS1", "BA1"))
    if consensus_badge is not None:
        return consensus_badge
    existing = _first_met_acmg_badge(payload, ("PM2", "BS1", "BA1"))
    if existing is not None:
        return existing
    return ReportCallBadge(text="None", kind="neutral")


def _first_acmg_badge_from_consensus(
    evidence_map: dict[str, dict[str, Any]],
    codes: tuple[str, ...],
) -> ReportCallBadge | None:
    worksheet = evidence_map.get("clinical_consensus", {}).get("acmg_worksheet")
    if not isinstance(worksheet, dict):
        return None
    criteria = worksheet.get("criteria")
    if not isinstance(criteria, list):
        return None
    allowed_levels = {"source_asserted", "eamos_hint"}
    for code in codes:
        for row in criteria:
            if not isinstance(row, dict):
                continue
            if (
                row.get("code") == code
                and row.get("state") == "met"
                and row.get("assertion_level") in allowed_levels
            ):
                return ReportCallBadge(text=code, kind="acmg")
    return None


def _first_met_acmg_badge(
    payload: ReportPayload,
    codes: tuple[str, ...],
) -> ReportCallBadge | None:
    scaffold = payload.acmg_criteria_scaffold
    if scaffold is None:
        return None
    for code in codes:
        if any(item.code == code and item.verdict == "met" for item in scaffold.criteria):
            return ReportCallBadge(text=code, kind="acmg")
    return None


def _population_group_from_summary(
    item: dict[str, Any],
) -> PopulationFrequencyAncestryGroup | None:
    group_id = str(item.get("id") or "").strip()
    if group_id not in CORE_GNOMAD_GROUPS:
        return None
    ac = _as_int(item.get("allele_count", item.get("ac")))
    an = _as_int(item.get("allele_number", item.get("an")))
    af = _as_float(item.get("allele_frequency", item.get("af")))
    if af is None and ac is not None and an:
        af = ac / an
    return PopulationFrequencyAncestryGroup(
        id=group_id,
        allele_count=ac,
        allele_number=an,
        allele_frequency=af,
        homozygote_count=_as_int(item.get("homozygote_count")),
    )


def _age_distribution_from_summary(value: Any) -> PopulationAgeDistribution | None:
    if not isinstance(value, dict):
        return None
    het = _age_histogram_from_summary(value.get("het"))
    hom = _age_histogram_from_summary(value.get("hom"))
    if het is None and hom is None:
        return None
    return PopulationAgeDistribution(het=het, hom=hom)


def _age_distributions_from_summary(value: Any) -> list[PopulationSequencingAgeDistribution]:
    if not isinstance(value, list):
        return []
    distributions: list[PopulationSequencingAgeDistribution] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        age_distribution = _age_distribution_from_summary(item.get("age_distribution"))
        if age_distribution is None:
            continue
        sequencing_type = str(item.get("sequencing_type") or "unknown")
        if sequencing_type not in {"joint", "exome", "genome", "unknown"}:
            sequencing_type = "unknown"
        distributions.append(
            PopulationSequencingAgeDistribution(
                sequencing_type=sequencing_type,  # type: ignore[arg-type]
                age_distribution=age_distribution,
            )
        )
    return distributions


def _age_histogram_from_summary(value: Any) -> PopulationAgeHistogram | None:
    if not isinstance(value, dict):
        return None
    return PopulationAgeHistogram(
        bin_edges=[
            float(item) for item in value.get("bin_edges", []) if isinstance(item, int | float)
        ],
        bin_freq=[int(item) for item in value.get("bin_freq", []) if isinstance(item, int)],
        n_smaller=_as_int(value.get("n_smaller")),
        n_larger=_as_int(value.get("n_larger")),
    )


def _combined_status(evidence_statuses: dict[str, str], source_names: tuple[str, ...]) -> str:
    statuses = [evidence_statuses.get(name) for name in source_names if evidence_statuses.get(name)]
    if not statuses:
        return "missing"
    if any(status == "live" for status in statuses):
        return "live"
    if any(status == "cache" for status in statuses):
        return "cache"
    if any(status == "fixture" for status in statuses):
        return "fixture"
    return statuses[0]


def _classification_theme(label: str) -> str:
    normalized = label.lower()
    if "conflict" in normalized or "uncertain" in normalized or normalized == "vus":
        return "caution_orange_state"
    if "benign" in normalized:
        return "benign_green_state"
    if "pathogenic" in normalized:
        return "risk_red_state"
    return "neutral_slate_state"


def _title_classification(value: str) -> str:
    normalized = value.strip().replace("_", " ")
    if not normalized:
        return "Unavailable"
    if normalized.lower() in {"vus", "uncertain significance"}:
        return "VUS"
    return normalized.title()


def _format_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    percent = value * 100
    if percent == 0:
        return "0%"
    if percent < 0.01:
        return f"{percent:.3g}%"
    if percent < 1:
        return f"{percent:.3f}%"
    return f"{percent:.2f}%"


def _format_score(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value == 0:
        return "0"
    if abs(value) < 1:
        return f"{value:.3g}"
    return f"{value:g}"


def _dedupe_strings(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
