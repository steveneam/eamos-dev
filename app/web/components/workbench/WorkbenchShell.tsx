'use client'
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { useRouter } from 'next/navigation'
import type {
  AlleleMode,
  GeneViewerResponse,
  GeneViewerRequest,
  PrimerPair,
  ProteinDomainTrack,
  ViewerTrack,
  WorkbenchTool,
  WorkbenchDesignContextV1,
} from '@/lib/backend'
import { getGeneViewer, lookupSummary } from '@/lib/api'
import { adaptGeneViewer } from '@/lib/workbench/gene-viewer-adapter'
import { adaptFullLocus, type FullLocusViewModel } from '@/lib/workbench/full-locus-adapter'
import type { ClinvarVariant, GeneWindowData } from '@/lib/workbench/gene-window'
import { CanvasHeader, type ViewerMode } from './CanvasHeader'
import { SidePanel } from './SidePanel'
import { ToolIcon } from './ToolIcon'
import { WorkbenchAiPanel } from './WorkbenchAiPanel'
import { defaultViewerPane, TOOL_META, type ViewerPane } from './tools'
import { readPane, writePane } from '@/lib/work-rail-collapse'
import { PrimerPanel } from './primer/PrimerPanel'
import { CrisprPanel } from './crispr/CrisprPanel'
import { AlignPanel } from './align/AlignPanel'
import {
  SequenceViewerV2,
  type ScratchEntry,
  type SequenceViewerHandle,
} from './viewer/SequenceViewerV2'
import { FullLocusViewer, FullLocusUnsupportedBanner } from './viewer/FullLocusViewer'
import {
  DEFAULT_ZOOM_STEP,
  ZOOM_SETTINGS_BY_STEP,
  type ZoomStep,
} from './viewer/zoom-config'
import {
  DEFAULT_TRACKS,
  type SelectionSummary,
  type StrandMode,
  type TrackState,
} from './viewer/viewer-types'
import { WorkRail } from '@/components/layout/WorkRail'
import { RailFoot } from '@/components/layout/RailFoot'
import { LibrarySection } from '@/components/library/LibrarySection'
import { reportHrefForQuery } from '@/lib/variant-search'
import type { SavedVariant } from '@/lib/variant-library'
import {
  buildWorkbenchDesignContext,
  canonicalVariantFromViewer,
  parseGenomicIdentity,
  type DesignSelectionDraft,
} from '@/lib/workbench/design-context'
import {
  clearWorkbenchWorkspace,
  createWorkbenchWorkspace,
  readWorkbenchWorkspace,
  workbenchIdentity,
  workspaceExpiryLabel,
  writeWorkbenchWorkspace,
  type WorkbenchBrowserWorkspaceV1,
  type WorkbenchDerivedResultV1,
} from '@/lib/workbench/workspace'
import {
  designDraftFromWindow,
  windowStateFromDesignDraft,
  type WindowDesignState,
} from '@/lib/workbench/window-design-context'

export type { ScratchEntry }

interface WorkbenchShellProps {
  tool: WorkbenchTool
  gene: string
  cdna: string
  transcript?: string
  initialView: ViewerMode
  onViewChange: (view: ViewerMode) => void
  onTranscriptChange: (transcript: string) => void
}

const PANEL_TOOLS: WorkbenchTool[] = ['primer', 'crispr', 'align']
const WORKBENCH_VIEWER_TRACKS: ViewerTrack[] = [
  'sequence',
  'exons',
  'clinvar',
  'protein_features',
  'restriction',
]

