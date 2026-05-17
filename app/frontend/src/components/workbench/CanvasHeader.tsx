import { useEffect, useRef, useState } from 'react'
import type { WorkbenchTool } from '@/lib/backend'
import { TOOL_META } from './tools'
import { ToolBar } from './ToolBar'
import type { StrandMode, TrackState } from './viewer/viewer-types'

const TRACKS: Array<{ key: keyof TrackState; label: string }> = [
  { key: 'annotations', label: 'Features (exon / intron / oligo)' },
  { key: 'domains', label: 'Protein domain bar' },
  { key: 'clinvar', label: 'ClinVar pins' },
  { key: 'clinvarDensity', label: 'ClinVar density (gene map)' },
  { key: 'conservation', label: 'Conservation (PhyloP)' },
  { key: 'restriction', label: 'Restriction sites' },
]

const STRANDS: Array<{ s: StrandMode; label: string; title: string }> = [
  { s: 'top', label: '5′→3′', title: 'Top strand only' },
  { s: 'both', label: 'Both', title: 'Both strands' },
  { s: 'rev', label: '3′→5′', title: 'Reverse-complement view' },
]

interface CanvasHeaderProps {
  tool: WorkbenchTool
  onSelectTool: (tool: WorkbenchTool) => void
  trackOn: TrackState
  onToggleTrack: (key: keyof TrackState) => void
  strandMode: StrandMode
  onStrand: (s: StrandMode) => void
}

export function CanvasHeader({
  tool,
  onSelectTool,
  trackOn,
  onToggleTrack,
  strandMode,
  onStrand,
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

  return (
    <div className="canvas-head">
      <div className="canvas-head-left">
        <h1 className="canvas-title">{meta.title}</h1>
        <span className="canvas-subtitle">{meta.sub}</span>
      </div>

      <div className="canvas-head-right">
        <ToolBar active={tool} onSelect={onSelectTool} />

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
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </svg>
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
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Export
            </button>
          </>
        )}
      </div>
    </div>
  )
}
