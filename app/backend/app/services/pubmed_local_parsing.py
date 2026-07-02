from __future__ import annotations

import csv
import gzip
from collections.abc import Iterable
from datetime import datetime, timezone
from hashlib import md5, sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Any
import xml.etree.ElementTree as ET

from app.core.config import Settings
from app.services.pubmed_local_constants import (
    BIOMEDICAL_DOMAIN_MARKERS,
    DEFAULT_ALLOWED_LANGUAGES,
    DEFAULT_EXCLUDED_PUBLICATION_TYPES,
    NON_BIOMEDICAL_NEGATIVE_MARKERS,
    PUBMED_LOCAL_SOURCE_VERSION_PREFIX,
)
from app.services.pubmed_local_license_policy import (
    abstract_policy_for_license,
    classify_license_profile,
)
from app.services.pubmed_local_models import PubMedSeedQuery, PubMedSourceFileManifest


def read_seed_queries(path: Path) -> list[PubMedSeedQuery]:
    seeds: list[PubMedSeedQuery] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row_number, row in enumerate(reader, start=2):
            gene = str(row.get("gene") or "").strip().upper()
            scope = str(row.get("scope") or "variant").strip().lower()
            if not gene:
                raise ValueError(f"seed row {row_number} missing gene")
            if scope not in {"variant", "gene"}:
                raise ValueError(f"seed row {row_number} has unsupported scope")
            seed = PubMedSeedQuery(
                gene=gene,
                cdna=_clean_optional(row.get("cdna")),
                transcript=_clean_optional(row.get("transcript")),
                protein_change=_clean_optional(row.get("protein_change")),
                rsid=_clean_optional(row.get("rsid")),
                genomic_hg38=_clean_optional(row.get("genomic_hg38")),
                scope=scope,
            )
            if seed.scope == "variant" and not seed.variant_terms:
                raise ValueError(f"seed row {row_number} variant scope needs a variant identifier")
            seeds.append(seed)
    return seeds


def read_pmc_oa_license_map(paths: Iterable[Path]) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for path in paths:
        for row in _iter_pmc_license_rows(path):
            pmcid = _normalize_pmcid(
                row.get("pmcid")
                or row.get("pmc_id")
                or row.get("accession")
                or row.get("article_id")
            )
            if not pmcid:
                continue
            license_value = (
                row.get("license_code")
                or row.get("license")
                or row.get("license_type")
                or row.get("license_url")
            )
            license_profile = classify_license_profile(license_value)
            rows[pmcid] = {
                "license_profile": license_profile,
                "license_source": "pmc_oa_license_metadata",
                "license_raw": _normalize_space(str(license_value or "")),
            }
    return rows


def _iter_pmc_license_rows(path: Path) -> Iterable[dict[str, Any]]:
    if path.suffix.lower() in {".jsonl", ".ndjson"} or path.name.endswith(".jsonl.gz"):
        with _open_text(path) as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    yield row
        return

    with _open_text(path) as handle:
        sample = handle.read(4096)
        handle.seek(0)
        delimiter = "\t" if "\t" in sample and sample.count("\t") >= sample.count(",") else ","
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            yield dict(row)


def _apply_pmc_license_overlay(
    article: dict[str, Any],
    pmc_license_map: dict[str, dict[str, str]],
) -> dict[str, Any]:
    pmcid = _normalize_pmcid(article.get("pmcid"))
    if not pmcid:
        return article
    overlay = pmc_license_map.get(pmcid)
    if not overlay:
        return article

    article = dict(article)
    prior_profile = str(article.get("license_profile") or "unknown")
    overlay_profile = overlay.get("license_profile") or "unknown"
    if overlay_profile != "unknown":
        article["license_profile"] = overlay_profile
        article["license_source"] = overlay.get("license_source") or "pmc_oa_license_metadata"
        transient_abstract = _clean_optional(article.get("_transient_abstract_text"))
        abstract_policy = abstract_policy_for_license(overlay_profile, transient_abstract)
        article["abstract_policy"] = abstract_policy
        if abstract_policy == "licensed_text_persisted" and transient_abstract:
            article["abstract_text"] = transient_abstract
            article["abstract_sha256"] = sha256(transient_abstract.encode("utf-8")).hexdigest()
        else:
            article["abstract_text"] = None
            article["abstract_sha256"] = None

    article["_pmc_license_overlay_used"] = True
    article["provenance_json"] = _merge_provenance(
        article.get("provenance_json"),
        {
            "pmc_license_overlay": {
                "pmcid": pmcid,
                "prior_license_profile": prior_profile,
                "license_profile": article.get("license_profile"),
                "text_policy": article.get("abstract_policy"),
            }
        },
    )
    return article


