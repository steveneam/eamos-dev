'use client'
import { BASE_W_MAX, BASE_W_MIN } from './zoom-config'

interface ZoomSliderProps {
  baseW: number
  onBaseW: (w: number) => void
}

// Minimal zoom control: −/+ steppers around a density slider. Lives inside
// the viewer canvas (hover-revealed) so the chrome stays out of the way.
// The semantic Gene/Exon/Codon presets and the Hide-map button were
// retired — the density slider alone is enough density control, and the
// gene-minimap collapse is now handled by its own section header.
export function ZoomSlider({ baseW, onBaseW }: ZoomSliderProps) {
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
    </div>
  )
}
