from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from app.tools.base import FixtureBackedTool, ToolResult

SPLICEAI_SOURCE_URL = "https://spliceailookup.broadinstitute.org/"
DEFAULT_SPLICEAI_THRESHOLD = 0.2
ALPHAMISSENSE_KEYS = {"alphamissense", "alpha_missense", "alpha missense"}
SPLICEAI_COMPONENTS = {
    "DS_AG": "acceptor_gain",
    "DS_AL": "acceptor_loss",
    "DS_DG": "donor_gain",
    "DS_DL": "donor_loss",
}
SPLICEAI_DISTANCES = {
    "DP_AG": "acceptor_gain_distance",
    "DP_AL": "acceptor_loss_distance",
    "DP_DG": "donor_gain_distance",
    "DP_DL": "donor_loss_distance",
}


@dataclass(frozen=True)
class ComputationalVariantIdentity:
    gene: str = ""
    variant_id: str = ""
    genomic_hg38: str = ""
    genomic_hgvs: str = ""
    transcript_hgvs: str = ""
    cdna: str = ""
    protein_change: str = ""
    dbsnp_rsid: str = ""

    @property
    def request_identity(self) -> dict[str, str]:
        return {
            key: value
            for key, value in {
                "gene": self.gene,
                "variant_id": self.variant_id,
                "genomic_hg38": self.genomic_hg38,
                "genomic_hgvs": self.genomic_hgvs,
                "transcript_hgvs": self.transcript_hgvs,
                "cdna": self.cdna,
                "protein_change": self.protein_change,
                "dbsnp_rsid": self.dbsnp_rsid,
            }.items()
            if value
        }

    @property
    def has_variant_level_identifier(self) -> bool:
        return any(
            (
                self.variant_id,
                self.genomic_hg38,
                self.genomic_hgvs,
                self.transcript_hgvs,
                self.cdna,
                self.protein_change,
                self.dbsnp_rsid,
            )
        )


class ComputationalAnnotationsTool(FixtureBackedTool):
    source = "computational_annotations"
    fixture_name = "computational_annotations_fixtures.json"

    def get_evidence(self, variant=None) -> ToolResult:
        identity = _identity_from_variant(variant)
        if not identity.gene or not identity.has_variant_level_identifier:
            warnings = ["computational_annotations_requires_variant_identity"]
            return ToolResult(
                source=self.source,
                status="missing",
                request_identity=identity.request_identity,
                summary=_unavailable_summary(identity, warnings),
                warnings=warnings,
                raw=None,
                source_url=_source_search_url(identity),
            )

        record = _fixture_record(self.load_fixture(), identity)
        if not self.settings.use_real_apis:
            return _result_from_record(
                status="fixture" if record else "missing",
                identity=identity,
                record=record,
                missing_warning="computational_annotations_not_found",
            )

        if record is None:
            return _result_from_record(
                status="missing",
                identity=identity,
                record=None,
                missing_warning="computational_annotations_not_found",
            )

        return _result_from_record(
            status="fallback",
            identity=identity,
            record=record,
            extra_warnings=["computational_annotations_curated_fixture_snapshot"],
        )


