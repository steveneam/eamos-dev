from __future__ import annotations

import gzip
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.services.protein_annotation import (
    HMMPRESS_SUFFIXES,
    LocalHmmerRunner,
    resolve_executable,
    resolve_protein_runtime_path,
)


@dataclass(frozen=True)
class ProteinRuntimePreparationResult:
    ready: bool
    status: str
    hmmscan_available: bool
    hmmpress_available: bool
    pfam_hmm_present: bool
    pfam_hmm_extracted: bool
    hmmpress_ran: bool
    missing_index_count: int
    warnings: tuple[str, ...] = ()


def prepare_protein_annotation_runtime(
    settings: Settings,
    *,
    force_hmmpress: bool = False,
) -> ProteinRuntimePreparationResult:
    hmmscan = resolve_executable(settings.protein_annotation_hmmscan_path)
    hmmpress = resolve_executable(settings.protein_annotation_hmmpress_path)
    pfam_hmm = resolve_protein_runtime_path(settings, settings.protein_annotation_pfam_hmm_path)
    pfam_hmm_gz = resolve_protein_runtime_path(
        settings, settings.protein_annotation_pfam_hmm_gz_path
    )

    if hmmscan is None:
        return _result("hmmscan_executable_missing", hmmscan=False, hmmpress=hmmpress is not None)
    if hmmpress is None:
        return _result("hmmpress_executable_missing", hmmscan=True, hmmpress=False)

    extracted = False
    if not pfam_hmm.is_file():
        if not pfam_hmm_gz.is_file():
            return _result(
                "pfam_hmm_source_missing",
                hmmscan=True,
                hmmpress=True,
            )
        _extract_gzip_atomic(source=pfam_hmm_gz, destination=pfam_hmm)
        extracted = True

    missing_indexes = _missing_pfam_indexes(pfam_hmm)
    hmmpress_ran = False
    if force_hmmpress or missing_indexes:
        completed = subprocess.run(
            [hmmpress, "-f", str(pfam_hmm)],
            capture_output=True,
            text=True,
            timeout=settings.protein_annotation_hmmpress_timeout_seconds,
            check=False,
        )
        hmmpress_ran = True
        if completed.returncode != 0:
            return _result(
                "hmmpress_failed",
                hmmscan=True,
                hmmpress=True,
                pfam_hmm_present=pfam_hmm.is_file(),
                pfam_hmm_extracted=extracted,
                hmmpress_ran=True,
                warnings=("hmmpress_failed_no_live_protein_api_fallback",),
            )

    runtime = LocalHmmerRunner(settings).status()
    if not runtime.ready:
        return _result(
            runtime.reason or "protein_annotation_runtime_unavailable",
            hmmscan=True,
            hmmpress=True,
            pfam_hmm_present=pfam_hmm.is_file(),
            pfam_hmm_extracted=extracted,
            hmmpress_ran=hmmpress_ran,
            missing_index_count=len(runtime.missing_indexes),
            warnings=runtime.warnings,
        )

    return _result(
        "ready",
        ready=True,
        hmmscan=True,
        hmmpress=True,
        pfam_hmm_present=True,
        pfam_hmm_extracted=extracted,
        hmmpress_ran=hmmpress_ran,
        missing_index_count=0,
    )


def _missing_pfam_indexes(pfam_hmm: Path) -> tuple[Path, ...]:
    return tuple(
        pfam_hmm.with_suffix(pfam_hmm.suffix + suffix)
        for suffix in HMMPRESS_SUFFIXES
        if not pfam_hmm.with_suffix(pfam_hmm.suffix + suffix).is_file()
    )


def _extract_gzip_atomic(*, source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            with gzip.open(source, "rb") as gzip_file:
                shutil.copyfileobj(gzip_file, temp_file, length=1024 * 1024)
        Path(temp_name).replace(destination)
    except Exception:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        raise


def _result(
    status: str,
    *,
    ready: bool = False,
    hmmscan: bool,
    hmmpress: bool,
    pfam_hmm_present: bool = False,
    pfam_hmm_extracted: bool = False,
    hmmpress_ran: bool = False,
    missing_index_count: int = 0,
    warnings: tuple[str, ...] = (),
) -> ProteinRuntimePreparationResult:
    return ProteinRuntimePreparationResult(
        ready=ready,
        status=status,
        hmmscan_available=hmmscan,
        hmmpress_available=hmmpress,
        pfam_hmm_present=pfam_hmm_present,
        pfam_hmm_extracted=pfam_hmm_extracted,
        hmmpress_ran=hmmpress_ran,
        missing_index_count=missing_index_count,
        warnings=warnings,
    )
