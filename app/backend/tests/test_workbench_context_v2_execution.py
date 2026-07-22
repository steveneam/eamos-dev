from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.schemas.workbench import (
    AlignRequest,
    CrisprOffTargetRequest,
    CrisprRequest,
    CrisprScreeningPrimerRequest,
    CrisprSsodnRequest,
    PrimerPair,
    PrimerRequest,
    PrimerResponse,
)
from app.schemas.workflow import (
    CanonicalVariantRefV1,
    SelectionRangeV1,
    WorkbenchDesignContextV2,
    WorkbenchReferenceBasisV2,
    WorkbenchSparseEditV2,
    build_workbench_design_context_digest_v2,
)
from app.services.sequence_context import (
    NormalizedVariantQuery,
    SequenceContext,
    SequenceContextResult,
)
from app.services.crispr_design import LocalDeterministicCrisprProvider
from app.services.crispr_offtarget_index import build_spcas9_offtarget_index_from_sequences
from app.services.crispr_offtarget_screening import (
    IndexedSqliteCrisprOffTargetProvider,
    MockCasOffinderOffTargetProvider,
)
from app.services.workbench_design import WorkbenchDesignError
from app.services.workbench_design_context import verify_workbench_design_context_v2
from app.services.workbench_design_service import WorkbenchDesignService

_REFERENCE_TEMPLATE = ("ACGT" * 40)[:160]
REFERENCE = _REFERENCE_TEMPLATE[:50] + "A" + _REFERENCE_TEMPLATE[51:]


