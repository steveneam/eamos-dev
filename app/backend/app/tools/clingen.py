from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

import httpx

from app.tools.base import FixtureBackedTool, ToolResult

_CLASSIFICATION_TO_EXPERT_PANEL = {
    "pathogenic": "pathogenic",
    "likely pathogenic": "likely_pathogenic",
    "likely_pathogenic": "likely_pathogenic",
    "uncertain significance": "vus",
    "vus": "vus",
    "likely benign": "likely_benign",
    "likely_benign": "likely_benign",
    "benign": "benign",
    "conflicting": "conflicting",
    "conflicting classifications of pathogenicity": "conflicting",
    "not classified": "not_classified",
    "not_classified": "not_classified",
}
_ACMG_CODE_RE = re.compile(
    r"\b(PVS1|PS[1-4]|PM[1-6]|PP[1-5]|BA1|BS[1-4]|BP[1-7])" r"(?:_([A-Za-z][A-Za-z0-9]*))?\b",
    flags=re.IGNORECASE,
)


def _unavailable_summary(gene: str | None) -> dict[str, Any]:
    return {
        "gene": gene or "",
        "classification": "Unavailable",
        "review_status": "not found",
        "conditions": [],
        "accession": None,
        "criteria": [],
        "assertion_method": None,
        "expert_panel": None,
    }


class ClingenTool(FixtureBackedTool):
    source = "clingen"
    fixture_name = "clingen_fixtures.json"

    def get_evidence(self, variant=None) -> ToolResult:
        if variant is None:
            return ToolResult(
                source=self.source,
                status="missing",
                request_identity={},
                summary=_unavailable_summary(None),
                raw={"records": []},
                source_url=_erepo_url(self.settings.clingen_erepo_base_url),
            )

        gene = str(getattr(variant, "gene", "") or "").strip().upper()
        terms = _variant_terms(variant)
        request_identity = {"gene": gene, "terms": terms}

        if not self.settings.use_real_apis:
            records = _matching_fixture_records(self.load_fixture(), gene, terms)
            return _result_from_records(
                source=self.source,
                status="fixture" if records else "missing",
                request_identity=request_identity,
                records=records,
                base_url=self.settings.clingen_erepo_base_url,
            )

        try:
            records = self._fetch_live(gene=gene, terms=terms)
        except Exception as exc:
            return ToolResult(
                source=self.source,
                status="fallback",
                request_identity=request_identity,
                summary=_unavailable_summary(gene),
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                raw=None,
                source_url=_erepo_url(self.settings.clingen_erepo_base_url),
            )

        return _result_from_records(
            source=self.source,
            status="live",
            request_identity=request_identity,
            records=records,
            base_url=self.settings.clingen_erepo_base_url,
            not_found_warning="clingen_variant_not_found",
        )

    def _fetch_live(self, *, gene: str, terms: list[str]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for term in terms:
            params = {
                "columns": "gene,hgvs",
                "values": f"{gene},{term}",
                "matchTypes": "exact,contains",
                "matchMode": "and",
                "pgSize": "10",
                "pg": "1",
            }
            url = (
                f"{self.settings.clingen_erepo_base_url.rstrip('/')}"
                f"/api/summary/classifications?{urlencode(params, safe=',():>')}"
            )
            response = httpx.get(url, timeout=12.0)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list):
                continue
            for record in data:
                if not isinstance(record, dict):
                    continue
                key = str(record.get("uuid") or record.get("_id") or id(record))
                if key in seen:
                    continue
                seen.add(key)
                records.append(record)
        return records


def _variant_terms(variant: Any) -> list[str]:
    terms: list[str] = []
    transcript_hgvs = str(getattr(variant, "transcript_hgvs", "") or "").strip()
    if transcript_hgvs:
        terms.append(transcript_hgvs)
        cdna = transcript_hgvs.split(":")[-1].strip()
        if cdna and cdna != transcript_hgvs:
            terms.append(cdna)

    for attr in ("genomic_hgvs", "genomic_hg38", "protein_change"):
        value = str(getattr(variant, attr, "") or "").strip()
        if value:
            terms.append(value)

    seen: set[str] = set()
    result: list[str] = []
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        result.append(term)
    return result


def _matching_fixture_records(
    fixture: dict[str, Any],
    gene: str,
    terms: list[str],
) -> list[dict[str, Any]]:
    records = fixture.get("records")
    if not isinstance(records, list):
        return []
    return [
        record
        for record in records
        if isinstance(record, dict) and _record_matches(record, gene, terms)
    ]


