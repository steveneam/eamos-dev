from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime
from hashlib import sha256
import hmac
import json
import secrets

from app.schemas.batch import BatchInputEnvelopeV2, BatchSourceSnapshotV2
from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.services.batch_engine.normalization import BatchAlleleNormalizer


def build_source_snapshot(
    *,
    envelope: BatchInputEnvelopeV2,
    normalizer: BatchAlleleNormalizer,
    lookup_ready: bool,
    interval_capability: CapabilityExecutionDisclosureV2 | None = None,
    created_at: datetime | None = None,
) -> BatchSourceSnapshotV2:
    timestamp = (created_at or datetime.now(UTC)).astimezone(UTC)
    capabilities = [
        CapabilityExecutionDisclosureV2(
            capability_id="batch.vcf_intake",
            claim="bounded HTSlib streaming intake for VCF and VCF.gz",
            execution="eamos_local",
            algorithm_id="pysam_variantfile_stream",
            algorithm_version="0.24.0",
            input_scope="wes_single_or_small_family_vcf",
            source_status="not_required",
            applicability="applicable",
            validation_status="validated",
            validation_matrix_id="batch-wes-streaming-v1",
            retention="none",
            consent_required=False,
            warnings=list(envelope.warnings),
            requirements=[],
        ),
        normalizer.disclosure(),
        _lookup_disclosure(lookup_ready),
    ]
    if interval_capability is not None:
        capabilities.append(interval_capability)
    payload = {
        "created_at": timestamp.isoformat(),
        "reference_release": normalizer.reference_release,
        "capabilities": [item.model_dump(mode="json") for item in capabilities],
    }
    digest = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return BatchSourceSnapshotV2(
        snapshot_id=f"batch-snapshot-{digest[:24]}",
        created_at=timestamp,
        genome_build="GRCh38",
        reference_release=normalizer.reference_release,
        capabilities=capabilities,
    )


def unavailable_interval_capability(requirement: str) -> CapabilityExecutionDisclosureV2:
    return CapabilityExecutionDisclosureV2(
        capability_id="batch.interval_filter",
        claim="coordinate-backed panel or capture interval filtering",
        execution="unavailable",
        input_scope="grch38_panel_intervals",
        source_status="unavailable",
        applicability="applicable",
        validation_status="unvalidated",
        retention="none",
        consent_required=False,
        warnings=["INFO GENE and ANN fields are never treated as interval authority."],
        requirements=[requirement],
    )


def mounted_interval_capability(
    *,
    manifest_id: str,
    artifact_sha256: str,
    source_release: str,
    validation_matrix_id: str | None,
) -> CapabilityExecutionDisclosureV2:
    return CapabilityExecutionDisclosureV2(
        capability_id="batch.interval_filter",
        claim="coordinate-backed panel or capture interval filtering",
        execution="mounted_artifact",
        algorithm_id="eamos_coordinate_interval_filter",
        algorithm_version="1",
        input_scope="grch38_panel_intervals",
        source_status="source_backed",
        source_record_ids=[manifest_id],
        source_release=source_release,
        artifact_manifest_id=manifest_id,
        artifact_sha256=artifact_sha256,
        applicability="applicable",
        validation_status="validated" if validation_matrix_id else "unvalidated",
        validation_matrix_id=validation_matrix_id,
        retention="none",
        consent_required=False,
        warnings=["VCF INFO gene annotations are preserved only as provenance."],
        requirements=[],
    )


class SnapshotCursorCodec:
    """Opaque HMAC-bound paging cursors that cannot cross a source snapshot."""

    def __init__(self, secret: bytes | None = None) -> None:
        self._secret = secret or secrets.token_bytes(32)
        if len(self._secret) < 32:
            raise ValueError("batch cursor secret must contain at least 32 bytes")

    def encode(self, *, snapshot_id: str, offset: int) -> str:
        payload = json.dumps(
            {"snapshot": snapshot_id, "offset": max(0, int(offset))},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        signature = hmac.digest(self._secret, payload, "sha256")
        return f"{_b64(payload)}.{_b64(signature)}"

    def decode(self, cursor: str | None, *, snapshot_id: str) -> int:
        if not cursor:
            return 0
        try:
            payload_text, signature_text = cursor.split(".", 1)
            payload = _unb64(payload_text)
            signature = _unb64(signature_text)
            expected = hmac.digest(self._secret, payload, "sha256")
            if not hmac.compare_digest(signature, expected):
                raise ValueError
            decoded = json.loads(payload)
            if decoded.get("snapshot") != snapshot_id:
                raise ValueError
            offset = int(decoded["offset"])
            if offset < 0:
                raise ValueError
            return offset
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("batch cursor is invalid for the requested source snapshot") from exc


def _lookup_disclosure(ready: bool) -> CapabilityExecutionDisclosureV2:
    if ready:
        return CapabilityExecutionDisclosureV2(
            capability_id="batch.direct_report_lookup",
            claim="annotate normalized alleles through the direct Report lookup service",
            execution="eamos_local",
            algorithm_id="eamos_direct_report_lookup_adapter",
            algorithm_version="2",
            input_scope="normalized_grch38_allele",
            source_status="not_required",
            applicability="applicable",
            validation_status="unvalidated",
            retention="none",
            consent_required=False,
            warnings=["Each field remains bound to its Report V2 execution disclosure."],
            requirements=[],
        )
    return CapabilityExecutionDisclosureV2(
        capability_id="batch.direct_report_lookup",
        claim="annotate normalized alleles through the direct Report lookup service",
        execution="unavailable",
        input_scope="normalized_grch38_allele",
        source_status="unavailable",
        applicability="applicable",
        validation_status="unvalidated",
        retention="none",
        consent_required=False,
        warnings=[],
        requirements=["inject the direct LookupService during application startup"],
    )


def _b64(value: bytes) -> str:
    return urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return urlsafe_b64decode(value + "=" * (-len(value) % 4))
