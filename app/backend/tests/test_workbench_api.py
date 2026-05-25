from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import status

from app.core.config import Settings
from app.schemas.workbench import (
    AlignRequest,
    AlignResponse,
    CrisprRequest,
    CrisprResponse,
    PrimerRequest,
    PrimerResponse,
)
from app.services.crispr_design import (
    CRISPR_PROVIDER_CRISPRSCORE_R,
    CRISPR_PROVIDER_LOCAL_DETERMINISTIC,
    CrisprScoreRAdapter,
    CrisprScoreRBackedCrisprProvider,
    LocalDeterministicCrisprProvider,
)
from app.services.sequence_context import (
    SequenceContext,
    SequenceContextResult,
    normalize_sequence_query,
    unsupported_input_warning,
)
from app.services.workbench_design import (
    ALIGN_MAX_MATRIX_CELLS,
    ALIGN_MAX_SEQUENCE_BASES,
    PRIMER_SPECIFICITY_UCSC_ISPCR,
    WORKBENCH_PROVIDER_MALFORMED,
    WORKBENCH_PROVIDER_UNAVAILABLE,
    LocalIsPcrSpecificityProvider,
    PrimerSpecificityResult,
    Primer3PrimerProvider,
    TemplateAmpliconSpecificityProvider,
    WorkbenchDesignError,
    WorkbenchDesignService,
    _align_sequences,
)
from app.services.trace_parser import (
    TRACE_MAX_BASE_CALLS,
    TRACE_MAX_CHANNEL_SAMPLES,
    TRACE_MAX_ENCODED_BYTES,
    TRACE_INVALID_SIGNAL,
    TRACE_PAYLOAD_TOO_LARGE,
    TRACE_PARSER_UNAVAILABLE,
    TRACE_UNSUPPORTED_FORMAT,
    TraceParseError,
    parse_ab1_base64,
    parse_ab1_bytes,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures" / "workbench"


class FailingWorkbenchService:
    def __init__(self, error: WorkbenchDesignError) -> None:
        self.error = error

    def design_primers(self, _payload):
        raise self.error

    def design_guides(self, _payload):
        raise self.error

    def align(self, _payload):
        raise self.error


class StaticSequenceContextService:
    def __init__(self, result: SequenceContextResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    def resolve(self, **kwargs) -> SequenceContextResult:
        self.calls.append(kwargs)
        return self.result


class FakePrimerProvider:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def design(self, payload, context) -> PrimerResponse:
        self.calls.append((payload, context))
        return PrimerResponse(mode=payload.mode, pairs=[])


class FakeCrisprProvider:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def design(self, payload, context) -> CrisprResponse:
        self.calls.append((payload, context))
        return CrisprResponse(cas=payload.cas, guides=[], ssodn=None)


class FakeAlignProvider:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def align(self, payload, context) -> AlignResponse:
        self.calls.append((payload, context))
        return AlignResponse(
            reference="ACGT",
            sanger_read="ACGT",
            match_line="||||",
            mismatch_positions=[],
            target_position=1,
            trace_channels=[],
            base_calls=list("ACGT"),
            q_scores=[],
        )


class QueuedSpecificityProvider:
    def __init__(self, results: list[PrimerSpecificityResult]) -> None:
        self.results = results
        self.calls: list[dict] = []

    def check(self, **kwargs) -> PrimerSpecificityResult:
        self.calls.append(kwargs)
        return self.results.pop(0)


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _settings(**overrides) -> Settings:
    return Settings(jwt_secret="test-secret", **overrides)


def _context() -> SequenceContext:
    return SequenceContext(
        gene="RPE65",
        cdna="c.260A>G",
        transcript="NM_000329.3",
        transcript_hgvs="NM_000329.3:c.260A>G",
        query_kind="cdna",
        genome_build="GRCh38",
        genomic_hg38="1-68444869-T-C",
        window_sequence="A" * 1000,
        target_offset=500,
        reference_base="T",
        alternate_base="C",
        source="resolver",
    )


def _specificity_result(
    *,
    hits: int = 1,
    intended_hits: int = 1,
    product_sizes: tuple[int, ...] = (421,),
    note: str = "Specificity provider note.",
) -> PrimerSpecificityResult:
    return PrimerSpecificityResult(
        hits=hits,
        intended_hits=intended_hits,
        product_sizes=product_sizes,
        note=note,
    )


def test_create_app_wires_workbench_design_service(app) -> None:
    assert isinstance(app.state.workbench_design_service, WorkbenchDesignService)
    assert app.state.sequence_context_service is not None


@pytest.mark.parametrize(
    "path,payload,fixture_name",
    [
        ("/api/v1/primer", {"gene": "RPE65", "cdna": "c.260A>G"}, "primer_rpe65.json"),
        ("/api/v1/crispr", {"gene": "RPE65", "cdna": "c.260A>G"}, "crispr_rpe65.json"),
        ("/api/v1/align", {"gene": "RPE65", "cdna": "c.260A>G"}, "align_rpe65.json"),
    ],
)
def test_workbench_endpoints_preserve_fixture_responses(
    client,
    path: str,
    payload: dict,
    fixture_name: str,
) -> None:
    response = client.post(path, json=payload)

    assert response.status_code == 200
    assert response.json() == _fixture(fixture_name)


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/v1/primer", {"gene": "RPE65", "cdna": "c.260A>G"}),
        ("/api/v1/crispr", {"gene": "RPE65", "cdna": "c.260A>G"}),
        ("/api/v1/align", {"gene": "RPE65", "cdna": "c.260A>G"}),
    ],
)
def test_workbench_service_failures_map_to_structured_http_errors(
    client,
    path: str,
    payload: dict,
) -> None:
    client.app.state.workbench_design_service = FailingWorkbenchService(
        WorkbenchDesignError(
            code=WORKBENCH_PROVIDER_MALFORMED,
            message="Provider returned an invalid design.",
            status_code=status.HTTP_502_BAD_GATEWAY,
            warnings=[WORKBENCH_PROVIDER_MALFORMED, "provider_payload_missing_field"],
        )
    )

    response = client.post(path, json=payload)

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": WORKBENCH_PROVIDER_MALFORMED,
        "message": "Provider returned an invalid design.",
        "warnings": [WORKBENCH_PROVIDER_MALFORMED, "provider_payload_missing_field"],
    }