def _record_matches(record: dict[str, Any], gene: str, terms: list[str]) -> bool:
    record_gene = str(record.get("gene") or record.get("geneSymbol") or "").strip().upper()
    if gene and record_gene and record_gene != gene:
        return False
    if not terms:
        return bool(gene and record_gene == gene)

    searchable = " ".join(
        str(record.get(key) or "")
        for key in (
            "hgvs",
            "hgvsc",
            "hgvsg",
            "preferredTitle",
            "variantTitle",
            "summaryDesc",
        )
    ).lower()
    return any(term.lower() in searchable for term in terms)


def _result_from_records(
    *,
    source: str,
    status: str,
    request_identity: dict[str, Any],
    records: list[dict[str, Any]],
    base_url: str,
    not_found_warning: str | None = None,
) -> ToolResult:
    summary = _summary_from_records(records, request_identity.get("gene"))
    warnings = [not_found_warning] if not records and not_found_warning else []
    return ToolResult(
        source=source,
        status=status,
        request_identity=request_identity,
        summary=summary,
        warnings=warnings,
        raw={"records": records},
        source_url=_record_source_url(records[0], base_url) if records else _erepo_url(base_url),
    )


def _summary_from_records(records: list[dict[str, Any]], gene: str | None) -> dict[str, Any]:
    if not records:
        return _unavailable_summary(gene)
    record = records[0]
    return {
        "gene": _text(record.get("gene") or gene),
        "classification": _classification(record) or "Unavailable",
        "review_status": _review_status(record),
        "conditions": _conditions(record),
        "accession": _record_id(record),
        "criteria": _criteria(record),
        "assertion_method": _text(record.get("assertionMethod") or record.get("criteriaSet")),
        "source_url": _record_source_url(record, ""),
        "expert_panel": _expert_panel(record),
    }


def _expert_panel(record: dict[str, Any]) -> dict[str, Any] | None:
    nested = record.get("expertPanel") or record.get("expert_panel") or {}
    if not isinstance(nested, dict):
        nested = {}

    vcep = _expert_panel_vcep(record, nested)
    criteria = _expert_panel_criteria(record, nested)
    classification = _expert_panel_classification(nested.get("final_classification")) or (
        _expert_panel_classification(_classification(record))
    )
    if classification is None:
        classification = "not_classified"

    nested_provenance = (
        nested.get("provenance") if isinstance(nested.get("provenance"), dict) else {}
    )
    source_url = _text(
        nested.get("source_url") or nested.get("sourceUrl") or nested_provenance.get("source_url")
    ) or _record_source_url(record, "")
    source_version = _text(
        nested.get("source_version")
        or nested.get("sourceVersion")
        or record.get("sourceVersion")
        or record.get("source_version")
    )
    fetched_at = _text(
        nested.get("fetched_at")
        or nested.get("fetchedAt")
        or record.get("fetchedAt")
        or record.get("lastFetchedAt")
        or vcep["last_curated_date"]
    )
    raw_jsonld_ref = _text(nested.get("raw_jsonld_ref") or nested.get("rawJsonLdRef"))
    cache_record_id = _text(nested.get("cache_record_id") or nested.get("cacheRecordId"))

    return {
        "vcep": vcep,
        "final_classification": classification,
        "narrative": _text(nested.get("narrative") or record.get("summaryDesc"))
        or "ClinGen Evidence Repository VCEP assertion is available.",
        "criteria": criteria,
        "source_scope": _text(nested.get("source_scope") or nested.get("sourceScope"))
        or _source_scope(record, vcep),
        "provenance": {
            "source_url": source_url,
            "fetched_at": fetched_at or "unknown",
            "source_version": source_version or "ClinGen Evidence Repository",
            "cache_record_id": cache_record_id,
            "raw_jsonld_ref": raw_jsonld_ref,
        },
        "freshness": "unknown",
        "freshness_reason": None,
    }


def _expert_panel_vcep(record: dict[str, Any], nested: dict[str, Any]) -> dict[str, Any]:
    raw_vcep = nested.get("vcep") if isinstance(nested.get("vcep"), dict) else {}
    assertion_method = _text(record.get("assertionMethod") or record.get("criteriaSet"))
    return {
        "id": _text(
            raw_vcep.get("id")
            or nested.get("vcep_id")
            or nested.get("vcepId")
            or record.get("vcepId")
        )
        or "ClinGen:VCEP",
        "name": _text(
            raw_vcep.get("name")
            or nested.get("vcep_name")
            or nested.get("vcepName")
            or record.get("vcepName")
            or assertion_method
        )
        or "ClinGen Variant Curation Expert Panel",
        "affiliation_id": _text(
            raw_vcep.get("affiliation_id")
            or raw_vcep.get("affiliationId")
            or nested.get("affiliation_id")
            or nested.get("affiliationId")
            or record.get("affiliationId")
        ),
        "last_curated_date": _text(
            raw_vcep.get("last_curated_date")
            or raw_vcep.get("lastCuratedDate")
            or nested.get("last_curated_date")
            or nested.get("lastCuratedDate")
            or record.get("lastCuratedDate")
            or record.get("dateLastEvaluated")
        )
        or "unknown",
        "vcep_url": _text(
            raw_vcep.get("vcep_url")
            or raw_vcep.get("vcepUrl")
            or nested.get("vcep_url")
            or nested.get("vcepUrl")
            or _record_source_url(record, "")
        )
        or _erepo_url(""),
    }


