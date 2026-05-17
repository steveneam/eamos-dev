from __future__ import annotations

from urllib.parse import quote_plus

import httpx

from app.tools.base import FixtureBackedTool, ToolResult


def _extract_hgvs(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


def _scholar_url(gene: str, hgvs: str | None) -> str:
    query = f"{gene} {hgvs}".strip() if hgvs else gene
    return f"https://scholar.google.com/scholar?q={quote_plus(query)}"


class LitVar2Tool(FixtureBackedTool):
    source = "litvar2"
    fixture_name = "litvar2_fixtures.json"

    def get_evidence(self, variant=None) -> ToolResult:
        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            return ToolResult(source=self.source, status="fixture", **fixture)
        try:
            return self._fetch_live(variant)
        except Exception as exc:
            fixture = self.load_fixture()
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
            publications = client.get(
                f"{self.settings.litvar2_base_url}/variant/get/{litvar_id}/publications"
            )
            publications.raise_for_status()
            payload = publications.json()

        pmids = payload.get("pmids", []) if isinstance(payload, dict) else []
        articles = []
        for item in pmids or []:
            pmid = str(item)
            if not pmid:
                continue
            articles.append(
                {
                    "pmid": pmid,
                    "title": "",
                    "authors": "",
                    "journal": "",
                    "year": "",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "abstract": None,
                }
            )
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
            raw=payload,
            source_url=f"{self.settings.litvar2_base_url}/variant/get/{litvar_id}/publications",
        )
