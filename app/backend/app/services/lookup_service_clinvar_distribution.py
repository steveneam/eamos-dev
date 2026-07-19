from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
import sqlite3
from typing import Any

from app.schemas.workflow import CanonicalVariantRefV1, CuratedVariantPageV1
from app.schemas.workbench import SourceDisclosure
from app.schemas.run import CuratedVariantsDistribution
from app.services.clinvar_local import (
    ClinVarLocalError,
    ClinVarLocalStore,
    build_clinvar_gene_distribution,
    build_clinvar_gene_distribution_from_index,
    inspect_clinvar_gene_distribution_index,
)
from app.services.compact_coordinate_index import compact_coordinate_index_from_settings
from app.services.local_evidence_orchestrator import LocalEvidenceRuntimeGate

CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX = (
    "clinvar_gene_distribution_excluded_pending_index"
)


@lru_cache(maxsize=4)
def clinvar_distribution_store(vcf_path: str | None) -> ClinVarLocalStore:
    return ClinVarLocalStore(Path(vcf_path)) if vcf_path else ClinVarLocalStore()


def clinvar_gene_distribution_exclusion_warning(settings: Any) -> str | None:
    if LocalEvidenceRuntimeGate.from_settings(settings).allows(
        "lookup"
    ) and not clinvar_distribution_runtime_path(settings):
        return CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX
    return None


def clinvar_distribution_runtime_path(settings: Any) -> str | None:
    if not LocalEvidenceRuntimeGate.from_settings(settings).allows("lookup"):
        return None
    try:
        inspection = inspect_clinvar_gene_distribution_index(
            settings,
            verify_checksum=False,
        )
    except Exception:
        return None
    if not inspection.ready:
        return None
    raw_path = Path(getattr(settings, "clinvar_gene_distribution_index_path"))
    resolved = (
        raw_path if raw_path.is_absolute() else Path(getattr(settings, "backend_root")) / raw_path
    )
    return str(resolved)


def local_clinvar_gene_distribution(
    gene: str,
    settings: Any,
    *,
    variant_id: str | None = None,
) -> CuratedVariantsDistribution:
    index_path = clinvar_distribution_runtime_path(settings)
    if index_path:
        return build_clinvar_gene_distribution_from_index(
            gene,
            index_path=Path(index_path),
            query_variant_id=variant_id,
        )
    if LocalEvidenceRuntimeGate.from_settings(settings).allows("lookup"):
        raise ClinVarLocalError(
            "gene_distribution_index_not_ready",
            "ClinVar gene-distribution index is not ready",
        )
    store = clinvar_distribution_store(None)
    return build_clinvar_gene_distribution(gene, store=store, query_variant_id=variant_id)


def local_clinvar_curated_variant_page(
    gene: str,
    settings: Any,
    *,
    classification: str | None,
    consequence: str | None,
    limit: int,
    cursor: str | None,
) -> CuratedVariantPageV1:
    gene_symbol = gene.strip().upper()
    bounded_limit = max(1, min(100, int(limit)))
    after_variant_id = _decode_curated_cursor(cursor) if cursor else None
    index_path = clinvar_distribution_runtime_path(settings)
    if index_path:
        return _indexed_curated_variant_page(
            gene_symbol,
            settings,
            index_path=Path(index_path),
            classification=classification,
            consequence=consequence,
            limit=bounded_limit,
            after_variant_id=after_variant_id,
        )
    if LocalEvidenceRuntimeGate.from_settings(settings).allows("lookup"):
        return CuratedVariantPageV1(
            gene=gene_symbol,
            classification_filter=classification,
            consequence_filter=consequence,
            items=[],
            next_cursor=None,
            total=0,
            source_disclosure=SourceDisclosure(
                source_status="unavailable",
                provider_id="eamos_clinvar_distribution",
                provider_label="Eamos ClinVar distribution index",
                warnings=["clinvar_gene_distribution_index_not_ready"],
                requirements=["Materialize and verify the local ClinVar distribution index."],
            ),
            warnings=["curated_variant_identity_index_unavailable"],
        )
    return _fixture_curated_variant_page(
        gene_symbol,
        classification=classification,
        consequence=consequence,
        limit=bounded_limit,
        after_variant_id=after_variant_id,
    )


