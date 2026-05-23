from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal
from urllib.parse import quote_plus

import httpx

from app.core.config import Settings
from app.tools.base import ToolResult

CLINICAL_TRIALS_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
CLINICAL_TRIALS_STUDY_URL = "https://clinicaltrials.gov/study"
CLINICAL_TRIALS_SEARCH_URL = "https://clinicaltrials.gov/search"
ACTIVE_TRIAL_STATUSES = ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING")
DISCOVERY_ONLY_WARNING = "clinical_trials_discovery_only:not_eligibility"
GENE_LEVEL_WARNING = "clinical_trials_gene_level_match:not_variant_specific"
DISEASE_LEVEL_WARNING = "clinical_trials_disease_level_match:not_variant_specific"
QUERY_SCOPE_WARNING = "clinical_trials_match_level_from_query_scope"

ReportMatchLevel = Literal["variant_level", "gene_level", "disease_level", "unavailable"]


@dataclass(frozen=True)
class ClinicalTrialQuery:
    query_term: str
    requested_match_level: ReportMatchLevel
    variant_aliases: tuple[str, ...] = ()
    gene_terms: tuple[str, ...] = ()
    disease_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClinicalTrialMatch:
    nct_id: str
    title: str
    status: str | None
    phase: str | None
    conditions: tuple[str, ...]
    interventions: tuple[str, ...]
    locations: tuple[str, ...]
    match_level: ReportMatchLevel
    matched_terms: tuple[str, ...]
    source_url: str
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("conditions", "interventions", "locations", "matched_terms", "warnings"):
            data[key] = list(data[key])
        return data


# Offline fixtures for the legacy text summary path. Structured rows require
# ClinicalTrials.gov v2 JSON so they are not fabricated from these summaries.
_FIXTURE_MAP: dict[str, str] = {
    "RPE65": (
        "13 active/not-yet ClinicalTrials.gov records found for RPE65 in the "
        "development snapshot:\n"
        "- NCT06088992 - ACTIVE_NOT_RECRUITING - Leber Congenital Amaurosis "
        "Inherited Blindness of Gene Therapy Trial (LIGHT)\n"
        "- NCT06196827 - ACTIVE_NOT_RECRUITING - Safety and tolerability of "
        "LX101 for inherited retinal dystrophy associated with RPE65\n"
        "- NCT04516369 - ACTIVE_NOT_RECRUITING - Efficacy and safety of "
        "voretigene neparvovec in Japanese patients\n"
        "- NCT07265895 - NOT_YET_RECRUITING - Inherited retinal diseases "
        "natural history and genotype-phenotype correlations\n"
        "- NCT00481546 - ACTIVE_NOT_RECRUITING - Phase 1 gene vector trial in "
        "patients with retinal disease due to RPE65 mutations\n"
        "- NCT00999609 - ACTIVE_NOT_RECRUITING - Safety and efficacy study in "
        "subjects with Leber congenital amaurosis\n"
        "- NCT07054632 - ACTIVE_NOT_RECRUITING - Efficacy and safety of LX101 "
        "for inherited retinal dystrophy\n"
        "- NCT03602820 - ACTIVE_NOT_RECRUITING - Long-term follow-up after "
        "voretigene neparvovec-rzyl\n"
        "- NCT06212297 - ACTIVE_NOT_RECRUITING - Fellow-eye study of LX101\n"
        "- NCT05858983 - RECRUITING - Gene therapy in subjects with biallelic "
        "RPE65 mutation-associated inherited retinal dystrophy\n"
        "- NCT06024057 - NOT_YET_RECRUITING - Expanded clinical study "
        "evaluating AAV2-RPE65 gene therapy\n"
        "- NCT05906953 - RECRUITING - Safety and efficacy trial of HG004 for "
        "Leber congenital amaurosis\n"
        "- NCT01208389 - ACTIVE_NOT_RECRUITING - Phase 1 follow-on study of "
        "AAV2-hRPE65v2 vector"
    ),
    "RPGR": (
        "2 active trials found for RPGR:\n"
        "- NCT03252847 - Phase I/II - RECRUITING - "
        "AGTC-501 gene therapy for RPGR-associated X-linked retinitis pigmentosa\n"
        "- NCT04671433 - Phase I/II - RECRUITING - "
        "AAV-RPGR subretinal gene therapy dose-escalation study"
    ),
    "ABCA4": (
        "1 active trial found for ABCA4:\n"
        "- NCT04483440 - Phase I/II - RECRUITING - "
        "4D-150 subretinal AAV delivery for ABCA4-associated Stargardt disease"
    ),
    "CNGA3": (
        "1 active trial found for CNGA3:\n"
        "- NCT02610582 - Phase I/II - ACTIVE_NOT_RECRUITING - "
        "rAAV.hCNGA3 gene therapy for CNGA3-associated achromatopsia"
    ),
}

