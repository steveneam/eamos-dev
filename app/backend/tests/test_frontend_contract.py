"""Field-name parity test between Pydantic models and frontend TS interfaces.

Every Pydantic field on the in-scope models must appear as a key on its
matching ``export interface`` in the active frontend ``backend.ts`` contract.

The check is asymmetric:
- TS may carry extra fields the backend does not declare (view-only state).
- Pydantic fields missing from TS fail the test — that's the contract drift
  the rebuilt frontend cannot tolerate (ReportPage / AIStack read these names).

When this test fails: rename the missing fields in ``backend.ts`` to match the
Pydantic models, then commit the schema and active TypeScript contract together.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import get_args

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
from app.schemas.capabilities import (
    CapabilityApplicabilityV2,
    CapabilityExecutionDisclosureV2,
    CapabilityExecutionV2,
    CapabilityRetentionV2,
    CapabilitySourceStatusV2,
    CapabilityValidationStatusV2,
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
    ComputationalAlternate,
    ComputationalDeepDiveSection,
    ComputationalEvidenceDecision,
    ComputationalPredictorRow,
    DiseaseMechanismSection,
    InterpretationSummary,
    LovdBasicObservation,
    LovdBasicRecordsSection,
    LovdInstallationSource,
    MolecularContextSection,
    OmimCrossReference,
    ReportCallBadge,
    ReportCallCard,
    ReportCallInteraction,
    ReportDataCurrency,
    ReportDataCurrencySource,
    ReportExtractionPlan,
    ReportExtractionSectionTarget,
    ReportPayload,
    SourceFactPolicyEnvelope,
    SourcePolicyDecision,
    SourceProvenance,
    TherapiesTrialsSection,
    ClinicalTrialQueryExecution,
    TrialMatch,
    VariantReportHeader,
    VariantReportCallCards,
    VariantReportProfile,
    VariantSummaryRow,
)
from app.schemas.search import (
    SearchAnswerRequest,
    SearchAnswerResponse,
    SearchCitation,
    SearchHit,
    SearchResponse,
)
from app.schemas.workbench import (
    AlignReferenceRequest,
    AlignReferenceResponse,
    AlignRequest,
    AlignResponse,
    AlignTraceHetCall,
    AlignTraceRequest,
    AlignTraceResponse,
    AlignTraceTrimRange,
    CrisprGuide,
    CrisprGuideIdentityV2,
    CrisprOffTargetLocus,
    CrisprOffTargetRequest,
    CrisprOffTargetResponse,
    CrisprOffTargetSite,
    CrisprRequest,
    CrisprResponse,
    CrisprScoreDirectionV2,
    CrisprScoreFamilyV2,
    CrisprScoreV2,
    CrisprScreeningPrimerRequest,
    CrisprScreeningPrimerResponse,
    CrisprScreeningPrimerTarget,
    CrisprScreeningRegion,
    CrisprSsodnDesign,
    CrisprSsodnRequest,
    CrisprSsodnResponse,
    CrisprTideResponse,
    CrisprTideSpectrumBin,
    CrisprTraceDifferenceBin,
    CrisprVerifiedLocusV2,
    HdrSsodn,
    PrimerPair,
    PrimerRequest,
    PrimerResponse,
    ScreeningPrimer,
    SourceDisclosure,
    TraceChannel,
)
from app.schemas.workflow import (
    CanonicalVariantRefV1,
    CompareViewV1,
    ConsequenceBucketV1,
    CuratedVariantPageV1,
    ProcessingDisclosureV1,
    ProcessingExecutionV1,
    ProcessingInputClassV1,
    ProcessingRetentionV1,
    RelatedVariantGroupV1,
    RelatedVariantItemV1,
    RelatedVariantRelationshipV1,
    SelectionOrientationV1,
    SelectionOverlapV1,
    SelectionRangeV1,
    SelectionStrandV1,
    SequenceBasisV1,
    VariantResolutionStatusV1,
    WorkbenchDesignContextV1,
    WorkbenchContextOriginV2,
    WorkbenchDesignContextV2,
    WorkbenchEditOperationV2,
    WorkbenchReferenceBasisV2,
    WorkbenchResultBindingV2,
    WorkbenchResultStateV2,
    WorkbenchSparseEditV2,
    WorkbenchViewV1,
    WorkflowActiveToolV1,
    WorkflowArtifactDownloadStateV1,
    WorkflowArtifactKindV1,
    WorkflowArtifactV1,
    WorkflowAsyncStateV1,
    WorkflowContextV1,
    WorkflowOriginSurfaceV1,
    WorkflowOwnerScopeV1,
    WorkflowRunKindV1,
    WorkflowRunStatusV1,
    WorkflowRunV1,
)
from app.schemas.panels import (
    Panel,
    PanelGene,
    PanelIntervalProvenanceV2,
    PanelIntervalScopeV2,
    PanelLaunchPostureV2,
    PanelListResponse,
    PanelResolveRequest,
    PanelSourceSnapshotV2,
    PanelSummary,
)
from app.schemas.batch import (
    BatchAlleleIdentityV2,
    BatchAlleleV2,
    BatchAnalysisScopeV2,
    BatchCohortModelV2,
    BatchCreateRequest,
    BatchCreateResponse,
    BatchExportFormatV2,
    BatchExportStateV2,
    BatchExportV2,
    BatchFieldExecutionV2,
    BatchFieldNameV2,
    BatchFieldValueStatusV2,
    BatchFilterDispositionV2,
    BatchFilterOutcomeV2,
    BatchFilterPlanV2,
    BatchFilterReasonV2,
    BatchFilterStageV2,
    BatchFilters,
    BatchInputEnvelopeV2,
    BatchInputFormatV2,
    BatchIntervalScopeV2,
    BatchJob,
    BatchJobQuery,
    BatchPage,
    BatchPagingV2,
    BatchResult,
    BatchSampleProvenanceV2,
    BatchSourceSnapshotV2,
    BatchUploadResponse,
    BatchNormalizationStatusV2,
    ParsedVariant,
)
from app.schemas.paper_variants import (
    PaperAdjudicationRecommendationV2,
    PaperAiAdjudicationV2,
    PaperBibliographicMetadataV2,
    PaperDocumentBundleRequestV2,
    PaperDocumentBundleV2,
    PaperDocumentExtractionV2,
    PaperDocumentKindV2,
    PaperDocumentMetadataV2,
    PaperDocumentRoleV2,
    PaperDocumentUploadV2,
    PaperEvidenceSpanV2,
    PaperExtractionLayerV2,
    PaperExtractionQualityV2,
    PaperMentionResolutionV2,
    PaperPageExtractionQualityV2,
    PaperResolutionStatusV2,
    PaperVariantMentionV2,
    PaperVariantsExtractResponse,
    VariantContext,
    VariantLevel,
)
from app.schemas.report import (
    ReportCoverageV2,
    ReportExecutionStateV2,
    ReportMatchLevelV2,
    ReportPredictorExecutionV2,
    ReportPredictorStateV2,
    ReportSectionExecutionV2,
    ReportSectionIdV2,
    ReportSectionStateV2,
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
    ReportDataCurrencySource: "SourceFreshness",
    ReportDataCurrency: "ReportDataCurrency",
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
    SourcePolicyDecision: "SourcePolicyDecision",
    SourceFactPolicyEnvelope: "SourceFactPolicyEnvelope",
    OmimCrossReference: "OmimCrossReference",
    LovdInstallationSource: "LovdInstallationSource",
    LovdBasicObservation: "LovdBasicObservation",
    LovdBasicRecordsSection: "LovdBasicRecordsSection",
    ReportExtractionSectionTarget: "ReportExtractionSectionTarget",
    ReportExtractionPlan: "ReportExtractionPlan",
    VariantReportHeader: "VariantReportHeader",
    InterpretationSummary: "InterpretationSummary",
    DiseaseMechanismSection: "DiseaseMechanismSection",
    MolecularContextSection: "MolecularContextSection",
    ComputationalAlternate: "ComputationalAlternate",
    ComputationalEvidenceDecision: "ComputationalEvidenceDecision",
    ComputationalPredictorRow: "ComputationalPredictorRow",
    ComputationalDeepDiveSection: "ComputationalDeepDiveSection",
    AcmgWorksheetCriterion: "AcmgWorksheetCriterion",
    AcmgWorksheetLedger: "AcmgWorksheetLedger",
    TrialMatch: "TrialMatch",
    ClinicalTrialQueryExecution: "ClinicalTrialQueryExecution",
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
    CapabilityExecutionDisclosureV2: "CapabilityExecutionDisclosureV2",
    SourceDisclosure: "SourceDisclosure",
    PrimerRequest: "PrimerRequest",
    PrimerResponse: "PrimerResponse",
    PrimerPair: "PrimerPair",
    CrisprRequest: "CrisprRequest",
    CrisprResponse: "CrisprResponse",
    CrisprGuide: "CrisprGuide",
    CrisprVerifiedLocusV2: "CrisprVerifiedLocusV2",
    CrisprGuideIdentityV2: "CrisprGuideIdentityV2",
    CrisprScoreV2: "CrisprScoreV2",
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
    CrisprTraceDifferenceBin: "CrisprTraceDifferenceBin",
    CrisprTideResponse: "CrisprTideResponse",
    AlignRequest: "AlignRequest",
    AlignResponse: "AlignResponse",
    AlignReferenceRequest: "AlignReferenceRequest",
    AlignReferenceResponse: "AlignReferenceResponse",
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
    PanelIntervalProvenanceV2: "PanelIntervalProvenanceV2",
    PanelSourceSnapshotV2: "PanelSourceSnapshotV2",
    PanelSummary: "PanelSummary",
    Panel: "Panel",
    PanelListResponse: "PanelListResponse",
    PanelResolveRequest: "PanelResolveRequest",
    ParsedVariant: "ParsedVariant",
    BatchInputEnvelopeV2: "BatchInputEnvelopeV2",
    BatchAlleleV2: "BatchAlleleV2",
    BatchAlleleIdentityV2: "BatchAlleleIdentityV2",
    BatchSourceSnapshotV2: "BatchSourceSnapshotV2",
    BatchFilterPlanV2: "BatchFilterPlanV2",
    BatchFilterDispositionV2: "BatchFilterDispositionV2",
    BatchSampleProvenanceV2: "BatchSampleProvenanceV2",
    BatchFieldExecutionV2: "BatchFieldExecutionV2",
    BatchPagingV2: "BatchPagingV2",
    BatchExportV2: "BatchExportV2",
    BatchFilters: "BatchFilters",
    BatchUploadResponse: "BatchUploadResponse",
    BatchCreateRequest: "BatchCreateRequest",
    BatchCreateResponse: "BatchCreateResponse",
    BatchPage: "BatchPage",
    BatchJobQuery: "BatchJobQuery",
    BatchResult: "BatchResult",
    BatchJob: "BatchJob",
    SearchHit: "SearchHit",
    SearchResponse: "SearchResponse",
    SearchCitation: "SearchCitation",
    SearchAnswerRequest: "SearchAnswerRequest",
    SearchAnswerResponse: "SearchAnswerResponse",
    CanonicalVariantRefV1: "CanonicalVariantRefV1",
    SelectionRangeV1: "SelectionRangeV1",
    WorkbenchDesignContextV1: "WorkbenchDesignContextV1",
    WorkbenchReferenceBasisV2: "WorkbenchReferenceBasisV2",
    WorkbenchSparseEditV2: "WorkbenchSparseEditV2",
    WorkbenchDesignContextV2: "WorkbenchDesignContextV2",
    WorkbenchResultBindingV2: "WorkbenchResultBindingV2",
    WorkflowContextV1: "WorkflowContextV1",
    ProcessingDisclosureV1: "ProcessingDisclosureV1",
    WorkflowArtifactV1: "WorkflowArtifactV1",
    WorkflowRunV1: "WorkflowRunV1",
    RelatedVariantItemV1: "RelatedVariantItemV1",
    RelatedVariantGroupV1: "RelatedVariantGroupV1",
    CuratedVariantPageV1: "CuratedVariantPageV1",
    PaperDocumentUploadV2: "PaperDocumentUploadV2",
    PaperBibliographicMetadataV2: "PaperBibliographicMetadataV2",
    PaperDocumentMetadataV2: "PaperDocumentMetadataV2",
    PaperDocumentBundleV2: "PaperDocumentBundleV2",
    PaperDocumentBundleRequestV2: "PaperDocumentBundleRequestV2",
    PaperPageExtractionQualityV2: "PaperPageExtractionQualityV2",
    PaperEvidenceSpanV2: "PaperEvidenceSpanV2",
    PaperVariantMentionV2: "PaperVariantMentionV2",
    PaperMentionResolutionV2: "PaperMentionResolutionV2",
    PaperAiAdjudicationV2: "PaperAiAdjudicationV2",
    PaperDocumentExtractionV2: "PaperDocumentExtractionV2",
    PaperVariantsExtractResponse: "PaperVariantsResponse",
    ReportSectionExecutionV2: "ReportSectionExecutionV2",
    ReportPredictorExecutionV2: "ReportPredictorExecutionV2",
    ReportExecutionStateV2: "ReportExecutionStateV2",
}

WORKFLOW_LITERAL_TO_TS_TYPE = {
    VariantResolutionStatusV1: "VariantResolutionStatusV1",
    WorkflowOriginSurfaceV1: "WorkflowOriginSurfaceV1",
    WorkflowActiveToolV1: "WorkflowActiveToolV1",
    SelectionStrandV1: "SelectionStrandV1",
    SelectionOrientationV1: "SelectionOrientationV1",
    SequenceBasisV1: "SequenceBasisV1",
    SelectionOverlapV1: "SelectionOverlapV1",
    ProcessingExecutionV1: "ProcessingExecutionV1",
    ProcessingInputClassV1: "ProcessingInputClassV1",
    ProcessingRetentionV1: "ProcessingRetentionV1",
    WorkflowRunKindV1: "WorkflowRunKindV1",
    WorkflowRunStatusV1: "WorkflowRunStatusV1",
    WorkflowOwnerScopeV1: "WorkflowOwnerScopeV1",
    WorkflowArtifactKindV1: "WorkflowArtifactKindV1",
    WorkflowArtifactDownloadStateV1: "WorkflowArtifactDownloadStateV1",
    RelatedVariantRelationshipV1: "RelatedVariantRelationshipV1",
    ConsequenceBucketV1: "ConsequenceBucketV1",
    WorkbenchViewV1: "WorkbenchViewV1",
    CompareViewV1: "CompareViewV1",
    WorkflowAsyncStateV1: "WorkflowAsyncStateV1",
    CapabilityExecutionV2: "CapabilityExecutionV2",
    CapabilitySourceStatusV2: "CapabilitySourceStatusV2",
    CapabilityApplicabilityV2: "CapabilityApplicabilityV2",
    CapabilityValidationStatusV2: "CapabilityValidationStatusV2",
    CapabilityRetentionV2: "CapabilityRetentionV2",
    WorkbenchEditOperationV2: "WorkbenchEditOperationV2",
    WorkbenchContextOriginV2: "WorkbenchContextOriginV2",
    WorkbenchResultStateV2: "WorkbenchResultStateV2",
    CrisprScoreFamilyV2: "CrisprScoreFamilyV2",
    CrisprScoreDirectionV2: "CrisprScoreDirectionV2",
    VariantLevel: "VariantLevel",
    VariantContext: "VariantContext",
    PaperDocumentRoleV2: "PaperDocumentRoleV2",
    PaperDocumentKindV2: "PaperDocumentKindV2",
    PaperExtractionQualityV2: "PaperExtractionQualityV2",
    PaperExtractionLayerV2: "PaperExtractionLayerV2",
    PaperResolutionStatusV2: "PaperResolutionStatusV2",
    PaperAdjudicationRecommendationV2: "PaperAdjudicationRecommendationV2",
    BatchInputFormatV2: "BatchInputFormatV2",
    BatchAnalysisScopeV2: "BatchAnalysisScopeV2",
    BatchCohortModelV2: "BatchCohortModelV2",
    BatchNormalizationStatusV2: "BatchNormalizationStatusV2",
    BatchFilterStageV2: "BatchFilterStageV2",
    BatchFilterOutcomeV2: "BatchFilterOutcomeV2",
    BatchFilterReasonV2: "BatchFilterReasonV2",
    BatchIntervalScopeV2: "BatchIntervalScopeV2",
    BatchFieldNameV2: "BatchFieldNameV2",
    BatchFieldValueStatusV2: "BatchFieldValueStatusV2",
    BatchExportFormatV2: "BatchExportFormatV2",
    BatchExportStateV2: "BatchExportStateV2",
    PanelLaunchPostureV2: "PanelLaunchPostureV2",
    PanelIntervalScopeV2: "PanelIntervalScopeV2",
    ReportSectionIdV2: "ReportSectionIdV2",
    ReportSectionStateV2: "ReportSectionStateV2",
    ReportMatchLevelV2: "ReportMatchLevelV2",
    ReportPredictorStateV2: "ReportPredictorStateV2",
    ReportCoverageV2: "ReportCoverageV2",
}


BE6_REPORT_V2_FIELDS: dict[type[BaseModel], set[str]] = {
    CodonCell: {"aa_alt", "dna_ref", "dna_alt"},
    NearbyVariant: {"protein_change"},
    LocusContext: {"coords"},
    PredictorCard: {"verdict_label"},
    AcmgCriteriaScaffold: {"intro", "note"},
    CuratedVariantsDistribution: {
        "license_gate",
        "launch_gate",
        "public_serialization_allowed",
        "query_accession",
        "query_cell",
        "query_classification",
        "query_variant_id",
        "row_totals",
        "source_id",
        "source_status",
        "source_url",
        "source_version",
        "subtitle",
        "warnings",
    },
    AssociatedCondition: {"db_tag", "db_tag_bold", "source_list"},
    PublicationsCallout: {"blurb"},
}


def _frontend_backend_ts_paths() -> list[Path]:
    # tests/ -> backend/ -> app/web/...
    app_root = Path(__file__).resolve().parents[2]
    return [app_root / "web" / "lib" / "backend.ts"]


def _path_id(path: Path) -> str:
    return path.relative_to(Path(__file__).resolve().parents[3]).as_posix()


def _extract_ts_interface_body(source: str, name: str) -> str:
    """Return an interface body plus inherited interface fields."""
    match = re.search(
        rf"export\s+interface\s+{re.escape(name)}" r"(?:\s+extends\s+(?P<parents>[^\{]+))?\s*\{",
        source,
    )
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
    body = source[start : i - 1]
    parents = match.group("parents")
    if not parents:
        return body
    inherited = [
        _extract_ts_interface_body(source, parent.strip()) for parent in parents.split(",")
    ]
    return "\n".join([*inherited, body])


def _extract_ts_literal_values(source: str, name: str) -> set[str]:
    match = re.search(
        rf"export\s+type\s+{re.escape(name)}\s*=\s*(.*?)"
        r"(?=\nexport\s+(?:type|interface|function)|\nconst\s|\Z)",
        source,
        re.DOTALL,
    )
    if not match:
        raise AssertionError(f"export type {name} not found in backend.ts")
    return set(re.findall(r"'([^']+)'", match.group(1)))


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


@pytest.mark.parametrize(
    "literal_type,ts_name",
    list(WORKFLOW_LITERAL_TO_TS_TYPE.items()),
    ids=lambda value: value if isinstance(value, str) else str(value),
)
@pytest.mark.parametrize(
    "backend_ts_path",
    _frontend_backend_ts_paths(),
    ids=_path_id,
)
def test_workflow_literal_values_match_typescript(literal_type, ts_name, backend_ts_path):
    backend_ts = backend_ts_path.read_text(encoding="utf-8")
    assert _extract_ts_literal_values(backend_ts, ts_name) == set(get_args(literal_type))


@pytest.mark.parametrize(
    "model,ts_name",
    [
        (CanonicalVariantRefV1, "CanonicalVariantRefV1"),
        (SelectionRangeV1, "SelectionRangeV1"),
        (WorkbenchDesignContextV1, "WorkbenchDesignContextV1"),
        (WorkflowContextV1, "WorkflowContextV1"),
        (ProcessingDisclosureV1, "ProcessingDisclosureV1"),
        (WorkflowArtifactV1, "WorkflowArtifactV1"),
        (WorkflowRunV1, "WorkflowRunV1"),
        (RelatedVariantItemV1, "RelatedVariantItemV1"),
        (RelatedVariantGroupV1, "RelatedVariantGroupV1"),
        (CuratedVariantPageV1, "CuratedVariantPageV1"),
        (CapabilityExecutionDisclosureV2, "CapabilityExecutionDisclosureV2"),
        (WorkbenchReferenceBasisV2, "WorkbenchReferenceBasisV2"),
        (WorkbenchSparseEditV2, "WorkbenchSparseEditV2"),
        (WorkbenchDesignContextV2, "WorkbenchDesignContextV2"),
        (WorkbenchResultBindingV2, "WorkbenchResultBindingV2"),
        (CrisprVerifiedLocusV2, "CrisprVerifiedLocusV2"),
        (CrisprGuideIdentityV2, "CrisprGuideIdentityV2"),
        (CrisprScoreV2, "CrisprScoreV2"),
        (PaperDocumentUploadV2, "PaperDocumentUploadV2"),
        (PaperBibliographicMetadataV2, "PaperBibliographicMetadataV2"),
        (PaperDocumentMetadataV2, "PaperDocumentMetadataV2"),
        (PaperDocumentBundleV2, "PaperDocumentBundleV2"),
        (PaperDocumentBundleRequestV2, "PaperDocumentBundleRequestV2"),
        (PaperPageExtractionQualityV2, "PaperPageExtractionQualityV2"),
        (PaperEvidenceSpanV2, "PaperEvidenceSpanV2"),
        (PaperVariantMentionV2, "PaperVariantMentionV2"),
        (PaperMentionResolutionV2, "PaperMentionResolutionV2"),
        (PaperAiAdjudicationV2, "PaperAiAdjudicationV2"),
        (PaperDocumentExtractionV2, "PaperDocumentExtractionV2"),
        (BatchInputEnvelopeV2, "BatchInputEnvelopeV2"),
        (BatchAlleleV2, "BatchAlleleV2"),
        (BatchAlleleIdentityV2, "BatchAlleleIdentityV2"),
        (BatchSourceSnapshotV2, "BatchSourceSnapshotV2"),
        (BatchFilterPlanV2, "BatchFilterPlanV2"),
        (BatchFilterDispositionV2, "BatchFilterDispositionV2"),
        (BatchSampleProvenanceV2, "BatchSampleProvenanceV2"),
        (BatchFieldExecutionV2, "BatchFieldExecutionV2"),
        (BatchPagingV2, "BatchPagingV2"),
        (BatchExportV2, "BatchExportV2"),
        (PanelIntervalProvenanceV2, "PanelIntervalProvenanceV2"),
        (PanelSourceSnapshotV2, "PanelSourceSnapshotV2"),
        (ReportSectionExecutionV2, "ReportSectionExecutionV2"),
        (ReportPredictorExecutionV2, "ReportPredictorExecutionV2"),
        (ReportExecutionStateV2, "ReportExecutionStateV2"),
    ],
    ids=lambda value: value if isinstance(value, str) else value.__name__,
)
@pytest.mark.parametrize(
    "backend_ts_path",
    _frontend_backend_ts_paths(),
    ids=_path_id,
)
def test_workflow_required_and_nullable_fields_match_typescript(model, ts_name, backend_ts_path):
    backend_ts = backend_ts_path.read_text(encoding="utf-8")
    body = _extract_ts_interface_body(backend_ts, ts_name)

    for field_name, field in model.model_fields.items():
        declaration = re.search(
            rf"^\s*{re.escape(field_name)}(?P<optional>\?)?\s*:\s*(?P<type>[^\n]+)",
            body,
            re.MULTILINE,
        )
        assert declaration, f"{ts_name}.{field_name} is missing from backend.ts"
        assert (
            bool(declaration.group("optional")) is not field.is_required()
        ), f"{ts_name}.{field_name} requiredness differs from Pydantic"
        python_nullable = type(None) in get_args(field.annotation)
        typescript_nullable = bool(re.search(r"\bnull\b", declaration.group("type")))
        assert (
            typescript_nullable is python_nullable
        ), f"{ts_name}.{field_name} null behavior differs from Pydantic"


@pytest.mark.parametrize(
    "backend_ts_path",
    _frontend_backend_ts_paths(),
    ids=_path_id,
)
def test_workflow_schema_versions_and_url_builders_are_mirrored(backend_ts_path):
    backend_ts = backend_ts_path.read_text(encoding="utf-8")
    expected_versions = {
        "CanonicalVariantRefV1": "canonical_variant_ref.v1",
        "SelectionRangeV1": "selection_range.v1",
        "WorkbenchDesignContextV1": "workbench_design_context.v1",
        "WorkflowContextV1": "workflow_context.v1",
        "WorkflowRunV1": "workflow_run.v1",
        "CapabilityExecutionDisclosureV2": "capability_execution.v2",
        "WorkbenchReferenceBasisV2": "workbench_reference_basis.v2",
        "WorkbenchDesignContextV2": "workbench_design_context.v2",
        "CrisprGuideIdentityV2": "crispr_guide_identity.v2",
        "PaperDocumentBundleV2": "paper_document_bundle.v2",
        "PaperDocumentBundleRequestV2": "paper_document_bundle_request.v2",
        "PaperDocumentExtractionV2": "paper_document_extraction.v2",
        "BatchInputEnvelopeV2": "batch_input_envelope.v2",
        "BatchSourceSnapshotV2": "batch_source_snapshot.v2",
        "PanelSourceSnapshotV2": "panel_source_snapshot.v2",
        "ReportExecutionStateV2": "report_execution_state.v2",
    }
    for interface, version in expected_versions.items():
        body = _extract_ts_interface_body(backend_ts, interface)
        assert re.search(
            rf"^\s*schema_version\??\s*:\s*'{re.escape(version)}'",
            body,
            re.MULTILINE,
        )
    for builder in (
        "buildReportHrefV1",
        "buildWorkbenchHrefV1",
        "buildCompareHrefV1",
        "buildPaperHrefV1",
    ):
        assert f"export function {builder}(" in backend_ts


@pytest.mark.parametrize(
    "backend_ts_path",
    _frontend_backend_ts_paths(),
    ids=_path_id,
)
def test_workbench_v2_responses_share_one_typescript_envelope(backend_ts_path):
    backend_ts = backend_ts_path.read_text(encoding="utf-8")
    envelope = _extract_ts_interface_body(backend_ts, "WorkbenchV2ResponseEnvelope")
    for field in ("execution_disclosure", "verified_context", "context_binding"):
        assert re.search(rf"^\s*{field}\?\s*:", envelope, re.MULTILINE)
    for response in (
        "PrimerResponse",
        "CrisprResponse",
        "CrisprSsodnResponse",
        "CrisprOffTargetResponse",
        "CrisprScreeningPrimerResponse",
        "CrisprTideResponse",
        "AlignTraceResponse",
        "AlignResponse",
        "AlignReferenceResponse",
    ):
        assert re.search(
            rf"export\s+interface\s+{response}\s+extends\s+WorkbenchV2ResponseEnvelope",
            backend_ts,
        )


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
        r"^\s*transcript_projection\??\s*:\s*ViewerTranscriptProjection \| null",
        response_body,
        re.MULTILINE,
    )
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
    "backend_ts_path",
    _frontend_backend_ts_paths(),
    ids=_path_id,
)
def test_search_contract_declares_response_and_answer_literals(backend_ts_path):
    backend_ts = backend_ts_path.read_text(encoding="utf-8")

    assert "export type SearchMetadataValue =" in backend_ts
    assert "export type SearchDocType =" in backend_ts
    for doc_type in (
        "'report'",
        "'run'",
        "'library_variant'",
        "'popular_variant'",
        "'publication'",
        "'trial'",
        "'report_section'",
        "'gene'",
        "'condition'",
        "'gene_disease'",
        "'source'",
    ):
        assert doc_type in backend_ts

    assert "export type SearchVisibilityScope =" in backend_ts
    for visibility_scope in ("'public'", "'private'", "'internal'"):
        assert visibility_scope in backend_ts

    assert "export type SearchMatchType =" in backend_ts
    for match_type in (
        "'exact_run_id'",
        "'exact_report_id'",
        "'exact_patient_id'",
        "'exact_variant'",
        "'full_text'",
    ):
        assert match_type in backend_ts


@pytest.mark.parametrize(
    "backend_ts_path",
    _frontend_backend_ts_paths(),
    ids=_path_id,
)
def test_paper_upload_handle_is_request_only_in_typescript(backend_ts_path):
    backend_ts = backend_ts_path.read_text(encoding="utf-8")

    request_body = _extract_ts_interface_body(backend_ts, "PaperDocumentUploadV2")
    assert re.search(r"^\s*upload_ref\s*:\s*string", request_body, re.MULTILINE)
    for output_interface in (
        "PaperDocumentMetadataV2",
        "PaperDocumentBundleV2",
        "PaperDocumentExtractionV2",
        "PaperVariantsResponse",
    ):
        assert "upload_ref" not in _extract_ts_interface_body(backend_ts, output_interface)


@pytest.mark.parametrize(
    "model,fields",
    list(BE6_REPORT_V2_FIELDS.items()),
    ids=lambda v: v.__name__ if isinstance(v, type) else ",".join(sorted(v)),
)
def test_be6_report_v2_fields_are_declared_on_pydantic_models(model, fields):
    assert fields <= set(model.model_fields.keys())
