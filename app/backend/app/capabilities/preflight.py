from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter
import tempfile

from app.capabilities.models import RuntimeProbeV1


@dataclass(frozen=True)
class PackagePreflight:
    installed_version: str | None
    probe: RuntimeProbeV1


@lru_cache(maxsize=1)
def run_package_preflights(fixtures_root_value: str) -> dict[str, PackagePreflight]:
    fixtures_root = Path(fixtures_root_value)
    return {
        "primer3-py": _run_probe(
            distribution="primer3-py",
            probe_id="primer3.functional.sanger_qpcr.v1",
            matrix_id="workbench-primer3-runtime-v1",
            requirement="install primer3-py==2.3.0 and preserve its GPLv2 distribution terms",
            callback=_probe_primer3,
        ),
        "biopython": _run_probe(
            distribution="biopython",
            probe_id="biopython.functional.ab1.v1",
            matrix_id="workbench-ab1-runtime-v1",
            requirement="install biopython==1.87 with the checked AB1 parser",
            callback=lambda: _probe_biopython(fixtures_root),
        ),
        "pysam": _run_probe(
            distribution="pysam",
            probe_id="pysam.functional.tabix_vcf.v1",
            matrix_id="batch-pysam-runtime-v1",
            requirement="install pysam==0.24.0 with HTSlib VCF and tabix support",
            callback=_probe_pysam,
        ),
        "pypdfium2": _run_probe(
            distribution="pypdfium2",
            probe_id="pdfium.functional.document_matrix.v1",
            matrix_id="paper-pdfium-runtime-v1",
            requirement="install pypdfium2==5.12.1 and preserve bundled PDFium notices",
            callback=lambda: _probe_pdfium(fixtures_root),
        ),
        "pypdf": _run_probe(
            distribution="pypdf",
            probe_id="pypdf.functional.fallback.v1",
            matrix_id="paper-pypdf-fallback-v1",
            requirement="install the pinned pypdf fallback",
            callback=lambda: _probe_pypdf(fixtures_root),
        ),
    }


def _run_probe(
    *,
    distribution: str,
    probe_id: str,
    matrix_id: str,
    requirement: str,
    callback,
) -> PackagePreflight:
    started = perf_counter()
    try:
        installed_version = version(distribution)
    except PackageNotFoundError:
        return PackagePreflight(
            installed_version=None,
            probe=RuntimeProbeV1(
                probe_id=probe_id,
                status="unavailable",
                executed=True,
                elapsed_ms=_elapsed_ms(started),
                validation_matrix_id=matrix_id,
                requirements=[requirement],
            ),
        )
    try:
        callback()
    except Exception as exc:
        return PackagePreflight(
            installed_version=installed_version,
            probe=RuntimeProbeV1(
                probe_id=probe_id,
                status="failed",
                executed=True,
                elapsed_ms=_elapsed_ms(started),
                validation_matrix_id=matrix_id,
                warnings=[f"functional probe failed with {type(exc).__name__}"],
                requirements=[requirement],
            ),
        )
    return PackagePreflight(
        installed_version=installed_version,
        probe=RuntimeProbeV1(
            probe_id=probe_id,
            status="passed",
            executed=True,
            elapsed_ms=_elapsed_ms(started),
            validation_matrix_id=matrix_id,
        ),
    )


