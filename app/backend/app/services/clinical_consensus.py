from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings
from app.schemas.run import (
    AcmgCriteriaScaffold,
    AcmgWorksheetCriterion,
    AcmgWorksheetLedger,
)
from app.services import clinvar_vcv
from app.services.clinvar_vcv import (
    DEFAULT_CLINVAR_VCV_MAX_XML_BYTES,
    EutilsClinVarVcvClient,
)
from app.services.report_source_truth import report_source_allows_payload

_CLINGEN_SOURCE = "ClinGen Evidence Repository"
_CLINVAR_SOURCE = "ClinVar VCV"
_EAMOS_SOURCE = "Eamos worksheet scaffold"
_UNAVAILABLE_CLASSIFICATIONS = {"", "unavailable", "not found", "none"}
_ACMG_CODE_RE = re.compile(
    r"\b(PVS1|PS[1-4]|PM[1-6]|PP[1-5]|BA1|BS[1-4]|BP[1-7])" r"(?:_([A-Za-z][A-Za-z0-9]*))?\b",
    flags=re.IGNORECASE,
)
_RAW_POPULATION_METRIC_RE = re.compile(
    r"("
    r"\bgnomad\b|"
    r"\b(?:AF|AC|AN)\s*[=:]?\s*\d|"
    r"\ballele[_ -]?(?:frequency|count|number|denominator)\b|"
    r"\bpopmax\b|"
    r"\bhom(?:ozygote)?(?:[_ -]?count)?\b|"
    r"\b(?:afr|ami|amr|asj|eas|fin|mid|nfe|remaining|sas)\b|"
    r"\bage[_ -]?distribution\b|\bbin[_ -]?(?:edges|freq)\b|\bn_(?:smaller|larger)\b|"
    r">\s*250k\s+alleles\b"
    r")",
    flags=re.IGNORECASE,
)
_SANITIZED_POPULATION_RATIONALE = (
    "Population-frequency criterion summarized without raw source metrics; "
    "review Section 3 population frequency detail for source values."
)


class ClinVarVcvClinicalClient(Protocol):
    def fetch_vcv_xml(self, variation_id: str) -> str:
        """Return ClinVar VCV XML for a ClinVar Variation ID."""


@dataclass(frozen=True)
class ClinicalConsensusResult:
    summary: dict[str, Any]
    ledger: AcmgWorksheetLedger
    status: str
    warnings: list[str]


