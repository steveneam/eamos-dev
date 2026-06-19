from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from app.tools.base import FixtureBackedTool, ToolResult


def _unavailable_summary(gene: str | None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "gene": gene or "",
        "approved_symbol": gene or "",
        "hgnc_id": None,
        "primary_condition": None,
        "disease_ids": [],
        "inheritance": None,
        "penetrance": None,
        "gene_disease_validity": None,
        "mechanism": None,
        "conditions": [],
        "source_counts": {},
        "gencc_assertion_count": 0,
        "gencc_submitters": [],
        "gencc_assertions": [],
        "provenance": [],
        "warnings": list(warnings or []),
    }


class ClinicalGeneDiseaseStore(Protocol):
    def get_gene_disease_summary(self, *, gene: str) -> dict[str, Any] | None: ...


class GeneDiseaseTool(FixtureBackedTool):
    source = "gene_disease"
    fixture_name = "gene_disease_fixtures.json"

    def __init__(
        self,
        settings,
        *,
        clinical_source_store: ClinicalGeneDiseaseStore | None = None,
    ) -> None:
        super().__init__(settings)
        self.clinical_source_store = clinical_source_store

    def get_evidence(self, variant=None) -> ToolResult:
        gene = str(getattr(variant, "gene", "") if variant is not None else "").strip().upper()
        if not gene:
            return ToolResult(
                source=self.source,
                status="missing",
                request_identity={},
                summary=_unavailable_summary(None, ["gene_disease_requires_gene"]),
                raw=None,
            )

        request_identity = {"gene": gene}
        fixture_record = _fixture_record(self.load_fixture(), gene)
        if not self.settings.use_real_apis:
            return _result_from_record(
                status="fixture" if fixture_record else "missing",
                request_identity=request_identity,
                record=fixture_record,
                gene=gene,
                missing_warning="gene_disease_not_found",
            )

        warnings: list[str] = []
        if self.clinical_source_store is not None:
            try:
                source_summary = self.clinical_source_store.get_gene_disease_summary(gene=gene)
            except Exception as exc:
                warnings.append(f"gene_disease_source_table_failed:{type(exc).__name__}")
            else:
                if source_summary is not None:
                    return _result_from_source_table_summary(
                        request_identity=request_identity,
                        summary=source_summary,
                        gene=gene,
                        extra_warnings=warnings,
                    )

        record = deepcopy(fixture_record) if fixture_record else {"gene": gene, "conditions": []}
        try:
            hgnc_record = self._fetch_hgnc(gene)
            if hgnc_record:
                _merge_hgnc_record(record, hgnc_record)
                _add_live_hgnc_provenance(record, gene)
        except Exception as exc:
            warnings.append(f"gene_disease_hgnc_fetch_failed:{type(exc).__name__}")

        if not fixture_record and not record.get("hgnc_id"):
            return _result_from_record(
                status="fallback",
                request_identity=request_identity,
                record=None,
                gene=gene,
                missing_warning="gene_disease_not_found",
                extra_warnings=warnings,
            )

        if fixture_record:
            warnings.append("gene_disease_curated_fixture_snapshot")
        return _result_from_record(
            status="fallback" if fixture_record else "live",
            request_identity=request_identity,
            record=record,
            gene=gene,
            extra_warnings=warnings,
        )

    def _fetch_hgnc(self, gene: str) -> dict[str, Any] | None:
        response = httpx.get(
            f"{self.settings.hgnc_rest_base_url.rstrip('/')}/fetch/symbol/{quote(gene)}",
            headers={"Accept": "application/json"},
            timeout=8.0,
        )
        response.raise_for_status()
        payload = response.json()
        docs = payload.get("response", {}).get("docs", []) if isinstance(payload, dict) else []
        if not isinstance(docs, list) or not docs:
            return None
        first = docs[0]
        return first if isinstance(first, dict) else None


def _result_from_source_table_summary(
    *,
    request_identity: dict[str, Any],
    summary: dict[str, Any],
    gene: str,
    extra_warnings: list[str] | None = None,
) -> ToolResult:
    normalized = _unavailable_summary(gene)
    normalized.update(summary)
    normalized["warnings"] = _dedupe(
        [*_string_list(summary.get("warnings")), *list(extra_warnings or [])]
    )
    return ToolResult(
        source=GeneDiseaseTool.source,
        status="source_table",
        request_identity=request_identity,
        summary=normalized,
        warnings=list(extra_warnings or []),
        raw=summary,
        source_url=_primary_source_url(normalized) or _gene_search_url(gene),
    )


def _fixture_record(fixture: dict[str, Any], gene: str) -> dict[str, Any] | None:
    genes = fixture.get("genes")
    if not isinstance(genes, dict):
        return None
    record = genes.get(gene)
    return deepcopy(record) if isinstance(record, dict) else None


