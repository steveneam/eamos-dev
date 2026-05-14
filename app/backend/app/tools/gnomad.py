from __future__ import annotations

import httpx

from app.tools.base import FixtureBackedTool, ToolResult

GNOMAD_GRAPHQL_URL = "https://gnomad.broadinstitute.org/api"

_GNOMAD_QUERY = """
query GnomadVariant($variantId: String!, $dataset: DatasetId!) {
  variant(variantId: $variantId, dataset: $dataset) {
    variantId
    exome {
      ac
      an
      ac_hom
      af
      faf95 { popmax popmax_population }
    }
    genome {
      ac
      an
      ac_hom
      af
      faf95 { popmax popmax_population }
    }
    flags
  }
}
"""


def _extract_cdna(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


class GnomadTool(FixtureBackedTool):
    source = "gnomad"
    fixture_name = "gnomad_fixtures.json"
    DATASET = "gnomad_r4"

    def get_evidence(self, variant=None) -> ToolResult:
        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            gene = (variant.gene if variant is not None else None) or ""
            fallback_url = (
                f"https://gnomad.broadinstitute.org/gene/{gene}?dataset={self.DATASET}" if gene else None
            )
            return ToolResult(source=self.source, status="fixture", source_url=fallback_url, **fixture)
        try:
            return self._fetch_live(variant)
        except Exception as exc:
            fixture = self.load_fixture()
            gene = variant.gene or ""
            fallback_url = (
                f"https://gnomad.broadinstitute.org/gene/{gene}?dataset={self.DATASET}" if gene else None
            )
            return ToolResult(
                source=self.source,
                status="fallback",
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                source_url=fallback_url,
                **fixture,
            )

    def _fetch_live(self, variant) -> ToolResult:
        """
        gnomAD v4 GraphQL query.
        Requires a genomic variant ID in the form chr-pos-ref-alt (e.g. 1-68444869-T-C).
        The variant object must carry a populated genomic_hg38 field from VEP;
        without it the live query cannot be constructed and a stub is returned.
        """
        gene = variant.gene
        cdna = _extract_cdna(variant.transcript_hgvs)
        variant_id = getattr(variant, "genomic_hg38", None)

        if not variant_id:
            return ToolResult(
                source=self.source,
                status="live_stub",
                request_identity={"gene": gene, "cdna": cdna},
                summary={},
                warnings=[
                    "gnomAD live query requires genomic coordinates (chr-pos-ref-alt) "
                    "from VEP; populate variant.genomic_hg38 before calling live mode."
                ],
                source_url=(
                    f"https://gnomad.broadinstitute.org/gene/{gene}?dataset={self.DATASET}"
                    if gene else None
                ),
            )

        response = httpx.post(
            GNOMAD_GRAPHQL_URL,
            json={
                "query": _GNOMAD_QUERY,
                "variables": {"variantId": variant_id, "dataset": self.DATASET},
            },
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json().get("data", {}).get("variant") or {}

        exome = data.get("exome") or {}
        genome = data.get("genome") or {}

        # Prefer exome; fall back to genome for non-exome-captured variants
        source_data = exome if exome.get("ac") else genome
        faf = source_data.get("faf95") or {}

        summary = {
            "gene": gene,
            "variant_id": variant_id,
            "allele_frequency": source_data.get("af"),
            "allele_count": source_data.get("ac"),
            "allele_number": source_data.get("an"),
            "homozygote_count": source_data.get("ac_hom"),
            "popmax_frequency": faf.get("popmax"),
            "popmax_population": faf.get("popmax_population"),
            "flags": data.get("flags", []),
            "url": (
                f"https://gnomad.broadinstitute.org/variant/{variant_id}"
                f"?dataset={self.DATASET}"
            ),
        }
        return ToolResult(
            source=self.source,
            status="live",
            request_identity={"variant_id": variant_id, "dataset": self.DATASET},
            summary=summary,
            raw=data,
            source_url=f"https://gnomad.broadinstitute.org/variant/{variant_id}?dataset={self.DATASET}",
        )