def test_real_mode_primer_service_uses_sequence_context_and_provider() -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    sequence_service = StaticSequenceContextService(
        SequenceContextResult(query=query, context=_context())
    )
    primer_provider = FakePrimerProvider()
    service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=sequence_service,
        primer_provider=primer_provider,
    )

    response = service.design_primers(PrimerRequest(gene="RPE65", cdna="c.260A>G"))

    assert response == PrimerResponse(mode="sanger", pairs=[])
    assert sequence_service.calls == [{"gene": "RPE65", "cdna": "c.260A>G"}]
    assert primer_provider.calls[0][1].genomic_hg38 == "1-68444869-T-C"


def test_real_mode_crispr_service_uses_sequence_context_and_provider() -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    sequence_service = StaticSequenceContextService(
        SequenceContextResult(query=query, context=_context())
    )
    crispr_provider = FakeCrisprProvider()
    service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=sequence_service,
        primer_provider=FakePrimerProvider(),
        crispr_provider=crispr_provider,
    )

    response = service.design_guides(CrisprRequest(gene="RPE65", cdna="c.260A>G"))

    assert response == CrisprResponse(cas="SpCas9", guides=[], ssodn=None)
    assert sequence_service.calls == [{"gene": "RPE65", "cdna": "c.260A>G"}]
    assert crispr_provider.calls[0][1].genomic_hg38 == "1-68444869-T-C"


