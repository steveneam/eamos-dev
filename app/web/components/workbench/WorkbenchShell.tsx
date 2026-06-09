'use client'
import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react'
import { useRouter } from 'next/navigation'
import type { AlleleMode, PrimerPair, WorkbenchTool } from '@/lib/backend'
import { getGeneViewer } from '@/lib/api'
import { adaptGeneViewer } from '@/lib/workbench/gene-viewer-adapter'
import { adaptFullLocus, type FullLocusViewModel } from '@/lib/workbench/full-locus-adapter'
import { GENE_VIEWER_SAMPLE } from '@/lib/workbench/gene-viewer-sample'
import type { ClinvarVariant, GeneWindowData } from '@/lib/workbench/gene-window'
import { CanvasHeader, type ViewerMode } from './CanvasHeader'
import { SidePanel } from './SidePanel'
import { defaultViewerPane, type ViewerPane } from './tools'
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
import { ZoomSlider } from './viewer/ZoomSlider'
import { ZOOM_PRESETS } from './viewer/zoom-config'
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

export type { ScratchEntry }

interface WorkbenchShellProps {
  tool: WorkbenchTool
  gene: string
  cdna: string
  transcript?: string
}

const PANEL_TOOLS: WorkbenchTool[] = ['primer', 'crispr', 'align']

function renderToolPanel(
  tool: WorkbenchTool,
  gene: string,
  cdna: string,
  data: GeneWindowData,
  primerSel: { selected: PrimerPair | null; onSelect: (p: PrimerPair | null) => void },
) {
  switch (tool) {
    case 'primer':
      return (
        <PrimerPanel
          gene={gene}
          cdna={cdna}
          selected={primerSel.selected}
          onSelect={primerSel.onSelect}
        />
      )
    case 'crispr':
      return <CrisprPanel gene={gene} cdna={cdna} />
    case 'align':
      return <AlignPanel data={data} cdna={cdna} />
    default:
      return null
  }
}

function isDefaultViewerRequest(gene: string, cdna: string, transcript?: string): boolean {
  return (
    gene.trim().toUpperCase() === GENE_VIEWER_SAMPLE.identity.gene &&
    cdna.replace(/\s+/g, '') === GENE_VIEWER_SAMPLE.queried_variant.hgvs_c &&
    (!transcript || transcript === GENE_VIEWER_SAMPLE.identity.resolved_transcript)
  )
}

