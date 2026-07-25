from __future__ import annotations

import json
from pathlib import Path
import resource
import sys
from time import perf_counter

from app.capabilities.batch_normalizer import BatchNormalizerRuntime
from app.capabilities.errors import RuntimeCompositionError
from app.capabilities.models import (
    RuntimeCapabilityRegistryV1,
    RuntimeComponentV1,
    RuntimeProbeV1,
    RuntimeStartupMetricsV1,
)
from app.capabilities.pdf_worker import PdfTextWorker, run_pdf_worker_preflight
from app.capabilities.preflight import PackagePreflight, run_package_preflights
from app.core.config import Settings
from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.services.batch import BatchService
from app.services.lookup_service import LookupService

PACKAGE_CONTRACTS = {
    "primer3-py": {
        "component_id": "python.primer3",
        "display_name": "Primer3 primer design runtime",
        "pinned_version": "2.3.0",
        "license_spdx": "GPL-2.0-only",
        "license_posture": "copyleft_review_required",
        "capability_id": "workbench.primer3_design",
        "claim": "Primer3 Sanger and qPCR primer design",
        "algorithm_id": "primer3",
        "input_scope": "bounded_verified_sequence_context",
        "notice_ids": ["primer3-gplv2"],
    },
    "biopython": {
        "component_id": "python.biopython",
        "display_name": "Biopython AB1 runtime",
        "pinned_version": "1.87",
        "license_spdx": "Biopython",
        "license_posture": "permissive",
        "capability_id": "workbench.ab1_parsing",
        "claim": "AB1 trace parsing through Biopython",
        "algorithm_id": "biopython_abi_parser",
        "input_scope": "bounded_request_lifetime_ab1",
        "notice_ids": ["biopython-license"],
    },
    "pysam": {
        "component_id": "python.pysam",
        "display_name": "pysam HTSlib runtime",
        "pinned_version": "0.24.0",
        "license_spdx": "MIT",
        "license_posture": "permissive",
        "capability_id": "batch.vcf_streaming_runtime",
        "claim": "Indexed bounded VCF and tabix reads",
        "algorithm_id": "pysam_htslib",
        "input_scope": "bounded_vcf_and_tabix",
        "notice_ids": ["pysam-mit"],
    },
    "pypdfium2": {
        "component_id": "python.pypdfium2",
        "display_name": "PDFium text extraction runtime",
        "pinned_version": "5.12.1",
        "license_spdx": "BSD-3-Clause OR Apache-2.0",
        "license_posture": "permissive",
        "capability_id": "paper.pdfium_text_extraction",
        "claim": "Page-preserving local PDFium text extraction",
        "algorithm_id": "pdfium_textpage",
        "input_scope": "bounded_pdf_document",
        "notice_ids": ["pypdfium2-license", "pdfium-third-party-notices"],
    },
    "pypdf": {
        "component_id": "python.pypdf",
        "display_name": "pypdf fallback runtime",
        "pinned_version": "6.14.2",
        "license_spdx": "BSD-3-Clause",
        "license_posture": "permissive",
        "capability_id": "paper.pypdf_fallback",
        "claim": "Bounded local pypdf fallback extraction",
        "algorithm_id": "pypdf_text_extraction",
        "input_scope": "bounded_pdf_document",
        "notice_ids": ["pypdf-bsd3"],
    },
}


