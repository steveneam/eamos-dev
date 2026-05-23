from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Protocol, cast
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.schemas.run import (
    FunctionalEvidenceCode,
    FunctionalEvidenceDisplayMetrics,
    FunctionalEvidenceSourceBreakdown,
    FunctionalEvidenceSourceTag,
    FunctionalEvidenceSummary,
    FunctionalStudy,
)
from app.services.publication_literature import VariantLiteratureTerms

_FUNCTIONAL_CODES = ("PS3", "BS3")
_FUNCTIONAL_CODE_ORDER = {"PS3": 0, "BS3": 1}
_SOURCE_ORDER = {"clingen": 0, "clinvar": 1, "pubmed": 2}
_SOURCE_FAILED_STATUSES = {"fallback", "error", "failed"}
_FUNCTIONAL_SIGNAL_RE = re.compile(
    r"\b("
    r"functional(?:ly)?|assay|splic(?:e|ing)|mini[- ]?gene|minigene|"
    r"transcript analysis|RNA analysis|RT[- ]?PCR|cDNA analysis|zebrafish|"
    r"mouse model|animal model|cell model|in vitro|in vivo|knock[- ]?in|"
    r"knock[- ]?out|rescue|complementation|enzym(?:e|atic)|enzyme activity|"
    r"retinoid isomerase|protein activity|expression|mRNA|protein function|"
    r"locali[sz]ation|trafficking|stability|folding|western blot|immunoblot|"
    r"immunofluorescence|reporter assay|luciferase|electrophysiology|"
    r"patch clamp|channel activity|transport activity|binding"
    r")\b",
    flags=re.IGNORECASE,
)
_STRONG_FUNCTIONAL_SIGNAL_RE = re.compile(
    r"\b(functional stud(?:y|ies)|functional evidence|functional assay|"
    r"published functional|splicing assay|mini[- ]?gene|minigene|assay|"
    r"transcript analysis|RNA analysis|RT[- ]?PCR|cDNA analysis|enzyme activity|"
    r"enzymatic activity|retinoid isomerase|protein activity|zebrafish|"
    r"mouse model|animal model|cell model|in vitro|in vivo|knock[- ]?in|"
    r"knock[- ]?out|rescue assay|complementation|reporter assay|luciferase|"
    r"electrophysiology|patch clamp|channel activity|transport activity)\b",
    flags=re.IGNORECASE,
)


