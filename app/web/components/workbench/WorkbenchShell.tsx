'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { AlleleMode, WorkbenchTool } from '@/lib/backend'
import { getGeneViewer } from '@/lib/api'
import { adaptGeneViewer } from '@/lib/workbench/gene-viewer-adapter'
import { adaptFullLocus, type FullLocusViewModel } from '@/lib/workbench/full-locus-adapter'
import { GENE_VIEWER_SAMPLE } from '@/lib/workbench/gene-viewer-sample'
import type { GeneWindowData } from '@/lib/workbench/gene-window'
import { CanvasHeader, type ViewerMode } from './CanvasHeader'
import { SidePanel } from './SidePanel'
import { viewerCollapsed } from './tools'
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

export type { ScratchEntry }

interface WorkbenchShellProps {
  tool: WorkbenchTool
  gene: string
  cdna: string
  transcript?: string
}

const PANEL_TOOLS: WorkbenchTool[] = ['primer', 'crispr', 'align', 'compare']

function renderToolPanel(
  tool: WorkbenchTool,
  gene: string,
  cdna: string,
  data: GeneWindowData,
) {
  switch (tool) {
    case 'primer':
      return <PrimerPanel gene={gene} cdna={cdna} />
    case 'crispr':
      return <CrisprPanel gene={gene} cdna={cdna} />
    case 'align':
      return <AlignPanel data={data} cdna={cdna} />
    case 'compare':
      // Compare tool is still pending — keeps the placeholder.
      return <div className="viewer-loading">Compare tool — coming soon</div>
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

function readSideCollapsed(): boolean {
  try {
    return localStorage.getItem('eamos-side-collapsed') === '1'
  } catch {
    return false
  }
}

export function WorkbenchShell({ tool, gene, cdna, transcript }: WorkbenchShellProps) {
  const [trackOn, setTrackOn] = useState<TrackState>(DEFAULT_TRACKS)
  const [strandMode, setStrandMode] = useState<StrandMode>('both')
  const [baseW, setBaseW] = useState<number>(ZOOM_PRESETS.exon)
  const [navCollapsed, setNavCollapsed] = useState(false)
  const [exonTableOpen, setExonTableOpen] = useState(false)
  const [sideCollapsed, setSideCollapsed] = useState(readSideCollapsed)
  const [scratch, setScratch] = useState<ScratchEntry[]>([])
  const [selSummary, setSelSummary] = useState<SelectionSummary | null>(null)
  const [activeExon, setActiveExon] = useState(4)

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
  const collapsed = viewerCollapsed(tool)

  const toggleTrack = useCallback(
    (key: keyof TrackState) => setTrackOn((t) => ({ ...t, [key]: !t[key] })),
    [],
  )
  const toggleSide = useCallback(() => {
    setSideCollapsed((c) => {
      const next = !c
      try {
        localStorage.setItem('eamos-side-collapsed', next ? '1' : '0')
      } catch {
        /* private mode — ignore */
      }
      return next
    })
  }, [])

  return (
    <div className={`wb${sideCollapsed && data ? ' side-collapsed' : ''}`}>
      <main className="canvas">
        <CanvasHeader
          tool={tool}
          gene={gene}
          variant={cdna}
          trackOn={trackOn}
          onToggleTrack={toggleTrack}
          strandMode={strandMode}
          onStrand={setStrandMode}
          alleleMode={alleleMode}
          onAlleleMode={setAlleleMode}
          viewerMode={viewerMode}
          onViewerMode={setViewerMode}
        />

        <section className={collapsed ? 'viewer viewer-collapsed' : 'viewer'}>
          {viewerMode === 'locus' && locusModel?.kind === 'ready' ? (
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
            />
          ) : (
            <div className="viewer-loading" role={viewerError ? 'alert' : 'status'}>
              {viewerError ?? 'Loading sequence...'}
            </div>
          )}
        </section>

        <section className="tool-panels">
          {data ? (
            PANEL_TOOLS.map((p) => (
              <div
                key={p}
                className={p === tool ? 'tool-panel active' : 'tool-panel'}
                data-panel={p}
              >
                {p === tool && renderToolPanel(p, gene, cdna, data)}
              </div>
            ))
          ) : (
            <div className="tool-panel active" data-panel={tool}>
              <div className="viewer-loading">{viewerError ?? 'Loading sequence...'}</div>
            </div>
          )}
        </section>
      </main>

      {data ? (
        <SidePanel
          tool={tool}
          data={data}
          scratch={scratch}
          selection={selSummary}
          collapsed={sideCollapsed}
          exonTableOpen={exonTableOpen}
          activeExon={activeExon}
          onToggleCollapsed={toggleSide}
          onToggleExonTable={() => setExonTableOpen((o) => !o)}
          onResetAll={() => viewerRef.current?.resetEdits()}
          onJumpToExon={(n) => viewerRef.current?.jumpToExon(n)}
          onDelSelection={() => viewerRef.current?.delSelection()}
          onReplaceSelection={(seq) => viewerRef.current?.replaceSelection(seq)}
          onClearSelection={() => viewerRef.current?.clearSelection()}
        />
      ) : (
        <aside className="side">
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
        </aside>
      )}
    </div>
  )
}
