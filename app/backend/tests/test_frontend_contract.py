"""Field-name parity test between Pydantic models and frontend TS interfaces.

Every Pydantic field on the in-scope models must appear as a key on its
matching ``export interface`` in both frontend ``backend.ts`` mirrors.

The check is asymmetric:
- TS may carry extra fields the backend does not declare (view-only state).
- Pydantic fields missing from TS fail the test — that's the contract drift
  the rebuilt frontend cannot tolerate (ReportPage / AIStack read these names).

When this test fails: rename the missing fields in ``backend.ts`` to match the
Pydantic models, then commit both sides together.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.schemas.chat import RunChatRequest, RunChatResponse
from app.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    WorkbenchContext,
    WorkbenchEdit,
)
from app.schemas.lookup import (
    LookupRequest,
    LookupResponse,
    SearchInputAiExtraction,
    SearchInputCandidate,
    SearchInputCoordinateResolutionAudit,
    SearchInputInterpretation,
    SearchInputParseRequest,
    SearchInputParseResponse,
    SearchInputSourceInputs,
)
from app.schemas.protein_annotation import (
    ProteinAnnotationRequest,
    ProteinDomainTrack,
    ProteinDomainTrackFeature,
    ProteinTrackProvenance,
    ProteinTrackVariantMarker,
)
from app.schemas.gene_viewer import (
    AppliedVariant,
    ClinvarVariant,
    ExonVariantDensity,
    GeneViewerRequest,
    GeneViewerResponse,
    ProteinActiveSite,
    ProteinProductEffect,
    ProteinProductExonEffect,
    ProteinDomain,
    ProteinFeatures,
    ProteinPointFeature,
    ProteinRangeFeature,
    QueriedVariant,
    RestrictionSite,
    ViewerCodonStart,
    ViewerCoordinateMapRange,
    ViewerFeatureInterval,
    ViewerFullLocus,
    ViewerGenomicLocus,
    ViewerFeature,
    ViewerIdentity,
    ViewerLocus,
    ViewerProvenance,
    ViewerProvenanceSource,
    ViewerRenderingHints,
    ViewerSegment,
    ViewerSequences,
    ViewerSummary,
    ViewerTranscriptProjection,
    ViewerTranscriptProjectionInterval,
    ViewerTracks,
    ViewerWindow,
    ViewerWindowRequest,
)
from app.schemas.run import (
    AcmgCriteriaScaffold,
    AcmgCriterion,
    AssociatedCondition,
    CodonCell,
    CuratedVariantsDistribution,
    EvidenceSourceSummary,
    ExpertPanelCriterion,
    ExpertPanelProvenance,
    ExpertPanelSection,
    ExpertPanelVcep,
    FunctionalEvidenceSourceBreakdown,
    FunctionalEvidenceDisplayMetrics,
    FunctionalEvidenceSummary,
    FunctionalStudy,
    GeneContextRenderHints,
    GeneContextSnapshot,
    GeneContextTranscriptExon,
    GeneContextTranscriptIntron,
    GeneContextVariantProjection,
    GeneContextWorkbenchLink,
    InSilicoPredictions,
    LocusContext,
    NearbyVariant,
    PopulationAgeDistribution,
    PopulationAgeBin,
    PopulationAgeHistogram,
    PopulationAgeHistogramView,
    PopulationSequencingAgeDistribution,
    PopulationFrequencyAncestryGroup,
    PopulationFrequencyDatasetCell,
    PopulationFrequencyDetail,
    PopulationFrequencyOverall,
    PopulationFrequencyOverallTotalCell,
    PopulationFrequencyReportSection,
    PopulationFrequencySexCell,
    PopulationFrequencySourceRow,
    PopulationFrequencyVisualGroup,
    PopulationFrequencyVisualScale,
    PredictorCard,
    PublicationLiterature,
    PublicationScopeCount,
    PublicationScopeCounts,
    PublicationSnippet,
    PublicationSourceBreakdown,
    PublicationTimeline,
    PublicationYearCount,
    PublicationsCallout,
    PubMedArticle,
    AcmgWorksheetCriterion,
    AcmgWorksheetLedger,
    ComputationalDeepDiveSection,
    ComputationalPredictorRow,
    DiseaseMechanismSection,
    InterpretationSummary,
    MolecularContextSection,
    ReportCallBadge,
    ReportCallCard,
    ReportCallInteraction,
    ReportExtractionPlan,
    ReportExtractionSectionTarget,
    ReportPayload,
    SourceProvenance,
    TherapiesTrialsSection,
    TrialMatch,
    VariantReportHeader,
    VariantReportCallCards,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.schemas.workbench import (
    AlignRequest,
    AlignResponse,
    AlignTraceHetCall,
    AlignTraceRequest,
    AlignTraceResponse,
    AlignTraceTrimRange,
    CrisprGuide,
    CrisprOffTargetLocus,
    CrisprOffTargetRequest,
    CrisprOffTargetResponse,
    CrisprOffTargetSite,
    CrisprRequest,
    CrisprResponse,
    CrisprScreeningPrimerRequest,
    CrisprScreeningPrimerResponse,
    CrisprScreeningPrimerTarget,
    CrisprScreeningRegion,
    CrisprSsodnDesign,
    CrisprSsodnRequest,
    CrisprSsodnResponse,
    CrisprTideResponse,
    CrisprTideSpectrumBin,
    HdrSsodn,
    PrimerPair,
    PrimerRequest,
    PrimerResponse,
    ScreeningPrimer,
    TraceChannel,
)
from app.schemas.panels import (
    Panel,
    PanelGene,
    PanelListResponse,
    PanelResolveRequest,
    PanelSummary,
)
from app.schemas.batch import (
    BatchCreateRequest,
    BatchCreateResponse,
    BatchFilters,
    BatchJob,
    BatchJobQuery,
    BatchPage,
    BatchResult,
    BatchUploadResponse,
    ParsedVariant,
)

MODEL_TO_TS_INTERFACE: dict[type[BaseModel], str] = {
    LookupResponse: "LookupResponse",
    LookupRequest: "LookupRequest",
    SearchInputAiExtraction: "SearchInputAiExtraction",
    SearchInputCandidate: "SearchInputCandidate",
    SearchInputCoordinateResolutionAudit: "SearchInputCoordinateResolutionAudit",
    SearchInputInterpretation: "SearchInputInterpretation",
    SearchInputParseRequest: "SearchInputParseRequest",
    SearchInputParseResponse: "SearchInputParseResponse",
    SearchInputSourceInputs: "SearchInputSourceInputs",
    ProteinAnnotationRequest: "ProteinAnnotationRequest",
    ProteinTrackProvenance: "ProteinTrackProvenance",
    ProteinDomainTrackFeature: "ProteinDomainTrackFeature",
    ProteinTrackVariantMarker: "ProteinTrackVariantMarker",
    ProteinDomainTrack: "ProteinDomainTrack",
    RunChatRequest: "RunChatRequest",
    RunChatResponse: "RunChatResponse",
    ReportPayload: "ReportPayload",
    EvidenceSourceSummary: "EvidenceSourceSummary",
    ExpertPanelVcep: "ExpertPanelVcep",
    ExpertPanelCriterion: "ExpertPanelCriterion",
    ExpertPanelProvenance: "ExpertPanelProvenance",
    ExpertPanelSection: "ExpertPanelSection",
    VariantSummaryRow: "VariantSummaryRow",
    PubMedArticle: "PubMedArticle",
    LocusContext: "LocusContext",
    NearbyVariant: "NearbyVariant",
    CodonCell: "CodonCell",
    InSilicoPredictions: "InSilicoPredictions",
    PredictorCard: "PredictorCard",
    AcmgCriterion: "AcmgCriterion",
    AcmgCriteriaScaffold: "AcmgCriteriaScaffold",
    CuratedVariantsDistribution: "CuratedVariantsDistribution",
    AssociatedCondition: "AssociatedCondition",
    PublicationsCallout: "PublicationsCallout",
    PublicationSnippet: "PublicationSnippet",
    PublicationSourceBreakdown: "PublicationSourceBreakdown",
    PublicationYearCount: "PublicationYearCount",
    PublicationTimeline: "PublicationTimeline",
    PublicationScopeCount: "PublicationScopeCount",
    PublicationScopeCounts: "PublicationScopeCounts",
    PublicationLiterature: "PublicationLiterature",
    FunctionalEvidenceSourceBreakdown: "FunctionalEvidenceSourceBreakdown",
    FunctionalEvidenceDisplayMetrics: "FunctionalEvidenceDisplayMetrics",
    FunctionalStudy: "FunctionalStudy",
    FunctionalEvidenceSummary: "FunctionalEvidenceSummary",
    ReportCallBadge: "ReportCallBadge",
    ReportCallInteraction: "ReportCallInteraction",
    ReportCallCard: "ReportCallCard",
    VariantReportCallCards: "VariantReportCallCards",
    PopulationFrequencyAncestryGroup: "PopulationFrequencyAncestryGroup",
    PopulationAgeHistogram: "PopulationAgeHistogram",
    PopulationAgeDistribution: "PopulationAgeDistribution",
    PopulationSequencingAgeDistribution: "PopulationSequencingAgeDistribution",
    PopulationFrequencyDetail: "PopulationFrequencyDetail",
    PopulationFrequencyDatasetCell: "PopulationFrequencyDatasetCell",
    PopulationFrequencySexCell: "PopulationFrequencySexCell",
    PopulationFrequencyOverallTotalCell: "PopulationFrequencyOverallTotalCell",
    PopulationFrequencyOverall: "PopulationFrequencyOverall",
    SourceProvenance: "SourceProvenance",
    ReportExtractionSectionTarget: "ReportExtractionSectionTarget",
    ReportExtractionPlan: "ReportExtractionPlan",
    VariantReportHeader: "VariantReportHeader",
    InterpretationSummary: "InterpretationSummary",
    DiseaseMechanismSection: "DiseaseMechanismSection",
    MolecularContextSection: "MolecularContextSection",
    ComputationalPredictorRow: "ComputationalPredictorRow",
    ComputationalDeepDiveSection: "ComputationalDeepDiveSection",
    AcmgWorksheetCriterion: "AcmgWorksheetCriterion",
    AcmgWorksheetLedger: "AcmgWorksheetLedger",
    TrialMatch: "TrialMatch",
    TherapiesTrialsSection: "TherapiesTrialsSection",
    PopulationFrequencyVisualScale: "PopulationFrequencyVisualScale",
    PopulationFrequencyVisualGroup: "PopulationFrequencyVisualGroup",
    PopulationAgeBin: "PopulationAgeBin",
    PopulationAgeHistogramView: "PopulationAgeHistogramView",
    PopulationFrequencySourceRow: "PopulationFrequencySourceRow",
    PopulationFrequencyReportSection: "PopulationFrequencyReportSection",
    VariantReportProfile: "VariantReportProfile",
    ChatRequest: "ChatRequest",
    ChatResponse: "ChatResponse",
    ChatMessage: "ChatMessage",
    WorkbenchContext: "WorkbenchContext",
    WorkbenchEdit: "WorkbenchEdit",
    PrimerRequest: "PrimerRequest",
    PrimerResponse: "PrimerResponse",
    PrimerPair: "PrimerPair",
    CrisprRequest: "CrisprRequest",
    CrisprResponse: "CrisprResponse",
    CrisprGuide: "CrisprGuide",
    HdrSsodn: "HdrSsodn",
    CrisprSsodnRequest: "CrisprSsodnRequest",
    CrisprSsodnDesign: "CrisprSsodnDesign",
    CrisprSsodnResponse: "CrisprSsodnResponse",
    CrisprOffTargetLocus: "CrisprOffTargetLocus",
    CrisprOffTargetRequest: "CrisprOffTargetRequest",
    CrisprOffTargetSite: "CrisprOffTargetSite",
    CrisprOffTargetResponse: "CrisprOffTargetResponse",
    CrisprScreeningRegion: "CrisprScreeningRegion",
    CrisprScreeningPrimerTarget: "CrisprScreeningPrimerTarget",
    CrisprScreeningPrimerRequest: "CrisprScreeningPrimerRequest",
    ScreeningPrimer: "ScreeningPrimer",
    CrisprScreeningPrimerResponse: "CrisprScreeningPrimerResponse",
    CrisprTideSpectrumBin: "CrisprTideSpectrumBin",
    CrisprTideResponse: "CrisprTideResponse",
    AlignRequest: "AlignRequest",
    AlignResponse: "AlignResponse",
    AlignTraceRequest: "AlignTraceRequest",
    AlignTraceResponse: "AlignTraceResponse",
    AlignTraceTrimRange: "AlignTraceTrimRange",
    AlignTraceHetCall: "AlignTraceHetCall",
    TraceChannel: "TraceChannel",
    ViewerWindowRequest: "ViewerWindowRequest",
    GeneViewerRequest: "GeneViewerRequest",
    ViewerIdentity: "ViewerIdentity",
    ViewerLocus: "ViewerLocus",
    ViewerSummary: "ViewerSummary",
    ViewerWindow: "ViewerWindow",
    ViewerSegment: "ViewerSegment",
    QueriedVariant: "QueriedVariant",
    AppliedVariant: "AppliedVariant",
    ViewerSequences: "ViewerSequences",
    ClinvarVariant: "ClinvarVariant",
    ExonVariantDensity: "ExonVariantDensity",
    ProteinDomain: "ProteinDomain",
    ProteinActiveSite: "ProteinActiveSite",
    ProteinProductEffect: "ProteinProductEffect",
    ProteinProductExonEffect: "ProteinProductExonEffect",
    ProteinRangeFeature: "ProteinRangeFeature",
    ProteinPointFeature: "ProteinPointFeature",
    ProteinFeatures: "ProteinFeatures",
    RestrictionSite: "RestrictionSite",
    ViewerFeature: "ViewerFeature",
    ViewerTracks: "ViewerTracks",
    ViewerProvenanceSource: "ViewerProvenanceSource",
    ViewerProvenance: "ViewerProvenance",
    ViewerGenomicLocus: "ViewerGenomicLocus",
    ViewerCoordinateMapRange: "ViewerCoordinateMapRange",
    ViewerCodonStart: "ViewerCodonStart",
    ViewerTranscriptProjectionInterval: "ViewerTranscriptProjectionInterval",
    ViewerTranscriptProjection: "ViewerTranscriptProjection",
    ViewerFeatureInterval: "ViewerFeatureInterval",
    ViewerRenderingHints: "ViewerRenderingHints",
    ViewerFullLocus: "ViewerFullLocus",
    GeneViewerResponse: "GeneViewerResponse",
    GeneContextTranscriptExon: "GeneContextTranscriptExon",
    GeneContextTranscriptIntron: "GeneContextTranscriptIntron",
    GeneContextVariantProjection: "GeneContextVariantProjection",
    GeneContextRenderHints: "GeneContextRenderHints",
    GeneContextWorkbenchLink: "GeneContextWorkbenchLink",
    GeneContextSnapshot: "GeneContextSnapshot",
    PanelGene: "PanelGene",
    PanelSummary: "PanelSummary",
    Panel: "Panel",
    PanelListResponse: "PanelListResponse",
    PanelResolveRequest: "PanelResolveRequest",
    ParsedVariant: "ParsedVariant",
    BatchFilters: "BatchFilters",
    BatchUploadResponse: "BatchUploadResponse",
    BatchCreateRequest: "BatchCreateRequest",
    BatchCreateResponse: "BatchCreateResponse",
    BatchPage: "BatchPage",
    BatchJobQuery: "BatchJobQuery",
    BatchResult: "BatchResult",
    BatchJob: "BatchJob",
}


BE6_REPORT_V2_FIELDS: dict[type[BaseModel], set[str]] = {
    CodonCell: {"aa_alt", "dna_ref", "dna_alt"},
    NearbyVariant: {"protein_change"},
    LocusContext: {"coords"},
    PredictorCard: {"verdict_label"},
    AcmgCriteriaScaffold: {"intro", "note"},
    CuratedVariantsDistribution: {"row_totals", "subtitle"},
    AssociatedCondition: {"db_tag", "db_tag_bold", "source_list"},
    PublicationsCallout: {"blurb"},
}


def _frontend_backend_ts_paths() -> list[Path]:
    # tests/ -> backend/ -> app/ -> {frontend,web}/...
    app_root = Path(__file__).resolve().parents[2]
    return [
        app_root / "frontend" / "src" / "lib" / "backend.ts",
        app_root / "web" / "lib" / "backend.ts",
    ]


def _path_id(path: Path) -> str:
    return path.relative_to(Path(__file__).resolve().parents[3]).as_posix()


def _extract_ts_interface_body(source: str, name: str) -> str:
    """Return the body slice between { and the matching } for the named interface."""
    match = re.search(rf"export\s+interface\s+{re.escape(name)}\s*\{{", source)
    if not match:
        raise AssertionError(f"export interface {name} not found in backend.ts")
    start = match.end()
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise AssertionError(f"unterminated interface {name} in backend.ts")
    return source[start : i - 1]


@pytest.mark.parametrize(
    "model,ts_name",
    list(MODEL_TO_TS_INTERFACE.items()),
    ids=lambda v: v if isinstance(v, str) else v.__name__,
)
@pytest.mark.parametrize(
    "backend_ts_path",
    _frontend_backend_ts_paths(),
    ids=_path_id,
)
def test_pydantic_field_names_present_in_typescript(model, ts_name, backend_ts_path):
    backend_ts = backend_ts_path.read_text(encoding="utf-8")
    body = _extract_ts_interface_body(backend_ts, ts_name)

    pydantic_fields = set(model.model_fields.keys())
    missing = {
        field
        for field in pydantic_fields
        if not re.search(rf"^\s*{re.escape(field)}\??\s*:", body, re.MULTILINE)
    }
    assert not missing, (
        f"{ts_name} in {_path_id(backend_ts_path)} is missing fields present "
        f"on {model.__name__} (Pydantic): {sorted(missing)}"
    )


def test_frontend_backend_ts_mirrors_are_byte_identical():
    frontend_backend_ts, next_backend_ts = _frontend_backend_ts_paths()
    assert frontend_backend_ts.read_bytes() == next_backend_ts.read_bytes()


@pytest.mark.parametrize(
    "backend_ts_path",
    _frontend_backend_ts_paths(),
    ids=_path_id,
)
def test_computational_predictor_calibration_contract_uses_ramp_verdict(backend_ts_path):
    backend_ts = backend_ts_path.read_text(encoding="utf-8")

    assert "export type RampVerdict =" in backend_ts
    for verdict in (
        "'Pathogenic'",
        "'Likely pathogenic'",
        "'VUS'",
        "'Likely benign'",
        "'Benign'",
    ):
        assert verdict in backend_ts

    body = _extract_ts_interface_body(backend_ts, "ComputationalPredictorRow")
    assert re.search(r"^\s*calibration_bucket\??\s*:\s*RampVerdict \| null", body, re.MULTILINE)
    assert re.search(r"^\s*calibrated_label\??\s*:\s*string \| null", body, re.MULTILINE)
    assert re.search(r"^\s*calibration_method\??\s*:\s*string \| null", body, re.MULTILINE)
    assert re.search(r"^\s*calibration_version\??\s*:\s*string \| null", body, re.MULTILINE)


@pytest.mark.parametrize(
    "backend_ts_path",
    _frontend_backend_ts_paths(),
    ids=_path_id,
)
def test_gene_viewer_contract_declares_full_locus_mode(backend_ts_path):
    backend_ts = backend_ts_path.read_text(encoding="utf-8")

    assert "'full_gene'" in backend_ts
    assert "export type ViewerDisplayBasis =" in backend_ts
    response_body = _extract_ts_interface_body(backend_ts, "GeneViewerResponse")
    assert re.search(
        r"^\s*full_locus\??\s*:\s*ViewerFullLocus \| null",
        response_body,
        re.MULTILINE,
    )
    window_body = _extract_ts_interface_body(backend_ts, "ViewerWindow")
    assert re.search(
        r"^\s*basis\??\s*:\s*ViewerDisplayBasis",
        window_body,
        re.MULTILINE,
    )


@pytest.mark.parametrize(
    "model,fields",
    list(BE6_REPORT_V2_FIELDS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_be6_report_v2_fields_are_declared_on_pydantic_models(model, fields):
    assert fields <= set(model.model_fields.keys())