class ClinGenFunctionalClient(Protocol):
    def search(self, *, gene: str, hgvs: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return ClinGen ERepo classification records for a gene + HGVS term."""


class ClinVarFunctionalClient(Protocol):
    def fetch_vcv_xml(self, variation_id: str) -> str:
        """Return ClinVar VCV XML for a ClinVar Variation ID."""


@dataclass
class _FunctionalHit:
    id: str
    pmid: str | None = None
    citation: str | None = None
    source_tags: set[FunctionalEvidenceSourceTag] = field(default_factory=set)
    evidence_codes: set[FunctionalEvidenceCode] = field(default_factory=set)
    asserted_codes: set[str] = field(default_factory=set)
    snippets: list[str] = field(default_factory=list)


class _FunctionalEvidenceCollector:
    def __init__(self) -> None:
        self.by_pmid: dict[str, _FunctionalHit] = {}
        self.per_source: dict[FunctionalEvidenceSourceTag, set[str]] = {
            "clingen": set(),
            "clinvar": set(),
            "pubmed": set(),
        }

    def add(
        self,
        *,
        source: FunctionalEvidenceSourceTag,
        pmid: str | None = None,
        citation: str | None = None,
        fallback_id: str | None = None,
        evidence_codes: list[FunctionalEvidenceCode] | None = None,
        asserted_codes: list[str] | None = None,
        snippet: str | None = None,
    ) -> None:
        pmid = pmid.strip() if pmid else None
        citation = _normalize_space(citation) if citation else None
        hit_id = pmid or citation or fallback_id
        if not hit_id:
            return
        hit = self.by_pmid.setdefault(hit_id, _FunctionalHit(id=hit_id))
        if pmid and hit.pmid is None:
            hit.pmid = pmid
        if citation and hit.citation is None:
            hit.citation = citation
        hit.source_tags.add(source)
        self.per_source[source].add(hit_id)
        for code in evidence_codes or []:
            hit.evidence_codes.add(code)
        for code in asserted_codes or []:
            hit.asserted_codes.add(code)
        if snippet:
            normalized = _normalize_space(snippet)
            if normalized and normalized not in hit.snippets:
                hit.snippets.append(normalized[:420])

    def summary(self, warnings: list[str]) -> FunctionalEvidenceSummary:
        studies = [
            FunctionalStudy(
                id=hit.id,
                pmid=hit.pmid,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{hit.pmid}/" if hit.pmid else None,
                citation=hit.citation,
                source_tags=sorted(hit.source_tags, key=lambda source: _SOURCE_ORDER[source]),
                evidence_codes=sorted(hit.evidence_codes),
                asserted_codes=sorted(hit.asserted_codes, key=_asserted_code_sort_key),
                snippet=hit.snippets[0] if hit.snippets else None,
            )
            for hit in self.by_pmid.values()
        ]
        studies.sort(
            key=lambda study: (
                study.source_tags[0] if study.source_tags else "",
                study.pmid or study.id,
            )
        )
        evidence_codes = sorted(
            {code for hit in self.by_pmid.values() for code in hit.evidence_codes},
            key=lambda code: _FUNCTIONAL_CODE_ORDER[code],
        )
        source_asserted_codes = sorted(
            {code for hit in self.by_pmid.values() for code in hit.asserted_codes},
            key=_asserted_code_sort_key,
        )
        return FunctionalEvidenceSummary(
            total_count=len(studies),
            source_breakdown=FunctionalEvidenceSourceBreakdown(
                clingen=len(self.per_source["clingen"]),
                clinvar=len(self.per_source["clinvar"]),
                pubmed=len(self.per_source["pubmed"]),
            ),
            evidence_codes=evidence_codes,
            source_asserted_codes=source_asserted_codes,
            display_metrics=_display_metrics(
                total_count=len(studies),
                evidence_codes=evidence_codes,
                asserted_codes=source_asserted_codes,
            ),
            studies=studies,
            warnings=warnings,
        )


class ClinGenERepoFunctionalClient:
    def __init__(self, settings: Settings, *, timeout_seconds: float = 12.0) -> None:
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def search(self, *, gene: str, hgvs: str, limit: int = 10) -> list[dict[str, Any]]:
        params = {
            "columns": "gene,hgvs",
            "values": f"{gene.upper()},{hgvs}",
            "matchTypes": "exact,contains",
            "matchMode": "and",
            "pgSize": str(max(1, min(limit, 50))),
            "pg": "1",
        }
        url = (
            f"{self.settings.clingen_erepo_base_url.rstrip('/')}/api/summary/classifications"
            f"?{urlencode(params, safe=',():')}"
        )
        response = httpx.get(
            url,
            timeout=self.timeout_seconds,
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        records = payload.get("data") if isinstance(payload, dict) else None
        return (
            [record for record in records if isinstance(record, dict)]
            if isinstance(records, list)
            else []
        )


class ClinVarVcvFunctionalClient:
    def __init__(self, settings: Settings, *, timeout_seconds: float = 12.0) -> None:
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def fetch_vcv_xml(self, variation_id: str) -> str:
        response = httpx.get(
            f"{self.settings.clinvar_base_url.rstrip('/')}/efetch.fcgi",
            params={
                "db": "clinvar",
                "id": variation_id,
                "rettype": "vcv",
                "is_variationid": "true",
                "from_esearch": "true",
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.text


class FunctionalEvidenceExtractor:
    """Count functional-study PMIDs without assigning ACMG PS3/BS3 strength."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        clingen_client: ClinGenFunctionalClient | None = None,
        clinvar_client: ClinVarFunctionalClient | None = None,
    ) -> None:
        self.settings = settings
        self.clingen_client = clingen_client or (
            ClinGenERepoFunctionalClient(settings) if settings is not None else None
        )
        self.clinvar_client = clinvar_client or (
            ClinVarVcvFunctionalClient(settings) if settings is not None else None
        )

    def build_for_lookup(
        self,
        variant: Any,
        evidence_map: dict[str, dict[str, Any]],
        *,
        evidence_raw: dict[str, Any] | None = None,
        source_statuses: dict[str, str] | None = None,
        allow_live: bool = False,
    ) -> FunctionalEvidenceSummary:
        warnings: list[str] = []
        collector = _FunctionalEvidenceCollector()
        terms = VariantLiteratureTerms.build(variant)

        self._collect_pubmed_articles(collector, evidence_map, terms)
        self._collect_clingen(
            collector,
            variant,
            evidence_raw=evidence_raw,
            allow_live=allow_live,
            warnings=warnings,
        )
        self._collect_clinvar(
            collector,
            evidence_map,
            evidence_raw=evidence_raw,
            source_statuses=source_statuses,
            allow_live=allow_live,
            warnings=warnings,
        )
        return collector.summary(warnings)

    def _collect_pubmed_articles(
        self,
        collector: _FunctionalEvidenceCollector,
        evidence_map: dict[str, dict[str, Any]],
        terms: VariantLiteratureTerms,
    ) -> None:
        articles = evidence_map.get("pubmed", {}).get("articles")
        if not isinstance(articles, list):
            return
        searchable_terms = [
            term
            for term in sorted(terms.snippet_terms, key=len, reverse=True)
            if term != terms.gene
        ]
        for item in articles:
            if not isinstance(item, dict):
                continue
            pmid = str(item.get("pmid") or "").strip()
            if not pmid:
                continue
            text = " ".join(
                str(item.get(field) or "") for field in ("title", "abstract") if item.get(field)
            )
            sentence = _functional_sentence_with_variant(text, searchable_terms)
            if sentence is not None:
                collector.add(source="pubmed", pmid=pmid, snippet=sentence)

    def _collect_clingen(
        self,
        collector: _FunctionalEvidenceCollector,
        variant: Any,
        *,
        evidence_raw: dict[str, Any] | None,
        allow_live: bool,
        warnings: list[str],
    ) -> None:
        records = _coerce_clingen_records((evidence_raw or {}).get("clingen"))
        if allow_live and self.clingen_client is not None:
            try:
                records.extend(self._fetch_clingen_records(variant))
            except Exception as exc:
                warnings.append(f"functional_clingen_failed:{type(exc).__name__}")

        seen_records: set[str] = set()
        for record in records:
            record_id = str(record.get("uuid") or record.get("_id") or id(record))
            if record_id in seen_records:
                continue
            seen_records.add(record_id)
            record_codes = _functional_codes_from_values(record.get("metCodes"))
            record_asserted_codes = _asserted_functional_codes_from_values(record.get("metCodes"))
            summary = str(record.get("summaryDesc") or "")
            for sentence in _split_sentences(summary):
                explicit_codes = _functional_codes_from_text(sentence)
                explicit_asserted_codes = _asserted_functional_codes_from_text(sentence)
                has_functional_evidence_sentence = _has_strong_functional_signal(sentence)
                if not explicit_codes and not has_functional_evidence_sentence:
                    continue
                sentence_codes = explicit_codes or record_codes
                sentence_asserted_codes = explicit_asserted_codes or record_asserted_codes
                pmids = _pmids_in_sentence(sentence)
                for pmid in pmids:
                    collector.add(
                        source="clingen",
                        pmid=pmid,
                        evidence_codes=sentence_codes,
                        asserted_codes=sentence_asserted_codes,
                        snippet=sentence,
                    )
                if not pmids and sentence_codes and _has_strong_functional_signal(sentence):
                    collector.add(
                        source="clingen",
                        citation=_citation_from_sentence(sentence),
                        fallback_id=f"{record_id}:{','.join(sentence_codes)}:{sentence[:80]}",
                        evidence_codes=sentence_codes,
                        asserted_codes=sentence_asserted_codes,
                        snippet=sentence,
                    )

    def _fetch_clingen_records(self, variant: Any) -> list[dict[str, Any]]:
        if self.clingen_client is None:
            return []
        gene = str(getattr(variant, "gene", "") or "").strip().upper()
        transcript_hgvs = str(getattr(variant, "transcript_hgvs", "") or "").strip()
        cdna = transcript_hgvs.split(":")[-1].strip() if transcript_hgvs else ""
        terms = [term for term in (transcript_hgvs, cdna) if term]
        records: list[dict[str, Any]] = []
        for term in _unique(terms):
            records.extend(self.clingen_client.search(gene=gene, hgvs=term))
        return records

    def _collect_clinvar(
        self,
        collector: _FunctionalEvidenceCollector,
        evidence_map: dict[str, dict[str, Any]],
        *,
        evidence_raw: dict[str, Any] | None,
        source_statuses: dict[str, str] | None,
        allow_live: bool,
        warnings: list[str],
    ) -> None:
        if _source_failed("clinvar", source_statuses):
            return
        clinvar_raw = (evidence_raw or {}).get("clinvar")
        xml_text = _clinvar_xml_from_raw(clinvar_raw)
        if not xml_text and allow_live and self.clinvar_client is not None:
            variation_id = _clinvar_variation_id(clinvar_raw, evidence_map.get("clinvar", {}))
            if variation_id:
                try:
                    xml_text = self.clinvar_client.fetch_vcv_xml(variation_id)
                except Exception as exc:
                    warnings.append(f"functional_clinvar_vcv_failed:{type(exc).__name__}")
        if not xml_text:
            return
        self._collect_clinvar_xml(collector, xml_text, warnings)

    def _collect_clinvar_xml(
        self,
        collector: _FunctionalEvidenceCollector,
        xml_text: str,
        warnings: list[str],
    ) -> None:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            warnings.append("functional_clinvar_vcv_parse_failed")
            return
        for elem in root.iter():
            tag = _local_name(elem.tag)
            if tag not in {"Comment", "Attribute"}:
                continue
            text = "".join(elem.itertext())
            for sentence in _functional_sentences_with_pmids(text):
                codes = _functional_codes_from_text(sentence)
                asserted_codes = _asserted_functional_codes_from_text(sentence)
                for pmid in _pmids_in_sentence(sentence):
                    collector.add(
                        source="clinvar",
                        pmid=pmid,
                        evidence_codes=codes,
                        asserted_codes=asserted_codes,
                        snippet=sentence,
                    )