def _source_file_manifests(
    xml_files: Iterable[Path],
    jsonl_files: Iterable[Path],
    pubtator_edge_files: Iterable[Path],
    litvar_edge_files: Iterable[Path],
    *,
    xml_source_kind: str,
    checksum_summary: dict[str, Any],
) -> tuple[PubMedSourceFileManifest, ...]:
    md5_by_path = checksum_summary.get("by_path") if checksum_summary else {}
    manifests: list[PubMedSourceFileManifest] = []
    for load_order, path in enumerate(xml_files, start=1):
        manifests.append(
            PubMedSourceFileManifest(
                path=path,
                load_order=load_order,
                source_kind=_pubmed_xml_source_kind(path, xml_source_kind),
                source_format="pubmed_xml",
                source_file_name=path.name,
                size_bytes=_safe_size(path),
                md5_status=str(md5_by_path.get(str(path), "not_checked")),
            )
        )
    offset = len(manifests)
    for index, path in enumerate(jsonl_files, start=1):
        manifests.append(
            PubMedSourceFileManifest(
                path=path,
                load_order=offset + index,
                source_kind="import_jsonl",
                source_format="jsonl",
                source_file_name=path.name,
                size_bytes=_safe_size(path),
                md5_status="not_checked",
            )
        )
    offset = len(manifests)
    for index, path in enumerate(pubtator_edge_files, start=1):
        manifests.append(
            PubMedSourceFileManifest(
                path=path,
                load_order=offset + index,
                source_kind="pubtator_edges",
                source_format="literature_edge_jsonl",
                source_file_name=path.name,
                size_bytes=_safe_size(path),
                md5_status="not_checked",
            )
        )
    offset = len(manifests)
    for index, path in enumerate(litvar_edge_files, start=1):
        manifests.append(
            PubMedSourceFileManifest(
                path=path,
                load_order=offset + index,
                source_kind="litvar_edges",
                source_format="literature_edge_jsonl",
                source_file_name=path.name,
                size_bytes=_safe_size(path),
                md5_status="not_checked",
            )
        )
    return tuple(manifests)


def _pubmed_xml_source_kind(path: Path, mode: str) -> str:
    if mode in {"baseline", "pubmed_baseline"}:
        return "pubmed_baseline"
    if mode in {"update", "pubmed_update"}:
        return "pubmed_update"
    if mode == "pubmed_xml":
        return "pubmed_xml"
    folded = "/".join(part.lower() for part in path.parts)
    if "baseline" in folded:
        return "pubmed_baseline"
    if "update" in folded:
        return "pubmed_update"
    return "pubmed_xml"


def _iter_articles_from_source_file(
    source_file: PubMedSourceFileManifest,
    *,
    source_version: str,
    pmc_license_map: dict[str, dict[str, str]],
) -> Iterable[dict[str, Any]]:
    if source_file.source_format == "pubmed_xml":
        iterator = _parse_pubmed_xml(
            source_file.path,
            source_version=source_version,
            pmc_license_map=pmc_license_map,
        )
    else:
        iterator = _parse_pubmed_jsonl(
            source_file.path,
            source_version=source_version,
            pmc_license_map=pmc_license_map,
        )
    for article in iterator:
        yield _with_source_file_provenance(article, source_file)


def _with_source_file_provenance(
    article: dict[str, Any],
    source_file: PubMedSourceFileManifest,
) -> dict[str, Any]:
    provenance = _json_object(article.get("provenance_json"))
    provenance["source_file"] = {
        "file_name": source_file.source_file_name,
        "load_order": source_file.load_order,
        "source_kind": source_file.source_kind,
        "source_format": source_file.source_format,
    }
    article["provenance_json"] = json.dumps(provenance, sort_keys=True)
    return article


def _iter_literature_edges_from_source_file(
    source_file: PubMedSourceFileManifest,
    *,
    source_version: str,
) -> Iterable[dict[str, Any] | None]:
    with _open_text(source_file.path) as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                yield None
                continue
            if not isinstance(row, dict):
                yield None
                continue
            yield _literature_edge_from_jsonl_row(
                row,
                source_file=source_file,
                line_number=line_number,
                source_version=source_version,
            )


