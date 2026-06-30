from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import status

from app.core.config import Settings
from app.schemas.workbench import (
    AlignReferenceResponse,
    AlignRequest,
    AlignResponse,
    AlignTraceRequest,
    AlignTraceResponse,
    CrisprOffTargetRequest,
    CrisprOffTargetResponse,
    CrisprRequest,
    CrisprResponse,
    CrisprSsodnRequest,
    CrisprTideResponse,
    PrimerPair,
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
from app.services.crispr_offtarget_index import build_spcas9_offtarget_index_from_sequences
from app.services.dbsnp_local import DbSnpLocalStore
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
    LocalDbSnpPrimerSnpMaskingProvider,
    LocalIsPcrSpecificityProvider,
    PrimerSpecificityResult,
    Primer3PrimerProvider,
    TemplateAmpliconSpecificityProvider,
    WorkbenchDesignError,
    WorkbenchDesignService,
    _align_sequences,
)
from app.services.crispr_offtarget_screening import (
    MOCK_SCREENING_TEMPLATE_WARNING,
    IndexedSqliteCrisprOffTargetProvider,
)
from app.services.crispr_ssodn import SSODN_MOCK_GENOMIC_WINDOW_WARNING
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
LOCAL_HG38_2BIT_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "bio_assets" / "genomes" / "hg38.2bit"
)
LOCAL_MANE_GFF_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "bio_assets"
    / "transcripts"
    / "MANE.GRCh38.v1.5.refseq_genomic.gff.gz"
)
RPE65_SSODN_PUBLIC_FINGERPRINTS = {
    "c.247T>C": (57, 56, "6c46cf72520215eea658884e717ff5734011e9b386128128188b2b2edf665718"),
    "c.419G>A": (61, 0, "11d3503e6bfb8b040fdba34b5d42a959d00a2a72105eb6f5a8f74cee11ef4b4b"),
    "c.65T>C": (61, 37, "2c300ad88a378d16d1d070d54103360bfa2c5d55111242fe7f72a07837956f71"),
    "c.675C>G": (62, 38, "094f579c803ccec699ffce58134ce8fac0b4d2e4be33d997d6b685db9edce4cc"),
    "c.881A>C": (61, 39, "3decd801aa812943ad7881b5fb6bdf695a1973cacac4807694a164a1f0e80662"),
    "c.1301C>T": (61, 25, "2939082cd5fbe5d2fe0317453488aaf4a22f91ea0966a85cb0003794dfc9072b"),
    "c.260A>G": (61, 47, "5496370ed7a8d38bceaf7fb6b6e7bc850717829338e77648b492890b4532e69d"),
}


class FailingWorkbenchService:
    def __init__(self, error: WorkbenchDesignError) -> None:
        self.error = error

    def design_primers(self, _payload):
        raise self.error

    def design_guides(self, _payload):
        raise self.error

    def enumerate_crispr_offtargets(self, _payload):
        raise self.error

    def design_crispr_screening_primers(self, _payload):
        raise self.error

    def design_crispr_ssodn(self, _payload):
        raise self.error

    def resolve_align_reference(self, _payload):
        raise self.error

    def align(self, _payload):
        raise self.error

    def analyze_trace(self, _payload):
        raise self.error

    def analyze_crispr_tide(self, **_kwargs):
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


class FakeScreeningPrimerProvider:
    def __init__(self, pairs: list[PrimerPair] | None = None) -> None:
        self.pairs = pairs if pairs is not None else []
        self.calls: list[tuple] = []

    def design(self, payload, context) -> PrimerResponse:
        self.calls.append((payload, context))
        return PrimerResponse(mode=payload.mode, pairs=self.pairs)


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


def _rpe65_vus1_ab1_blob() -> str:
    return base64.b64encode((FIXTURES_DIR / "rpe65_vus1.ab1").read_bytes()).decode("ascii")


class QueuedSpecificityProvider:
    def __init__(self, results: list[PrimerSpecificityResult]) -> None:
        self.results = results
        self.calls: list[dict] = []

    def check(self, **kwargs) -> PrimerSpecificityResult:
        self.calls.append(kwargs)
        return self.results.pop(0)


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _require_local_ssodn_assets() -> None:
    missing = [path for path in (LOCAL_HG38_2BIT_PATH, LOCAL_MANE_GFF_PATH) if not path.is_file()]
    if missing:
        pytest.skip(f"local ssODN runtime asset(s) absent: {', '.join(map(str, missing))}")


def _settings(**overrides) -> Settings:
    return Settings(jwt_secret="test-secret", **overrides)


def _app_settings(tmp_path: Path, **overrides) -> Settings:
    return Settings(
        upload_dir=tmp_path / "uploads",
        final_report_dir=tmp_path / "final_reports",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'app.db').as_posix()}",
        jwt_secret="test-secret",
        **overrides,
    )


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