def _coerce_clingen_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        records = value.get("data", value.get("records"))
        if isinstance(records, list):
            return [record for record in records if isinstance(record, dict)]
        return [value]
    if isinstance(value, list):
        return [record for record in value if isinstance(record, dict)]
    return []


def _clinvar_xml_from_raw(raw: Any) -> str | None:
    if isinstance(raw, str) and "<ClinVarResult-Set" in raw:
        return raw
    if isinstance(raw, dict):
        xml_text = raw.get("vcv_xml")
        if isinstance(xml_text, str) and xml_text.strip():
            return xml_text
    return None


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


def _functional_codes_from_values(value: Any) -> list[FunctionalEvidenceCode]:
    values = value if isinstance(value, list) else []
    found: list[FunctionalEvidenceCode] = []
    for item in values:
        text = str(item)
        for code in _FUNCTIONAL_CODES:
            if re.match(rf"^{code}(?:\b|_)", text, flags=re.IGNORECASE):
                found.append(cast(FunctionalEvidenceCode, code))
    return _unique(found)


def _asserted_functional_codes_from_values(value: Any) -> list[str]:
    values = value if isinstance(value, list) else []
    found: list[str] = []
    for item in values:
        found.extend(_asserted_functional_codes_from_text(str(item)))
    return _unique(found)