def test_real_mode_align_service_uses_sequence_context_and_provider() -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    sequence_service = StaticSequenceContextService(
        SequenceContextResult(query=query, context=_context())
    )
    align_provider = FakeAlignProvider()
    service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=sequence_service,
        primer_provider=FakePrimerProvider(),
        align_provider=align_provider,
    )

    payload = AlignRequest(gene="RPE65", cdna="c.260A>G", user_sequence="ACGT")
    response = service.align(payload)

    assert response == AlignResponse(
        reference="ACGT",
        sanger_read="ACGT",
        match_line="||||",
        mismatch_positions=[],
        target_position=1,
        trace_channels=[],
        base_calls=list("ACGT"),
        q_scores=[],
    )
    assert sequence_service.calls == [{"gene": "RPE65", "cdna": "c.260A>G"}]
    assert align_provider.calls == [(payload, _context())]


def test_real_mode_missing_sequence_context_maps_to_422(client) -> None:
    query = normalize_sequence_query("RPE65", "rs1645931040")
    warning = unsupported_input_warning("rsid")
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, warnings=[warning])
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/primer",
        json={"gene": "RPE65", "cdna": "rs1645931040"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": warning,
        "message": "Workbench sequence context is unavailable for real-mode primer design.",
        "warnings": [warning],
    }


def test_real_mode_crispr_unsupported_cas_maps_to_422(client) -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(
            use_real_apis=True,
            crispr_provider=CRISPR_PROVIDER_LOCAL_DETERMINISTIC,
        ),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, context=_context())
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/crispr",
        json={"gene": "RPE65", "cdna": "c.260A>G", "cas": "SaCas9"},
    )

    warning = unsupported_input_warning("cas")
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": warning,
        "message": "Real-mode CRISPR design currently supports SpCas9 only.",
        "warnings": [warning],
    }


def test_real_mode_crispr_route_returns_local_deterministic_guides(client) -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    context = _context()
    context.window_sequence = "TGGACAAGACAGTCGCCATTCGGTGCCTACATTCAAGAGAACAACGAA"
    context.target_offset = 28
    context.reference_base = "A"
    context.alternate_base = "G"
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(
            use_real_apis=True,
            crispr_provider=CRISPR_PROVIDER_LOCAL_DETERMINISTIC,
        ),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, context=context)
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/crispr",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cas"] == "SpCas9"
    assert body["guides"]
    assert body["guides"][0]["notes"].startswith("Local deterministic SpCas9")
    assert body["ssodn"]["edits_encoded"] == ["c.260A>G"]


def test_real_mode_align_route_aligns_user_sequence_to_sequence_context(client) -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    context = _context()
    context.window_sequence = "TTTAAACCCGGGTTT"
    context.target_offset = 9
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, context=context)
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/align",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "user_sequence": "AAACCCAGG",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reference"] == "AAACCCGGG"
    assert body["sanger_read"] == "AAACCCAGG"
    assert body["match_line"] == "|||||| ||"
    assert body["mismatch_positions"] == [6]
    assert body["target_position"] == 6
    assert body["base_calls"] == list("AAACCCAGG")
    assert body["q_scores"] == []
    assert body["trace_channels"] == []


def test_real_mode_align_requires_read_input_maps_to_422(client) -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, context=_context())
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/align",
        json={"gene": "RPE65", "cdna": "c.260A>G"},
    )

    warning = unsupported_input_warning("alignment_read")
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": warning,
        "message": "Real-mode alignment requires user_sequence or ab1_blob_base64.",
        "warnings": [warning],
    }


def test_real_mode_align_rejects_ambiguous_read_inputs(client) -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, context=_context())
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/align",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "user_sequence": "ACGT",
            "ab1_blob_base64": base64.b64encode(b"synthetic-ab1").decode("ascii"),
        },
    )

    warning = unsupported_input_warning("alignment_read")
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": warning,
        "message": "Provide either user_sequence or ab1_blob_base64, not both.",
        "warnings": [warning],
    }


def test_real_mode_align_rejects_overlong_user_sequence(client) -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, context=_context())
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/align",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "user_sequence": "A" * (ALIGN_MAX_SEQUENCE_BASES + 1),
        },
    )

    warning = unsupported_input_warning("alignment_length")
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": warning,
        "message": (
            "Alignment read is too long for the local Workbench aligner "
            f"({ALIGN_MAX_SEQUENCE_BASES} bp limit)."
        ),
        "warnings": [warning],
    }


