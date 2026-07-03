from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from urllib.parse import quote

from app.schemas.search import SearchDocumentWrite, SearchVariantWrite
from app.services.source_imports import ClinicalSourceImportBundle

CONDITION_DOC_TYPE = "condition"
GENE_DISEASE_DOC_TYPE = "gene_disease"
CLINICAL_SOURCE_STATUS = "tracked_clinical_source_asset"


def build_clinical_source_search_documents(
    bundle: ClinicalSourceImportBundle,
) -> list[SearchDocumentWrite]:
    return _dedupe_documents(
        [
            *_build_condition_documents(bundle),
            *_build_gene_disease_documents(bundle),
        ]
    )


def _build_condition_documents(bundle: ClinicalSourceImportBundle) -> list[SearchDocumentWrite]:
    source_versions = _source_versions(bundle)
    by_condition: dict[str, dict[str, object]] = {}
    mondo_by_xref: dict[str, str] = {}

    for row in bundle.mondo_rows:
        disease_id = _text(row.get("mondo_id"))
        name = _text(row.get("name"))
        if not disease_id or not name:
            continue
        entry = _condition_entry(by_condition, disease_id, name)
        _add(entry, "ids", disease_id)
        _add_many(entry, "xrefs", _text_list(row.get("xrefs")))
        _add(entry, "definitions", _text(row.get("definition")))
        _add(entry, "sources", _source_label(row.get("provenance"), default="MONDO"))
        for xref in _text_list(row.get("xrefs")):
            mondo_by_xref[xref.upper()] = disease_id

    for row in bundle.hpo_disease_rows:
        raw_disease_id = _text(row.get("disease_id"))
        disease_id = _mapped_condition_id(raw_disease_id, mondo_by_xref)
        name = _text(row.get("disease_name"))
        if not disease_id or not name:
            continue
        entry = _condition_entry(by_condition, disease_id, name)
        if raw_disease_id:
            _add(entry, "ids", raw_disease_id)
        _add(entry, "phenotypes", _text(row.get("hpo_label")))
        _add(entry, "hpo_ids", _text(row.get("hpo_id")))
        _add(entry, "sources", _source_label(row.get("provenance"), default="HPO"))

    for row in bundle.clingen_rows:
        disease_id = _text(row.get("disease_id"))
        name = _text(row.get("disease_label"))
        if not disease_id or not name:
            continue
        entry = _condition_entry(by_condition, disease_id, name)
        _add(entry, "genes", _text(row.get("gene_symbol")))
        _add(entry, "gene_validity", _text(row.get("classification")))
        _add(entry, "inheritance", _text(row.get("mode_of_inheritance")))
        _add(entry, "sources", _source_label(row.get("provenance"), default="ClinGen"))

    for row in bundle.gencc_rows:
        disease_id = _text(row.get("disease_curie"))
        name = _text(row.get("disease_title"))
        if not disease_id or not name:
            continue
        entry = _condition_entry(by_condition, disease_id, name)
        _add(entry, "genes", _text(row.get("gene_symbol")))
        _add(entry, "gencc_assertions", _text(row.get("assertion")))
        _add(entry, "sources", _source_label(row.get("provenance"), default="GenCC"))

    documents: list[SearchDocumentWrite] = []
    for disease_id, entry in sorted(by_condition.items()):
        name = _first(entry, "names") or disease_id
        ids = _sorted_values(entry, "ids")
        xrefs = _sorted_values(entry, "xrefs")
        phenotypes = _sorted_values(entry, "phenotypes")
        genes = _sorted_values(entry, "genes")
        validity = _sorted_values(entry, "gene_validity")
        gencc_assertions = _sorted_values(entry, "gencc_assertions")
        sources = _sorted_values(entry, "sources")
        source_ids = _source_ids_from_sources(sources)
        summary_text = _join_text(
            [
                name,
                _first(entry, "definitions"),
                f"{len(phenotypes)} HPO phenotype(s)" if phenotypes else None,
                f"{len(genes)} gene relationship(s)" if genes else None,
            ]
        )
        evidence_text = _join_text(
            [
                *ids,
                *xrefs,
                *phenotypes[:12],
                *genes[:20],
                *validity,
                *gencc_assertions,
                *sources,
            ]
        )
        identifier_text = _join_text([disease_id, name, *ids, *xrefs])
        target_href = f"/report?q={quote(name)}"
        documents.append(
            SearchDocumentWrite(
                source_key=f"{CONDITION_DOC_TYPE}:{_stable_token(disease_id or name)}",
                doc_type=CONDITION_DOC_TYPE,
                visibility_scope="public",
                report_title=name,
                summary_text=summary_text,
                evidence_text=evidence_text,
                identifier_text=identifier_text,
                search_text=_join_text([identifier_text, summary_text, evidence_text]),
                metadata={
                    "condition_id": disease_id,
                    "disease_id": disease_id,
                    "mondo_id": disease_id if disease_id.startswith("MONDO:") else None,
                    "source_ids": ",".join(source_ids),
                    "source_versions": _source_version_summary(source_versions, source_ids),
                    "hpo_phenotype_count": len(phenotypes),
                    "gene_count": len(genes),
                    "gene_validity_count": len(validity),
                    "gencc_assertion_count": len(gencc_assertions),
                    "source_status": CLINICAL_SOURCE_STATUS,
                    "target_href": target_href,
                },
            )
        )
    return documents