def normalize_computational_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize dbNSFP/MyVariant-like predictor blocks into report row dicts."""

    clean_record = deepcopy(record)
    predictors, filtered_warnings = _predictor_rows(clean_record)
    spliceai = _spliceai_summary(clean_record)
    spliceai_row = _spliceai_predictor_row(spliceai)
    if spliceai_row is not None:
        predictors.insert(0, spliceai_row)

    conservation, conservation_filtered_warnings = _conservation_rows(clean_record)
    warnings = _dedupe(
        [
            *_string_list(clean_record.get("warnings")),
            *filtered_warnings,
            *conservation_filtered_warnings,
        ]
    )
    if not predictors:
        warnings.append("computational_predictors_unavailable")

    return {
        "gene": _text(clean_record.get("gene")) or "",
        "variant_id": _text(clean_record.get("variant_id"))
        or _text(clean_record.get("genomic_hg38"))
        or "",
        "genomic_hg38": _text(clean_record.get("genomic_hg38")) or "",
        "transcript_hgvs": _first_text(clean_record.get("transcript_hgvs")) or "",
        "protein_change": _first_text(clean_record.get("protein_change")) or "",
        "predictors": predictors,
        "spliceai": spliceai,
        "spliceai_max_delta": spliceai.get("max_delta") if spliceai else None,
        "spliceai_consequence": spliceai.get("consequence") if spliceai else None,
        "conservation": conservation,
        "provenance": _provenance(clean_record),
        "warnings": _dedupe(warnings),
    }


def _identity_from_variant(variant) -> ComputationalVariantIdentity:
    if variant is None:
        return ComputationalVariantIdentity()
    transcript_hgvs = _text(getattr(variant, "transcript_hgvs", None)) or ""
    return ComputationalVariantIdentity(
        gene=(_text(getattr(variant, "gene", None)) or "").upper(),
        variant_id=_text(getattr(variant, "variant_id", None)) or "",
        genomic_hg38=_text(getattr(variant, "genomic_hg38", None)) or "",
        genomic_hgvs=_text(getattr(variant, "genomic_hgvs", None)) or "",
        transcript_hgvs=transcript_hgvs,
        cdna=_extract_cdna(transcript_hgvs),
        protein_change=_text(getattr(variant, "protein_change", None)) or "",
        dbsnp_rsid=_text(getattr(variant, "dbsnp_rsid", None)) or "",
    )


def _unavailable_summary(
    identity: ComputationalVariantIdentity,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "gene": identity.gene,
        "variant_id": identity.variant_id or identity.genomic_hg38,
        "genomic_hg38": identity.genomic_hg38,
        "transcript_hgvs": identity.transcript_hgvs,
        "protein_change": identity.protein_change,
        "predictors": [],
        "spliceai": None,
        "spliceai_max_delta": None,
        "spliceai_consequence": None,
        "conservation": [],
        "provenance": [],
        "warnings": list(warnings or []),
    }


def _fixture_record(
    fixture: dict[str, Any],
    identity: ComputationalVariantIdentity,
) -> dict[str, Any] | None:
    records = fixture.get("records") or fixture.get("variants")
    if not isinstance(records, list):
        return None
    for record in records:
        if not isinstance(record, dict):
            continue
        if _record_matches(record, identity):
            return deepcopy(record)
    return None


def _record_matches(record: dict[str, Any], identity: ComputationalVariantIdentity) -> bool:
    record_gene = (_text(record.get("gene")) or "").upper()
    if identity.gene and record_gene and record_gene != identity.gene:
        return False

    record_identifiers = {_identifier_key(item) for item in _record_identifiers(record)}
    request_identifiers = {_identifier_key(item) for item in _identity_identifiers(identity)}
    record_identifiers.discard("")
    request_identifiers.discard("")
    return bool(record_identifiers & request_identifiers)


def _record_identifiers(record: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "variant_id",
        "genomic_hg38",
        "genomic_hgvs",
        "transcript_hgvs",
        "protein_change",
        "dbsnp_rsid",
        "aliases",
    ):
        values.extend(_string_list(record.get(key)))
    return values


def _identity_identifiers(identity: ComputationalVariantIdentity) -> list[str]:
    return [
        identity.variant_id,
        identity.genomic_hg38,
        identity.genomic_hgvs,
        identity.transcript_hgvs,
        identity.cdna,
        identity.protein_change,
        identity.dbsnp_rsid,
    ]


def _result_from_record(
    *,
    status: str,
    identity: ComputationalVariantIdentity,
    record: dict[str, Any] | None,
    missing_warning: str | None = None,
    extra_warnings: list[str] | None = None,
) -> ToolResult:
    warnings = list(extra_warnings or [])
    if record is None:
        if missing_warning:
            warnings.append(missing_warning)
        return ToolResult(
            source=ComputationalAnnotationsTool.source,
            status=status,
            request_identity=identity.request_identity,
            summary=_unavailable_summary(identity, warnings),
            warnings=warnings,
            raw=None,
            source_url=_source_search_url(identity),
        )

    summary = normalize_computational_record(record)
    summary["warnings"] = _dedupe([*summary.get("warnings", []), *warnings])
    return ToolResult(
        source=ComputationalAnnotationsTool.source,
        status=status,
        request_identity=identity.request_identity,
        summary=summary,
        warnings=warnings,
        raw=_sanitize_raw_record(record),
        source_url=_primary_source_url(summary) or _source_search_url(identity),
    )


def _predictor_rows(record: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for source_name, block in _annotation_blocks(record):
        for item in _list_of_dicts(block.get("predictors")):
            row, filtered = _row_from_metric(item, source_name=source_name, block=block)
            if filtered:
                warnings.append("alphamissense_on_hold")
                continue
            if row is not None:
                rows.append(row)
    return _dedupe_rows(rows), _dedupe(warnings)


def _conservation_rows(record: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for source_name, block in _annotation_blocks(record):
        for item in _list_of_dicts(block.get("conservation")):
            row, filtered = _row_from_metric(item, source_name=source_name, block=block)
            if filtered:
                warnings.append("alphamissense_on_hold")
                continue
            if row is not None:
                rows.append(row)
    return _dedupe_rows(rows), _dedupe(warnings)


def _row_from_metric(
    item: dict[str, Any],
    *,
    source_name: str,
    block: dict[str, Any],
) -> tuple[dict[str, Any] | None, bool]:
    name = _text(item.get("name") or item.get("metric"))
    if not name:
        return None, False
    if _is_alphamissense(name):
        return None, True
    row = {
        "name": name,
        "score": _score_value(item.get("score")),
        "threshold": _score_value(item.get("threshold")),
        "interpretation": _text(
            item.get("interpretation") or item.get("prediction") or item.get("verdict")
        ),
        "source": _text(item.get("source")) or _source_label(source_name),
        "version": _text(item.get("version")) or _text(block.get("version")),
        "source_url": _text(item.get("source_url")) or _text(block.get("source_url")),
        "warnings": _string_list(item.get("warnings")),
    }
    return row, False


def _spliceai_summary(record: dict[str, Any]) -> dict[str, Any] | None:
    spliceai = _spliceai_block(record)
    if not spliceai:
        return None

    component_scores = _component_values(spliceai, SPLICEAI_COMPONENTS)
    if not component_scores:
        return None

    max_component = max(component_scores, key=lambda key: component_scores[key])
    max_delta = component_scores[max_component]
    consequence = _text(spliceai.get("consequence")) or SPLICEAI_COMPONENTS[max_component]
    return {
        "component_scores": component_scores,
        "distance_positions": _component_values(spliceai, SPLICEAI_DISTANCES, as_float=False),
        "max_delta": max_delta,
        "max_component": max_component,
        "consequence": consequence,
        "distance": _optional_int(spliceai.get("distance")),
        "mask": _optional_int(spliceai.get("mask")),
        "source": "SpliceAI",
        "version": _text(spliceai.get("version")),
        "source_url": _text(spliceai.get("source_url")) or SPLICEAI_SOURCE_URL,
        "warnings": _string_list(spliceai.get("warnings")),
    }


def _spliceai_predictor_row(spliceai: dict[str, Any] | None) -> dict[str, Any] | None:
    if not spliceai:
        return None
    max_delta = _score_value(spliceai.get("max_delta"))
    if max_delta is None:
        return None
    return {
        "name": "SpliceAI",
        "score": max_delta,
        "threshold": DEFAULT_SPLICEAI_THRESHOLD,
        "interpretation": _text(spliceai.get("consequence")),
        "source": "SpliceAI",
        "version": _text(spliceai.get("version")),
        "source_url": _text(spliceai.get("source_url")) or SPLICEAI_SOURCE_URL,
        "warnings": _string_list(spliceai.get("warnings")),
    }


def _spliceai_block(record: dict[str, Any]) -> dict[str, Any]:
    direct = record.get("spliceai")
    if isinstance(direct, dict):
        return direct
    sources = record.get("sources")
    if isinstance(sources, dict):
        block = sources.get("spliceai") or sources.get("SpliceAI")
        if isinstance(block, dict):
            return block
    summary = record.get("summary")
    if isinstance(summary, dict) and any(key in summary for key in SPLICEAI_COMPONENTS):
        return summary
    return {}


def _annotation_blocks(record: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    blocks = [("record", record)]
    sources = record.get("sources")
    if isinstance(sources, dict):
        for source_name, block in sources.items():
            if not isinstance(block, dict) or _is_alphamissense(source_name):
                continue
            blocks.append((source_name, block))
    return blocks


def _provenance(record: dict[str, Any]) -> list[dict[str, Any]]:
    provenance = record.get("provenance")
    if not isinstance(provenance, list):
        return []
    return [
        item
        for item in provenance
        if isinstance(item, dict) and not _is_alphamissense(item.get("source"))
    ]


def _sanitize_raw_record(record: dict[str, Any]) -> dict[str, Any]:
    clean = deepcopy(record)
    for block in [clean, *_source_dicts(clean)]:
        if isinstance(block.get("predictors"), list):
            block["predictors"] = [
                item
                for item in block["predictors"]
                if not (
                    isinstance(item, dict)
                    and _is_alphamissense(item.get("name") or item.get("metric"))
                )
            ]
        if isinstance(block.get("conservation"), list):
            block["conservation"] = [
                item
                for item in block["conservation"]
                if not (
                    isinstance(item, dict)
                    and _is_alphamissense(item.get("name") or item.get("metric"))
                )
            ]
    sources = clean.get("sources")
    if isinstance(sources, dict):
        for source_name in list(sources):
            if _is_alphamissense(source_name):
                del sources[source_name]
    if isinstance(clean.get("provenance"), list):
        clean["provenance"] = [
            item
            for item in clean["provenance"]
            if not (isinstance(item, dict) and _is_alphamissense(item.get("source")))
        ]
    return clean


def _source_dicts(record: dict[str, Any]) -> list[dict[str, Any]]:
    sources = record.get("sources")
    if not isinstance(sources, dict):
        return []
    return [block for block in sources.values() if isinstance(block, dict)]


def _component_values(
    block: dict[str, Any],
    keys: dict[str, str],
    *,
    as_float: bool = True,
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    nested_key = "component_scores" if as_float else "component_positions"
    nested = block.get(nested_key)
    if not isinstance(nested, dict):
        nested = {}
    for canonical, alias in keys.items():
        value = block.get(canonical)
        if value is None:
            value = block.get(alias)
        if value is None:
            value = nested.get(canonical)
        if value is None:
            value = nested.get(alias)
        if value is None:
            continue
        parsed = _optional_float(value) if as_float else _optional_int(value)
        if parsed is not None:
            values[canonical] = parsed
    return values


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str | None]] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        key = (str(row.get("name")), str(row.get("source")), row.get("version"))
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def _primary_source_url(summary: dict[str, Any]) -> str | None:
    for item in summary.get("provenance", []):
        if isinstance(item, dict):
            source_url = _text(item.get("source_url"))
            if source_url:
                return source_url
    for row in [*summary.get("predictors", []), *summary.get("conservation", [])]:
        if isinstance(row, dict):
            source_url = _text(row.get("source_url"))
            if source_url:
                return source_url
    return None


def _source_search_url(identity: ComputationalVariantIdentity) -> str | None:
    variant = identity.genomic_hg38 or identity.variant_id or identity.genomic_hgvs
    if variant:
        return f"https://myvariant.info/v1/query?q={quote(variant)}"
    if identity.gene:
        return f"https://myvariant.info/v1/query?q={quote(identity.gene)}"
    return None


def _source_label(source_name: str) -> str:
    labels = {
        "dbnsfp": "dbNSFP",
        "myvariant": "MyVariant.info",
        "cadd": "CADD",
        "primateai_3d": "PrimateAI-3D",
        "spliceai": "SpliceAI",
    }
    return labels.get(source_name.lower(), source_name)


def _identifier_key(value: str | None) -> str:
    text = (value or "").strip().lower()
    if text.startswith("chr"):
        text = text[3:]
    return text.replace(" ", "")


def _extract_cdna(transcript_hgvs: str) -> str:
    if not transcript_hgvs:
        return ""
    return transcript_hgvs.split(":")[-1]


def _is_alphamissense(value: Any) -> bool:
    text = (str(value) if value is not None else "").strip().lower()
    if text in ALPHAMISSENSE_KEYS:
        return True
    return text.replace("-", "").replace("_", "").replace(" ", "") == "alphamissense"


def _dedupe(items: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [text for text in (_text(item) for item in value) if text]
    text = _text(value)
    return [text] if text else []


def _first_text(value: Any) -> str | None:
    items = _string_list(value)
    return items[0] if items else None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("description", "label", "name", "value"):
            text = _text(value.get(key))
            if text:
                return text
        return None
    text = str(value).strip()
    return text or None


def _score_value(value: Any) -> str | float | None:
    if value is None or value == "":
        return None
    number = _optional_float(value)
    if number is not None:
        return number
    return _text(value)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
