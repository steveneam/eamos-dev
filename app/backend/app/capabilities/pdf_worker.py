from __future__ import annotations

import argparse
from functools import lru_cache
import json
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
from time import perf_counter
from typing import Any

from app.capabilities.models import RuntimeProbeV1
from app.core.config import Settings
from app.services.pdf_text import PdfTextLimits

MAX_WORKER_MEMORY_MB = 2048
MAX_WORKER_CPU_SECONDS = 60
MAX_WORKER_OUTPUT_BYTES = 20_000_000


class PdfWorkerError(RuntimeError):
    pass


class PdfWorkerDeadlineExceeded(PdfWorkerError):
    pass


class PdfTextWorker:
    """Run untrusted PDF parsing in a killable, resource-capped child process."""

    def __init__(
        self,
        *,
        backend_root: Path,
        timeout_seconds: float,
        memory_mb: int,
        cpu_seconds: int,
        max_output_bytes: int,
        executable: Path | None = None,
    ) -> None:
        self.backend_root = backend_root.resolve()
        self.timeout_seconds = max(0.05, min(float(timeout_seconds), 120.0))
        self.memory_mb = max(256, min(int(memory_mb), MAX_WORKER_MEMORY_MB))
        self.cpu_seconds = max(1, min(int(cpu_seconds), MAX_WORKER_CPU_SECONDS))
        self.max_output_bytes = max(
            1_000_000,
            min(int(max_output_bytes), MAX_WORKER_OUTPUT_BYTES),
        )
        # Keep the virtualenv launcher path; resolving its symlink would bypass
        # the environment that contains the pinned PDF runtime.
        self.executable = Path(executable or sys.executable).absolute()

    @classmethod
    def from_settings(cls, settings: Settings) -> "PdfTextWorker":
        response_deadline = float(settings.paper_variants_pdf_timeout_seconds)
        worker_deadline = max(0.05, response_deadline - min(0.25, response_deadline / 4))
        return cls(
            backend_root=settings.backend_root,
            timeout_seconds=worker_deadline,
            memory_mb=settings.paper_pdf_worker_memory_mb,
            cpu_seconds=settings.paper_pdf_worker_cpu_seconds,
            max_output_bytes=settings.paper_pdf_worker_max_output_bytes,
        )

    def extract(
        self,
        file_path: Any,
        *,
        engine: str,
        limits: PdfTextLimits | None = None,
    ) -> dict[str, Any]:
        path = Path(file_path).resolve()
        normalized_engine = str(engine or "").strip().lower()
        if not path.is_file():
            return _empty_result(normalized_engine, "pdf_file_missing")
        active_limits = limits or PdfTextLimits()
        command = self._base_command()
        command.extend(
            [
                "--file",
                str(path),
                "--engine",
                normalized_engine,
                "--max-file-bytes",
                str(active_limits.max_file_bytes),
                "--max-pages",
                str(active_limits.max_pages),
                "--max-objects",
                str(active_limits.max_objects),
                "--max-page-characters",
                str(active_limits.max_page_characters),
                "--max-total-characters",
                str(active_limits.max_total_characters),
            ]
        )
        payload = self._run(command, timeout_seconds=self.timeout_seconds)
        return _validate_result(payload, limits=active_limits, expected_engine=normalized_engine)

    def _base_command(self) -> list[str]:
        return [
            str(self.executable),
            "-m",
            "app.capabilities.pdf_worker",
            "--memory-mb",
            str(self.memory_mb),
            "--cpu-seconds",
            str(self.cpu_seconds),
        ]

    def _run(self, command: list[str], *, timeout_seconds: float) -> object:
        try:
            completed = subprocess.run(
                command,
                cwd=self.backend_root,
                env={
                    "HOME": "/tmp",
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONIOENCODING": "utf-8",
                },
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise PdfWorkerDeadlineExceeded("pdf_worker_deadline_exceeded") from exc
        except OSError as exc:
            raise PdfWorkerError("pdf_worker_start_failed") from exc
        if completed.returncode != 0:
            raise PdfWorkerError("pdf_worker_failed")
        if len(completed.stdout) > self.max_output_bytes:
            raise PdfWorkerError("pdf_worker_output_limit_exceeded")
        try:
            return json.loads(completed.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PdfWorkerError("pdf_worker_response_invalid") from exc


@lru_cache(maxsize=8)
def run_pdf_worker_preflight(
    *,
    backend_root_value: str,
    fixture_path_value: str,
    executable_value: str,
    memory_mb: int,
    cpu_seconds: int,
    max_output_bytes: int,
) -> RuntimeProbeV1:
    started = perf_counter()
    worker = PdfTextWorker(
        backend_root=Path(backend_root_value),
        timeout_seconds=5.0,
        memory_mb=memory_mb,
        cpu_seconds=cpu_seconds,
        max_output_bytes=max_output_bytes,
        executable=Path(executable_value),
    )
    requirement = "restore the killable resource-capped PDF worker and deadline probe"
    try:
        selectable = worker.extract(Path(fixture_path_value), engine="pdfium")
        if selectable["page_count"] < 1 or not selectable["text"]:
            raise PdfWorkerError("pdf_worker_selectable_probe_failed")
        with tempfile.TemporaryDirectory(prefix="eamos-pdf-worker-preflight-") as directory:
            from pypdf import PdfWriter

            blank_path = Path(directory) / "blank.pdf"
            malformed_path = Path(directory) / "malformed.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            with blank_path.open("wb") as handle:
                writer.write(handle)
            malformed_path.write_bytes(b"%PDF-not-a-valid-document")
            blank = worker.extract(blank_path, engine="pdfium")
            malformed = worker.extract(malformed_path, engine="pdfium")
        if "ocr_required:page:1" not in blank["warnings"]:
            raise PdfWorkerError("pdf_worker_blank_probe_failed")
        if malformed["page_count"] != 0 or not malformed["warnings"]:
            raise PdfWorkerError("pdf_worker_malformed_probe_failed")
        deadline_command = worker._base_command()
        deadline_command.extend(["--self-test-delay-ms", "250"])
        try:
            worker._run(deadline_command, timeout_seconds=0.05)
        except PdfWorkerDeadlineExceeded:
            pass
        else:
            raise PdfWorkerError("pdf_worker_deadline_probe_failed")
    except Exception as exc:
        return RuntimeProbeV1(
            probe_id="paper.pdf_worker.functional.v1",
            status="failed",
            executed=True,
            elapsed_ms=_elapsed_ms(started),
            validation_matrix_id="paper-pdf-worker-runtime-v1",
            warnings=[f"PDF worker preflight failed with {type(exc).__name__}"],
            requirements=[requirement],
        )
    return RuntimeProbeV1(
        probe_id="paper.pdf_worker.functional.v1",
        status="passed",
        executed=True,
        elapsed_ms=_elapsed_ms(started),
        validation_matrix_id="paper-pdf-worker-runtime-v1",
    )


def _worker_main(args: argparse.Namespace) -> int:
    _apply_resource_limits(memory_mb=args.memory_mb, cpu_seconds=args.cpu_seconds)
    if args.self_test_delay_ms:
        time.sleep(min(args.self_test_delay_ms, 2_000) / 1000)
        sys.stdout.write("{}")
        return 0
    if args.file is None or args.engine is None:
        return 2
    from app.services.pdf_text import extract_pdf_text

    limits = PdfTextLimits(
        max_file_bytes=args.max_file_bytes,
        max_pages=args.max_pages,
        max_objects=args.max_objects,
        max_page_characters=args.max_page_characters,
        max_total_characters=args.max_total_characters,
    )
    result = extract_pdf_text(args.file, engine=args.engine, limits=limits)
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


def _apply_resource_limits(*, memory_mb: int, cpu_seconds: int) -> None:
    memory_bytes = max(256, min(memory_mb, MAX_WORKER_MEMORY_MB)) * 1024 * 1024
    cpu_limit = max(1, min(cpu_seconds, MAX_WORKER_CPU_SECONDS))
    limits = (
        (resource.RLIMIT_AS, memory_bytes),
        (resource.RLIMIT_CPU, cpu_limit),
        (resource.RLIMIT_NOFILE, 64),
        (resource.RLIMIT_CORE, 0),
    )
    for key, value in limits:
        resource.setrlimit(key, (value, value))
        if resource.getrlimit(key) != (value, value):
            raise RuntimeError("pdf_worker_resource_limit_failed")


def _validate_result(
    payload: object,
    *,
    limits: PdfTextLimits,
    expected_engine: str,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PdfWorkerError("pdf_worker_response_invalid")
    required = {"text", "pages", "page_count", "engine", "engine_version", "metadata", "warnings"}
    if set(payload) != required:
        raise PdfWorkerError("pdf_worker_response_invalid")
    text = payload["text"]
    pages = payload["pages"]
    warnings = payload["warnings"]
    metadata = payload["metadata"]
    if not isinstance(text, str) or len(text) > limits.max_total_characters:
        raise PdfWorkerError("pdf_worker_response_invalid")
    if not isinstance(pages, list) or len(pages) > limits.max_pages:
        raise PdfWorkerError("pdf_worker_response_invalid")
    if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
        raise PdfWorkerError("pdf_worker_response_invalid")
    if not isinstance(metadata, dict) or payload["engine"] != expected_engine:
        raise PdfWorkerError("pdf_worker_response_invalid")
    if payload["page_count"] != len(pages):
        raise PdfWorkerError("pdf_worker_response_invalid")
    return payload


def _empty_result(engine: str, warning: str) -> dict[str, Any]:
    return {
        "text": "",
        "pages": [],
        "page_count": 0,
        "engine": engine,
        "engine_version": "unavailable",
        "metadata": {},
        "warnings": [warning],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--engine", choices=("pdfium", "pypdf"))
    parser.add_argument("--memory-mb", type=int, default=1536)
    parser.add_argument("--cpu-seconds", type=int, default=30)
    parser.add_argument("--max-file-bytes", type=int, default=50_000_000)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--max-objects", type=int, default=200_000)
    parser.add_argument("--max-page-characters", type=int, default=500_000)
    parser.add_argument("--max-total-characters", type=int, default=2_000_000)
    parser.add_argument("--self-test-delay-ms", type=int, default=0)
    return parser


def _elapsed_ms(started: float) -> float:
    return round(max(0.0, (perf_counter() - started) * 1000), 3)


if __name__ == "__main__":
    raise SystemExit(_worker_main(_parser().parse_args()))
