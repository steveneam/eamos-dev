from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, cast
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.data_sources import PolicyAction
from app.schemas.run import (
    FunctionalEvidenceCode,
    FunctionalEvidenceCodeRestsOn,
    FunctionalEvidenceDisplayMetrics,
    FunctionalEvidenceSourceBreakdown,
    FunctionalEvidenceSourceTag,
    FunctionalEvidenceSummary,
    FunctionalMeasurementValue,
    FunctionalStudy,
    SourceProvenance,
)
from app.services import clinvar_vcv
from app.services.clinvar_vcv import (
    DEFAULT_CLINVAR_VCV_MAX_XML_BYTES,
    EutilsClinVarVcvClient,
)
from app.services.mavedb_local import (
    MAVEDB_ARCHIVE_DIGEST_ALGORITHM_V4,
    MAVEDB_ARCHIVE_DIGEST_VALUE_V4,
    MAVEDB_ARCHIVE_RELEASE_DOI_V4,
    MAVEDB_CALIBRATION_RESERVED,
    MAVEDB_LOCAL_SOURCE_ID,
    MaveDbLocalInspection,
    MaveDbLocalStore,
    MaveDbMatchRecord,
    MaveDbRecord,
    mavedb_record_to_canonical_dict,
)
from app.services.publication_literature import VariantLiteratureTerms
from app.services.report_source_truth import report_source_allows_payload
from app.services.source_fact_policy import build_source_fact_policy_envelope

_FUNCTIONAL_CODES = ("PS3", "BS3")
_FUNCTIONAL_CODE_ORDER = {"PS3": 0, "BS3": 1}
_SOURCE_ORDER = {"clingen": 0, "clinvar": 1, "pubmed": 2, "mavedb": 3}
_MAVEDB_PUBLIC_FIELDS = (
    "archive_provenance",
    "score_set_metadata",
    "score_set_metadata.experiment",
    "score_set_metadata.methods",
    "score_set_metadata.linked_identifiers",
    "target_metadata",
    "target_metadata.assembly",
    "variant_scores.raw_score",
    "variant_scores.score_column",
    "variant_scores.score_unit",
    "variant_scores.identifiers",
    "variant_scores.uncertainty",
    "deprecation_state",
)
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


class MaveDbFunctionalClient(Protocol):
    def search_records(
        self,
        variant: Any,
        *,
        limit: int,
        verify_checksum: bool = True,
    ) -> tuple[list[MaveDbRecord], MaveDbLocalInspection]:
        """Return local CC0 MaveDB records for a normalized variant."""


@dataclass
class _FunctionalHit:
    id: str
    pmid: str | None = None
    url: str | None = None
    citation: str | None = None
    source_accession: str | None = None
    source_tags: set[FunctionalEvidenceSourceTag] = field(default_factory=set)
    evidence_codes: set[FunctionalEvidenceCode] = field(default_factory=set)
    asserted_codes: set[str] = field(default_factory=set)
    asserted_codes_by_source: dict[FunctionalEvidenceSourceTag, set[str]] = field(
        default_factory=dict
    )
    functional_score: Decimal | float | None = None
    functional_score_label: str | None = None
    mavedb_match: MaveDbMatchRecord | None = None
    snippets: list[str] = field(default_factory=list)


