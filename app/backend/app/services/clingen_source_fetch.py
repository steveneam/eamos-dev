from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any

import httpx

from app.core.config import Settings

EREPO_CLASSIFICATIONS_FILENAME = "clingen-erepo-classifications.jsonl"
CSPEC_ENTITIES_FILENAME = "clingen-cspec-entities.jsonl"
CSPEC_SERVICE_FILENAME = "clingen-cspec-service.json"
DEFAULT_EREPO_PAGE_SIZE = 500
DEFAULT_CSPEC_PAGE_SIZE = 250
DEFAULT_CSPEC_DETAIL = "high"
DEFAULT_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class ClinGenSourceFetchResult:
    status: str
    fetched_at: str
    erepo_classification_count: int = 0
    erepo_page_count: int = 0
    cspec_entity_count: int = 0
    cspec_page_count: int = 0
    cspec_entity_type_counts: dict[str, int] = field(default_factory=dict)
    output_files: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.status == "ready"

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "status": self.status,
            "fetched_at": self.fetched_at,
            "erepo_classification_count": self.erepo_classification_count,
            "erepo_page_count": self.erepo_page_count,
            "cspec_entity_count": self.cspec_entity_count,
            "cspec_page_count": self.cspec_page_count,
            "cspec_entity_type_counts": dict(self.cspec_entity_type_counts),
            "output_files": dict(self.output_files),
            "warnings": list(self.warnings),
            "startup_download_allowed": False,
            "request_time_materialization_allowed": False,
            "operator_initiated_download": True,
            "secret_values_emitted": False,
            "local_path_values_emitted": False,
            "raw_source_rows_emitted": False,
        }


class ClinGenSourceFetchError(RuntimeError):
    pass


