import type { ZoomLevel } from './viewer-types'

export const BASE_W_MIN = 8
export const BASE_W_MAX = 22

/** Preset -> base width (px/base). Chips are semantic jumps; the slider is
 * continuous density. */
export const ZOOM_PRESETS: Record<ZoomLevel, number> = {
  gene: 9,
  exon: 14,
  codon: 20,
}