def _functional_codes_from_text(text: str) -> list[FunctionalEvidenceCode]:
    found = [
        cast(FunctionalEvidenceCode, code)
        for code in _FUNCTIONAL_CODES
        if re.search(rf"\b{code}(?:\b|_)", text, flags=re.IGNORECASE)
    ]
    return _unique(found)


def _asserted_functional_codes_from_text(text: str) -> list[str]:
    found: list[str] = []
    pattern = re.compile(r"\b(PS3|BS3)(?:_([A-Za-z][A-Za-z0-9]*))?\b", flags=re.IGNORECASE)
    for match in pattern.finditer(text):
        base = match.group(1).upper()
        suffix = match.group(2)
        found.append(f"{base}_{suffix}" if suffix else base)
    return _unique(found)


def _display_metrics(
    *,
    total_count: int,
    evidence_codes: list[FunctionalEvidenceCode],
    asserted_codes: list[str],
) -> FunctionalEvidenceDisplayMetrics:
    study_count_badge_text = f"{total_count} Unique"
    code_set = set(evidence_codes)
    if total_count == 0:
        return FunctionalEvidenceDisplayMetrics(study_count_badge_text=study_count_badge_text)
    if {"PS3", "BS3"} <= code_set:
        return FunctionalEvidenceDisplayMetrics(
            primary_label="Conflicting Functional Data",
            acmg_badge_text="Review Required",
            study_count_badge_text=study_count_badge_text,
            ui_color_theme="caution_orange_state",
        )
    if "PS3" in code_set:
        return FunctionalEvidenceDisplayMetrics(
            primary_label="Functional Deficit",
            acmg_badge_text=_preferred_asserted_code("PS3", asserted_codes),
            study_count_badge_text=study_count_badge_text,
            ui_color_theme="danger_red_state",
        )
    if "BS3" in code_set:
        return FunctionalEvidenceDisplayMetrics(
            primary_label="Normal Function",
            acmg_badge_text=_preferred_asserted_code("BS3", asserted_codes),
            study_count_badge_text=study_count_badge_text,
            ui_color_theme="safe_green_state",
        )
    return FunctionalEvidenceDisplayMetrics(
        primary_label="Functional Evidence Found",
        acmg_badge_text="Review Required",
        study_count_badge_text=study_count_badge_text,
        ui_color_theme="caution_orange_state",
    )