function renderToolPanel(
  tool: WorkbenchTool,
  gene: string,
  cdna: string,
  transcript: string | undefined,
  data: GeneWindowData,
  controls: {
    primerSelected: PrimerPair | null
    onPrimerSelect: (p: PrimerPair | null) => void
    onCrisprSubTab: (tab: string) => void
    designContext: WorkbenchDesignContextV1 | null
    resultDigest?: string
    derivedResult?: WorkbenchDerivedResultV1
    executionBlockedReason: string | null
    onResultDigest: (
      tool: 'primer' | 'crispr' | 'align',
      digest: string,
      derivedResult?: WorkbenchDerivedResultV1,
    ) => void
  },
) {
  switch (tool) {
    case 'primer':
      return (
        <PrimerPanel
          gene={gene}
          cdna={cdna}
          selected={controls.primerSelected}
          onSelect={controls.onPrimerSelect}
          designContext={controls.designContext}
          restoredResultDigest={controls.resultDigest}
          restoredDerivedResult={controls.derivedResult}
          executionBlockedReason={controls.executionBlockedReason}
          onResultDigest={(digest, summary) => controls.onResultDigest('primer', digest, summary)}
        />
      )
    case 'crispr':
      return <CrisprPanel
        gene={gene}
        cdna={cdna}
        designContext={controls.designContext}
        restoredResultDigest={controls.resultDigest}
        restoredDerivedResult={controls.derivedResult}
        executionBlockedReason={controls.executionBlockedReason}
        onResultDigest={(digest, summary) => controls.onResultDigest('crispr', digest, summary)}
        onSubTabChange={controls.onCrisprSubTab}
      />
    case 'align':
      return <AlignPanel
        data={data}
        gene={gene}
        cdna={cdna}
        transcript={transcript ?? data.transcript}
        designContext={controls.designContext}
        restoredResultDigest={controls.resultDigest}
        restoredDerivedResult={controls.derivedResult}
        executionBlockedReason={controls.executionBlockedReason}
        onResultDigest={(digest, summary) => controls.onResultDigest('align', digest, summary)}
      />
    default:
      return null
  }
}

function summaryClassification(header: Record<string, unknown> | null | undefined): string | null {
  const classification = header?.classification
  return typeof classification === 'string' ? classification : null
}

function exonForQueriedVariant(data: GeneWindowData): number {
  const cdsPos = data.queriedVariant.cdsPos
  return (
    data.exons.find((exon) => cdsPos >= exon.cdsStart && cdsPos <= exon.cdsEnd)?.num ??
    data.exons[0]?.num ??
    0
  )
}

function draftFromWorkspace(workspace: WorkbenchBrowserWorkspaceV1): DesignSelectionDraft | null {
  if (!workspace.selection) return null
  return {
    genomicStart: workspace.selection.genomicStart,
    genomicEnd: workspace.selection.genomicEnd,
    orientation: workspace.selection.orientation,
    sequenceBasis: workspace.selection.sequenceBasis,
    baseAllele: workspace.selection.baseAllele,
    editRevision: workspace.selection.editRevision,
    edits: workspace.edits,
  }
}

function defaultDesignDraft(
  response: GeneViewerResponse | null,
  alleleMode: AlleleMode,
): DesignSelectionDraft | null {
  if (!response?.full_locus) return null
  const genomic = parseGenomicIdentity(
    response.queried_variant.genomic_hg38,
    response.full_locus.locus.chrom,
  )
  if (!genomic) return null
  return {
    genomicStart: genomic.position,
    genomicEnd: genomic.position + Math.max(1, genomic.ref.length) - 1,
    orientation: 'transcript',
    sequenceBasis: alleleMode,
    baseAllele: alleleMode,
    editRevision: 0,
    edits: [],
  }
}

function designExecutionBlockedReason(
  context: WorkbenchDesignContextV1 | null,
): string | null {
  if (!context) return null
  const queried = parseGenomicIdentity(
    context.variant.genomic_hg38,
    context.selection.chrom,
  )
  const selection = context.selection
  if (
    !queried ||
    selection.genomic_start !== queried.position ||
    selection.genomic_end !== queried.position ||
    selection.edit_revision !== 0 ||
    selection.sequence_basis === 'edited'
  ) {
    return 'The deployed design engine validates this envelope but still executes only at the queried-variant window. Distant or edited selections are blocked to prevent a misleading result.'
  }
  return null
}