def test_real_mode_align_ab1_unsupported_file_maps_to_422(client, monkeypatch) -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")

    def unsupported_trace(_blob):
        raise TraceParseError(
            code=TRACE_UNSUPPORTED_FORMAT,
            message="AB1 trace payload could not be parsed.",
        )

    monkeypatch.setattr(
        "app.services.workbench_design.parse_ab1_base64",
        unsupported_trace,
    )
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, context=_context())
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/align",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "ab1_blob_base64": base64.b64encode(b"not-an-ab1").decode("ascii"),
        },
    )

    warning = unsupported_input_warning("ab1")
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": warning,
        "message": "AB1 trace payload could not be parsed.",
        "warnings": [warning, TRACE_UNSUPPORTED_FORMAT],
    }


def test_real_mode_align_ab1_parser_unavailable_maps_to_503(client, monkeypatch) -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")

    def missing_parser(_blob):
        raise TraceParseError(
            code=TRACE_PARSER_UNAVAILABLE,
            message="Biopython is required to parse AB1 trace files.",
        )

    monkeypatch.setattr(
        "app.services.workbench_design.parse_ab1_base64",
        missing_parser,
    )
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, context=_context())
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/align",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "ab1_blob_base64": base64.b64encode(b"synthetic-ab1").decode("ascii"),
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": WORKBENCH_PROVIDER_UNAVAILABLE,
        "message": "Biopython is required to parse AB1 trace files.",
        "warnings": [WORKBENCH_PROVIDER_UNAVAILABLE, TRACE_PARSER_UNAVAILABLE],
    }


def test_trace_parser_extracts_synthetic_ab1_record() -> None:
    class FakeSeqIO:
        @staticmethod
        def read(handle, file_format):
            assert handle.read() == b"synthetic-ab1"
            assert file_format == "abi"
            return SimpleNamespace(
                seq="ACGT",
                annotations={
                    "abif_raw": {
                        "FWO_1": b"GATC",
                        "DATA9": [0, 10],
                        "DATA10": [0, 5],
                        "DATA11": [4, 8],
                        "DATA12": [2, 2],
                        "PBAS2": b"ACGT",
                        "PCON2": [40, 39, 38, 37],
                        "PLOC2": [3, 6, 9, 12],
                    }
                },
                letter_annotations={"phred_quality": [41, 40, 39, 38]},
            )

    trace = parse_ab1_bytes(b"synthetic-ab1", seqio_module=FakeSeqIO)

    assert trace.sequence == "ACGT"
    assert trace.base_calls == tuple("ACGT")
    assert trace.q_scores == (41, 40, 39, 38)
    assert trace.peak_locations == (3, 6, 9, 12)
    assert [(channel.base, channel.values) for channel in trace.trace_channels] == [
        ("A", (0.0, 1.0)),
        ("T", (0.5, 1.0)),
        ("C", (1.0, 1.0)),
        ("G", (0.0, 1.0)),
    ]


def test_trace_parser_rejects_oversized_base64_before_parser() -> None:
    with pytest.raises(TraceParseError) as error:
        parse_ab1_base64("A" * (TRACE_MAX_ENCODED_BYTES + 1))

    assert error.value.code == TRACE_PAYLOAD_TOO_LARGE


def test_trace_parser_rejects_too_many_base_calls() -> None:
    class FakeSeqIO:
        @staticmethod
        def read(_handle, _file_format):
            return SimpleNamespace(
                seq="A" * (TRACE_MAX_BASE_CALLS + 1),
                annotations={"abif_raw": {}},
                letter_annotations={},
            )

    with pytest.raises(TraceParseError) as error:
        parse_ab1_bytes(b"synthetic-ab1", seqio_module=FakeSeqIO)

    assert error.value.code == TRACE_PAYLOAD_TOO_LARGE