export function WorkbenchShell({ tool, gene, cdna, transcript }: WorkbenchShellProps) {
  const [trackOn, setTrackOn] = useState<TrackState>(DEFAULT_TRACKS)
  const [strandMode, setStrandMode] = useState<StrandMode>('both')
  const [baseW, setBaseW] = useState<number>(ZOOM_PRESETS.exon)
  const [navCollapsed, setNavCollapsed] = useState(false)
  const [exonTableOpen, setExonTableOpen] = useState(false)
  const [scratch, setScratch] = useState<ScratchEntry[]>([])
  const [selSummary, setSelSummary] = useState<SelectionSummary | null>(null)
  const [activeExon, setActiveExon] = useState(4)

  // ClinVar focus (clicked lollipop → Scratchpad log card). Key-stamped to the
  // variant context so it auto-clears when gene/cdna/transcript change, without
  // a setState-in-effect (mirrors the viewer's activeExonOverride pattern).
  const clinvarKey = `${gene}|${cdna}|${transcript ?? ''}`
  const [clinvarFocus, setClinvarFocus] = useState<{
    key: string
    variant: ClinvarVariant | null
  }>({ key: clinvarKey, variant: null })
  const selectedClinvar = clinvarFocus.key === clinvarKey ? clinvarFocus.variant : null
  const setSelectedClinvar = useCallback(
    (variant: ClinvarVariant | null) => setClinvarFocus({ key: clinvarKey, variant }),
    [clinvarKey],
  )

  const [alleleMode, setAlleleMode] = useState<AlleleMode>('reference')
  const [viewerMode, setViewerMode] = useState<ViewerMode>('window')
  const [data, setData] = useState<GeneWindowData | null>(() =>
    isDefaultViewerRequest(gene, cdna, transcript)
      ? adaptGeneViewer(GENE_VIEWER_SAMPLE, 'reference')
      : null,
  )
  const [locusModel, setLocusModel] = useState<FullLocusViewModel | null>(null)
  const [viewerError, setViewerError] = useState<string | null>(null)

  useEffect(() => {
    let stale = false
    const defaultRequest = isDefaultViewerRequest(gene, cdna, transcript)
    queueMicrotask(() => {
      if (stale) return
      setViewerError(null)
      if (!defaultRequest) setData(null)
      if (viewerMode !== 'locus') setLocusModel(null)
    })
    getGeneViewer({
      gene,
      cdna,
      transcript,
      allele_mode: alleleMode,
      window: viewerMode === 'locus' ? { kind: 'full_gene' } : undefined,
    })
      .then((resp) => {
        if (stale) return
        setData(adaptGeneViewer(resp, alleleMode))
        if (viewerMode === 'locus') setLocusModel(adaptFullLocus(resp))
        else setLocusModel(null)
      })
      .catch(() => {
        if (stale) return
        if (viewerMode === 'window' && defaultRequest) {
          setData(adaptGeneViewer(GENE_VIEWER_SAMPLE, alleleMode))
          return
        }
        if (viewerMode === 'locus') {
          setLocusModel({
            kind: 'unsupported',
            gene,
            cdna,
            transcript: transcript ?? '',
            warnings: [`full_gene_request_failed:${gene}`],
          })
        }
        setViewerError(`Sequence unavailable for ${gene} ${cdna}`)
        setData(null)
      })
    return () => {
      stale = true
    }
  }, [alleleMode, cdna, gene, transcript, viewerMode])

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

  // Primer pair toggled "show on gene view" → a rough amplicon overlay in the
  // viewer (only meaningful on the Primer tool; gated at the prop below).
  const [selectedPrimer, setSelectedPrimer] = useState<PrimerPair | null>(null)

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
      <FullLocusViewer model={locusModel} />
    ) : viewerMode === 'locus' && locusModel?.kind === 'unsupported' ? (
      <>
        <FullLocusUnsupportedBanner
          gene={locusModel.gene}
          onBackToWindow={() => setViewerMode('window')}
        />
        {data ? (
          <SequenceViewerV2
            ref={viewerRef}
            data={data}
            trackOn={trackOn}
            strandMode={strandMode}
            baseW={baseW}
            onBaseW={setBaseW}
            navCollapsed={navCollapsed}
            onToggleMinimap={() => setNavCollapsed((c) => !c)}
            alleleMode={alleleMode}
            onScratchChange={setScratch}
            onSelectionChange={setSelSummary}
            onActiveExonChange={setActiveExon}
            onClinvarSelect={setSelectedClinvar}
            activeClinvar={selectedClinvar?.cv ?? null}
            selectedPrimer={tool === 'primer' ? selectedPrimer : null}
          />
        ) : null}
      </>
    ) : data ? (
      <SequenceViewerV2
        ref={viewerRef}
        data={data}
        trackOn={trackOn}
        strandMode={strandMode}
        baseW={baseW}
        onBaseW={setBaseW}
        navCollapsed={navCollapsed}
        onToggleMinimap={() => setNavCollapsed((c) => !c)}
        alleleMode={alleleMode}
        onScratchChange={setScratch}
        onSelectionChange={setSelSummary}
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
    <div className="tool-panel active" data-panel={tool}>
      {data ? (
        renderToolPanel(tool, gene, cdna, data, {
          selected: selectedPrimer,
          onSelect: setSelectedPrimer,
        })
      ) : (
        <div className="viewer-loading">{viewerError ?? 'Loading sequence...'}</div>
      )}
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
      {canvasHeader}
      <section className="viewer">{viewerBody}</section>
    </main>
  ) : (
    <main className="canvas canvas-split" data-viewer-pane={viewerPane}>
      <div className="wb-viewer-col">{viewerColumn}</div>
      <aside className="wb-tool-rail">{toolPanel}</aside>
    </main>
  )

  return (
    <div className="wb-work-shell-wrap" style={{ '--rail-top': 'calc(var(--nav-h) + var(--ctx-h))' } as CSSProperties}>
      <WorkRail
        surface="workbench"
        title="Workbench"
        output={canvasOutput}
        foot={<RailFoot />}
        className="wb-work-shell"
      >
        {railContent}
        <LibrarySection onOpen={openInViewer} currentQuery={`${gene} ${cdna}`} openLabel="Open in viewer" />
      </WorkRail>
    </div>
  )
}
