"""Fail-soft bibliographic metadata from embedded fields and bounded text."""

from __future__ import annotations

import re
from typing import Any, Mapping

from app.schemas.paper_variants import PaperBibliographicMetadataV2, PaperSourceMetadata
from app.services.paper_extract.document import PaperInputDocument

_DOI_RE = re.compile(r"\b10\.[0-9]{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
_PMID_RE = re.compile(r"\bPMID\s*[:#]?\s*([0-9]{6,9})\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(?:19|20)[0-9]{2}\b")


def bibliographic_metadata(
    document: PaperInputDocument,
) -> PaperBibliographicMetadataV2 | None:
    embedded = _clean_mapping(document.embedded_metadata)
    bounded = document.text[:20_000]
    lines = [line.strip() for line in bounded.splitlines() if line.strip()]
    title = _meaningful(embedded.get("title"), 512, placeholders={"untitled"})
    provenance: list[str] = []
    if title:
        provenance.append(f"{document.extraction_engine}:embedded_title")
    elif (
        len(lines) >= 2
        and 8 <= len(lines[0]) <= 500
        and not re.search(r"\b[cpgrmno]\.", lines[0], flags=re.IGNORECASE)
    ):
        title = lines[0]
        provenance.append("eamos_text:first_nonempty_line")

    doi = _bounded(embedded.get("doi"), 160)
    if not doi:
        match = _DOI_RE.search(bounded)
        doi = match.group(0).rstrip(".,;)") if match else None
        if doi:
            provenance.append("eamos_text:doi_grammar")
    pmid = _bounded(embedded.get("pmid"), 128)
    if not pmid:
        match = _PMID_RE.search(bounded)
        pmid = match.group(1) if match else None
        if pmid:
            provenance.append("eamos_text:pmid_grammar")
    year_value = embedded.get("year")
    year = _year(year_value)
    if year is None:
        match = _YEAR_RE.search(bounded)
        year = int(match.group(0)) if match else None
        if year:
            provenance.append("eamos_text:year_grammar")

    authors = _authors(embedded.get("author") or embedded.get("authors"))
    if authors:
        provenance.append(f"{document.extraction_engine}:embedded_authors")
    journal = _meaningful(
        embedded.get("journal") or embedded.get("subject"),
        160,
        placeholders={"unspecified", "none"},
    )
    if journal:
        provenance.append(f"{document.extraction_engine}:embedded_journal")
    if not any((title, authors, year, journal, doi, pmid)):
        return None
    return PaperBibliographicMetadataV2(
        title=title,
        authors=authors,
        year=year,
        journal=journal,
        doi=doi,
        pmid=pmid,
        provenance=list(dict.fromkeys(provenance)),
    )


def legacy_source_metadata(
    metadata: PaperBibliographicMetadataV2 | None,
) -> PaperSourceMetadata | None:
    if metadata is None:
        return None
    return PaperSourceMetadata(
        title=metadata.title,
        authors=metadata.authors,
        year=str(metadata.year) if metadata.year is not None else None,
        journal=metadata.journal,
        doi=metadata.doi,
        pmid=metadata.pmid,
    )


def _clean_mapping(value: Mapping[str, Any]) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, raw in value.items():
        if raw is None:
            continue
        normalized_key = str(key).strip().lower().lstrip("/")[:64]
        normalized_value = str(raw).replace("\x00", " ").strip()
        if normalized_key and normalized_value:
            clean[normalized_key] = normalized_value[:512]
    return clean


def _bounded(value: str | None, limit: int) -> str | None:
    if not value:
        return None
    return value.strip()[:limit] or None


def _meaningful(value: str | None, limit: int, *, placeholders: set[str]) -> str | None:
    bounded = _bounded(value, limit)
    if bounded is None or bounded.lower().strip("() ") in placeholders:
        return None
    return bounded


def _authors(value: str | None) -> list[str]:
    if not value:
        return []
    values = re.split(r"\s*(?:;|\band\b)\s*", value)
    return [
        item[:160]
        for item in values
        if item and item.lower().strip("() ") not in {"anonymous", "unknown", "unspecified"}
    ][:128]


def _year(value: str | None) -> int | None:
    if not value:
        return None
    match = _YEAR_RE.search(value)
    return int(match.group(0)) if match else None
