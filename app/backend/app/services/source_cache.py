from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.schemas.lookup import LookupRequest, LookupResponse


@dataclass(frozen=True)
class HeroExampleVariant:
    label: str
    gene: str
    cdna: str

    @property
    def cache_key(self) -> str:
        return source_cache_key(self.gene, self.cdna)


def source_cache_key(gene: str, cdna: str) -> str:
    return f"{gene.strip().upper()}:{cdna.strip()}"


def clingen_vcep_source_cache_key(
    *,
    gene: str,
    transcript_hgvs: str | None = None,
    cdna: str | None = None,
    genomic_hgvs: str | None = None,
    genomic_hg38: str | None = None,
    caid: str | None = None,
    clinvar_summary: dict[str, Any] | None = None,
    clinvar_raw: Any = None,
) -> str | None:
    """Return the CAR #3 ClinGen ERepo cache key with explicit precedence."""

    normalized_caid = _caid(caid) or _first_caid(clinvar_summary) or _first_caid(clinvar_raw)
    if normalized_caid:
        return f"caid:{normalized_caid}"

    normalized_vcv = _vcv_from_clinvar(clinvar_summary) or _vcv_from_clinvar(clinvar_raw)
    if normalized_vcv:
        return f"clinvar:{normalized_vcv}"

    gene_key = gene.strip().upper()
    if not gene_key:
        return None
    for value in (transcript_hgvs, genomic_hgvs, genomic_hg38, cdna):
        hgvs = _hgvs_token(value)
        if hgvs:
            return f"hgvs:{gene_key}:{hgvs}"
    return None


HERO_EXAMPLE_VARIANTS: tuple[HeroExampleVariant, ...] = (
    HeroExampleVariant(label="RPE65 c.11+5G>A", gene="RPE65", cdna="c.11+5G>A"),
    HeroExampleVariant(label="USH2A c.2276G>T", gene="USH2A", cdna="c.2276G>T"),
    HeroExampleVariant(label="BRCA1 c.5266dupC", gene="BRCA1", cdna="c.5266dupC"),
)

_HERO_EXAMPLE_KEYS = {item.cache_key for item in HERO_EXAMPLE_VARIANTS}


def is_hero_example_variant(gene: str, cdna: str) -> bool:
    return source_cache_key(gene, cdna) in _HERO_EXAMPLE_KEYS


_CAID_RE = re.compile(r"\bCA\d+\b", flags=re.IGNORECASE)
_VCV_RE = re.compile(r"\bVCV0*(\d{1,12})\b", flags=re.IGNORECASE)
_CLINVAR_ID_KEYS = {
    "accession",
    "clinvar_id",
    "variation_id",
    "variationid",
    "VariationID",
    "uid",
}


def _first_caid(value: Any) -> str | None:
    for text in _iter_text(value):
        caid = _caid(text)
        if caid:
            return caid
    return None


def _caid(value: str | None) -> str | None:
    if not value:
        return None
    match = _CAID_RE.search(value)
    return match.group(0).upper() if match else None


def _vcv_from_clinvar(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if key_text in _CLINVAR_ID_KEYS:
                vcv = _vcv(child)
                if vcv:
                    return vcv
            if isinstance(child, (dict, list)):
                nested = _vcv_from_clinvar(child)
                if nested:
                    return nested
    elif isinstance(value, list):
        for child in value:
            nested = _vcv_from_clinvar(child)
            if nested:
                return nested
    return None


def _vcv(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = _VCV_RE.search(text)
    if match:
        return f"VCV{int(match.group(1)):09d}"
    if text.isdigit():
        return f"VCV{int(text):09d}"
    return None


def _hgvs_token(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    return re.sub(r"\s+", "", text)


def _iter_text(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from _iter_text(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_text(child)
    elif value is not None:
        yield str(value)


class HeroExampleSourceCacheWarmer:
    def __init__(self, lookup_service) -> None:
        self.lookup_service = lookup_service

    def warm(self, *, refresh: bool = True) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for example in HERO_EXAMPLE_VARIANTS:
            response: LookupResponse = self.lookup_service.lookup(
                LookupRequest(gene=example.gene, cdna=example.cdna),
                refresh=refresh,
            )
            results.append(
                {
                    "label": example.label,
                    "cache_key": example.cache_key,
                    "query": response.query,
                    "evidence_statuses": {item.source: item.status for item in response.evidence},
                    "warnings": list(response.warnings),
                }
            )
        return results