def build_runtime_composition(
    *,
    settings: Settings,
    batch_service: BatchService,
    lookup_service: LookupService,
    normalizer_runtime: BatchNormalizerRuntime,
    pdf_worker: PdfTextWorker,
    composition_started_at: float,
) -> RuntimeCapabilityRegistryV1:
    _assert_core_composition(
        settings=settings,
        batch_service=batch_service,
        lookup_service=lookup_service,
        normalizer_runtime=normalizer_runtime,
    )
    package_preflights = run_package_preflights(str(settings.fixtures_root.resolve()))
    pdf_worker_probe = run_pdf_worker_preflight(
        backend_root_value=str(pdf_worker.backend_root),
        fixture_path_value=str(
            settings.fixtures_root / "reports" / "backend_report_recommendations_v2.pdf"
        ),
        executable_value=str(pdf_worker.executable),
        memory_mb=pdf_worker.memory_mb,
        cpu_seconds=pdf_worker.cpu_seconds,
        max_output_bytes=pdf_worker.max_output_bytes,
    )
    package_components = [
        _package_component(name, package_preflights[name]) for name in PACKAGE_CONTRACTS
    ]
    package_capabilities = [
        _package_capability(name, package_preflights[name]) for name in PACKAGE_CONTRACTS
    ]
    components = [
        *_core_service_components(),
        *package_components,
        *_batch_normalizer_components(normalizer_runtime),
        *_unapproved_material_components(),
        _pdf_worker_component(pdf_worker_probe),
    ]
    capabilities = [
        _direct_lookup_capability(),
        _stable_cursor_capability(),
        normalizer_runtime.normalizer.disclosure(),
        *package_capabilities,
        _paper_process_isolation_capability(pdf_worker_probe),
    ]
    runtime_payload_size, container_image_size, measurement_requirements = _read_build_measurement(
        settings.runtime_build_inventory_path
    )
    return RuntimeCapabilityRegistryV1(
        status="degraded" if any(item.status != "ready" for item in components) else "ready",
        core_services_ready=True,
        startup_metrics=RuntimeStartupMetricsV1(
            composition_elapsed_ms=_elapsed_ms(composition_started_at),
            process_peak_rss_bytes=_peak_rss_bytes(),
            container_image_size_bytes=container_image_size,
            runtime_payload_size_bytes=runtime_payload_size,
            measurement_scope="container_build" if runtime_payload_size is not None else "process",
            requirements=measurement_requirements,
        ),
        components=components,
        capabilities=capabilities,
    )


def _assert_core_composition(
    *,
    settings: Settings,
    batch_service: BatchService,
    lookup_service: LookupService,
    normalizer_runtime: BatchNormalizerRuntime,
) -> None:
    if batch_service.lookup_service is not lookup_service:
        raise RuntimeCompositionError("batch_direct_lookup_not_injected")
    if batch_service.normalizer is not normalizer_runtime.normalizer:
        raise RuntimeCompositionError("batch_normalizer_not_injected")
    if len(settings.batch_cursor_secret) < 32:
        raise RuntimeCompositionError("batch_cursor_secret_too_short")


def _core_service_components() -> list[RuntimeComponentV1]:
    rows = (
        (
            "service.direct_lookup",
            "Direct Report lookup service",
            "batch.direct_report_lookup",
            "startup.lookup_identity.v1",
        ),
        (
            "service.batch",
            "Batch execution service",
            "batch.vcf_streaming_runtime",
            "startup.batch_injection.v1",
        ),
        (
            "service.batch_cursor_signing",
            "Restart-stable batch cursor signing",
            "batch.snapshot_cursor",
            "startup.batch_cursor_key.v1",
        ),
    )
    return [
        RuntimeComponentV1(
            component_id=component_id,
            display_name=display_name,
            kind="service",
            status="ready",
            required_at_startup=True,
            launch_posture="enabled",
            installed_version="2",
            pinned_version="2",
            license_spdx=None,
            license_posture="not_applicable",
            capability_ids=[capability_id],
            probe=RuntimeProbeV1(
                probe_id=probe_id,
                status="passed",
                executed=True,
                elapsed_ms=0,
                validation_matrix_id="runtime-composition-core-v1",
            ),
        )
        for component_id, display_name, capability_id, probe_id in rows
    ]