def _expert_panel_criteria(
    record: dict[str, Any],
    nested: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_criteria = nested.get("criteria")
    if isinstance(raw_criteria, list):
        rows = [
            _expert_panel_criterion_from_dict(item)
            for item in raw_criteria
            if isinstance(item, dict)
        ]
        return [row for row in rows if row is not None]

    rationale = _text(record.get("summaryDesc") or record.get("description"))
    evidence_refs = [ref for ref in (_record_id(record),) if ref]
    rows: list[dict[str, Any]] = []
    for value in _criteria(record):
        parsed = _parse_acmg_strength(value)
        if parsed is None:
            continue
        code, applied_strength = parsed
        rows.append(
            {
                "code": code,
                "applied_strength": applied_strength,
                "default_strength": applied_strength,
                "state": "met",
                "assertion_level": "vcep_specified",
                "rationale": rationale or f"ClinGen VCEP source-asserted {applied_strength}.",
                "source": "ClinGen Evidence Repository",
                "evidence_refs": evidence_refs,
                "warnings": [],
            }
        )
    return rows


def _expert_panel_criterion_from_dict(value: dict[str, Any]) -> dict[str, Any] | None:
    code = _text(value.get("code"))
    applied = _text(value.get("applied_strength") or value.get("appliedStrength"))
    default = _text(value.get("default_strength") or value.get("defaultStrength"))
    if not code and applied:
        parsed = _parse_acmg_strength(applied)
        if parsed is not None:
            code, applied = parsed
    if not code:
        return None
    if not applied:
        applied = code
    if not default:
        default = applied
    state = _text(value.get("state")) or "met"
    if state not in {"met", "not_met", "not_assessed", "conflicting"}:
        state = "met"
    evidence_refs = value.get("evidence_refs", value.get("evidenceRefs", []))
    if not isinstance(evidence_refs, list):
        evidence_refs = [evidence_refs]
    warnings = value.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = [warnings]
    return {
        "code": code,
        "applied_strength": applied,
        "default_strength": default,
        "state": state,
        "assertion_level": "vcep_specified",
        "rationale": _text(value.get("rationale")),
        "source": _text(value.get("source")) or "ClinGen Evidence Repository",
        "evidence_refs": [item for item in (_text(item) for item in evidence_refs) if item],
        "warnings": [item for item in (_text(item) for item in warnings) if item],
    }


def _expert_panel_classification(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return _CLASSIFICATION_TO_EXPERT_PANEL.get(
        " ".join(text.replace("_", " ").strip().lower().split())
    )


def _parse_acmg_strength(value: str) -> tuple[str, str] | None:
    match = _ACMG_CODE_RE.search(value)
    if match is None:
        return None
    code = match.group(1).upper()
    strength = match.group(2)
    return code, f"{code}_{strength}" if strength else code


def _source_scope(record: dict[str, Any], vcep: dict[str, Any]) -> str:
    gene = _text(record.get("gene") or record.get("geneSymbol"))
    hgvs = _text(record.get("hgvs") or record.get("hgvsc") or record.get("hgvsg"))
    target = " ".join(item for item in (gene, hgvs) if item)
    if target:
        return f"ClinGen Evidence Repository - {vcep['name']} curation for {target}"
    return f"ClinGen Evidence Repository - {vcep['name']} curation"


def _classification(record: dict[str, Any]) -> str | None:
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


def _review_status(record: dict[str, Any]) -> str | None:
    for key in ("reviewStatus", "classificationStatus", "approvalStatus", "status"):
        value = _text(record.get(key))
        if value:
            return value
    return _text(record.get("assertionMethod"))


def _conditions(record: dict[str, Any]) -> list[str]:
    raw = record.get("conditions", record.get("condition"))
    if isinstance(raw, list):
        return [item for item in (_text(value) for value in raw) if item]
    text = _text(raw)
    return [text] if text else []


def _criteria(record: dict[str, Any]) -> list[str]:
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


def _record_source_url(record: dict[str, Any], base_url: str) -> str:
    for key in ("sourceUrl", "url", "iri"):
        value = _text(record.get(key))
        if value:
            return value
    return _erepo_url(base_url)


def _erepo_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/" if base else "https://erepo.clinicalgenome.org/evrepo/"


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
