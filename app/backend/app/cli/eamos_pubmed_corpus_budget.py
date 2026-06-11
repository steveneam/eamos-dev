from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

BYTES_PER_GIB = 1024**3
DEFAULT_STORAGE_USED_GIB = 38.0
DEFAULT_STORAGE_QUOTA_GIB = 100.0
DEFAULT_DATABASE_USED_GIB = 0.019
DEFAULT_DATABASE_QUOTA_GIB = 8.0
DEFAULT_FILTERED_PMC_FRACTION = 0.05


@dataclass(frozen=True)
class ListingSource:
    key: str
    label: str
    url: str


@dataclass(frozen=True)
class ListingEntry:
    name: str
    size_bytes: int
    last_modified: str = ""


@dataclass(frozen=True)
class InventoryItem:
    label: str
    file_count: int
    compressed_bytes: int
    source_keys: tuple[str, ...]
    note: str = ""

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "file_count": self.file_count,
            "compressed_gib": _round_gib(self.compressed_bytes),
            "compressed_bytes": self.compressed_bytes,
            "source_keys": list(self.source_keys),
            "note": self.note,
        }


LISTING_SOURCES: tuple[ListingSource, ...] = (
    ListingSource(
        "pubmed_baseline",
        "PubMed 2026 baseline XML",
        "https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/",
    ),
    ListingSource(
        "pubmed_updatefiles",
        "PubMed 2026 update XML",
        "https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/",
    ),
    ListingSource(
        "pubtator3",
        "PubTator3 bulk data",
        "https://ftp.ncbi.nlm.nih.gov/pub/lu/PubTator3/",
    ),
    ListingSource(
        "pmc_top",
        "PMC top-level crosswalks",
        "https://ftp.ncbi.nlm.nih.gov/pub/pmc/",
    ),
    ListingSource(
        "pmc_oa_comm_xml",
        "PMC OA commercial-use XML",
        "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_bulk/oa_comm/xml/",
    ),
    ListingSource(
        "pmc_oa_noncomm_xml",
        "PMC OA non-commercial XML",
        "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_bulk/oa_noncomm/xml/",
    ),
    ListingSource(
        "pmc_oa_other_xml",
        "PMC OA other-license XML",
        "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_bulk/oa_other/xml/",
    ),
    ListingSource(
        "pmc_oa_comm_txt",
        "PMC OA commercial-use text",
        "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_bulk/oa_comm/txt/",
    ),
    ListingSource(
        "pmc_oa_noncomm_txt",
        "PMC OA non-commercial text",
        "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_bulk/oa_noncomm/txt/",
    ),
    ListingSource(
        "pmc_oa_other_txt",
        "PMC OA other-license text",
        "https://ftp.ncbi.nlm.nih.gov/pub/pmc/deprecated/oa_bulk/oa_other/txt/",
    ),
)