def _synthetic_context(
    *,
    gene: str = "BRCA1",
    cdna: str = "c.100A>G",
    transcript: str = "NM_007294.4",
    genomic_hg38: str = "17-43044295-A-G",
) -> SequenceContext:
    return SequenceContext(
        gene=gene,
        cdna=cdna,
        transcript=transcript,
        transcript_hgvs=f"{transcript}:{cdna}",
        query_kind="cdna",
        genome_build="GRCh38",
        genomic_hg38=genomic_hg38,
        window_sequence="ACGT" * 260,
        target_offset=320,
        reference_base="A",
        alternate_base="G",
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


def test_crispr_offtargets_route_returns_deidentified_fixture_shape(client) -> None:
    response = client.post(
        "/api/v1/crispr/offtargets",
        json={
            "guide": "GAGTCCGAGCAGAAGAAGAT",
            "pam": "NGG",
            "max_mismatches": 2,
            "on_target_locus": {
                "chromosome": "7",
                "position": 117509080,
                "strand": "+",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body == _fixture("crispr_offtargets_deidentified.json")
    assert set(body) == {"genome_build", "sites", "source_disclosure"}
    assert body["source_disclosure"]["source_status"] == "fallback"
    assert body["source_disclosure"]["provider_id"] == "mock_cas_offinder"
    assert set(body["sites"][0]) == {
        "sequence",
        "pam",
        "score",
        "mismatches",
        "gene",
        "gene_id",
        "biotype",
        "chromosome",
        "strand",
        "position",
        "on_target",
    }
    assert body["sites"][0]["on_target"] is True
    assert all(site["mismatches"] <= 2 for site in body["sites"])


def test_crispr_offtargets_service_is_deterministic_against_fixture() -> None:
    payload = CrisprOffTargetRequest(
        guide="GAGTCCGAGCAGAAGAAGAT",
        pam="NGG",
        max_mismatches=2,
        on_target_locus={"chromosome": "7", "position": 117509080, "strand": "+"},
    )
    service = WorkbenchDesignService(settings=_settings(use_real_apis=False))

    first = service.enumerate_crispr_offtargets(payload)
    second = service.enumerate_crispr_offtargets(payload)

    assert isinstance(first, CrisprOffTargetResponse)
    assert first == second
    assert first.model_dump() == _fixture("crispr_offtargets_deidentified.json")


def test_crispr_offtargets_indexed_provider_returns_index_hits(tmp_path: Path) -> None:
    guide = "GAGTCCGAGCAGAAGAAGAT"
    mismatch = "C" + guide[1:]
    index_path = tmp_path / "spcas9_offtargets.sqlite"
    build_spcas9_offtarget_index_from_sequences(
        [
            ("1", f"{guide}AGG{'N' * 40}"),
            ("2", f"{'N' * 4}{mismatch}TGG{'N' * 40}"),
        ],
        index_path,
        genome_build="GRCh38",
        source_version="pytest-mini",
    )
    service = WorkbenchDesignService(
        settings=_settings(
            workbench_live_design_enabled=True,
            crispr_offtarget_provider="auto",
            crispr_offtarget_index_path=index_path,
        )
    )

    response = service.enumerate_crispr_offtargets(
        CrisprOffTargetRequest(
            guide=guide,
            pam="NGG",
            max_mismatches=1,
            on_target_locus={"chromosome": "1", "position": 18, "strand": "+"},
        )
    )

    assert isinstance(service.crispr_offtarget_provider, IndexedSqliteCrisprOffTargetProvider)
    assert response.genome_build == "GRCh38"
    assert [site.mismatches for site in response.sites] == [0, 1]
    assert response.sites[0].on_target is True
    assert response.sites[0].chromosome == "chr1"
    assert response.sites[1].sequence == mismatch
    assert response.sites[1].chromosome == "chr2"
    assert response.sites[1].on_target is False


def test_crispr_offtargets_route_indexed_provider_returns_index_hits(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    guide = "GAGTCCGAGCAGAAGAAGAT"
    mismatch = "C" + guide[1:]
    index_path = tmp_path / "spcas9_offtargets.sqlite"
    build_spcas9_offtarget_index_from_sequences(
        [
            ("1", f"{guide}AGG{'N' * 40}"),
            ("2", f"{'N' * 4}{mismatch}TGG{'N' * 40}"),
        ],
        index_path,
        genome_build="GRCh38",
        source_version="pytest-mini",
    )
    settings = _app_settings(
        tmp_path,
        workbench_live_design_enabled=True,
        crispr_offtarget_provider="indexed_sqlite",
        crispr_offtarget_index_path=index_path,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.post(
            "/api/v1/crispr/offtargets",
            json={
                "guide": guide,
                "pam": "NGG",
                "max_mismatches": 1,
                "on_target_locus": {"chromosome": "1", "position": 18, "strand": "+"},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["genome_build"] == "GRCh38"
    assert [site["mismatches"] for site in body["sites"]] == [0, 1]
    assert body["sites"][0]["chromosome"] == "chr1"
    assert body["sites"][1]["sequence"] == mismatch
    assert body["sites"][1]["chromosome"] == "chr2"
    assert all(site["gene"] != "OTSG1" for site in body["sites"])


def test_crispr_offtargets_route_auto_missing_index_uses_mock_fallback(
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    settings = _app_settings(
        tmp_path,
        workbench_live_design_enabled=True,
        crispr_offtarget_provider="auto",
        crispr_offtarget_index_path=tmp_path / "missing.sqlite",
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.post(
            "/api/v1/crispr/offtargets",
            json={
                "guide": "GAGTCCGAGCAGAAGAAGAT",
                "pam": "NGG",
                "max_mismatches": 1,
                "on_target_locus": {"chromosome": "7", "position": 117509080, "strand": "+"},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["genome_build"] == "GRCh38"
    assert body["sites"][0]["on_target"] is True
    assert body["sites"][0]["chromosome"] == "chr7"
    assert any(site["gene"] == "OTSG1" for site in body["sites"])


def test_crispr_offtargets_forced_index_missing_maps_to_503(tmp_path: Path) -> None:
    service = WorkbenchDesignService(
        settings=_settings(
            workbench_live_design_enabled=True,
            crispr_offtarget_provider="indexed_sqlite",
            crispr_offtarget_index_path=tmp_path / "missing.sqlite",
        )
    )

    with pytest.raises(WorkbenchDesignError) as exc_info:
        service.enumerate_crispr_offtargets(CrisprOffTargetRequest(guide="GAGTCCGAGCAGAAGAAGAT"))

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc_info.value.code == "crispr_offtarget_index_unavailable"


def test_crispr_offtargets_route_forced_index_missing_fails_closed(
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app

    settings = _app_settings(
        tmp_path,
        workbench_live_design_enabled=True,
        crispr_offtarget_provider="indexed_sqlite",
        crispr_offtarget_index_path=tmp_path / "missing.sqlite",
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.post(
            "/api/v1/crispr/offtargets",
            json={"guide": "GAGTCCGAGCAGAAGAAGAT"},
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    detail = response.json()["detail"]
    assert detail["code"] == "crispr_offtarget_index_unavailable"
    assert detail["warnings"] == ["crispr_offtarget_index_unavailable"]


def test_crispr_ssodn_route_returns_lab_ordered_rpe65_donor(client) -> None:
    _require_local_ssodn_assets()

    response = client.post(
        "/api/v1/crispr/ssodn",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "protein_change": "p.Asp87Gly",
        },
    )

    assert response.status_code == 200
    body = response.json()
    ssodn = body["ssodn"]
    assert body["genome_build"] == "GRCh38"
    assert body["warnings"] == []
    assert ssodn["template_source"] == "local_mane_hg38_transcript"
    assert ssodn["oligo_length"] == 120
    assert ssodn["variant_offset"] == 61
    assert ssodn["arm_lengths"] == {"left": 61, "right": 58}
    assert ssodn["reference_arm"][61] == "A"
    assert ssodn["oligo_sequence"][61] == "G"
    assert ssodn["repair_template"] == ssodn["oligo_sequence"]
    assert ssodn["strand"] == "-"
    assert ssodn["orientation"] == "sense"
    assert ssodn["protocol"] == "lab_genomic"
    assert ssodn["oligo_name"] == "ss oligo for c.260A>G; p.Asp87Gly; GAT > GGT"
    assert ssodn["variant_genomic"] == "chr1:68444869"
    assert len(ssodn["intron_mask"]) == 120
    assert sum(ssodn["intron_mask"]) == 47
    assert ssodn["oligo_sequence"].isupper()


@pytest.mark.parametrize(
    "cdna,expected_offset,expected_intron_count,expected_sha256",
    [
        (cdna, offset, intron_count, digest)
        for cdna, (offset, intron_count, digest) in RPE65_SSODN_PUBLIC_FINGERPRINTS.items()
    ],
)
def test_crispr_ssodn_public_rpe65_examples_match_expected_ordered_donor(
    cdna: str,
    expected_offset: int,
    expected_intron_count: int,
    expected_sha256: str,
) -> None:
    _require_local_ssodn_assets()
    service = WorkbenchDesignService(settings=_settings(use_real_apis=False))

    response = service.design_crispr_ssodn(CrisprSsodnRequest(gene="RPE65", cdna=cdna))

    assert response.warnings == []
    assert response.ssodn.template_source == "local_mane_hg38_transcript"
    assert response.ssodn.oligo_length == 120
    assert response.ssodn.variant_offset == expected_offset
    if cdna == "c.260A>G":
        assert response.ssodn.variant_genomic == "chr1:68444869"
    assert sum(response.ssodn.intron_mask) == expected_intron_count
    assert hashlib.sha256(response.ssodn.oligo_sequence.encode("ascii")).hexdigest() == (
        expected_sha256
    )


def test_crispr_ssodn_non_default_length_recalculates_centered_offset() -> None:
    _require_local_ssodn_assets()
    service = WorkbenchDesignService(settings=_settings(use_real_apis=False))

    response = service.design_crispr_ssodn(
        CrisprSsodnRequest(gene="RPE65", cdna="c.260A>G", oligo_length=100)
    )

    assert response.ssodn.oligo_length == 100
    assert response.ssodn.variant_offset == 51
    assert response.ssodn.arm_lengths == {"left": 51, "right": 48}
    assert len(response.ssodn.oligo_sequence) == 100
    assert len(response.ssodn.intron_mask) == 100
    assert response.ssodn.reference_arm[51] == "A"
    assert response.ssodn.oligo_sequence[51] == "G"


def test_crispr_ssodn_falls_back_to_sequence_context_mock_when_local_assets_do_not_apply(
    client,
) -> None:
    query = normalize_sequence_query("TEST", "c.1A>G")
    context = _context()
    context.gene = "TEST"
    context.cdna = "c.1A>G"
    context.transcript = "NM_TEST.1"
    context.window_sequence = "A"
    context.target_offset = 0
    context.reference_base = "A"
    context.alternate_base = "G"
    context.strand = "+"
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=False),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, context=context)
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/crispr/ssodn",
        json={"gene": "TEST", "cdna": "c.1A>G", "oligo_length": 100},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["warnings"] == [SSODN_MOCK_GENOMIC_WINDOW_WARNING]
    assert body["ssodn"]["template_source"] == "mock_genomic_window"
    assert body["ssodn"]["variant_offset"] == 49
    assert body["ssodn"]["variant_genomic"] is None
    assert body["ssodn"]["reference_arm"][49] == "A"
    assert body["ssodn"]["oligo_sequence"][49] == "G"


def test_crispr_ssodn_sequence_context_window_reports_variant_genomic() -> None:
    query = normalize_sequence_query("TEST", "c.1A>G")
    context = _context()
    context.gene = "TEST"
    context.cdna = "c.1A>G"
    context.transcript = "NM_TEST.1"
    context.genomic_hg38 = "7-117509080-A-G"
    context.window_sequence = ("C" * 49) + "A" + ("C" * 50)
    context.target_offset = 49
    context.reference_base = "A"
    context.alternate_base = "G"
    context.strand = "+"
    service = WorkbenchDesignService(
        settings=_settings(use_real_apis=False),
        sequence_context_service=StaticSequenceContextService(
            SequenceContextResult(query=query, context=context)
        ),
        primer_provider=FakePrimerProvider(),
    )

    response = service.design_crispr_ssodn(
        CrisprSsodnRequest(gene="TEST", cdna="c.1A>G", oligo_length=100)
    )

    assert response.ssodn.template_source == "sequence_context"
    assert response.ssodn.variant_genomic == "chr7:117509080"
    assert response.ssodn.reference_arm[49] == "A"
    assert response.ssodn.oligo_sequence[49] == "G"


def test_crispr_offtargets_unsupported_enzyme_maps_to_422(client) -> None:
    response = client.post(
        "/api/v1/crispr/offtargets",
        json={
            "guide": "GAGTCCGAGCAGAAGAAGAT",
            "enzyme": "SaCas9",
        },
    )

    warning = unsupported_input_warning("enzyme")
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": warning,
        "message": "CRISPR off-target screening currently supports SpCas9 NGG only.",
        "warnings": [warning],
    }


def test_crispr_screening_primers_route_maps_primer_pair(client) -> None:
    pair = PrimerPair(
        index=1,
        forward="AACCGGTTAACCGGTTAA",
        reverse="TTGGAACCTTGGAACCTT",
        tm_forward=59.9,
        tm_reverse=60.1,
        gc_forward=44.4,
        gc_reverse=55.5,
        product_size=421,
        specificity_hits=3,
        secondary_structure_risk="moderate",
        secondary_structure_notes=(
            "Primer3 thermodynamic secondary-structure screen moderate; "
            "max pair complement-end 38.2."
        ),
        notes="Synthetic primer engine result.",
        recommended=True,
    )
    primer_provider = FakeScreeningPrimerProvider([pair])
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=False),
        primer_provider=primer_provider,
    )

    response = client.post(
        "/api/v1/crispr/screening-primers",
        json={
            "naming_prefix": "11.1 Cor",
            "sites": [
                {
                    "site_index": 1,
                    "point": "chr7:117509080",
                    "template_sequence": "A" * 900,
                    "target_offset": 400,
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "sanger"
    assert body["warnings"] == []
    assert body["primers"] == [
        {
            "site_index": 1,
            "point": "chr7:117509080",
            "region": "chr7:117508680-117509480",
            "name_forward": "11.1_Cor_1_F",
            "name_reverse": "11.1_Cor_1_R",
            "forward": "AACCGGTTAACCGGTTAA",
            "reverse": "TTGGAACCTTGGAACCTT",
            "tm_forward": 59.9,
            "tm_reverse": 60.1,
            "gc_forward": 44.4,
            "gc_reverse": 55.5,
            "product_size": 421,
            "specificity_hits": 3,
            "other_products": "2 other product(s); see notes",
            "secondary_structure_risk": "moderate",
            "secondary_structure_notes": (
                "Primer3 thermodynamic secondary-structure screen moderate; "
                "max pair complement-end 38.2."
            ),
            "recommended": True,
            "notes": "Synthetic primer engine result.",
            "template_source": "template_sequence",
        }
    ]
    primer_payload, context = primer_provider.calls[0]
    assert primer_payload == PrimerRequest(
        gene="CRISPR_SCREENING",
        cdna="site-1",
        mode="sanger",
    )
    assert context.window_sequence == "A" * 900
    assert context.target_offset == 400
    assert context.genomic_hg38 == "7-117509080-N-N"


def test_crispr_screening_primers_region_without_template_uses_mock_window(client) -> None:
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=False),
        primer_provider=FakeScreeningPrimerProvider(),
    )

    response = client.post(
        "/api/v1/crispr/screening-primers",
        json={
            "flank_bp": 50,
            "sites": [
                {
                    "site_index": 1,
                    "chromosome": "12",
                    "position": 102912875,
                    "sequence": "GAGTGCGAGCAGAAGAATAT",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["primers"] == []
    assert body["warnings"] == [
        MOCK_SCREENING_TEMPLATE_WARNING,
        "crispr_screening_primer_unavailable:site_1",
    ]


def test_crispr_screening_primers_region_uses_reference_window_provider(client) -> None:
    class ReferenceWindowProvider:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, int, str | None]] = []

        def get_sequence(self, chrom: str, start: int, end: int, build: str | None = None):
            self.calls.append((chrom, start, end, build))
            return SimpleNamespace(sequence="C" * 101, genome_build=build or "GRCh38")

    pair = PrimerPair(
        index=1,
        forward="AACCGGTTAACCGGTTAA",
        reverse="TTGGAACCTTGGAACCTT",
        tm_forward=59.9,
        tm_reverse=60.1,
        gc_forward=44.4,
        gc_reverse=55.5,
        product_size=101,
        specificity_hits=1,
        notes="Reference-backed screening primer.",
        recommended=True,
    )
    primer_provider = FakeScreeningPrimerProvider([pair])
    reference_provider = ReferenceWindowProvider()
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=False),
        primer_provider=primer_provider,
        screening_reference_provider=reference_provider,
    )

    response = client.post(
        "/api/v1/crispr/screening-primers",
        json={
            "flank_bp": 50,
            "sites": [
                {
                    "site_index": 1,
                    "chromosome": "12",
                    "position": 102912875,
                    "sequence": "GAGTGCGAGCAGAAGAATAT",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["warnings"] == []
    assert body["primers"][0]["template_source"] == "reference_window"
    assert reference_provider.calls == [("chr12", 102912825, 102912925, "GRCh38")]
    primer_payload, context = primer_provider.calls[0]
    assert primer_payload.avoid_snps is True
    assert context.window_sequence == "C" * 101
    assert context.target_offset == 50
    assert context.source_metadata["template_source"] == "reference_window"


def test_crispr_screening_primers_missing_locus_maps_to_422(client) -> None:
    response = client.post(
        "/api/v1/crispr/screening-primers",
        json={"sites": [{"site_index": 1, "template_sequence": "A" * 900}]},
    )

    warning = unsupported_input_warning("screening_locus")
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": warning,
        "message": (
            "Screening-primer targets require chromosome and position, "
            "or a point formatted as chrN:position."
        ),
        "warnings": [warning],
    }


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/v1/primer", {"gene": "RPE65", "cdna": "c.260A>G"}),
        ("/api/v1/crispr", {"gene": "RPE65", "cdna": "c.260A>G"}),
        ("/api/v1/crispr/offtargets", {"guide": "GAGTCCGAGCAGAAGAAGAT"}),
        ("/api/v1/crispr/ssodn", {"gene": "RPE65", "cdna": "c.260A>G"}),
        (
            "/api/v1/crispr/screening-primers",
            {"sites": [{"site_index": 1, "point": "chr7:117509080"}]},
        ),
        ("/api/v1/align", {"gene": "RPE65", "cdna": "c.260A>G"}),
        ("/api/v1/align/reference", {"gene": "RPE65", "cdna": "c.260A>G"}),
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


def test_align_trace_endpoint_analyzes_rpe65_vus1_ab1_in_fixture_mode(client) -> None:
    response = client.post(
        "/api/v1/align/trace",
        json={"ab1_blob_base64": _rpe65_vus1_ab1_blob()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sequence"].startswith("AACGGAGGATA")
    assert len(body["base_calls"]) == 570
    assert len(body["q_scores"]) == 570
    assert len(body["base_confidence"]) == 570
    assert len(body["peak_locations"]) == 570
    assert body["sample_count"] == 16506
    assert [channel["base"] for channel in body["trace_channels"]] == ["A", "T", "C", "G"]
    assert body["trim"] == {
        "start": 25,
        "end": 568,
        "method": "modified_mott_q20_phfinder3",
        "q_cutoff": 20,
    }
    assert body["noise_floor"] >= 1.0
    assert body["warnings"] == []
    assert body["het"]
    assert all(body["trim"]["start"] <= call["index"] < body["trim"]["end"] for call in body["het"])
    assert all(call["main_ratio"] >= 0.5 for call in body["het"])


def test_crispr_tide_endpoint_returns_observed_only_source_backed_spectrum(client) -> None:
    trace_bytes = (FIXTURES_DIR / "rpe65_vus1.ab1").read_bytes()

    response = client.post(
        "/api/v1/crispr/tide?cut_site_index=100",
        files={
            "control_file": ("control.ab1", trace_bytes, "application/octet-stream"),
            "edited_file": ("edited.ab1", trace_bytes, "application/octet-stream"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_backed"] is True
    assert body["analysis_kind"] == "tide"
    assert body["provider_label"] == "Eamos observed-only TIDE-style analyzer"
    assert body["cut_site_index"] == 100
    assert body["editing_efficiency"] == 0.0
    assert body["r_squared"] == 1.0
    assert body["spectrum"] == [{"size": 0, "observed": 1.0, "predicted": None}]
    assert body["predicted_available"] is False
    assert "observed-only" in body["notes"].lower()
    assert "crispr_tide_consensus_only" in body["warnings"]


def test_workbench_service_crispr_tide_is_always_on_without_real_apis() -> None:
    service = WorkbenchDesignService(settings=_settings(use_real_apis=False))
    trace_bytes = (FIXTURES_DIR / "rpe65_vus1.ab1").read_bytes()

    response = service.analyze_crispr_tide(
        control_bytes=trace_bytes,
        edited_bytes=trace_bytes,
        cut_site_index=100,
    )

    assert isinstance(response, CrisprTideResponse)
    assert response.source_backed is True
    assert response.analysis_kind == "tide"
    assert response.editing_efficiency == 0.0
    assert response.spectrum[0].size == 0
    assert response.spectrum[0].observed == 1.0


def test_crispr_tide_unsupported_trace_upload_maps_to_422(client) -> None:
    trace_bytes = (FIXTURES_DIR / "rpe65_vus1.ab1").read_bytes()

    response = client.post(
        "/api/v1/crispr/tide?cut_site_index=100",
        files={
            "control_file": ("control.ab1", b"not-an-ab1", "application/octet-stream"),
            "edited_file": ("edited.ab1", trace_bytes, "application/octet-stream"),
        },
    )

    warning = unsupported_input_warning("ab1")
    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": warning,
        "message": "AB1 trace payload could not be parsed.",
        "warnings": [warning, TRACE_UNSUPPORTED_FORMAT],
    }


def test_crispr_tide_parser_unavailable_maps_to_503(client, monkeypatch) -> None:
    def missing_parser(_data):
        raise TraceParseError(
            code=TRACE_PARSER_UNAVAILABLE,
            message="Biopython is required to parse AB1 trace files.",
        )

    monkeypatch.setattr(
        "app.services.workbench_design.parse_ab1_bytes",
        missing_parser,
    )

    response = client.post(
        "/api/v1/crispr/tide?cut_site_index=100",
        files={
            "control_file": ("control.ab1", b"synthetic-ab1", "application/octet-stream"),
            "edited_file": ("edited.ab1", b"synthetic-ab1", "application/octet-stream"),
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": WORKBENCH_PROVIDER_UNAVAILABLE,
        "message": "Biopython is required to parse AB1 trace files.",
        "warnings": [WORKBENCH_PROVIDER_UNAVAILABLE, TRACE_PARSER_UNAVAILABLE],
    }


def test_workbench_service_analyze_trace_is_always_on_without_real_apis() -> None:
    service = WorkbenchDesignService(settings=_settings(use_real_apis=False))

    response = service.analyze_trace(AlignTraceRequest(ab1_blob_base64=_rpe65_vus1_ab1_blob()))

    assert isinstance(response, AlignTraceResponse)
    assert response.trim.method == "modified_mott_q20_phfinder3"
    assert response.trim.start == 25
    assert response.trim.end == 568
    assert len(response.het) >= 1


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

    assert response.mode == "sanger"
    assert response.pairs == []
    assert response.source_disclosure is not None
    assert response.source_disclosure.source_status == "local_provider"
    assert response.source_disclosure.provider_id == "primer3_template_specificity"
    assert sequence_service.calls == [
        {"gene": "RPE65", "cdna": "c.260A>G", "prefer_resolver": True}
    ]
    assert primer_provider.calls[0][1].genomic_hg38 == "1-68444869-T-C"


def test_workbench_live_design_uses_provider_without_global_real_apis() -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    sequence_service = StaticSequenceContextService(
        SequenceContextResult(query=query, context=_context())
    )
    primer_provider = FakePrimerProvider()
    service = WorkbenchDesignService(
        settings=_settings(use_real_apis=False),
        sequence_context_service=sequence_service,
        primer_provider=primer_provider,
    )

    response = service.design_primers(PrimerRequest(gene="RPE65", cdna="c.260A>G"))

    assert response.mode == "sanger"
    assert response.pairs == []
    assert response.source_disclosure is not None
    assert response.source_disclosure.source_status == "local_provider"
    assert response.source_disclosure.provider_id == "primer3_template_specificity"
    assert sequence_service.calls == [
        {"gene": "RPE65", "cdna": "c.260A>G", "prefer_resolver": True}
    ]
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

    assert response.cas == "SpCas9"
    assert response.guides == []
    assert response.ssodn is None
    assert response.source_disclosure is not None
    assert response.source_disclosure.source_status == "local_provider"
    assert response.source_disclosure.provider_id == "local_deterministic_spcas9"
    assert sequence_service.calls == [
        {"gene": "RPE65", "cdna": "c.260A>G", "prefer_resolver": True}
    ]
    assert crispr_provider.calls[0][1].genomic_hg38 == "1-68444869-T-C"


def test_workbench_live_design_uses_crispr_provider_without_global_real_apis() -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G")
    sequence_service = StaticSequenceContextService(
        SequenceContextResult(query=query, context=_context())
    )
    crispr_provider = FakeCrisprProvider()
    service = WorkbenchDesignService(
        settings=_settings(use_real_apis=False),
        sequence_context_service=sequence_service,
        primer_provider=FakePrimerProvider(),
        crispr_provider=crispr_provider,
    )

    response = service.design_guides(CrisprRequest(gene="RPE65", cdna="c.260A>G"))

    assert response.cas == "SpCas9"
    assert response.guides == []
    assert response.ssodn is None
    assert response.source_disclosure is not None
    assert response.source_disclosure.source_status == "local_provider"
    assert response.source_disclosure.provider_id == "local_deterministic_spcas9"
    assert sequence_service.calls == [
        {"gene": "RPE65", "cdna": "c.260A>G", "prefer_resolver": True}
    ]
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

    assert response.reference == "ACGT"
    assert response.sanger_read == "ACGT"
    assert response.match_line == "||||"
    assert response.mismatch_positions == []
    assert response.target_position == 1
    assert response.trace_channels == []
    assert response.base_calls == list("ACGT")
    assert response.q_scores == []
    assert response.source_disclosure is not None
    assert response.source_disclosure.source_status == "local_provider"
    assert response.source_disclosure.provider_id == "local_sanger_aligner"
    assert sequence_service.calls == [{"gene": "RPE65", "cdna": "c.260A>G"}]
    assert align_provider.calls == [(payload, _context())]


def test_real_mode_workbench_disclosure_is_not_rpe65_fixture_bound() -> None:
    query = normalize_sequence_query("BRCA1", "c.100A>G")
    sequence_service = StaticSequenceContextService(
        SequenceContextResult(query=query, context=_synthetic_context())
    )
    service = WorkbenchDesignService(
        settings=_settings(use_real_apis=True),
        sequence_context_service=sequence_service,
        primer_provider=FakePrimerProvider(),
        crispr_provider=FakeCrisprProvider(),
    )

    primer = service.design_primers(PrimerRequest(gene="BRCA1", cdna="c.100A>G"))
    crispr = service.design_guides(CrisprRequest(gene="BRCA1", cdna="c.100A>G"))

    assert primer.source_disclosure is not None
    assert primer.source_disclosure.source_status == "local_provider"
    assert crispr.source_disclosure is not None
    assert crispr.source_disclosure.source_status == "local_provider"
    assert sequence_service.calls == [
        {"gene": "BRCA1", "cdna": "c.100A>G", "prefer_resolver": True},
        {"gene": "BRCA1", "cdna": "c.100A>G", "prefer_resolver": True},
    ]


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
    assert body["source_disclosure"]["source_status"] == "local_provider"
    assert body["source_disclosure"]["provider_id"] == "local_sanger_aligner"


def test_workbench_live_align_is_not_bound_to_global_real_apis_or_rpe65() -> None:
    query = normalize_sequence_query("BRCA1", "c.100A>G")
    context = _synthetic_context()
    context.window_sequence = "GGGTTTAAACCCGGGTTT"
    context.target_offset = 8
    sequence_service = StaticSequenceContextService(
        SequenceContextResult(query=query, context=context)
    )
    align_provider = FakeAlignProvider()
    payload = AlignRequest(
        gene="BRCA1",
        cdna="c.100A>G",
        user_sequence="TTTAAACCC",
    )
    service = WorkbenchDesignService(
        settings=_settings(use_real_apis=False, workbench_live_design_enabled=True),
        sequence_context_service=sequence_service,
        primer_provider=FakePrimerProvider(),
        align_provider=align_provider,
    )

    response = service.align(payload)

    assert response.source_disclosure is not None
    assert response.source_disclosure.source_status == "local_provider"
    assert response.source_disclosure.provider_id == "local_sanger_aligner"
    assert sequence_service.calls == [{"gene": "BRCA1", "cdna": "c.100A>G"}]
    assert align_provider.calls == [(payload, context)]


def test_align_reference_route_resolves_sequence_context_without_read_input(client) -> None:
    query = normalize_sequence_query("RPE65", "c.260A>G", "NM_000329.3")
    context = _context()
    context.window_sequence = "TTTAAACCCGGGTTT"
    context.target_offset = 9
    sequence_context_service = StaticSequenceContextService(
        SequenceContextResult(query=query, context=context)
    )
    client.app.state.workbench_design_service = WorkbenchDesignService(
        settings=_settings(use_real_apis=False),
        sequence_context_service=sequence_context_service,
        primer_provider=FakePrimerProvider(),
    )

    response = client.post(
        "/api/v1/align/reference",
        json={
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "transcript": "NM_000329.3",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert (
        body
        == AlignReferenceResponse(
            gene="RPE65",
            cdna="c.260A>G",
            transcript="NM_000329.3",
            transcript_hgvs="NM_000329.3:c.260A>G",
            genome_build="GRCh38",
            genomic_hg38="1-68444869-T-C",
            strand="unknown",
            reference="TTTAAACCCGGGTTT",
            target_position=9,
            reference_base="T",
            alternate_base="C",
            source="resolver",
            warnings=[],
            source_disclosure={
                "source_status": "source_backed",
                "provider_id": "sequence_context_alignment_reference",
                "provider_label": "Sequence-context alignment reference",
                "source_version": None,
                "cache_status": "resolved",
                "warnings": [],
                "requirements": [],
            },
        ).model_dump()
    )
    assert sequence_context_service.calls == [
        {
            "gene": "RPE65",
            "cdna": "c.260A>G",
            "transcript": "NM_000329.3",
            "species": "human",
            "prefer_resolver": True,
        }
    ]


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
    assert [(channel.base, channel.raw_values) for channel in trace.trace_channels] == [
        ("A", (0.0, 5.0)),
        ("T", (4.0, 8.0)),
        ("C", (2.0, 2.0)),
        ("G", (0.0, 10.0)),
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
                "PRIMER_LEFT_0": [300, 18],
                "PRIMER_RIGHT_0": [720, 18],
                "PRIMER_LEFT_0_TM": 59.94,
                "PRIMER_RIGHT_0_TM": 60.05,
                "PRIMER_LEFT_0_GC_PERCENT": 44.4,
                "PRIMER_RIGHT_0_GC_PERCENT": 55.5,
                "PRIMER_LEFT_0_SELF_ANY_TH": 22.5,
                "PRIMER_LEFT_0_SELF_END_TH": 10.0,
                "PRIMER_LEFT_0_HAIRPIN_TH": 18.0,
                "PRIMER_RIGHT_0_SELF_ANY_TH": 31.2,
                "PRIMER_RIGHT_0_SELF_END_TH": 12.0,
                "PRIMER_RIGHT_0_HAIRPIN_TH": 17.0,
                "PRIMER_PAIR_0_COMPL_ANY_TH": 30.0,
                "PRIMER_PAIR_0_COMPL_END_TH": 38.2,
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
    assert pair.secondary_structure_risk == "moderate"
    assert pair.secondary_structure_notes == (
        "Primer3 thermodynamic secondary-structure screen moderate; "
        "max pair complement-end 38.2."
    )
    assert pair.self_any_forward == 22.5
    assert pair.self_any_reverse == 31.2
    assert pair.self_end_forward == 10.0
    assert pair.self_end_reverse == 12.0
    assert pair.hairpin_tm_forward == 18.0
    assert pair.hairpin_tm_reverse == 17.0
    assert pair.pair_compl_end == 38.2
    assert pair.forward_strand == "Plus"
    assert pair.reverse_strand == "Minus"
    assert pair.forward_template_start == 301
    assert pair.forward_template_stop == 318
    assert pair.reverse_template_start == 721
    assert pair.reverse_template_stop == 704
    assert pair.genomic_chromosome == "chr1"
    assert pair.genome_build == "GRCh38"
    assert pair.forward_genomic_start == 68444669
    assert pair.forward_genomic_stop == 68444686
    assert pair.reverse_genomic_start == 68445089
    assert pair.reverse_genomic_stop == 68445072
    assert pair.amplicon_template_start == 301
    assert pair.amplicon_template_end == 721
    assert pair.amplicon_genomic_start == 68444669
    assert pair.amplicon_genomic_end == 68445089
    assert pair.recommended is True
    assert "Primer3 local design" in pair.notes
    assert "Specificity provider note." in pair.notes
    assert specificity_provider.calls[0]["forward"] == "AACCGGTTAACCGGTTAA"
    assert specificity_provider.calls[0]["reverse"] == "TTGGAACCTTGGAACCTT"
    assert specificity_provider.calls[0]["product_min"] == 300
    assert specificity_provider.calls[0]["product_max"] == 700
    assert Primer3Module.bindings.seq_args["SEQUENCE_TARGET"] == [500, 1]
    assert Primer3Module.bindings.global_args["PRIMER_THERMODYNAMIC_OLIGO_ALIGNMENT"] == 1
    assert Primer3Module.bindings.global_args["PRIMER_PRODUCT_SIZE_RANGE"] == [[300, 700]]


def test_primer3_provider_warns_when_snp_masking_requested_without_provider() -> None:
    class Bindings:
        def __init__(self) -> None:
            self.seq_args = {}

        def design_primers(self, *, seq_args, global_args):
            self.seq_args = seq_args
            return {
                "PRIMER_PAIR_NUM_RETURNED": 1,
                "PRIMER_LEFT_0_SEQUENCE": "AACCGGTTAACCGGTTAA",
                "PRIMER_RIGHT_0_SEQUENCE": "TTGGAACCTTGGAACCTT",
                "PRIMER_LEFT_0_TM": 60.0,
                "PRIMER_RIGHT_0_TM": 60.0,
                "PRIMER_LEFT_0_GC_PERCENT": 44.4,
                "PRIMER_RIGHT_0_GC_PERCENT": 55.5,
                "PRIMER_PAIR_0_PRODUCT_SIZE": 421,
            }

    class Primer3Module:
        bindings = Bindings()

    provider = Primer3PrimerProvider(
        primer3_module=Primer3Module(),
        specificity_provider=QueuedSpecificityProvider([_specificity_result()]),
    )

    response = provider.design(
        payload=PrimerRequest(gene="RPE65", cdna="c.260A>G", avoid_snps=True),
        context=_context(),
    )

    assert response.pairs
    assert "primer_snp_masking_not_configured" in response.pairs[0].notes
    assert "not yet applied" not in response.pairs[0].notes
    assert "SEQUENCE_EXCLUDED_REGION" not in Primer3Module.bindings.seq_args


def test_primer3_provider_dbsnp_masking_excludes_regions_and_rejects_3prime_hits() -> None:
    class Bindings:
        def __init__(self) -> None:
            self.seq_args = {}

        def design_primers(self, *, seq_args, global_args):
            self.seq_args = seq_args
            return {
                "PRIMER_PAIR_NUM_RETURNED": 2,
                "PRIMER_LEFT_0_SEQUENCE": "AACCGGTTAACCGGTTAAA",
                "PRIMER_RIGHT_0_SEQUENCE": "TTGGAACCTTGGAACCTT",
                "PRIMER_LEFT_0": [471, 19],
                "PRIMER_RIGHT_0": [720, 18],
                "PRIMER_LEFT_0_TM": 60.0,
                "PRIMER_RIGHT_0_TM": 60.0,
                "PRIMER_LEFT_0_GC_PERCENT": 44.4,
                "PRIMER_RIGHT_0_GC_PERCENT": 55.5,
                "PRIMER_PAIR_0_PRODUCT_SIZE": 250,
                "PRIMER_LEFT_1_SEQUENCE": "TTTTGGCCAATTGGCCAATT",
                "PRIMER_RIGHT_1_SEQUENCE": "AAGGTTAAGGTTAAGGTTAA",
                "PRIMER_LEFT_1": [300, 20],
                "PRIMER_RIGHT_1": [720, 20],
                "PRIMER_LEFT_1_TM": 61.0,
                "PRIMER_RIGHT_1_TM": 61.0,
                "PRIMER_LEFT_1_GC_PERCENT": 45.0,
                "PRIMER_RIGHT_1_GC_PERCENT": 45.0,
                "PRIMER_PAIR_1_PRODUCT_SIZE": 421,
            }

    class Primer3Module:
        bindings = Bindings()

    specificity_provider = QueuedSpecificityProvider([_specificity_result()])
    provider = Primer3PrimerProvider(
        primer3_module=Primer3Module(),
        specificity_provider=specificity_provider,
        snp_masking_provider=LocalDbSnpPrimerSnpMaskingProvider(DbSnpLocalStore()),
    )

    response = provider.design(
        payload=PrimerRequest(gene="RPE65", cdna="c.260A>G", avoid_snps=True),
        context=_context(),
    )

    assert Primer3Module.bindings.seq_args["SEQUENCE_EXCLUDED_REGION"] == [[489, 1], [500, 1]]
    assert len(response.pairs) == 1
    pair = response.pairs[0]
    assert pair.index == 2
    assert pair.recommended is True
    assert "dbSNP local SNP masking active" in pair.notes
    assert "snp_count=2" in pair.notes
    assert "excluded_regions=2" in pair.notes
    assert "rejected_3prime_pairs=1" in pair.notes
    assert str(FIXTURES_DIR).lower() not in pair.notes.lower()
    assert len(specificity_provider.calls) == 1


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