def test_trace_parser_rejects_too_many_channel_samples() -> None:
    class FakeSeqIO:
        @staticmethod
        def read(_handle, _file_format):
            return SimpleNamespace(
                seq="A",
                annotations={
                    "abif_raw": {
                        "FWO_1": b"GATC",
                        "DATA9": [1] * (TRACE_MAX_CHANNEL_SAMPLES + 1),
                    }
                },
                letter_annotations={},
            )

    with pytest.raises(TraceParseError) as error:
        parse_ab1_bytes(b"synthetic-ab1", seqio_module=FakeSeqIO)

    assert error.value.code == TRACE_PAYLOAD_TOO_LARGE


def test_trace_parser_rejects_non_finite_channel_values() -> None:
    class FakeSeqIO:
        @staticmethod
        def read(_handle, _file_format):
            return SimpleNamespace(
                seq="A",
                annotations={
                    "abif_raw": {
                        "FWO_1": b"GATC",
                        "DATA9": [1, float("nan")],
                    }
                },
                letter_annotations={},
            )

    with pytest.raises(TraceParseError) as error:
        parse_ab1_bytes(b"synthetic-ab1", seqio_module=FakeSeqIO)

    assert error.value.code == TRACE_INVALID_SIGNAL


def test_large_alignment_skips_pairwise_matrix(monkeypatch) -> None:
    sequence_length = int(ALIGN_MAX_MATRIX_CELLS**0.5) + 1

    def fail_pairwise(**_kwargs):
        raise AssertionError("pairwise aligner should not run for oversized matrices")

    monkeypatch.setattr("app.services.workbench_design._bio_pairwise_alignment", fail_pairwise)

    cells = _align_sequences(reference="A" * sequence_length, read="A" * sequence_length)

    assert len(cells) == sequence_length
    assert all(cell.reference_base == "A" and cell.read_base == "A" for cell in cells[:5])


def test_primer3_provider_maps_engine_output() -> None:
    class Bindings:
        def __init__(self) -> None:
            self.seq_args = {}
            self.global_args = {}

        def design_primers(self, *, seq_args, global_args):
            self.seq_args = seq_args
            self.global_args = global_args
            return {
                "PRIMER_PAIR_NUM_RETURNED": 1,
                "PRIMER_LEFT_0_SEQUENCE": "AACCGGTTAACCGGTTAA",
                "PRIMER_RIGHT_0_SEQUENCE": "TTGGAACCTTGGAACCTT",
                "PRIMER_LEFT_0_TM": 59.94,
                "PRIMER_RIGHT_0_TM": 60.05,
                "PRIMER_LEFT_0_GC_PERCENT": 44.4,
                "PRIMER_RIGHT_0_GC_PERCENT": 55.5,
                "PRIMER_PAIR_0_PRODUCT_SIZE": 421,
            }

    class Primer3Module:
        bindings = Bindings()

    specificity_provider = QueuedSpecificityProvider([_specificity_result()])
    provider = Primer3PrimerProvider(
        primer3_module=Primer3Module(),
        specificity_provider=specificity_provider,
    )

    response = provider.design(
        payload=PrimerRequest(gene="RPE65", cdna="c.260A>G"),
        context=_context(),
    )

    assert len(response.pairs) == 1
    pair = response.pairs[0]
    assert pair.index == 1
    assert pair.forward == "AACCGGTTAACCGGTTAA"
    assert pair.reverse == "TTGGAACCTTGGAACCTT"
    assert pair.tm_forward == 59.9
    assert pair.tm_reverse == 60.0
    assert pair.gc_forward == 44.4
    assert pair.gc_reverse == 55.5
    assert pair.product_size == 421
    assert pair.specificity_hits == 1
    assert pair.recommended is True
    assert "Primer3 local design" in pair.notes
    assert "Specificity provider note." in pair.notes
    assert specificity_provider.calls[0]["forward"] == "AACCGGTTAACCGGTTAA"
    assert specificity_provider.calls[0]["reverse"] == "TTGGAACCTTGGAACCTT"
    assert specificity_provider.calls[0]["product_min"] == 300
    assert specificity_provider.calls[0]["product_max"] == 700
    assert Primer3Module.bindings.seq_args["SEQUENCE_TARGET"] == [500, 1]
    assert Primer3Module.bindings.global_args["PRIMER_PRODUCT_SIZE_RANGE"] == [[300, 700]]