class _FunctionalEvidenceCollector:
    def __init__(self) -> None:
        self.by_pmid: dict[str, _FunctionalHit] = {}
        self.per_source: dict[FunctionalEvidenceSourceTag, set[str]] = {
            "clingen": set(),
            "clinvar": set(),
            "pubmed": set(),
            "mavedb": set(),
        }

    def add(
        self,
        *,
        source: FunctionalEvidenceSourceTag,
        pmid: str | None = None,
        url: str | None = None,
        citation: str | None = None,
        source_accession: str | None = None,
        fallback_id: str | None = None,
        evidence_codes: list[FunctionalEvidenceCode] | None = None,
        asserted_codes: list[str] | None = None,
        functional_score: Decimal | float | None = None,
        functional_score_label: str | None = None,
        mavedb_match: MaveDbMatchRecord | None = None,
        snippet: str | None = None,
    ) -> None:
        pmid = pmid.strip() if pmid else None
        url = _normalize_space(url) if url else None
        citation = _normalize_space(citation) if citation else None
        source_accession = _normalize_space(source_accession) if source_accession else None
        hit_id = pmid or citation or fallback_id
        if not hit_id:
            return
        hit = self.by_pmid.setdefault(hit_id, _FunctionalHit(id=hit_id))
        if pmid and hit.pmid is None:
            hit.pmid = pmid
        if url and hit.url is None:
            hit.url = url
        if citation and hit.citation is None:
            hit.citation = citation
        if source_accession and hit.source_accession is None:
            hit.source_accession = source_accession
        if functional_score is not None and hit.functional_score is None:
            hit.functional_score = functional_score
        if functional_score_label and hit.functional_score_label is None:
            hit.functional_score_label = _normalize_space(functional_score_label)
        if mavedb_match is not None and hit.mavedb_match is None:
            hit.mavedb_match = mavedb_match
        hit.source_tags.add(source)
        self.per_source[source].add(hit_id)
        for code in evidence_codes or []:
            hit.evidence_codes.add(code)
        for code in asserted_codes or []:
            hit.asserted_codes.add(code)
            hit.asserted_codes_by_source.setdefault(source, set()).add(code)
        if snippet:
            normalized = _normalize_space(snippet)
            if normalized and normalized not in hit.snippets:
                hit.snippets.append(normalized[:420])

    def summary(self, warnings: list[str]) -> FunctionalEvidenceSummary:
        studies = [_functional_study(hit) for hit in self.by_pmid.values()]
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
        source_asserted_codes_by_source = {
            source: sorted(
                {
                    code
                    for hit in self.by_pmid.values()
                    for code in hit.asserted_codes_by_source.get(source, set())
                },
                key=_asserted_code_sort_key,
            )
            for source in ("clingen", "clinvar")
        }
        curator_cited_count = len(
            {
                hit.id
                for hit in self.by_pmid.values()
                if hit.asserted_codes_by_source.get("clingen")
                or hit.asserted_codes_by_source.get("clinvar")
            }
        )
        non_mavedb_count = len(
            {
                hit.id
                for hit in self.by_pmid.values()
                if any(source != "mavedb" for source in hit.source_tags)
            }
        )
        summary_warnings = list(warnings)
        if source_asserted_codes:
            summary_warnings.append(
                "functional_source_assertions_context_only:assay_validation_missing"
            )
        return FunctionalEvidenceSummary(
            total_count=len(studies),
            source_breakdown=FunctionalEvidenceSourceBreakdown(
                clingen=len(self.per_source["clingen"]),
                clinvar=len(self.per_source["clinvar"]),
                pubmed=len(self.per_source["pubmed"]),
                mavedb=len(self.per_source["mavedb"]),
            ),
            evidence_codes=evidence_codes,
            source_asserted_codes=source_asserted_codes,
            display_metrics=_display_metrics(
                total_count=len(studies),
                source_asserted_codes_by_source=source_asserted_codes_by_source,
                curator_cited_count=curator_cited_count,
                mavedb_only_uncurated=bool(studies) and non_mavedb_count == 0,
            ),
            studies=studies,
            warnings=summary_warnings,
        )