def _sha256(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def _variant() -> CanonicalVariantRefV1:
    return CanonicalVariantRefV1(
        schema_version="canonical_variant_ref.v1",
        gene="TEST",
        cdna="c.51A>G",
        transcript="NM_TEST.1",
        protein_hgvs="p.Lys17Arg",
        genomic_hg38="7-1050-A-G",
        variant_key="TEST:NM_TEST.1:c.51A>G",
        species="human",
        genome_build="GRCh38",
        resolution_status="resolved",
        source_support=["test-resolver"],
        warnings=[],
    )


def _selection(*, basis: str, sequence_sha256: str, revision: int) -> SelectionRangeV1:
    return SelectionRangeV1(
        schema_version="selection_range.v1",
        variant_key="TEST:NM_TEST.1:c.51A>G",
        transcript="NM_TEST.1",
        genome_build="GRCh38",
        chrom="chr7",
        genomic_start=1020,
        genomic_end=1089,
        strand="+",
        orientation="genomic_forward",
        sequence_basis=basis,
        edit_revision=revision,
        sequence_sha256=sequence_sha256,
        cdna_start=21,
        cdna_end=90,
        cds_start=21,
        cds_end=90,
        protein_start=7,
        protein_end=30,
        overlaps=["cds", "exon"],
    )


def _context(*, edited: bool = False) -> WorkbenchDesignContextV2:
    reference = WorkbenchReferenceBasisV2(
        transcript="NM_TEST.1",
        genome_build="GRCh38",
        chrom="chr7",
        genomic_start=1000,
        genomic_end=1159,
        strand="+",
        orientation="genomic_forward",
        source_id="synthetic_reference",
        source_release="test-1",
        source_record_id="chr7.1000-1159",
        sequence_length=len(REFERENCE),
        sequence_sha256=_sha256(REFERENCE),
    )
    edits: list[WorkbenchSparseEditV2] = []
    basis = "reference"
    revision = 0
    sequence_digest = reference.sequence_sha256
    if edited:
        edits = [
            WorkbenchSparseEditV2(
                edit_id="edit-1",
                operation="substitution",
                start_offset=50,
                end_offset=51,
                reference_bases=REFERENCE[50],
                alternate_bases="G" if REFERENCE[50] != "G" else "A",
            )
        ]
        effective = REFERENCE[:50] + edits[0].alternate_bases + REFERENCE[51:]
        basis = "edited"
        revision = 1
        sequence_digest = _sha256(effective)
    selection = _selection(
        basis=basis,
        sequence_sha256=sequence_digest,
        revision=revision,
    )
    payload = {
        "variant": _variant(),
        "reference": reference,
        "selection": selection,
        "edits": edits,
        "revision": revision,
    }
    return WorkbenchDesignContextV2(
        **payload,
        context_digest=build_workbench_design_context_digest_v2(**payload),
    )


def _resolved(sequence: str = REFERENCE, *, strand: str = "+") -> SequenceContextResult:
    query = NormalizedVariantQuery(
        gene="TEST",
        hgvs="c.51A>G",
        transcript="NM_TEST.1",
        kind="cdna",
        transcript_hgvs="NM_TEST.1:c.51A>G",
        resolver_transcript="NM_TEST.1",
        resolver_transcript_hgvs="NM_TEST.1:c.51A>G",
    )
    return SequenceContextResult(
        query=query,
        context=SequenceContext(
            gene="TEST",
            cdna="c.51A>G",
            transcript="NM_TEST.1",
            transcript_hgvs="NM_TEST.1:c.51A>G",
            query_kind="cdna",
            genome_build="GRCh38",
            genomic_hg38="7-1050-A-G",
            strand=strand,
            window_sequence=sequence,
            target_offset=50,
            reference_base="A",
            alternate_base="G",
            source="resolver",
            source_metadata={
                "source_id": "synthetic_reference",
                "source_release": "test-1",
                "source_record_id": "chr7.1000-1159",
            },
        ),
    )


def _reverse_complement(sequence: str) -> str:
    return sequence.translate(str.maketrans("ACGTN", "TGCAN"))[::-1]


def _apply_test_edits(
    reference: str,
    edits: list[WorkbenchSparseEditV2],
) -> str:
    pieces: list[str] = []
    cursor = 0
    for edit in edits:
        pieces.extend((reference[cursor : edit.start_offset], edit.alternate_bases))
        cursor = edit.end_offset
    pieces.append(reference[cursor:])
    return "".join(pieces)


def _context_for_sequence(
    sequence: str,
    *,
    orientation: str = "genomic_forward",
    strand: str = "+",
    selection_offsets: tuple[int, int] = (20, 90),
    edits: list[WorkbenchSparseEditV2] | None = None,
    overlaps: list[str] | None = None,
) -> WorkbenchDesignContextV2:
    reverse_orientation = orientation == "genomic_reverse" or (
        orientation == "transcript" and strand == "-"
    )
    oriented = _reverse_complement(sequence) if reverse_orientation else sequence
    coordinates = tuple(range(1159, 999, -1)) if reverse_orientation else tuple(range(1000, 1160))
    start_offset, end_offset = selection_offsets
    selected_coordinates = coordinates[start_offset:end_offset]
    sparse_edits = list(edits or [])
    effective = _apply_test_edits(oriented, sparse_edits)
    revision = 1 if sparse_edits else 0
    basis = "edited" if sparse_edits else "reference"
    reference = WorkbenchReferenceBasisV2(
        transcript="NM_TEST.1",
        genome_build="GRCh38",
        chrom="chr7",
        genomic_start=1000,
        genomic_end=1159,
        strand=strand,
        orientation=orientation,
        source_id="synthetic_reference",
        source_release="test-1",
        source_record_id="chr7.1000-1159",
        sequence_length=len(oriented),
        sequence_sha256=_sha256(oriented),
    )
    selection = SelectionRangeV1(
        schema_version="selection_range.v1",
        variant_key="TEST:NM_TEST.1:c.51A>G",
        transcript="NM_TEST.1",
        genome_build="GRCh38",
        chrom="chr7",
        genomic_start=min(selected_coordinates),
        genomic_end=max(selected_coordinates),
        strand=strand,
        orientation=orientation,
        sequence_basis=basis,
        edit_revision=revision,
        sequence_sha256=_sha256(effective),
        cdna_start=None,
        cdna_end=None,
        cds_start=None,
        cds_end=None,
        protein_start=None,
        protein_end=None,
        overlaps=overlaps or ["exon"],
    )
    payload = {
        "variant": _variant(),
        "reference": reference,
        "selection": selection,
        "edits": sparse_edits,
        "revision": revision,
    }
    return WorkbenchDesignContextV2(
        **payload,
        context_digest=build_workbench_design_context_digest_v2(**payload),
    )


class _StaticSequenceContextService:
    def __init__(self, resolved: SequenceContextResult) -> None:
        self.resolved = resolved
        self.calls: list[dict[str, object]] = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return self.resolved


class _CapturingPrimerProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[PrimerRequest, SequenceContext]] = []

    def design(self, payload: PrimerRequest, context: SequenceContext) -> PrimerResponse:
        self.calls.append((payload, context))
        return PrimerResponse(
            mode=payload.mode,
            pairs=[
                PrimerPair(
                    index=1,
                    forward="AACCGGTTAACCGGTTAA",
                    reverse="TTGGAACCTTGGAACCTT",
                    tm_forward=60.0,
                    tm_reverse=60.0,
                    gc_forward=44.4,
                    gc_reverse=55.5,
                    product_size=70,
                    specificity_hits=1,
                    recommended=True,
                )
            ],
        )


