from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from app.core.config import Settings
from app.schemas.gene_viewer import GeneViewerResponse
from app.schemas.lookup import LookupResponse
from app.services.local_evidence_orchestrator import (
    CLINVAR_SOURCE_ID,
    DBSNP_SOURCE_ID,
    GENCODE_SOURCE_ID,
    LOCAL_EVIDENCE_RUNTIME_FLOWS,
    LOCAL_EVIDENCE_SOURCE_ORDER,
    MANE_SOURCE_ID,
    REPEATMASKER_SOURCE_ID,
    LocalEvidenceBundle,
    LocalEvidenceOrchestrator,
    LocalEvidenceRuntimeGate,
    LocalEvidenceVariantIdentity,
)
from app.services.reference_genome import (
    ReferenceBaseCheck,
    ReferenceGenomeMetadata,
    ReferenceWindow,
)
from app.services.sequence_window_model import LocalSequenceWindowBuilder


def test_rsid_resolution_composes_local_source_models_without_live_fallbacks() -> None:
    orchestrator = LocalEvidenceOrchestrator(
        sequence_builder=LocalSequenceWindowBuilder(_Rpe65ReferenceStore(), flank_bp=2)
    )

    bundle = orchestrator.resolve_rsid(
        "rs1645931040",
        include_sequence=True,
    )

    assert bundle.available is True
    assert bundle.unavailable_reason is None
    assert bundle.warnings == ()
    assert bundle.variant_identity == LocalEvidenceVariantIdentity(
        chrom="1",
        position=68444869,
        ref="T",
        alt="C",
        variant_id="1-68444869-T-C",
        genomic_hgvs="NC_000001.11:g.68444869T>C",
        rsid="rs1645931040",
        source=DBSNP_SOURCE_ID,
    )

    assert bundle.dbsnp is not None
    assert bundle.dbsnp.available is True
    assert bundle.dbsnp.record is not None
    assert bundle.dbsnp.record.provenance.source_id == DBSNP_SOURCE_ID

    assert bundle.clinvar is not None
    assert bundle.clinvar.available is True
    assert bundle.clinvar.record is not None
    assert bundle.clinvar.record.accession == "VCV001421454"
    assert bundle.clinvar.record.classification == "Uncertain significance"

    assert bundle.transcript_coordinate is not None
    assert bundle.transcript_coordinate.available is True
    assert bundle.transcript_coordinate.location is not None
    assert bundle.transcript_coordinate.location.region == "exon"
    assert bundle.transcript_coordinate.location.exon_number == 4
    assert bundle.transcript_coordinate.location.cds_position == 260
    assert bundle.transcript_coordinate.location.strand == "-"

    assert bundle.repeatmasker is not None
    assert bundle.repeatmasker.available is True
    assert bundle.repeatmasker.repeats == ()

    assert bundle.sequence_context is not None
    assert bundle.sequence_context.unavailable_reason is None
    assert bundle.sequence_context.gene == "RPE65"
    assert bundle.sequence_context.transcript == "NM_000329.3"
    assert bundle.sequence_context.cdna_hgvs == "NM_000329.3:c.260A>G"
    assert bundle.sequence_context.reference_window is not None
    assert bundle.sequence_context.reference_window.sequence == "AATAA"
    assert bundle.sequence_context.reference_base_check is not None
    assert bundle.sequence_context.reference_base_check.matches is True
    assert bundle.sequence_context.variant_window is not None
    assert bundle.sequence_context.variant_window.applied_sequence == "AACAA"

    assert any(token.startswith(f"{DBSNP_SOURCE_ID}:") for token in bundle.provenance)
    assert any(token.startswith(f"{CLINVAR_SOURCE_ID}:") for token in bundle.provenance)
    assert any(token.startswith("transcript_model:NM_000329.3:exon") for token in bundle.provenance)
    assert f"{REPEATMASKER_SOURCE_ID}:hits=0" in bundle.provenance
    assert not any("live" in token or "source_cache" in token for token in bundle.provenance)


def test_multiallelic_rsid_requires_explicit_allele_before_orchestration() -> None:
    bundle = LocalEvidenceOrchestrator().resolve_rsid("rs1801133")

    assert bundle.available is False
    assert bundle.unavailable_reason == "ambiguous_rsid_alleles"
    assert bundle.variant_identity is None
    assert bundle.dbsnp is not None
    assert bundle.dbsnp.available is True
    assert bundle.dbsnp.record is not None
    assert bundle.dbsnp.record.is_multiallelic is True
    assert bundle.clinvar is None
    assert bundle.transcript_coordinate is None
    assert bundle.repeatmasker is None
    assert bundle.sequence_context is None
    assert bundle.warnings == ("local_evidence_ambiguous_rsid_alleles",)


def test_no_hit_local_sources_remain_visible_and_do_not_substitute_fixture_records() -> None:
    bundle = LocalEvidenceOrchestrator().resolve_variant(
        gene="RPE65",
        chrom="NC_000001.11",
        position=68444869,
        ref="T",
        alt="A",
    )

    assert bundle.available is True
    assert bundle.variant_identity is not None
    assert bundle.variant_identity.variant_id == "1-68444869-T-A"
    assert bundle.dbsnp is not None
    assert bundle.dbsnp.available is False
    assert bundle.dbsnp.unavailable_reason == "allele_mismatch"
    assert bundle.clinvar is not None
    assert bundle.clinvar.available is False
    assert bundle.clinvar.record is None
    assert bundle.clinvar.unavailable_reason == "allele_mismatch"
    assert "dbsnp_local_allele_mismatch" in bundle.warnings
    assert "clinvar_local_allele_mismatch" in bundle.warnings
    assert any(token == f"{CLINVAR_SOURCE_ID}:no_record" for token in bundle.provenance)


