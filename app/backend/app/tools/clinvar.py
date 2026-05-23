from __future__ import annotations

import httpx

from app.services.sequence_context import genomic_variant_id_to_refseq_hgvs
from app.tools.base import FixtureBackedTool, ToolResult


def _extract_cdna(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


def _clinvar_search_url(term: str | None) -> str | None:
    if not term:
        return None
    return f"https://www.ncbi.nlm.nih.gov/clinvar/?term={term}"


def _unavailable_summary(gene: str | None) -> dict:
    return {
        "gene": gene or "",
        "protein_change": None,
        "classification": "Unavailable",
        "review_status": "not found",
        "conditions": [],
        "consequence": "",
        "accession": None,
    }


def _fixture_matches_variant(variant, fixture: dict) -> bool:
    if variant is None:
        return True
    summary = fixture.get("summary", {}) if isinstance(fixture, dict) else {}
    fixture_gene = str(summary.get("gene") or "").upper()
    request_gene = str(getattr(variant, "gene", "") or "").upper()
    if fixture_gene and request_gene and fixture_gene != request_gene:
        return False
    search_text = _source_search_text(variant).lower()
    request_variant_id = str(getattr(variant, "genomic_hg38", "") or "").lower()
    request_genomic_hgvs = str(getattr(variant, "genomic_hgvs", "") or "").lower()
    return any(
        token in search_text or token in request_variant_id or token in request_genomic_hgvs
        for token in ("c.260a>g", "1-68444869-t-c", "68444869t>c")
    )


def _source_search_text(variant) -> str:
    gene = getattr(variant, "gene", "") or ""
    genomic_hgvs = getattr(variant, "genomic_hgvs", "") or ""
    if genomic_hgvs:
        return genomic_hgvs

    genomic_hg38 = getattr(variant, "genomic_hg38", "") or ""
    inferred_genomic_hgvs = (
        genomic_variant_id_to_refseq_hgvs(genomic_hg38) if genomic_hg38 else None
    )
    if inferred_genomic_hgvs:
        return inferred_genomic_hgvs

    source_inputs = getattr(
        getattr(variant, "search_input_resolution", None), "source_inputs", None
    )
    search_text = getattr(source_inputs, "clinvar", None) if source_inputs is not None else None
    if search_text:
        return search_text

    transcript_hgvs = getattr(variant, "transcript_hgvs", None)
    cdna = _extract_cdna(transcript_hgvs)
    return f"{gene}:{cdna}" if cdna else gene


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
            if variant is not None and not _fixture_matches_variant(variant, fixture):
                return ToolResult(
                    source=self.source,
                    status="missing",
                    request_identity={"search_text": _source_search_text(variant)},
                    summary=_unavailable_summary(gene),
                    warnings=["clinvar_fixture_variant_mismatch"],
                    raw=None,
                    source_url=_clinvar_search_url(_source_search_text(variant) or gene),
                )
            return ToolResult(
                source=self.source, status="fixture", source_url=fallback_url, **fixture
            )
        try:
            return self._fetch_live(variant)
        except Exception as exc:
            gene = variant.gene or ""
            search_text = _source_search_text(variant)
            return ToolResult(
                source=self.source,
                status="fallback",
                request_identity={"search_text": search_text or gene},
                summary=_unavailable_summary(gene),
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                raw=None,
                source_url=_clinvar_search_url(search_text or gene),
            )

    def _fetch_live(self, variant) -> ToolResult:
        gene = variant.gene
        search_text = _source_search_text(variant)

        # Step 1: resolve search term to ClinVar variation ID
        search_response = httpx.get(
            f"{self.settings.clinvar_base_url}/esearch.fcgi",
            params={"db": "clinvar", "term": search_text, "retmode": "json"},
            timeout=10.0,
        )
        search_response.raise_for_status()
        id_list = search_response.json().get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return ToolResult(
                source=self.source,
                status="live",
                request_identity={"search_text": search_text},
                summary=_unavailable_summary(gene),
                warnings=["clinvar_variant_not_found"],
                raw={},
                source_url=_clinvar_search_url(search_text),
            )
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
