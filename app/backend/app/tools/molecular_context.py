from __future__ import annotations

from copy import deepcopy
from typing import Any
from urllib.parse import quote

from app.tools.base import FixtureBackedTool, ToolResult


def _unavailable_summary(gene: str | None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "gene": gene or "",
        "gnomad_constraint": None,
        "clingen_dosage": None,
        "overlapping_cnvs": [],
        "provenance": [],
        "warnings": list(warnings or []),
    }


class MolecularContextTool(FixtureBackedTool):
    source = "molecular_context"
    fixture_name = "molecular_context_fixtures.json"

    def get_evidence(self, variant=None) -> ToolResult:
        gene = str(getattr(variant, "gene", "") if variant is not None else "").strip().upper()
        if not gene:
            return ToolResult(
                source=self.source,
                status="missing",
                request_identity={},
                summary=_unavailable_summary(None, ["molecular_context_requires_gene"]),
                raw=None,
            )

        request_identity = {
            "gene": gene,
            "variant_id": str(getattr(variant, "genomic_hg38", "") or ""),
            "transcript_hgvs": str(getattr(variant, "transcript_hgvs", "") or ""),
        }
        record = _fixture_record(self.load_fixture(), gene)
        if not self.settings.use_real_apis:
            return _result_from_record(
                status="fixture" if record else "missing",
                request_identity=request_identity,
                record=record,
                gene=gene,
                missing_warning="molecular_context_not_found",
            )

        if record is None:
            return _result_from_record(
                status="missing",
                request_identity=request_identity,
                record=None,
                gene=gene,
                missing_warning="molecular_context_not_found",
            )

        return _result_from_record(
            status="fallback",
            request_identity=request_identity,
            record=record,
            gene=gene,
            extra_warnings=["molecular_context_curated_fixture_snapshot"],
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
            source=MolecularContextTool.source,
            status=status,
            request_identity=request_identity,
            summary=_unavailable_summary(gene, warnings),
            warnings=warnings,
            raw=None,
            source_url=_gnomad_gene_url(gene),
        )

    summary = _summary_from_record(record, gene)
    summary["warnings"] = _dedupe([*summary.get("warnings", []), *warnings])
    return ToolResult(
        source=MolecularContextTool.source,
        status=status,
        request_identity=request_identity,
        summary=summary,
        warnings=warnings,
        raw=record,
        source_url=_primary_source_url(summary) or _gnomad_gene_url(gene),
    )


def _summary_from_record(record: dict[str, Any], gene: str) -> dict[str, Any]:
    return {
        "gene": _text(record.get("gene")) or gene,
        "gnomad_constraint": _dict_or_none(record.get("gnomad_constraint")),
        "clingen_dosage": _dict_or_none(record.get("clingen_dosage")),
        "overlapping_cnvs": _string_list(record.get("overlapping_cnvs")),
        "provenance": _provenance(record),
        "warnings": _string_list(record.get("warnings")),
    }


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _provenance(record: dict[str, Any]) -> list[dict[str, Any]]:
    provenance = record.get("provenance")
    if not isinstance(provenance, list):
        return []
    return [item for item in provenance if isinstance(item, dict)]


def _primary_source_url(summary: dict[str, Any]) -> str | None:
    for item in summary.get("provenance", []):
        if not isinstance(item, dict):
            continue
        source_url = _text(item.get("source_url"))
        if source_url:
            return source_url
    return None


def _gnomad_gene_url(gene: str) -> str:
    return f"https://gnomad.broadinstitute.org/gene/{quote(gene)}?dataset=gnomad_r4"


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