function WorkbenchShellInner({
  tool,
  gene,
  cdna,
  transcript,
  initialView,
  onViewChange,
  onTranscriptChange,
}: WorkbenchShellProps) {
  const workspaceIdentity = workbenchIdentity(gene, cdna, transcript)
  // Keep the server and hydration render identical. Browser-session state is
  // restored only after hydration below.
  const [initialWorkspace] = useState(() => createWorkbenchWorkspace(workspaceIdentity))
  const workspaceRef = useRef(initialWorkspace)
  const [trackOn, setTrackOn] = useState<TrackState>(DEFAULT_TRACKS)
  const [strandMode, setStrandMode] = useState<StrandMode>('both')
  const [zoomStep, setZoomStep] = useState<ZoomStep>(DEFAULT_ZOOM_STEP)
  const zoomSetting = ZOOM_SETTINGS_BY_STEP[zoomStep]
  const [navCollapsed, setNavCollapsed] = useState(false)
  const [exonTableOpen, setExonTableOpen] = useState(false)
  const [scratch, setScratch] = useState<ScratchEntry[]>([])
  const [selSummary, setSelSummary] = useState<SelectionSummary | null>(null)
  // Primer pair toggled "show on gene view"; cleared with the session.
  const [selectedPrimer, setSelectedPrimer] = useState<PrimerPair | null>(null)
  const viewerContextKey = `${gene}|${cdna}|${transcript ?? ''}`
  const [activeExonFocus, setActiveExonFocus] = useState<{ key: string; exon: number } | null>(null)

  // ClinVar focus (clicked lollipop → Scratchpad log card). Key-stamped to the
  // variant context so it auto-clears when gene/cdna/transcript change, without
  // a setState-in-effect (mirrors the viewer's activeExonOverride pattern).
  const clinvarKey = viewerContextKey
  const [clinvarFocus, setClinvarFocus] = useState<{
    key: string
    variant: ClinvarVariant | null
  }>({ key: clinvarKey, variant: null })
  const selectedClinvar = clinvarFocus.key === clinvarKey ? clinvarFocus.variant : null
  const setSelectedClinvar = useCallback(
    (variant: ClinvarVariant | null) => setClinvarFocus({ key: clinvarKey, variant }),
    [clinvarKey],
  )

  const [alleleMode, setAlleleMode] = useState<AlleleMode>(
    initialWorkspace.selection?.baseAllele ?? 'reference',
  )
  const viewerMode = initialView
  const setViewerMode = onViewChange
  const [data, setData] = useState<GeneWindowData | null>(null)
  const [architectureData, setArchitectureData] = useState<GeneWindowData | null>(null)
  const [architectureProteinDomainTrack, setArchitectureProteinDomainTrack] =
    useState<ProteinDomainTrack | null>(null)
  const [locusModel, setLocusModel] = useState<FullLocusViewModel | null>(null)
  const [locusResponse, setLocusResponse] = useState<GeneViewerResponse | null>(null)
  const [viewerError, setViewerError] = useState<string | null>(null)
  const [designDraft, setDesignDraft] = useState<DesignSelectionDraft | null>(
    draftFromWorkspace(initialWorkspace),
  )
  const [designContext, setDesignContext] = useState<WorkbenchDesignContextV1 | null>(null)
  const [contextStatus, setContextStatus] = useState<'resolving' | 'ready' | 'unavailable'>(
    'resolving',
  )
  const [resultDigests, setResultDigests] = useState(
    initialWorkspace.result_digests,
  )
  const [derivedResults, setDerivedResults] = useState(
    initialWorkspace.derived_results,
  )
  const [workspaceExpiresAt, setWorkspaceExpiresAt] = useState(
    initialWorkspace.expires_at,
  )
  const [workspaceEpoch, setWorkspaceEpoch] = useState(0)
  const [workspaceSaveState, setWorkspaceSaveState] = useState<'dirty' | 'saved' | 'unavailable'>('saved')
  const [workspaceReady, setWorkspaceReady] = useState(false)

  useEffect(() => {
    const restored = readWorkbenchWorkspace(workspaceIdentity)
    if (restored) workspaceRef.current = restored
    queueMicrotask(() => {
      if (restored) {
        setAlleleMode(restored.selection?.baseAllele ?? 'reference')
        setDesignDraft(draftFromWorkspace(restored))
        setResultDigests(restored.result_digests)
        setDerivedResults(restored.derived_results)
        setWorkspaceExpiresAt(restored.expires_at)
      }
      setWorkspaceReady(true)
    })
  }, [workspaceIdentity])
  const activeExon =
    data != null
      ? activeExonFocus?.key === viewerContextKey
        ? activeExonFocus.exon
        : exonForQueriedVariant(data)
      : 0
  const setActiveExon = useCallback(
    (exon: number) => setActiveExonFocus({ key: viewerContextKey, exon }),
    [viewerContextKey],
  )

  useEffect(() => {
    const controller = new AbortController()
    queueMicrotask(() => {
      if (controller.signal.aborted) return
      setViewerError(null)
      setData(null)
      setArchitectureData(null)
      setArchitectureProteinDomainTrack(null)
    })
    const viewerRequest: GeneViewerRequest = {
      gene,
      cdna,
      transcript,
      allele_mode: alleleMode,
      tracks: WORKBENCH_VIEWER_TRACKS,
    }
    const summaryRequest = { gene, cdna, transcript, species: 'human' as const }
    Promise.all([
      getGeneViewer(viewerRequest, { signal: controller.signal }),
      lookupSummary(summaryRequest, { signal: controller.signal }).catch(() => null),
    ])
      .then(([resp, summary]) => {
        if (controller.signal.aborted) return
        const queriedVariantClassification = summaryClassification(summary?.header)
        setData(adaptGeneViewer(resp, alleleMode, { queriedVariantClassification }))
        setArchitectureData(adaptGeneViewer(resp, 'variant', {
          architecture: 'transcript',
          queriedVariantClassification,
        }))
        setArchitectureProteinDomainTrack(resp.tracks.protein_features.domain_track ?? null)
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setViewerError(error instanceof Error ? error.message : `Sequence unavailable for ${gene} ${cdna}`)
        setData(null)
        setArchitectureData(null)
        setArchitectureProteinDomainTrack(null)
      })
    return () => controller.abort()
  }, [alleleMode, cdna, gene, transcript])

  useEffect(() => {
    const controller = new AbortController()
    queueMicrotask(() => {
      if (controller.signal.aborted) return
      setLocusModel(null)
      setLocusResponse(null)
    })
    getGeneViewer({
      gene,
      cdna,
      transcript,
      allele_mode: 'reference',
      window: { kind: 'full_gene' },
      tracks: WORKBENCH_VIEWER_TRACKS,
    }, { signal: controller.signal })
      .then((response) => {
        if (controller.signal.aborted) return
        setLocusResponse(response.full_locus ? response : null)
        setLocusModel(adaptFullLocus(response))
      })
      .catch(() => {
        if (controller.signal.aborted) return
        setLocusResponse(null)
        setLocusModel({
          kind: 'unsupported',
          gene,
          cdna,
          transcript: transcript ?? '',
          warnings: [`full_gene_request_failed:${gene}`],
        })
      })
    return () => controller.abort()
  }, [cdna, gene, transcript])

  const activeDraft = useMemo(() => {
    const basis = designDraft ?? defaultDesignDraft(locusResponse, alleleMode)
    if (!basis) return null
    return {
      ...basis,
      baseAllele: alleleMode,
      sequenceBasis: basis.edits.length > 0 ? 'edited' as const : alleleMode,
      editRevision: basis.edits.length > 0 ? Math.max(1, basis.editRevision) : 0,
    }
  }, [alleleMode, designDraft, locusResponse])

  useEffect(() => {
    let stale = false
    queueMicrotask(() => {
      if (stale) return
      setDesignContext(null)
      setContextStatus(locusResponse && activeDraft ? 'resolving' : 'unavailable')
    })
    if (!locusResponse || !activeDraft) return () => { stale = true }
    buildWorkbenchDesignContext(locusResponse, activeDraft)
      .then((context) => {
        if (stale) return
        setDesignContext(context)
        setContextStatus(context ? 'ready' : 'unavailable')
      })
      .catch(() => {
        if (stale) return
        setDesignContext(null)
        setContextStatus('unavailable')
      })
    return () => { stale = true }
  }, [activeDraft, locusResponse])

  useEffect(() => {
    if (typeof window === 'undefined' || !workspaceReady) return
    const activeTool = tool === 'compare' ? 'viewer' : tool
    try {
      const next = writeWorkbenchWorkspace({
        ...workspaceRef.current,
        identity: workspaceIdentity,
        active_tool: activeTool,
        view: viewerMode,
        selection: activeDraft ? {
          genomicStart: activeDraft.genomicStart,
          genomicEnd: activeDraft.genomicEnd,
          orientation: activeDraft.orientation,
          sequenceBasis: activeDraft.sequenceBasis,
          baseAllele: activeDraft.baseAllele,
          editRevision: activeDraft.editRevision,
        } : null,
        edits: activeDraft?.edits ?? [],
        result_digests: resultDigests,
        derived_results: derivedResults,
      })
      workspaceRef.current = next
      queueMicrotask(() => {
        setWorkspaceExpiresAt(next.expires_at)
        setWorkspaceSaveState('saved')
      })
    } catch {
      queueMicrotask(() => setWorkspaceSaveState('unavailable'))
    }
  }, [activeDraft, derivedResults, resultDigests, tool, viewerMode, workspaceIdentity, workspaceReady])

  const recordResultDigest = useCallback(
    (
      resultTool: 'primer' | 'crispr' | 'align',
      digest: string,
      derivedResult?: WorkbenchDerivedResultV1,
    ) => {
      if (!/^[0-9a-f]{64}$/.test(digest)) return
      setWorkspaceSaveState('dirty')
      setResultDigests((current) => ({ ...current, [resultTool]: digest }))
      setDerivedResults((current) => {
        if (!derivedResult || derivedResult.tool !== resultTool || derivedResult.result_digest !== digest) {
          const next = { ...current }
          delete next[resultTool]
          return next
        }
        return { ...current, [resultTool]: derivedResult }
      })
    },
    [],
  )

  const clearWorkspace = useCallback(() => {
    clearWorkbenchWorkspace()
    const fresh = createWorkbenchWorkspace(workspaceIdentity)
    workspaceRef.current = fresh
    setDesignDraft(null)
    setResultDigests({})
    setDerivedResults({})
    setAlleleMode('reference')
    setScratch([])
    setSelSummary(null)
    setSelectedClinvar(null)
    setSelectedPrimer(null)
    setClinvarFocus({ key: viewerContextKey, variant: null })
    setWorkspaceExpiresAt(fresh.expires_at)
    setWorkspaceSaveState('saved')
    setWorkspaceEpoch((value) => value + 1)
  }, [setSelectedClinvar, viewerContextKey, workspaceIdentity])

  const windowInitialState = useMemo(
    () => locusResponse && data
      ? windowStateFromDesignDraft(locusResponse, data, activeDraft)
      : null,
    [activeDraft, data, locusResponse],
  )
  const windowBridgeEstablishedRef = useRef(false)
  const executionBlockedReason = designExecutionBlockedReason(designContext)
  const handleWindowDesignState = useCallback((state: WindowDesignState) => {
    if (!locusResponse || !data) return
    const strand = locusResponse.full_locus?.transcript_projection.strand
    const orientation = strandMode === 'rev'
      ? strand === '-' ? 'genomic_forward' : 'genomic_reverse'
      : 'transcript'
    const draft = designDraftFromWindow(locusResponse, data, state, alleleMode, orientation)
    if (draft) {
      windowBridgeEstablishedRef.current = true
      setWorkspaceSaveState('dirty')
      setDesignDraft(draft)
    } else if (windowBridgeEstablishedRef.current) {
      setWorkspaceSaveState('dirty')
      setDesignDraft(null)
    }
  }, [alleleMode, data, locusResponse, strandMode])

  const viewerRef = useRef<SequenceViewerHandle>(null)
  const router = useRouter()

  // Per-tool viewer pane for the 3-column canvas (STEP 6). SSR returns the
  // per-tool default; the client reads the persisted value (lazy init, no
  // setState-in-effect — mirrors WorkRail.initialCollapsed).
  const [paneByTool, setPaneByTool] = useState<Record<string, ViewerPane>>(() => {
    const init: Record<string, ViewerPane> = {}
    for (const t of PANEL_TOOLS) {
      let pane = defaultViewerPane(t)
      if (typeof window !== 'undefined') {
        const stored = readPane(t)
        if (stored === 'expanded' || stored === 'collapsed' || stored === 'hidden') pane = stored
      }
      init[t] = pane
    }
    return init
  })
  const viewerPane: ViewerPane =
    tool === 'viewer' ? 'expanded' : paneByTool[tool] ?? defaultViewerPane(tool)
  const setViewerPane = useCallback(
    (next: ViewerPane) => {
      setPaneByTool((m) => ({ ...m, [tool]: next }))
      writePane(tool, next)
    },
    [tool],
  )

  // Selecting CRISPR → Off-targets (the widest content) collapses the viewer so
  // the table gets the room. One-way nudge — the user can re-expand via the stub.
  const handleCrisprSubTab = useCallback(
    (subTab: string) => {
      if (subTab === 'offtargets') setViewerPane('collapsed')
    },
    [setViewerPane],
  )

  const toggleTrack = useCallback(
    (key: keyof TrackState) => setTrackOn((t) => ({ ...t, [key]: !t[key] })),
    [],
  )

  // Opening a saved variant on /workbench loads it into the sequence viewer
  // (a new URL → WorkbenchClient re-reads gene/cdna), not the report. Rows with
  // no gene (some VCF cohorts) can't drive the viewer, so they fall back to the
  // report — the shared LibrarySection's default behaviour.
  const openInViewer = useCallback(
    (v: SavedVariant) => {
      if (v.gene) {
        const params = new URLSearchParams({ gene: v.gene, cdna: v.variant ?? v.query })
        router.push(`/workbench?${params.toString()}`)
        return
      }
      const href = reportHrefForQuery(v.query)
      if (href) router.push(href)
    },
    [router],
  )

  // The rail content: SidePanel (or loading stub). The tool switcher now lives
  // in the context strip under the nav, not the rail.
  const railContent = data ? (
    <>
      <SidePanel
        tool={tool}
        data={data}
        scratch={scratch}
        selection={selSummary}
        selectedClinvar={selectedClinvar}
        exonTableOpen={exonTableOpen}
        activeExon={activeExon}
        onClearClinvar={() => setSelectedClinvar(null)}
        onToggleExonTable={() => setExonTableOpen((o) => !o)}
        onResetAll={() => viewerRef.current?.resetEdits()}
        onJumpToExon={(n) => viewerRef.current?.jumpToExon(n)}
        onDelSelection={() => viewerRef.current?.delSelection()}
        onReplaceSelection={(seq) => viewerRef.current?.replaceSelection(seq)}
        onClearSelection={() => viewerRef.current?.clearSelection()}
      />
    </>
  ) : (
    <>
      <div className="side-section">
        <div className="side-h">Viewer request</div>
        <div className="side-info">
          <b>{gene}</b>
          <br />
          {cdna}
          {transcript ? (
            <>
              <br />
              {transcript}
            </>
          ) : null}
        </div>
      </div>
    </>
  )

  // Canvas output — the dominant pane. For the bare Sequence viewer it's one
  // column; for a tool it's a 2-column grid [viewer | tool rail] so the primary
  // action (Generate / Run) sits beside the sequence, not below it (STEP 7).
  const isViewerOnly = tool === 'viewer'
  const fullLocusInitialState = activeDraft ? {
    selection: {
      genomicStart: activeDraft.genomicStart,
      genomicEnd: activeDraft.genomicEnd,
    },
    orientation: activeDraft.orientation,
    edits: activeDraft.edits,
    editRevision: activeDraft.editRevision,
  } : null

  const canvasHeader = (
    <CanvasHeader
      tool={tool}
      trackOn={trackOn}
      onToggleTrack={toggleTrack}
      strandMode={strandMode}
      onStrand={setStrandMode}
      alleleMode={alleleMode}
      onAlleleMode={setAlleleMode}
      viewerMode={viewerMode}
      onViewerMode={setViewerMode}
    />
  )

  const viewerBody =
    viewerMode === 'locus' && locusModel?.kind === 'ready' ? (
      <FullLocusViewer
        key={workspaceEpoch}
        model={locusModel}
        alleleMode={alleleMode}
        initialState={fullLocusInitialState}
        onDesignSelectionChange={(draft) => {
          setWorkspaceSaveState('dirty')
          setDesignDraft(draft)
        }}
        onTranscriptChange={onTranscriptChange}
      />
    ) : viewerMode === 'locus' && locusModel?.kind === 'unsupported' ? (
      <>
        <FullLocusUnsupportedBanner
          gene={locusModel.gene}
          onBackToWindow={() => setViewerMode('window')}
        />
        {data ? (
          <SequenceViewerV2
            key={workspaceEpoch}
            ref={viewerRef}
            data={data}
            architectureData={architectureData}
            architectureProteinDomainTrack={architectureProteinDomainTrack}
            trackOn={trackOn}
            strandMode={strandMode}
            baseW={zoomSetting.baseW}
            basesPerRow={zoomSetting.basesPerRow}
            zoomStep={zoomStep}
            onZoomStep={setZoomStep}
            navCollapsed={navCollapsed}
            onToggleMinimap={() => setNavCollapsed((c) => !c)}
            alleleMode={alleleMode}
            onScratchChange={setScratch}
            onSelectionChange={setSelSummary}
            initialDesignState={windowInitialState}
            onDesignStateChange={handleWindowDesignState}
            onActiveExonChange={setActiveExon}
            onClinvarSelect={setSelectedClinvar}
            activeClinvar={selectedClinvar?.cv ?? null}
            selectedPrimer={tool === 'primer' ? selectedPrimer : null}
          />
        ) : null}
      </>
    ) : data ? (
      <SequenceViewerV2
        key={workspaceEpoch}
        ref={viewerRef}
        data={data}
        architectureData={architectureData}
        architectureProteinDomainTrack={architectureProteinDomainTrack}
        trackOn={trackOn}
        strandMode={strandMode}
        baseW={zoomSetting.baseW}
        basesPerRow={zoomSetting.basesPerRow}
        zoomStep={zoomStep}
        onZoomStep={setZoomStep}
        navCollapsed={navCollapsed}
        onToggleMinimap={() => setNavCollapsed((c) => !c)}
        alleleMode={alleleMode}
        onScratchChange={setScratch}
        onSelectionChange={setSelSummary}
        initialDesignState={windowInitialState}
        onDesignStateChange={handleWindowDesignState}
        onActiveExonChange={setActiveExon}
        onClinvarSelect={setSelectedClinvar}
        activeClinvar={selectedClinvar?.cv ?? null}
        selectedPrimer={tool === 'primer' ? selectedPrimer : null}
      />
    ) : (
      <div className="viewer-loading" role={viewerError ? 'alert' : 'status'}>
        {viewerError ?? 'Loading sequence...'}
      </div>
    )

  const toolPanel = (
    <div key={`${tool}-${workspaceEpoch}`} className="tool-panel active" data-panel={tool}>
      {data ? (
        renderToolPanel(tool, gene, cdna, transcript, data, {
          primerSelected: selectedPrimer,
          onPrimerSelect: setSelectedPrimer,
          onCrisprSubTab: handleCrisprSubTab,
          designContext,
          resultDigest: tool === 'primer' || tool === 'crispr' || tool === 'align'
            ? resultDigests[tool]
            : undefined,
          derivedResult: tool === 'primer' || tool === 'crispr' || tool === 'align'
            ? derivedResults[tool]
            : undefined,
          executionBlockedReason,
          onResultDigest: recordResultDigest,
        })
      ) : (
        <div className="viewer-loading">{viewerError ?? 'Loading sequence...'}</div>
      )}
    </div>
  )

  const workspaceBar = (
    <div className="wb-workspace-status" role="status">
      <span className={`wb-workspace-state wb-workspace-state--${workspaceSaveState}`}>
        {workspaceSaveState === 'dirty'
          ? 'Saving in this tab…'
          : workspaceSaveState === 'unavailable'
            ? 'Browser-session storage unavailable'
            : 'Saved in this tab'}
      </span>
      <span>
        Anonymous browser session · expires in {workspaceExpiryLabel(workspaceExpiresAt)} or when this tab session ends
      </span>
      <span>
        {contextStatus === 'ready' && designContext
          ? `${designContext.selection.chrom}:${designContext.selection.genomic_start.toLocaleString('en-US')}-${designContext.selection.genomic_end.toLocaleString('en-US')} · context ${designContext.context_digest.slice(0, 10)}`
          : contextStatus === 'resolving'
            ? 'Resolving exact design context…'
            : 'Exact design context unavailable; design runs are disabled'}
      </span>
      <button type="button" onClick={clearWorkspace}>Clear session workspace</button>
    </div>
  )

  // The viewer column: full content when expanded; a re-expand stub when
  // collapsed. (`hidden` drops the column — handled by the grid template.)
  const viewerColumn =
    viewerPane === 'collapsed' ? (
      <button
        type="button"
        className="wb-viewer-stub"
        onClick={() => setViewerPane('expanded')}
        aria-label="Expand sequence viewer"
        title="Show sequence"
      >
        <span>Sequence</span>
      </button>
    ) : (
      <>
        <div className="wb-viewer-head">
          <button
            type="button"
            className="wb-viewer-min"
            onClick={() => setViewerPane('collapsed')}
            aria-label="Minimise sequence viewer"
            title="Minimise sequence"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          {canvasHeader}
        </div>
        <section className="viewer">{viewerBody}</section>
      </>
    )

  const canvasOutput = isViewerOnly ? (
    <main className="canvas">
      {workspaceBar}
      {canvasHeader}
      <section className="viewer">{viewerBody}</section>
    </main>
  ) : (
    <main className="canvas canvas-split" data-viewer-pane={viewerPane}>
      {workspaceBar}
      <div className="wb-viewer-col">{viewerColumn}</div>
      <aside className="wb-tool-rail">{toolPanel}</aside>
    </main>
  )

  return (
    <div className="wb-work-shell-wrap" style={{ '--rail-top': 'calc(var(--nav-h) + var(--ctx-h))' } as CSSProperties}>
      <WorkRail
        surface="workbench"
        title={TOOL_META[tool].rail}
        titleIcon={
          <span className="wb-tool-ic" aria-hidden>
            <ToolIcon tool={tool} />
          </span>
        }
        output={canvasOutput}
        foot={<RailFoot />}
        aiPanel={<WorkbenchAiPanel tool={tool} gene={gene} cdna={cdna} />}
        className="wb-work-shell"
      >
        {railContent}
        <LibrarySection onOpen={openInViewer} currentQuery={`${gene} ${cdna}`} openLabel="Open in viewer" />
      </WorkRail>
    </div>
  )
}

export function WorkbenchShell(props: WorkbenchShellProps) {
  const identity = workbenchIdentity(props.gene, props.cdna, props.transcript)
  return <WorkbenchShellInner key={identity} {...props} />
}