def _build_gene_disease_documents(
    bundle: ClinicalSourceImportBundle,
) -> list[SearchDocumentWrite]:
    source_versions = _source_versions(bundle)
    by_relationship: dict[tuple[str, str], dict[str, object]] = {}

    for row in bundle.clingen_rows:
        gene = _text(row.get("gene_symbol"))
        disease_id = _text(row.get("disease_id"))
        disease_name = _text(row.get("disease_label"))
        if not gene or not disease_id or not disease_name:
            continue
        entry = _gene_disease_entry(by_relationship, gene, disease_id, disease_name)
        _add(entry, "hgnc_ids", _text(row.get("gene_hgnc_id")))
        _add(entry, "clingen_classifications", _text(row.get("classification")))
        _add(entry, "inheritance", _text(row.get("mode_of_inheritance")))
        _add(entry, "source_dates", _text(row.get("source_date")))
        _add(entry, "report_urls", _text(row.get("report_url")))
        _add(entry, "sources", _source_label(row.get("provenance"), default="ClinGen"))

    for row in bundle.gencc_rows:
        gene = _text(row.get("gene_symbol"))
        disease_id = _text(row.get("disease_curie"))
        disease_name = _text(row.get("disease_title"))
        if not gene or not disease_id or not disease_name:
            continue
        entry = _gene_disease_entry(by_relationship, gene, disease_id, disease_name)
        _add(entry, "hgnc_ids", _text(row.get("gene_curie")))
        _add(entry, "gencc_assertions", _text(row.get("assertion")))
        _add(entry, "submitters", _text(row.get("submitter")))
        _add(entry, "source_dates", _text(row.get("source_date")))
        _add(entry, "report_urls", _text(row.get("report_url")))
        _add(entry, "sources", _source_label(row.get("provenance"), default="GenCC"))

    documents: list[SearchDocumentWrite] = []
    for (gene, disease_id), entry in sorted(by_relationship.items()):
        disease_name = _first(entry, "disease_names") or disease_id
        clingen = _sorted_values(entry, "clingen_classifications")
        gencc = _sorted_values(entry, "gencc_assertions")
        inheritance = _sorted_values(entry, "inheritance")
        hgnc_ids = _sorted_values(entry, "hgnc_ids")
        submitters = _sorted_values(entry, "submitters")
        source_dates = _sorted_values(entry, "source_dates")
        report_urls = _sorted_values(entry, "report_urls")
        sources = _sorted_values(entry, "sources")
        source_ids = _source_ids_from_sources(sources)
        title = f"{gene} - {disease_name}"
        summary_text = _join_text(
            [
                title,
                f"ClinGen: {', '.join(clingen)}" if clingen else None,
                f"GenCC: {', '.join(gencc)}" if gencc else None,
                f"Inheritance: {', '.join(inheritance)}" if inheritance else None,
            ]
        )
        evidence_text = _join_text([*hgnc_ids, *source_dates, *report_urls, *sources])
        identifier_text = _join_text([gene, disease_id, disease_name, *hgnc_ids])
        target_href = f"/report?q={quote(f'{gene} {disease_name}')}"
        documents.append(
            SearchDocumentWrite(
                source_key=(f"{GENE_DISEASE_DOC_TYPE}:" f"{_stable_token(f'{gene}:{disease_id}')}"),
                doc_type=GENE_DISEASE_DOC_TYPE,
                visibility_scope="public",
                report_title=title,
                summary_text=summary_text,
                evidence_text=evidence_text,
                identifier_text=identifier_text,
                search_text=_join_text([identifier_text, summary_text, evidence_text]),
                metadata={
                    "gene": gene,
                    "disease_id": disease_id,
                    "disease_name": disease_name,
                    "source_ids": ",".join(source_ids),
                    "source_versions": _source_version_summary(source_versions, source_ids),
                    "clingen_classification": ", ".join(clingen) if clingen else None,
                    "gencc_assertions": ", ".join(gencc) if gencc else None,
                    "gencc_submitter_count": len(submitters),
                    "source_status": CLINICAL_SOURCE_STATUS,
                    "target_href": target_href,
                },
                variants=[
                    SearchVariantWrite(
                        gene_symbol=gene,
                        gene_symbol_norm=gene,
                    )
                ],
            )
        )
    return documents


