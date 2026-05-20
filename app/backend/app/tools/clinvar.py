from __future__ import annotations

import httpx

from app.tools.base import FixtureBackedTool, ToolResult


def _extract_cdna(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


class ClinvarTool(FixtureBackedTool):
    source = "clinvar"
    fixture_name = "clinvar_fixtures.json"

    def get_evidence(self, variant=None) -> ToolResult:
        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            gene = (variant.gene if variant is not None else None) or ""
            fallback_url = (
                f"https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]" if gene else None
            )
            return ToolResult(
                source=self.source, status="fixture", source_url=fallback_url, **fixture
            )
        try:
            return self._fetch_live(variant)
        except Exception as exc:
            fixture = self.load_fixture()
            gene = variant.gene or ""
            fallback_url = (
                f"https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]" if gene else None
            )
            return ToolResult(
                source=self.source,
                status="fallback",
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                source_url=fallback_url,
                **fixture,
            )

    def _fetch_live(self, variant) -> ToolResult:
        gene = variant.gene
        cdna = _extract_cdna(variant.transcript_hgvs)
        search_text = f"{gene}:{cdna}" if cdna else gene

        # Step 1: resolve search term to ClinVar variation ID
        search_response = httpx.get(
            f"{self.settings.clinvar_base_url}/esearch.fcgi",
            params={"db": "clinvar", "term": search_text, "retmode": "json"},
            timeout=10.0,
        )
        search_response.raise_for_status()
        id_list = search_response.json().get("esearchresult", {}).get("idlist", [])
        if not id_list:
            raise RuntimeError(f"No ClinVar ID found for {search_text!r}")
        clinvar_id = id_list[0]

        # Step 2: fetch summary for that ID
        summary_response = httpx.get(
            f"{self.settings.clinvar_base_url}/esummary.fcgi",
            params={"db": "clinvar", "id": clinvar_id, "retmode": "json"},
            timeout=10.0,
        )
        summary_response.raise_for_status()
        payload = summary_response.json()["result"][clinvar_id]
        summary = {
            "gene": payload["genes"][0]["symbol"] if payload.get("genes") else gene,
            "protein_change": payload.get("protein_change"),
            "classification": payload["germline_classification"]["description"],
            "review_status": payload["germline_classification"]["review_status"],
            "conditions": [
                item["trait_name"] for item in payload["germline_classification"]["trait_set"]
            ],
            "consequence": (payload.get("molecular_consequence_list") or [""])[0],
            "accession": payload.get("accession"),
        }
        return ToolResult(
            source=self.source,
            status="live",
            request_identity={"search_text": search_text, "clinvar_id": clinvar_id},
            summary=summary,
            raw=payload,
            source_url=f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{clinvar_id}/",
        )
