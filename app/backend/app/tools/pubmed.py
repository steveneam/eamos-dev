from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from app.services.pubmed_local import PubMedLocalStore
from app.tools.base import FixtureBackedTool, ToolResult


def _extract_cdna(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


def _protein_identifier(protein_change: str | None) -> str | None:
    if not protein_change:
        return None
    protein = protein_change.strip()
    if protein.startswith("p."):
        protein = protein[2:]
    if protein.startswith("(") and protein.endswith(")") and len(protein) > 2:
        protein = protein[1:-1]
    return protein or None


def _identifier_term(identifier: str) -> str:
    return f'"{identifier}"[Title/Abstract]'


def _gene_scope_query(gene: str) -> str:
    return f"{gene}[Gene Name]"


def _gene_scope_url(gene: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/?term={gene}[gene]"


def _source_reported_count(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _gene_scope_from_esearch(gene: str, search_result: dict, *, status: str) -> dict | None:
    total_count = _source_reported_count(search_result.get("count"))
    if total_count is None:
        return None
    return {
        "query": _gene_scope_query(gene),
        "total_count": total_count,
        "source_status": status,
        "source_url": _gene_scope_url(gene),
    }


def _fixture_matches_variant(variant, fixture: dict) -> bool:
    if variant is None:
        return True
    request_gene = str(getattr(variant, "gene", "") or "").upper()
    if request_gene != "RPE65":
        return False
    cdna = (_extract_cdna(getattr(variant, "transcript_hgvs", None)) or "").lower()
    protein = (_protein_identifier(getattr(variant, "protein_change", None)) or "").lower()
    genomic_hg38 = str(getattr(variant, "genomic_hg38", "") or "").lower()
    return any(
        token
        for token in (
            cdna == "c.260a>g",
            protein in {"asp87gly", "d87g"},
            genomic_hg38 == "1-68444869-t-c",
        )
    )


def _empty_result(variant, *, status: str, warnings: list[str]) -> ToolResult:
    gene = str(getattr(variant, "gene", "") or "")
    cdna = _extract_cdna(getattr(variant, "transcript_hgvs", None))
    term = _gene_scope_query(gene)
    if cdna:
        term = f"{gene}[Gene Name] AND {_identifier_term(cdna)}"
    return ToolResult(
        source=PubmedTool.source,
        status=status,
        request_identity={"term": term},
        summary={"articles": [], "total": 0},
        warnings=warnings,
        raw={},
        source_url=_gene_scope_url(gene) if gene else None,
    )


def _with_extra_warnings(result: ToolResult, warnings: list[str]) -> ToolResult:
    if not warnings:
        return result
    result.warnings = [*warnings, *result.warnings]
    return result


def _eutils_params(settings: Any, params: dict[str, object]) -> dict[str, object]:
    payload = dict(params)
    if settings.ncbi_eutils_tool:
        payload["tool"] = settings.ncbi_eutils_tool
    if settings.ncbi_eutils_email:
        payload["email"] = settings.ncbi_eutils_email
    if settings.ncbi_eutils_api_key:
        payload["api_key"] = settings.ncbi_eutils_api_key
    return payload


def _author_display(authors: list[dict[str, Any]]) -> str:
    if len(authors) == 0:
        return "Unknown"
    if len(authors) == 1:
        return authors[0].get("name", "Unknown")
    return f"{authors[0].get('name', '')} et al."


def _article_from_pubmed_summary(
    pmid: str,
    entry: dict[str, Any],
    abstracts: dict[str, str],
) -> dict[str, Any]:
    authors = entry.get("authors", [])
    return {
        "pmid": pmid,
        "title": entry.get("title", "Untitled"),
        "authors": _author_display(authors if isinstance(authors, list) else []),
        "journal": entry.get("source", ""),
        "year": (entry.get("pubdate", "") or "")[:4],
        "publication_date": entry.get("sortpubdate") or entry.get("pubdate") or None,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "abstract": abstracts.get(pmid),
    }


def fetch_pubmed_article_metadata(
    settings: Any,
    pmids: list[str],
    *,
    limit: int = 50,
    client: httpx.Client | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bounded_limit = max(0, min(int(limit), 50))
    unique_pmids: list[str] = []
    for item in pmids:
        pmid = str(item).strip()
        if not pmid or not pmid.isdigit() or pmid in unique_pmids:
            continue
        unique_pmids.append(pmid)
        if len(unique_pmids) >= bounded_limit:
            break
    if not unique_pmids:
        return [], {}

    def _fetch(active_client: httpx.Client) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        pmid_str = ",".join(unique_pmids)
        summary_resp = active_client.get(
            f"{settings.clinvar_base_url}/esummary.fcgi",
            params=_eutils_params(settings, {"db": "pubmed", "id": pmid_str, "retmode": "json"}),
        )
        fetch_resp = active_client.get(
            f"{settings.clinvar_base_url}/efetch.fcgi",
            params=_eutils_params(
                settings,
                {"db": "pubmed", "id": pmid_str, "retmode": "xml", "rettype": "abstract"},
            ),
        )
        summary_resp.raise_for_status()
        fetch_resp.raise_for_status()

        result = summary_resp.json().get("result", {})
        abstracts = _parse_abstracts_xml(fetch_resp.text)
        articles = []
        for pmid in unique_pmids:
            entry = result.get(pmid, {})
            if not entry or pmid == "uids":
                continue
            articles.append(_article_from_pubmed_summary(pmid, entry, abstracts))
        return articles, result

    if client is not None:
        return _fetch(client)
    with httpx.Client(timeout=12.0) as owned_client:
        return _fetch(owned_client)


class PubmedTool(FixtureBackedTool):
    source = "pubmed"
    fixture_name = "pubmed_fixtures.json"
    FETCH_COUNT = 10

    def get_evidence(self, variant=None, *, refresh: bool = False) -> ToolResult:
        local_warnings: list[str] = []
        if self.settings.pubmed_local_enabled and variant is not None and not refresh:
            db_path = self.settings.pubmed_local_sqlite_path
            manifest_path = self.settings.pubmed_local_manifest_path
            if not db_path.is_absolute():
                db_path = self.settings.backend_root / db_path
            if not manifest_path.is_absolute():
                manifest_path = self.settings.backend_root / manifest_path
            local_store = PubMedLocalStore(
                db_path,
                manifest_path=manifest_path,
                enabled=True,
            )
            local_result, needs_live_fallback = local_store.search_tool_result(
                variant,
                limit=max(1, min(int(self.settings.pubmed_local_max_results), 50)),
            )
            local_warnings.extend(local_result.warnings)
            if local_result.status == "local" and (
                local_result.summary.get("articles")
                or not needs_live_fallback
                or not self.settings.pubmed_local_fallback_on_no_hit
                or not self.settings.use_real_apis
            ):
                return local_result

        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            gene = (variant.gene if variant is not None else None) or ""
            fallback_url = _gene_scope_url(gene) if gene else None
            if variant is not None and not _fixture_matches_variant(variant, fixture):
                return _with_extra_warnings(
                    _empty_result(
                        variant,
                        status="missing",
                        warnings=["pubmed_fixture_variant_mismatch"],
                    ),
                    local_warnings,
                )
            return _with_extra_warnings(
                ToolResult(
                    source=self.source, status="fixture", source_url=fallback_url, **fixture
                ),
                local_warnings,
            )
        try:
            result = self._fetch_live(variant)
            if local_warnings:
                result.warnings = [
                    *local_warnings,
                    "pubmed_local_no_hit_live_fallback",
                    *result.warnings,
                ]
            return result
        except Exception as exc:
            fixture = self.load_fixture()
            gene = variant.gene or ""
            fallback_url = _gene_scope_url(gene) if gene else None
            if not _fixture_matches_variant(variant, fixture):
                return _with_extra_warnings(
                    _empty_result(
                        variant,
                        status="fallback",
                        warnings=[
                            f"live_fetch_failed:{type(exc).__name__}",
                            "pubmed_fallback_fixture_variant_mismatch",
                        ],
                    ),
                    local_warnings,
                )
            return _with_extra_warnings(
                ToolResult(
                    source=self.source,
                    status="fallback",
                    warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                    source_url=fallback_url,
                    **fixture,
                ),
                local_warnings,
            )

    def _fetch_live(self, variant) -> ToolResult:
        gene = variant.gene
        cdna = _extract_cdna(variant.transcript_hgvs)
        protein = _protein_identifier(getattr(variant, "protein_change", None))
        rsid = getattr(variant, "dbsnp_rsid", None)

        identifiers = [item for item in (cdna, protein, rsid) if item]
        if identifiers:
            or_group = " OR ".join(_identifier_term(item) for item in identifiers)
            term = f"{gene}[Gene Name] AND ({or_group})"
        else:
            term = _gene_scope_query(gene)

        search_response = httpx.get(
            f"{self.settings.clinvar_base_url}/esearch.fcgi",
            params=self._eutils_params(
                {
                    "db": "pubmed",
                    "term": term,
                    "retmax": self.FETCH_COUNT,
                    "retmode": "json",
                    "sort": "relevance",
                }
            ),
            timeout=10.0,
        )
        search_response.raise_for_status()
        search_result = search_response.json().get("esearchresult", {})
        id_list = search_result.get("idlist", [])
        gene_scope = (
            _gene_scope_from_esearch(gene, search_result, status="live")
            if term == _gene_scope_query(gene)
            else None
        )

        if not id_list:
            if identifiers:
                gene_scope = self._fetch_gene_scope_count(gene)
                summary = {"articles": [], "total": 0}
                if gene_scope is not None:
                    summary["gene_scope"] = gene_scope
                return ToolResult(
                    source=self.source,
                    status="live",
                    request_identity={"term": term, "gene_scope_term": _gene_scope_query(gene)},
                    summary=summary,
                    raw={},
                    source_url=_gene_scope_url(gene),
                )
            summary = {"articles": [], "total": 0}
            if gene_scope is not None:
                summary["gene_scope"] = gene_scope
            return ToolResult(
                source=self.source,
                status="live",
                request_identity={"term": term},
                summary=summary,
                raw={},
                source_url=_gene_scope_url(gene),
            )

        if gene_scope is None:
            gene_scope = self._fetch_gene_scope_count(gene)

        articles, result = fetch_pubmed_article_metadata(
            self.settings,
            [str(item) for item in id_list],
            limit=self.FETCH_COUNT,
        )

        summary = {"articles": articles, "total": len(articles)}
        if gene_scope is not None:
            summary["gene_scope"] = gene_scope

        return ToolResult(
            source=self.source,
            status="live",
            request_identity={"term": term},
            summary=summary,
            raw=result,
            source_url=_gene_scope_url(gene),
        )

    def _eutils_params(self, params: dict[str, object]) -> dict[str, object]:
        return _eutils_params(self.settings, params)

    def _fetch_gene_scope_count(self, gene: str) -> dict | None:
        try:
            response = httpx.get(
                f"{self.settings.clinvar_base_url}/esearch.fcgi",
                params=self._eutils_params(
                    {
                        "db": "pubmed",
                        "term": _gene_scope_query(gene),
                        "retmax": 0,
                        "retmode": "json",
                    }
                ),
                timeout=10.0,
            )
            response.raise_for_status()
            search_result = response.json().get("esearchresult", {})
        except Exception:
            return None
        return _gene_scope_from_esearch(gene, search_result, status="live")


def _parse_abstracts_xml(xml_text: str) -> dict[str, str]:
    """Return {pmid: abstract_text} from an efetch XML response."""
    abstracts: dict[str, str] = {}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return abstracts
    for article_el in root.iter("PubmedArticle"):
        pmid_el = article_el.find(".//MedlineCitation/PMID")
        if pmid_el is None or not pmid_el.text:
            continue
        pmid = pmid_el.text.strip()
        parts: list[str] = []
        for abstract_el in article_el.findall(".//Abstract/AbstractText"):
            text = "".join(abstract_el.itertext()).strip()
            if text:
                label = abstract_el.get("Label")
                parts.append(f"{label}: {text}" if label else text)
        if parts:
            abstracts[pmid] = " ".join(parts)
    return abstracts