def _package_component(name: str, preflight: PackagePreflight) -> RuntimeComponentV1:
    contract = PACKAGE_CONTRACTS[name]
    version_matches = preflight.installed_version == contract["pinned_version"]
    if preflight.installed_version is None:
        status = "unavailable"
    elif preflight.probe.status != "passed" or not version_matches:
        status = "invalid"
    else:
        status = "ready"
    requirements = list(preflight.probe.requirements)
    if preflight.installed_version is not None and not version_matches:
        requirements.append(
            f"install exact {name}=={contract['pinned_version']} instead of the loaded version"
        )
    if status != "ready" and not requirements:
        requirements.append(f"restore the functional {name} runtime preflight")
    return RuntimeComponentV1(
        component_id=contract["component_id"],
        display_name=contract["display_name"],
        kind="package",
        status=status,
        required_at_startup=False,
        launch_posture="enabled" if status == "ready" else "gated",
        installed_version=preflight.installed_version,
        pinned_version=contract["pinned_version"],
        license_spdx=contract["license_spdx"],
        license_posture=contract["license_posture"],
        sbom_ref=(
            f"pkg:pypi/{name}@{preflight.installed_version}"
            if preflight.installed_version
            else f"pkg:pypi/{name}@{contract['pinned_version']}"
        ),
        notice_ids=contract["notice_ids"],
        capability_ids=[contract["capability_id"]],
        probe=preflight.probe,
        requirements=requirements,
    )


def _package_capability(name: str, preflight: PackagePreflight):
    contract = PACKAGE_CONTRACTS[name]
    ready = (
        preflight.probe.status == "passed"
        and preflight.installed_version == contract["pinned_version"]
    )
    if ready:
        return CapabilityExecutionDisclosureV2(
            capability_id=contract["capability_id"],
            claim=contract["claim"],
            execution="eamos_local",
            algorithm_id=contract["algorithm_id"],
            algorithm_version=preflight.installed_version,
            input_scope=contract["input_scope"],
            source_status="not_required",
            applicability="applicable",
            validation_status="validated",
            validation_matrix_id=preflight.probe.validation_matrix_id,
            retention="none",
            consent_required=False,
        )
    requirements = list(preflight.probe.requirements)
    if preflight.installed_version and preflight.installed_version != contract["pinned_version"]:
        requirements.append(f"load exact {name}=={contract['pinned_version']}")
    if not requirements:
        requirements.append(f"restore the functional {name} runtime preflight")
    return CapabilityExecutionDisclosureV2(
        capability_id=contract["capability_id"],
        claim=contract["claim"],
        execution="unavailable",
        input_scope=contract["input_scope"],
        source_status="unavailable",
        applicability="applicable",
        validation_status="failed" if preflight.probe.status == "failed" else "unvalidated",
        validation_matrix_id=preflight.probe.validation_matrix_id,
        retention="none",
        consent_required=False,
        warnings=list(preflight.probe.warnings),
        requirements=requirements,
    )


