from __future__ import annotations

import httpx

from app.tools.base import FixtureBackedTool, ToolResult


def _extract_cdna(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


def _variant_id_key(value: str | None) -> str:
    text = (value or "").strip()
    if text.startswith("chr"):
        text = text[3:]
    return text.lower()


def _fixture_matches_variant(variant, fixture: dict) -> bool:
    if variant is None:
        return True
    summary = fixture.get("summary", {}) if isinstance(fixture, dict) else {}
    fixture_gene = str(summary.get("gene") or "").upper()
    request_gene = str(getattr(variant, "gene", "") or "").upper()
    if fixture_gene and request_gene and fixture_gene != request_gene:
        return False
    request_identity = fixture.get("request_identity", {}) if isinstance(fixture, dict) else {}
    fixture_variant = _variant_id_key(str(request_identity.get("variant") or ""))
    request_variant = _variant_id_key(getattr(variant, "genomic_hg38", None))
    if fixture_variant and request_variant and fixture_variant == request_variant:
        return True
    request_cdna = _extract_cdna(getattr(variant, "transcript_hgvs", None))
    return bool(request_gene == "RPE65" and request_cdna == "c.260A>G")


def _unavailable_result(variant, *, status: str, warnings: list[str]) -> ToolResult:
    gene = str(getattr(variant, "gene", "") or "")
    cdna = _extract_cdna(getattr(variant, "transcript_hgvs", None))
    return ToolResult(
        source=SpliceAiTool.source,
        status=status,
        request_identity={"gene": gene, "cdna": cdna} if cdna else {"gene": gene},
        summary={},
        warnings=warnings,
        raw=None,
        source_url=SpliceAiTool._TOOL_URL,
    )


class SpliceAiTool(FixtureBackedTool):
    source = "spliceai"
    fixture_name = "spliceai_fixtures.json"
    HG = 38
    DISTANCE = 500
    MASK = 0

    _TOOL_URL = "https://spliceailookup.broadinstitute.org/"

    def get_evidence(self, variant=None) -> ToolResult:
        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            if variant is not None and not _fixture_matches_variant(variant, fixture):
                return _unavailable_result(
                    variant,
                    status="missing",
                    warnings=["spliceai_fixture_variant_mismatch"],
                )
            return ToolResult(
                source=self.source, status="fixture", source_url=self._TOOL_URL, **fixture
            )
        try:
            return self._fetch_live(variant)
        except Exception as exc:
            fixture = self.load_fixture()
            if not _fixture_matches_variant(variant, fixture):
                return _unavailable_result(
                    variant,
                    status="fallback",
                    warnings=[
                        f"live_fetch_failed:{type(exc).__name__}",
                        "spliceai_fallback_fixture_variant_mismatch",
                    ],
                )
            return ToolResult(
                source=self.source,
                status="fallback",
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                source_url=self._TOOL_URL,
                **fixture,
            )

    def _fetch_live(self, variant) -> ToolResult:
        gene = variant.gene
        cdna = _extract_cdna(variant.transcript_hgvs)
        genomic_hg38 = getattr(variant, "genomic_hg38", None)

        if not genomic_hg38:
            return ToolResult(
                source=self.source,
                status="live_stub",
                request_identity={"gene": gene, "cdna": cdna},
                summary={},
                warnings=[
                    "SpliceAI live query requires genomic coordinates (chr-pos-ref-alt) "
                    "from identifier resolution; populate variant.genomic_hg38 before "
                    "calling live mode."
                ],
                source_url=self._TOOL_URL,
            )

        response = httpx.get(
            self.settings.spliceai_base_url,
            params={
                "hg": self.HG,
                "variant": genomic_hg38,
                "distance": self.DISTANCE,
                "mask": self.MASK,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        top = payload["scores"][0]
        summary = {
            "gene": top.get("g_name"),
            "transcript_id": top.get("t_id"),
            "acceptor_loss": float(top.get("DS_AL", 0.0)),
            "donor_loss": float(top.get("DS_DL", 0.0)),
            "acceptor_gain": float(top.get("DS_AG", 0.0)),
            "donor_gain": float(top.get("DS_DG", 0.0)),
            "distance": int(payload.get("distance", self.DISTANCE)),
            "mask": int(payload.get("mask", self.MASK)),
        }
        return ToolResult(
            source=self.source,
            status="live",
            request_identity={
                "hg": self.HG,
                "variant": genomic_hg38,
                "distance": self.DISTANCE,
                "mask": self.MASK,
            },
            summary=summary,
            raw=payload,
            source_url=self._TOOL_URL,
        )