def test_local_orchestrator_has_no_public_contract_surface() -> None:
    assert not issubclass(LocalEvidenceBundle, BaseModel)
    assert not issubclass(LocalEvidenceVariantIdentity, BaseModel)
    assert "local_evidence" not in LookupResponse.model_fields
    assert "local_evidence" not in GeneViewerResponse.model_fields
    assert LOCAL_EVIDENCE_SOURCE_ORDER == (
        DBSNP_SOURCE_ID,
        CLINVAR_SOURCE_ID,
        MANE_SOURCE_ID,
        GENCODE_SOURCE_ID,
        REPEATMASKER_SOURCE_ID,
    )


def test_local_evidence_runtime_gate_is_disabled_by_default() -> None:
    gate = LocalEvidenceRuntimeGate.from_settings(Settings(jwt_secret="test-secret"))

    decision = gate.for_flow("lookup")

    assert LOCAL_EVIDENCE_RUNTIME_FLOWS == ("lookup", "search", "gene_viewer", "workbench")
    assert decision.enabled is False
    assert decision.reason == "local_evidence_disabled"
    assert gate.allows("lookup") is False


def test_local_evidence_runtime_gate_requires_explicit_real_api_opt_in() -> None:
    settings = Settings(
        jwt_secret="test-secret",
        local_evidence_enabled=True,
        local_evidence_allowed_flows_raw="lookup,gene-viewer",
        use_real_apis=False,
    )
    gate = LocalEvidenceRuntimeGate.from_settings(settings)

    assert gate.for_flow("lookup").reason == "local_evidence_real_apis_required"
    assert gate.for_flow("gene_viewer").enabled is False

    live_gate = LocalEvidenceRuntimeGate.from_settings(
        Settings(
            jwt_secret="test-secret",
            local_evidence_enabled=True,
            local_evidence_allowed_flows_raw="lookup,gene-viewer",
            use_real_apis=True,
        )
    )

    assert live_gate.for_flow("lookup").enabled is True
    assert live_gate.for_flow("lookup").reason == "local_evidence_enabled"
    assert live_gate.for_flow("gene-viewer").enabled is True
    assert live_gate.for_flow("workbench").reason == "local_evidence_flow_not_enabled"


def test_local_evidence_runtime_gate_rejects_unknown_flows_fail_closed() -> None:
    gate = LocalEvidenceRuntimeGate.from_settings(
        Settings(
            jwt_secret="test-secret",
            local_evidence_enabled=True,
            local_evidence_allowed_flows_raw="all,unknown-flow",
            use_real_apis=True,
        )
    )

    assert gate.for_flow("workbench").enabled is True
    assert gate.for_flow("not-a-flow").enabled is False
    assert gate.for_flow("not-a-flow").reason == "local_evidence_unknown_flow"
    assert "local_evidence_unknown_configured_flow:unknown_flow" in gate.warnings


class _Rpe65ReferenceStore:
    def metadata(self) -> ReferenceGenomeMetadata:
        return ReferenceGenomeMetadata(
            source_id="ucsc_hg38_2bit",
            source_url=None,
            source_version="test_rpe65_reference",
            genome_build="GRCh38",
            relative_path="tests/fixtures/rpe65_reference",
            path=Path("tests/fixtures/rpe65_reference"),
            checksum_algorithm="sha256",
            checksum="0" * 64,
            reader="test_fixture",
            source_local_path=None,
            source_local_md5=None,
            source_local_size_bytes=None,
        )

    def get_sequence(
        self,
        chrom: str,
        start: int,
        end: int,
        build: str | None = None,
    ) -> ReferenceWindow:
        assert build in {None, "GRCh38"}
        normalized_chrom = chrom.removeprefix("chr")
        if normalized_chrom == "NC_000001.11":
            normalized_chrom = "1"
        assert normalized_chrom == "1"
        sequence = "".join(
            "T" if position == 68444869 else "A" for position in range(start, end + 1)
        )
        return ReferenceWindow(
            requested_chrom=chrom,
            chrom="1",
            start=start,
            end=end,
            zero_based_start=start - 1,
            zero_based_end_exclusive=end,
            sequence=sequence,
            genome_build="GRCh38",
            source_id="ucsc_hg38_2bit",
        )

    def validate_reference_base(
        self,
        chrom: str,
        position: int,
        expected: str,
        build: str | None = None,
    ) -> ReferenceBaseCheck:
        window = self.get_sequence(chrom, position, position, build=build)
        observed = window.sequence
        expected_base = expected.strip().upper()
        return ReferenceBaseCheck(
            requested_chrom=chrom,
            chrom=window.chrom,
            position=position,
            expected_base=expected_base,
            observed_base=observed,
            matches=observed == expected_base,
            reason=(
                "reference_base_match" if observed == expected_base else "reference_base_mismatch"
            ),
            genome_build="GRCh38",
            source_id="ucsc_hg38_2bit",
        )