class ClinicalConsensusBuilder:
    """Build clinical consensus and ACMG worksheet rows from source assertions."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        clinvar_client: ClinVarVcvClinicalClient | None = None,
        clinvar_vcv_max_xml_bytes: int = DEFAULT_CLINVAR_VCV_MAX_XML_BYTES,
    ) -> None:
        self.settings = settings
        self.clinvar_vcv_max_xml_bytes = clinvar_vcv_max_xml_bytes
        self.clinvar_client = clinvar_client or (
            EutilsClinVarVcvClient(
                base_url=settings.clinvar_base_url,
                max_xml_bytes=clinvar_vcv_max_xml_bytes,
            )
            if settings is not None
            else None
        )

    def build_for_lookup(
        self,
        variant: Any,
        payload,
        evidence_map: dict[str, dict[str, Any]],
        *,
        evidence_raw: dict[str, Any] | None = None,
        source_statuses: dict[str, str] | None = None,
        allow_live: bool = False,
    ) -> ClinicalConsensusResult:
        warnings: list[str] = []
        raw = evidence_raw if evidence_raw is not None else {}
        statuses = source_statuses or {}
        clingen_allowed = _source_allowed("clingen", source_statuses)
        clinvar_allowed = _source_allowed("clinvar", source_statuses)
        clinvar_raw = raw.get("clinvar") if clinvar_allowed else None
        clingen_records = _coerce_clingen_records(raw.get("clingen")) if clingen_allowed else []
        clinvar_summary = evidence_map.get("clinvar", {}) if clinvar_allowed else {}

        clingen_consensus = _clingen_consensus(clingen_records)
        clinvar_consensus = _clinvar_consensus(clinvar_summary)
        clinvar_xml = clinvar_vcv.clinvar_vcv_xml_from_raw(clinvar_raw)
        if (
            not clinvar_xml
            and allow_live
            and self.clinvar_client is not None
            and not _source_failed("clinvar", statuses)
        ):
            variation_id = _clinvar_variation_id(clinvar_raw, clinvar_summary)
            if variation_id:
                try:
                    clinvar_xml = self.clinvar_client.fetch_vcv_xml(variation_id)
                    clinvar_vcv.store_clinvar_vcv_xml(clinvar_raw, clinvar_xml)
                except Exception as exc:
                    warnings.append(f"clinical_consensus_clinvar_vcv_failed:{type(exc).__name__}")
        clinvar_parse_result = clinvar_vcv.clinvar_vcv_parse_result(
            clinvar_raw,
            xml_text=clinvar_xml,
            max_xml_bytes=self.clinvar_vcv_max_xml_bytes,
        )

        source_rows = [
            *_clingen_criteria_rows(clingen_records),
            *_clinvar_criteria_rows(clinvar_parse_result, warnings),
        ]

        classification = None
        classification_source = None
        review_status = None
        accession = None
        source_url = None
        status = "missing"
        if clingen_consensus["classification"]:
            classification = clingen_consensus["classification"]
            classification_source = "ClinGen"
            review_status = clingen_consensus["review_status"]
            accession = clingen_consensus["accession"]
            source_url = clingen_consensus["source_url"]
            status = statuses.get("clingen", "missing")
        elif clinvar_consensus["classification"]:
            classification = clinvar_consensus["classification"]
            classification_source = "ClinVar"
            review_status = clinvar_consensus["review_status"]
            accession = clinvar_consensus["accession"]
            source_url = clinvar_consensus["source_url"]
            status = statuses.get("clinvar", "missing")
        else:
            warnings.append("clinical_consensus_unavailable")

        fixture_mode = source_statuses is None or any(
            str(statuses.get(source) or "").strip().lower() == "fixture"
            for source in ("clingen", "clinvar")
        )
        scaffold_rows = _eamos_scaffold_rows(payload.acmg_criteria_scaffold)
        if not fixture_mode:
            scaffold_rows = [row for row in scaffold_rows if row.assertion_level == "not_assessed"]
        criteria = _merge_criteria_rows(
            [
                *source_rows,
                *scaffold_rows,
            ]
        )
        ledger = AcmgWorksheetLedger(
            classification=classification,
            classification_source=classification_source,
            criteria=criteria,
            synthesis=_synthesis(classification_source),
            disclaimer=_disclaimer(payload.acmg_criteria_scaffold),
        )
        summary = {
            "classification": classification,
            "classification_source": classification_source,
            "review_status": review_status,
            "accession": accession,
            "source_url": source_url,
            "source_asserted_criteria": [
                row.code for row in criteria if row.assertion_level == "source_asserted"
            ],
            "acmg_worksheet": ledger.model_dump(mode="json"),
            "warnings": warnings,
        }
        return ClinicalConsensusResult(
            summary=summary,
            ledger=ledger,
            status=status,
            warnings=warnings,
        )


def _coerce_clingen_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        records = value.get("records", value.get("data"))
        if isinstance(records, list):
            return [record for record in records if isinstance(record, dict)]
        if _classification_from_record(value) or _criteria_from_record(value):
            return [value]
    if isinstance(value, list):
        return [record for record in value if isinstance(record, dict)]
    return []


def _clingen_consensus(records: list[dict[str, Any]]) -> dict[str, str | None]:
    for record in records:
        classification = _classification_from_record(record)
        if _usable_classification(classification):
            return {
                "classification": classification,
                "review_status": _review_status_from_record(record),
                "accession": _record_id(record),
                "source_url": _source_url_from_record(record),
            }
    return {
        "classification": None,
        "review_status": None,
        "accession": None,
        "source_url": None,
    }


def _clinvar_consensus(summary: dict[str, Any]) -> dict[str, str | None]:
    classification = _text(summary.get("classification"))
    if not _usable_classification(classification):
        classification = None
    return {
        "classification": classification,
        "review_status": _text(summary.get("review_status")),
        "accession": _text(summary.get("accession")),
        "source_url": _clinvar_source_url(summary),
    }


def _clingen_criteria_rows(records: list[dict[str, Any]]) -> list[AcmgWorksheetCriterion]:
    rows: list[AcmgWorksheetCriterion] = []
    for record in records:
        rationale = _text(record.get("summaryDesc") or record.get("description"))
        evidence_refs = [ref for ref in (_record_id(record),) if ref]
        for value in _criteria_from_record(record):
            parsed = _parse_acmg_code(value)
            if parsed is None:
                continue
            code, strength = parsed
            rows.append(
                AcmgWorksheetCriterion(
                    code=code,
                    state="met",
                    strength=strength,
                    assertion_level="source_asserted",
                    rationale=sanitize_acmg_rationale(
                        rationale or f"ClinGen source-asserted {value}."
                    ),
                    source=_CLINGEN_SOURCE,
                    evidence_refs=evidence_refs,
                )
            )
    return rows


def _clinvar_criteria_rows(
    parse_result: clinvar_vcv.ClinVarVcvParseResult,
    warnings: list[str],
) -> list[AcmgWorksheetCriterion]:
    if parse_result.error_code == "xml_too_large":
        warnings.append("clinical_consensus_clinvar_vcv_too_large")
        return []
    if parse_result.error_code == "parse_failed":
        warnings.append("clinical_consensus_clinvar_vcv_parse_failed")
        return []
    if parse_result.extraction is None:
        return []

    rows: list[AcmgWorksheetCriterion] = []
    for text in parse_result.extraction.texts_for(("Comment", "Attribute", "Description")):
        text = _normalize_space(text)
        if not text:
            continue
        for sentence in _split_sentences(text):
            for match in _ACMG_CODE_RE.finditer(sentence):
                code = match.group(1).upper()
                strength = _normalize_strength(match.group(2))
                rows.append(
                    AcmgWorksheetCriterion(
                        code=code,
                        state=_state_from_context(sentence),
                        strength=strength,
                        assertion_level="source_asserted",
                        rationale=sanitize_acmg_rationale(sentence),
                        source=_CLINVAR_SOURCE,
                        evidence_refs=[f"PMID:{pmid}" for pmid in sorted(_pmids(sentence))],
                    )
                )
    return rows


def _eamos_scaffold_rows(
    scaffold: AcmgCriteriaScaffold | None,
) -> list[AcmgWorksheetCriterion]:
    if scaffold is None:
        return []
    return [
        AcmgWorksheetCriterion(
            code=item.code,
            state=item.verdict,
            assertion_level="not_assessed" if item.verdict == "not_assessed" else "eamos_hint",
            rationale=sanitize_acmg_rationale(item.note),
            source=_EAMOS_SOURCE if item.verdict != "not_assessed" else None,
            evidence_refs=[item.code] if item.note else [],
        )
        for item in scaffold.criteria
    ]


def _merge_criteria_rows(rows: list[AcmgWorksheetCriterion]) -> list[AcmgWorksheetCriterion]:
    merged: dict[str, AcmgWorksheetCriterion] = {}
    order: list[str] = []
    for row in rows:
        if row.code not in merged:
            merged[row.code] = row
            order.append(row.code)
            continue
        existing = merged[row.code]
        if _row_priority(row) < _row_priority(existing):
            merged[row.code] = row
    return [merged[code] for code in order]


def sanitize_acmg_rationale(text: str | None) -> str | None:
    if text is None:
        return None
    if _RAW_POPULATION_METRIC_RE.search(text):
        return _SANITIZED_POPULATION_RATIONALE
    return text


def _row_priority(row: AcmgWorksheetCriterion) -> int:
    if row.assertion_level == "source_asserted" and row.source == _CLINGEN_SOURCE:
        return 0
    if row.assertion_level == "source_asserted":
        return 1
    if row.assertion_level == "eamos_hint":
        return 2
    return 3


def _classification_from_record(record: dict[str, Any]) -> str | None:
    for key in (
        "classification",
        "classificationDescription",
        "provisionalClassification",
        "provisionalVariantClassification",
        "clinicalSignificance",
    ):
        value = _text(record.get(key))
        if value:
            return value
    return None


def _review_status_from_record(record: dict[str, Any]) -> str | None:
    for key in ("reviewStatus", "classificationStatus", "approvalStatus", "status"):
        value = _text(record.get(key))
        if value:
            return value
    return _text(record.get("assertionMethod"))


def _criteria_from_record(record: dict[str, Any]) -> list[str]:
    raw = record.get("metCodes", record.get("metCriteria", record.get("criteria")))
    if isinstance(raw, list):
        return [item for item in (_text(value) for value in raw) if item]
    text = _text(raw)
    return [text] if text else []


def _record_id(record: dict[str, Any]) -> str | None:
    for key in ("uuid", "_id", "id", "classificationId"):
        value = _text(record.get(key))
        if value:
            return value
    return None


def _source_url_from_record(record: dict[str, Any]) -> str | None:
    for key in ("sourceUrl", "url", "iri"):
        value = _text(record.get(key))
        if value:
            return value
    return None


def _parse_acmg_code(value: str) -> tuple[str, str | None] | None:
    match = _ACMG_CODE_RE.search(value)
    if match is None:
        return None
    return match.group(1).upper(), _normalize_strength(match.group(2))


def _normalize_strength(value: str | None) -> str | None:
    if not value:
        return None
    text = value.replace("_", " ").strip()
    return text[:1].upper() + text[1:] if text else None


def _state_from_context(text: str):
    lowered = text.lower()
    if "conflict" in lowered:
        return "conflicting"
    if "not met" in lowered or "not applicable" in lowered:
        return "not_met"
    return "met"


def _clinvar_variation_id(raw: Any, summary: dict[str, Any]) -> str | None:
    if isinstance(raw, dict):
        for key in ("uid", "variation_id", "clinvar_id"):
            value = str(raw.get(key) or "").strip()
            if value.isdigit():
                return value
    accession = str(summary.get("accession") or "").strip()
    match = re.search(r"VCV0*(\d+)", accession, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _clinvar_source_url(summary: dict[str, Any]) -> str | None:
    variation_id = _clinvar_variation_id({}, summary)
    if variation_id:
        return f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{variation_id}/"
    return None


def _source_failed(source: str, source_statuses: dict[str, str]) -> bool:
    return not report_source_allows_payload(source_statuses.get(source, "missing"))


def _source_allowed(
    source: str,
    source_statuses: dict[str, str] | None,
) -> bool:
    if source_statuses is None:
        return True
    return report_source_allows_payload(source_statuses.get(source, "missing"))


def _usable_classification(value: str | None) -> bool:
    return (value or "").strip().lower() not in _UNAVAILABLE_CLASSIFICATIONS


def _synthesis(source: str | None) -> str | None:
    if source == "ClinGen":
        return (
            "ClinGen/VCEP source-reported classification is used ahead of ClinVar; "
            "Eamos criteria remain worksheet hints only."
        )
    if source == "ClinVar":
        return (
            "ClinVar aggregate classification is used because no ClinGen/VCEP "
            "classification was available; Eamos criteria remain worksheet hints only."
        )
    return None


def _disclaimer(scaffold: AcmgCriteriaScaffold | None) -> str:
    if scaffold is not None and scaffold.disclaimer:
        return scaffold.disclaimer
    return "Supporting evidence, not a clinical classification."


def _split_sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[.!?;])\s+", text) if item.strip()]


def _pmids(text: str) -> set[str]:
    return set(re.findall(r"\bPMID:\s*(\d{6,9})\b", text, flags=re.IGNORECASE))


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


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
