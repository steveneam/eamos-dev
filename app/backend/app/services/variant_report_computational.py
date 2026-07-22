from __future__ import annotations

from typing import Any

from app.schemas.run import (
    ComputationalDeepDiveSection,
    ComputationalPredictorRow,
    ReportPayload,
    SourceProvenance,
)
from app.services.computational_calibration import calibration_field_values
from app.services.report_provenance import (
    provenance_for_source,
    source_provenance_from_mapping,
)
from app.services.report_source_truth import report_source_category, report_source_is_weak
from app.services.variant_report_helpers import (
    _dedupe_provenance,
    _dedupe_text,
    _dict_or_empty,
    _filter_provenance,
    _list_of_dicts,
    _optional_bool,
    _optional_float,
    _optional_text,
    _string_list,
)


def build_computational_deep_dive(
    *,
    payload: ReportPayload,
    evidence_map: dict[str, dict[str, Any]],
    evidence_statuses: dict[str, str],
    provenance: list[SourceProvenance],
) -> ComputationalDeepDiveSection:
    computational = evidence_map.get("computational_annotations", {})
    if computational:
        section = _computational_deep_dive_from_annotations(
            computational,
            status=evidence_statuses.get("computational_annotations", "missing"),
            provenance=provenance,
        )
        if section is not None:
            return section

    legacy_fixture_mode = any(
        report_source_category(evidence_statuses.get(source, "missing")) == "fixture"
        for source in ("computational_annotations", "spliceai", "vep")
    )
    if legacy_fixture_mode:
        return _computational_deep_dive_from_legacy_predictions(payload, provenance)
    return ComputationalDeepDiveSection(
        warnings=["computational_predictors_unavailable"],
    )


def _computational_deep_dive_from_legacy_predictions(
    payload: ReportPayload,
    provenance: list[SourceProvenance],
) -> ComputationalDeepDiveSection:
    predictions = payload.in_silico_predictions
    rows: list[ComputationalPredictorRow] = []
    spliceai_max_delta: float | None = None
    spliceai_consequence: str | None = None
    if predictions is not None:
        for card in predictions.cards:
            rows.append(
                ComputationalPredictorRow(
                    name=card.name,
                    score=card.score,
                    threshold=card.threshold,
                    interpretation=card.verdict_label or card.verdict,
                    source=card.name,
                    source_url=card.source_url,
                    **calibration_field_values(card.name, card.score),
                )
            )
            if card.name == "SpliceAI":
                spliceai_max_delta = card.score
                spliceai_consequence = card.verdict_label or card.verdict

    warnings = []
    if not rows:
        warnings.append("computational_predictors_unavailable")
    return ComputationalDeepDiveSection(
        predictors=rows,
        spliceai_max_delta=spliceai_max_delta,
        spliceai_consequence=spliceai_consequence,
        conservation=[],
        provenance=_filter_provenance(provenance, {"spliceai", "vep"}),
        warnings=warnings,
    )


def _computational_deep_dive_from_annotations(
    computational: dict[str, Any],
    *,
    status: str,
    provenance: list[SourceProvenance],
) -> ComputationalDeepDiveSection | None:
    weak_source = report_source_is_weak(status)
    raw_predictors = _list_of_dicts(computational.get("predictors"))
    accepted_predictors = (
        [item for item in raw_predictors if _independently_source_backed_predictor(item)]
        if weak_source
        else raw_predictors
    )
    rejected_fixture_rows = len(accepted_predictors) != len(raw_predictors)
    rows = [
        row
        for row in (_computational_row_from_dict(item) for item in accepted_predictors)
        if row is not None
    ]

    spliceai = _dict_or_empty(computational.get("spliceai"))
    if weak_source and spliceai and not _independently_source_backed_predictor(spliceai):
        spliceai = {}
        rejected_fixture_rows = True
    spliceai_max_delta = _optional_float(spliceai.get("max_delta"))
    spliceai_consequence = _optional_text(spliceai.get("consequence"))
    spliceai_row = _spliceai_row(spliceai)
    if spliceai_row is not None and spliceai_row.name not in {row.name for row in rows}:
        rows.append(spliceai_row)

    raw_conservation = _list_of_dicts(computational.get("conservation"))
    accepted_conservation = (
        [item for item in raw_conservation if _independently_source_backed_predictor(item)]
        if weak_source
        else raw_conservation
    )
    rejected_fixture_rows = rejected_fixture_rows or (
        len(accepted_conservation) != len(raw_conservation)
    )
    conservation = [
        row
        for row in (_computational_row_from_dict(item) for item in accepted_conservation)
        if row is not None
    ]
    warnings = _dedupe_text(
        [
            *_string_list(computational.get("warnings")),
            *(["computational_fixture_rows_rejected"] if rejected_fixture_rows else []),
        ]
    )
    if not rows and not conservation and spliceai_max_delta is None:
        warnings.append("computational_predictors_unavailable")
        if not computational.get("predictors") and not computational.get("spliceai"):
            return None

    return ComputationalDeepDiveSection(
        predictors=rows,
        spliceai_max_delta=spliceai_max_delta,
        spliceai_consequence=spliceai_consequence,
        conservation=conservation,
        provenance=_dedupe_provenance(
            [
                *_filter_provenance(provenance, {"computational_annotations", "spliceai"}),
                *_computational_annotations_provenance(computational, status=status),
            ]
        ),
        warnings=_dedupe_text(warnings),
    )


