from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.schemas.run import (
    PublicationLiterature,
    PublicationSnippet,
    PublicationScope,
    PublicationScopeCount,
    PublicationScopeCounts,
    PublicationSourceBreakdown,
    PublicationSourceTag,
    PublicationTimeline,
    PublicationYearCount,
    PubMedArticle,
)
from app.services.report_source_truth import (
    combined_report_source_status,
    report_source_allows_payload,
)

_AA3_TO_1 = {
    "Ala": "A",
    "Arg": "R",
    "Asn": "N",
    "Asp": "D",
    "Cys": "C",
    "Gln": "Q",
    "Glu": "E",
    "Gly": "G",
    "His": "H",
    "Ile": "I",
    "Leu": "L",
    "Lys": "K",
    "Met": "M",
    "Phe": "F",
    "Pro": "P",
    "Ser": "S",
    "Thr": "T",
    "Trp": "W",
    "Tyr": "Y",
    "Val": "V",
    "Ter": "*",
    "Stop": "*",
}
_AA1_TO_3 = {value: key for key, value in _AA3_TO_1.items() if value != "*"}
_AA1_TO_3["*"] = "Ter"


def _append_unique(items: list[str], value: str | None) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text and text not in items:
        items.append(text)


def _cdna_from_transcript_hgvs(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    return transcript_hgvs.split(":")[-1].strip()


def _protein_aliases(protein_change: str | None) -> list[str]:
    if not protein_change:
        return []
    aliases: list[str] = []
    raw = protein_change.strip()
    if raw.startswith("p."):
        raw = raw[2:]
    if raw.startswith("(") and raw.endswith(")") and len(raw) > 2:
        raw = raw[1:-1]
    _append_unique(aliases, raw)
    _append_unique(aliases, f"p.{raw}" if raw else None)

    three_letter = re.fullmatch(
        r"([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2}|Ter|Stop|\*)",
        raw,
    )
    if three_letter:
        ref, pos, alt = three_letter.groups()
        ref_one = _AA3_TO_1.get(ref)
        alt_one = _AA3_TO_1.get(alt, alt if alt == "*" else None)
        if ref_one and alt_one:
            one_letter = f"{ref_one}{pos}{alt_one}"
            _append_unique(aliases, one_letter)
            _append_unique(aliases, f"p.{one_letter}")

    one_letter = re.fullmatch(r"([A-Z*])(\d+)([A-Z*])", raw)
    if one_letter:
        ref, pos, alt = one_letter.groups()
        ref_three = _AA1_TO_3.get(ref)
        alt_three = _AA1_TO_3.get(alt)
        if ref_three and alt_three:
            three = f"{ref_three}{pos}{alt_three}"
            _append_unique(aliases, three)
            _append_unique(aliases, f"p.{three}")

    return aliases


@dataclass(frozen=True)
class VariantLiteratureTerms:
    gene: str
    terms: tuple[str, ...]
    snippet_terms: tuple[str, ...]

    @classmethod
    def build(cls, variant: Any) -> VariantLiteratureTerms:
        gene = str(getattr(variant, "gene", "") or "").strip().upper()
        transcript_hgvs = str(getattr(variant, "transcript_hgvs", "") or "").strip()
        cdna = _cdna_from_transcript_hgvs(transcript_hgvs)
        protein_change = str(getattr(variant, "protein_change", "") or "").strip()
        rsid = str(getattr(variant, "dbsnp_rsid", "") or "").strip()
        genomic_hg38 = str(getattr(variant, "genomic_hg38", "") or "").strip()

        terms: list[str] = []
        _append_unique(terms, gene)
        _append_unique(terms, transcript_hgvs)
        _append_unique(terms, cdna)
        for alias in _protein_aliases(protein_change):
            _append_unique(terms, alias)
        _append_unique(terms, rsid)
        _append_unique(terms, genomic_hg38)

        snippet_terms = [term for term in terms if term and term != gene]
        if not snippet_terms and gene:
            snippet_terms = [gene]
        return cls(gene=gene, terms=tuple(terms), snippet_terms=tuple(snippet_terms))


@dataclass(frozen=True)
class _SnippetTextCandidate:
    section: str
    text: str
    source: str


@dataclass
class _AggregatedArticle:
    pmid: str
    data: dict[str, Any] = field(default_factory=dict)
    source_tags: set[PublicationSourceTag] = field(default_factory=set)


def _article_items(summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(summary, dict):
        return []
    articles = summary.get("articles")
    return (
        [item for item in articles if isinstance(item, dict)] if isinstance(articles, list) else []
    )


def _merge_article_data(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if value not in (None, "", []):
            merged[key] = value
    return merged


def _is_pmid_context_key(key: str) -> bool:
    key_lower = key.lower()
    tokens = {token for token in re.split(r"[^a-z0-9]+", key_lower) if token}
    return any(
        token.startswith(("pmid", "pubmed", "citation")) for token in tokens
    ) or key_lower in {"reference", "references"}


def _extract_pmids(value: Any, *, pmid_context: bool = False) -> set[str]:
    pmids: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            is_pmid_key = _is_pmid_context_key(str(key))
            pmids.update(_extract_pmids(item, pmid_context=pmid_context or is_pmid_key))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            pmids.update(_extract_pmids(item, pmid_context=pmid_context))
    elif pmid_context and isinstance(value, int):
        if value > 0:
            pmids.add(str(value))
    elif pmid_context and isinstance(value, str):
        stripped = value.strip()
        if re.fullmatch(r"\d{6,9}", stripped):
            pmids.add(stripped)
        else:
            pmids.update(re.findall(r"(?:PMID[:\s]*)?(\d{6,9})", stripped, flags=re.IGNORECASE))
    return pmids


class PublicationPmidAggregator:
    def collect(
        self,
        evidence_map: dict[str, dict[str, Any]],
        evidence_raw: dict[str, Any] | None = None,
        source_statuses: dict[str, str] | None = None,
    ) -> tuple[list[_AggregatedArticle], PublicationSourceBreakdown]:
        by_pmid: dict[str, _AggregatedArticle] = {}
        per_source: dict[PublicationSourceTag, set[str]] = {
            "litvar2": set(),
            "pubmed": set(),
            "clinvar": set(),
            "clingen": set(),
        }

        for source in ("pubmed", "litvar2"):
            if _source_failed(source, source_statuses):
                continue
            for item in _article_items(evidence_map.get(source)):
                pmid = str(item.get("pmid") or "").strip()
                if not pmid:
                    continue
                tag = source  # type: ignore[assignment]
                article = by_pmid.setdefault(pmid, _AggregatedArticle(pmid=pmid))
                article.data = _merge_article_data(article.data, item)
                article.source_tags.add(tag)
                per_source[tag].add(pmid)

        clinvar_pmids: set[str] = set()
        if not _source_failed("clinvar", source_statuses):
            clinvar_pmids = _extract_pmids(evidence_map.get("clinvar"))
            if evidence_raw is not None:
                clinvar_pmids.update(_extract_pmids(evidence_raw.get("clinvar")))
        for pmid in clinvar_pmids:
            article = by_pmid.setdefault(pmid, _AggregatedArticle(pmid=pmid))
            article.source_tags.add("clinvar")
            per_source["clinvar"].add(pmid)

        breakdown = PublicationSourceBreakdown(
            litvar2=len(per_source["litvar2"]),
            pubmed=len(per_source["pubmed"]),
            clinvar=len(per_source["clinvar"]),
            clingen=0,
        )
        return list(by_pmid.values()), breakdown


def _source_failed(source: str, source_statuses: dict[str, str] | None) -> bool:
    if source_statuses is None:
        return False
    return not report_source_allows_payload(source_statuses.get(source, "missing"))


def _source_status(source: str, source_statuses: dict[str, str] | None) -> str | None:
    return source_statuses.get(source) if source_statuses else None


def _aggregate_source_status(
    breakdown: PublicationSourceBreakdown,
    source_statuses: dict[str, str] | None,
) -> str | None:
    if not source_statuses:
        return None
    statuses = [
        source_statuses[source]
        for source in ("pubmed", "litvar2", "clinvar", "clingen")
        if source in source_statuses and source_statuses[source]
    ]
    if not statuses:
        return None
    return combined_report_source_status(statuses)


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _gene_scope_count(
    evidence_map: dict[str, dict[str, Any]],
    source_statuses: dict[str, str] | None,
    gene: str,
) -> PublicationScopeCount:
    pubmed_status = _source_status("pubmed", source_statuses)
    default_query = f"{gene}[Gene Name]" if gene else None
    if _source_failed("pubmed", source_statuses):
        return PublicationScopeCount(
            scope="gene",
            total_count=None,
            count_kind="unavailable",
            query=default_query,
            source_status=pubmed_status,
            warnings=["gene_scope_count_unavailable:pubmed_failed"],
        )

    gene_scope = evidence_map.get("pubmed", {}).get("gene_scope")
    if isinstance(gene_scope, dict):
        total_count = _optional_int(gene_scope.get("total_count"))
        if total_count is not None:
            return PublicationScopeCount(
                scope="gene",
                total_count=total_count,
                count_kind="gene_wide_source_count",
                query=str(gene_scope.get("query") or default_query or ""),
                source_status=str(gene_scope.get("source_status") or pubmed_status or ""),
                source_breakdown=PublicationSourceBreakdown(pubmed=total_count),
            )

    return PublicationScopeCount(
        scope="gene",
        total_count=None,
        count_kind="unavailable",
        query=default_query,
        source_status=pubmed_status,
        warnings=["gene_scope_count_unavailable:source_count_missing"],
    )


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _term_pattern(term: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if _term_pattern(term).search(text)]


def _sentence_with_term(text: str, terms: list[str]) -> tuple[str, list[str]] | None:
    normalized = _normalize_space(text)
    if not normalized:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    for sentence in sentences:
        found = _matched_terms(sentence, terms)
        if found:
            return sentence[:320], found
    found = _matched_terms(normalized, terms)
    if found:
        return normalized[:320], found
    return None


def _snippet_confidence(term: str) -> str:
    lowered = term.lower()
    if lowered.startswith("rs"):
        return "rsid"
    if lowered.startswith(("c.", "p.")) or ":" in term:
        return "exact_variant"
    return "variant_alias"


def _text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, dict):
        values: list[str] = []
        for item in value.values():
            values.extend(_text_values(item))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_text_values(item))
        return values
    return []


def _snippet_text_candidates(article: dict[str, Any]) -> list[_SnippetTextCandidate]:
    candidates: list[_SnippetTextCandidate] = []
    candidate_fields = (
        ("title", "title", "pubmed_efetch"),
        ("abstract", "abstract", "pubmed_efetch"),
        ("pubtator", "abstract", "pubtator"),
        ("pubtator_text", "abstract", "pubtator"),
        ("pubtator_abstract", "abstract", "pubtator"),
        ("body", "body", "pmc_bioc"),
        ("full_text", "body", "pmc_bioc"),
        ("pmc_text", "body", "pmc_bioc"),
        ("table", "table", "pmc_bioc"),
        ("tables", "table", "pmc_bioc"),
        ("table_text", "table", "pmc_bioc"),
        ("supplement", "supplement", "pmc_bioc"),
        ("supplementary", "supplement", "pmc_bioc"),
        ("supplementary_text", "supplement", "pmc_bioc"),
        ("litvar2_snippet", "unknown", "litvar2"),
        ("litvar_snippet", "unknown", "litvar2"),
    )
    seen: set[tuple[str, str, str]] = set()
    for key, section, source in candidate_fields:
        for text in _text_values(article.get(key)):
            normalized = _normalize_space(text)
            if not normalized:
                continue
            candidate_key = (section, source, normalized)
            if candidate_key in seen:
                continue
            seen.add(candidate_key)
            candidates.append(
                _SnippetTextCandidate(section=section, source=source, text=normalized)
            )
    return candidates


def _has_gene_context(candidates: list[_SnippetTextCandidate], gene: str) -> bool:
    if not gene:
        return False
    return any(_term_pattern(gene).search(candidate.text) for candidate in candidates)


class VariantMentionSnippetter:
    def extract(
        self,
        article: dict[str, Any],
        terms: VariantLiteratureTerms,
    ) -> tuple[list[PublicationSnippet], str | None]:
        searchable_terms = sorted(terms.snippet_terms, key=len, reverse=True)
        candidates = _snippet_text_candidates(article)
        for candidate in candidates:
            match = _sentence_with_term(candidate.text, searchable_terms)
            if match is None:
                continue
            snippet, matched_terms = match
            confidence = _snippet_confidence(matched_terms[0])
            return [
                PublicationSnippet(
                    section=candidate.section,  # type: ignore[arg-type]
                    text=snippet,
                    matched_terms=matched_terms,
                    source=candidate.source,  # type: ignore[arg-type]
                    confidence=confidence,  # type: ignore[arg-type]
                )
            ], "exact_variant_snippet"

        if _has_gene_context(candidates, terms.gene):
            return [], "gene_only_no_variant"
        if any(candidate.section == "abstract" for candidate in candidates):
            return [], "abstract_only_no_variant"
        if "litvar2" in set(article.get("source_tags") or []):
            return [], "reported_in_litvar2_no_text"
        if "clinvar" in set(article.get("source_tags") or []):
            return [], "reported_in_clinvar_no_text"
        if "pubmed" in set(article.get("source_tags") or []):
            return [], "pubmed_no_text"
        return [], "no_text_available"


def _date_sort_key(article: PubMedArticle) -> tuple[int, int, int, str]:
    date_text = article.publication_date or article.year or ""
    match = re.search(r"(\d{4})(?:[-\s/]?(\d{1,2}))?(?:[-\s/]?(\d{1,2}))?", date_text)
    if not match:
        return (0, 0, 0, article.pmid)
    year = int(match.group(1))
    month = int(match.group(2) or 1)
    day = int(match.group(3) or 1)
    return (year, month, day, article.pmid)


def _publication_year(article: PubMedArticle) -> int | None:
    date_text = article.publication_date or article.year or ""
    match = re.search(r"(\d{4})", date_text)
    return int(match.group(1)) if match else None


def _build_publication_timeline(articles: list[PubMedArticle]) -> PublicationTimeline:
    counts_by_year: dict[int, int] = {}
    total_without_year = 0
    for article in articles:
        year = _publication_year(article)
        if year is None:
            total_without_year += 1
            continue
        counts_by_year[year] = counts_by_year.get(year, 0) + 1

    publications_by_year = [
        PublicationYearCount(year=year, count=counts_by_year[year])
        for year in sorted(counts_by_year)
    ]
    return PublicationTimeline(
        publications_by_year=publications_by_year,
        total_with_year=sum(counts_by_year.values()),
        total_without_year=total_without_year,
    )


class EamosProprietaryVariantLiteratureExtractor:
    def __init__(
        self,
        aggregator: PublicationPmidAggregator | None = None,
        snippetter: VariantMentionSnippetter | None = None,
    ) -> None:
        self.aggregator = aggregator or PublicationPmidAggregator()
        self.snippetter = snippetter or VariantMentionSnippetter()

    def build_for_lookup(
        self,
        variant: Any,
        evidence_map: dict[str, dict[str, Any]],
        *,
        evidence_raw: dict[str, Any] | None = None,
        source_statuses: dict[str, str] | None = None,
        limit: int = 5,
        offset: int = 0,
        scope: PublicationScope = "variant",
    ) -> PublicationLiterature:
        bounded_limit = max(1, min(limit, 50))
        bounded_offset = max(0, offset)
        terms = VariantLiteratureTerms.build(variant)
        aggregated, breakdown = self.aggregator.collect(
            evidence_map,
            evidence_raw=evidence_raw,
            source_statuses=source_statuses,
        )
        articles = [self._article_from_aggregated(item, terms) for item in aggregated]
        articles.sort(key=_date_sort_key, reverse=True)
        publication_timeline = _build_publication_timeline(articles)
        page = articles[bounded_offset : bounded_offset + bounded_limit]
        variant_count = PublicationScopeCount(
            scope="variant",
            total_count=len(articles),
            count_kind="deduped_pmids",
            query=" ".join(terms.terms),
            source_status=_aggregate_source_status(breakdown, source_statuses),
            source_breakdown=breakdown,
        )
        gene_count = _gene_scope_count(evidence_map, source_statuses, terms.gene)
        scope_counts = PublicationScopeCounts(variant=variant_count, gene=gene_count)
        if scope == "gene":
            return PublicationLiterature(
                total_count=gene_count.total_count or 0,
                shown_count=0,
                offset=0,
                limit=bounded_limit,
                scope="gene",
                variant_terms=[terms.gene] if terms.gene else [],
                source_breakdown=gene_count.source_breakdown,
                publication_timeline=PublicationTimeline(),
                scope_counts=scope_counts,
                articles=[],
                warnings=list(gene_count.warnings),
            )

        return PublicationLiterature(
            total_count=len(articles),
            shown_count=len(page),
            offset=bounded_offset,
            limit=bounded_limit,
            scope="variant",
            variant_terms=list(terms.terms),
            source_breakdown=breakdown,
            publication_timeline=publication_timeline,
            scope_counts=scope_counts,
            articles=page,
            warnings=[],
        )

    def _article_from_aggregated(
        self,
        item: _AggregatedArticle,
        terms: VariantLiteratureTerms,
    ) -> PubMedArticle:
        source_tags = sorted(item.source_tags)
        article_data = {
            **item.data,
            "pmid": item.pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{item.pmid}/",
            "source_tags": source_tags,
        }
        snippets, status = self.snippetter.extract(article_data, terms)
        year = str(article_data.get("year") or "")
        publication_date = article_data.get("publication_date") or year or None
        return PubMedArticle(
            pmid=item.pmid,
            title=article_data.get("title") or "Untitled",
            authors=article_data.get("authors") or "",
            journal=article_data.get("journal") or "",
            year=year,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{item.pmid}/",
            abstract=article_data.get("abstract"),
            pmcid=article_data.get("pmcid"),
            doi=article_data.get("doi"),
            publication_date=publication_date,
            snippets=snippets,
            source_tags=source_tags,
            snippet_status=status,
        )