PUBTATOR_SELECTOR_FILES = frozenset(
    {
        "bioconcepts2pubtator3.gz",
        "gene2pubtator3.gz",
        "mutation2pubtator3.gz",
        "relation2pubtator3.gz",
    }
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a SUPA-LIT-0 PubMed/PubTator/PMC corpus size budget from "
            "official directory-listing HTML. This command only fetches or parses "
            "listing pages; it never downloads source payloads and never mutates "
            "Supabase, Storage, Postgres, or local materialization DBs."
        )
    )
    parser.add_argument(
        "--fetch-official-listings",
        action="store_true",
        help="fetch public listing HTML from NCBI/PMC; source payloads are not downloaded",
    )
    parser.add_argument(
        "--listing-dir",
        type=Path,
        help="offline listing HTML directory; files are named <source-key>.html",
    )
    parser.add_argument("--storage-used-gib", type=float, default=DEFAULT_STORAGE_USED_GIB)
    parser.add_argument("--storage-quota-gib", type=float, default=DEFAULT_STORAGE_QUOTA_GIB)
    parser.add_argument("--database-used-gib", type=float, default=DEFAULT_DATABASE_USED_GIB)
    parser.add_argument("--database-quota-gib", type=float, default=DEFAULT_DATABASE_QUOTA_GIB)
    parser.add_argument(
        "--filtered-pmc-fraction",
        type=float,
        default=DEFAULT_FILTERED_PMC_FRACTION,
        help="planning fraction of PMC OA commercial XML for the filtered-source scenario",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    if not args.fetch_official_listings and args.listing_dir is None:
        _print_report(
            _failed_report(
                "listing_source_required",
                "pass --fetch-official-listings or --listing-dir",
                network_used=False,
            ),
            compact=args.compact,
        )
        return 2

    try:
        source_entries, load_warnings = _load_listing_entries(
            listing_dir=args.listing_dir,
            fetch_official=args.fetch_official_listings,
        )
    except (OSError, URLError, TimeoutError) as exc:
        _print_report(
            _failed_report(
                "listing_fetch_failed",
                type(exc).__name__,
                network_used=args.fetch_official_listings,
            ),
            compact=args.compact,
        )
        return 2

    inventory = build_inventory(source_entries)
    report = build_budget_report(
        inventory,
        source_entries=source_entries,
        warnings=load_warnings,
        network_used=args.fetch_official_listings,
        storage_used_gib=args.storage_used_gib,
        storage_quota_gib=args.storage_quota_gib,
        database_used_gib=args.database_used_gib,
        database_quota_gib=args.database_quota_gib,
        filtered_pmc_fraction=args.filtered_pmc_fraction,
    )
    _print_report(report, compact=args.compact)
    return 0


def build_inventory(
    source_entries: Mapping[str, Sequence[ListingEntry]],
) -> dict[str, InventoryItem]:
    pubmed_baseline = _item_from_entries(
        "PubMed 2026 baseline XML",
        source_entries.get("pubmed_baseline", ()),
        source_keys=("pubmed_baseline",),
        include=lambda name: bool(re.fullmatch(r"pubmed26n\d+\.xml\.gz", name)),
        note="baseline XML gzip files only; README and md5 sidecars excluded",
    )
    pubmed_updates = _item_from_entries(
        "PubMed 2026 update XML",
        source_entries.get("pubmed_updatefiles", ()),
        source_keys=("pubmed_updatefiles",),
        include=lambda name: bool(re.fullmatch(r"pubmed26n\d+\.xml\.gz", name)),
        note="current update XML gzip files only; stats and md5 sidecars excluded",
    )
    pubtator_entries = source_entries.get("pubtator3", ())
    pubtator_selectors = _item_from_entries(
        "PubTator3 selector tables",
        pubtator_entries,
        source_keys=("pubtator3",),
        include=lambda name: name in PUBTATOR_SELECTOR_FILES,
        note="gene, mutation, relation, and bioconcept selector tables",
    )
    pubtator_bioc = _item_from_entries(
        "PubTator3 full BioC XML",
        pubtator_entries,
        source_keys=("pubtator3",),
        include=lambda name: bool(re.fullmatch(r"BioCXML\.\d+\.tar\.gz", name)),
        note="full raw BioC mirror; not needed for selector-first import",
    )
    pmc_crosswalk = _item_from_entries(
        "PMC ID crosswalk",
        source_entries.get("pmc_top", ()),
        source_keys=("pmc_top",),
        include=lambda name: name == "PMC-ids.csv.gz",
        note="PMCID/PMID/DOI crosswalk manifest",
    )
    pmc_xml = _sum_items(
        "PMC OA XML baseline packages",
        [
            _pmc_baseline_item(source_entries, "pmc_oa_comm_xml"),
            _pmc_baseline_item(source_entries, "pmc_oa_noncomm_xml"),
            _pmc_baseline_item(source_entries, "pmc_oa_other_xml"),
        ],
        note="commercial, noncommercial, and other-license XML baseline packages",
    )
    pmc_txt = _sum_items(
        "PMC OA text baseline packages",
        [
            _pmc_baseline_item(source_entries, "pmc_oa_comm_txt"),
            _pmc_baseline_item(source_entries, "pmc_oa_noncomm_txt"),
            _pmc_baseline_item(source_entries, "pmc_oa_other_txt"),
        ],
        note="commercial, noncommercial, and other-license plain-text baseline packages",
    )
    pmc_comm_xml = _pmc_baseline_item(source_entries, "pmc_oa_comm_xml")
    pubmed_all = _sum_items(
        "PubMed baseline plus current updates",
        [pubmed_baseline, pubmed_updates],
        note="compressed PubMed source mirror budget before checksum sidecars",
    )
    return {
        "pubmed_baseline": pubmed_baseline,
        "pubmed_updates": pubmed_updates,
        "pubmed_all": pubmed_all,
        "pubtator_selectors": pubtator_selectors,
        "pubtator_bioc": pubtator_bioc,
        "pmc_crosswalk": pmc_crosswalk,
        "pmc_oa_xml": pmc_xml,
        "pmc_oa_txt": pmc_txt,
        "pmc_oa_comm_xml": pmc_comm_xml,
    }


def build_budget_report(
    inventory: Mapping[str, InventoryItem],
    *,
    source_entries: Mapping[str, Sequence[ListingEntry]],
    warnings: Sequence[str],
    network_used: bool,
    storage_used_gib: float,
    storage_quota_gib: float,
    database_used_gib: float,
    database_quota_gib: float,
    filtered_pmc_fraction: float,
) -> dict[str, Any]:
    pubmed = inventory["pubmed_all"].compressed_bytes
    pubtator_selectors = inventory["pubtator_selectors"].compressed_bytes
    pubtator_bioc = inventory["pubtator_bioc"].compressed_bytes
    pmc_crosswalk = inventory["pmc_crosswalk"].compressed_bytes
    pmc_xml = inventory["pmc_oa_xml"].compressed_bytes
    pmc_txt = inventory["pmc_oa_txt"].compressed_bytes
    filtered_pmc = int(inventory["pmc_oa_comm_xml"].compressed_bytes * filtered_pmc_fraction)

    scenarios = [
        _scenario(
            "pubmed_raw_mirror",
            "PubMed baseline/update raw mirror",
            raw_source_bytes=pubmed,
            postgres_low_gib=0,
            postgres_high_gib=0,
            storage_used_gib=storage_used_gib,
            storage_quota_gib=storage_quota_gib,
            database_used_gib=database_used_gib,
            database_quota_gib=database_quota_gib,
            notes=(
                "Fits only as a near-quota raw source mirror with current usage; "
                "no room for next-baseline overlap."
            ),
        ),
        _scenario(
            "pubmed_plus_pubtator_selectors",
            "PubMed raw plus full PubTator selector tables",
            raw_source_bytes=pubmed + pubtator_selectors,
            postgres_low_gib=_gib(pubtator_selectors) * 2.0,
            postgres_high_gib=_gib(pubtator_selectors) * 5.0,
            storage_used_gib=storage_used_gib,
            storage_quota_gib=storage_quota_gib,
            database_used_gib=database_used_gib,
            database_quota_gib=database_quota_gib,
            notes=(
                "Useful selector-first path, but full selector-table Postgres import "
                "needs a separate database budget or filtering."
            ),
        ),
        _scenario(
            "pubmed_plus_filtered_pmc_oa_xml",
            "PubMed raw plus filtered PMC OA commercial XML",
            raw_source_bytes=pubmed + pmc_crosswalk + filtered_pmc,
            postgres_low_gib=0.25,
            postgres_high_gib=2.5,
            storage_used_gib=storage_used_gib,
            storage_quota_gib=storage_quota_gib,
            database_used_gib=database_used_gib,
            database_quota_gib=database_quota_gib,
            notes=(
                f"Uses {filtered_pmc_fraction:.1%} of commercial-use PMC XML as a "
                "planning placeholder; exact package set must be selected before upload."
            ),
        ),
        _scenario(
            "full_pmc_pubtator_raw_mirrors",
            "Full PubMed, PubTator BioC, and PMC OA XML+text raw mirrors",
            raw_source_bytes=pubmed + pubtator_bioc + pmc_crosswalk + pmc_xml + pmc_txt,
            postgres_low_gib=100.0,
            postgres_high_gib=300.0,
            storage_used_gib=storage_used_gib,
            storage_quota_gib=storage_quota_gib,
            database_used_gib=database_used_gib,
            database_quota_gib=database_quota_gib,
            notes="Exceeds the included Storage/database budget by design; do not mirror wholesale.",
        ),
    ]

    return {
        "mode": "pubmed_corpus_budget",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "budgeted",
        "ready_for_upload": False,
        "approval_required_before_upload": True,
        "guardrails": _guardrails(network_used=network_used),
        "capacity": {
            "storage_used_gib": round(storage_used_gib, 3),
            "storage_quota_gib": round(storage_quota_gib, 3),
            "storage_headroom_gib": round(storage_quota_gib - storage_used_gib, 3),
            "database_used_gib": round(database_used_gib, 3),
            "database_quota_gib": round(database_quota_gib, 3),
            "database_headroom_gib": round(database_quota_gib - database_used_gib, 3),
        },
        "inventory": {key: item.to_sanitized_dict() for key, item in sorted(inventory.items())},
        "source_listing_summary": {
            key: {"entry_count": len(entries)} for key, entries in sorted(source_entries.items())
        },
        "scenarios": scenarios,
        "recommendation": {
            "path": "PubMed-first filtered-source path",
            "decision": "do_not_upload_without_approval",
            "reason": (
                "Current storage headroom is too small for PubMed raw source plus "
                "version overlap or any PMC/PubTator expansion."
            ),
            "next_step": (
                "Stage on an explicit non-C volume, filter/derive the Eamos corpus, "
                "then ask for approval before any bulk Supabase upload or overage."
            ),
        },
        "official_listing_urls": {source.key: source.url for source in LISTING_SOURCES},
        "warnings": list(warnings),
    }


def _scenario(
    scenario_id: str,
    label: str,
    *,
    raw_source_bytes: int,
    postgres_low_gib: float,
    postgres_high_gib: float,
    storage_used_gib: float,
    storage_quota_gib: float,
    database_used_gib: float,
    database_quota_gib: float,
    notes: str,
) -> dict[str, Any]:
    raw_source_gib = _gib(raw_source_bytes)
    storage_after = storage_used_gib + raw_source_gib
    storage_overage = max(storage_after - storage_quota_gib, 0.0)
    version_overlap_after = storage_used_gib + (raw_source_gib * 2)
    db_after_high = database_used_gib + postgres_high_gib
    storage_risk = _risk(storage_after, storage_quota_gib, reserve_gib=10.0)
    database_risk = _risk(db_after_high, database_quota_gib, reserve_gib=1.0)
    approval = (
        storage_overage > 0
        or version_overlap_after > storage_quota_gib
        or db_after_high > database_quota_gib
        or storage_risk != "green"
    )
    return {
        "id": scenario_id,
        "label": label,
        "raw_source_compressed_gib": round(raw_source_gib, 3),
        "storage_after_upload_gib": round(storage_after, 3),
        "storage_headroom_after_upload_gib": round(storage_quota_gib - storage_after, 3),
        "storage_overage_gib": round(storage_overage, 3),
        "version_overlap_storage_after_gib": round(version_overlap_after, 3),
        "postgres_table_index_estimate_gib": {
            "low": round(postgres_low_gib, 3),
            "high": round(postgres_high_gib, 3),
            "database_after_high_gib": round(db_after_high, 3),
        },
        "risk": {"storage": storage_risk, "database": database_risk},
        "approval_required": approval,
        "go_no_go": "hold_for_approval" if approval else "go_after_written_runbook",
        "monthly_raw_storage_egress_gib": 0,
        "operator_reseed_egress_gib": round(raw_source_gib, 3),
        "notes": notes,
    }


def _load_listing_entries(
    *,
    listing_dir: Path | None,
    fetch_official: bool,
) -> tuple[dict[str, list[ListingEntry]], list[str]]:
    warnings: list[str] = []
    result: dict[str, list[ListingEntry]] = {}
    for source in LISTING_SOURCES:
        if listing_dir is not None:
            listing_path = listing_dir / f"{source.key}.html"
            if not listing_path.exists():
                warnings.append(f"listing_missing:{source.key}")
                result[source.key] = []
                continue
            html = listing_path.read_text(encoding="utf-8")
        elif fetch_official:
            html = _fetch_listing_html(source.url)
        else:
            result[source.key] = []
            continue
        result[source.key] = parse_apache_listing(html)
    return result, warnings


def parse_apache_listing(html: str) -> list[ListingEntry]:
    entries: list[ListingEntry] = []
    pattern = re.compile(
        r'<a\s+href="[^"]+">(?P<name>[^<]+)</a>\s+'
        r"(?P<date>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+"
        r"(?P<size>[0-9.]+[KMGT]?)\s*",
        re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        name = match.group("name").strip()
        if name in {"Parent Directory", "README.txt", "readme.txt"}:
            continue
        entries.append(
            ListingEntry(
                name=name,
                last_modified=match.group("date"),
                size_bytes=_parse_listing_size(match.group("size")),
            )
        )
    return entries


def _fetch_listing_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "eamos-supa-lit-0-budget/1.0"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - public NCBI listings only.
        return response.read().decode("utf-8", errors="replace")


def _parse_listing_size(value: str) -> int:
    match = re.fullmatch(r"(?P<num>[0-9]+(?:\.[0-9]+)?)(?P<unit>[KMGT]?)", value.strip())
    if not match:
        return 0
    number = float(match.group("num"))
    multiplier = {
        "": 1,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
    }[match.group("unit").upper()]
    return int(number * multiplier)


def _item_from_entries(
    label: str,
    entries: Iterable[ListingEntry],
    *,
    source_keys: tuple[str, ...],
    include: Callable[[str], bool],
    note: str,
) -> InventoryItem:
    selected = [entry for entry in entries if include(entry.name)]
    return InventoryItem(
        label=label,
        file_count=len(selected),
        compressed_bytes=sum(entry.size_bytes for entry in selected),
        source_keys=source_keys,
        note=note,
    )


def _pmc_baseline_item(
    source_entries: Mapping[str, Sequence[ListingEntry]],
    key: str,
) -> InventoryItem:
    return _item_from_entries(
        key.replace("_", " "),
        source_entries.get(key, ()),
        source_keys=(key,),
        include=lambda name: bool(re.fullmatch(r".*\.baseline\.\d{4}-\d{2}-\d{2}\.tar\.gz", name)),
        note="baseline tar.gz packages only; file lists and incrementals excluded",
    )


def _sum_items(label: str, items: Sequence[InventoryItem], *, note: str) -> InventoryItem:
    source_keys: list[str] = []
    for item in items:
        source_keys.extend(item.source_keys)
    return InventoryItem(
        label=label,
        file_count=sum(item.file_count for item in items),
        compressed_bytes=sum(item.compressed_bytes for item in items),
        source_keys=tuple(source_keys),
        note=note,
    )


def _risk(after_gib: float, quota_gib: float, *, reserve_gib: float) -> str:
    if after_gib > quota_gib:
        return "red"
    if quota_gib - after_gib < reserve_gib:
        return "yellow"
    return "green"


def _gib(size_bytes: int) -> float:
    return size_bytes / BYTES_PER_GIB


def _round_gib(size_bytes: int) -> float:
    return round(_gib(size_bytes), 3)


def _guardrails(*, network_used: bool) -> dict[str, Any]:
    return {
        "network": {
            "used": network_used,
            "provider": "official_listing_html_only" if network_used else None,
        },
        "source_payload_download": "not_used",
        "supabase_storage_mutation": "not_used",
        "supabase_database_mutation": "not_used",
        "startup_download": "not_used",
        "request_time_materialization": "not_used",
        "patient_data": "not_used",
        "secrets_in_output": "blocked",
        "local_paths_in_output": "blocked",
        "private_object_paths_in_output": "blocked",
        "raw_full_text_in_output": "blocked",
    }


def _failed_report(code: str, message: str, *, network_used: bool) -> dict[str, Any]:
    return {
        "mode": "pubmed_corpus_budget",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "ready_for_upload": False,
        "approval_required_before_upload": True,
        "code": code,
        "message": message,
        "guardrails": _guardrails(network_used=network_used),
    }


def _print_report(report: dict[str, Any], *, compact: bool) -> None:
    print(json.dumps(report, indent=None if compact else 2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