def test_context_v2_verifier_executes_declared_selection_and_sparse_edits() -> None:
    context = _context(edited=True)

    verified = verify_workbench_design_context_v2(context, _resolved())

    assert verified.context == context
    assert verified.reference_sequence == REFERENCE
    assert verified.effective_sequence[50] == context.edits[0].alternate_bases
    assert verified.engine_context.window_sequence == verified.effective_sequence[20:90]
    assert verified.engine_context.target_offset == 30
    assert verified.engine_context.source_metadata["context_digest"] == context.context_digest


@pytest.mark.parametrize(
    ("resolved", "code"),
    [
        (_resolved(REFERENCE[:-1] + "A"), "workbench_context_reference_digest_mismatch"),
        (
            SequenceContextResult(query=_resolved().query, context=None, warnings=[]),
            "workbench_context_source_unavailable",
        ),
    ],
)
def test_context_v2_verifier_fails_closed_for_unverified_reference(
    resolved: SequenceContextResult,
    code: str,
) -> None:
    with pytest.raises(WorkbenchDesignError) as captured:
        verify_workbench_design_context_v2(_context(), resolved)

    assert captured.value.code == code
    assert REFERENCE not in captured.value.message


def test_context_v2_service_reports_missing_source_as_unavailable() -> None:
    unavailable = SequenceContextResult(query=_resolved().query, context=None, warnings=[])
    service = WorkbenchDesignService(
        sequence_context_service=_StaticSequenceContextService(unavailable),
        primer_provider=_CapturingPrimerProvider(),
    )

    with pytest.raises(WorkbenchDesignError) as captured:
        service.design_primers(
            PrimerRequest(
                gene="TEST",
                cdna="c.51A>G",
                design_context_v2=_context(),
            )
        )

    assert captured.value.code == "workbench_context_source_unavailable"
    assert captured.value.status_code == 503


def test_context_v2_verifier_rejects_edit_reference_mismatch() -> None:
    context = _context(edited=True)
    corrupted_edit = context.edits[0].model_copy(update={"reference_bases": "T"})
    corrupted = context.model_copy(update={"edits": [corrupted_edit]})

    with pytest.raises(WorkbenchDesignError) as captured:
        verify_workbench_design_context_v2(corrupted, _resolved())

    assert captured.value.code == "workbench_context_edit_reference_mismatch"


def test_context_v2_discloses_unverified_optional_source_identity_metadata() -> None:
    resolved = _resolved()
    assert resolved.context is not None
    resolved = resolved.model_copy(
        update={"context": resolved.context.model_copy(update={"source_metadata": {}})}
    )
    service = WorkbenchDesignService(
        sequence_context_service=_StaticSequenceContextService(resolved),
        primer_provider=_CapturingPrimerProvider(),
    )

    response = service.design_primers(
        PrimerRequest(
            gene="TEST",
            cdna="c.51A>G",
            design_context_v2=_context(),
        )
    )

    assert response.execution_disclosure is not None
    assert response.execution_disclosure.source_release is None
    assert (
        "workbench_reference_source_identity_metadata_unavailable"
        in response.execution_disclosure.warnings
    )
    assert "versioned_reference_source_metadata" in response.execution_disclosure.requirements


def test_context_v2_primer_executes_exact_edited_selection_and_binds_result() -> None:
    context = _context(edited=True)
    sequence_service = _StaticSequenceContextService(_resolved())
    primer_provider = _CapturingPrimerProvider()
    service = WorkbenchDesignService(
        sequence_context_service=sequence_service,
        primer_provider=primer_provider,
    )

    response = service.design_primers(
        PrimerRequest(
            gene="TEST",
            cdna="c.51A>G",
            design_context_v2=context,
        )
    )

    assert response.verified_context == context
    assert response.context_binding is not None
    assert response.context_binding.state == "current"
    assert response.execution_disclosure is not None
    assert response.execution_disclosure.capability_id == "primer_design"
    assert response.execution_disclosure.retention == "request_lifetime"
    assert (
        primer_provider.calls[0][1].window_sequence
        == (REFERENCE[:50] + "G" + REFERENCE[51:])[20:90]
    )
    assert primer_provider.calls[0][1].genomic_coordinates == tuple(range(1020, 1090))
    assert sequence_service.calls == [
        {
            "gene": "TEST",
            "cdna": "c.51A>G",
            "transcript": "NM_TEST.1",
            "prefer_resolver": True,
        }
    ]


