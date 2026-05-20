from __future__ import annotations

from collections import Counter

import httpx

from app.tools.base import FixtureBackedTool, ToolResult


class EnsemblVepTool(FixtureBackedTool):
    source = "vep"
    fixture_name = "vep_fixtures.json"

    def get_evidence(self, variant=None) -> ToolResult:
        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            hgvs = variant.transcript_hgvs if variant is not None else None
            fallback_url = (
                f"https://www.ensembl.org/Homo_sapiens/Variation/Explore?v={hgvs}" if hgvs else None
            )
            return ToolResult(
                source=self.source, status="fixture", source_url=fallback_url, **fixture
            )
        try:
            return self._fetch_live(variant)
        except Exception as exc:
            fixture = self.load_fixture()
            hgvs = variant.transcript_hgvs
            fallback_url = (
                f"https://www.ensembl.org/Homo_sapiens/Variation/Explore?v={hgvs}" if hgvs else None
            )
            return ToolResult(
                source=self.source,
                status="fallback",
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                source_url=fallback_url,
                **fixture,
            )

    def _fetch_live(self, variant) -> ToolResult:
        hgvs = variant.transcript_hgvs
        gene = variant.gene

        response = httpx.get(
            f"{self.settings.vep_base_url}/vep/human/hgvs/{hgvs}",
            params={"content-type": "application/json"},
            headers={"Accept": "application/json"},
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()[0]
        consequences = payload.get("transcript_consequences", [])

        # Pick the canonical transcript for the target gene; fall back to first result
        canonical = next(
            (item for item in consequences if item.get("gene_symbol") == gene),
            consequences[0] if consequences else {},
        )

        term_counter = Counter(
            term for item in consequences for term in item.get("consequence_terms", [])
        )
        total_terms = sum(term_counter.values()) or 1
        distribution = {
            key: round((count / total_terms) * 100, 1) for key, count in term_counter.items()
        }
        summary = {
            "gene": canonical.get("gene_symbol"),
            "transcript_id": canonical.get("transcript_id"),
            "biotype": canonical.get("biotype"),
            "protein_change": canonical.get("amino_acids"),
            "cds_position": canonical.get("cds_start"),
            "protein_position": canonical.get("protein_start"),
            "most_severe_consequence": payload.get("most_severe_consequence"),
            "consequence_distribution": distribution,
        }
        return ToolResult(
            source=self.source,
            status="live",
            request_identity={"hgvs": hgvs},
            summary=summary,
            raw=payload,
            source_url=f"https://www.ensembl.org/Homo_sapiens/Variation/Explore?v={hgvs}",
        )