_FIXTURE_GENERIC = (
    "Live ClinicalTrials.gov data is not available in offline mode. "
    "Search ClinicalTrials.gov with the gene name to find active trials. "
    "Filter by status: RECRUITING or ACTIVE_NOT_RECRUITING."
)

_PHASE_LABELS = {
    "EARLY_PHASE1": "Early Phase 1",
    "PHASE1": "Phase 1",
    "PHASE2": "Phase 2",
    "PHASE3": "Phase 3",
    "PHASE4": "Phase 4",
    "PHASE1_PHASE2": "Phase 1/2",
    "PHASE2_PHASE3": "Phase 2/3",
    "NA": "N/A",
}


class ClinicalTrialsTool:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_trials_summary(self, gene: str) -> str:
        gene = gene.strip().upper()
        if not self.settings.use_real_apis:
            return _FIXTURE_MAP.get(gene, _FIXTURE_GENERIC)

        result = self.get_trial_matches(gene=gene, limit=15)
        rows = result.summary.get("trial_rows", [])
        if not rows:
            if result.status == "fallback":
                return _FIXTURE_MAP.get(
                    gene,
                    "Clinical trials lookup unavailable for "
                    f"{gene}. Check ClinicalTrials.gov directly.",
                )
            return f"No active trials found for {gene} on ClinicalTrials.gov."

        lines = [f"{len(rows)} active/not-yet ClinicalTrials.gov record(s) found for {gene}:"]
        for row in rows:
            phase = row.get("phase") or "Phase N/A"
            status = row.get("status") or "Unknown"
            lines.append(f"- {row['nct_id']} - {phase} - {status} - {row['title']}")
        return "\n".join(lines)

    def get_trial_matches(
        self,
        variant: Any | None = None,
        *,
        gene: str | None = None,
        variant_aliases: tuple[str, ...] | list[str] | None = None,
        disease_terms: tuple[str, ...] | list[str] | None = None,
        limit: int = 10,
    ) -> ToolResult:
        resolved_gene = _normalize_gene(gene or getattr(variant, "gene", None))
        aliases = _dedupe(
            [
                *_string_list(variant_aliases),
                *_variant_aliases_from_variant(variant),
            ]
        )
        diseases = tuple(_dedupe(_string_list(disease_terms)))
        query_plan = tuple(_build_query_plan(resolved_gene, aliases, diseases))
        request_identity: dict[str, Any] = {
            "gene": resolved_gene,
            "variant_aliases": list(aliases),
            "disease_terms": list(diseases),
            "query_plan": [query.query_term for query in query_plan],
        }

        if not query_plan:
            warnings = ["clinical_trials_requires_gene_variant_or_disease"]
            return ToolResult(
                source="clinical_trials",
                status="missing",
                request_identity=request_identity,
                summary=_summary([], None, warnings),
                warnings=warnings,
                raw=None,
            )

        if not self.settings.use_real_apis:
            warnings = ["structured_clinical_trials_require_live_api"]
            return ToolResult(
                source="clinical_trials",
                status="fixture",
                request_identity=request_identity,
                summary=_summary([], query_plan[0], warnings),
                warnings=warnings,
                raw=None,
                source_url=_search_url(query_plan[0].query_term),
            )

        try:
            rows, selected_query, warnings = self._fetch_structured_live(query_plan, limit=limit)
        except Exception as exc:
            warnings = [f"clinical_trials_fetch_failed:{type(exc).__name__}"]
            return ToolResult(
                source="clinical_trials",
                status="fallback",
                request_identity=request_identity,
                summary=_summary([], query_plan[0], warnings),
                warnings=warnings,
                raw=None,
                source_url=_search_url(query_plan[0].query_term),
            )

        status = "live" if rows else "missing"
        return ToolResult(
            source="clinical_trials",
            status=status,
            request_identity={
                **request_identity,
                "selected_query": selected_query.query_term if selected_query else None,
            },
            summary=_summary(rows, selected_query or query_plan[0], warnings),
            warnings=warnings,
            raw=[row.as_dict() for row in rows],
            source_url=_search_url((selected_query or query_plan[0]).query_term),
        )

    def _fetch_structured_live(
        self,
        query_plan: tuple[ClinicalTrialQuery, ...],
        *,
        limit: int,
    ) -> tuple[list[ClinicalTrialMatch], ClinicalTrialQuery | None, list[str]]:
        warnings: list[str] = []
        for query in query_plan:
            payload = self._fetch_v2_payload(query.query_term, limit=limit)
            parsed = parse_clinicaltrials_v2_studies(payload, query=query, limit=limit)
            rows = _dedupe_trials(parsed)
            if query.requested_match_level == "variant_level":
                rows = [row for row in rows if row.match_level == "variant_level"]
                if not rows:
                    warnings.append("clinical_trials_variant_level_not_found")
                    continue
            if rows:
                if rows[0].match_level in {"gene_level", "disease_level"}:
                    warnings.append("variant_level_trial_not_found:using_lower_match_level")
                return rows[:limit], query, _dedupe(warnings)

        warnings.append("clinical_trials_no_active_matches")
        return [], None, _dedupe(warnings)

    def _fetch_v2_payload(self, query_term: str, *, limit: int) -> dict[str, Any]:
        response = httpx.get(
            CLINICAL_TRIALS_BASE_URL,
            params={
                "query.term": query_term,
                "filter.overallStatus": ",".join(ACTIVE_TRIAL_STATUSES),
                "pageSize": max(1, min(limit, 50)),
                "format": "json",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


def parse_clinicaltrials_v2_studies(
    payload: dict[str, Any],
    *,
    query: ClinicalTrialQuery | None = None,
    limit: int | None = None,
) -> list[ClinicalTrialMatch]:
    rows: list[ClinicalTrialMatch] = []
    for study in _study_list(payload):
        row = parse_clinicaltrials_v2_study(study, query=query)
        if row is None:
            continue
        rows.append(row)
        if limit is not None and len(rows) >= limit:
            break
    return rows


def parse_clinicaltrials_v2_study(
    study: dict[str, Any],
    *,
    query: ClinicalTrialQuery | None = None,
) -> ClinicalTrialMatch | None:
    protocol = _dict(study.get("protocolSection"))
    identification = _dict(protocol.get("identificationModule"))
    status_module = _dict(protocol.get("statusModule"))
    design = _dict(protocol.get("designModule"))
    conditions_module = _dict(protocol.get("conditionsModule"))
    interventions_module = _dict(protocol.get("armsInterventionsModule"))
    locations_module = _dict(protocol.get("contactsLocationsModule"))

    nct_id = _text(identification.get("nctId"))
    if not nct_id:
        return None

    title = (
        _text(identification.get("briefTitle"))
        or _text(identification.get("officialTitle"))
        or "Untitled clinical trial"
    )
    conditions = tuple(_string_list(conditions_module.get("conditions")))
    interventions = tuple(_intervention_names(interventions_module))
    locations = tuple(_location_summaries(locations_module))
    match_level, matched_terms, match_warnings = _match_level(study, query)

    warnings = [DISCOVERY_ONLY_WARNING, *match_warnings]
    if match_level == "gene_level":
        warnings.append(GENE_LEVEL_WARNING)
    elif match_level == "disease_level":
        warnings.append(DISEASE_LEVEL_WARNING)

    return ClinicalTrialMatch(
        nct_id=nct_id,
        title=title,
        status=_text(status_module.get("overallStatus")),
        phase=_phase_label(design.get("phases")),
        conditions=conditions,
        interventions=interventions,
        locations=locations,
        match_level=match_level,
        matched_terms=tuple(matched_terms),
        source_url=f"{CLINICAL_TRIALS_STUDY_URL}/{quote_plus(nct_id)}",
        warnings=tuple(_dedupe(warnings)),
    )


def _summary(
    rows: list[ClinicalTrialMatch],
    query: ClinicalTrialQuery | None,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "trial_rows": [row.as_dict() for row in rows],
        "total": len(rows),
        "query_term": query.query_term if query else None,
        "source_url": _search_url(query.query_term) if query else None,
        "warnings": _dedupe(warnings),
        "disclaimer": "ClinicalTrials.gov rows are discovery links, not eligibility guidance.",
    }


def _build_query_plan(
    gene: str | None,
    variant_aliases: tuple[str, ...],
    disease_terms: tuple[str, ...],
) -> list[ClinicalTrialQuery]:
    plan: list[ClinicalTrialQuery] = []
    gene_terms = (gene,) if gene else ()
    if variant_aliases:
        plan.append(
            ClinicalTrialQuery(
                query_term=" OR ".join(f'"{alias}"' for alias in variant_aliases),
                requested_match_level="variant_level",
                variant_aliases=variant_aliases,
                gene_terms=gene_terms,
                disease_terms=disease_terms,
            )
        )
    if gene and disease_terms:
        plan.append(
            ClinicalTrialQuery(
                query_term=f"{gene} " + " OR ".join(f'"{term}"' for term in disease_terms[:3]),
                requested_match_level="gene_level",
                variant_aliases=variant_aliases,
                gene_terms=gene_terms,
                disease_terms=disease_terms,
            )
        )
    if gene:
        plan.append(
            ClinicalTrialQuery(
                query_term=gene,
                requested_match_level="gene_level",
                variant_aliases=variant_aliases,
                gene_terms=gene_terms,
                disease_terms=disease_terms,
            )
        )
    elif disease_terms:
        plan.append(
            ClinicalTrialQuery(
                query_term=" OR ".join(f'"{term}"' for term in disease_terms[:3]),
                requested_match_level="disease_level",
                variant_aliases=variant_aliases,
                disease_terms=disease_terms,
            )
        )
    return plan


def _match_level(
    study: dict[str, Any],
    query: ClinicalTrialQuery | None,
) -> tuple[ReportMatchLevel, list[str], list[str]]:
    if query is None:
        return "unavailable", [], [QUERY_SCOPE_WARNING]

    text_blob = _normalized_match_text(_flatten_strings(study))
    variant_matches = _matched_terms(text_blob, query.variant_aliases)
    if variant_matches:
        return "variant_level", variant_matches, []

    gene_matches = _matched_terms(text_blob, query.gene_terms)
    if gene_matches:
        return "gene_level", gene_matches, []

    disease_matches = _matched_terms(text_blob, query.disease_terms)
    if disease_matches:
        return "disease_level", disease_matches, []

    if query.requested_match_level in {"gene_level", "disease_level"}:
        return query.requested_match_level, [], [QUERY_SCOPE_WARNING]
    return "unavailable", [], [QUERY_SCOPE_WARNING]


def _matched_terms(text_blob: str, terms: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for term in terms:
        normalized = _normalized_match_text([term])
        if normalized and normalized in text_blob:
            matches.append(term)
    return _dedupe(matches)


def _study_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    studies = payload.get("studies")
    if not isinstance(studies, list):
        return []
    return [study for study in studies if isinstance(study, dict)]


def _intervention_names(module: dict[str, Any]) -> list[str]:
    interventions = module.get("interventions")
    if not isinstance(interventions, list):
        return []
    names: list[str] = []
    for item in interventions:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name")) or _text(item.get("interventionName"))
        if name:
            names.append(name)
    return _dedupe(names)


def _location_summaries(module: dict[str, Any], *, limit: int = 5) -> list[str]:
    locations = module.get("locations")
    if not isinstance(locations, list):
        return []

    summaries: list[str] = []
    for location in locations[:limit]:
        if not isinstance(location, dict):
            continue
        facility = _text(location.get("facility"))
        place = ", ".join(
            _dedupe(
                [
                    _text(location.get("city")),
                    _text(location.get("state")),
                    _text(location.get("country")),
                ]
            )
        )
        status = _text(location.get("status"))
        parts = [part for part in (facility, place, status) if part]
        if parts:
            summaries.append(" - ".join(parts))

    remaining = len(locations) - limit
    if remaining > 0:
        summaries.append(f"{remaining} additional location(s) listed")
    return summaries


def _phase_label(value: Any) -> str | None:
    phases = _string_list(value)
    if not phases:
        return None
    labels = [_PHASE_LABELS.get(phase.upper(), phase.replace("_", " ").title()) for phase in phases]
    return "/".join(_dedupe(labels))


def _variant_aliases_from_variant(variant: Any | None) -> tuple[str, ...]:
    if variant is None:
        return ()
    aliases: list[str] = []
    for attr in (
        "transcript_hgvs",
        "hgvs",
        "cdna",
        "protein_change",
        "dbsnp_rsid",
        "genomic_hgvs",
        "genomic_hg38",
    ):
        aliases.extend(_string_list(getattr(variant, attr, None)))
    for alias in tuple(aliases):
        if ":" in alias:
            aliases.append(alias.rsplit(":", 1)[-1])
    return tuple(_dedupe(aliases))


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for nested in value.values():
            result.extend(_flatten_strings(nested))
        return result
    if isinstance(value, list):
        result = []
        for nested in value:
            result.extend(_flatten_strings(nested))
        return result
    return []


def _normalized_match_text(values: list[str] | tuple[str, ...]) -> str:
    return " ".join(" ".join(value.casefold().split()) for value in values if value)


def _dedupe(items: list[str | None] | tuple[str | None, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _dedupe_trials(rows: list[ClinicalTrialMatch]) -> list[ClinicalTrialMatch]:
    seen: set[str] = set()
    result: list[ClinicalTrialMatch] = []
    for row in rows:
        if row.nct_id in seen:
            continue
        seen.add(row.nct_id)
        result.append(row)
    return result


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list) or isinstance(value, tuple):
        return [text for text in (_text(item) for item in value) if text]
    text = _text(value)
    return [text] if text else []


def _normalize_gene(value: Any) -> str | None:
    text = _text(value)
    return text.upper() if text else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _search_url(query_term: str) -> str:
    return f"{CLINICAL_TRIALS_SEARCH_URL}?term={quote_plus(query_term)}"