def _batch_normalizer_components(
    runtime: BatchNormalizerRuntime,
) -> list[RuntimeComponentV1]:
    if runtime.status == "ready":
        probe = RuntimeProbeV1(
            probe_id="bcftools.version_and_manifest.v1",
            status="passed",
            executed=True,
            elapsed_ms=0,
            validation_matrix_id=runtime.validation_matrix_id,
        )
        return [
            RuntimeComponentV1(
                component_id="binary.bcftools",
                display_name="bcftools normalization runtime",
                kind="binary",
                status="ready",
                required_at_startup=False,
                launch_posture="enabled",
                installed_version=runtime.binary_version,
                pinned_version=runtime.binary_version,
                license_spdx="GPL-3.0-or-later",
                license_posture="copyleft_review_required",
                sbom_ref=f"pkg:generic/bcftools@{runtime.binary_version}",
                notice_ids=["bcftools-gpl3"],
                capability_ids=["batch.variant_normalization"],
                artifact_manifest_id=runtime.manifest_id,
                artifact_sha256=runtime.binary_sha256,
                probe=probe,
            ),
            RuntimeComponentV1(
                component_id="material.grch38_batch_reference",
                display_name="Immutable GRCh38 batch normalization reference",
                kind="material",
                status="ready",
                required_at_startup=False,
                launch_posture="enabled",
                installed_version=runtime.reference_release,
                pinned_version=runtime.reference_release,
                license_spdx="LicenseRef-GRCh38-terms",
                license_posture="terms_review_required",
                capability_ids=["batch.variant_normalization"],
                artifact_manifest_id=runtime.manifest_id,
                artifact_sha256=runtime.reference_sha256,
                probe=probe,
            ),
        ]
    requirements = list(runtime.requirements)
    probe = RuntimeProbeV1(
        probe_id="bcftools.version_and_manifest.v1",
        status="unavailable",
        executed=False,
        elapsed_ms=0,
        requirements=requirements,
    )
    return [
        RuntimeComponentV1(
            component_id="binary.bcftools",
            display_name="bcftools normalization runtime",
            kind="binary",
            status="unavailable",
            required_at_startup=False,
            launch_posture="gated",
            pinned_version=None,
            license_spdx="GPL-3.0-or-later",
            license_posture="copyleft_review_required",
            sbom_ref="pkg:generic/bcftools",
            notice_ids=["bcftools-gpl3"],
            capability_ids=["batch.variant_normalization"],
            probe=probe,
            requirements=requirements,
        ),
        RuntimeComponentV1(
            component_id="material.grch38_batch_reference",
            display_name="Immutable GRCh38 batch normalization reference",
            kind="material",
            status="unavailable",
            required_at_startup=False,
            launch_posture="gated",
            license_spdx="LicenseRef-GRCh38-terms",
            license_posture="terms_review_required",
            capability_ids=["batch.variant_normalization"],
            probe=probe,
            requirements=requirements,
        ),
    ]


def _unapproved_material_components() -> list[RuntimeComponentV1]:
    rows = (
        ("material.crispr_offtarget", "GRCh38 CRISPR off-target index"),
        ("binary.ucsc_ispcr", "Licensed UCSC isPcr runtime"),
        ("material.primer_dbsnp", "dbSNP primer-mask tabix artifact"),
        ("runtime.crisprscore_r", "crisprScore R and model runtime"),
        ("material.report_alphamissense", "AlphaMissense predictor artifact"),
        ("material.report_esm1b", "ESM1b predictor artifact"),
        ("material.report_ci_spliceai", "CI-SpliceAI model and reference artifacts"),
        ("material.report_capice", "CAPICE model and feature artifacts"),
        ("material.report_revel", "REVEL predictor artifact"),
        ("material.report_primateai3d", "PrimateAI-3D predictor artifact"),
        ("material.paper_corpus", "Approved open-access Paper validation corpus"),
        ("material.paper_allele_resolver", "Paper allele-resolution source artifact"),
        ("material.batch_mane", "MANE Select and Plus Clinical intervals"),
        ("material.batch_hgnc", "HGNC symbol and alias artifact"),
        ("material.batch_gencc", "GenCC gene-disease assertions"),
        ("material.batch_mondo", "Mondo disease ontology artifact"),
        ("material.batch_vep", "Optional offline VEP cache"),
    )
    requirement = "approve the exact Wave 3 source, terms, digest, build, mount, and probe card"
    return [
        RuntimeComponentV1(
            component_id=component_id,
            display_name=display_name,
            kind="binary" if component_id.startswith(("binary.", "runtime.")) else "material",
            status="unavailable",
            required_at_startup=False,
            launch_posture="gated",
            license_spdx=None,
            license_posture="terms_review_required",
            probe=RuntimeProbeV1(
                probe_id=f"{component_id}.manifest.v1",
                status="unavailable",
                executed=False,
                elapsed_ms=0,
                requirements=[requirement],
            ),
            requirements=[requirement],
        )
        for component_id, display_name in rows
    ]


def _pdf_worker_component(probe: RuntimeProbeV1) -> RuntimeComponentV1:
    ready = probe.status == "passed"
    requirements = list(probe.requirements)
    if not ready and not requirements:
        requirements.append("restore the killable resource-capped PDF worker preflight")
    return RuntimeComponentV1(
        component_id="isolation.paper_pdf_worker",
        display_name="Killable resource-capped PDF worker process",
        kind="isolation",
        status="ready" if ready else "invalid",
        required_at_startup=False,
        launch_posture="enabled" if ready else "gated",
        installed_version="1",
        pinned_version="1",
        license_spdx=None,
        license_posture="not_applicable",
        capability_ids=["paper.pdf_process_isolation"],
        probe=probe,
        requirements=requirements,
    )