def _result_from_record(
    *,
    status: str,
    request_identity: dict[str, Any],
    record: dict[str, Any] | None,
    gene: str,
    missing_warning: str | None = None,
    extra_warnings: list[str] | None = None,
) -> ToolResult:
    warnings = list(extra_warnings or [])
    if record is None:
        if missing_warning:
            warnings.append(missing_warning)
        return ToolResult(
            source=GeneDiseaseTool.source,
            status=status,
            request_identity=request_identity,
            summary=_unavailable_summary(gene, warnings),
            warnings=warnings,
            raw=None,
            source_url=_gene_search_url(gene),
        )

    summary = _summary_from_record(record, gene)
    summary["warnings"] = _dedupe([*summary.get("warnings", []), *warnings])
    return ToolResult(
        source=GeneDiseaseTool.source,
        status=status,
        request_identity=request_identity,
        summary=summary,
        warnings=warnings,
        raw=record,
        source_url=_primary_source_url(summary) or _gene_search_url(gene),
    )


def _summary_from_record(record: dict[str, Any], gene: str) -> dict[str, Any]:
    conditions = _conditions(record)
    primary = conditions[0] if conditions else {}
    primary_condition = _text(record.get("primary_condition")) or _text(primary.get("name"))
    disease_ids = _dedupe(
        [
            *_string_list(record.get("disease_ids")),
            *_string_list(primary.get("disease_ids")),
        ]
    )
    inheritance = _text(record.get("inheritance")) or _text(primary.get("inheritance"))
    validity = _text(record.get("gene_disease_validity")) or _text(primary.get("validity"))
    mechanism = _text(record.get("mechanism")) or _text(primary.get("mechanism"))
    penetrance = _text(record.get("penetrance"))
    warnings = _string_list(record.get("warnings"))
    if penetrance is None and "penetrance_not_source_backed" not in warnings:
        warnings.append("penetrance_not_source_backed")

    return {
        "gene": _text(record.get("gene")) or gene,
        "approved_symbol": _text(record.get("approved_symbol")) or gene,
        "hgnc_id": _text(record.get("hgnc_id")),
        "gene_name": _text(record.get("gene_name")),
        "primary_condition": primary_condition,
        "disease_ids": disease_ids,
        "inheritance": inheritance,
        "penetrance": penetrance,
        "gene_disease_validity": validity,
        "mechanism": mechanism,
        "conditions": conditions,
        "provenance": _provenance(record),
        "warnings": warnings,
    }


def _merge_hgnc_record(record: dict[str, Any], hgnc_record: dict[str, Any]) -> None:
    record["approved_symbol"] = _text(hgnc_record.get("symbol")) or record.get("approved_symbol")
    record["hgnc_id"] = _text(hgnc_record.get("hgnc_id")) or record.get("hgnc_id")
    record["gene_name"] = _text(hgnc_record.get("name")) or record.get("gene_name")
    aliases = _string_list(hgnc_record.get("alias_symbol"))
    if aliases:
        record["aliases"] = _dedupe([*_string_list(record.get("aliases")), *aliases])
    omim_ids = _string_list(hgnc_record.get("omim_id"))
    if omim_ids:
        record["gene_ids"] = _dedupe(
            [*_string_list(record.get("gene_ids")), *[f"OMIM:{item}" for item in omim_ids]]
        )


def _add_live_hgnc_provenance(record: dict[str, Any], gene: str) -> None:
    provenance = _provenance(record)
    provenance = [
        item
        for item in provenance
        if not (item.get("source") == "HGNC" and item.get("status") == "fixture")
    ]
    provenance.insert(
        0,
        {
            "source": "HGNC",
            "status": "live",
            "query": {"symbol": gene},
            "source_url": _hgnc_source_url(record),
            "version": "HGNC REST",
            "warnings": [],
        },
    )
    record["provenance"] = provenance


def _conditions(record: dict[str, Any]) -> list[dict[str, Any]]:
    conditions = record.get("conditions")
    if not isinstance(conditions, list):
        return []
    result: list[dict[str, Any]] = []
    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        result.append(
            {
                "name": _text(condition.get("name")) or "",
                "disease_ids": _string_list(condition.get("disease_ids")),
                "inheritance": _text(condition.get("inheritance")),
                "validity": _text(condition.get("validity")),
                "mechanism": _text(condition.get("mechanism")),
                "source_urls": _string_list(condition.get("source_urls")),
            }
        )
    return result


def _provenance(record: dict[str, Any]) -> list[dict[str, Any]]:
    provenance = record.get("provenance")
    if not isinstance(provenance, list):
        return []
    return [item for item in provenance if isinstance(item, dict)]


def _primary_source_url(summary: dict[str, Any]) -> str | None:
    for item in summary.get("provenance", []):
        if isinstance(item, dict):
            source_url = _text(item.get("source_url"))
            if source_url:
                return source_url
    return None


def _gene_search_url(gene: str) -> str:
    return f"https://www.ncbi.nlm.nih.gov/medgen/?term={quote(gene)}"


def _hgnc_source_url(record: dict[str, Any]) -> str | None:
    hgnc_id = _text(record.get("hgnc_id"))
    if not hgnc_id:
        return None
    return f"https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/{quote(hgnc_id)}"


def _dedupe(items: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [text for text in (_text(item) for item in value) if text]
    text = _text(value)
    return [text] if text else []


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("description", "label", "name", "value"):
            text = _text(value.get(key))
            if text:
                return text
        return None
    text = str(value).strip()
    return text or None