def _literature_edge_from_jsonl_row(
    row: dict[str, Any],
    *,
    source_file: PubMedSourceFileManifest,
    line_number: int,
    source_version: str,
) -> dict[str, Any] | None:
    pmid = str(row.get("pmid") or row.get("pubmed_id") or "").strip()
    if not re.fullmatch(r"\d{1,9}", pmid):
        return None

    source = _clean_optional(row.get("source")) or _literature_edge_source(source_file.source_kind)
    raw_entity_type = (
        row.get("entity_type")
        or row.get("type")
        or row.get("annotation_type")
        or ("variant" if source_file.source_kind == "litvar_edges" else "entity")
    )
    entity_type = _normalize_edge_entity_type(raw_entity_type)
    identifier = _clean_optional(
        row.get("identifier")
        or row.get("normalized_id")
        or row.get("concept_id")
        or row.get("variant_id")
        or row.get("rsid")
        or row.get("hgvs")
        or row.get("cdna")
        or row.get("variant")
    )
    matched_text = _clean_optional(
        row.get("matched_text") or row.get("mention") or row.get("text") or row.get("name")
    )
    normalized_identifier = _normalize_term(identifier or matched_text)
    normalized_mention = _normalize_term(matched_text)
    if not normalized_identifier and not normalized_mention:
        return None

    evidence_text = _clean_optional(
        row.get("evidence_text") or row.get("snippet") or row.get("context")
    )
    annotation_id = _clean_optional(row.get("annotation_id") or row.get("id"))
    provenance = {
        "source_channel": "literature_edge_jsonl",
        "line_number": line_number,
        "annotation_id": annotation_id,
        "source_file": {
            "file_name": source_file.source_file_name,
            "load_order": source_file.load_order,
            "source_kind": source_file.source_kind,
            "source_format": source_file.source_format,
        },
    }
    return {
        "edge_id": _literature_edge_id(
            source_file=source_file,
            line_number=line_number,
            pmid=pmid,
            source=source,
            entity_type=entity_type,
            identifier=identifier,
            matched_text=matched_text,
            annotation_id=annotation_id,
        ),
        "pmid": pmid,
        "source": source,
        "entity_type": entity_type,
        "identifier": identifier,
        "normalized_identifier": normalized_identifier,
        "matched_text": matched_text or "",
        "normalized_mention": normalized_mention,
        "section": _clean_optional(row.get("section")) or "",
        "offset_start": _optional_int(row.get("offset_start"), row.get("start")),
        "offset_end": _optional_int(row.get("offset_end"), row.get("end")),
        "relation_type": _clean_optional(row.get("relation_type") or row.get("relation")),
        "evidence_text": evidence_text,
        "source_url": _clean_optional(row.get("source_url") or row.get("url")),
        "source_file_id": source_file.source_file_id,
        "source_kind": source_file.source_kind,
        "source_file_name": source_file.source_file_name,
        "load_order": source_file.load_order,
        "source_version": source_version,
        "imported_at": _utc_now(),
        "provenance_json": json.dumps(provenance, sort_keys=True),
    }


def _normalize_edge_entity_type(value: Any) -> str:
    text = _normalize_space(str(value or "")).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if text in {"mutation", "mutations", "sequence_variant", "dna_variant"}:
        return "variant"
    if text in {"genes", "gene_symbol"}:
        return "gene"
    return text or "entity"


def _literature_edge_source(source_kind: str) -> str:
    if source_kind == "litvar_edges":
        return "litvar2"
    if source_kind == "pubtator_edges":
        return "pubtator"
    return source_kind


