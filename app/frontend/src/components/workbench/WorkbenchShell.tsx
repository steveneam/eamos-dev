import { useCallback, useRef, useState } from 'react'
import type { WorkbenchTool } from '@/lib/backend'
import { RPE65_V2 } from '@/lib/workbench/sample-rpe65-v2'
import { CanvasHeader } from './CanvasHeader'
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
  type StrandMode,
  type TrackState,
  type ZoomLevel,
} from './viewer/viewer-types'

export type { ScratchEntry }

interface WorkbenchShellProps {
  tool: WorkbenchTool
  onSelectTool: (tool: WorkbenchTool) => void
}

const PANEL_TOOLS: WorkbenchTool[] = ['primer', 'crispr', 'align', 'compare']
const DATA = RPE65_V2

function readSideCollapsed(): boolean {
  try {
    return localStorage.getItem('eamos-side-collapsed') === '1'
  } catch {
    return false
  }
}

export function WorkbenchShell({ tool, onSelectTool }: WorkbenchShellProps) {
  const [trackOn, setTrackOn] = useState<TrackState>(DEFAULT_TRACKS)
  const [strandMode, setStrandMode] = useState<StrandMode>('both')
  const [baseW, setBaseW] = useState<number>(ZOOM_PRESETS.exon)
  const [navCollapsed, setNavCollapsed] = useState(false)
  const [exonTableOpen, setExonTableOpen] = useState(false)
  const [sideCollapsed, setSideCollapsed] = useState(readSideCollapsed)
  const [scratch, setScratch] = useState<ScratchEntry[]>([])
  // Seeded to the variant exon; the viewer re-reports via onActiveExonChange.
  const [activeExon, setActiveExon] = useState(4)

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
          onSelectTool={onSelectTool}
          trackOn={trackOn}
          onToggleTrack={toggleTrack}
          strandMode={strandMode}
          onStrand={setStrandMode}
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
            data={DATA}
            trackOn={trackOn}
            strandMode={strandMode}
            baseW={baseW}
            navCollapsed={navCollapsed}
            onScratchChange={setScratch}
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
              {/* FE-6 (primer/crispr) and FE-7 (align/compare) fill these. */}
            </div>
          ))}
        </section>
      </main>

      <SidePanel
        tool={tool}
        data={DATA}
        scratch={scratch}
        collapsed={sideCollapsed}
        exonTableOpen={exonTableOpen}
        activeExon={activeExon}
        onToggleCollapsed={toggleSide}
        onToggleExonTable={() => setExonTableOpen((o) => !o)}
        onResetAll={() => viewerRef.current?.resetEdits()}
        onJumpToExon={(n) => viewerRef.current?.jumpToExon(n)}
      />
    </div>
  )
}