def _independently_source_backed_predictor(item: dict[str, Any]) -> bool:
    source_id = _optional_text(item.get("source_id"))
    source = (_optional_text(item.get("source")) or "").strip().lower()
    version = _optional_text(item.get("version"))
    return bool(
        source_id
        and "fixture" not in source_id.casefold()
        and version
        and item.get("public_serialization_allowed") is True
        and source != "fixture"
    )


def _computational_row_from_dict(item: dict[str, Any]) -> ComputationalPredictorRow | None:
    name = _optional_text(item.get("name"))
    if not name:
        return None
    score = _score_value(item.get("score"))
    source = _optional_text(item.get("source")) or name
    calibration = calibration_field_values(name, score)
    return ComputationalPredictorRow(
        name=name,
        score=score,
        threshold=_score_value(item.get("threshold")),
        interpretation=_optional_text(item.get("interpretation")),
        source=source,
        source_id=_optional_text(item.get("source_id")),
        version=_optional_text(item.get("version")),
        **calibration,
        source_url=_optional_text(item.get("source_url")),
        public_serialization_allowed=_optional_bool(item.get("public_serialization_allowed")),
        launch_gate=_optional_text(item.get("launch_gate")),
        warnings=_string_list(item.get("warnings")),
    )


def _spliceai_row(spliceai: dict[str, Any]) -> ComputationalPredictorRow | None:
    if not spliceai:
        return None
    max_delta = _optional_float(spliceai.get("max_delta"))
    component_scores = _dict_or_empty(spliceai.get("component_scores"))
    if max_delta is None and not component_scores:
        return None
    consequence = _optional_text(spliceai.get("consequence"))
    component_text = _spliceai_component_text(component_scores)
    interpretation_parts = []
    if consequence:
        interpretation_parts.append(f"Max delta consequence: {consequence}.")
    if component_text:
        interpretation_parts.append(f"Component scores: {component_text}.")
    return ComputationalPredictorRow(
        name="SpliceAI",
        score=max_delta,
        threshold=_score_value(spliceai.get("threshold")),
        interpretation=" ".join(interpretation_parts) or None,
        source=_optional_text(spliceai.get("source")) or "SpliceAI",
        source_id=_optional_text(spliceai.get("source_id")),
        version=_optional_text(spliceai.get("version")),
        **calibration_field_values("SpliceAI", max_delta),
        source_url=_optional_text(spliceai.get("source_url")),
        public_serialization_allowed=_optional_bool(spliceai.get("public_serialization_allowed")),
        launch_gate=_optional_text(spliceai.get("launch_gate")),
        warnings=_string_list(spliceai.get("warnings")),
    )


def _spliceai_component_text(component_scores: dict[str, Any]) -> str:
    components: list[str] = []
    for key in ("DS_AL", "DS_DL", "DS_AG", "DS_DG"):
        score = _optional_float(component_scores.get(key))
        if score is not None:
            components.append(f"{key}={score:g}")
    return ", ".join(components)


def _score_value(value: Any) -> str | float | None:
    numeric = _optional_float(value)
    if numeric is not None:
        return numeric
    return _optional_text(value)


def _computational_annotations_provenance(
    summary: dict[str, Any],
    *,
    status: str,
) -> list[SourceProvenance]:
    raw = summary.get("provenance")
    provenance: list[SourceProvenance] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            provenance.append(source_provenance_from_mapping(item))
    if provenance:
        return provenance
    gene = _optional_text(summary.get("gene"))
    return [
        provenance_for_source(
            "computational_annotations",
            status=status,
            query={"gene": gene} if gene else {},
            warnings=_string_list(summary.get("warnings")),
        )
    ]
