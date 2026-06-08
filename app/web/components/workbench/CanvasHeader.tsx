'use client'
import { useEffect, useRef, useState } from 'react'
import type { AlleleMode, WorkbenchTool } from '@/lib/backend'
import { TOOL_META } from './tools'
import { IconExport, IconTracks } from '@/components/icons/Icon'
import type { StrandMode, TrackState } from './viewer/viewer-types'

// Minimal-chrome header above the viewer: shows the active gene + variant
// only. Descriptive metrics (transcript ID, coordinates, build, gene length)
// stay in the right-hand workspace panel — they don't earn space here.

const TRACKS: Array<{ key: keyof TrackState; label: string }> = [
  { key: 'annotations', label: 'Features (exon / intron / oligo)' },
  { key: 'domains', label: 'Protein domain bar' },
  { key: 'clinvar', label: 'ClinVar (gene map + in-window pins)' },
  { key: 'conservation', label: 'Conservation (PhyloP)' },
  { key: 'restriction', label: 'Restriction sites' },
]

const ALLELES: Array<{ m: AlleleMode; label: string; title: string }> = [
  { m: 'reference', label: 'Reference', title: 'Reference / control sequence' },
  {
    m: 'variant',
    label: 'Variant',
    title: 'Variant-applied: the queried SNV overlaid on the window',
  },
]

export type ViewerMode = 'window' | 'locus'

const VIEWER_MODES: Array<{ m: ViewerMode; label: string; title: string }> = [
  { m: 'window', label: 'Window', title: 'CDS-centric window with introns collapsed' },
  {
    m: 'locus',
    label: 'Full gene',
    title: 'Full genomic locus — introns and UTRs visible',
  },
]

const STRANDS: Array<{ s: StrandMode; label: string; title: string }> = [
  { s: 'top', label: '5′→3′', title: 'Top strand only' },
  { s: 'both', label: 'Both', title: 'Both strands' },
  { s: 'rev', label: '3′→5′', title: 'Reverse-complement view' },
]

interface CanvasHeaderProps {
  tool: WorkbenchTool
  trackOn: TrackState
  onToggleTrack: (key: keyof TrackState) => void
  strandMode: StrandMode
  onStrand: (s: StrandMode) => void
  alleleMode: AlleleMode
  onAlleleMode: (m: AlleleMode) => void
  viewerMode?: ViewerMode
  onViewerMode?: (m: ViewerMode) => void
}

export function CanvasHeader({
  tool,
  trackOn,
  onToggleTrack,
  strandMode,
  onStrand,
  alleleMode,
  onAlleleMode,
  viewerMode,
  onViewerMode,
}: CanvasHeaderProps) {
  const meta = TOOL_META[tool]
  const [tracksOpen, setTracksOpen] = useState(false)
  const tracksRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!tracksOpen) return
    const onDown = (e: MouseEvent) => {
      if (tracksRef.current && !tracksRef.current.contains(e.target as Node))
        setTracksOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [tracksOpen])

  const trackCount = Object.values(trackOn).filter(Boolean).length

  // The gene · variant identity lives in the context strip now (single source);
  // this header is just the view controls. When a tool has none (e.g. Align),
  // there's nothing to render.
  const hasControls = tool === 'viewer' || meta.tracks
  if (!hasControls) return null

  return (
    <div className="canvas-head">
      <div className="canvas-head-right">
        {tool === 'viewer' && viewerMode && onViewerMode && (
          <div
            className="sv-strand-pill sv-viewer-mode-pill"
            role="group"
            aria-label="Viewer mode"
          >
            {VIEWER_MODES.map((vm) => (
              <button
                key={vm.m}
                type="button"
                className={viewerMode === vm.m ? 'active' : undefined}
                title={vm.title}
                onClick={() => onViewerMode(vm.m)}
              >
                {vm.label}
              </button>
            ))}
          </div>
        )}
        {tool === 'viewer' && (
          <div
            className="sv-strand-pill sv-allele-pill"
            role="group"
            aria-label="Sequence basis"
          >
            {ALLELES.map((al) => (
              <button
                key={al.m}
                type="button"
                className={alleleMode === al.m ? 'active' : undefined}
                title={al.title}
                onClick={() => onAlleleMode(al.m)}
              >
                {al.label}
              </button>
            ))}
          </div>
        )}
        {meta.tracks && (
          <>
            <div className="sv-dropdown" ref={tracksRef}>
              <button
                type="button"
                className="sv-dropdown-btn"
                aria-haspopup="menu"
                aria-expanded={tracksOpen}
                aria-controls="sv-tracks-menu"
                onClick={() => setTracksOpen((o) => !o)}
              >
                <IconTracks />
                Tracks
                <span className="sv-dropdown-count">{trackCount}</span>
              </button>
              {tracksOpen && (
                <div className="sv-dropdown-menu" id="sv-tracks-menu">
                  {TRACKS.map((t) => (
                    <label key={t.key}>
                      <input
                        type="checkbox"
                        checked={trackOn[t.key]}
                        onChange={() => onToggleTrack(t.key)}
                      />
                      <span>{t.label}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="sv-strand-pill" role="group" aria-label="Strand orientation">
              {STRANDS.map((st) => (
                <button
                  key={st.s}
                  type="button"
                  className={strandMode === st.s ? 'active' : undefined}
                  title={st.title}
                  onClick={() => onStrand(st.s)}
                >
                  {st.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              className="sv-export-btn"
              title="Export / print this view"
              onClick={() => window.print()}
            >
              <IconExport />
              Export
            </button>
          </>
        )}
      </div>
    </div>
  )
}