def _fixture_curated_variant_page(
    gene: str,
    *,
    classification: str | None,
    consequence: str | None,
    limit: int,
    after_variant_id: str | None,
) -> CuratedVariantPageV1:
    store = clinvar_distribution_store(None)
    matching = [
        record
        for record in store.records()
        if gene in record.gene_symbols
        and _classification_matches(record.classification, classification)
        and _fixture_consequence(record) == (consequence or _fixture_consequence(record))
    ]
    matching.sort(key=lambda record: record.gnomad_variant_id)
    total = len(matching)
    if after_variant_id:
        matching = [record for record in matching if record.gnomad_variant_id > after_variant_id]
    selected = matching[: limit + 1]
    has_more = len(selected) > limit
    selected = selected[:limit]
    items: list[CanonicalVariantRefV1] = []
    warnings = ["clinvar_local_fixture_scope"]
    for record in selected:
        canonical = _fixture_record_to_canonical(record, gene=gene)
        if canonical is None:
            warnings.append("curated_variant_missing_transcript_hgvs")
            continue
        items.append(canonical)
    next_cursor = (
        _encode_curated_cursor(selected[-1].gnomad_variant_id)
        if has_more and selected
        else None
    )
    provenance = store.provenance()
    return CuratedVariantPageV1(
        gene=gene,
        classification_filter=classification,
        consequence_filter=consequence,
        items=items,
        next_cursor=next_cursor,
        total=total,
        source_disclosure=SourceDisclosure(
            source_status="fixture",
            provider_id="ncbi_clinvar_fixture",
            provider_label="Bundled ClinVar test fixture",
            source_version=provenance.source_version,
            cache_status="bundled_fixture",
            warnings=["clinvar_local_fixture_scope"],
            requirements=["Use a verified local ClinVar index for release data."],
        ),
        warnings=list(dict.fromkeys(warnings)),
    )


def _indexed_curated_variant_page(
    gene: str,
    settings: Any,
    *,
    index_path: Path,
    classification: str | None,
    consequence: str | None,
    limit: int,
    after_variant_id: str | None,
) -> CuratedVariantPageV1:
    base_clauses = ["gene = ?"]
    params: list[Any] = [gene]
    if consequence:
        base_clauses.append("cell like ?")
        params.append(f"%_{consequence}")
    classification_clause, classification_params = _classification_sql(classification)
    if classification_clause:
        base_clauses.append(classification_clause)
        params.extend(classification_params)
    clauses = list(base_clauses)
    if after_variant_id:
        clauses.append("variant_id > ?")
        params.append(after_variant_id)
    where = " and ".join(clauses)
    base_where = " and ".join(base_clauses)
    fetch_limit = max(limit * 5, limit + 1)
    try:
        with sqlite3.connect(index_path) as connection:
            all_rows = connection.execute(
                f"select variant_id, accession, classification, cell "
                f"from clinvar_gene_distribution_variant where {where} "
                "order by variant_id asc limit ?",
                (*params, fetch_limit + 1),
            ).fetchall()
            total = int(
                connection.execute(
                    "select count(*) from clinvar_gene_distribution_variant "
                    f"where {base_where}",
                    tuple(params[: len(params) - (1 if after_variant_id else 0)]),
                ).fetchone()[0]
            )
    except sqlite3.Error:
        return CuratedVariantPageV1(
            gene=gene,
            classification_filter=classification,
            consequence_filter=consequence,
            items=[],
            next_cursor=None,
            total=0,
            source_disclosure=SourceDisclosure(
                source_status="unavailable",
                provider_id="eamos_clinvar_distribution",
                provider_label="Eamos ClinVar distribution index",
                warnings=["clinvar_gene_distribution_index_read_failed"],
                requirements=["Repair or rematerialize the verified index."],
            ),
            warnings=["curated_variant_identity_index_unavailable"],
        )
    has_more_source = len(all_rows) > fetch_limit
    rows = all_rows[:fetch_limit]
    coordinate_index = compact_coordinate_index_from_settings(settings)
    items: list[CanonicalVariantRefV1] = []
    unresolved = 0
    consumed_variant_id: str | None = None
    consumed_index = -1
    for consumed_index, (variant_id, accession, _raw_classification, _cell) in enumerate(rows):
        consumed_variant_id = str(variant_id)
        resolved = coordinate_index.resolve_variant(
            gene=gene,
            cdna="",
            accession=str(accession) if accession else None,
        )
        if resolved is None:
            unresolved += 1
            continue
        items.append(
            CanonicalVariantRefV1(
                schema_version="canonical_variant_ref.v1",
                gene=gene,
                cdna=resolved.cdna,
                transcript=resolved.transcript,
                protein_hgvs=resolved.protein_change,
                genomic_hg38=resolved.genomic_hg38,
                variant_key=resolved.genomic_hg38,
                species="human",
                genome_build="GRCh38",
                resolution_status="resolved",
                source_support=list(
                    dict.fromkeys(["ncbi_clinvar", resolved.source, *resolved.provenance])
                ),
                warnings=list(resolved.warnings),
            )
        )
        if len(items) >= limit:
            break
    inspection = inspect_clinvar_gene_distribution_index(
        settings,
        verify_checksum=False,
    )
    next_cursor = None
    if consumed_variant_id and (has_more_source or consumed_index < len(rows) - 1):
        next_cursor = _encode_curated_cursor(consumed_variant_id)
    warnings = []
    if unresolved:
        warnings.append(f"curated_variants_without_canonical_identity:{unresolved}")
    return CuratedVariantPageV1(
        gene=gene,
        classification_filter=classification,
        consequence_filter=consequence,
        items=items,
        next_cursor=next_cursor,
        total=total,
        source_disclosure=SourceDisclosure(
            source_status="source_backed",
            provider_id="eamos_clinvar_distribution",
            provider_label="Eamos local ClinVar distribution index",
            source_version=inspection.source_version,
            cache_status="local_verified_index" if inspection.ready else None,
            warnings=list(inspection.warnings),
            requirements=[],
        ),
        warnings=warnings,
    )


