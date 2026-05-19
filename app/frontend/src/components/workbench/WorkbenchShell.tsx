import { useCallback, useEffect, useRef, useState } from 'react'
import type { AlleleMode, WorkbenchTool } from '@/lib/backend'
import { getGeneViewer } from '@/lib/api'
import { adaptGeneViewer } from '@/lib/workbench/gene-viewer-adapter'
import { GENE_VIEWER_SAMPLE } from '@/lib/workbench/gene-viewer-sample'
import { CanvasHeader } from './CanvasHeader'
import { CrisprPanel } from './crispr/CrisprPanel'
import { PrimerPanel } from './primer/PrimerPanel'
import { SidePanel } from './SidePanel'
import { viewerCollapsed } from './tools'
import {
  SequenceViewerV2,
  type ScratchEntry,
  type SequenceViewerHandle,
} from './viewer/SequenceViewerV2'
import { ZoomSlider } from './viewer/ZoomSlider'
import { ZOOM_PRESETS } from './viewer/zoom-config'
import {
  DEFAULT_TRACKS,
  type SelectionSummary,
  type StrandMode,
  type TrackState,
  type ZoomLevel,
} from './viewer/viewer-types'

export type { ScratchEntry }

interface WorkbenchShellProps {
  tool: WorkbenchTool
}

const PANEL_TOOLS: WorkbenchTool[] = ['primer', 'crispr', 'align', 'compare']

// Workbench is RPE65-sample-scoped in this milestone (FE-4: no-param
// /workbench defaults to the RPE65 sample). The viewer query is the
// variant carried by the offline viewer sample; getGeneViewer() is
// mock-first (transport failure → GENE_VIEWER_SAMPLE; the adapter fills
// the whole-gene scaffold the payload does not carry yet).
const VIEWER_GENE = GENE_VIEWER_SAMPLE.identity.gene
const QUERY_CDNA = GENE_VIEWER_SAMPLE.queried_variant.hgvs_c

function readSideCollapsed(): boolean {
  try {
    return localStorage.getItem('eamos-side-collapsed') === '1'
  } catch {
    return false
  }
}

export function WorkbenchShell({ tool }: WorkbenchShellProps) {
  const [trackOn, setTrackOn] = useState<TrackState>(DEFAULT_TRACKS)
  const [strandMode, setStrandMode] = useState<StrandMode>('both')
  const [baseW, setBaseW] = useState<number>(ZOOM_PRESETS.exon)
  const [navCollapsed, setNavCollapsed] = useState(false)
  const [exonTableOpen, setExonTableOpen] = useState(false)
  const [sideCollapsed, setSideCollapsed] = useState(readSideCollapsed)
  const [scratch, setScratch] = useState<ScratchEntry[]>([])
  const [selSummary, setSelSummary] = useState<SelectionSummary | null>(null)
  // Seeded to the variant exon; the viewer re-reports via onActiveExonChange.
  const [activeExon, setActiveExon] = useState(4)

  // GV-006: reference/control vs variant-applied sequence basis. Default
  // `reference` per plans/gene-viewer/spec.md. Data is loaded via the
  // backend viewer endpoint (mock-first) and adapted for the active mode;
  // the adapter overlays the queried SNV onto the window in `variant` mode.
  const [alleleMode, setAlleleMode] = useState<AlleleMode>('reference')
  const [data, setData] = useState(() =>
    adaptGeneViewer(GENE_VIEWER_SAMPLE, 'reference'),
  )

  useEffect(() => {
    let stale = false
    getGeneViewer({
      gene: VIEWER_GENE,
      cdna: QUERY_CDNA,
      allele_mode: alleleMode,
    })
      .then((resp) => {
        if (!stale) setData(adaptGeneViewer(resp, alleleMode))
      })
      .catch(() => {
        // A reachable backend error keeps the last good (sample) render
        // rather than masking it with a blank canvas. Transport failure is
        // already handled inside getGeneViewer() (→ GENE_VIEWER_SAMPLE).
        if (!stale) setData(adaptGeneViewer(GENE_VIEWER_SAMPLE, alleleMode))
      })
    return () => {
      stale = true
    }
  }, [alleleMode])

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
  const onPreset = useCallback((level: ZoomLevel) => setBaseW(ZOOM_PRESETS[level]), [])

  return (
    <div className={`wb${sideCollapsed ? ' side-collapsed' : ''}`}>
      <main className="canvas">
        <CanvasHeader
          tool={tool}
          trackOn={trackOn}
          onToggleTrack={toggleTrack}
          strandMode={strandMode}
          onStrand={setStrandMode}
          alleleMode={alleleMode}
          onAlleleMode={setAlleleMode}
        />

        <section className={collapsed ? 'viewer viewer-collapsed' : 'viewer'}>
          <ZoomSlider
            baseW={baseW}
            navCollapsed={navCollapsed}
            onBaseW={setBaseW}
            onPreset={onPreset}
            onToggleNav={() => setNavCollapsed((c) => !c)}
          />
          <SequenceViewerV2
            ref={viewerRef}
            data={data}
            trackOn={trackOn}
            strandMode={strandMode}
            baseW={baseW}
            navCollapsed={navCollapsed}
            alleleMode={alleleMode}
            onScratchChange={setScratch}
            onSelectionChange={setSelSummary}
            onActiveExonChange={setActiveExon}
          />
        </section>

        <section className="tool-panels">
          {PANEL_TOOLS.map((p) => (
            <div
              key={p}
              className={p === tool ? 'tool-panel active' : 'tool-panel'}
              data-panel={p}
            >
              {p === 'primer' && <PrimerPanel gene={data.gene} cdna={QUERY_CDNA} />}
              {p === 'crispr' && <CrisprPanel gene={data.gene} cdna={QUERY_CDNA} />}
              {/* FE-7 (align/compare) fills the rest. */}
            </div>
          ))}
        </section>
      </main>

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
    </div>
  )
}