def test_context_v2_crispr_binds_guide_pam_cut_locus_and_explicit_scores() -> None:
    guide = "GAGTCCGAGCAGAAGAAGAT"
    bases = list("A" * 160)
    bases[50] = "A"
    bases[55:75] = guide
    bases[75:78] = "AGG"
    sequence = "".join(bases)
    context = _context_for_sequence(sequence)
    service = WorkbenchDesignService(
        sequence_context_service=_StaticSequenceContextService(_resolved(sequence)),
        primer_provider=_CapturingPrimerProvider(),
        crispr_provider=LocalDeterministicCrisprProvider(),
        crispr_offtarget_provider=MockCasOffinderOffTargetProvider(),
    )

    response = service.design_guides(
        CrisprRequest(
            gene="TEST",
            cdna="c.51A>G",
            strand_filter="plus",
            design_context_v2=context,
        )
    )

    assert response.ssodn is None
    assert response.context_binding is not None
    assert response.context_binding.result_context_digest == context.context_digest
    assert len(response.guides) == 1
    result = response.guides[0]
    assert result.identity is not None
    assert result.identity.guide == guide
    assert result.identity.pam == "AGG"
    assert result.identity.locus.chromosome == "chr7"
    assert result.identity.locus.protospacer_start == 1055
    assert result.identity.locus.protospacer_end == 1074
    assert result.identity.locus.pam_start == 1075
    assert result.identity.locus.pam_end == 1077
    assert result.identity.locus.cut_position == 1072
    assert result.identity.context_digest == context.context_digest
    assert [score.algorithm_id for score in result.scores] == [
        "eamos_gc_poly_t_heuristic",
        "hsu_mit_in_context_risk",
    ]
    assert result.scores[0].direction == "descriptive"
    assert "not_ruleset3" in result.scores[0].execution_disclosure.warnings
    assert "not_genome_wide" in result.scores[1].execution_disclosure.warnings

    off_target = service.enumerate_crispr_offtargets(
        CrisprOffTargetRequest(
            guide=guide,
            pam="AGG",
            on_target_locus={
                "chromosome": "chr7",
                "position": result.identity.locus.cut_position,
                "strand": "+",
            },
            design_context_v2=context,
            guide_identity=result.identity,
        )
    )
    assert off_target.sites == []
    assert off_target.guide_identity == result.identity
    assert off_target.execution_disclosure is not None
    assert off_target.execution_disclosure.execution == "unavailable"
    assert off_target.execution_disclosure.requirements == ["immutable_index_manifest_binding"]


def test_context_v2_offtarget_executes_only_with_bound_immutable_index(
    tmp_path: Path,
) -> None:
    guide = "GAGTCCGAGCAGAAGAAGAT"
    bases = list("A" * 160)
    bases[55:75] = guide
    bases[75:78] = "AGG"
    sequence = "".join(bases)
    context = _context_for_sequence(sequence)
    index_path = tmp_path / "spcas9.sqlite"
    build_spcas9_offtarget_index_from_sequences(
        [("7", ("N" * 1054) + guide + "AGG" + ("N" * 40))],
        index_path,
        source_version="synthetic-grch38-v1",
    )
    provider = IndexedSqliteCrisprOffTargetProvider(
        index_path,
        artifact_manifest_id="crispr.synthetic.v1",
        artifact_sha256="a" * 64,
        source_release="synthetic-grch38-v1",
    )
    service = WorkbenchDesignService(
        sequence_context_service=_StaticSequenceContextService(_resolved(sequence)),
        primer_provider=_CapturingPrimerProvider(),
        crispr_provider=LocalDeterministicCrisprProvider(),
        crispr_offtarget_provider=provider,
    )
    design = service.design_guides(
        CrisprRequest(
            gene="TEST",
            cdna="c.51A>G",
            strand_filter="plus",
            design_context_v2=context,
        )
    )
    identity = design.guides[0].identity
    assert identity is not None

    response = service.enumerate_crispr_offtargets(
        CrisprOffTargetRequest(
            guide=guide,
            pam="AGG",
            max_mismatches=1,
            on_target_locus={
                "chromosome": "chr7",
                "position": identity.locus.cut_position,
                "strand": "+",
            },
            design_context_v2=context,
            guide_identity=identity,
        )
    )

    assert response.execution_disclosure is not None
    assert response.execution_disclosure.execution == "mounted_artifact"
    assert response.execution_disclosure.artifact_manifest_id == "crispr.synthetic.v1"
    assert response.execution_disclosure.artifact_sha256 == "a" * 64
    assert response.sites[0].on_target is True
    assert response.sites[0].position == identity.locus.cut_position
    assert response.sites[0].scores[0].algorithm_id == "hsu_mit_cutting_score"
    assert response.sites[0].scores[0].guide_identity_sha256 == identity.identity_sha256