def _literature_edge_id(
    *,
    source_file: PubMedSourceFileManifest,
    line_number: int,
    pmid: str,
    source: str,
    entity_type: str,
    identifier: str | None,
    matched_text: str | None,
    annotation_id: str | None,
) -> str:
    payload = "|".join(
        (
            source_file.source_file_id,
            str(line_number),
            pmid,
            source,
            entity_type,
            identifier or "",
            matched_text or "",
            annotation_id or "",
        )
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _optional_int(*values: Any) -> int | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _edge_seed_terms_by_pmid(
    source_files: Iterable[PubMedSourceFileManifest],
    seeds: list[PubMedSeedQuery],
    *,
    source_version: str,
) -> dict[str, dict[str, list[tuple[str, str, str]]]]:
    if not seeds:
        return {}
    edge_sources = [
        source_file
        for source_file in source_files
        if source_file.source_format == "literature_edge_jsonl"
    ]
    if not edge_sources:
        return {}
    by_pmid: dict[str, dict[str, list[tuple[str, str, str]]]] = {}
    for source_file in edge_sources:
        for edge in _iter_literature_edges_from_source_file(
            source_file,
            source_version=source_version,
        ):
            if edge is None:
                continue
            for seed in seeds:
                matched_terms = _edge_matched_seed_terms(edge, seed)
                if not matched_terms:
                    continue
                seed_terms = by_pmid.setdefault(edge["pmid"], {}).setdefault(
                    seed.coverage_key,
                    [],
                )
                seed_terms.extend(matched_terms)
    return {
        pmid: {
            coverage_key: _dedupe_term_matches(matches) for coverage_key, matches in by_seed.items()
        }
        for pmid, by_seed in by_pmid.items()
    }


def _edge_matched_seed_terms(
    edge: dict[str, Any],
    seed: PubMedSeedQuery,
) -> list[tuple[str, str, str]]:
    edge_type = str(edge.get("entity_type") or "")
    source = str(edge.get("source") or "edge")
    field = f"edge:{source}"
    normalized_values = {
        str(edge.get("normalized_identifier") or ""),
        str(edge.get("normalized_mention") or ""),
    }
    matches: list[tuple[str, str, str]] = []
    if edge_type == "gene" and _normalize_term(seed.gene) in normalized_values:
        matches.append(("gene", seed.gene, field))
    if edge_type in {"variant", "rsid", "snp"}:
        for term_type, value in seed.terms:
            if term_type == "gene":
                continue
            if _normalize_term(value) in normalized_values:
                matches.append((term_type, value, field))
    return matches


def _dedupe_term_matches(
    matches: Iterable[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    deduped: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for term_type, value, field in matches:
        key = (term_type, value, field)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


def _iter_articles(
    xml_files: Iterable[Path],
    jsonl_files: Iterable[Path],
    *,
    source_version: str,
    pmc_license_map: dict[str, dict[str, str]] | None = None,
) -> Iterable[dict[str, Any]]:
    pmc_license_map = pmc_license_map or {}
    for path in xml_files:
        yield from _parse_pubmed_xml(
            path,
            source_version=source_version,
            pmc_license_map=pmc_license_map,
        )
    for path in jsonl_files:
        yield from _parse_pubmed_jsonl(
            path,
            source_version=source_version,
            pmc_license_map=pmc_license_map,
        )


def _parse_pubmed_jsonl(
    path: Path,
    *,
    source_version: str,
    pmc_license_map: dict[str, dict[str, str]],
) -> Iterable[dict[str, Any]]:
    with _open_text(path) as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            pmid = str(row.get("pmid") or "").strip()
            if not re.fullmatch(r"\d{1,9}", pmid):
                continue
            license_profile = classify_license_profile(
                str(row.get("license_profile") or row.get("copyright") or "")
            )
            abstract = _clean_optional(row.get("abstract"))
            abstract_policy = abstract_policy_for_license(license_profile, abstract)
            if abstract_policy != "licensed_text_persisted":
                abstract = None
            title = _clean_optional(row.get("title")) or "Untitled"
            article = {
                "pmid": pmid,
                "title": title,
                "authors_display": _clean_optional(row.get("authors")) or "",
                "journal": _clean_optional(row.get("journal")) or "",
                "year": _clean_optional(row.get("year"))
                or _year_from_date(row.get("publication_date")),
                "publication_date": _clean_optional(row.get("publication_date")),
                "doi": _clean_optional(row.get("doi")),
                "pmcid": _clean_optional(row.get("pmcid")),
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "source_status": _clean_optional(row.get("source_status")) or "available",
                "source_version": source_version,
                "fetched_at": _utc_now(),
                "license_profile": license_profile,
                "license_source": _clean_optional(row.get("license_source")) or "import_jsonl",
                "abstract_policy": abstract_policy,
                "abstract_text": abstract,
                "abstract_sha256": (
                    sha256(abstract.encode("utf-8")).hexdigest() if abstract else None
                ),
                "is_retracted": 1 if bool(row.get("is_retracted")) else 0,
                "mesh_terms": tuple(_string_list(row.get("mesh_terms"))),
                "chemical_terms": tuple(_string_list(row.get("chemical_terms"))),
                "publication_types": tuple(_string_list(row.get("publication_types"))),
                "language": _clean_optional(row.get("language")) or "",
                "provenance_json": json.dumps(
                    {
                        "source_channel": "import_jsonl",
                        "line_number": line_number,
                        "text_policy": abstract_policy,
                    },
                    sort_keys=True,
                ),
                "_transient_abstract_text": _clean_optional(row.get("abstract")) or "",
            }
            yield _apply_pmc_license_overlay(article, pmc_license_map)


def _parse_pubmed_xml(
    path: Path,
    *,
    source_version: str,
    pmc_license_map: dict[str, dict[str, str]],
) -> Iterable[dict[str, Any]]:
    with _open_binary(path) as handle:
        context = ET.iterparse(handle, events=("start", "end"))
        root: ET.Element | None = None
        for event, elem in context:
            if event == "start":
                if root is None:
                    root = elem
                continue
            if elem.tag == "PubmedArticle":
                article = _article_from_pubmed_xml(elem, source_version=source_version)
                if article is not None:
                    yield _apply_pmc_license_overlay(article, pmc_license_map)
                _clear_parsed_xml_element(elem, root)
            elif elem.tag == "DeleteCitation":
                for pmid_el in elem.findall(".//PMID"):
                    pmid = (pmid_el.text or "").strip()
                    if re.fullmatch(r"\d{1,9}", pmid):
                        yield _deleted_article(pmid, source_version=source_version)
                _clear_parsed_xml_element(elem, root)


def _clear_parsed_xml_element(elem: ET.Element, root: ET.Element | None) -> None:
    elem.clear()
    if root is not None and root is not elem:
        root.clear()


def _article_from_pubmed_xml(elem: ET.Element, *, source_version: str) -> dict[str, Any] | None:
    pmid = _find_text(elem, ".//MedlineCitation/PMID")
    if not pmid or not re.fullmatch(r"\d{1,9}", pmid):
        return None
    title = _normalize_space(_iter_text_first(elem, ".//Article/ArticleTitle")) or "Untitled"
    abstract_parts: list[str] = []
    for abstract_el in elem.findall(".//Article/Abstract/AbstractText"):
        text = _normalize_space("".join(abstract_el.itertext()))
        if not text:
            continue
        label = abstract_el.get("Label")
        abstract_parts.append(f"{label}: {text}" if label else text)
    abstract = " ".join(abstract_parts) if abstract_parts else None
    copyright_text = _find_text(elem, ".//Article/Abstract/CopyrightInformation")
    license_profile = classify_license_profile(copyright_text)
    abstract_policy = abstract_policy_for_license(license_profile, abstract)
    stored_abstract = abstract if abstract_policy == "licensed_text_persisted" else None
    journal = (
        _find_text(elem, ".//Article/Journal/ISOAbbreviation")
        or _find_text(elem, ".//Article/Journal/Title")
        or ""
    )
    publication_date = _publication_date(elem)
    year = (
        _year_from_date(publication_date)
        or _find_text(elem, ".//Article/Journal/JournalIssue/PubDate/Year")
        or ""
    )
    authors = _authors_display(elem)
    doi = _article_id(elem, "doi") or _elocation_id(elem, "doi")
    pmcid = _article_id(elem, "pmc")
    mesh_terms = tuple(
        _normalize_space("".join(item.itertext()))
        for item in elem.findall(".//MeshHeading/DescriptorName")
        if _normalize_space("".join(item.itertext()))
    )
    chemical_terms = tuple(
        _normalize_space("".join(item.itertext()))
        for item in elem.findall(".//Chemical/NameOfSubstance")
        if _normalize_space("".join(item.itertext()))
    )
    publication_types = tuple(
        _normalize_space("".join(item.itertext()))
        for item in elem.findall(".//PublicationTypeList/PublicationType")
        if _normalize_space("".join(item.itertext()))
    )
    language = _find_text(elem, ".//Article/Language") or ""
    provenance = {
        "source_channel": "pubmed_xml",
        "source_release": source_version,
        "text_policy": abstract_policy,
        "license_source": "CopyrightInformation" if copyright_text else "not_present",
    }
    return {
        "pmid": pmid,
        "title": title,
        "authors_display": authors,
        "journal": journal,
        "year": year,
        "publication_date": publication_date,
        "doi": doi,
        "pmcid": pmcid,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "source_status": "available",
        "source_version": source_version,
        "fetched_at": _utc_now(),
        "license_profile": license_profile,
        "license_source": "pubmed_xml_copyright_information" if copyright_text else None,
        "abstract_policy": abstract_policy,
        "abstract_text": stored_abstract,
        "abstract_sha256": (
            sha256(stored_abstract.encode("utf-8")).hexdigest() if stored_abstract else None
        ),
        "is_retracted": 1 if _is_retracted(publication_types) else 0,
        "mesh_terms": mesh_terms,
        "chemical_terms": chemical_terms,
        "publication_types": publication_types,
        "language": language,
        "provenance_json": json.dumps(provenance, sort_keys=True),
        "_transient_abstract_text": abstract or "",
    }


def _deleted_article(pmid: str, *, source_version: str) -> dict[str, Any]:
    return {
        "pmid": pmid,
        "title": "Deleted PubMed citation",
        "authors_display": "",
        "journal": "",
        "year": "",
        "publication_date": None,
        "doi": None,
        "pmcid": None,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "source_status": "deleted",
        "source_version": source_version,
        "fetched_at": _utc_now(),
        "license_profile": "metadata_only",
        "license_source": "pubmed_deletecitation",
        "abstract_policy": "metadata_only_no_abstract",
        "abstract_text": None,
        "abstract_sha256": None,
        "is_retracted": 0,
        "mesh_terms": (),
        "chemical_terms": (),
        "publication_types": (),
        "language": "",
        "provenance_json": json.dumps({"source_channel": "pubmed_xml_deletecitation"}),
    }


def _normalize_allowed_domains(values: Iterable[str]) -> set[str]:
    domains = {str(value).strip().lower() for value in values if str(value).strip()}
    return {domain for domain in domains if domain in BIOMEDICAL_DOMAIN_MARKERS}


def _article_matches_allowed_domains(article: dict[str, Any], allowed_domains: set[str]) -> bool:
    if not allowed_domains:
        return True
    if str(article.get("source_status") or "") != "available":
        return False
    if int(article.get("is_retracted") or 0):
        return False
    language = str(article.get("language") or "").strip().lower()
    if language and language not in DEFAULT_ALLOWED_LANGUAGES:
        return False
    publication_types = tuple(
        str(item).strip().lower() for item in article.get("publication_types") or ()
    )
    if any(item in DEFAULT_EXCLUDED_PUBLICATION_TYPES for item in publication_types):
        return False

    haystack = _domain_filter_text(article)
    if any(marker in haystack for marker in NON_BIOMEDICAL_NEGATIVE_MARKERS) and not any(
        _domain_matches(haystack, domain) for domain in allowed_domains
    ):
        return False
    return any(_domain_matches(haystack, domain) for domain in allowed_domains)


def _domain_matches(text: str, domain: str) -> bool:
    return any(
        _contains_domain_marker(text, marker)
        for marker in BIOMEDICAL_DOMAIN_MARKERS.get(domain, ())
    )


def _contains_domain_marker(text: str, marker: str) -> bool:
    marker = marker.strip().lower()
    if not marker:
        return False
    if " " in marker:
        return marker in text
    return re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", text) is not None


def _domain_filter_text(article: dict[str, Any]) -> str:
    fields = _article_search_fields(article)
    return _normalize_space(" ".join(fields.values())).lower()


def _matched_seed_terms(
    article: dict[str, Any],
    seeds: list[PubMedSeedQuery],
    *,
    extra_terms_by_seed: dict[str, list[tuple[str, str, str]]] | None = None,
) -> list[tuple[PubMedSeedQuery, list[tuple[str, str, str]]]]:
    if not seeds:
        return []
    fields = _article_search_fields(article)
    matches: list[tuple[PubMedSeedQuery, list[tuple[str, str, str]]]] = []
    for seed in seeds:
        extra_terms = tuple((extra_terms_by_seed or {}).get(seed.coverage_key, ()))
        extra_gene_match = next(
            (
                matched_field
                for term_type, _value, matched_field in extra_terms
                if term_type == "gene"
            ),
            None,
        )
        gene_match = _find_seed_term_field(seed.gene, "gene", fields)
        if gene_match is None:
            gene_match = extra_gene_match
        if gene_match is None:
            continue
        matched_terms: list[tuple[str, str, str]] = [("gene", seed.gene, gene_match)]
        variant_matched = False
        for term_type, value in seed.terms:
            if term_type == "gene":
                continue
            field = _find_seed_term_field(value, term_type, fields)
            if field is None:
                field = next(
                    (
                        matched_field
                        for extra_type, extra_value, matched_field in extra_terms
                        if extra_type == term_type
                        and _normalize_term(extra_value) == _normalize_term(value)
                    ),
                    None,
                )
            if field is None:
                continue
            matched_terms.append((term_type, value, field))
            variant_matched = True
        if seed.scope == "variant" and not variant_matched:
            continue
        matches.append((seed, matched_terms))
    return matches


def _article_search_fields(article: dict[str, Any]) -> dict[str, str]:
    return {
        "title": str(article.get("title") or ""),
        "abstract": str(
            article.get("abstract_text") or article.get("_transient_abstract_text") or ""
        ),
        "journal": str(article.get("journal") or ""),
        "authors": str(article.get("authors_display") or ""),
        "doi": str(article.get("doi") or ""),
        "pmcid": str(article.get("pmcid") or ""),
        "mesh": " ".join(article.get("mesh_terms") or ()),
        "chemical": " ".join(article.get("chemical_terms") or ()),
        "publication_types": " ".join(article.get("publication_types") or ()),
    }


def _find_seed_term_field(term: str, term_type: str, fields: dict[str, str]) -> str | None:
    if term_type == "gene":
        return _find_gene_term_field(term, fields)
    return _find_term_field(term, fields)


def _find_gene_term_field(term: str, fields: dict[str, str]) -> str | None:
    symbol = str(term or "").strip()
    if not symbol:
        return None
    for field, text in fields.items():
        if _contains_gene_symbol(text, symbol):
            return field
    return None


def _contains_gene_symbol(text: str | None, symbol: str) -> bool:
    if not text:
        return False
    token = re.escape(symbol)
    if symbol.isalpha() and len(symbol) <= 4:
        return re.search(rf"(?<![A-Za-z0-9]){token}(?![A-Za-z0-9])", text) is not None
    return re.search(rf"(?<![A-Za-z0-9]){token}(?![A-Za-z0-9])", text, re.IGNORECASE) is not None


def _find_term_field(term: str, fields: dict[str, str]) -> str | None:
    norm = _normalize_term(term)
    if not norm:
        return None
    for field, text in fields.items():
        if norm in _normalize_text_for_contains(text):
            return field
    return None


def _verify_input_md5_sidecars(xml_paths: Iterable[Path]) -> dict[str, Any]:
    verified = 0
    missing = 0
    mismatched = 0
    warnings: list[str] = []
    by_path: dict[str, str] = {}
    for path in xml_paths:
        sidecar = _md5_sidecar_path(path)
        if sidecar is None:
            missing += 1
            by_path[str(path)] = "missing"
            warnings.append("input_md5_sidecar_missing")
            continue
        expected = _read_md5_sidecar(sidecar)
        actual = _file_md5(path)
        if not expected or expected.lower() != actual.lower():
            mismatched += 1
            by_path[str(path)] = "mismatch"
            warnings.append("input_md5_sidecar_mismatch")
            continue
        verified += 1
        by_path[str(path)] = "verified"
    if mismatched:
        status = "mismatch"
    elif missing:
        status = "partial"
    else:
        status = "verified" if verified else "not_checked"
    return {
        "status": status,
        "verified_count": verified,
        "missing_count": missing,
        "mismatched_count": mismatched,
        "by_path": by_path,
        "warnings": tuple(_dedupe(warnings)),
    }


def _md5_sidecar_path(path: Path) -> Path | None:
    candidates = (
        path.with_name(f"{path.name}.md5"),
        path.with_suffix(f"{path.suffix}.md5"),
        path.with_suffix(".md5"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _read_md5_sidecar(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"\b([a-fA-F0-9]{32})\b", text)
    return match.group(1) if match else None


def _file_md5(path: Path) -> str:
    digest = md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_pmcid(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    text = re.sub(r"[^A-Z0-9]", "", text)
    if not text:
        return None
    return text if text.startswith("PMC") else f"PMC{text}"


def _merge_provenance(value: Any, patch: dict[str, Any]) -> str:
    base: dict[str, Any] = {}
    if isinstance(value, str) and value.strip():
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = {}
        if isinstance(decoded, dict):
            base = dict(decoded)
    base.update(patch)
    return json.dumps(base, sort_keys=True)


def _normalize_term(value: str | None) -> str:
    text = _normalize_space(value or "").lower()
    return re.sub(r"[^a-z0-9.>:_-]+", "", text)


def _normalize_text_for_contains(value: str | None) -> str:
    text = _normalize_space(value or "").lower()
    return re.sub(r"[^a-z0-9.>:_-]+", " ", text)


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _cdna_from_transcript_hgvs(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(":")[-1].strip() or None


def _gene_scope_query(gene: str) -> str:
    return f"{gene}[Gene Name]"


def _gene_scope_url(gene: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/?term={gene}[gene]"


def _connect_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def _safe_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def _json_list(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return []
    else:
        decoded = value
    if not isinstance(decoded, list):
        return []
    return [str(item) for item in decoded if isinstance(item, str)]


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
    else:
        decoded = value
    return dict(decoded) if isinstance(decoded, dict) else {}


def _json_dict_int(value: Any) -> dict[str, int]:
    decoded = _json_object(value)
    return {str(key): int(raw or 0) for key, raw in decoded.items()}


def _json_nested_int(value: Any) -> dict[str, dict[str, int]]:
    decoded = _json_object(value)
    nested: dict[str, dict[str, int]] = {}
    for key, raw in decoded.items():
        if not isinstance(raw, dict):
            continue
        nested[str(key)] = {
            str(child_key): int(child_value or 0) for child_key, child_value in raw.items()
        }
    return nested


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Iterable):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _open_binary(path: Path):
    return gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb")


def _open_text(path: Path):
    return (
        gzip.open(path, "rt", encoding="utf-8")
        if path.suffix == ".gz"
        else path.open(
            "r",
            encoding="utf-8",
        )
    )


def _find_text(elem: ET.Element, path: str) -> str | None:
    item = elem.find(path)
    if item is None or item.text is None:
        return None
    return _normalize_space(item.text)


def _iter_text_first(elem: ET.Element, path: str) -> str:
    item = elem.find(path)
    return "".join(item.itertext()) if item is not None else ""


def _publication_date(elem: ET.Element) -> str | None:
    pub_date = elem.find(".//Article/Journal/JournalIssue/PubDate")
    if pub_date is None:
        return None
    year = _find_text(pub_date, "Year")
    month = _find_text(pub_date, "Month")
    day = _find_text(pub_date, "Day")
    if not year:
        medline = _find_text(pub_date, "MedlineDate")
        return medline
    parts = [year]
    if month:
        parts.append(month)
    if day:
        parts.append(day)
    return "-".join(parts)


def _year_from_date(value: Any) -> str:
    text = str(value or "")
    match = re.search(r"(\d{4})", text)
    return match.group(1) if match else ""


def _authors_display(elem: ET.Element) -> str:
    names: list[str] = []
    for author in elem.findall(".//Article/AuthorList/Author"):
        collective = _find_text(author, "CollectiveName")
        if collective:
            names.append(collective)
            continue
        last = _find_text(author, "LastName")
        initials = _find_text(author, "Initials")
        if last:
            names.append(f"{last} {initials}".strip())
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return f"{names[0]} et al."


def _article_id(elem: ET.Element, id_type: str) -> str | None:
    for item in elem.findall(".//PubmedData/ArticleIdList/ArticleId"):
        if (item.get("IdType") or "").lower() == id_type and item.text:
            return item.text.strip()
    return None


def _elocation_id(elem: ET.Element, id_type: str) -> str | None:
    for item in elem.findall(".//Article/ELocationID"):
        if (item.get("EIdType") or "").lower() == id_type and item.text:
            return item.text.strip()
    return None


def _is_retracted(publication_types: Iterable[str]) -> bool:
    return any("retract" in item.lower() for item in publication_types)


def _default_source_version() -> str:
    return f"{PUBMED_LOCAL_SOURCE_VERSION_PREFIX}-{datetime.now(timezone.utc).date().isoformat()}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
