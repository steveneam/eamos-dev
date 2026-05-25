from __future__ import annotations

from dataclasses import dataclass
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


HERO_EXAMPLE_VARIANTS: tuple[HeroExampleVariant, ...] = (
    HeroExampleVariant(label="RPE65 c.260A>G", gene="RPE65", cdna="c.260A>G"),
    HeroExampleVariant(label="RPE65 c.11+5G>A", gene="RPE65", cdna="c.11+5G>A"),
    HeroExampleVariant(label="USH2A c.2276G>T", gene="USH2A", cdna="c.2276G>T"),
    HeroExampleVariant(label="BRCA1 c.5266dupC", gene="BRCA1", cdna="c.5266dupC"),
)

_HERO_EXAMPLE_KEYS = {item.cache_key for item in HERO_EXAMPLE_VARIANTS}


def is_hero_example_variant(gene: str, cdna: str) -> bool:
    return source_cache_key(gene, cdna) in _HERO_EXAMPLE_KEYS


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