def _probe_primer3() -> None:
    import primer3

    bases = "ACGT"
    template = "".join(
        bases[value % 4]
        for block in range(50)
        for value in sha256(f"eamos-primer3-{block}".encode()).digest()
    )[:1000]
    profiles = {
        "sanger": ([300, 500], {"PRIMER_MAX_POLY_X": 5, "PRIMER_GC_CLAMP": 0}),
        "qpcr": (
            [80, 180],
            {"PRIMER_MAX_POLY_X": 4, "PRIMER_GC_CLAMP": 1, "PRIMER_MAX_END_GC": 3},
        ),
    }
    for mode, (product_range, overrides) in profiles.items():
        global_args = {
            "PRIMER_TASK": "generic",
            "PRIMER_NUM_RETURN": 1,
            "PRIMER_OPT_SIZE": 20,
            "PRIMER_MIN_SIZE": 18,
            "PRIMER_MAX_SIZE": 25,
            "PRIMER_MIN_TM": 58.0,
            "PRIMER_OPT_TM": 60.0,
            "PRIMER_MAX_TM": 62.0,
            "PRIMER_MIN_GC": 35.0,
            "PRIMER_MAX_GC": 70.0,
            "PRIMER_MAX_NS_ACCEPTED": 0,
            "PRIMER_THERMODYNAMIC_OLIGO_ALIGNMENT": 1,
            "PRIMER_PRODUCT_SIZE_RANGE": [product_range],
            **overrides,
        }
        result = primer3.bindings.design_primers(
            seq_args={
                "SEQUENCE_ID": f"runtime-preflight-{mode}",
                "SEQUENCE_TEMPLATE": template,
                "SEQUENCE_TARGET": [500, 1],
            },
            global_args=global_args,
        )
        if int(result.get("PRIMER_PAIR_NUM_RETURNED", 0)) < 1:
            raise RuntimeError("primer3_profile_returned_no_pair")


def _probe_biopython(fixtures_root: Path) -> None:
    from app.services.trace_parser import parse_ab1_bytes

    trace = parse_ab1_bytes((fixtures_root / "workbench" / "rpe65_vus1.ab1").read_bytes())
    if not trace.sequence or not trace.base_calls:
        raise RuntimeError("ab1_probe_returned_no_calls")


def _probe_pysam() -> None:
    import pysam

    vcf = (
        "##fileformat=VCFv4.2\n"
        "##contig=<ID=1,length=1000>\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t101\trs-preflight\tA\tG\t60\tPASS\t.\n"
    )
    with tempfile.TemporaryDirectory(prefix="eamos-pysam-preflight-") as directory:
        source = Path(directory) / "probe.vcf"
        compressed = Path(directory) / "probe.vcf.gz"
        source.write_text(vcf, encoding="ascii")
        pysam.tabix_compress(str(source), str(compressed), force=True)
        pysam.tabix_index(str(compressed), preset="vcf", force=True)
        with pysam.VariantFile(str(compressed)) as reader:
            rows = list(reader.fetch("1", 100, 101))
    if len(rows) != 1 or rows[0].id != "rs-preflight":
        raise RuntimeError("pysam_tabix_probe_mismatch")


def _probe_pdfium(fixtures_root: Path) -> None:
    from pypdf import PdfWriter

    from app.services.pdf_text import extract_pdf_text

    fixture = fixtures_root / "reports" / "backend_report_recommendations_v2.pdf"
    selectable = extract_pdf_text(fixture, engine="pdfium")
    if selectable["page_count"] < 1 or not selectable["text"]:
        raise RuntimeError("pdfium_selectable_text_probe_failed")
    with tempfile.TemporaryDirectory(prefix="eamos-pdfium-preflight-") as directory:
        blank_path = Path(directory) / "blank.pdf"
        malformed_path = Path(directory) / "malformed.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        with blank_path.open("wb") as handle:
            writer.write(handle)
        malformed_path.write_bytes(b"%PDF-not-a-valid-document")
        blank = extract_pdf_text(blank_path, engine="pdfium")
        malformed = extract_pdf_text(malformed_path, engine="pdfium")
    if "ocr_required:page:1" not in blank["warnings"]:
        raise RuntimeError("pdfium_blank_page_probe_failed")
    if malformed["page_count"] != 0 or not malformed["warnings"]:
        raise RuntimeError("pdfium_malformed_probe_failed")


def _probe_pypdf(fixtures_root: Path) -> None:
    from app.services.pdf_text import extract_pdf_text

    fixture = fixtures_root / "reports" / "backend_report_recommendations_v2.pdf"
    result = extract_pdf_text(fixture, engine="pypdf")
    if result["page_count"] < 1 or not result["text"]:
        raise RuntimeError("pypdf_fallback_probe_failed")


def _elapsed_ms(started: float) -> float:
    return round(max(0.0, (perf_counter() - started) * 1000), 3)
