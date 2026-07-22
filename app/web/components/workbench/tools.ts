import type { WorkbenchTool } from '@/lib/backend'

export const TOOL_ORDER: WorkbenchTool[] = ['viewer', 'primer', 'crispr', 'align']

interface ToolMeta {
  /** Rail label (short) */
  rail: string
  /** Canvas-header title */
  title: string
  /** Canvas-header subtitle */
  sub: string
  /** Whether the track-toggle group is shown for this tool */
  tracks: boolean
}

export const TOOL_META: Record<WorkbenchTool, ToolMeta> = {
  viewer: {
    rail: 'Sequence',
    title: 'Sequence viewer',
    sub: 'RPE65 (ENSG00000116745) · 21,139 bp · exon 4 around c.260',
    tracks: true,
  },
  primer: {
    rail: 'Primer',
    title: 'Primer designer',
    sub: 'Primer3 engine · Sanger / qPCR modes',
    tracks: true,
  },
  crispr: {
    rail: 'CRISPR',
    title: 'CRISPR designer',
    sub: 'Provider-verified guide design · gRNA + ssODN repair template',
    tracks: true,
  },
  align: {
    rail: 'Align',
    title: 'Sequence alignment',
    sub: 'Pairwise alignment · paste / FASTA / AB1 chromatogram',
    tracks: false,
  },
  compare: {
    rail: 'Compare',
    title: 'Variant comparator',
    sub: 'Side-by-side comparison of 2–3 variants in this gene',
    tracks: false,
  },
}

/** Three-state pane for the workbench 3-column canvas: the sequence viewer can
 *  be `expanded` (shares the canvas with the tool rail), `collapsed` (a narrow
 *  stub the user can re-expand), or `hidden` (removed so the tool takes the full
 *  width — e.g. the CRISPR off-target table). */
export type ViewerPane = 'expanded' | 'collapsed' | 'hidden'

/** Default pane per tool — Align opens `collapsed` (the alignment result is the
 *  focus, the reference sequence is secondary); Primer/CRISPR open `expanded`
 *  (the sequence informs the design). */
export function defaultViewerPane(tool: WorkbenchTool): ViewerPane {
  return tool === 'align' ? 'collapsed' : 'expanded'
}