def _direct_lookup_capability() -> CapabilityExecutionDisclosureV2:
    return CapabilityExecutionDisclosureV2(
        capability_id="batch.direct_report_lookup",
        claim="Annotate normalized alleles through the direct Report lookup service",
        execution="eamos_local",
        algorithm_id="eamos_direct_report_lookup_adapter",
        algorithm_version="2",
        input_scope="normalized_grch38_allele",
        source_status="not_required",
        applicability="applicable",
        validation_status="validated",
        validation_matrix_id="batch-direct-lookup-parity-v1",
        retention="none",
        consent_required=False,
        warnings=["Each field remains bound to its Report V2 execution disclosure."],
    )


def _stable_cursor_capability() -> CapabilityExecutionDisclosureV2:
    return CapabilityExecutionDisclosureV2(
        capability_id="batch.snapshot_cursor",
        claim="HMAC-authenticated snapshot paging cursor stable across process restarts",
        execution="eamos_local",
        algorithm_id="hmac_sha256_domain_separated_cursor",
        algorithm_version="2",
        input_scope="batch_snapshot_id_and_offset",
        source_status="not_required",
        applicability="applicable",
        validation_status="validated",
        validation_matrix_id="batch-snapshot-cursor-v2",
        retention="none",
        consent_required=False,
    )


def _paper_process_isolation_capability(
    probe: RuntimeProbeV1,
) -> CapabilityExecutionDisclosureV2:
    if probe.status == "passed":
        return CapabilityExecutionDisclosureV2(
            capability_id="paper.pdf_process_isolation",
            claim="Killable resource-capped isolation for hostile PDF parsing",
            execution="eamos_local",
            algorithm_id="eamos_pdf_subprocess_worker",
            algorithm_version="1",
            input_scope="untrusted_pdf_document",
            source_status="not_required",
            applicability="applicable",
            validation_status="validated",
            validation_matrix_id=probe.validation_matrix_id,
            retention="request_lifetime",
            consent_required=False,
        )
    requirements = list(probe.requirements) or [
        "restore the killable resource-capped PDF worker preflight"
    ]
    return CapabilityExecutionDisclosureV2(
        capability_id="paper.pdf_process_isolation",
        claim="Killable resource-capped isolation for hostile PDF parsing",
        execution="unavailable",
        input_scope="untrusted_pdf_document",
        source_status="unavailable",
        applicability="applicable",
        validation_status="failed",
        validation_matrix_id=probe.validation_matrix_id,
        retention="none",
        consent_required=False,
        warnings=list(probe.warnings),
        requirements=requirements,
    )


def _read_build_measurement(path: Path) -> tuple[int | None, int | None, list[str]]:
    try:
        if not path.is_file() or path.stat().st_size > 5_000_000:
            raise ValueError
        decoded = json.loads(path.read_text(encoding="utf-8"))
        if decoded.get("schema_version") != "runtime_component_inventory.v1":
            raise ValueError
        measurement = decoded["measurement"]
        payload_size = int(measurement["runtime_payload_size_bytes"])
        image_size_value = measurement.get("container_image_size_bytes")
        image_size = int(image_size_value) if image_size_value is not None else None
        requirements = (
            []
            if image_size is not None
            else ["record docker image inspect size and immutable digest after the image build"]
        )
        return payload_size, image_size, requirements
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
        return (
            None,
            None,
            ["build the container inventory and record docker image size plus immutable digest"],
        )


def _peak_rss_bytes() -> int:
    value = max(0, int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    return value if sys.platform == "darwin" else value * 1024


def _elapsed_ms(started: float) -> float:
    return round(max(0.0, (perf_counter() - started) * 1000), 3)
