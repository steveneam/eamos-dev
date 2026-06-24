from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

import httpx

from app.services.clingen_local import ClinGenLocalStore
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

    def get_evidence(self, variant=None, *, refresh: bool = False) -> ToolResult:
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

        if self.settings.clingen_local_enabled and not refresh:
            local_result = self._get_local_evidence(
                gene=gene,
                terms=terms,
                request_identity=request_identity,
            )
            if local_result is not None:
                return local_result

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

    def _get_local_evidence(
        self,
        *,
        gene: str,
        terms: list[str],
        request_identity: dict[str, Any],
    ) -> ToolResult | None:
        local_warnings: list[str] = []
        try:
            store = ClinGenLocalStore(
                _settings_path(self.settings, self.settings.clingen_local_sqlite_path),
                manifest_path=_settings_path(
                    self.settings,
                    self.settings.clingen_local_manifest_path,
                ),
                enabled=True,
            )
            records, inspection, needs_live_fallback = store.search_records(
                gene=gene,
                terms=terms,
                limit=self.settings.clingen_local_max_results,
                verify_checksum=False,
            )
        except Exception as exc:
            if self.settings.use_real_apis and self.settings.clingen_local_fallback_on_no_hit:
                return None
            return ToolResult(
                source=self.source,
                status="fallback",
                request_identity=request_identity,
                summary=_unavailable_summary(gene),
                warnings=[f"clingen_local_failed:{type(exc).__name__}"],
                raw=None,
                source_url=_erepo_url(self.settings.clingen_erepo_base_url),
            )

        if inspection.ready:
            local_warnings.extend(inspection.warnings)
        else:
            local_warnings.append(f"clingen_local_unavailable:{inspection.status}")

        if records:
            identity_records = _filter_variant_identity_records(records, terms)
            if records and not identity_records:
                local_warnings.append("clingen_local_candidate_rejected_by_variant_identity_guard")
            if (
                records
                and not identity_records
                and self.settings.use_real_apis
                and self.settings.clingen_local_fallback_on_no_hit
            ):
                return None
            records = identity_records

        if records:
            return _result_from_records(
                source=self.source,
                status="local",
                request_identity=request_identity,
                records=records,
                base_url=self.settings.clingen_erepo_base_url,
                warnings=local_warnings,
                source_version=inspection.source_version,
            )

        can_live_fallback = (
            self.settings.use_real_apis
            and self.settings.clingen_local_fallback_on_no_hit
            and (needs_live_fallback or not inspection.ready)
        )
        if can_live_fallback:
            return None

        return _result_from_records(
            source=self.source,
            status="missing",
            request_identity=request_identity,
            records=[],
            base_url=self.settings.clingen_erepo_base_url,
            not_found_warning="clingen_local_variant_not_found",
            warnings=local_warnings,
            source_version=inspection.source_version,
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
        return _filter_variant_identity_records(records, terms)


def cached_clingen_result_matches_variant(result: ToolResult, variant: Any) -> bool:
    """Revalidate a cached VCEP result before it can attach to a report."""

    terms = _variant_terms(variant)
    if not terms:
        return False

    summary = result.summary if isinstance(result.summary, dict) else {}
    for candidate in (
        summary.get("identity_match"),
        _nested_identity_match(summary, "expert_panel", "provenance", "identity_match"),
    ):
        if _identity_match_matches_terms(candidate, terms):
            return True

    records = _cached_raw_records(result.raw)
    return bool(records and _filter_variant_identity_records(records, terms))


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
    gene_records = [
        record
        for record in records
        if isinstance(record, dict) and _record_gene_matches(record, gene)
    ]
    if not terms:
        return gene_records
    return _filter_variant_identity_records(gene_records, terms)


def _record_matches(record: dict[str, Any], gene: str, terms: list[str]) -> bool:
    if not _record_gene_matches(record, gene):
        return False
    if not terms:
        record_gene = str(record.get("gene") or record.get("geneSymbol") or "").strip().upper()
        return bool(gene and record_gene == gene)
    return _strict_variant_record_matches(record, terms)


def _record_gene_matches(record: dict[str, Any], gene: str) -> bool:
    record_gene = str(record.get("gene") or record.get("geneSymbol") or "").strip().upper()
    if gene and record_gene and record_gene != gene:
        return False
    return True


def _filter_variant_identity_records(
    records: list[dict[str, Any]], terms: list[str]
) -> list[dict[str, Any]]:
    if not terms:
        return records
    matched: list[dict[str, Any]] = []
    for record in records:
        identity_match = _identity_match_for_record(record, terms)
        if identity_match is None or not identity_match.get("auto_attach_allowed"):
            continue
        enriched = dict(record)
        enriched["_eamos_identity_match"] = identity_match
        matched.append(enriched)
    return matched


def _strict_variant_record_matches(record: dict[str, Any], terms: list[str]) -> bool:
    identity_match = _identity_match_for_record(record, terms)
    return bool(identity_match and identity_match.get("auto_attach_allowed"))


def _cached_raw_records(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        records = raw.get("records")
    else:
        records = raw
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def _nested_identity_match(value: dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _identity_match_matches_terms(value: Any, terms: list[str]) -> bool:
    if not isinstance(value, dict) or value.get("auto_attach_allowed") is not True:
        return False
    request_terms = [_normalize_identity_token(term) for term in terms]
    request_terms = [term for term in request_terms if term]
    if not request_terms:
        return False
    matched_values = [
        value.get("normalized_matched"),
        value.get("matched"),
        value.get("normalized_requested"),
        value.get("requested"),
    ]
    normalized_values = [
        _normalize_identity_token(item) for item in matched_values if _text(item)
    ]
    return any(
        _identity_term_matches(identity_value, request_term)
        for identity_value in normalized_values
        for request_term in request_terms
    )


def _record_identity_values(record: dict[str, Any]) -> list[str]:
    return [value for _, value, _ in _record_identity_values_with_fields(record)]


def _record_identity_values_with_fields(record: dict[str, Any]) -> list[tuple[str, str, str]]:
    identity_keys = {
        "caid",
        "canonicalalleleid",
        "classificationid",
        "clinvarvariationid",
        "cvid",
        "hgvs",
        "hgvsc",
        "hgvsg",
        "id",
        "preferredtitle",
        "preferredvartitle",
        "uuid",
        "varianttitle",
        "variationid",
    }
    values_with_fields: list[tuple[str, str, str]] = []

    def collect(value: Any, key: str | None = None) -> None:
        key_norm = _normalize_key(key)
        if isinstance(value, dict):
            for child_key, child in value.items():
                collect(child, str(child_key))
            return
        if isinstance(value, (list, tuple, set)):
            for child in value:
                collect(child, key)
            return
        if value is None:
            return
        if key_norm in identity_keys or (key_norm is not None and "hgvs" in key_norm):
            text = _text(value)
            if text:
                values_with_fields.append((key or "unknown", text, _identity_tier(key_norm, text)))

    collect(record)
    return values_with_fields


def _identity_match_for_record(
    record: dict[str, Any],
    terms: list[str],
) -> dict[str, Any] | None:
    identity_values = _record_identity_values_with_fields(record)
    if not identity_values:
        return None

    request_terms = [(term, _normalize_identity_token(term)) for term in terms]
    request_terms = [(term, normalized) for term, normalized in request_terms if normalized]
    if not request_terms:
        return None

    for requested, normalized_requested in request_terms:
        for source_field, matched, tier in identity_values:
            normalized_matched = _normalize_identity_token(matched)
            if not normalized_matched:
                continue
            if _identity_term_matches(normalized_matched, normalized_requested):
                return {
                    "tier": tier,
                    "source_field": source_field,
                    "requested": requested,
                    "matched": matched,
                    "normalized_requested": normalized_requested,
                    "normalized_matched": normalized_matched,
                    "auto_attach_allowed": tier != "candidate_text",
                }
    return None


def _identity_tier(key_norm: str | None, value: str) -> str:
    key = key_norm or ""
    normalized = _normalize_identity_token(value)
    if key in {"classificationid", "id", "uuid"}:
        return "assertion_id"
    if "caid" in key or "canonicalalleleid" in key or normalized.startswith("ca"):
        return "caid"
    if "clinvar" in key or "variationid" in key or key == "cvid":
        return "clinvar_variation_id"
    if "vrs" in key:
        return "vrs"
    if "spdi" in key:
        return "spdi"
    if ":g." in normalized or re.match(r"^(?:chr)?[0-9xy]+-\d+-[acgtn]+-[acgtn]+$", normalized):
        return "genomic_hgvs"
    if ":c." in normalized or re.search(r"\bc\.", normalized):
        return "transcript_hgvs"
    if "hgvs" in key or "title" in key:
        return "candidate_text"
    return "candidate_text"


def _normalize_key(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _normalize_identity_token(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\s+", "", text).lower()
    return re.sub(r"[^a-z0-9.>:_+\-*?]+", "", text)


def _identity_term_matches(identity_value: str, request_term: str) -> bool:
    if identity_value == request_term:
        return True
    start = 0
    while True:
        index = identity_value.find(request_term, start)
        if index == -1:
            return False
        end = index + len(request_term)
        before_ok = index == 0 or not _is_identity_token_char(identity_value[index - 1])
        after_ok = end == len(identity_value) or not _is_identity_token_char(identity_value[end])
        if before_ok and after_ok:
            return True
        start = index + 1


def _is_identity_token_char(value: str) -> bool:
    return value.isalnum() or value in {".", "_", "+", "-", ">", "*", "?"}


def _result_from_records(
    *,
    source: str,
    status: str,
    request_identity: dict[str, Any],
    records: list[dict[str, Any]],
    base_url: str,
    not_found_warning: str | None = None,
    warnings: list[str] | None = None,
    source_version: str | None = None,
) -> ToolResult:
    summary = _summary_from_records(records, request_identity.get("gene"))
    result_warnings = list(warnings or [])
    if not records and not_found_warning:
        result_warnings.append(not_found_warning)
    return ToolResult(
        source=source,
        status=status,
        request_identity=request_identity,
        summary=summary,
        warnings=_dedupe(result_warnings),
        raw={"records": records},
        source_url=_record_source_url(records[0], base_url) if records else _erepo_url(base_url),
        source_version=source_version or _records_source_version(records),
    )


def _summary_from_records(records: list[dict[str, Any]], gene: str | None) -> dict[str, Any]:
    if not records:
        return _unavailable_summary(gene)
    record = records[0]
    identity_match = record.get("_eamos_identity_match")
    if not isinstance(identity_match, dict):
        identity_match = None
    return {
        "gene": _text(record.get("gene") or gene),
        "classification": _classification(record) or "Unavailable",
        "review_status": _review_status(record),
        "conditions": _conditions(record),
        "accession": _record_id(record),
        "identity_match": identity_match,
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
    identity_match = record.get("_eamos_identity_match")
    if not isinstance(identity_match, dict):
        identity_match = None

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
            "identity_match": identity_match,
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
            or record.get("ep")
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


def _settings_path(settings, path) -> Any:
    return path if path.is_absolute() else settings.backend_root / path


def _records_source_version(records: list[dict[str, Any]]) -> str | None:
    for record in records:
        version = _text(record.get("sourceVersion") or record.get("source_version"))
        if version:
            return version
    return None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


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
