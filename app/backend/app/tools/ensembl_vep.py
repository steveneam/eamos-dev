from __future__ import annotations

from collections import Counter

import httpx

from app.tools.base import FixtureBackedTool, ToolResult


def _extract_cdna(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    return transcript_hgvs.split(":")[-1]


def _fixture_matches_variant(variant, summary: dict) -> bool:
    if variant is None:
        return True
    fixture_gene = str(summary.get("gene") or "").upper()
    request_gene = str(getattr(variant, "gene", "") or "").upper()
    if fixture_gene and request_gene and fixture_gene != request_gene:
        return False
    request_cdna = _extract_cdna(getattr(variant, "transcript_hgvs", None))
    fixture_hgvs = str(summary.get("hgvs") or summary.get("input") or "")
    if not fixture_hgvs:
        fixture_hgvs = "c.260A>G" if fixture_gene == "RPE65" else ""
    return bool(request_cdna and fixture_hgvs.endswith(request_cdna))


def _missing_result(variant, *, warning: str) -> ToolResult:
    hgvs = getattr(variant, "transcript_hgvs", None)
    fallback_url = (
        f"https://www.ensembl.org/Homo_sapiens/Variation/Explore?v={hgvs}" if hgvs else None
    )
    return ToolResult(
        source=EnsemblVepTool.source,
        status="missing",
        request_identity={"hgvs": hgvs} if hgvs else {},
        summary={},
        warnings=[warning],
        raw=None,
        source_url=fallback_url,
    )


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
            if variant is not None and not _fixture_matches_variant(
                variant, fixture.get("summary", {})
            ):
                return _missing_result(variant, warning="vep_fixture_variant_mismatch")
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
            if not _fixture_matches_variant(variant, fixture.get("summary", {})):
                result = _missing_result(variant, warning="vep_fallback_fixture_variant_mismatch")
                result.status = "fallback"
                result.warnings.insert(0, f"live_fetch_failed:{type(exc).__name__}")
                return result
            return ToolResult(
                source=self.source,
                status="fallback",
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                source_url=fallback_url,
                **fixture,
            )

    def _fetch_live(self, variant) -> ToolResult:
        source_inputs = getattr(
            getattr(variant, "search_input_resolution", None), "source_inputs", None
        )
        hgvs = getattr(source_inputs, "ensembl_vep", None) if source_inputs is not None else None
        if source_inputs is not None and not hgvs:
            return ToolResult(
                source=self.source,
                status="live_stub",
                request_identity={"submitted": variant.transcript_hgvs},
                summary={},
                warnings=[
                    "Ensembl VEP live query requires transcript HGVS or RefSeq genomic HGVS; "
                    "no source-specific VEP identifier was resolved."
                ],
                source_url=None,
            )
        hgvs = hgvs or variant.transcript_hgvs
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
            "exon": canonical.get("exon"),
            "codons": canonical.get("codons"),
            "protein_change": canonical.get("amino_acids"),
            "cds_position": canonical.get("cds_start"),
            "protein_position": canonical.get("protein_start"),
            "strand": _strand_label(canonical.get("strand")),
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


def _strand_label(value) -> str | None:
    if value in {1, "1", "+", "+1"}:
        return "+"
    if value in {-1, "-1", "-"}:
        return "-"
    return None
