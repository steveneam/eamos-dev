from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.tools.base import FixtureBackedTool, ToolResult


def _unavailable_summary(gene: str | None) -> dict[str, Any]:
    return {
        "gene": gene or "",
        "classification": "Unavailable",
        "review_status": "not found",
        "conditions": [],
        "accession": None,
        "criteria": [],
        "assertion_method": None,
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
    }


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