def fetch_clingen_source_snapshots(
    settings: Settings,
    *,
    output_dir: Path,
    include_erepo: bool = True,
    include_cspec: bool = True,
    erepo_page_size: int = DEFAULT_EREPO_PAGE_SIZE,
    cspec_page_size: int = DEFAULT_CSPEC_PAGE_SIZE,
    cspec_detail: str = DEFAULT_CSPEC_DETAIL,
    cspec_entity_types: Sequence[str] | None = None,
    max_pages: int | None = None,
    force: bool = False,
    timeout_seconds: float = 30.0,
    retries: int = 3,
    backoff_seconds: float = 0.5,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> ClinGenSourceFetchResult:
    if not include_erepo and not include_cspec:
        return ClinGenSourceFetchResult(
            status="nothing_requested",
            fetched_at=_utc_now(),
            warnings=("no_clingen_sources_requested",),
        )

    resolved_output_dir = _resolve_path(settings, output_dir)
    output_files = _target_files(
        resolved_output_dir,
        include_erepo=include_erepo,
        include_cspec=include_cspec,
    )
    existing = [path.name for path in output_files.values() if path.exists()]
    if existing and not force:
        return ClinGenSourceFetchResult(
            status="destination_exists",
            fetched_at=_utc_now(),
            output_files={key: path.name for key, path in output_files.items()},
            warnings=("use_force_to_replace_existing_clingen_source_snapshot",),
        )

    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    own_client = client is None
    http_client = client or httpx.Client(follow_redirects=True)
    temp_paths: list[Path] = []
    warnings: list[str] = []
    fetched_at = _utc_now()
    erepo_count = 0
    erepo_pages = 0
    cspec_count = 0
    cspec_pages = 0
    cspec_counts: dict[str, int] = {}
    try:
        if include_erepo:
            erepo_temp = _temp_path(output_files["erepo_classifications"])
            temp_paths.append(erepo_temp)
            erepo_count, erepo_pages = _fetch_erepo_classifications(
                http_client,
                settings=settings,
                destination=erepo_temp,
                page_size=erepo_page_size,
                max_pages=max_pages,
                timeout_seconds=timeout_seconds,
                retries=retries,
                backoff_seconds=backoff_seconds,
                sleep=sleep,
                warnings=warnings,
            )
        if include_cspec:
            service_temp = _temp_path(output_files["cspec_service"])
            entities_temp = _temp_path(output_files["cspec_entities"])
            temp_paths.extend([service_temp, entities_temp])
            cspec_count, cspec_pages, cspec_counts = _fetch_cspec_entities(
                http_client,
                settings=settings,
                service_destination=service_temp,
                entity_destination=entities_temp,
                page_size=cspec_page_size,
                detail=cspec_detail,
                entity_types=cspec_entity_types,
                max_pages=max_pages,
                timeout_seconds=timeout_seconds,
                retries=retries,
                backoff_seconds=backoff_seconds,
                sleep=sleep,
                warnings=warnings,
            )
        for key, path in output_files.items():
            temp_path = _temp_path(path)
            if temp_path.exists():
                temp_path.replace(path)
    except Exception:
        for path in temp_paths:
            path.unlink(missing_ok=True)
        raise
    finally:
        if own_client:
            http_client.close()

    return ClinGenSourceFetchResult(
        status="ready",
        fetched_at=fetched_at,
        erepo_classification_count=erepo_count,
        erepo_page_count=erepo_pages,
        cspec_entity_count=cspec_count,
        cspec_page_count=cspec_pages,
        cspec_entity_type_counts=cspec_counts,
        output_files={key: path.name for key, path in output_files.items()},
        warnings=tuple(_dedupe(warnings)),
    )


def _fetch_erepo_classifications(
    client: httpx.Client,
    *,
    settings: Settings,
    destination: Path,
    page_size: int,
    max_pages: int | None,
    timeout_seconds: float,
    retries: int,
    backoff_seconds: float,
    sleep: Callable[[float], None],
    warnings: list[str],
) -> tuple[int, int]:
    count = 0
    pages = 0
    endpoint = f"{settings.clingen_erepo_base_url.rstrip('/')}/api/summary/classifications"
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for page in _page_numbers(max_pages):
            payload = _fetch_json(
                client,
                endpoint,
                params={"pg": page, "pgSize": max(1, int(page_size))},
                timeout_seconds=timeout_seconds,
                retries=retries,
                backoff_seconds=backoff_seconds,
                sleep=sleep,
            )
            records = _records_from_payload(payload)
            if not records:
                break
            pages += 1
            for record in records:
                handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
                handle.write("\n")
                count += 1
    if count == 0:
        warnings.append("clingen_erepo_no_classifications_fetched")
    return count, pages


def _fetch_cspec_entities(
    client: httpx.Client,
    *,
    settings: Settings,
    service_destination: Path,
    entity_destination: Path,
    page_size: int,
    detail: str,
    entity_types: Sequence[str] | None,
    max_pages: int | None,
    timeout_seconds: float,
    retries: int,
    backoff_seconds: float,
    sleep: Callable[[float], None],
    warnings: list[str],
) -> tuple[int, int, dict[str, int]]:
    base = settings.clingen_cspec_base_url.rstrip("/")
    service_payload = _fetch_json(
        client,
        f"{base}/srvc",
        params={},
        timeout_seconds=timeout_seconds,
        retries=retries,
        backoff_seconds=backoff_seconds,
        sleep=sleep,
    )
    service_destination.write_text(
        json.dumps(service_payload, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    selected_types = list(entity_types or _cspec_entity_types(service_payload))
    if not selected_types:
        warnings.append("clingen_cspec_no_entity_types_discovered")
        return 0, 0, {}

    page_size = max(1, min(int(page_size), DEFAULT_CSPEC_PAGE_SIZE))
    detail = detail if detail in {"low", "med", "high"} else DEFAULT_CSPEC_DETAIL
    total = 0
    pages = 0
    counts: dict[str, int] = {}
    with entity_destination.open("w", encoding="utf-8", newline="\n") as handle:
        for entity_type in selected_types:
            type_count = 0
            endpoint = f"{base}/{entity_type}/id"
            for page in _page_numbers(max_pages):
                payload = _fetch_json(
                    client,
                    endpoint,
                    params={"pg": page, "pgSize": page_size, "detail": detail},
                    timeout_seconds=timeout_seconds,
                    retries=retries,
                    backoff_seconds=backoff_seconds,
                    sleep=sleep,
                )
                records = _records_from_payload(payload)
                if not records:
                    break
                pages += 1
                for record in records:
                    handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
                    handle.write("\n")
                    total += 1
                    type_count += 1
            counts[entity_type] = type_count
            if type_count == 0:
                warnings.append(f"clingen_cspec_no_rows:{entity_type}")
    if total == 0:
        warnings.append("clingen_cspec_no_entities_fetched")
    return total, pages, counts


def _fetch_json(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, Any],
    timeout_seconds: float,
    retries: int,
    backoff_seconds: float,
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(max(0, int(retries)) + 1):
        try:
            response = client.get(url, params=params, timeout=timeout_seconds)
            if response.status_code == 404:
                return {"data": []}
            if response.status_code in DEFAULT_RETRY_STATUS_CODES:
                if attempt < retries:
                    _sleep_before_retry(response, attempt, backoff_seconds, sleep)
                    continue
            response.raise_for_status()
            decoded = response.json()
            return decoded if isinstance(decoded, dict) else {"data": decoded}
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                _sleep_before_retry(None, attempt, backoff_seconds, sleep)
                continue
            break
    raise ClinGenSourceFetchError(f"ClinGen source fetch failed for {url}") from last_error


def _sleep_before_retry(
    response: httpx.Response | None,
    attempt: int,
    backoff_seconds: float,
    sleep: Callable[[float], None],
) -> None:
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after is not None:
        try:
            delay = max(0.0, float(retry_after))
        except ValueError:
            delay = backoff_seconds * (2**attempt)
    else:
        delay = backoff_seconds * (2**attempt)
    if delay > 0:
        sleep(delay)


def _records_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    status = payload.get("status")
    if isinstance(status, dict) and int(status.get("code") or 0) == 404:
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return [record for record in data if isinstance(record, dict)]
    return []


def _cspec_entity_types(payload: dict[str, Any]) -> list[str]:
    data = payload.get("data")
    ent_types = data.get("entTypes") if isinstance(data, dict) else None
    if not isinstance(ent_types, dict):
        return []
    return sorted(str(entity_type) for entity_type in ent_types)


def _target_files(
    output_dir: Path,
    *,
    include_erepo: bool,
    include_cspec: bool,
) -> dict[str, Path]:
    result: dict[str, Path] = {}
    if include_erepo:
        result["erepo_classifications"] = output_dir / EREPO_CLASSIFICATIONS_FILENAME
    if include_cspec:
        result["cspec_entities"] = output_dir / CSPEC_ENTITIES_FILENAME
        result["cspec_service"] = output_dir / CSPEC_SERVICE_FILENAME
    return result


def _temp_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.tmp")


def _page_numbers(max_pages: int | None):
    page = 1
    while max_pages is None or page <= max_pages:
        yield page
        page += 1


def _resolve_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


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