def test_primer3_provider_recommends_first_single_intended_specificity_hit() -> None:
    class Bindings:
        def design_primers(self, *, seq_args, global_args):
            return {
                "PRIMER_PAIR_NUM_RETURNED": 2,
                "PRIMER_LEFT_0_SEQUENCE": "AAAAAAAAAAAAAAAAAAAA",
                "PRIMER_RIGHT_0_SEQUENCE": "CCCCCCCCCCCCCCCCCCCC",
                "PRIMER_LEFT_0_TM": 60.0,
                "PRIMER_RIGHT_0_TM": 60.0,
                "PRIMER_LEFT_0_GC_PERCENT": 0.0,
                "PRIMER_RIGHT_0_GC_PERCENT": 100.0,
                "PRIMER_PAIR_0_PRODUCT_SIZE": 421,
                "PRIMER_LEFT_1_SEQUENCE": "TTTTTTTTTTTTTTTTTTTT",
                "PRIMER_RIGHT_1_SEQUENCE": "GGGGGGGGGGGGGGGGGGGG",
                "PRIMER_LEFT_1_TM": 60.0,
                "PRIMER_RIGHT_1_TM": 60.0,
                "PRIMER_LEFT_1_GC_PERCENT": 0.0,
                "PRIMER_RIGHT_1_GC_PERCENT": 100.0,
                "PRIMER_PAIR_1_PRODUCT_SIZE": 517,
            }

    class Primer3Module:
        bindings = Bindings()

    provider = Primer3PrimerProvider(
        primer3_module=Primer3Module(),
        specificity_provider=QueuedSpecificityProvider(
            [
                _specificity_result(hits=2, intended_hits=1, product_sizes=(421, 530)),
                _specificity_result(hits=1, intended_hits=1, product_sizes=(517,)),
            ]
        ),
    )

    response = provider.design(
        payload=PrimerRequest(gene="RPE65", cdna="c.260A>G"),
        context=_context(),
    )

    assert [pair.recommended for pair in response.pairs] == [False, True]


@pytest.mark.parametrize(
    "forward,reverse,reverse_template,middle_size,expected_size",
    [
        (
            "CCTTCAGGTTCATCCGCACT",
            "AGAGGCAATCAGTGCAGTCC",
            "GGACTGCACTGATTGCCTCT",
            477,
            517,
        ),
        (
            "GCTGTACGGATTGCTCCTGT",
            "ACACCAATTGCAGGAAAGCAT",
            "ATGCTTTCCTGCAATTGGTGT",
            550,
            591,
        ),
    ],
)
def test_template_specificity_counts_user_validated_rpe65_amplicons(
    forward: str,
    reverse: str,
    reverse_template: str,
    middle_size: int,
    expected_size: int,
) -> None:
    template = f"{'N' * 15}{forward}{'A' * middle_size}{reverse_template}{'N' * 15}"
    context = _context()
    context.window_sequence = template
    context.target_offset = 15 + len(forward) + 20

    result = TemplateAmpliconSpecificityProvider().check(
        forward=forward,
        reverse=reverse,
        product_min=500,
        product_max=1000,
        context=context,
    )

    assert result.hits == 1
    assert result.intended_hits == 1
    assert result.product_sizes == (expected_size,)
    assert f"{expected_size} bp" in result.note