def _functional_study(hit: _FunctionalHit) -> FunctionalStudy:
    common: dict[str, Any] = {
        "id": hit.id,
        "pmid": hit.pmid,
        "url": hit.url or (f"https://pubmed.ncbi.nlm.nih.gov/{hit.pmid}/" if hit.pmid else None),
        "citation": hit.citation,
        "source_accession": hit.source_accession,
        "source_tags": sorted(hit.source_tags, key=lambda source: _SOURCE_ORDER[source]),
        "evidence_codes": sorted(hit.evidence_codes),
        "asserted_codes": sorted(hit.asserted_codes, key=_asserted_code_sort_key),
        "functional_score": hit.functional_score,
        "functional_score_label": hit.functional_score_label,
        "snippet": hit.snippets[0] if hit.snippets else None,
    }
    match = hit.mavedb_match
    if match is None:
        return FunctionalStudy(**common)

    policy_envelope = build_source_fact_policy_envelope(
        source_id=MAVEDB_LOCAL_SOURCE_ID,
        field_paths=_MAVEDB_PUBLIC_FIELDS,
        source_record_id=match.variant_score.variant_urn,
        source_version=match.archive_release_doi,
        source_url=match.source_url,
        origin_kind="direct",
        match_level=match.match_level,
        action_field_allowlists={
            MAVEDB_LOCAL_SOURCE_ID: {
                PolicyAction.PRODUCT_EXPORT: _MAVEDB_PUBLIC_FIELDS,
            }
        },
    )
    if not _mavedb_public_archive_verified(match):
        _mark_mavedb_fixture_policy_denied(policy_envelope)
    policy_envelope["record_license"] = match.score_set.license_snapshot
    policy_envelope["attribution"] = "MaveDB / Variant Effect"
    canonical = mavedb_record_to_canonical_dict(match)
    provenance = SourceProvenance(
        source="MaveDB",
        status="local",
        query={
            "match_level": match.match_level,
            "requested_identity": match.requested_identity,
            "matched_identity": match.matched_identity,
        },
        version=match.archive_release_doi,
        storage_kind="verified_local_sqlite",
        warnings=[],
        **policy_envelope,
    )
    return FunctionalStudy(
        **common,
        **policy_envelope,
        raw_score=canonical["variant_score"]["raw_score"],
        score_unit=match.variant_score.score_unit,
        score_column=match.variant_score.score_column,
        score_direction="source_defined_neutral",
        score_set_urn=match.score_set.score_set_urn,
        variant_urn=match.variant_score.variant_urn,
        experiment_urn=match.score_set.experiment_urn,
        experiment_set_urn=match.score_set.experiment_set_urn,
        target_accession=match.target.target_accession,
        target_kind=match.target.target_kind,
        target_assembly=match.target.target_assembly,
        target_sequence_checksum=match.target.target_sequence_checksum,
        target_identity=match.target.exact_identity,
        mave_hgvs_nt=match.variant_score.mave_hgvs_nt,
        mave_hgvs_splice=match.variant_score.mave_hgvs_splice,
        mave_hgvs_pro=match.variant_score.mave_hgvs_pro,
        score_column_description=match.variant_score.score_column_description,
        score_column_details=match.variant_score.score_column_details,
        uncertainty_values=[
            FunctionalMeasurementValue(
                column=value.column,
                source_value=value.source_value,
                parsed_value=value.parsed_value,
                description=value.description,
                details=value.details,
            )
            for value in match.variant_score.uncertainty_values
        ],
        assay_context=(
            match.score_set.short_description
            or match.score_set.experiment_short_description
            or match.score_set.title
        ),
        method_text=_mavedb_method_text(match),
        linked_doi_identifiers=list(match.score_set.doi_identifiers),
        linked_publication_identifiers=list(match.score_set.publication_identifiers),
        archive_release_doi=match.archive_release_doi,
        archive_sha256=match.archive_sha256,
        archive_checksum_algorithm=match.archive_digest_algorithm,
        archive_checksum_value=match.archive_digest_value,
        archive_checksum_verified=match.archive_digest_verified,
        local_logical_checksum_verified=match.local_logical_checksum_verified,
        data_usage_policy_decision=match.score_set.data_usage_policy_decision,
        match_requested_identity=match.requested_identity,
        match_matched_identity=match.matched_identity,
        calibration_status=MAVEDB_CALIBRATION_RESERVED.status,
        deprecated=match.score_set.deprecated or match.variant_score.deprecated,
        superseded_by=(match.variant_score.superseded_by or match.score_set.superseded_by),
        provenance=[provenance],
    )


def _mavedb_public_archive_verified(match: MaveDbMatchRecord) -> bool:
    return bool(
        match.archive_release_doi == MAVEDB_ARCHIVE_RELEASE_DOI_V4
        and match.archive_digest_algorithm == MAVEDB_ARCHIVE_DIGEST_ALGORITHM_V4
        and match.archive_digest_value == MAVEDB_ARCHIVE_DIGEST_VALUE_V4
        and match.archive_digest_verified
        and bool(re.fullmatch(r"[0-9a-f]{64}", match.archive_sha256))
        and match.archive_member_digests_verified
        and bool(match.metadata_schema_version)
        and match.local_logical_checksum_verified
    )


