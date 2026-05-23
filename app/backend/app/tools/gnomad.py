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
      homozygote_count
      af
      populations { id ac an homozygote_count }
      age_distribution {
        het { bin_edges bin_freq n_smaller n_larger }
        hom { bin_edges bin_freq n_smaller n_larger }
      }
      faf95 { popmax popmax_population }
    }
    genome {
      ac
      an
      homozygote_count
      af
      populations { id ac an homozygote_count }
      age_distribution {
        het { bin_edges bin_freq n_smaller n_larger }
        hom { bin_edges bin_freq n_smaller n_larger }
      }
      faf95 { popmax popmax_population }
    }
    joint {
      ac
      an
      homozygote_count
      populations { id ac an homozygote_count }
      age_distribution {
        het { bin_edges bin_freq n_smaller n_larger }
        hom { bin_edges bin_freq n_smaller n_larger }
      }
      faf95 { popmax popmax_population }
    }
    flags
  }
}
"""

CORE_GENETIC_ANCESTRY_GROUPS = {
    "afr",
    "ami",
    "amr",
    "asj",
    "eas",
    "fin",
    "mid",
    "nfe",
    "remaining",
    "sas",
}


def _variant_source_url(variant_id: str | None) -> str | None:
    if not variant_id:
        return None
    return f"https://gnomad.broadinstitute.org/variant/{variant_id}?dataset={GnomadTool.DATASET}"


def _gene_source_url(gene: str | None) -> str | None:
    if not gene:
        return None
    return f"https://gnomad.broadinstitute.org/gene/{gene}?dataset={GnomadTool.DATASET}"


def _extract_cdna(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


def _allele_frequency(data: dict) -> float | None:
    if data.get("af") is not None:
        return data.get("af")
    ac = data.get("ac")
    an = data.get("an")
    if ac is None or not an:
        return None
    return ac / an


def _select_sequencing_type(data: dict) -> tuple[str, dict]:
    joint = data.get("joint") or {}
    if joint.get("an") is not None:
        return "joint", joint
    exome = data.get("exome") or {}
    genome = data.get("genome") or {}
    if exome.get("an") is not None and (exome.get("ac") or genome.get("an") is None):
        return "exome", exome
    if genome.get("an") is not None:
        return "genome", genome
    return "unknown", {}


def _age_distribution_for(data: dict, source_data: dict) -> dict | None:
    if isinstance(source_data.get("age_distribution"), dict):
        return source_data["age_distribution"]
    for key in ("exome", "genome"):
        source = data.get(key) or {}
        if isinstance(source.get("age_distribution"), dict):
            return source["age_distribution"]
    return None


def _genetic_ancestry_groups(source_data: dict) -> list[dict]:
    groups = []
    for item in source_data.get("populations") or []:
        if not isinstance(item, dict):
            continue
        group_id = str(item.get("id") or "").strip()
        if group_id not in CORE_GENETIC_ANCESTRY_GROUPS:
            continue
        ac = item.get("ac")
        an = item.get("an")
        groups.append(
            {
                "id": group_id,
                "allele_count": ac,
                "allele_number": an,
                "allele_frequency": (ac / an) if ac is not None and an else None,
                "homozygote_count": item.get("homozygote_count"),
            }
        )
    return groups


def _fixture_matches_variant(variant, fixture: dict) -> bool:
    if variant is None:
        return True
    summary = fixture.get("summary", {}) if isinstance(fixture, dict) else {}
    fixture_gene = str(summary.get("gene") or "").upper()
    request_gene = str(getattr(variant, "gene", "") or "").upper()
    if fixture_gene and request_gene and fixture_gene != request_gene:
        return False
    fixture_variant = str(summary.get("variant_id") or "").strip().lower()
    request_variant = str(getattr(variant, "genomic_hg38", "") or "").strip().lower()
    if fixture_variant and request_variant and fixture_variant == request_variant:
        return True
    request_cdna = _extract_cdna(getattr(variant, "transcript_hgvs", None))
    return bool(request_gene == "RPE65" and request_cdna == "c.260A>G")


def _unavailable_result(variant, *, status: str, warnings: list[str]) -> ToolResult:
    gene = str(getattr(variant, "gene", "") or "")
    variant_id = str(getattr(variant, "genomic_hg38", "") or "")
    source_url = _variant_source_url(variant_id) or _gene_source_url(gene)
    return ToolResult(
        source=GnomadTool.source,
        status=status,
        request_identity={
            key: value
            for key, value in {"variant_id": variant_id, "dataset": GnomadTool.DATASET}.items()
            if value
        },
        summary={
            key: value
            for key, value in {
                "gene": gene,
                "variant_id": variant_id,
                "dataset": GnomadTool.DATASET,
                "url": source_url,
            }.items()
            if value
        },
        warnings=warnings,
        raw=None,
        source_url=source_url,
    )


class GnomadTool(FixtureBackedTool):
    source = "gnomad"
    fixture_name = "gnomad_fixtures.json"
    DATASET = "gnomad_r4"

    def get_evidence(self, variant=None) -> ToolResult:
        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            if variant is not None and not _fixture_matches_variant(variant, fixture):
                return _unavailable_result(
                    variant,
                    status="missing",
                    warnings=["gnomad_fixture_variant_mismatch"],
                )
            gene = (variant.gene if variant is not None else None) or ""
            fallback_url = _gene_source_url(gene)
            return ToolResult(
                source=self.source, status="fixture", source_url=fallback_url, **fixture
            )
        try:
            return self._fetch_live(variant)
        except Exception as exc:
            fixture = self.load_fixture()
            gene = variant.gene or ""
            variant_id = getattr(variant, "genomic_hg38", None)
            fallback_url = _variant_source_url(variant_id) or _gene_source_url(gene)
            warnings = [f"live_fetch_failed:{type(exc).__name__}"]
            if not _fixture_matches_variant(variant, fixture):
                warnings.append("gnomad_fallback_fixture_variant_mismatch")
                return _unavailable_result(variant, status="fallback", warnings=warnings)
            return ToolResult(
                source=self.source,
                status="fallback",
                warnings=warnings,
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
                    "from identifier resolution; populate variant.genomic_hg38 before "
                    "calling live mode."
                ],
                source_url=(
                    f"https://gnomad.broadinstitute.org/gene/{gene}?dataset={self.DATASET}"
                    if gene
                    else None
                ),
            )

        response = httpx.post(
            GNOMAD_GRAPHQL_URL,
            json={
                "query": _GNOMAD_QUERY,
                "variables": {"variantId": variant_id, "dataset": self.DATASET},
            },
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )
        response.raise_for_status()
        body = response.json()
        data = body.get("data", {}).get("variant")
        source_url = (
            f"https://gnomad.broadinstitute.org/variant/{variant_id}?dataset={self.DATASET}"
        )

        if not data:
            return ToolResult(
                source=self.source,
                status="live",
                request_identity={"variant_id": variant_id, "dataset": self.DATASET},
                summary={
                    "gene": gene,
                    "variant_id": variant_id,
                    "dataset": self.DATASET,
                    "url": source_url,
                },
                raw=body,
                warnings=["gnomad_variant_not_found"],
                source_url=source_url,
            )

        sequencing_type, source_data = _select_sequencing_type(data)
        faf = source_data.get("faf95") or {}

        summary = {
            "gene": gene,
            "variant_id": variant_id,
            "dataset": self.DATASET,
            "sequencing_type": sequencing_type,
            "allele_frequency": _allele_frequency(source_data),
            "allele_count": source_data.get("ac"),
            "allele_number": source_data.get("an"),
            "homozygote_count": source_data.get("homozygote_count"),
            "popmax_frequency": faf.get("popmax"),
            "popmax_population": faf.get("popmax_population"),
            "genetic_ancestry_groups": _genetic_ancestry_groups(source_data),
            "age_distribution": _age_distribution_for(data, source_data),
            "flags": data.get("flags", []),
            "url": source_url,
        }
        return ToolResult(
            source=self.source,
            status="live",
            request_identity={"variant_id": variant_id, "dataset": self.DATASET},
            summary=summary,
            raw=data,
            source_url=source_url,
        )