def _fixture_record_to_canonical(record, *, gene: str) -> CanonicalVariantRefV1 | None:
    transcript: str | None = None
    cdna: str | None = None
    protein: str | None = None
    for alias in record.hgvs_aliases:
        prefix, separator, value = alias.partition(":")
        normalized = value if separator else alias
        if normalized.startswith("c.") and cdna is None:
            transcript = prefix if separator else None
            cdna = normalized
        elif normalized.startswith("p.") and protein is None:
            protein = normalized
    if cdna is None:
        return None
    return CanonicalVariantRefV1(
        schema_version="canonical_variant_ref.v1",
        gene=gene,
        cdna=cdna,
        transcript=transcript,
        protein_hgvs=protein,
        genomic_hg38=record.gnomad_variant_id,
        variant_key=record.gnomad_variant_id,
        species="human",
        genome_build="GRCh38",
        resolution_status="resolved",
        source_support=["ncbi_clinvar_fixture"],
        warnings=["clinvar_local_fixture_scope"],
    )


def _classification_matches(raw: str, requested: str | None) -> bool:
    if requested is None:
        return True
    normalized = raw.lower().replace(" ", "_")
    if requested == "likely_pathogenic":
        return "likely_pathogenic" in normalized
    if requested == "pathogenic":
        return "pathogenic" in normalized and "likely_pathogenic" not in normalized
    if requested == "likely_benign":
        return "likely_benign" in normalized
    if requested == "benign":
        return "benign" in normalized and "likely_benign" not in normalized
    return "uncertain" in normalized or "conflict" in normalized or "vus" in normalized


def _classification_sql(requested: str | None) -> tuple[str | None, list[str]]:
    if requested is None:
        return None, []
    normalized = "lower(replace(replace(classification, ' ', '_'), '-', '_'))"
    if requested == "likely_pathogenic":
        return f"{normalized} like ?", ["%likely_pathogenic%"]
    if requested == "pathogenic":
        return (
            f"{normalized} like ? and {normalized} not like ?",
            ["%pathogenic%", "%likely_pathogenic%"],
        )
    if requested == "likely_benign":
        return f"{normalized} like ?", ["%likely_benign%"]
    if requested == "benign":
        return (
            f"{normalized} like ? and {normalized} not like ?",
            ["%benign%", "%likely_benign%"],
        )
    return (
        f"({normalized} like ? or {normalized} like ? or {normalized} like ?)",
        ["%uncertain%", "%conflict%", "%vus%"],
    )


def _fixture_consequence(record) -> str:
    protein_aliases = [
        alias.lower()
        for alias in record.hgvs_aliases
        if ":p." in alias.lower() or alias.lower().startswith("p.")
    ]
    if any("p.=" in alias or "synonymous" in alias for alias in protein_aliases):
        return "synonymous"
    if any(
        token in alias
        for alias in protein_aliases
        for token in ("ter", "*", "fs", "frameshift", "splice")
    ):
        return "lof"
    if protein_aliases or len(record.ref) != len(record.alt):
        return "missense"
    return "noncoding"


def _encode_curated_cursor(variant_id: str) -> str:
    return base64.urlsafe_b64encode(variant_id.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_curated_cursor(cursor: str) -> str:
    try:
        padding = "=" * (-len(cursor) % 4)
        value = base64.b64decode(cursor + padding, altchars=b"-_", validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid curated variant cursor.") from exc
    if not value or len(value) > 256 or any(char.isspace() for char in value):
        raise ValueError("Invalid curated variant cursor.")
    return value
