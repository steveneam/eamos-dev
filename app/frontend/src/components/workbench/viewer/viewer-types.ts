/** Strand display mode for the sequence rows. */
export type StrandMode = 'top' | 'both' | 'rev'

/** Toggleable viewer tracks. `clinvar` = in-window pins;
 *  `clinvarDensity` = the gene-minimap per-exon bubbles (modification #1). */
export interface TrackState {
  annotations: boolean
  domains: boolean
  clinvar: boolean
  clinvarDensity: boolean
  conservation: boolean
  restriction: boolean
}

export const DEFAULT_TRACKS: TrackState = {
  annotations: true,
  domains: false,
  clinvar: true,
  clinvarDensity: true,
  conservation: false,
  restriction: false,
}

/** Semantic zoom presets — retained alongside the density slider. */
export type ZoomLevel = 'gene' | 'exon' | 'codon'