def test_local_ispcr_specificity_provider_maps_whole_genome_products(tmp_path: Path) -> None:
    binary_path = tmp_path / "isPcr"
    genome_path = tmp_path / "hg38.2bit"
    binary_path.write_text("stub", encoding="utf-8")
    genome_path.write_text("stub", encoding="utf-8")
    calls: list[tuple[list[str], dict]] = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        stdout = "\n".join(
            [
                ">RPE65_c.260A>G chr1:68444500+68445000",
                "A" * 501,
                ">RPE65_c.260A>G chr2:1000+1400",
                "C" * 401,
            ]
        )
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    provider = LocalIsPcrSpecificityProvider(
        _settings(
            ucsc_ispcr_timeout_seconds=2.5,
            ucsc_ispcr_min_perfect=16,
            ucsc_ispcr_min_good=18,
        ),
        binary_path=binary_path,
        genome_path=genome_path,
        runner=runner,
    )

    result = provider.check(
        forward="AACCGGTTAACCGGTTAA",
        reverse="TTGGAACCTTGGAACCTT",
        product_min=300,
        product_max=700,
        context=_context(),
    )

    assert result.hits == 2
    assert result.intended_hits == 1
    assert result.product_sizes == (401, 501)
    assert "UCSC isPcr whole-genome hg38 specificity screen" in result.note
    command, kwargs = calls[0]
    assert command == [
        str(binary_path),
        "-minSize=300",
        "-maxSize=700",
        "-minPerfect=16",
        "-minGood=18",
        str(genome_path),
        "stdin",
        "stdout",
    ]
    assert kwargs["input"] == "RPE65_c.260A>G\tAACCGGTTAACCGGTTAA\tTTGGAACCTTGGAACCTT\n"
    assert kwargs["timeout"] == 2.5
    assert kwargs["check"] is False


def test_local_ispcr_specificity_provider_requires_local_assets(tmp_path: Path) -> None:
    provider = LocalIsPcrSpecificityProvider(
        _settings(),
        binary_path=tmp_path / "missing-isPcr",
        genome_path=tmp_path / "missing-hg38.2bit",
    )

    with pytest.raises(WorkbenchDesignError) as error:
        provider.check(
            forward="AACCGGTTAACCGGTTAA",
            reverse="TTGGAACCTTGGAACCTT",
            product_min=300,
            product_max=700,
            context=_context(),
        )

    assert error.value.code == WORKBENCH_PROVIDER_UNAVAILABLE
    assert error.value.status_code == 503


def test_workbench_service_can_opt_into_local_ispcr_specificity_provider() -> None:
    service = WorkbenchDesignService(
        settings=_settings(primer_specificity_provider=PRIMER_SPECIFICITY_UCSC_ISPCR)
    )

    assert isinstance(service.primer_provider, Primer3PrimerProvider)
    assert isinstance(service.primer_provider.specificity_provider, LocalIsPcrSpecificityProvider)


def test_workbench_service_uses_local_deterministic_crispr_provider_by_default() -> None:
    service = WorkbenchDesignService(
        settings=_settings(crispr_provider=CRISPR_PROVIDER_LOCAL_DETERMINISTIC)
    )

    assert isinstance(service.crispr_provider, LocalDeterministicCrisprProvider)


def test_workbench_service_can_opt_into_crisprscore_r_provider() -> None:
    service = WorkbenchDesignService(
        settings=_settings(
            crispr_provider=CRISPR_PROVIDER_CRISPRSCORE_R,
            crispr_rscript_path=Path("C:/R/bin/Rscript.exe"),
            crispr_ruleset3_conda_env=Path("C:/conda/envs/ruleset3"),
            crispr_lindel_conda_env=Path("C:/conda/envs/lindel"),
        )
    )

    assert isinstance(service.crispr_provider, CrisprScoreRBackedCrisprProvider)
    fallback = service.crispr_provider.fallback_provider
    assert isinstance(fallback.scoring_adapter, CrisprScoreRAdapter)
    assert fallback.scoring_adapter.rscript_path == Path("C:/R/bin/Rscript.exe")
    assert Path(fallback.scoring_adapter.rule_set3_conda_env or "") == Path(
        "C:/conda/envs/ruleset3"
    )
    assert Path(fallback.scoring_adapter.lindel_conda_env or "") == Path("C:/conda/envs/lindel")