def _mark_mavedb_fixture_policy_denied(envelope: dict[str, object]) -> None:
    decisions = envelope.get("policy_decisions")
    if isinstance(decisions, list):
        for decision in decisions:
            if not isinstance(decision, dict):
                continue
            if decision.get("action") not in {
                "cache",
                "public_serialize",
                "product_export",
            }:
                continue
            decision["outcome"] = "denied"
            decision["reason"] = "synthetic_fixture_not_public"
    envelope["public_serialization_allowed"] = False
    envelope["export_allowed"] = False
    envelope["cache_allowed"] = False
    envelope["decision_reason"] = "synthetic_fixture_not_public"


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


class FunctionalEvidenceExtractor:
    """Count functional-study PMIDs without assigning ACMG PS3/BS3 strength."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        clingen_client: ClinGenFunctionalClient | None = None,
        clinvar_client: ClinVarFunctionalClient | None = None,
        mavedb_store: MaveDbFunctionalClient | None = None,
        include_nonpublic_mavedb_fixtures: bool = False,
        clinvar_vcv_max_xml_bytes: int = DEFAULT_CLINVAR_VCV_MAX_XML_BYTES,
    ) -> None:
        self.settings = settings
        self.clinvar_vcv_max_xml_bytes = clinvar_vcv_max_xml_bytes
        self.include_nonpublic_mavedb_fixtures = include_nonpublic_mavedb_fixtures
        self.clingen_client = clingen_client or (
            ClinGenERepoFunctionalClient(settings) if settings is not None else None
        )
        self.clinvar_client = clinvar_client or (
            EutilsClinVarVcvClient(
                base_url=settings.clinvar_base_url,
                max_xml_bytes=clinvar_vcv_max_xml_bytes,
            )
            if settings is not None
            else None
        )
        self.mavedb_store = mavedb_store or (
            MaveDbLocalStore(
                _settings_path(settings, settings.mavedb_local_sqlite_path),
                manifest_path=_settings_path(settings, settings.mavedb_local_manifest_path),
                enabled=settings.mavedb_local_enabled,
            )
            if settings is not None and settings.mavedb_local_enabled
            else None
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

        self._collect_pubmed_articles(
            collector,
            evidence_map,
            terms,
            source_statuses=source_statuses,
        )
        self._collect_clingen(
            collector,
            variant,
            evidence_raw=evidence_raw,
            source_statuses=source_statuses,
            allow_live=allow_live,
            warnings=warnings,
        )
        self._collect_mavedb(
            collector,
            variant,
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
        *,
        source_statuses: dict[str, str] | None,
    ) -> None:
        if _source_failed("pubmed", source_statuses):
            return
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
        source_statuses: dict[str, str] | None,
        allow_live: bool,
        warnings: list[str],
    ) -> None:
        records = (
            []
            if _source_failed("clingen", source_statuses)
            else _coerce_clingen_records((evidence_raw or {}).get("clingen"))
        )
        if (
            allow_live
            and self.clingen_client is not None
            and not _source_failed("clingen", source_statuses)
        ):
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

    def _collect_mavedb(
        self,
        collector: _FunctionalEvidenceCollector,
        variant: Any,
        *,
        warnings: list[str],
    ) -> None:
        if self.mavedb_store is None:
            return
        limit = int(getattr(self.settings, "mavedb_local_max_results", 25) or 25)
        try:
            records, inspection = self.mavedb_store.search_records(
                variant,
                limit=limit,
                verify_checksum=True,
            )
        except Exception as exc:
            warnings.append(f"functional_mavedb_failed:{type(exc).__name__}")
            return
        if not inspection.ready:
            warnings.append(f"functional_mavedb_unavailable:{inspection.status}")
            return
        if inspection.status != "ready" and not self.include_nonpublic_mavedb_fixtures:
            warnings.append(f"functional_mavedb_nonpublic:{inspection.status}")
            return
        warnings.extend(f"functional_mavedb_notice:{notice}" for notice in inspection.warnings)
        for record in records:
            collector.add(
                source="mavedb",
                url=record.source_url,
                citation=f"MaveDB {record.score_set_id}",
                source_accession=record.score_set_id,
                fallback_id=f"mavedb:{record.score_set_id}:{record.variant}",
                functional_score=record.score,
                functional_score_label=f"Raw {record.variant_score.score_column}",
                mavedb_match=record,
                snippet=_mavedb_public_snippet(record),
            )

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
        xml_text = clinvar_vcv.clinvar_vcv_xml_from_raw(clinvar_raw)
        if not xml_text and allow_live and self.clinvar_client is not None:
            variation_id = _clinvar_variation_id(clinvar_raw, evidence_map.get("clinvar", {}))
            if variation_id:
                try:
                    xml_text = self.clinvar_client.fetch_vcv_xml(variation_id)
                    clinvar_vcv.store_clinvar_vcv_xml(clinvar_raw, xml_text)
                except Exception as exc:
                    warnings.append(f"functional_clinvar_vcv_failed:{type(exc).__name__}")
        parse_result = clinvar_vcv.clinvar_vcv_parse_result(
            clinvar_raw,
            xml_text=xml_text,
            max_xml_bytes=self.clinvar_vcv_max_xml_bytes,
        )
        if parse_result.extraction is None and parse_result.error_code is None:
            return
        self._collect_clinvar_extraction(collector, parse_result, warnings)

    def _collect_clinvar_extraction(
        self,
        collector: _FunctionalEvidenceCollector,
        parse_result: clinvar_vcv.ClinVarVcvParseResult,
        warnings: list[str],
    ) -> None:
        if parse_result.error_code == "xml_too_large":
            warnings.append("functional_clinvar_vcv_too_large")
            return
        if parse_result.error_code == "parse_failed":
            warnings.append("functional_clinvar_vcv_parse_failed")
            return
        if parse_result.extraction is None:
            return
        for text in parse_result.extraction.texts_for(("Comment", "Attribute")):
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
    source_asserted_codes_by_source: dict[FunctionalEvidenceSourceTag, list[str]],
    curator_cited_count: int,
    mavedb_only_uncurated: bool = False,
) -> FunctionalEvidenceDisplayMetrics:
    study_count_badge_text = f"{total_count} Unique"
    clingen_codes = source_asserted_codes_by_source.get("clingen", [])
    clinvar_codes = source_asserted_codes_by_source.get("clinvar", [])

    if _has_functional_direction_conflict(clingen_codes, clinvar_codes):
        return FunctionalEvidenceDisplayMetrics(
            state="conflict",
            primary_label="Conflicting Functional Data",
            acmg_badge_text="Review Required",
            verdict_source="conflict",
            study_count_badge_text=study_count_badge_text,
            conflict_split=None,
            ui_color_theme="caution_yellow_state",
        )

    clingen_direction = _single_functional_direction(clingen_codes)
    clinvar_direction = _single_functional_direction(clinvar_codes)

    if clingen_direction is not None:
        code = _preferred_asserted_code(clingen_direction, clingen_codes)
        source = "clingen+clinvar" if clinvar_direction == clingen_direction else "clingen"
        return _curator_backed_display_metrics(
            total_count=total_count,
            study_count_badge_text=study_count_badge_text,
            code=code,
            direction=clingen_direction,
            verdict_source=source,
            curator_cited_count=curator_cited_count,
        )

    if clinvar_direction is not None:
        code = _preferred_asserted_code(clinvar_direction, clinvar_codes)
        return _curator_backed_display_metrics(
            total_count=total_count,
            study_count_badge_text=study_count_badge_text,
            code=code,
            direction=clinvar_direction,
            verdict_source="clinvar",
            curator_cited_count=curator_cited_count,
        )

    if total_count == 0:
        return FunctionalEvidenceDisplayMetrics(
            state="none",
            study_count_badge_text=study_count_badge_text,
            verdict_source="none",
        )

    return FunctionalEvidenceDisplayMetrics(
        state="uncurated",
        primary_label="Functional Work Found - Not ACMG-graded",
        acmg_badge_text="No code asserted",
        verdict_source="uncurated",
        study_count_badge_text=study_count_badge_text,
        ui_color_theme=("neutral_slate_state" if mavedb_only_uncurated else "info_blue_state"),
    )


def _curator_backed_display_metrics(
    *,
    total_count: int,
    study_count_badge_text: str,
    code: str,
    direction: FunctionalEvidenceCode,
    verdict_source: str,
    curator_cited_count: int,
) -> FunctionalEvidenceDisplayMetrics:
    if direction == "PS3":
        state = "strong_deficit" if code.upper().endswith("_STRONG") else "emerging_deficit"
        return FunctionalEvidenceDisplayMetrics(
            state=state,
            primary_label="Functional Deficit",
            acmg_badge_text=code,
            verdict_source=verdict_source,  # type: ignore[arg-type]
            study_count_badge_text=study_count_badge_text,
            code_rests_on=_code_rests_on(curator_cited_count, total_count),
            ui_color_theme="danger_red_state" if state == "strong_deficit" else "risk_red_state",
        )
    return FunctionalEvidenceDisplayMetrics(
        state="normal",
        primary_label="Normal Function",
        acmg_badge_text=code,
        verdict_source=verdict_source,  # type: ignore[arg-type]
        study_count_badge_text=study_count_badge_text,
        code_rests_on=_code_rests_on(curator_cited_count, total_count),
        ui_color_theme="safe_green_state",
    )


def _preferred_asserted_code(base_code: FunctionalEvidenceCode, asserted_codes: list[str]) -> str:
    for code in asserted_codes:
        if code.upper().startswith(base_code):
            return code
    return base_code


def _has_functional_direction_conflict(
    clingen_codes: list[str],
    clinvar_codes: list[str],
) -> bool:
    clingen_directions = _functional_directions(clingen_codes)
    clinvar_directions = _functional_directions(clinvar_codes)
    if len(clingen_directions) > 1 or len(clinvar_directions) > 1:
        return True
    return bool(
        clingen_directions and clinvar_directions and clingen_directions != clinvar_directions
    )


def _functional_directions(codes: list[str]) -> set[FunctionalEvidenceCode]:
    return {direction for direction in (_functional_direction(code) for code in codes) if direction}


def _single_functional_direction(codes: list[str]) -> FunctionalEvidenceCode | None:
    directions = _functional_directions(codes)
    if len(directions) == 1:
        return next(iter(directions))
    return None


def _functional_direction(code: str) -> FunctionalEvidenceCode | None:
    upper = code.upper()
    if upper.startswith("PS3"):
        return "PS3"
    if upper.startswith("BS3"):
        return "BS3"
    return None


def _code_rests_on(
    curator_cited_count: int,
    total_count: int,
) -> FunctionalEvidenceCodeRestsOn | None:
    if curator_cited_count <= 0 or total_count <= curator_cited_count:
        return None
    return FunctionalEvidenceCodeRestsOn(cited=curator_cited_count, total=total_count)


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


def _mavedb_public_snippet(record: MaveDbRecord) -> str:
    score = record.variant_score.raw_score_source or f"{record.score:g}"
    gene = f"{record.gene} " if record.gene else ""
    return f"MaveDB CC0 score {score} for {gene}{record.variant}; score set {record.score_set_id}."


def _mavedb_method_text(record: MaveDbRecord) -> str | None:
    parts = [
        text.strip()
        for text in (
            record.score_set.score_set_method_text,
            record.score_set.experiment_method_text,
        )
        if text and text.strip()
    ]
    return "\n\n".join(parts) or None


def _split_sentences(text: str) -> list[str]:
    normalized = _normalize_space(text)
    if not normalized:
        return []
    return [item.strip() for item in re.split(r"(?<=[.!?;])\s+", normalized) if item.strip()]


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _settings_path(settings: Settings, path):
    return path if path.is_absolute() else settings.backend_root / path


def _source_failed(source: str, source_statuses: dict[str, str] | None) -> bool:
    if source_statuses is None:
        return False
    return not report_source_allows_payload(source_statuses.get(source, "missing"))


def _unique(items: list[Any]) -> list[Any]:
    result: list[Any] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