def _preferred_asserted_code(base_code: FunctionalEvidenceCode, asserted_codes: list[str]) -> str:
    for code in asserted_codes:
        if code.upper().startswith(base_code):
            return code
    return base_code


def _asserted_code_sort_key(code: str) -> tuple[int, str]:
    base = code.split("_", 1)[0].upper()
    return (_FUNCTIONAL_CODE_ORDER.get(base, 99), code)


def _functional_sentences_with_pmids(text: str) -> list[str]:
    return [
        sentence
        for sentence in _split_sentences(text)
        if _has_functional_signal(sentence) and _pmids_in_sentence(sentence)
    ]


def _functional_sentence_with_variant(text: str, terms: list[str]) -> str | None:
    if not terms:
        return None
    for sentence in _split_sentences(text):
        lowered = sentence.lower()
        if _has_functional_signal(sentence) and any(term.lower() in lowered for term in terms):
            return sentence
    return None


def _has_functional_signal(text: str) -> bool:
    return bool(_FUNCTIONAL_SIGNAL_RE.search(text))


def _has_strong_functional_signal(text: str) -> bool:
    return bool(_STRONG_FUNCTIONAL_SIGNAL_RE.search(text))


def _pmids_in_sentence(sentence: str) -> set[str]:
    pmids: set[str] = set()
    pattern = re.compile(
        r"\b(?:PMIDs?|PubMed(?:\s+IDs?)?)\s*:?\s*" r"((?:\d{6,9}\s*(?:,|;|\band\b)?\s*)+)",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(sentence):
        pmids.update(re.findall(r"\b\d{6,9}\b", match.group(1)))
    return pmids


def _citation_from_sentence(sentence: str) -> str | None:
    match = re.search(r"\b([A-Z][A-Za-z'`-]+ et al\.,\s*\d{4})\b", sentence)
    if match:
        return match.group(1)
    return None


def _split_sentences(text: str) -> list[str]:
    normalized = _normalize_space(text)
    if not normalized:
        return []
    return [item.strip() for item in re.split(r"(?<=[.!?;])\s+", normalized) if item.strip()]


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _source_failed(source: str, source_statuses: dict[str, str] | None) -> bool:
    if not source_statuses:
        return False
    return source_statuses.get(source) in _SOURCE_FAILED_STATUSES


def _unique(items: list[Any]) -> list[Any]:
    result: list[Any] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
