/** Strand display mode for the sequence rows. */
export type StrandMode = 'top' | 'both' | 'rev'

/** Toggleable viewer tracks. `clinvar` = the unified ClinVar layer:
 *  gene-map per-exon density bubbles + in-window pins. */
export interface TrackState {
  annotations: boolean
  domains: boolean
  clinvar: boolean
  conservation: boolean
  restriction: boolean
}

export const DEFAULT_TRACKS: TrackState = {
  annotations: true,
  domains: false,
  clinvar: true,
  conservation: false,
  restriction: false,
}

/** Selection summary mirrored out of the viewer to the side-panel edit hub
 *  (FE-5.6 Unit C). The reducer + raw `{start,end}` stay inside the viewer;
 *  only this presentational digest crosses the callback seam. */
export interface SelectionSummary {
  /** Flat positions in the selection (>= 1). */
  len: number
  /** `posDisplay` of the low end (== `hiPos` when `len === 1`). */
  loPos: string
  /** `posDisplay` of the high end. */
  hiPos: string
  /** Single-base reference letter (`len === 1`); `''` for a range. */
  refBase: string
  /** Single-base: whether an edit already exists at this position. */
  hasEdit: boolean
  /** Range (`len > 1`) exonic/intronic breakdown; `''` for a single base. */
  span: string
}