def test_context_v2_screening_and_alignment_use_verified_selection_only() -> None:
    context = _context()
    primer_provider = _CapturingPrimerProvider()
    service = WorkbenchDesignService(
        sequence_context_service=_StaticSequenceContextService(_resolved()),
        primer_provider=primer_provider,
    )

    screening = service.design_crispr_screening_primers(
        CrisprScreeningPrimerRequest(
            design_context_v2=context,
            sites=[
                {
                    "site_index": 1,
                    "chromosome": "chr7",
                    "position": 1045,
                    "region": {
                        "chromosome": "chr7",
                        "start": 1030,
                        "end": 1060,
                    },
                }
            ],
        )
    )
    assert screening.context_binding is not None
    assert screening.primers
    assert primer_provider.calls[0][1].window_sequence == REFERENCE[30:61]

    alignment = service.align(
        AlignRequest(
            gene="TEST",
            cdna="c.51A>G",
            user_sequence=REFERENCE[20:90],
            design_context_v2=context,
        )
    )
    assert alignment.context_binding is not None
    assert alignment.execution_disclosure is not None
    assert alignment.execution_disclosure.retention == "request_lifetime"
    assert alignment.reference.replace("-", "") == REFERENCE[20:90]
    assert alignment.sanger_read.replace("-", "") == REFERENCE[20:90]


def test_context_v2_ssodn_is_typed_unavailable_after_context_verification() -> None:
    context = _context()
    sequence_service = _StaticSequenceContextService(_resolved())
    service = WorkbenchDesignService(
        sequence_context_service=sequence_service,
        primer_provider=_CapturingPrimerProvider(),
    )

    with pytest.raises(WorkbenchDesignError) as captured:
        service.design_crispr_ssodn(
            CrisprSsodnRequest(
                gene="TEST",
                cdna="c.51A>G",
                transcript="NM_TEST.1",
                design_context_v2=context,
            )
        )

    assert captured.value.status_code == 503
    assert captured.value.code == "crispr_ssodn_hdr_efficiency_contract_unavailable"
    assert sequence_service.calls


@pytest.mark.parametrize(
    ("operation", "start", "end", "alternate"),
    [
        ("insertion", 40, 40, "TT"),
        ("deletion", 60, 62, ""),
        ("delins", 60, 63, "GG"),
    ],
)
def test_context_v2_indels_preserve_request_lifetime_genomic_mapping(
    operation: str,
    start: int,
    end: int,
    alternate: str,
) -> None:
    edit = WorkbenchSparseEditV2(
        edit_id=f"edit-{operation}",
        operation=operation,
        start_offset=start,
        end_offset=end,
        reference_bases=REFERENCE[start:end],
        alternate_bases=alternate,
    )
    context = _context_for_sequence(REFERENCE, edits=[edit])

    verified = verify_workbench_design_context_v2(context, _resolved())

    assert verified.engine_context.genomic_coordinates == verified.selected_coordinates
    if operation == "insertion":
        assert verified.selected_coordinates.count(None) == 2
        assert verified.engine_context.target_offset == 32
    else:
        assert None not in verified.selected_coordinates
        assert len(verified.selected_sequence) < 70


@pytest.mark.parametrize(
    ("orientation", "strand"),
    [("genomic_reverse", "+"), ("transcript", "-")],
)
def test_context_v2_reverse_orientations_map_selection_coordinates_exactly(
    orientation: str,
    strand: str,
) -> None:
    context = _context_for_sequence(
        REFERENCE,
        orientation=orientation,
        strand=strand,
        overlaps=["exon", "intron"],
    )

    verified = verify_workbench_design_context_v2(
        context,
        _resolved(strand=strand),
    )

    assert verified.selected_sequence == _reverse_complement(REFERENCE)[20:90]
    assert verified.selected_coordinates == tuple(range(1139, 1069, -1))
    assert verified.engine_context.genomic_coordinates == verified.selected_coordinates


def test_context_v2_distant_utr_selection_is_explicitly_variant_excluding() -> None:
    context = _context_for_sequence(
        REFERENCE,
        selection_offsets=(100, 140),
        overlaps=["utr3", "exon"],
    )

    verified = verify_workbench_design_context_v2(context, _resolved())

    assert verified.selected_sequence == REFERENCE[100:140]
    assert verified.engine_context.target_offset == 20
    assert "workbench_selection_excludes_variant_locus" in verified.engine_context.warnings