def _condition_entry(
    by_condition: dict[str, dict[str, object]],
    disease_id: str,
    name: str,
) -> dict[str, object]:
    entry = by_condition.setdefault(
        disease_id,
        {
            "names": set(),
            "ids": set(),
            "xrefs": set(),
            "definitions": set(),
            "phenotypes": set(),
            "hpo_ids": set(),
            "genes": set(),
            "gene_validity": set(),
            "gencc_assertions": set(),
            "inheritance": set(),
            "sources": set(),
        },
    )
    _add(entry, "names", name)
    return entry


def _gene_disease_entry(
    by_relationship: dict[tuple[str, str], dict[str, object]],
    gene: str,
    disease_id: str,
    disease_name: str,
) -> dict[str, object]:
    normalized_gene = gene.strip().upper()
    entry = by_relationship.setdefault(
        (normalized_gene, disease_id),
        {
            "disease_names": set(),
            "hgnc_ids": set(),
            "clingen_classifications": set(),
            "gencc_assertions": set(),
            "inheritance": set(),
            "submitters": set(),
            "source_dates": set(),
            "report_urls": set(),
            "sources": set(),
        },
    )
    _add(entry, "disease_names", disease_name)
    return entry


def _mapped_condition_id(value: str | None, mondo_by_xref: Mapping[str, str]) -> str | None:
    if not value:
        return None
    return mondo_by_xref.get(value.upper(), value)


def _source_versions(bundle: ClinicalSourceImportBundle) -> dict[str, str]:
    return {
        version.source_id: version.source_release
        for version in bundle.source_versions
        if version.source_id and version.source_release
    }


def _source_label(provenance: object, *, default: str) -> str:
    source_id = default
    source_version = None
    if isinstance(provenance, Mapping):
        source_id = _text(provenance.get("source_id")) or default
        source_version = _text(provenance.get("source_version"))
    return f"{source_id}:{source_version}" if source_version else source_id


def _source_ids_from_sources(sources: Sequence[str]) -> list[str]:
    ids = []
    for source in sources:
        source_id = source.split(":", 1)[0].strip()
        if source_id and source_id not in ids:
            ids.append(source_id)
    return ids


def _source_version_summary(source_versions: Mapping[str, str], source_ids: Sequence[str]) -> str:
    parts = [
        f"{source_id}={source_versions[source_id]}"
        for source_id in source_ids
        if source_versions.get(source_id)
    ]
    return " | ".join(parts)


def _add(entry: dict[str, object], key: str, value: str | None) -> None:
    if not value:
        return
    bucket = entry.get(key)
    if isinstance(bucket, set):
        bucket.add(value)


def _add_many(entry: dict[str, object], key: str, values: Sequence[str]) -> None:
    for value in values:
        _add(entry, key, value)


def _first(entry: Mapping[str, object], key: str) -> str | None:
    values = _sorted_values(entry, key)
    return values[0] if values else None


def _sorted_values(entry: Mapping[str, object], key: str) -> list[str]:
    value = entry.get(key)
    if not isinstance(value, set):
        return []
    return sorted(str(item) for item in value if str(item).strip())


def _text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _text_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [text for item in value if (text := _text(item))]
    text = _text(value)
    return [text] if text else []


def _join_text(items: Sequence[object | None]) -> str:
    return "\n".join(str(item).strip() for item in items if str(item or "").strip())


def _dedupe_documents(documents: Sequence[SearchDocumentWrite]) -> list[SearchDocumentWrite]:
    by_source_key: dict[str, SearchDocumentWrite] = {}
    for document in documents:
        by_source_key[document.source_key] = document
    return list(by_source_key.values())


def _stable_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9_.:-]+", "-", value.lower()).strip("-")
    if token:
        return token[:64]
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
