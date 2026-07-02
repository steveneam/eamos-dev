from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.services.lookup_service_cache import (
    annotate_source_cached_result,
    source_cache_token,
    source_version_from_result,
)
from app.services.source_cache import (
    clingen_vcep_source_cache_key,
    is_hero_example_variant,
    source_cache_key,
)
from app.tools.base import ToolResult
from app.tools.clingen import cached_clingen_result_matches_variant

SOURCE_CACHE_PERSIST_STATUSES = {"live", "cache"}
SOURCE_CACHE_FAILURE_STATUSES = {"fallback", "degraded", "error", "failed"}
SOURCE_CACHE_GENERAL_SOURCES = {"gnomad"}


class LookupSourceCacheOrchestrator:
    def __init__(
        self,
        *,
        settings: Any,
        source_cache_repo: Any,
        tool_registry: dict[str, Any],
        report_source_result_cache_writer: Callable[..., None],
        cache_key: str,
        gene: str,
        cdna: str,
        variant: Any,
        evidence_map: dict[str, dict[str, Any]],
        evidence_raw: dict[str, Any],
        warnings: list[str],
        refresh: bool,
        species: str,
        timing: Any = None,
    ) -> None:
        self.settings = settings
        self.source_cache_repo = source_cache_repo
        self.tool_registry = tool_registry
        self.report_source_result_cache_writer = report_source_result_cache_writer
        self.cache_key = cache_key
        self.gene = gene
        self.cdna = cdna
        self.variant = variant
        self.evidence_map = evidence_map
        self.evidence_raw = evidence_raw
        self.warnings = warnings
        self.refresh = refresh
        self.species = species
        self.timing = timing
        self.source_key = source_cache_key(gene, cdna)
        self.source_cache_enabled = (
            settings is not None and settings.use_real_apis and source_cache_repo is not None
        )
        self.source_cache_hero_variant = is_hero_example_variant(gene, cdna)

    def cached_result(self, name: str, producer: Callable[[], ToolResult]) -> ToolResult:
        provider_started = self.timing.start() if self.timing is not None else 0.0
        result_for_timing: ToolResult | None = None
        outcome = "producer"
        error_type: str | None = None
        allow_stale_on_exception = False
        source_cache_lookup_key = self.source_cache_key_for(name)
        use_source_cache = source_cache_lookup_key is not None
        try:
            skip_fresh_source_cache = (
                name == "clingen"
                and self.settings is not None
                and self.settings.clingen_local_enabled
            )
            if use_source_cache and not self.refresh and not skip_fresh_source_cache:
                hit = self.source_cache_repo.get_fresh(name, source_cache_lookup_key)
                if hit is not None:
                    hit_result = hit.to_tool_result(status="cache", cache_status="cache_hit")
                    if self.source_cache_result_matches_request(name, hit_result):
                        outcome = "source_cache_fresh_hit"
                        result_for_timing = hit_result
                        return hit_result
                    self.warnings.append(f"source_cache_identity_mismatch:{name}")

            allow_stale_on_exception = True
            result = producer()
            allow_stale_on_exception = False
            result_for_timing = result
            if use_source_cache and result.status in SOURCE_CACHE_FAILURE_STATUSES:
                stale = self.source_cache_repo.get_stale(name, source_cache_lookup_key)
                if stale is not None:
                    stale_result = stale.to_tool_result(
                        status="stale",
                        cache_status="stale_on_failure",
                        extra_warnings=[
                            f"source_cache_stale_on_failure:{name}",
                            f"live_status:{result.status}",
                            *result.warnings,
                        ],
                    )
                    if self.source_cache_result_matches_request(name, stale_result):
                        outcome = "source_cache_stale_on_failure"
                        result_for_timing = stale_result
                        return stale_result
                    result.warnings.append(f"source_cache_identity_mismatch:{name}")

            if (
                use_source_cache
                and result.status != "local"
                and self.should_persist_source_cache(name, result)
            ):
                self.persist_source_cache(name, source_cache_lookup_key, result)
                outcome = "producer_persisted"
            try:
                self.report_source_result_cache_writer(
                    self.cache_key,
                    variant=self.variant,
                    result=result,
                    species=self.species,
                )
            except Exception:
                pass
            return result
        except Exception as exc:
            error_type = type(exc).__name__
            if allow_stale_on_exception and use_source_cache:
                stale = self.source_cache_repo.get_stale(name, source_cache_lookup_key)
                if stale is not None:
                    stale_result = stale.to_tool_result(
                        status="stale",
                        cache_status="stale_on_failure",
                        extra_warnings=[
                            f"source_cache_stale_on_failure:{name}",
                            f"live_fetch_failed:{type(exc).__name__}",
                        ],
                    )
                    if self.source_cache_result_matches_request(name, stale_result):
                        outcome = "source_cache_stale_on_exception"
                        result_for_timing = stale_result
                        return stale_result
                    self.warnings.append(f"source_cache_identity_mismatch:{name}")
            raise
        finally:
            if self.timing is not None:
                self.timing.record_provider(
                    name,
                    provider_started,
                    status=result_for_timing.status if result_for_timing is not None else None,
                    cache_status=(
                        result_for_timing.cache_status if result_for_timing is not None else None
                    ),
                    outcome="error" if error_type and result_for_timing is None else outcome,
                    warning_count=(
                        len(result_for_timing.warnings) if result_for_timing is not None else 0
                    ),
                    error_type=error_type,
                )

    def source_cache_key_for(self, name: str) -> str | None:
        if not self.source_cache_enabled:
            return None
        if name == "clingen":
            return clingen_vcep_source_cache_key(
                gene=self.gene,
                transcript_hgvs=self.variant.transcript_hgvs,
                cdna=self.cdna,
                genomic_hgvs=self.variant.genomic_hgvs,
                genomic_hg38=self.variant.genomic_hg38,
                clinvar_summary=self.evidence_map.get("clinvar"),
                clinvar_raw=self.evidence_raw.get("clinvar"),
            )
        if self.source_cache_hero_variant:
            return self.source_key
        if name not in SOURCE_CACHE_GENERAL_SOURCES:
            return None
        variant_id = source_cache_token(self.variant.genomic_hg38)
        if not variant_id:
            return None
        dataset = str(getattr(self.tool_registry.get("gnomad"), "DATASET", "gnomad_r4"))
        return f"gnomad:{dataset}:{variant_id}"

    def should_persist_source_cache(self, name: str, result: ToolResult) -> bool:
        if result.status not in SOURCE_CACHE_PERSIST_STATUSES:
            return False
        if (
            not self.source_cache_hero_variant
            and name == "gnomad"
            and "gnomad_variant_not_found" in result.warnings
        ):
            return False
        if name == "clingen" and (
            "clingen_variant_not_found" in result.warnings
            or not (result.summary or {}).get("expert_panel")
        ):
            return False
        return True

    def source_cache_result_matches_request(self, name: str, result: ToolResult) -> bool:
        if name != "clingen":
            return True
        return cached_clingen_result_matches_variant(result, self.variant)

    def persist_source_cache(
        self,
        name: str,
        source_cache_lookup_key: str,
        result: ToolResult,
    ) -> None:
        annotate_source_cached_result(name, result, cache_key=source_cache_lookup_key)
        self.source_cache_repo.upsert(
            result.source,
            source_cache_lookup_key,
            normalized_identity={
                "query": source_cache_lookup_key,
                "gene": self.gene,
                "cdna": self.cdna,
                "genomic_hg38": self.variant.genomic_hg38,
                "genomic_hgvs": self.variant.genomic_hgvs,
            },
            request_identity=result.request_identity,
            status=result.status,
            summary=result.summary,
            raw=result.raw,
            warnings=result.warnings,
            source_url=result.source_url,
            ttl_days=self.settings.cache_ttl_days,
            source_version=source_version_from_result(result),
        )
