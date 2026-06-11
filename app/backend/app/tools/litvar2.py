from __future__ import annotations

from urllib.parse import quote, quote_plus

import httpx

from app.tools.base import FixtureBackedTool, ToolResult
from app.tools.pubmed import fetch_pubmed_article_metadata


def _extract_hgvs(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


def _scholar_url(gene: str, hgvs: str | None) -> str:
    query = f"{gene} {hgvs}".strip() if hgvs else gene
    return f"https://scholar.google.com/scholar?q={quote_plus(query)}"


def _fixture_matches_variant(variant, fixture: dict) -> bool:
    if variant is None:
        return True
    request_gene = str(getattr(variant, "gene", "") or "").upper()
    if request_gene != "RPE65":
        return False
    hgvs = (_extract_hgvs(getattr(variant, "transcript_hgvs", None)) or "").lower()
    genomic_hg38 = str(getattr(variant, "genomic_hg38", "") or "").lower()
    return hgvs == "c.260a>g" or genomic_hg38 == "1-68444869-t-c"


def _empty_result(variant, *, status: str, warnings: list[str]) -> ToolResult:
    gene = str(getattr(variant, "gene", "") or "")
    hgvs = _extract_hgvs(getattr(variant, "transcript_hgvs", None))
    summary = {
        "litvar_id": None,
        "total_publications": 0,
        "articles": [],
        "scholar_url": _scholar_url(gene, hgvs),
    }
    return ToolResult(
        source=LitVar2Tool.source,
        status=status,
        request_identity={"query": f"{gene} {hgvs}".strip() if hgvs else gene},
        summary=summary,
        warnings=warnings,
        raw={},
        source_url="https://www.ncbi.nlm.nih.gov/research/litvar2-api",
    )


class LitVar2Tool(FixtureBackedTool):
    source = "litvar2"
    fixture_name = "litvar2_fixtures.json"
    HYDRATE_COUNT = 20

    def get_evidence(self, variant=None) -> ToolResult:
        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            if variant is not None and not _fixture_matches_variant(variant, fixture):
                return _empty_result(
                    variant,
                    status="missing",
                    warnings=["litvar2_fixture_variant_mismatch"],
                )
            return ToolResult(source=self.source, status="fixture", **fixture)
        try:
            return self._fetch_live(variant)
        except Exception as exc:
            fixture = self.load_fixture()
            if not _fixture_matches_variant(variant, fixture):
                return _empty_result(
                    variant,
                    status="fallback",
                    warnings=[
                        f"live_fetch_failed:{type(exc).__name__}",
                        "litvar2_fallback_fixture_variant_mismatch",
                    ],
                )
            return ToolResult(
                source=self.source,
                status="fallback",
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                **fixture,
            )

    def _fetch_live(self, variant) -> ToolResult:
        hgvs = _extract_hgvs(variant.transcript_hgvs)
        rsid = getattr(variant, "dbsnp_rsid", None)
        query = rsid or (f"{variant.gene} {hgvs}".strip() if hgvs else variant.gene)
        with httpx.Client(timeout=15.0) as client:
            autocomplete = client.get(
                f"{self.settings.litvar2_base_url}/variant/autocomplete/",
                params={"query": query},
            )
            autocomplete.raise_for_status()
            matches = autocomplete.json()
            if isinstance(matches, dict):
                items = matches.get("data") or matches.get("results") or []
            else:
                items = matches
            first = {}
            if items:
                first = next(
                    (
                        item
                        for item in items
                        if rsid and isinstance(item, dict) and item.get("rsid") == rsid
                    ),
                    items[0],
                )
            litvar_id = (
                first.get("litvar_id")
                or first.get("id")
                or first.get("_id")
                or first.get("variant_id")
            )
            if not litvar_id:
                summary = {
                    "litvar_id": None,
                    "total_publications": 0,
                    "articles": [],
                    "scholar_url": _scholar_url(variant.gene, hgvs),
                }
                return ToolResult(
                    source=self.source,
                    status="live",
                    request_identity={"query": query},
                    summary=summary,
                    raw=matches,
                    source_url=self.settings.litvar2_base_url,
                )
            litvar_id_path = quote(str(litvar_id), safe="")
            publications = client.get(
                f"{self.settings.litvar2_base_url}/variant/get/{litvar_id_path}/publications"
            )
            publications.raise_for_status()
            payload = publications.json()
            pmids = _payload_pmids(payload)
            hydration_warnings: list[str] = []
            hydrated_articles: list[dict] = []
            if pmids:
                try:
                    hydrated_articles, _ = fetch_pubmed_article_metadata(
                        self.settings,
                        pmids,
                        limit=self.HYDRATE_COUNT,
                        client=client,
                    )
                except Exception as exc:
                    hydration_warnings.append(
                        f"litvar2_pubmed_hydration_failed:{type(exc).__name__}"
                    )

        hydrated_by_pmid = {str(item.get("pmid")): item for item in hydrated_articles}
        articles = []
        for item in pmids:
            pmid = str(item).strip()
            if not pmid:
                continue
            article = hydrated_by_pmid.get(pmid)
            if article is None:
                article = {
                    "pmid": pmid,
                    "title": "",
                    "authors": "",
                    "journal": "",
                    "year": "",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "abstract": None,
                }
            articles.append(article)
        total = payload.get("pmids_count") if isinstance(payload, dict) else None
        summary = {
            "litvar_id": litvar_id,
            "total_publications": int(total if total is not None else len(articles)),
            "articles": articles,
            "scholar_url": _scholar_url(variant.gene, hgvs),
        }
        return ToolResult(
            source=self.source,
            status="live",
            request_identity={"query": query, "litvar_id": litvar_id},
            summary=summary,
            warnings=hydration_warnings,
            raw=payload,
            source_url=(
                f"{self.settings.litvar2_base_url}/variant/get/"
                f"{quote(str(litvar_id), safe='')}/publications"
            ),
        )


def _payload_pmids(payload) -> list[str]:
    if not isinstance(payload, dict):
        return []
    pmids = payload.get("pmids", [])
    if not isinstance(pmids, list):
        return []
    values: list[str] = []
    for item in pmids:
        pmid = str(item).strip()
        if pmid:
            values.append(pmid)
    return values
