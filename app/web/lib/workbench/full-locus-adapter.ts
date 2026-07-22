/* Thin adapter: backend GeneViewerResponse → FullLocusViewModel for the
   full-gene viewer slice (FGV-003). Mirrors the pattern of
   gene-viewer-adapter.ts, but the row body stays snake-case-flat from the
   backend contract because there is no second naming convention worth
   introducing for a row-oriented payload. */

import type { GeneViewerResponse } from '../backend'
import type { ViewerFullLocus } from '../backend'
import { buildFullLocusRows, type FullLocusRows } from './full-locus-layout'

export type FullLocusViewModel =
  | {
      kind: 'unsupported'
      gene: string
      cdna: string
      transcript: string
      warnings: string[]
    }
  | {
      kind: 'ready'
      gene: string
      cdna: string
      transcript: string
      transcriptOptions: string[]
      fullLocus: ViewerFullLocus
      rows: FullLocusRows
      warnings: string[]
    }

export function adaptFullLocus(resp: GeneViewerResponse): FullLocusViewModel {
  const gene = resp.identity.gene
  const cdna = resp.queried_variant.hgvs_c
  const transcript = resp.identity.resolved_transcript
  const warnings = [...resp.provenance.warnings]

  if (!resp.full_locus) {
    return { kind: 'unsupported', gene, cdna, transcript, warnings }
  }

  return {
    kind: 'ready',
    gene,
    cdna,
    transcript,
    transcriptOptions: Array.from(
      new Set([transcript, ...resp.identity.transcript_aliases].filter(Boolean)),
    ),
    fullLocus: resp.full_locus,
    rows: buildFullLocusRows(resp.full_locus),
    warnings,
  }
}
