'use client'
import type { ZoomLevel } from './viewer-types'
import { BASE_W_MAX, BASE_W_MIN } from './zoom-config'

function presetForBaseW(w: number): ZoomLevel {
  if (w <= 11) return 'gene'
  if (w >= 18) return 'codon'
  return 'exon'
}

interface ZoomSliderProps {
  baseW: number
  navCollapsed: boolean
  onBaseW: (w: number) => void
  onPreset: (level: ZoomLevel) => void
  onToggleNav: () => void
}

const LEVELS: ZoomLevel[] = ['gene', 'exon', 'codon']

export function ZoomSlider({
  baseW,
  navCollapsed,
  onBaseW,
  onPreset,
  onToggleNav,
}: ZoomSliderProps) {
  const active = presetForBaseW(baseW)
  return (
    <div className="sv-zoombar">
      <div className="zoom-slider" role="group" aria-label="Zoom density">
        <button
          type="button"
          className="zoom-step"
          aria-label="Zoom out"
          onClick={() => onBaseW(Math.max(BASE_W_MIN, baseW - 2))}
        >
          −
        </button>
        <input
          type="range"
          min={BASE_W_MIN}
          max={BASE_W_MAX}
          step={1}
          value={baseW}
          aria-label="Base density"
          onChange={(e) => onBaseW(Number(e.target.value))}
        />
        <button
          type="button"
          className="zoom-step"
          aria-label="Zoom in"
          onClick={() => onBaseW(Math.min(BASE_W_MAX, baseW + 2))}
        >
          +
        </button>
      </div>

      <div className="zoom-pill" role="group" aria-label="Zoom level">
        {LEVELS.map((z) => (
          <button
            key={z}
            type="button"
            className={z === active ? 'active' : undefined}
            onClick={() => onPreset(z)}
          >
            {z[0].toUpperCase() + z.slice(1)}
          </button>
        ))}
      </div>

      <button
        type="button"
        className={`sv-navtoggle${navCollapsed ? ' on' : ''}`}
        title={navCollapsed ? 'Show gene map' : 'Hide gene map'}
        aria-pressed={navCollapsed}
        onClick={onToggleNav}
      >
        {navCollapsed ? 'Show map' : 'Hide map'}
      </button>
    </div>
  )
}
